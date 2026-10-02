"""
Auto-fix iteration loop against the canonical quality contract (Slice A Task 5).

The loop consumes typed :class:`PriorityFix` objects. A ``REPLACE_CONCEPT``
fix (e.g. CONCEPT_006) is *rejected* by the patch-based fixer rather than
patched — building the new-concept generator is Slice C Task 4. The loop must
degrade gracefully: never regress the score, and surface why it could not fix.
"""

from pathlib import Path

from app.autofix.iteration_loop import AutoFixIterationLoop
from app.autofix.prompt_fixer import PromptFixer
from app.config import settings
from app.quality.contracts import FixStrategy, PriorityFix, Severity


def load_test_case(filename: str) -> str:
    return (Path(settings.test_cases_dir) / filename).read_text(encoding="utf-8")


def _priority_fix(rule_id: str, strategy: FixStrategy) -> PriorityFix:
    return PriorityFix(
        priority=1,
        rule_id=rule_id,
        rule_name=rule_id.replace("_", " ").title(),
        family="concept_strength",
        severity=Severity.BLOCKER,
        issue="synthetic",
        recommendation="synthetic",
        impact="synthetic",
        strategy=strategy,
    )


def test_apply_fix_rejects_replace_concept() -> None:
    fixer = PromptFixer()
    prompt = "## Timeline\n0.0-3.0 SEC: hero does something\n"
    result = fixer.apply_fix(prompt, _priority_fix("CONCEPT_006", FixStrategy.REPLACE_CONCEPT))

    assert result.success is False
    # The prompt is returned unmodified; no misleading "fix" is applied.
    assert result.modified_prompt == prompt
    assert any("REPLACE_CONCEPT" in w or "concept" in w.lower() for w in result.warnings)


def test_apply_fix_rejects_human_review() -> None:
    fixer = PromptFixer()
    prompt = "## Timeline\n0.0-3.0 SEC: hero does something\n"
    result = fixer.apply_fix(prompt, _priority_fix("PRODUCIBILITY_001", FixStrategy.HUMAN_REVIEW))
    assert result.success is False


def test_autofix_fail_001_degrades_gracefully() -> None:
    prompt = load_test_case("FAIL_001_KIKO_STATIC_STATE_DOMINANCE.md")
    loop = AutoFixIterationLoop(ruleset_version="1.0", max_iterations=3)
    result = loop.run(prompt)

    # Top fix is CONCEPT_006 (REPLACE_CONCEPT) -> rejected, not patched.
    assert result.iteration_count == 0
    assert not result.applied_fixes
    # No regression: the score and status are preserved.
    assert result.final_score == result.initial_score
    assert result.final_status == result.initial_status
    # The loop explains that the concept, not the prompt text, must change.
    assert any("CONCEPT_006" in w for w in result.warnings)


def test_autofix_never_regresses_score() -> None:
    prompt = load_test_case("FAIL_002_OPA_REPETITIVE_OPEN_CLOSE.md")
    loop = AutoFixIterationLoop(ruleset_version="1.0", max_iterations=3)
    result = loop.run(prompt)
    assert result.final_score >= result.initial_score


class TestNewRuleFixStrategies:
    """ATTEMPT_001, ATTEMPT_002, CHAR_002, MOTION_001, PRODUCIBILITY_002 all
    require creative judgment the deterministic fixer cannot safely invent —
    each must decline with success=False and an actionable diagnostic rather
    than fabricating story content."""

    def _priority_fix(self, rule_id: str, recommendation: str = "") -> PriorityFix:
        from app.quality.contracts import Severity, strategy_for_rule

        return PriorityFix(
            priority=1,
            rule_id=rule_id,
            rule_name=rule_id,
            family="concept_strength",
            severity=Severity.CRITICAL,
            issue="test issue",
            recommendation=recommendation,
            impact="test impact",
            strategy=strategy_for_rule(rule_id),
        )

    def test_attempt_001_declines_with_diagnostic(self) -> None:
        fixer = PromptFixer()
        fix = self._priority_fix("ATTEMPT_001")
        result = fixer.apply_fix(
            "some prompt text", fix, video_plan_ir={"beats": [], "metadata": {"duration": 15.0}}
        )
        assert result.success is False
        assert result.rule_id == "ATTEMPT_001"
        assert len(result.warnings) > 0
        assert "no fix strategy for" not in result.fix_description.lower()

    def test_attempt_002_declines_with_diagnostic(self) -> None:
        fixer = PromptFixer()
        fix = self._priority_fix("ATTEMPT_002")
        result = fixer.apply_fix(
            "some prompt text", fix, video_plan_ir={"beats": [], "metadata": {"duration": 15.0}}
        )
        assert result.success is False
        assert result.rule_id == "ATTEMPT_002"
        assert "no fix strategy for" not in result.fix_description.lower()

    def test_char_002_declines_with_diagnostic(self) -> None:
        fixer = PromptFixer()
        fix = self._priority_fix("CHAR_002")
        result = fixer.apply_fix(
            "some prompt text", fix, video_plan_ir={"beats": [], "metadata": {"duration": 15.0}}
        )
        assert result.success is False
        assert result.rule_id == "CHAR_002"
        assert "no fix strategy for" not in result.fix_description.lower()

    def test_motion_001_declines_with_diagnostic(self) -> None:
        fixer = PromptFixer()
        fix = self._priority_fix("MOTION_001")
        result = fixer.apply_fix(
            "some prompt text", fix, video_plan_ir={"beats": [], "metadata": {"duration": 15.0}}
        )
        assert result.success is False
        assert result.rule_id == "MOTION_001"
        assert "no fix strategy for" not in result.fix_description.lower()

    def test_producibility_002_declines_with_diagnostic(self) -> None:
        fixer = PromptFixer()
        fix = self._priority_fix("PRODUCIBILITY_002")
        result = fixer.apply_fix(
            "some prompt text",
            fix,
            video_plan_ir={"setting": {"mainProps": []}, "metadata": {"duration": 15.0}},
        )
        assert result.success is False
        assert result.rule_id == "PRODUCIBILITY_002"
        assert "no fix strategy for" not in result.fix_description.lower()
