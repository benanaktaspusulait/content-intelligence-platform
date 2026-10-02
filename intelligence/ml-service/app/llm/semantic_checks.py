"""LLM-semantic quality checks that genuinely require judgment calls a
deterministic rule cannot make: whether two differently-worded attempts
represent the same underlying strategy, and whether a final twist is a
consequence of the same physical rule established earlier in the video.

Follows the same strict-JSON-with-markdown-fallback parsing convention as
app.qa.character_verifier.CharacterVerifier, and never silently treats an
unparseable LLM response as a passing (or any other) verdict — callers must
treat SemanticCheckServiceError as fail-closed, not fail-open.
"""

import json
import re
from typing import Any

from app.llm import get_provider


class SemanticCheckServiceError(RuntimeError):
    """Raised when an LLM response cannot be parsed into the expected shape.

    Callers (rule evaluators) must map this to RuleOutcome.SERVICE_ERROR,
    never to a silent PASS or FAIL guess.
    """


def _parse_json_with_markdown_fallback(response: str) -> dict[str, Any]:
    """Parse an LLM response as JSON, retrying inside a ```json fenced block.

    Mirrors CharacterVerifier._parse_llm_response's fallback strategy.
    """
    try:
        result: dict[str, Any] = json.loads(response)
        return result
    except json.JSONDecodeError as e:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                return result
            except json.JSONDecodeError:
                pass
        raise SemanticCheckServiceError(f"Failed to parse LLM response as JSON: {e}") from e


def find_duplicate_strategy_pairs(
    attempts: list[dict[str, str]], llm_provider: str | None = None
) -> list[tuple[int, int]]:
    """Identify attempt pairs that are the same strategy despite different wording.

    `attempts` must already be verb-distinct (the caller filters out literal
    primaryVerb repeats before calling this — those are a free deterministic
    check and never need an LLM call). Each attempt dict has keys
    "primaryVerb", "action", "consequence".

    Returns a list of (i, j) index pairs, i < j, that the LLM judges to be the
    same underlying strategy. Returns [] when 0 or 1 attempts are given
    (nothing to compare) without calling the LLM at all, and when the LLM
    confirms no duplicates.

    Raises SemanticCheckServiceError if the LLM response cannot be parsed.
    """
    if len(attempts) < 2:
        return []

    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        # get_provider/<Provider>.__init__ raises a bare ValueError for
        # missing credentials (e.g. "OPENAI_API_KEY not set"). Callers must
        # see this as a service error, not an unhandled exception that
        # crashes the whole rule evaluation.
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_attempts = "\n".join(
        f"{i}. primaryVerb={a['primaryVerb']!r}, action={a['action']!r}, consequence={a['consequence']!r}"
        for i, a in enumerate(attempts)
    )

    prompt = f"""You are reviewing a list of problem-solving attempts in a children's \
short-form video. Each attempt has a different labeled primary verb, but some attempts \
might still represent the SAME underlying strategy despite different wording (for \
example, "GRAB" and "YANK" can both just mean "pull the object away").

Attempts (0-indexed):
{numbered_attempts}

Identify which pairs of attempts, if any, represent the same underlying mechanical \
strategy rather than genuinely different approaches.

Respond in strict JSON format:
{{
  "duplicate_pairs": [[i, j], ...]
}}

Use an empty list if every attempt is a genuinely different strategy."""

    response = llm.complete(prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    if "duplicate_pairs" not in parsed:
        raise SemanticCheckServiceError("LLM response missing required field: duplicate_pairs")
    if not isinstance(parsed["duplicate_pairs"], list):
        raise SemanticCheckServiceError("duplicate_pairs must be a list")

    pairs: list[tuple[int, int]] = []
    for entry in parsed["duplicate_pairs"]:
        if not isinstance(entry, list) or len(entry) != 2:
            raise SemanticCheckServiceError(f"Malformed duplicate pair entry: {entry!r}")
        i, j = entry
        if not isinstance(i, int) or not isinstance(j, int):
            raise SemanticCheckServiceError(f"Malformed duplicate pair entry: {entry!r}")
        pairs.append((min(i, j), max(i, j)))

    return pairs


def check_twist_matches_rule(
    physical_rule: str, twist_description: str, llm_provider: str | None = None
) -> tuple[bool, str]:
    """Judge whether a final twist derives from the same established physical rule.

    Returns (matches, reasoning). Raises SemanticCheckServiceError if the LLM
    response cannot be parsed into the expected shape.
    """
    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        # Same fail-closed conversion as find_duplicate_strategy_pairs above:
        # missing credentials must surface as a typed service error, not an
        # unhandled exception that crashes the whole rule evaluation.
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    prompt = f"""You are reviewing the ending of a children's short-form video for \
structural consistency.

Established physical rule: {physical_rule!r}

Final twist: {twist_description!r}

Does the final twist derive from the SAME physical rule established earlier, just \
applied in a new or bigger way? Or does it introduce an unrelated, disconnected joke?

Respond in strict JSON format:
{{
  "matches_rule": true or false,
  "reasoning": "brief explanation of your decision"
}}"""

    response = llm.complete(prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    required_fields = ["matches_rule", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise SemanticCheckServiceError(f"LLM response missing required field: {field}")

    if not isinstance(parsed["matches_rule"], bool):
        raise SemanticCheckServiceError("matches_rule must be a boolean")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")

    return parsed["matches_rule"], parsed["reasoning"]


def count_independent_mechanics(
    physical_rule: str, beat_descriptions: list[str], llm_provider: str | None = None
) -> tuple[int, str]:
    """Judge how many independent physical/magical rules a concept actually exhibits.

    `physical_rule` is the author's stated core mechanic description.
    `beat_descriptions` is an ordered list of beat consequence/action strings
    across the video's timeline. Distinguishes "same mechanic applied with
    escalating/varied consequences" (count=1) from "a second, independent
    mechanic introduced partway through" (count=2+).

    Returns (mechanic_count, reasoning). With 0 or 1 beat descriptions there is
    nothing to compare, so this short-circuits to (1, <fixed reasoning>) without
    calling the LLM at all, mirroring find_duplicate_strategy_pairs' handling of
    a too-small input.

    Raises SemanticCheckServiceError if the LLM response cannot be parsed into
    the expected shape, if the LLM provider is unavailable (e.g. missing
    credentials), or if the LLM reports a count less than 1 (a concept always
    has at least one mechanic; anything else is a malformed/hallucinated
    response, not a valid judgment).
    """
    if len(beat_descriptions) < 2:
        return 1, "Fewer than two beats to compare; trivially a single mechanic."

    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        # get_provider/<Provider>.__init__ raises a bare ValueError for
        # missing credentials (e.g. "OPENAI_API_KEY not set"). Callers must
        # see this as a service error, not an unhandled exception that
        # crashes the whole rule evaluation.
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_beats = "\n".join(f"{i}. {desc!r}" for i, desc in enumerate(beat_descriptions))

    prompt = f"""You are reviewing a children's short-form video concept for mechanic focus.

Stated core physical/magical rule: {physical_rule!r}

Beat-by-beat consequences across the timeline (0-indexed):
{numbered_beats}

Determine how many independent physical/magical rules these beats collectively exhibit.
A single rule applied repeatedly — even with escalating, varied, or increasingly dramatic
consequences — counts as ONE mechanic (example: a puddle that gets deeper and deeper as a
character touches it with toe, then foot, then both feet is still one mechanic: "touching
increases depth"). A second, genuinely independent rule introduced partway through counts
as a SECOND mechanic (example: that same puddle later growing legs and chasing the
character on its own is a new, unrelated rule, not an escalation of the depth rule).

The count can never be less than 1 (every concept has at least one mechanic).

Respond in strict JSON format:
{{
  "mechanic_count": <integer, 1 or more>,
  "reasoning": "brief explanation identifying which beat(s), if any, introduce an independent mechanic"
}}"""

    response = llm.complete(prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    required_fields = ["mechanic_count", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise SemanticCheckServiceError(f"LLM response missing required field: {field}")

    if isinstance(parsed["mechanic_count"], bool) or not isinstance(parsed["mechanic_count"], int):
        raise SemanticCheckServiceError("mechanic_count must be an integer")
    if parsed["mechanic_count"] < 1:
        raise SemanticCheckServiceError(f"mechanic_count must be >= 1, got {parsed['mechanic_count']!r}")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")

    return parsed["mechanic_count"], parsed["reasoning"]
