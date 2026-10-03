# Plan A: Python Outcome Model + API Contract Completion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the full 5-state `RuleOutcome` (PASS/FAIL/UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR) visible end-to-end from the Python rule engine through the FastAPI HTTP response and the Spring DTOs that consume it, stop the free-text parser from manufacturing unverified positive evidence for HOOK_002/HOOK_003/CONSISTENCY_001, and normalize every LLM provider runtime failure into one typed error.

**Architecture:** `app/quality/contracts.py` already defines the correct 5-state `RuleOutcome` enum and `QualityReport.unknown_rules`/`not_applicable_rules`/`service_errors` accessors — this plan does not touch that file's enum/dataclass shapes. The gap is downstream: `app/api/quality.py`'s `QualityReportResponse` only carries `failed_rules` (a `bool`-collapsed `RuleEvaluationResponse`), the parser invents evidence instead of marking it missing, and `app/llm/semantic_checks.py` only converts the LLM-provider-construction `ValueError` to `SemanticCheckServiceError`, not the actual `llm.complete()` call's runtime failures. This plan edits the response models, the parser's four specific optimistic defaults, the semantic-check error wrapping, and the Spring-side DTOs that mirror the Python response shape — in that dependency order, each with its own tests, so every task leaves the suite green.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, pytest; Java 21, Spring Boot, Jackson records.

## Global Constraints

- Never convert `UNKNOWN`, `NOT_APPLICABLE`, or `SERVICE_ERROR` into `FAIL` or `PASS` anywhere in this plan — not in Python, not in the Spring DTO mapping.
- `SERVICE_ERROR` is an operational state, not a rule failure — it must never increment `blocker_count`/`critical_count` as if it were a `FAIL`. (It already fails closed to `BLOCKER` severity via `RuleEvaluation.effective_severity`, which is correct and must not change — that's about overall-status gating, not about pretending it is a `FAIL` outcome.)
- Do not touch `intelligence/data/rules/RULESET_1.3.yaml` in this plan — no rule semantics change here, only how outcomes are reported and how the parser produces evidence.
- Do not implement render-authorization evidence population (Spring `semanticProvider`/`independentRevalidationId` etc.) — that is Plan C. Do not implement rule evaluation-stage metadata (PRE_RENDER/POST_RENDER) — that is Plan D. Do not touch `FAMILY_WEIGHTS`/family-radar family lists — that is Plan E. Do not touch LLM provider `image` parameter handling — that is Plan B. Do not touch Angular — that is Plan F.
- Every task must leave `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q` fully green (zero failures) before moving to the next task, and `ruff check . && ruff format --check . && mypy --strict app` clean.
- Work directly on `master`. No worktree, no feature branch. Commit after each task.

---

### Task 1: Add `UNKNOWN`/`NOT_APPLICABLE`/`SERVICE_ERROR` rule lists to the HTTP response model

**Files:**
- Modify: `intelligence/ml-service/app/api/quality.py`
- Test: `intelligence/ml-service/tests/test_api_conversions.py`

**Interfaces:**
- Consumes: `app.quality.contracts.QualityReport.unknown_rules`, `.not_applicable_rules`, `.service_errors` (all `tuple[RuleEvaluation, ...]`, already implemented and tested in `tests/test_contracts_not_applicable.py` — do not modify `contracts.py` in this task).
- Produces: `RuleEvaluationResponse` gains a `str` `outcome` field (values: `"PASS"`, `"FAIL"`, `"UNKNOWN"`, `"NOT_APPLICABLE"`, `"SERVICE_ERROR"`) and drops the collapsed `result: bool` field. `QualityReportResponse` gains `unknown_rules: list[RuleEvaluationResponse]`, `not_applicable_rules: list[RuleEvaluationResponse]`, `service_errors: list[RuleEvaluationResponse]`.

This task touches a field that existing tests assert on (`result is False`) — those tests are fixed in this same task, not left broken.

- [ ] **Step 1: Write the failing test for the new response fields**

Read `intelligence/ml-service/tests/test_api_conversions.py` first (it already exists; you are appending to it, not replacing it). Add this test at the end of the file:

```python
def test_convert_quality_report_exposes_outcome_not_bool_result() -> None:
    parsed = parse_prompt(STATIC_PROMPT)
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    # Every failed rule now carries its explicit outcome string, not a
    # collapsed boolean that can't distinguish FAIL from UNKNOWN/SERVICE_ERROR.
    for fr in response.failed_rules:
        assert fr.outcome == "FAIL"
        assert not hasattr(fr, "result")


def test_convert_quality_report_separates_unknown_not_applicable_service_error() -> None:
    from app.quality.contracts import (
        EnhancedQualityReport,
        ParserMetadata,
        QualityReport,
        QualityStatus,
        RuleEvaluation,
        RuleOutcome,
        ScoreBreakdown,
        Severity,
    )

    base_report = QualityReport(
        overall_score=70.0,
        status=QualityStatus.NEEDS_REVISION,
        family_scores={"progression": 70.0},
        evaluations=(
            RuleEvaluation(
                rule_id="PAYOFF_005",
                rule_name="Fake Win Escalation",
                family="progression",
                outcome=RuleOutcome.NOT_APPLICABLE,
                configured_severity=Severity.WARNING,
                message="No fake-win beat present.",
            ),
            RuleEvaluation(
                rule_id="CONSISTENCY_002",
                rule_name="Character Continuity Lock",
                family="consistency",
                outcome=RuleOutcome.UNKNOWN,
                configured_severity=Severity.CRITICAL,
                message="No rendered video available yet.",
            ),
            RuleEvaluation(
                rule_id="GOAL_001",
                rule_name="Goal-Obstruction Clarity",
                family="concept_strength",
                outcome=RuleOutcome.SERVICE_ERROR,
                configured_severity=Severity.BLOCKER,
                message="LLM provider unavailable: OPENAI_API_KEY not set",
            ),
        ),
        ruleset_version="1.3",
        evaluated_at="2026-10-03T00:00:00Z",
    )
    enhanced = EnhancedQualityReport(
        base_report=base_report,
        score_breakdowns=(
            ScoreBreakdown(
                family="progression",
                score=70.0,
                weight=0.11,
                weighted_contribution=7.7,
                rules_passed=0,
                rules_failed=0,
                rules_warning=0,
            ),
        ),
        score_card={"score": 70.0, "label": "Acceptable", "color": "yellow", "status": "NEEDS_REVISION",
                    "blockers": 0, "criticals": 0, "warnings": 0, "passes": 0, "is_render_ready": False},
        timeline_data={"duration": 15.0, "beats": [], "consequence_markers": [], "state_segments": []},
        family_radar={"labels": [], "scores": [], "thresholds": {}},
        top_3_strengths=(),
        top_3_weaknesses=(),
        priority_fixes=(),
        parser_metadata=ParserMetadata(confidence=1.0),
    )

    response = convert_quality_report(enhanced, "1.3")

    assert len(response.unknown_rules) == 1
    assert response.unknown_rules[0].rule_id == "CONSISTENCY_002"
    assert response.unknown_rules[0].outcome == "UNKNOWN"

    assert len(response.not_applicable_rules) == 1
    assert response.not_applicable_rules[0].rule_id == "PAYOFF_005"
    assert response.not_applicable_rules[0].outcome == "NOT_APPLICABLE"

    assert len(response.service_errors) == 1
    assert response.service_errors[0].rule_id == "GOAL_001"
    assert response.service_errors[0].outcome == "SERVICE_ERROR"

    # None of these three leak into failed_rules (which stays FAIL-only).
    failed_ids = {fr.rule_id for fr in response.failed_rules}
    assert failed_ids.isdisjoint({"PAYOFF_005", "CONSISTENCY_002", "GOAL_001"})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py -k "outcome_not_bool or unknown_not_applicable_service_error" -v`

Expected: both FAIL. The first fails with `AttributeError: 'RuleEvaluationResponse' object has no attribute 'outcome'` (it currently has `result`). The second fails with `AttributeError: 'QualityReportResponse' object has no attribute 'unknown_rules'`.

- [ ] **Step 3: Also run the existing test that currently asserts the old `result` field, confirm it fails for the same reason it's about to be fixed**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py::test_convert_quality_report_uses_base_report_and_typed_fixes -v`

Expected: currently PASSES (it asserts `fr.result is False`, which is still true pre-change). You will update this test's assertion in Step 5 below once `result` is removed, since otherwise it would start failing for the wrong reason (attribute no longer exists) rather than being a meaningful check.

- [ ] **Step 4: Update `RuleEvaluationResponse` and `QualityReportResponse` in `app/api/quality.py`**

Read the full current `RuleEvaluationResponse` and `QualityReportResponse` definitions first (they are near the top of the file, right after the request models). Replace:

```python
class RuleEvaluationResponse(BaseModel):
    rule_id: str
    rule_name: str
    family: str
    severity: str
    result: bool
    message: str
    actual_value: float | None
    threshold_value: float | None
```

with:

```python
class RuleEvaluationResponse(BaseModel):
    rule_id: str
    rule_name: str
    family: str
    severity: str
    outcome: str
    message: str
    actual_value: float | None
    threshold_value: float | None
```

Replace:

```python
class QualityReportResponse(BaseModel):
    overall_score: float
    status: str
    ruleset_version: str
    blocker_count: int
    critical_count: int
    warning_count: int
    family_scores: dict[str, float]
    failed_rules: list[RuleEvaluationResponse]
    priority_fixes: list[PriorityFixResponse]
    score_card: ScoreCardResponse
    timeline_data: TimelineDataResponse
```

with:

```python
class QualityReportResponse(BaseModel):
    overall_score: float
    status: str
    ruleset_version: str
    blocker_count: int
    critical_count: int
    warning_count: int
    family_scores: dict[str, float]
    failed_rules: list[RuleEvaluationResponse]
    unknown_rules: list[RuleEvaluationResponse]
    not_applicable_rules: list[RuleEvaluationResponse]
    service_errors: list[RuleEvaluationResponse]
    priority_fixes: list[PriorityFixResponse]
    score_card: ScoreCardResponse
    timeline_data: TimelineDataResponse
```

- [ ] **Step 5: Update `convert_quality_report` to populate the three new lists and the `outcome` field**

Find `convert_quality_report` (currently builds `failed_rules` from `report.failed_rules`). Replace the `failed_rules` construction block:

```python
    failed_rules = [
        RuleEvaluationResponse(
            rule_id=ev.rule_id,
            rule_name=ev.rule_name,
            family=ev.family,
            severity=ev.configured_severity.value,
            result=(ev.outcome is RuleOutcome.PASS),
            message=ev.message,
            actual_value=_as_optional_float(ev.actual_value),
            threshold_value=_as_optional_float(ev.threshold_value),
        )
        for ev in report.failed_rules
    ]
```

with a shared helper plus four list comprehensions:

```python
    def _to_rule_evaluation_response(ev: Any) -> RuleEvaluationResponse:
        return RuleEvaluationResponse(
            rule_id=ev.rule_id,
            rule_name=ev.rule_name,
            family=ev.family,
            severity=ev.configured_severity.value,
            outcome=ev.outcome.value,
            message=ev.message,
            actual_value=_as_optional_float(ev.actual_value),
            threshold_value=_as_optional_float(ev.threshold_value),
        )

    failed_rules = [_to_rule_evaluation_response(ev) for ev in report.failed_rules]
    unknown_rules = [_to_rule_evaluation_response(ev) for ev in report.unknown_rules]
    not_applicable_rules = [_to_rule_evaluation_response(ev) for ev in report.not_applicable_rules]
    service_errors = [_to_rule_evaluation_response(ev) for ev in report.service_errors]
```

Note: `_to_rule_evaluation_response` is a nested function defined inside `convert_quality_report`, not a module-level function — keep it local since it closes over nothing but is only meaningful in this conversion context. Find where `QualityReportResponse(...)` is constructed later in the same function and add the three new fields:

```python
    return QualityReportResponse(
        overall_score=enhanced.overall_score,
        status=enhanced.status.value,
        ruleset_version=ruleset_version,
        blocker_count=report.blocker_count,
        critical_count=report.critical_count,
        warning_count=report.warning_count,
        family_scores=report.family_scores,
        failed_rules=failed_rules,
        unknown_rules=unknown_rules,
        not_applicable_rules=not_applicable_rules,
        service_errors=service_errors,
        priority_fixes=priority_fixes,
        score_card=score_card,
        timeline_data=timeline_data,
    )
```

(Read the actual current end of `convert_quality_report` before editing — match whatever variable names it already uses for `score_card`/`timeline_data`/`priority_fixes`; do not rename those, only add the three new fields to the constructor call.)

- [ ] **Step 6: Fix the pre-existing test that asserted the removed `result` field**

In `tests/test_api_conversions.py`, change:

```python
    # Failed rules are rendered with an explicit boolean result == False.
    assert all(fr.result is False for fr in response.failed_rules)
```

to:

```python
    # Failed rules are rendered with their explicit FAIL outcome, never a
    # collapsed boolean that can't distinguish FAIL from UNKNOWN/SERVICE_ERROR.
    assert all(fr.outcome == "FAIL" for fr in response.failed_rules)
```

- [ ] **Step 7: Run the full test file to verify everything passes**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py -v`

Expected: all tests PASS, including the two new ones and the fixed one.

- [ ] **Step 8: Run the full suite + lint/type checks**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: full suite green, no lint/type errors. If `mypy --strict` complains about the nested function's return type, add an explicit `-> RuleEvaluationResponse` return annotation (already shown above) — that should be sufficient.

- [ ] **Step 9: Commit**

```bash
git add intelligence/ml-service/app/api/quality.py intelligence/ml-service/tests/test_api_conversions.py
git commit -m "feat(intelligence): expose UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR rules in quality API response"
```

---

### Task 2: Expose the remaining Phase 13 enhanced-report fields on the API response

**Files:**
- Modify: `intelligence/ml-service/app/api/quality.py`
- Test: `intelligence/ml-service/tests/test_api_conversions.py`

**Interfaces:**
- Consumes: `EnhancedQualityReport.parser_metadata` (a `ParserMetadata` with `.confidence: float`, `.ambiguities: tuple[str, ...]`, `.assumptions: tuple[str, ...]`, `.warnings: tuple[str, ...]`), `.top_3_strengths: tuple[str, ...]`, `.top_3_weaknesses: tuple[str, ...]`.
- Produces: `QualityReportResponse` gains `parser_confidence: float`, `parser_warnings: list[str]`, `parser_assumptions: list[str]`, `top_strengths: list[str]`, `top_weaknesses: list[str]`. This task does NOT add `provenance`/`authorizationEligible`/`authorizationFailureReasons` — those require Plan C's evidence model to exist first and are added there, not here (adding them now with made-up values would itself be a fabricated-evidence violation of the project's core principle).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_api_conversions.py`:

```python
def test_convert_quality_report_exposes_parser_metadata_and_strengths_weaknesses() -> None:
    parsed = parse_prompt(STATIC_PROMPT)
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    assert response.parser_confidence == parsed.metadata.confidence
    assert response.parser_warnings == list(parsed.metadata.warnings)
    assert response.parser_assumptions == list(parsed.metadata.assumptions)
    assert response.top_strengths == list(enhanced.top_3_strengths)
    assert response.top_weaknesses == list(enhanced.top_3_weaknesses)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py::test_convert_quality_report_exposes_parser_metadata_and_strengths_weaknesses -v`

Expected: FAIL with `AttributeError: 'QualityReportResponse' object has no attribute 'parser_confidence'`.

- [ ] **Step 3: Add the five fields to `QualityReportResponse`**

Add after `service_errors` (from Task 1) and before `priority_fixes`:

```python
    parser_confidence: float
    parser_warnings: list[str]
    parser_assumptions: list[str]
    top_strengths: list[str]
    top_weaknesses: list[str]
```

- [ ] **Step 4: Populate them in `convert_quality_report`**

Add to the `QualityReportResponse(...)` constructor call (alongside the fields from Task 1):

```python
        parser_confidence=enhanced.parser_metadata.confidence,
        parser_warnings=list(enhanced.parser_metadata.warnings),
        parser_assumptions=list(enhanced.parser_metadata.assumptions),
        top_strengths=list(enhanced.top_3_strengths),
        top_weaknesses=list(enhanced.top_3_weaknesses),
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py -v`

Expected: all PASS.

- [ ] **Step 6: Run the full suite + lint/type checks**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add intelligence/ml-service/app/api/quality.py intelligence/ml-service/tests/test_api_conversions.py
git commit -m "feat(intelligence): expose parser confidence/warnings/assumptions and top strengths/weaknesses in quality API response"
```

---

### Task 3: Stop the parser from inventing unverified positive hook/consistency evidence

**Files:**
- Modify: `intelligence/ml-service/app/parser/prompt_parser.py`
- Test: `intelligence/ml-service/tests/test_parser_contract.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_identify_hook` returns a dict where `visualStrength`/`soundOffClear` are `None` (not fabricated `4`/`True`) when the prompt gives no actual evidence; `_extract_core_mechanic` returns `consistency=None` (not fabricated `"consistent"`) when no explicit rule-consistency statement is found. `hook.startsAt` already correctly defaults to `0.0` **only in the sense that `0.0` is the correct neutral default for the HOOK_002 tolerance window added in RULESET 1.3** — that field is NOT touched by this task; it was never the bug audit flagged for `startsAt`, since `HOOK_002`'s check (`starts_at > 0.8`) is already a real threshold HOOK_002 computes against, not a trusted-but-unverified claim like `visualStrength`/`soundOffClear`/`consistency` are. Likewise `coreMechanic.mechanicCount` and `beats[].relatesToCoreProblem` are explicitly OUT OF SCOPE for this task — see the "Why these four and not those" note below.

**Why these four fields and not `mechanicCount`/`relatesToCoreProblem`/`loopsToOpening`:** `mechanicCount=1` is never trusted at face value — `CONCEPT_007` always re-derives the real count via an LLM semantic check and ignores the author's claim except for a discrepancy note (see `rule_engine.py`'s `_evaluate_concept_007` docstring: "coreMechanic.mechanicCount is an author claim, verified (not trusted)"). Likewise `relatesToCoreProblem=True` is the documented backward-compatible default for pre-1.2 IRs and `BEAT_005` only flags it when an explicit `[DETACHED]` marker says otherwise — there is no silent-PASS risk because no rule treats the *absence* of evidence as proof of correctness; the rule only fires on affirmative contrary evidence. In sharp contrast, `HOOK_002` directly thresholds against the raw `visualStrength`/`soundOffClear` values with no semantic re-verification (`if visual_strength < 4`, `if not sound_off_clear`) — the parser's optimistic defaults of exactly `4` and `True` sit exactly on/past the passing threshold, so a parser that found zero real evidence manufactures a guaranteed PASS. Same for `CONSISTENCY_001`'s raw `consistency == "breaking"` check against a defaulted `"consistent"`. These two rules have no safety net; the other three do. Do not change the mechanicCount/relatesToCoreProblem/loopsToOpening defaults in this task — they are correct as-is and already covered by passing tests in `test_parser_contract.py` that must keep passing unmodified.

- [ ] **Step 1: Write the failing tests**

Read `intelligence/ml-service/tests/test_parser_contract.py` in full first (you are appending, and you need the existing `SAMPLE_PROMPT` style). Append:

```python
def test_hook_fields_are_none_when_no_explicit_evidence() -> None:
    """A prompt with no HOOK: section and no visual-strength/sound-off
    language must not fabricate a passing visualStrength=4/soundOffClear=True
    — those become None (evidence missing), not an invented pass."""
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    result = parse_prompt(prompt)
    ir = result.video_plan_ir
    assert ir["hook"]["visualStrength"] is None
    assert ir["hook"]["soundOffClear"] is None
    assert "hook.visualStrength" in " ".join(result.metadata.warnings) or any(
        "visualStrength" in w for w in result.metadata.warnings
    )


def test_hook_fields_are_populated_when_explicit_evidence_present() -> None:
    """An explicit HOOK: section with a stated visual strength and sound-off
    claim is parsed, not discarded."""
    prompt = """
Title: Loud Hook

15-second video

## Hook
Visual strength: 5
Sound off clear: true

## Timeline
0.0-15.0 SEC: Hero — explodes into view
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["hook"]["visualStrength"] == 5
    assert ir["hook"]["soundOffClear"] is True


def test_core_mechanic_consistency_is_none_when_not_stated() -> None:
    """No explicit consistency statement in the prompt must not default to
    the passing value "consistent" — it becomes None (evidence missing)."""
    prompt = """
Title: Plain Beat

15-second video

## Timeline
0.0-15.0 SEC: Hero — stands still
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["consistency"] is None


def test_core_mechanic_consistency_is_parsed_when_explicitly_stated() -> None:
    prompt = """
Title: Breaking Rule

15-second video

## Core Rule
The rule breaks halfway through on purpose for the twist.

## Timeline
0.0-15.0 SEC: Hero — walks normally
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["coreMechanic"]["consistency"] == "breaking"
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_parser_contract.py -k "hook_fields or consistency" -v`

Expected: `test_hook_fields_are_none_when_no_explicit_evidence` and `test_core_mechanic_consistency_is_none_when_not_stated` FAIL (currently returns `4`/`True`/`"consistent"`). `test_hook_fields_are_populated_when_explicit_evidence_present` and `test_core_mechanic_consistency_is_parsed_when_explicitly_stated` also FAIL since no extraction logic for these exists yet.

- [ ] **Step 3: Implement explicit hook visual-strength/sound-off extraction, replacing the optimistic defaults**

Read the current `_identify_hook` method in `prompt_parser.py` in full before editing (it currently hardcodes `"visualStrength": 4, "soundOffClear": True`). Replace it with:

```python
    def _identify_hook(self, text: str, beats: list[dict[str, Any]]) -> dict[str, Any]:
        """Identify hook characteristics.

        visualStrength and soundOffClear are only ever populated from
        explicit evidence in the prompt text. A prompt with no HOOK section
        and no visual-strength/sound-off language leaves both as None
        (evidence missing) rather than defaulting to values that would pass
        HOOK_002's un-reverified threshold checks.
        """
        starts_mid_action = "start" in text.lower() and ("mid" in text.lower() or "action" in text.lower())

        first_beat = beats[0] if beats else None

        visual_strength = self._extract_hook_visual_strength(text)
        sound_off_clear = self._extract_hook_sound_off_clear(text)

        if visual_strength is None:
            self.warnings.append(
                "hook.visualStrength not explicitly stated in prompt; evidence missing"
            )
        if sound_off_clear is None:
            self.warnings.append(
                "hook.soundOffClear not explicitly stated in prompt; evidence missing"
            )

        return {
            "anomaly": first_beat["action"] if first_beat else "Unknown",
            "startsAt": 0.0,
            "startsMidAction": starts_mid_action,
            "visualStrength": visual_strength,
            "soundOffClear": sound_off_clear,
        }

    def _extract_hook_visual_strength(self, text: str) -> int | None:
        """Extract an explicit visual-strength rating (1-5) from a HOOK
        section, e.g. "Visual strength: 5". Returns None when absent."""
        match = re.search(r"visual\s*strength[:\s]+(\d)", text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 5:
                return value
        return None

    def _extract_hook_sound_off_clear(self, text: str) -> bool | None:
        """Extract an explicit sound-off-clear claim from a HOOK section,
        e.g. "Sound off clear: true". Returns None when absent."""
        match = re.search(r"sound\s*off\s*clear[:\s]+(true|false|yes|no)", text, re.IGNORECASE)
        if match:
            return match.group(1).lower() in ("true", "yes")
        return None
```

- [ ] **Step 4: Implement explicit consistency extraction, replacing the optimistic default**

Read the current `_extract_core_mechanic` method in full before editing (it currently has two `return` paths, both hardcoding `"consistency": "consistent"`). Replace the whole method with:

```python
    def _extract_core_mechanic(self, text: str) -> dict[str, Any]:
        """Extract the core physical rule.

        consistency is only populated from explicit evidence ("breaking",
        "evolving", or an explicit "stays consistent"/"consistent throughout"
        statement). Absent evidence leaves consistency as None rather than
        defaulting to the passing value "consistent" — CONSISTENCY_001 has
        no semantic re-verification of this field, so a fabricated default
        would manufacture a guaranteed PASS.
        """
        rule_match = re.search(
            r"(?:ONE SIMPLE|CORE|MAIN)\s+(?:RULE|MECHANIC|CONCEPT):\s*\n((?:.*\n?)+?)(?:\n\n|={3,})",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        consistency = self._extract_mechanic_consistency(text)
        if consistency is None:
            self.warnings.append(
                "coreMechanic.consistency not explicitly stated in prompt; evidence missing"
            )

        if rule_match:
            rule_text = rule_match.group(1).strip()[:200]
            return {
                "physicalRule": rule_text,
                "causeEffect": "Extracted from prompt",
                "consistency": consistency,
                "mechanicCount": 1,  # Default assumption; author/parser does not
                # currently detect multiple mechanics from
                # text — CONCEPT_007 verifies this claim
                # semantically rather than trusting it.
            }

        self.ambiguities.append("Core mechanic not explicitly stated")
        return {
            "physicalRule": "Inferred from beat actions",
            "causeEffect": "Action-based consequence",
            "consistency": consistency,
            "mechanicCount": 1,
        }

    def _extract_mechanic_consistency(self, text: str) -> str | None:
        """Extract an explicit rule-consistency statement. Returns one of
        "breaking", "evolving", "consistent", or None if the prompt makes
        no explicit claim either way."""
        text_lower = text.lower()
        if "breaks" in text_lower or "breaking" in text_lower:
            return "breaking"
        if "evolves" in text_lower or "evolving" in text_lower:
            return "evolving"
        if "stays consistent" in text_lower or "consistent throughout" in text_lower:
            return "consistent"
        return None
```

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_parser_contract.py -v`

Expected: all PASS, including every pre-existing test in the file (re-read the full file's test list and confirm none of them asserted `visualStrength == 4`/`soundOffClear is True`/`consistency == "consistent"` as a default-path expectation — if one does, that test was relying on the exact bug this task fixes and must be corrected to assert `is None` instead; as of this plan being written, no such test exists in `test_parser_contract.py`, but re-verify directly before proceeding since the file may have changed).

- [ ] **Step 6: Check downstream consumers of these three fields for crashes on `None`**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && grep -rn "visualStrength\|soundOffClear" app/rules/rule_engine.py`

You will see `_evaluate_hook_002` does `hook.get("visualStrength", 1)` and `_evaluate_hook_003` does `hook.get("soundOffClear", False)`. Both use `.get(key, default)` which only applies the default when the **key is absent**, not when the value is explicitly `None` — since the parser now always includes the key with value `None`, `hook.get("visualStrength", 1)` will return `None`, not `1`, and `visual_strength < 4` will raise `TypeError: '<' not supported between instances of 'NoneType' and 'int'`. This is a real bug this task must also fix: these two evaluators must treat `None` as `UNKNOWN`, not crash and not silently default to a passing value. Read `_evaluate_hook_002` and `_evaluate_hook_003` in full, then fix both.

For `_evaluate_hook_002`, after the existing `starts_at`/`starts_mid_action` extraction lines, add a `None` guard for `visual_strength` before it's compared:

```python
        hook = video_plan_ir.get("hook", {})
        starts_mid_action = hook.get("startsMidAction", False)
        visual_strength = hook.get("visualStrength")
        starts_at = hook.get("startsAt", 0.0)
```

(Note the `.get("visualStrength")` with no second argument — this returns `None` whether the key is absent or explicitly `None`, which is the correct unified handling here.) Then, after the existing `starts_at > 0.8` and `not starts_mid_action` FAIL branches (keep those exactly as they are — a missing-anomaly-timing or non-mid-action start is still a real, verifiable FAIL regardless of visual strength), replace the final `if visual_strength < 4:` branch with:

```python
        if visual_strength is None:
            return RuleEvaluation(
                rule_id="HOOK_002",
                rule_name="First Frame Anomaly",
                family="hook_strength",
                severity="CRITICAL",
                result="UNKNOWN",
                message=(
                    "Hook starts mid-action, but visual strength was not explicitly stated "
                    "in the prompt and cannot be verified."
                ),
            )
        if visual_strength < 4:
```

(leave the rest of that branch and the final `return` for the PASS case unchanged).

For `_evaluate_hook_003`, read it in full, then change `sound_off_clear = hook.get("soundOffClear", False)` to `sound_off_clear = hook.get("soundOffClear")` and add a `None` branch before the existing `if not sound_off_clear:` FAIL branch:

```python
        hook = video_plan_ir.get("hook", {})
        sound_off_clear = hook.get("soundOffClear")

        if sound_off_clear is None:
            return RuleEvaluation(
                rule_id="HOOK_003",
                rule_name="Sound Independence",
                family="hook_strength",
                severity="CRITICAL",
                result="UNKNOWN",
                message=(
                    "hook.soundOffClear was not explicitly stated in the prompt and cannot "
                    "be verified."
                ),
            )
        if not sound_off_clear:
```

Similarly, `_evaluate_consistency_001` does `core_mechanic.get("consistency", "consistent")` — change to `core_mechanic.get("consistency")` and add a `None`/`UNKNOWN` branch before the existing `if consistency == "breaking":` check:

```python
        core_mechanic = video_plan_ir.get("coreMechanic", {})
        consistency = core_mechanic.get("consistency")

        if consistency is None:
            return RuleEvaluation(
                rule_id="CONSISTENCY_001",
                rule_name="Physics Rule Consistency",
                family="consistency",
                severity="WARNING",
                result="UNKNOWN",
                message=(
                    "coreMechanic.consistency was not explicitly stated in the prompt and "
                    "cannot be verified."
                ),
            )
        if consistency == "breaking":
```

- [ ] **Step 7: Write tests proving the three evaluators now return UNKNOWN instead of crashing or false-passing**

Create a new test file `tests/test_hook_consistency_unknown_on_missing_evidence.py`:

```python
"""HOOK_002, HOOK_003, and CONSISTENCY_001 must report UNKNOWN, not crash and
not fabricate a PASS, when the parser could not find explicit evidence for
visualStrength/soundOffClear/consistency (Plan A, Phase 5/1)."""

from typing import Any

from app.config import settings
from app.quality.contracts import RuleOutcome
from app.rules.rule_engine import RuleEngine

RULESET_1_0 = str(settings.rules_dir / "RULESET_1.0.yaml")


def _engine() -> RuleEngine:
    return RuleEngine(RULESET_1_0)


def test_hook_002_returns_unknown_when_visual_strength_is_none() -> None:
    engine = _engine()
    ir: dict[str, Any] = {
        "hook": {"startsMidAction": True, "visualStrength": None, "soundOffClear": True, "startsAt": 0.0},
        "beats": [],
    }
    evaluation = engine._evaluate_hook_002(ir, {})
    assert evaluation.outcome is RuleOutcome.UNKNOWN


def test_hook_002_still_fails_on_verified_non_mid_action_start() -> None:
    """A verified (not missing) False for startsMidAction is still a real FAIL,
    not UNKNOWN -- this task only changes handling of missing visualStrength."""
    engine = _engine()
    ir: dict[str, Any] = {
        "hook": {"startsMidAction": False, "visualStrength": None, "soundOffClear": True, "startsAt": 0.0},
        "beats": [],
    }
    evaluation = engine._evaluate_hook_002(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL


def test_hook_003_returns_unknown_when_sound_off_clear_is_none() -> None:
    engine = _engine()
    ir: dict[str, Any] = {"hook": {"soundOffClear": None}, "beats": []}
    evaluation = engine._evaluate_hook_003(ir, {})
    assert evaluation.outcome is RuleOutcome.UNKNOWN


def test_consistency_001_returns_unknown_when_consistency_is_none() -> None:
    engine = _engine()
    ir: dict[str, Any] = {"coreMechanic": {"consistency": None}, "beats": []}
    evaluation = engine._evaluate_consistency_001(ir, {})
    assert evaluation.outcome is RuleOutcome.UNKNOWN


def test_consistency_001_still_fails_on_verified_breaking_consistency() -> None:
    engine = _engine()
    ir: dict[str, Any] = {"coreMechanic": {"consistency": "breaking"}, "beats": []}
    evaluation = engine._evaluate_consistency_001(ir, {})
    assert evaluation.outcome is RuleOutcome.FAIL
```

- [ ] **Step 8: Run the new test file and the full suite**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_hook_consistency_unknown_on_missing_evidence.py -v && python -m pytest -q`

Expected: the 5 new tests PASS, and the full suite is still green. Pay close attention to any existing test in `tests/test_rule_engine_contract.py`, `tests/test_rule_engine_new_rules.py`, or `tests/test_ruleset_1_2_integration.py`/`tests/test_ruleset_1_3_integration.py` that builds a minimal IR with `hook={"visualStrength": 4, ...}` or omits `visualStrength` entirely expecting the old default-4 behavior — if any such test currently relies on an *omitted* key defaulting to `4`/`True`/`"consistent"`, it will now get `None` from `.get("visualStrength")` (no default) and may need updating to pass the value explicitly. Fix any such test to pass explicit evidence values rather than relying on removed defaults — do not weaken the new UNKNOWN behavior to make an old test pass.

- [ ] **Step 9: Run lint/type checks**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && ruff check . && ruff format --check . && mypy --strict app`

Expected: clean. If `mypy --strict` flags `visual_strength: int | None` comparisons, the `if visual_strength is None: return ...` guard above the comparison already narrows the type for the following `if visual_strength < 4:` line — no additional annotation should be needed, but if mypy still complains, add `assert visual_strength is not None` immediately after the `None` guard's early return (this is a no-op at runtime but satisfies the type narrower).

- [ ] **Step 10: Commit**

```bash
git add intelligence/ml-service/app/parser/prompt_parser.py intelligence/ml-service/app/rules/rule_engine.py intelligence/ml-service/tests/test_parser_contract.py intelligence/ml-service/tests/test_hook_consistency_unknown_on_missing_evidence.py
git commit -m "fix(intelligence): stop parser from fabricating hook/consistency evidence; HOOK_002/HOOK_003/CONSISTENCY_001 report UNKNOWN on missing evidence"
```

---

### Task 4: Stop requiring `[ATTEMPT: VERB]` markers and surface attempt-recognition confidence

**Files:**
- Modify: `intelligence/ml-service/app/parser/prompt_parser.py`
- Test: `intelligence/ml-service/tests/test_parser_contract.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_extract_attempt_marker` additionally recognizes an unmarked but clearly action-verb-led beat description as a lower-confidence attempt, emitting an assumption note; a beat recognized this way still gets `isAttempt=True` and a `primaryVerb`, but the parser records an assumption string identifying which beats were inferred vs. explicitly marked.

The spec requires markers to "improve confidence but not be mandatory for correctness." The current code (`_extract_attempt_marker`) already does the *conservative* half of this correctly — it never fabricates `isAttempt=True` from thin air — but it also never recognizes an attempt without the marker, which the spec also flags as wrong (markers must not be mandatory). This task adds the inference path without weakening the "beats without a marker default to `isAttempt=False`" principle **for cases that genuinely give no evidence**.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_parser_contract.py`:

```python
def test_unmarked_beat_with_clear_action_verb_is_inferred_as_attempt() -> None:
    """A beat description starting with a recognizable physical action verb,
    even with no [ATTEMPT: VERB] marker, is inferred as an attempt at lower
    confidence rather than being invisible to ATTEMPT_001/ATTEMPT_002."""
    prompt = """
Title: Mimi vs Rug

15-second video

## Characters
- Mimi: Curious

## Timeline
0.0-3.0 SEC: Mimi catches the sliding cup with both hands
3.0-6.0 SEC: Mimi blocks it with a book
6.0-15.0 SEC: Mimi watches the rug slide away
"""
    result = parse_prompt(prompt)
    ir = result.video_plan_ir
    beats = ir["beats"]
    assert beats[0]["isAttempt"] is True
    assert beats[0]["primaryVerb"] == "CATCHES"
    assert beats[1]["isAttempt"] is True
    assert beats[1]["primaryVerb"] == "BLOCKS"
    assert beats[2]["isAttempt"] is False
    assert any("inferred" in a.lower() for a in result.metadata.assumptions)


def test_explicit_marker_still_takes_precedence_over_inference() -> None:
    """When both an explicit [ATTEMPT: VERB] marker and an inferrable leading
    verb are present, the explicit marker's verb wins."""
    prompt = """
Title: Mimi vs Rug

15-second video

## Timeline
0.0-3.0 SEC: Mimi catches the sliding cup [ATTEMPT: GRAB]
"""
    ir = parse_prompt(prompt).video_plan_ir
    assert ir["beats"][0]["primaryVerb"] == "GRAB"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_parser_contract.py -k "inferred_as_attempt or explicit_marker_still_takes_precedence" -v`

Expected: `test_unmarked_beat_with_clear_action_verb_is_inferred_as_attempt` FAILS (`beats[0]["isAttempt"]` is currently `False`). `test_explicit_marker_still_takes_precedence_over_inference` currently PASSES (explicit markers already work) — confirm this with the run, it's a regression guard, not a new behavior.

- [ ] **Step 3: Add a conservative action-verb inference list and wire it into `_create_beat_from_description`**

Read `_extract_attempt_marker` and `_create_beat_from_description` in full before editing. Add a new method right after `_extract_attempt_marker`:

```python
    # Physical action verbs that, when they are the first word of a beat's
    # action text, indicate a problem-solving attempt even with no explicit
    # [ATTEMPT: VERB] marker. Deliberately short and conservative -- this is
    # a confidence-improving inference, not a replacement for the marker;
    # ambiguous or non-physical leading words are left unmarked (isAttempt
    # stays False) rather than guessed.
    _INFERABLE_ATTEMPT_VERBS = frozenset(
        {
            "CATCHES",
            "CATCH",
            "BLOCKS",
            "BLOCK",
            "GRABS",
            "GRAB",
            "PULLS",
            "PULL",
            "PUSHES",
            "PUSH",
            "LIFTS",
            "LIFT",
            "HOLDS",
            "HOLD",
            "STEPS",
            "STEP",
            "TURNS",
            "TURN",
            "PLACES",
            "PLACE",
            "ROTATES",
            "ROTATE",
        }
    )

    def _infer_attempt_from_leading_verb(self, description: str) -> tuple[bool, str]:
        """Infer isAttempt/primaryVerb from an unmarked beat's leading word,
        when that word is a known physical action verb. Returns
        (False, "") when the leading word is not in the conservative
        _INFERABLE_ATTEMPT_VERBS set -- never guessed from anything else.
        """
        first_word_match = re.match(r"[A-Za-z]+", description.strip())
        if not first_word_match:
            return False, ""
        first_word = first_word_match.group(0).upper()
        if first_word in self._INFERABLE_ATTEMPT_VERBS:
            return True, first_word
        return False, ""
```

Now find this block inside `_create_beat_from_description`:

```python
        is_attempt, primary_verb = self._extract_attempt_marker(description)
        relates_to_core_problem = self._extract_detached_marker(description)
```

Replace with:

```python
        is_attempt, primary_verb = self._extract_attempt_marker(description)
        if not is_attempt:
            is_attempt, primary_verb = self._infer_attempt_from_leading_verb(description)
            if is_attempt:
                self.assumptions.append(
                    f"Beat '{description[:40]}...' inferred as an attempt ({primary_verb}) "
                    "from its leading verb; no explicit [ATTEMPT: VERB] marker was present."
                )
        relates_to_core_problem = self._extract_detached_marker(description)
```

(Note: this preserves exact marker precedence — `_extract_attempt_marker` runs first and short-circuits the inference entirely when it finds a real marker, satisfying Step 1's second test.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_parser_contract.py -v`

Expected: all PASS, including every pre-existing test (re-verify `test_beats_default_isattempt_false_and_primaryverb_empty` still passes — it uses "stands still"/"walks away" as beat text, neither of which is in `_INFERABLE_ATTEMPT_VERBS`, so it should be unaffected; confirm this directly rather than assuming).

- [ ] **Step 5: Run full suite + lint/type**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add intelligence/ml-service/app/parser/prompt_parser.py intelligence/ml-service/tests/test_parser_contract.py
git commit -m "feat(intelligence): infer attempts from leading action verbs without requiring [ATTEMPT: VERB] markers"
```

---

### Task 5: Make timeline-parse failure explicit instead of silently returning an empty plan

**Files:**
- Modify: `intelligence/ml-service/app/parser/prompt_parser.py`
- Test: `intelligence/ml-service/tests/test_parser_contract.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_fallback_beat_parsing` still returns `[]` (an empty beat list is sometimes genuinely correct — e.g. a 0-beat edge case elsewhere in the suite), but `parse_prompt`'s resulting `ParserMetadata` now has a *new* field: `evidence_missing: tuple[str, ...]` on `ParserMetadata` in `contracts.py`, populated with `"beats"` whenever the fallback path with zero beats is hit, so callers can distinguish "genuinely empty timeline" from "the parser could not find any timeline at all."

- [ ] **Step 1: Write the failing test**

First read `app/quality/contracts.py`'s current `ParserMetadata` dataclass (it has `confidence`, `ambiguities`, `assumptions`, `warnings` — frozen, all defaults are empty tuples except `confidence`). Append to `tests/test_parser_contract.py`:

```python
def test_fallback_parsing_with_no_timeline_marks_evidence_missing() -> None:
    """A prompt with no parseable timeline at all must surface
    evidenceMissing=("beats",), not silently return an empty, valid-looking
    plan that callers mistake for a genuinely zero-beat video."""
    prompt = "Title: No Timeline Here\n\nJust some prose, no SEC markers at all.\n"
    result = parse_prompt(prompt)
    assert result.video_plan_ir["beats"] == []
    assert "beats" in result.metadata.evidence_missing


def test_normal_parse_with_beats_has_empty_evidence_missing() -> None:
    result = parse_prompt(SAMPLE_PROMPT)
    assert result.metadata.evidence_missing == ()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_parser_contract.py -k "evidence_missing" -v`

Expected: both FAIL. `AttributeError: 'ParserMetadata' object has no attribute 'evidence_missing'`.

- [ ] **Step 3: Add `evidence_missing` to `ParserMetadata` in `contracts.py`**

Read the current `ParserMetadata` dataclass in `app/quality/contracts.py` in full first. It currently is:

```python
@dataclass(frozen=True)
class ParserMetadata:
    """Confidence and provenance notes emitted by the prompt parser."""

    confidence: float
    ambiguities: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
```

Add one field:

```python
@dataclass(frozen=True)
class ParserMetadata:
    """Confidence and provenance notes emitted by the prompt parser."""

    confidence: float
    ambiguities: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    evidence_missing: tuple[str, ...] = ()
```

- [ ] **Step 4: Thread `evidence_missing` through the parser**

In `prompt_parser.py`, add `self.evidence_missing: list[str] = []` to `_reset_parser_state`:

```python
    def _reset_parser_state(self) -> None:
        """Clear warnings/assumptions/ambiguities/evidence_missing for new parse"""
        self.warnings = []
        self.assumptions = []
        self.ambiguities = []
        self.evidence_missing = []
```

Also add `self.evidence_missing: list[str] = []` to `__init__` (read `__init__` first — it currently sets `self.warnings`/`self.assumptions`/`self.ambiguities`; add the fourth list alongside them for consistency, since `_reset_parser_state` is called from `parse()` but the attribute should exist from construction too).

In `_fallback_beat_parsing`, read it in full (currently just appends a warning and returns `[]`). Change to:

```python
    def _fallback_beat_parsing(self, text: str, duration: float) -> list[dict[str, Any]]:
        """Fallback if no explicit timestamps found"""
        self.warnings.append("Using fallback beat parsing - confidence low")
        self.evidence_missing.append("beats")
        # Create generic beats
        return []
```

Finally, in `parse()`, find the `return` statement building the raw dict (`{"videoPlanIR": ..., "parserMetadata": {...}}`) and add `"evidence_missing": self.evidence_missing` to the `parserMetadata` dict:

```python
        return {
            "videoPlanIR": video_plan_ir,
            "parserMetadata": {
                "confidence": confidence,
                "ambiguities": self.ambiguities,
                "assumptions": self.assumptions,
                "warnings": self.warnings,
                "evidence_missing": self.evidence_missing,
            },
        }
```

Then in `parse_prompt` (the module-level convenience function at the bottom of the file), add `evidence_missing=tuple(pm.get("evidence_missing", []))` to the `ParserMetadata(...)` constructor call:

```python
    return ParseResult(
        video_plan_ir=raw["videoPlanIR"],
        metadata=ParserMetadata(
            confidence=float(pm.get("confidence", 0.0)),
            ambiguities=tuple(pm.get("ambiguities", [])),
            assumptions=tuple(pm.get("assumptions", [])),
            warnings=tuple(pm.get("warnings", [])),
            evidence_missing=tuple(pm.get("evidence_missing", [])),
        ),
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_parser_contract.py -v`

Expected: all PASS.

- [ ] **Step 6: Add `evidence_missing` to the API response too (completes the Task 2 field set correctly)**

In `app/api/quality.py`, add `evidence_missing: list[str]` to `QualityReportResponse` (alongside `parser_warnings`/`parser_assumptions` added in Task 2), and populate it in `convert_quality_report` with `evidence_missing=list(enhanced.parser_metadata.evidence_missing)`. Add a test to `tests/test_api_conversions.py`:

```python
def test_convert_quality_report_exposes_evidence_missing() -> None:
    parsed = parse_prompt("Title: No Timeline\n\nJust prose.\n")
    report = RuleEngine(RULESET).evaluate(parsed.video_plan_ir)
    enhanced = QualityScorer().create_enhanced_report(report, parsed.video_plan_ir, parsed.metadata)

    response = convert_quality_report(enhanced, "1.0")

    assert "beats" in response.evidence_missing
```

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py -v`

Expected: all PASS, including this new one.

- [ ] **Step 7: Run full suite + lint/type**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add intelligence/ml-service/app/quality/contracts.py intelligence/ml-service/app/parser/prompt_parser.py intelligence/ml-service/app/api/quality.py intelligence/ml-service/tests/test_parser_contract.py intelligence/ml-service/tests/test_api_conversions.py
git commit -m "feat(intelligence): surface evidence_missing when timeline parsing finds no beats at all"
```

---

### Task 6: Normalize all LLM provider runtime failures into `SemanticCheckServiceError`

**Files:**
- Modify: `intelligence/ml-service/app/llm/semantic_checks.py`
- Test: `intelligence/ml-service/tests/test_semantic_checks.py`

**Interfaces:**
- Consumes: nothing new from other tasks.
- Produces: a new module-level helper `_call_llm_safely(llm: LLMProvider, prompt: str) -> str` in `semantic_checks.py` that wraps `llm.complete(prompt)` and converts **any** exception (not just the provider-construction `ValueError` already handled separately) into `SemanticCheckServiceError`. All 7 existing `llm.complete(prompt)` call sites in this file are replaced with calls to this helper.

- [ ] **Step 1: Write the failing test**

Read `tests/test_semantic_checks.py` in full first — note its existing mocking convention (it patches `app.llm.semantic_checks.get_provider` to return a `Mock()` with `.complete` configured via `return_value` or `side_effect`). Append:

```python
class TestLlmRuntimeFailuresNormalizeToServiceError:
    def test_find_duplicate_strategy_pairs_wraps_timeout_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = TimeoutError("request timed out")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                find_duplicate_strategy_pairs(
                    [
                        {"primaryVerb": "PUSH", "action": "a", "consequence": "b"},
                        {"primaryVerb": "PULL", "action": "c", "consequence": "d"},
                    ]
                )

    def test_find_duplicate_strategy_pairs_wraps_generic_runtime_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = RuntimeError("SDK internal error")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                find_duplicate_strategy_pairs(
                    [
                        {"primaryVerb": "PUSH", "action": "a", "consequence": "b"},
                        {"primaryVerb": "PULL", "action": "c", "consequence": "d"},
                    ]
                )

    def test_check_twist_matches_rule_wraps_network_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = ConnectionError("network unreachable")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                check_twist_matches_rule(physical_rule="rule", twist_description="twist")

    def test_count_independent_mechanics_wraps_timeout_error(self) -> None:
        mock_llm = Mock()
        mock_llm.complete.side_effect = TimeoutError("request timed out")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            with pytest.raises(SemanticCheckServiceError):
                count_independent_mechanics(
                    physical_rule="rule", beat_descriptions=["beat one", "beat two"]
                )

    def test_service_error_message_does_not_leak_raw_exception_type_only(self) -> None:
        """The wrapped error's message must be safe/diagnostic -- it already
        is, since SemanticCheckServiceError just carries str(original_error);
        this test documents that no API key or secret-shaped string from a
        provider's internal error ever appears literally in the raised
        message when it wasn't in the original exception's str() already
        (we are not newly adding risk here, just confirming no masking is
        accidentally stripping the diagnostic value either)."""
        mock_llm = Mock()
        mock_llm.complete.side_effect = RuntimeError("provider said: invalid request")

        with patch("app.llm.semantic_checks.get_provider", return_value=mock_llm):
            try:
                check_twist_matches_rule(physical_rule="rule", twist_description="twist")
            except SemanticCheckServiceError as e:
                assert "invalid request" in str(e)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_semantic_checks.py -k "LlmRuntimeFailuresNormalizeToServiceError" -v`

Expected: all 5 FAIL — currently the raw `TimeoutError`/`RuntimeError`/`ConnectionError` propagates uncaught out of `find_duplicate_strategy_pairs`/`check_twist_matches_rule`/`count_independent_mechanics` (the test's `pytest.raises(SemanticCheckServiceError)` catches the wrong exception type, so pytest reports a failure, not the expected exception).

- [ ] **Step 3: Add the `_call_llm_safely` helper**

Read the full current `semantic_checks.py` file (it's grown across several past sessions — confirm the exact current list of functions calling `llm.complete(...)` before editing; as of this plan being written there are 7: `find_duplicate_strategy_pairs`, `check_twist_matches_rule`, `count_independent_mechanics`, `check_goal_is_natural`, `check_rule_is_predictable`, `check_opening_problem_legible`, `check_character_performance_readable`, and `check_attempts_are_generation_executable` — re-verify this count directly with `grep -n "llm.complete(" app/llm/semantic_checks.py` since it may have changed). Add this helper right after the `_parse_json_with_markdown_fallback` function definition:

```python
def _call_llm_safely(llm: Any, prompt: str) -> str:
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
```

(The `llm: Any` type is intentional: `get_provider` returns `LLMProvider`, but importing that type here would create a needless import for a parameter whose only use is calling `.complete()`; `Any` is already used elsewhere in this module's `_parse_json_with_markdown_fallback` return type pattern. If `mypy --strict` objects, import `from app.llm.provider import LLMProvider` and type the parameter as `LLMProvider` instead — check both ways and use whichever the existing file's import style favors.)

- [ ] **Step 4: Replace every `response = llm.complete(prompt)` call site with the safe wrapper**

For each of the functions found in Step 3, find its line that reads exactly:

```python
    response = llm.complete(prompt)
```

and replace with:

```python
    response = _call_llm_safely(llm, prompt)
```

Do this for all matching lines in the file (`find_duplicate_strategy_pairs`, `check_twist_matches_rule`, `count_independent_mechanics`, `check_goal_is_natural`, `check_rule_is_predictable`, `check_opening_problem_legible`, `check_character_performance_readable`, `check_attempts_are_generation_executable`). Note `check_attempts_are_generation_executable` may use a different local variable name for the response — read it directly and adapt the replacement to match its actual code rather than assuming identical structure to the others.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_semantic_checks.py -v`

Expected: all PASS, including every pre-existing test in the file (the wrapper is a strict superset of behavior — it still lets `SemanticCheckServiceError` through unchanged via the `except SemanticCheckServiceError: raise` clause, and still lets a normal successful `str` response through unchanged).

- [ ] **Step 6: Run full suite + lint/type checks**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add intelligence/ml-service/app/llm/semantic_checks.py intelligence/ml-service/tests/test_semantic_checks.py
git commit -m "fix(intelligence): normalize all LLM provider runtime failures to SemanticCheckServiceError, not just construction errors"
```

---

### Task 7: Make the FastAPI `/validate` endpoint return structured `SERVICE_ERROR`, not an unstructured 500, on an unhandled provider failure

**Files:**
- Modify: `intelligence/ml-service/app/api/quality.py`
- Test: `intelligence/ml-service/tests/test_api_conversions.py`

**Interfaces:**
- Consumes: `SemanticCheckServiceError` from Task 6.
- Produces: the `validate_prompt` endpoint handler catches any exception raised during `engine.evaluate(ir)` and, if the underlying cause chain contains `SemanticCheckServiceError`, still returns HTTP 200 with a `QualityReportResponse` whose `status == "SERVICE_ERROR"` rather than letting FastAPI's default handler produce a 500. (Rule evaluators already catch `SemanticCheckServiceError` themselves and convert it to a `SERVICE_ERROR` `RuleEvaluation` — re-verify this is still true for all current evaluators before writing this task's test, since this task's job is only to confirm the *endpoint* doesn't accidentally un-wrap that into an HTTP error somewhere above the rule engine, not to re-implement evaluator-level handling that already exists.)

- [ ] **Step 1: Read the full current rule-engine evaluator pattern to confirm there is no endpoint-level gap**

Run: `cd intelligence/ml-service && grep -n "except SemanticCheckServiceError" app/rules/rule_engine.py | wc -l`

Confirm this count matches (or exceeds) the number of LLM-semantic-check-calling evaluators (`ATTEMPT_002`, `PAYOFF_003`, `CONCEPT_007`, `GOAL_001`, `CONCEPT_008`, `HOOK_004`, `PERFORMANCE_001`, `GENERATION_EXECUTABLE_ATTEMPTS` — re-verify this list directly, do not trust this plan's memory of it). If any evaluator calling a semantic-check function does NOT have a matching `except SemanticCheckServiceError` block, that is a real gap to fix as part of this task — read that evaluator's full body and add the same `except SemanticCheckServiceError as e: return RuleEvaluation(..., severity="BLOCKER", result="SERVICE_ERROR", ...)` pattern already used by its siblings before proceeding to Step 2.

- [ ] **Step 2: Write the integration test proving the endpoint survives a provider failure as a 200 + SERVICE_ERROR, not a 500**

Append to `tests/test_api_conversions.py`:

```python
def test_validate_endpoint_returns_200_service_error_on_llm_provider_failure() -> None:
    """A semantic-check-dependent rule's LLM provider failing (e.g. missing
    credentials, network error) must surface as a normal 200 response with
    status SERVICE_ERROR, never an unstructured 500 -- the quality endpoint
    is expected-failure-aware for provider outages."""
    from unittest.mock import patch

    client = TestClient(app)
    # ATTEMPT_002 requires >=2 verb-distinct attempt beats to invoke its LLM
    # semantic check at all -- construct a prompt that reaches that path.
    attempt_prompt = (
        "Title: Attempt Service Error Test\n\n15-second video\n\n## Characters\n- Hero: Brave\n\n"
        "## Timeline\n"
        "0.0-3.0 SEC: Hero pushes the box [ATTEMPT: PUSH]\n"
        "3.0-6.0 SEC: Hero pulls the box [ATTEMPT: PULL]\n"
        "6.0-15.0 SEC: Hero watches the box\n"
    )
    with patch(
        "app.rules.rule_engine.find_duplicate_strategy_pairs",
        side_effect=__import__("app.llm.semantic_checks", fromlist=["SemanticCheckServiceError"]).SemanticCheckServiceError(
            "LLM provider unavailable: OPENAI_API_KEY not set"
        ),
    ):
        response = client.post(
            "/api/v1/quality/validate",
            json={"prompt": attempt_prompt, "ruleset_version": "1.3"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SERVICE_ERROR"
    assert len(body["service_errors"]) >= 1
    assert any(se["rule_id"] == "ATTEMPT_002" for se in body["service_errors"])
```

(The `__import__(...)` inline is deliberately avoided in favor of a clean top-of-file import — do not actually write it that way; instead add `from app.llm.semantic_checks import SemanticCheckServiceError` to the test file's existing imports at the top, read the current imports first, and use `SemanticCheckServiceError(...)` directly in the `side_effect=` line.)

- [ ] **Step 3: Run to verify current behavior**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py::test_validate_endpoint_returns_200_service_error_on_llm_provider_failure -v`

Expected: this test either already PASSES (if `ATTEMPT_002`'s existing `except SemanticCheckServiceError` handling and the Task 1 `service_errors` field are both already correct and connected) or FAILS with a `KeyError: 'service_errors'` (if Task 1 hasn't landed yet in this session — it should have, since tasks are sequential) or an actual 500 (if there's a real endpoint-level gap). Determine which case you're in before proceeding.

- [ ] **Step 4: If the test fails with an actual 500 (not a KeyError), find and fix the gap at the evaluator level — not the endpoint level**

Read `app/api/quality.py`'s `validate_prompt` function in full. The correct architecture is: `engine.evaluate(ir)` must never raise — every evaluator that calls a semantic-check function already catches `SemanticCheckServiceError` internally and returns a `RuleEvaluation` with `result="SERVICE_ERROR"` (per Step 1's audit of this file). The endpoint handler itself should need **no** try/except around `engine.evaluate(ir)` for this failure mode, because by the time control reaches the endpoint, the failure has already been converted into ordinary report data, not an exception.

If Step 3 shows an actual 500 (not a `KeyError`), the bug is that one specific evaluator is missing its `except SemanticCheckServiceError` block — go back to Step 1's grep output, identify exactly which semantic-check-calling evaluator lacks the matching `except` clause, read that evaluator's full current body in `app/rules/rule_engine.py`, and add the same pattern its siblings already use, e.g.:

```python
        try:
            judgment, reasoning = some_semantic_check_function(...)
        except SemanticCheckServiceError as e:
            return RuleEvaluation(
                rule_id="<THE_ACTUAL_RULE_ID>",
                rule_name="<THE_ACTUAL_RULE_NAME>",
                family="<THE_ACTUAL_FAMILY>",
                severity="BLOCKER",
                result="SERVICE_ERROR",
                message=f"<Specific check description> failed: {e}",
                details={"error": str(e)},
            )
```

Do not add a new try/except in `validate_prompt` itself as a workaround — that would paper over a missing evaluator-level handler rather than fixing it, and would make the next new rule added without proper error handling invisible again. The fix belongs in `rule_engine.py`, at the specific evaluator identified by Step 1, every time.

- [ ] **Step 5: Run the test again to confirm it passes**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest tests/test_api_conversions.py -v`

Expected: all PASS.

- [ ] **Step 6: Run full suite + lint/type**

Run: `cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data && python -m pytest -q && ruff check . && ruff format --check . && mypy --strict app`

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add intelligence/ml-service/app/api/quality.py intelligence/ml-service/app/rules/rule_engine.py intelligence/ml-service/tests/test_api_conversions.py
git commit -m "test(intelligence): prove /validate returns structured SERVICE_ERROR not a 500 on provider failure"
```

---

### Task 8: Mirror the new response fields on the Spring side

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/DtoModels.java`
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java`
- Test: find or create `intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/QualityReportDtoTest.java`

**Interfaces:**
- Consumes: the Python JSON shape produced by Task 1/2/5 (`outcome` instead of `result`, plus `unknown_rules`, `not_applicable_rules`, `service_errors`, `parser_confidence`, `parser_warnings`, `parser_assumptions`, `top_strengths`, `top_weaknesses`, `evidence_missing` — all snake_case on the wire from FastAPI/Pydantic, confirm Jackson's naming strategy handles this; read `intelligence/backend/src/main/resources/application.yml` or wherever Jackson config lives to confirm `spring.jackson.property-naming-strategy=SNAKE_CASE` or equivalent is already configured, since `QualityMlClient` is clearly already deserializing other snake_case fields like `blocker_count`/`critical_count` successfully today).
- Produces: `RuleEvaluationDto` gains `String outcome` replacing `boolean result`; `QualityReportDto` gains `List<RuleEvaluationDto> unknownRules`, `List<RuleEvaluationDto> notApplicableRules`, `List<RuleEvaluationDto> serviceErrors`, `double parserConfidence`, `List<String> parserWarnings`, `List<String> parserAssumptions`, `List<String> topStrengths`, `List<String> topWeaknesses`, `List<String> evidenceMissing`.

- [ ] **Step 1: Confirm the Jackson naming strategy currently in effect**

Run: `grep -rn "property-naming-strategy\|PropertyNamingStrategy" intelligence/backend/src/main/resources/ intelligence/backend/src/main/java/ 2>/dev/null`

If this finds a global `SNAKE_CASE` config, the Java field names below (`camelCase`) will correctly map to the Python response's `snake_case` wire format automatically — no `@JsonProperty` annotations needed, consistent with how `QualityReportDto`'s existing `overallScore`/`rulesetVersion` fields already map to `overall_score`/`ruleset_version` from Python today. If no such global config is found, each new/changed field needs an explicit `@JsonProperty("snake_case_name")` annotation — in that case, read how the *existing* fields in `QualityReportDto`/`RuleEvaluationDto` currently achieve the mapping (there must be some mechanism already, since the client works today) and follow the exact same approach for the new fields.

- [ ] **Step 2: Write the failing test**

First check whether any test file already exists for these DTOs:

Run: `find intelligence/backend/src/test -iname "*QualityReport*" -o -iname "*RuleEvaluation*"`

If none exists, create `intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/QualityReportDtoTest.java`:

```java
package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class QualityReportDtoTest {

  @Test
  void deserializesOutcomeAndNewRuleListsFromPythonSnakeCaseResponse() throws Exception {
    ObjectMapper mapper = new ObjectMapper();
    // Read how other tests in this package configure the ObjectMapper's
    // naming strategy before assuming the default -- if QualityMlClient
    // relies on a globally-configured Spring Boot RestClient ObjectMapper
    // bean, construct this test's mapper the same way rather than a bare
    // `new ObjectMapper()`, which does NOT apply snake_case by default.
    mapper.setPropertyNamingStrategy(
        com.fasterxml.jackson.databind.PropertyNamingStrategies.SNAKE_CASE);

    String json =
        """
        {
          "overall_score": 70.0,
          "status": "NEEDS_REVISION",
          "ruleset_version": "1.3",
          "blocker_count": 0,
          "critical_count": 0,
          "warning_count": 1,
          "family_scores": {"progression": 70.0},
          "failed_rules": [],
          "unknown_rules": [
            {"rule_id": "CONSISTENCY_002", "rule_name": "Character Continuity Lock",
             "family": "consistency", "severity": "CRITICAL", "outcome": "UNKNOWN",
             "message": "No rendered video available yet.", "actual_value": null,
             "threshold_value": null}
          ],
          "not_applicable_rules": [],
          "service_errors": [],
          "priority_fixes": [],
          "score_card": {"score": 70.0, "label": "Acceptable", "color": "yellow"},
          "timeline_data": {"beats": [], "consequence_markers": [], "state_segments": []},
          "parser_confidence": 0.9,
          "parser_warnings": [],
          "parser_assumptions": [],
          "top_strengths": [],
          "top_weaknesses": [],
          "evidence_missing": []
        }
        """;

    QualityReportDto dto = mapper.readValue(json, QualityReportDto.class);

    assertThat(dto.unknownRules()).hasSize(1);
    assertThat(dto.unknownRules().get(0).outcome()).isEqualTo("UNKNOWN");
    assertThat(dto.unknownRules().get(0).ruleId()).isEqualTo("CONSISTENCY_002");
    assertThat(dto.notApplicableRules()).isEmpty();
    assertThat(dto.serviceErrors()).isEmpty();
    assertThat(dto.parserConfidence()).isEqualTo(0.9);
    assertThat(dto.evidenceMissing()).isEmpty();
  }
}
```

(If the project uses JUnit 5 + AssertJ already — confirm via an existing test file's imports before assuming; if it uses a different assertion library, match that instead.)

- [ ] **Step 3: Run to verify it fails**

Run: `cd intelligence/backend && ./mvnw test -Dtest=QualityReportDtoTest -q` (or the project's actual test-run command — check `intelligence/backend/pom.xml` or a `Makefile`/`README` for the exact invocation if `./mvnw` isn't present at that path; the parent `pom.xml` lives at `intelligence/pom.xml` per the earlier directory listing, so this may need to run from `intelligence/` with a module flag — verify the correct working directory and command before running).

Expected: compilation failure (`cannot find symbol: method unknownRules()`) since the DTO doesn't have these fields/methods yet (Java records auto-generate accessor methods matching field names).

- [ ] **Step 4: Update `RuleEvaluationDto` in `DtoModels.java`**

Read the current `RuleEvaluationDto` record definition in full. Replace:

```java
record RuleEvaluationDto(
    String ruleId,
    String ruleName,
    String family,
    String severity,
    boolean result,
    String message,
    Double actualValue,
    Double thresholdValue) {}
```

with:

```java
record RuleEvaluationDto(
    String ruleId,
    String ruleName,
    String family,
    String severity,
    String outcome,
    String message,
    Double actualValue,
    Double thresholdValue) {}
```

- [ ] **Step 5: Update `QualityReportDto.java`**

Read the current full file (already shown above in this plan's investigation — it's a short record with a Javadoc comment per field). Replace the whole file content with:

```java
package com.pompomhills.intelligence.quality;

import java.util.List;
import java.util.Map;

/**
 * Quality validation report from ML service.
 *
 * @param overallScore 0-100 quality score
 * @param status RENDER_READY, NEEDS_REVISION, BLOCKED, or SERVICE_ERROR
 * @param rulesetVersion Ruleset version used
 * @param blockerCount Number of blocker-level failures
 * @param criticalCount Number of critical-level failures
 * @param warningCount Number of warning-level issues
 * @param familyScores Per-family scores (Concept Strength, Hook Strength, etc.)
 * @param failedRules Rule evaluations with outcome FAIL
 * @param unknownRules Rule evaluations with outcome UNKNOWN (applies but evidence missing)
 * @param notApplicableRules Rule evaluations with outcome NOT_APPLICABLE (does not apply to this concept)
 * @param serviceErrors Rule evaluations with outcome SERVICE_ERROR (provider/runtime failure, not a rule failure)
 * @param priorityFixes Top fixes sorted by severity
 * @param scoreCard UI-ready score card (label, color)
 * @param timelineData Beat-level timeline data for visualization
 * @param parserConfidence Parser's self-reported confidence (0.0-1.0) in the extracted Video Plan IR
 * @param parserWarnings Parser warnings about ambiguous or unparseable input
 * @param parserAssumptions Parser assumptions made when explicit evidence was absent
 * @param topStrengths Top-scoring quality families, human-readable
 * @param topWeaknesses Lowest-scoring quality families needing attention, human-readable
 * @param evidenceMissing Named IR sections the parser could not populate at all (e.g. "beats")
 */
public record QualityReportDto(
    double overallScore,
    String status,
    String rulesetVersion,
    int blockerCount,
    int criticalCount,
    int warningCount,
    Map<String, Double> familyScores,
    List<RuleEvaluationDto> failedRules,
    List<RuleEvaluationDto> unknownRules,
    List<RuleEvaluationDto> notApplicableRules,
    List<RuleEvaluationDto> serviceErrors,
    List<PriorityFixDto> priorityFixes,
    ScoreCardDto scoreCard,
    TimelineDataDto timelineData,
    double parserConfidence,
    List<String> parserWarnings,
    List<String> parserAssumptions,
    List<String> topStrengths,
    List<String> topWeaknesses,
    List<String> evidenceMissing) {}
```

- [ ] **Step 6: Run the test to verify it passes**

Run the same test command from Step 3.

Expected: PASS.

- [ ] **Step 7: Search for and fix any other Java code constructing a `RuleEvaluationDto` or `QualityReportDto` with the old shape**

Run: `grep -rln "RuleEvaluationDto(\|QualityReportDto(" intelligence/backend/src/main intelligence/creative-render-service/src/main 2>/dev/null`

For every file found (besides `DtoModels.java`/`QualityReportDto.java` themselves), read it and check whether it constructs either record positionally (Java records are positional-constructor by default) — if so, update the call site to match the new field list/order, or confirm it only ever deserializes these DTOs from JSON (never constructs them directly in code), in which case no change is needed there.

- [ ] **Step 8: Run the full Spring test suite**

Run: `cd intelligence/backend && ./mvnw test -q` (verify actual command/working-directory per Step 3's note).

Expected: all tests PASS, no compilation errors anywhere referencing these two DTOs.

- [ ] **Step 9: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/DtoModels.java intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/QualityReportDtoTest.java
git commit -m "feat(intelligence): mirror outcome/unknownRules/notApplicableRules/serviceErrors/parser-metadata fields on Spring QualityReportDto"
```

---

## Plan A completion checklist

Before considering Plan A done, re-run and confirm every one of these commands succeeds, and update `intelligence/docs/superpowers/PART_01_COMPLETION_ROADMAP.md`'s status table (mark Plan A ✅, note the final commit hash) in the same session:

```bash
cd intelligence/ml-service && source .venv/bin/activate && export POMPOM_DATA_ROOT=$(pwd)/../data
python -m pytest -q
ruff check .
ruff format --check .
mypy --strict app
```

```bash
cd intelligence/backend
./mvnw test -q   # confirm actual command per Task 8 Step 3's note
```

Do not start Plan C until all of the above are green and the roadmap doc is updated and committed.
