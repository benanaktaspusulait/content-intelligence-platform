from __future__ import annotations

import signal
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator
from unittest.mock import patch

from ..api.quality import convert_quality_report
from ..assessment.pre_render_assessment import build_pre_render_assessment
from ..parser.prompt_parser import parse_prompt
from ..quality.canonical_evidence import (
    attempt_evidence,
    beat_audit,
    escalation_evidence,
    specialized_applicability_evidence,
    story_density_evidence,
)
from ..quality.contracts import EnhancedQualityReport, ParseResult, QualityReport
from ..rules import rule_engine as rule_engine_module
from ..rules.rule_engine import RuleEngine
from ..scoring.quality_scorer import QualityScorer
from .provenance import GoldenFingerprint, build_golden_fingerprint


class GoldenAnalysisTimeout(TimeoutError):
    """Raised when a frozen prompt exceeds the bounded parser/evaluation window."""


@dataclass
class GoldenRun:
    golden_id: str
    prompt_text: str
    prompt_hash: str
    engine_input: dict[str, str]
    provider_mode: str
    fingerprint: GoldenFingerprint
    status: str
    parse_result: ParseResult | None = None
    report: QualityReport | None = None
    enhanced_report: EnhancedQualityReport | None = None
    assessment: dict[str, Any] | None = None
    api_report: dict[str, Any] | None = None
    known_issues: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goldenId": self.golden_id,
            "promptHash": self.prompt_hash,
            "engineInput": self.engine_input,
            "providerMode": self.provider_mode,
            "fingerprint": self.fingerprint.to_dict(),
            "status": self.status,
            "knownIssues": self.known_issues,
            "error": self.error,
            "parserMetadata": None
            if self.parse_result is None
            else {
                "confidence": self.parse_result.metadata.confidence,
                "ambiguities": list(self.parse_result.metadata.ambiguities),
                "assumptions": list(self.parse_result.metadata.assumptions),
                "warnings": list(self.parse_result.metadata.warnings),
                "evidenceMissing": list(self.parse_result.metadata.evidence_missing),
            },
            "videoPlanIR": None if self.parse_result is None else self.parse_result.video_plan_ir,
            "canonicalEvidence": None if self.parse_result is None else self._canonical_evidence(),
            "report": None if self.report is None else _report_dict(self.report),
            "assessment": self.assessment,
            "apiReport": self.api_report,
        }

    def _canonical_evidence(self) -> dict[str, Any]:
        assert self.parse_result is not None
        ir = self.parse_result.video_plan_ir
        attempts = attempt_evidence(ir)
        story = story_density_evidence(ir)
        escalation = escalation_evidence(ir)
        specialized_applicability = specialized_applicability_evidence(ir)
        return {
            "attempts": {
                "count": attempts.count,
                "beatIds": list(attempts.beat_ids),
                "verbs": list(attempts.verbs),
                "strategyFamilies": list(attempts.strategy_families),
                "activeSeconds": attempts.active_seconds,
                "activeRatio": attempts.active_ratio,
                "canonicalConfidence": attempts.canonical_confidence,
                "attempts": list(attempts.attempts),
            },
            "escalation": escalation.to_dict(),
            "storyDensity": story.__dict__,
            "specializedApplicability": {
                rule_id: evidence.to_dict()
                for rule_id, evidence in specialized_applicability.items()
            },
            "beatAudit": beat_audit(ir),
        }


def _report_dict(report: QualityReport) -> dict[str, Any]:
    return {
        "overallScore": report.overall_score,
        "status": report.status.value,
        "rulesetVersion": report.ruleset_version,
        "familyScores": report.family_scores,
        "familyAssessments": report.family_assessments,
        "evaluations": [
            {
                "ruleId": item.rule_id,
                "outcome": item.outcome.value,
                "severity": item.configured_severity.value,
                "family": item.family,
                "actualValue": item.actual_value,
                "requiredValue": item.required_value,
                "thresholdValue": item.threshold_value,
                "message": item.message,
                "details": item.details,
            }
            for item in report.evaluations
        ],
    }


def _alarm_handler(signum: int, frame: Any) -> None:
    raise GoldenAnalysisTimeout("deterministic Golden analysis exceeded its timeout")


def _bounded_call(function: Callable[[], Any], timeout_seconds: int) -> Any:
    previous = signal.getsignal(signal.SIGALRM)
    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return function()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _frozen_parse_result(parsed: ParseResult) -> ParseResult:
    ir = dict(parsed.video_plan_ir)
    metadata = dict(ir.get("metadata") or {})
    metadata["createdAt"] = "GOLDEN_DETERMINISTIC"
    ir["metadata"] = metadata
    return ParseResult(video_plan_ir=ir, metadata=parsed.metadata)


def _semantic_attempt_judgments(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "is_executable": True,
            "problem": "",
            "suggested_rewrite": "",
        }
        for index, _ in enumerate(attempts)
    ]


@contextmanager
def _frozen_semantic_mode(ir: dict[str, Any]) -> Iterator[None]:
    characters = ir.get("characters") or {}
    primary = str(characters.get("primary") or "Unknown")
    core = ir.get("coreMechanic") or {}
    object_name = str(core.get("primaryObject") or "object")
    with ExitStack() as stack:
        stack.enter_context(patch.object(rule_engine_module, "find_duplicate_strategy_pairs", return_value=[]))
        stack.enter_context(patch.object(rule_engine_module, "check_goal_is_natural", return_value=(True, "FROZEN_DETERMINISTIC")))
        stack.enter_context(patch.object(rule_engine_module, "check_rule_is_predictable", return_value=(True, "FROZEN_DETERMINISTIC")))
        stack.enter_context(
            patch.object(
                rule_engine_module,
                "check_single_agent_object_mechanic",
                return_value=(
                    {
                        "primary_agent": primary,
                        "primary_object": object_name,
                        "mechanic_carrier": "OBJECT_INTERACTION",
                        "causal_participants": [primary],
                        "reasoning": "FROZEN_DETERMINISTIC",
                    },
                    "PASS",
                ),
            )
        )
        stack.enter_context(patch.object(rule_engine_module, "check_twist_matches_rule", return_value=(True, "FROZEN_DETERMINISTIC")))
        stack.enter_context(patch.object(rule_engine_module, "check_opening_problem_legible", return_value=(True, "FROZEN_DETERMINISTIC")))
        stack.enter_context(patch.object(rule_engine_module, "check_character_performance_readable", return_value=(True, "FROZEN_DETERMINISTIC")))
        stack.enter_context(patch.object(rule_engine_module, "count_independent_mechanics", return_value=(1, "FROZEN_DETERMINISTIC")))
        stack.enter_context(
            patch.object(
                rule_engine_module,
                "check_attempts_are_generation_executable",
                side_effect=lambda attempts: _semantic_attempt_judgments(attempts),
            )
        )
        yield


def run_golden_asset(
    asset: dict[str, Any],
    *,
    manifest_path: str | Path,
    ruleset_path: str | Path,
    parse_timeout_seconds: int = 12,
) -> GoldenRun:
    manifest = Path(manifest_path)
    prompt_path = manifest.parent / str(asset["promptFile"])
    prompt_text = prompt_path.read_text(encoding="utf-8")
    fingerprint = build_golden_fingerprint(asset, ruleset_path=ruleset_path)
    engine_input = {"prompt": prompt_text}
    base = dict(
        golden_id=str(asset["goldenId"]),
        prompt_text=prompt_text,
        prompt_hash=str(asset["promptHash"]),
        engine_input=engine_input,
        provider_mode="FROZEN_DETERMINISTIC",
        fingerprint=fingerprint,
    )
    try:
        parsed = _bounded_call(lambda: parse_prompt(prompt_text), parse_timeout_seconds)
    except GoldenAnalysisTimeout as error:
        return GoldenRun(
            **base,
            status="PARSER_TIMEOUT",
            known_issues=[{"code": "PARSER_DISCOVERY_TIMEOUT", "message": str(error)}],
            error=str(error),
        )
    parsed = _frozen_parse_result(parsed)
    try:
        with _frozen_semantic_mode(parsed.video_plan_ir):
            engine = RuleEngine(str(ruleset_path))
            report = engine.evaluate(parsed.video_plan_ir)
            enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)
        assessment = build_pre_render_assessment(parsed.video_plan_ir, parsed.metadata, report, report.ruleset_version)
        api_report = convert_quality_report(
            enhanced,
            report.ruleset_version,
            video_plan_ir=parsed.video_plan_ir,
        ).model_dump(mode="json")
    except Exception as error:
        return GoldenRun(
            **base,
            status="ANALYSIS_ERROR",
            parse_result=parsed,
            known_issues=[{"code": "DETERMINISTIC_RUN_ERROR", "message": str(error)}],
            error=f"{type(error).__name__}: {error}",
        )
    return GoldenRun(
        **base,
        status="OK",
        parse_result=parsed,
        report=report,
        enhanced_report=enhanced,
        assessment=assessment,
        api_report=api_report,
    )
