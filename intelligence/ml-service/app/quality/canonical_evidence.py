"""Single read path for canonical beat/attempt evidence and evidence-gap classification.

The parser decides, once, which beats are attempts (``isAttempt``/``primaryVerb``/
``attemptSource``). Every downstream consumer -- attempt rules, the character-activity
rule, the pre-render assessment and the UI -- must read that decision through this
module instead of re-deriving it. This is an accessor, not an engine: it holds no
policy and no thresholds.

It also owns the one definition of an *evidence gap*, so creative assessment ("is the
plan good?") can be reported separately from evidence completeness ("do we know enough
to judge it?").
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .contracts import RuleEvaluation, RuleOutcome

UNSPECIFIED_VERB = "UNSPECIFIED"

# Set by rules that fail closed because the evidence they need is absent, not because
# the creative plan was judged weak (for example the two visual render-blocking gates).
EVIDENCE_INCOMPLETE_FAILURE = "EVIDENCE_INCOMPLETE"


@dataclass(frozen=True)
class AttemptEvidence:
    """Canonical attempt facts derived from ``beats[].isAttempt``."""

    count: int
    beat_ids: tuple[str, ...]
    verbs: tuple[str, ...]
    active_seconds: float
    active_ratio: float
    sources: dict[str, int]


def is_unspecified_verb(verb: object) -> bool:
    """True when a beat is an attempt but no action verb could be identified."""

    text = str(verb or "").strip().upper()
    return text in {"", UNSPECIFIED_VERB}


def attempt_beats(video_plan_ir: dict[str, Any]) -> list[dict[str, Any]]:
    """Beats the parser marked as active attempts, in timeline order."""

    return [beat for beat in video_plan_ir.get("beats", []) if beat.get("isAttempt", False)]


def attempt_evidence(video_plan_ir: dict[str, Any]) -> AttemptEvidence:
    """Summarise the canonical attempts (count, verbs, active time and provenance)."""

    attempts = attempt_beats(video_plan_ir)
    duration = video_plan_ir.get("metadata", {}).get("duration", 15.0)
    active_seconds = float(sum(beat.get("duration", 0.0) for beat in attempts))
    sources = Counter(str(beat.get("attemptSource") or "UNKNOWN") for beat in attempts)
    return AttemptEvidence(
        count=len(attempts),
        beat_ids=tuple(str(beat.get("id", "")) for beat in attempts),
        verbs=tuple(str(beat.get("primaryVerb", "")).strip().upper() for beat in attempts),
        active_seconds=active_seconds,
        active_ratio=active_seconds / duration if duration > 0 else 0.0,
        sources=dict(sources),
    )


def is_evidence_gap(evaluation: RuleEvaluation) -> bool:
    """True when the outcome reflects missing evidence rather than a creative judgment."""

    if evaluation.outcome in (RuleOutcome.UNKNOWN, RuleOutcome.SERVICE_ERROR):
        return True
    return (
        evaluation.outcome is RuleOutcome.FAIL
        and evaluation.details.get("failureBasis") == EVIDENCE_INCOMPLETE_FAILURE
    )


def evidence_gap_kind(evaluation: RuleEvaluation) -> str:
    if evaluation.outcome is RuleOutcome.UNKNOWN:
        return "UNKNOWN"
    if evaluation.outcome is RuleOutcome.SERVICE_ERROR:
        return "SERVICE_ERROR"
    return "EVIDENCE_INCOMPLETE_FAIL"


def unscored_families(evaluations: Iterable[RuleEvaluation]) -> tuple[str, ...]:
    """Families with no rule that produced a scoring signal (PASS, FAIL or SERVICE_ERROR).

    The rule engine reports such a family as ``0`` (a fail-closed placeholder). That
    number is not a creative result and must not be presented as one.
    """

    scoring = {RuleOutcome.PASS, RuleOutcome.FAIL, RuleOutcome.SERVICE_ERROR}
    families: dict[str, bool] = {}
    for evaluation in evaluations:
        families[evaluation.family] = families.get(evaluation.family, False) or evaluation.outcome in scoring
    return tuple(family for family, has_signal in families.items() if not has_signal)
