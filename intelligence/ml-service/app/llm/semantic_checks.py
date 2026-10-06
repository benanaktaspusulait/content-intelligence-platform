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

from app.llm import LLMProvider, get_provider


class SemanticCheckServiceError(RuntimeError):
    """Raised when an LLM response cannot be parsed into the expected shape.

    Callers (rule evaluators) must map this to RuleOutcome.SERVICE_ERROR,
    never to a silent PASS or FAIL guess.
    """


def check_single_agent_object_mechanic(
    primary_character: str,
    secondary_characters: list[str],
    physical_rule: str,
    cause_effect: str,
    beat_descriptions: list[str],
    llm_provider: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Judge whether one character and one object own the central mechanic."""
    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    prompt = f"""You are evaluating a children's short-form video concept.
The concept requires exactly one primary living agent interacting with exactly
one primary non-living object. Judge causal participation, not raw character
count. A background character that does not affect the mechanic is irrelevant.

Primary character: {primary_character!r}
Other named characters: {secondary_characters!r}
Physical rule: {physical_rule!r}
Cause and effect: {cause_effect!r}
Beat descriptions: {beat_descriptions!r}

A second living character is causal if it creates, demonstrates, obstructs,
triggers, resolves, or receives the payoff from the impossible mechanic. If
the evidence is insufficient, return UNKNOWN. Do not guess a missing object.

Respond with strict JSON:
{{
  "primary_agent": "name or null",
  "primary_object": "name or null",
  "mechanic_carrier": "OBJECT | OBJECT_INTERACTION | PRIMARY_AGENT | SECONDARY_AGENT | MULTI_AGENT | UNKNOWN",
  "causal_participants": ["names"],
  "decision": "PASS | FAIL | UNKNOWN",
  "reasoning": "brief explanation"
}}"""

    response = _call_llm_safely(llm, prompt)
    parsed = _parse_json_with_markdown_fallback(response)
    required = {
        "primary_agent", "primary_object", "mechanic_carrier",
        "causal_participants", "decision", "reasoning",
    }
    missing = required - parsed.keys()
    if missing:
        raise SemanticCheckServiceError(f"LLM response missing required fields: {sorted(missing)}")
    if not isinstance(parsed["primary_agent"], (str, type(None))) or not isinstance(
        parsed["primary_object"], (str, type(None))
    ):
        raise SemanticCheckServiceError("primary_agent and primary_object must be strings or null")
    if parsed["mechanic_carrier"] not in {
        "OBJECT", "OBJECT_INTERACTION", "PRIMARY_AGENT", "SECONDARY_AGENT", "MULTI_AGENT", "UNKNOWN"
    }:
        raise SemanticCheckServiceError("mechanic_carrier has an invalid value")
    if not isinstance(parsed["causal_participants"], list) or not all(
        isinstance(item, str) for item in parsed["causal_participants"]
    ):
        raise SemanticCheckServiceError("causal_participants must be a list of strings")
    if parsed["decision"] not in {"PASS", "FAIL", "UNKNOWN"}:
        raise SemanticCheckServiceError("decision has an invalid value")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")
    return {key: parsed[key] for key in required if key != "decision"}, parsed["decision"]


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


def _call_llm_safely(llm: LLMProvider, prompt: str) -> str:
    """Call ``llm.complete(prompt)``, converting ANY runtime failure
    (timeout, HTTP error, SDK error, network failure, malformed-response
    exception, or anything else the provider's SDK can raise) into
    SemanticCheckServiceError.

    This is distinct from the provider-construction ValueError each calling
    function already catches around ``get_provider(...)`` (missing
    credentials) -- that happens before this function is ever called. This
    function exists because the actual network call is where timeouts, HTTP
    errors, and SDK-internal errors occur, and until this fix those were not
    normalized at all: a provider-construction failure correctly became a
    typed SERVICE_ERROR, but a mid-call network blip crashed the whole
    request with an unstructured 500.
    """
    try:
        return llm.complete(prompt)
    except SemanticCheckServiceError:
        raise
    except Exception as e:
        raise SemanticCheckServiceError(f"LLM call failed: {e}") from e


def find_duplicate_strategy_pairs(
    attempts: list[dict[str, Any]], llm_provider: str | None = None
) -> list[tuple[int, int]]:
    """Identify attempt pairs that are the same strategy despite different wording.

    `attempts` must already be verb-distinct (the caller filters out literal
    primaryVerb repeats before calling this — those are a free deterministic
    check and never need an LLM call). Each attempt dict has keys
    primaryVerb, action, consequence, intendedStrategyFamily, reactiveActionFamily,
    targetObject, intendedEffect, and result.

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
        "{i}. intendedStrategyFamily={intended!r}, reactiveActionFamily={reactive!r}, "
        "primaryVerb={verb!r}, targetObject={target!r}, intendedEffect={effect!r}, "
        "action={action!r}, consequence={consequence!r}, result={result!r}".format(
            i=i,
            intended=a.get("intendedStrategyFamily", a.get("strategyFamily", "")),
            reactive=a.get("reactiveActionFamily", ""),
            verb=a.get("primaryVerb", ""),
            target=a.get("targetObject", ""),
            effect=a.get("intendedEffect", ""),
            action=a.get("action", ""),
            consequence=a.get("consequence", ""),
            result=a.get("result", ""),
        )
        for i, a in enumerate(attempts)
    )

    prompt = f"""You are reviewing a list of problem-solving attempts in a children's \
short-form video. Each attempt has a different labeled primary verb, but some attempts \
might still represent the SAME underlying strategy despite different wording.

Two ways attempts can be duplicates despite different wording:
1. Synonym substitution: "GRAB" and "YANK" can both just mean "pull the object away."
2. Intensity/angle variants of the identical strategy: "PUSH", "PUSH_HARDER", and \
"PUSH_FROM_LEFT" are still just "push the object" tried again with a different \
force or direction — not a new strategy. If the attempts all boil down to the \
same basic mechanical action repeated with more effort or from a different angle, \
and produce essentially the same kind of consequence each time, treat them as \
duplicates.

The one thing that makes attempts genuinely different, even with an overlapping verb, \
is a meaningfully different consequence or mechanism — e.g. "PUSH" that slides the \
object away vs. a later "PUSH" that is revealed to flip the object over is two \
different strategies, because the consequence differs in kind, not just in degree.

Attempts (0-indexed):
{numbered_attempts}

Identify which pairs of attempts, if any, represent the same underlying mechanical \
strategy rather than genuinely different approaches.

Respond in strict JSON format:
{{
  "duplicate_pairs": [[i, j], ...]
}}

Use an empty list if every attempt is a genuinely different strategy."""

    response = _call_llm_safely(llm, prompt)
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
    physical_rule: str,
    twist_description: str,
    llm_provider: str | None = None,
    *,
    mechanic_evidence: dict[str, Any] | None = None,
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
Canonical mechanic evidence: {mechanic_evidence or {}!r}

Final twist: {twist_description!r}

Does the final twist derive from the SAME physical rule established earlier, just \
applied in a new or bigger way? Or does it introduce an unrelated, disconnected joke?

Respond in strict JSON format:
{{
  "matches_rule": true or false,
  "reasoning": "brief explanation of your decision"
}}"""

    response = _call_llm_safely(llm, prompt)
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

    response = _call_llm_safely(llm, prompt)
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


def check_goal_is_natural(
    character_name: str,
    physical_rule: str,
    beat_descriptions: list[str],
    goal_evidence: dict[str, Any] | None = None,
    llm_provider: str | None = None,
) -> tuple[bool, str]:
    """Judge whether the character has an immediately understandable, natural
    physical goal that the established abnormal rule genuinely obstructs.

    Distinguishes a believable reason to keep trying (the character wants
    something ordinary and ought to want it) from an arbitrary or
    magic-demo setup invented only to showcase the mechanic (the character
    could simply walk away with no believable reason to continue).

    Returns (is_natural, reasoning). Raises SemanticCheckServiceError if the
    LLM response cannot be parsed into the expected shape, or if the LLM
    provider is unavailable (e.g. missing credentials).
    """
    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_beats = "\n".join(f"{i}. {desc!r}" for i, desc in enumerate(beat_descriptions))

    prompt = f"""You are reviewing a children's short-form video concept for goal clarity.

Character: {character_name!r}
Established abnormal physical rule: {physical_rule!r}
Canonical local-goal evidence (may be implicit, not a performance signal): {goal_evidence or {}!r}

Beat-by-beat actions/consequences across the timeline (0-indexed):
{numbered_beats}

Determine whether the character has an immediately understandable, natural physical
goal, and whether the abnormal rule genuinely obstructs that goal.

PASS example: a character wants to put on a slipper, straighten a picture frame, or
pick up a dropped pencil — an ordinary, believable thing to want — and the abnormal
rule gets in the way of that ordinary goal.

FAIL example: a character deliberately keeps dropping a pencil "to see if it floats,"
or otherwise has no goal beyond demonstrating the mechanic itself — the character
could simply walk away with no believable reason to keep trying.

Respond in strict JSON format:
{{
  "is_natural": true or false,
  "reasoning": "brief explanation of your decision"
}}"""

    response = _call_llm_safely(llm, prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    required_fields = ["is_natural", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise SemanticCheckServiceError(f"LLM response missing required field: {field}")

    if not isinstance(parsed["is_natural"], bool):
        raise SemanticCheckServiceError("is_natural must be a boolean")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")

    return parsed["is_natural"], parsed["reasoning"]


def check_rule_is_predictable(
    physical_rule: str, beat_descriptions: list[str], llm_provider: str | None = None
) -> tuple[bool, str]:
    """Judge whether a viewer could learn the established abnormal rule from
    the first 1-2 occurrences and predict what happens next.

    A single consistent mechanic (per CONCEPT_007) is not the same as a
    LEGIBLE one: a rule that depends on the character's exact position,
    angle, and speed in combination is technically one mechanic but
    unlearnable by a child audience watching once. This check asks whether
    the pattern is simple enough that a viewer could say "aha, I get it"
    partway through and anticipate the next beat.

    Returns (is_predictable, reasoning). Raises SemanticCheckServiceError if
    the LLM response cannot be parsed into the expected shape, or if the LLM
    provider is unavailable (e.g. missing credentials).
    """
    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_beats = "\n".join(f"{i}. {desc!r}" for i, desc in enumerate(beat_descriptions))

    prompt = f"""You are reviewing a children's short-form video concept for rule readability.

Stated physical/magical rule: {physical_rule!r}

Beat-by-beat actions/consequences across the timeline (0-indexed):
{numbered_beats}

Determine whether a child viewer could learn this rule from the first 1-2
occurrences and predict what happens on later occurrences — i.e. the rule is
SIMPLE and PREDICTABLE, not just internally consistent.

PASS example: "Kiko drops it -> the frame tilts sideways" or "Arda pushes the handle
down -> the handle pops back up" — one clear trigger, one clear consequence, easy
to anticipate after seeing it once.

FAIL example: a rule that depends on a combination of the character's exact position,
angle, and movement speed to determine which direction an object goes — technically
one consistent rule, but a viewer cannot learn or predict it from watching, because
too many factors interact at once.

Respond in strict JSON format:
{{
  "is_predictable": true or false,
  "reasoning": "brief explanation of your decision"
}}"""

    response = _call_llm_safely(llm, prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    required_fields = ["is_predictable", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise SemanticCheckServiceError(f"LLM response missing required field: {field}")

    if not isinstance(parsed["is_predictable"], bool):
        raise SemanticCheckServiceError("is_predictable must be a boolean")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")

    return parsed["is_predictable"], parsed["reasoning"]


def check_opening_problem_legible(
    anomaly: str, opening_beat_descriptions: list[str], llm_provider: str | None = None
) -> tuple[bool, str]:
    """Judge whether the opening window makes clear not just that something
    is unusual (HOOK_002's job), but what the character wants and why they
    can't get it yet.

    Returns (is_legible, reasoning). Raises SemanticCheckServiceError if the
    LLM response cannot be parsed into the expected shape, or if the LLM
    provider is unavailable (e.g. missing credentials).
    """
    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_beats = "\n".join(f"{i}. {desc!r}" for i, desc in enumerate(opening_beat_descriptions))

    prompt = f"""You are reviewing the opening window of a children's short-form video for
problem legibility.

Stated opening anomaly: {anomaly!r}

Opening beat(s) action/consequence (0-indexed):
{numbered_beats}

HOOK_002 already confirms something visually unusual is happening immediately. This
check asks a stricter question: within this same opening window, is it ALSO clear
what the character wants and why they can't get it yet — not just that something
odd is occurring?

PASS example: character reaches for a cup, the cup visibly slides away from their
hand — the goal (get the cup) and the obstruction (it won't stay still) are both
immediately legible.

FAIL example: the opening only shows an odd visual event (an object behaving
strangely) with no indication yet of what the character is trying to do about it or
why it matters to them.

Respond in strict JSON format:
{{
  "is_legible": true or false,
  "reasoning": "brief explanation of your decision"
}}"""

    response = _call_llm_safely(llm, prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    required_fields = ["is_legible", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise SemanticCheckServiceError(f"LLM response missing required field: {field}")

    if not isinstance(parsed["is_legible"], bool):
        raise SemanticCheckServiceError("is_legible must be a boolean")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")

    return parsed["is_legible"], parsed["reasoning"]


def check_character_performance_readable(
    character_name: str, beat_descriptions: list[str], llm_provider: str | None = None
) -> tuple[bool, str]:
    """Judge whether the character reads as emotionally engaged, sympathetic,
    and appropriately invested in the problem throughout — not blank,
    robotic, aggressive, or stuck in prolonged panic.

    Returns (is_readable, reasoning). Raises SemanticCheckServiceError if the
    LLM response cannot be parsed into the expected shape, or if the LLM
    provider is unavailable (e.g. missing credentials).
    """
    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_beats = "\n".join(f"{i}. {desc!r}" for i, desc in enumerate(beat_descriptions))

    prompt = f"""You are reviewing a children's short-form video concept for character
performance quality.

Character: {character_name!r}

Beat-by-beat actions/consequences across the timeline (0-indexed):
{numbered_beats}

Determine whether the character reads as emotionally engaged and sympathetic
throughout — curious, determined, mildly surprised, briefly frustrated — rather than
blank/robotic, overly aggressive, or stuck in prolonged panic/distress. A character
can take the problem seriously without losing charm; a short, charming reaction after
a failed attempt is good, as long as it doesn't stall the story.

Respond in strict JSON format:
{{
  "is_readable": true or false,
  "reasoning": "brief explanation of your decision"
}}"""

    response = _call_llm_safely(llm, prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    required_fields = ["is_readable", "reasoning"]
    for field in required_fields:
        if field not in parsed:
            raise SemanticCheckServiceError(f"LLM response missing required field: {field}")

    if not isinstance(parsed["is_readable"], bool):
        raise SemanticCheckServiceError("is_readable must be a boolean")
    if not isinstance(parsed["reasoning"], str):
        raise SemanticCheckServiceError("reasoning must be a string")

    return parsed["is_readable"], parsed["reasoning"]


def check_attempts_are_generation_executable(
    attempts: list[dict[str, str]], llm_provider: str | None = None
) -> list[dict[str, Any]]:
    """Judge whether each attempt is expressed as a concrete, visually
    distinct, generation-friendly physical action an image-to-video model
    can reliably render — not merely whether the strategies are
    conceptually/semantically different (that's find_duplicate_strategy_pairs'
    job, which this complements rather than replaces).

    `attempts` is an ordered list of dicts with keys "primaryVerb", "action",
    "consequence" (the same shape ATTEMPT_002 already builds). Distinguishes:
    - a concrete action/result pair ("lowers right foot" -> "box slides right
      one box-width") from an abstract strategy description ("blocks the
      escape route", "tries to outsmart the box") that requires spatial
      reasoning or mental-state interpretation a generation model can't
      execute;
    - attempts that are conceptually different but would visually collapse
      into the same choreography when actually rendered.

    Returns a list of per-attempt judgment dicts, one per input attempt, each
    shaped:
    {
        "index": int,
        "is_executable": bool,
        "problem": str,              # "" if is_executable is True
        "suggested_rewrite": str,    # "" if is_executable is True
    }

    Raises SemanticCheckServiceError if the LLM response cannot be parsed
    into the expected shape, or if the LLM provider is unavailable (e.g.
    missing credentials). Returns [] when 0 or 1 attempts are given (nothing
    to compare for visual collapse, and a single attempt's executability is
    better judged in context of its peers) without calling the LLM at all,
    mirroring find_duplicate_strategy_pairs' handling of a too-small input.
    """
    if len(attempts) < 2:
        return []

    try:
        llm = get_provider(llm_provider)
    except ValueError as e:
        raise SemanticCheckServiceError(f"LLM provider unavailable: {e}") from e

    numbered_attempts = "\n".join(
        "{i}. intendedStrategyFamily={intended!r}, reactiveActionFamily={reactive!r}, "
        "primaryVerb={verb!r}, targetObject={target!r}, intendedEffect={effect!r}, "
        "action={action!r}, consequence={consequence!r}, result={result!r}".format(
            i=i,
            intended=a.get("intendedStrategyFamily", a.get("strategyFamily", "")),
            reactive=a.get("reactiveActionFamily", ""),
            verb=a.get("primaryVerb", ""),
            target=a.get("targetObject", ""),
            effect=a.get("intendedEffect", ""),
            action=a.get("action", ""),
            consequence=a.get("consequence", ""),
            result=a.get("result", ""),
        )
        for i, a in enumerate(attempts)
    )

    prompt = f"""You are reviewing problem-solving attempts in a children's short-form video
for GENERATION EXECUTABILITY — whether an image-to-video generation model (such as
Seedance) can reliably render each attempt as a clear, visually distinct physical
action, as opposed to the attempts merely being conceptually/strategically different
on paper.

The core question for each attempt is NOT "is this a different strategy?" (that's a
separate check). It is: "will the viewer and the generation model clearly see a
different physical action?"

Every attempt should reduce to a simple, literal ACTION -> OBJECT RESPONSE ->
CHARACTER CONSEQUENCE sequence a generation model can execute without inferring
spatial layout or mental state.

GOOD (concrete, executable): "lowers right foot toward the box" -> "box slides one
box-width to the right" -> "foot lands on the floor". The verb is a literal physical
action (step, push, pull, lift, turn, place, hold, rotate), the object's response is
an explicit visible transformation, and the consequence is visible.

BAD (abstract, not reliably executable):
- "blocks the escape route" — requires the generation model to infer which route is
  blocked and which remains open; a spatial plan, not a literal action.
- "tries to outsmart the box" — describes intention, not a physical action at all.
- "pretends not to care" / "confidently tries again" — a performance/mental-state cue,
  not a primary physical action; acceptable only as a secondary detail alongside an
  explicit physical action, never as the sole description of an attempt.

Also flag when two attempts, despite being worded as different strategies, would
likely render as visually IDENTICAL choreography — e.g. "character steps toward
object" vs. "character confidently steps toward object" vs. "character secretly
steps toward object" are visually almost indistinguishable, even though their
adjectives differ.

Attempts (0-indexed):
{numbered_attempts}

For EACH attempt (0-indexed, same order as given), judge whether it is generation-
executable. An attempt is NOT executable if it lacks a concrete physical verb, lacks
a visible action-result pair, depends on complex spatial reasoning the generation
model would have to infer, or would likely render identically to another attempt in
this list despite different wording.

Respond in strict JSON format:
{{
  "judgments": [
    {{
      "index": 0,
      "is_executable": true or false,
      "problem": "brief explanation if not executable, empty string if executable",
      "suggested_rewrite": "a literal action/result rewrite if not executable, empty string if executable"
    }},
    ...
  ]
}}

Include exactly one judgment per attempt, in the same 0-indexed order given above."""

    response = _call_llm_safely(llm, prompt)
    parsed = _parse_json_with_markdown_fallback(response)

    if "judgments" not in parsed:
        raise SemanticCheckServiceError("LLM response missing required field: judgments")
    if not isinstance(parsed["judgments"], list):
        raise SemanticCheckServiceError("judgments must be a list")
    if len(parsed["judgments"]) != len(attempts):
        raise SemanticCheckServiceError(f"Expected {len(attempts)} judgments, got {len(parsed['judgments'])}")

    judgments: list[dict[str, Any]] = []
    required_fields = ["index", "is_executable", "problem", "suggested_rewrite"]
    seen_indices: set[int] = set()
    for expected_index, entry in enumerate(parsed["judgments"]):
        if not isinstance(entry, dict):
            raise SemanticCheckServiceError(f"Malformed judgment entry: {entry!r}")
        for field in required_fields:
            if field not in entry:
                raise SemanticCheckServiceError(f"Judgment entry missing required field: {field}")
        if isinstance(entry["index"], bool) or not isinstance(entry["index"], int):
            raise SemanticCheckServiceError("judgment index must be an integer")
        if entry["index"] != expected_index or entry["index"] in seen_indices or not 0 <= entry["index"] < len(attempts):
            raise SemanticCheckServiceError("judgment indices must be unique, in order, and within the attempt list")
        seen_indices.add(entry["index"])
        if not isinstance(entry["is_executable"], bool):
            raise SemanticCheckServiceError("is_executable must be a boolean")
        if not isinstance(entry["problem"], str):
            raise SemanticCheckServiceError("problem must be a string")
        if not isinstance(entry["suggested_rewrite"], str):
            raise SemanticCheckServiceError("suggested_rewrite must be a string")
        judgments.append(
            {
                "index": entry["index"],
                "is_executable": entry["is_executable"],
                "problem": entry["problem"],
                "suggested_rewrite": entry["suggested_rewrite"],
            }
        )

    return judgments
