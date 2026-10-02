# Rule Engine

Core validation engine that evaluates Video Plan IR against quality rules.

## Architecture

```
Video Plan IR
    ↓
Rule Engine ← Loads RULESET_1.0.yaml
    ↓
Evaluators (10 implemented)
    ↓
Quality Report
```

## Usage

```python
from app.rules.rule_engine import validate_video_plan
from app.parser.prompt_parser import parse_prompt

# Parse prompt
result = parse_prompt(prompt_text)
video_plan_ir = result["videoPlanIR"]

# Validate
report = validate_video_plan(video_plan_ir)

print(f"Overall Score: {report.overall_score}")
print(f"Status: {report.status}")
print(f"Blockers: {report.blocker_count}")
print(f"Criticals: {report.critical_count}")
print(f"Warnings: {report.warning_count}")

# Check if render ready
if report.is_render_ready:
    print("✅ RENDER READY")
else:
    print("❌ BLOCKED or NEEDS REVISION")
    
# Show failed rules
for rule in report.failed_rules:
    print(f"[{rule.severity}] {rule.rule_id}: {rule.message}")
```

## Quality Report Structure

```python
@dataclass
class QualityReport:
    overall_score: float  # 0-100
    status: str  # RENDER_READY, NEEDS_REVISION, BLOCKED

    blocker_count: int
    critical_count: int
    warning_count: int
    pass_count: int

    family_scores: Dict[str, float]  # Per-family scores
    evaluations: List[RuleEvaluation]  # All rule results
    failed_rules: List[RuleEvaluation]  # Only failures

    ruleset_version: str
    evaluated_at: str
```

## Status Determination

```python
if score >= 92 AND blockers == 0 AND criticals == 0:
    status = "RENDER_READY"
elif score < 80 OR blockers > 0:
    status = "BLOCKED"
else:
    status = "NEEDS_REVISION"
```

## Implemented Rules

### 1. CONCEPT_006 — Consequence Capacity (BLOCKER)
- **Check:** `distinct_consequence_count >= 4`
- **Severity:** BLOCKER if < 4, WARNING if == 4
- **Uses:** ConsequenceAnalyzer

### 2. BEAT_004 — Static State Dominance (CRITICAL)
- **Check:** `dominant_state_percentage <= 30%`
- **Severity:** CRITICAL if > 30%, WARNING if 25-30%
- **Uses:** StaticStateAnalyzer

### 3. REPETITION_002 — Visual Beat Repetition (CRITICAL)
- **Check:** No action repeats > 2-3 times without escalation
- **Severity:** CRITICAL if > 3x or 3x without consequence change
- **Logic:** Counts action frequency across beats

### 4. REPETITION_003 — Cycle Repetition Limit (CRITICAL)
- **Check:** Cycles repeat max 2-3 times with structural escalation
- **Severity:** CRITICAL if > 3x, WARNING if == 3x
- **Note:** Requires `cycleGroup` field (parser doesn't populate yet)

### 5. NOVELTY_001 — Novelty Timeline Distribution (WARNING)
- **Check:** `longest_novelty_gap <= 4.5s`
- **Severity:** CRITICAL if > 6s, WARNING if 4.5-6s
- **Uses:** ConsequenceAnalyzer

### 6. PROGRESSION_005 — Consequence Novelty Timeline (WARNING→CRITICAL)
- **Check:** Static pattern (repeat/continuation) <= 50% of video
- **Severity:** CRITICAL if > 65%, WARNING if 50-65%
- **Logic:** Sums duration of non-new beats

### 7. ESCALATION_004 — Delayed Payoff (WARNING→CRITICAL)
- **Check:** Final payoff starts before 75-80% of video
- **Severity:** CRITICAL if > 80% with weak middle, WARNING if > 75%
- **Uses:** finalPayoff.startsAt

### 8. PAYOFF_001 — Not Repeat of Opening (CRITICAL)
- **Check:** `isRepeatOfOpening == false`
- **Severity:** CRITICAL if true
- **Uses:** finalPayoff.isRepeatOfOpening

### 9. PRODUCIBILITY_001 — Very High Complexity Block (BLOCKER)
- **Check:** `overallComplexity != "very_high"`
- **Severity:** BLOCKER if very_high, WARNING if high
- **Uses:** producibility.overallComplexity

### 10. CONSISTENCY_001 — Physics Rule Consistency (WARNING)
- **Check:** `consistency == "consistent"`
- **Severity:** WARNING if breaking
- **Uses:** coreMechanic.consistency

## Example: Validating FAIL_001 (Kiko)

```python
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import validate_video_plan

# Load Kiko prompt
with open("kiko_slippery_rough.txt") as f:
    prompt_text = f.read()

# Parse
result = parse_prompt(prompt_text)
video_plan_ir = result["videoPlanIR"]

# Validate
report = validate_video_plan(video_plan_ir)

print(f"\n=== QUALITY REPORT ===")
print(f"Overall Score: {report.overall_score:.1f}/100")
print(f"Status: {report.status}")
print(f"\n=== SEVERITY COUNTS ===")
print(f"Blockers: {report.blocker_count}")
print(f"Criticals: {report.critical_count}")
print(f"Warnings: {report.warning_count}")
print(f"Passes: {report.pass_count}")

print(f"\n=== FAMILY SCORES ===")
for family, score in report.family_scores.items():
    print(f"{family}: {score:.1f}")

print(f"\n=== FAILED RULES ===")
for rule in report.failed_rules:
    print(f"[{rule.severity}] {rule.rule_id} — {rule.rule_name}")
    print(f"  {rule.message}")
    if rule.actual_value is not None:
        print(f"  Actual: {rule.actual_value}, Threshold: {rule.threshold_value}")
```

**Expected Output:**
```
=== QUALITY REPORT ===
Overall Score: 58.3/100
Status: BLOCKED

=== SEVERITY COUNTS ===
Blockers: 1
Criticals: 2
Warnings: 1
Passes: 6

=== FAMILY SCORES ===
concept_strength: 0.0
visual_novelty: 42.5
final_payoff: 40.0
...

=== FAILED RULES ===
[BLOCKER] CONCEPT_006 — Consequence Capacity
  Only 2 distinct visual consequences detected. Minimum: 4. Core mechanic insufficient for 15 seconds.
  Actual: 2, Threshold: 4

[CRITICAL] BEAT_004 — Static State Dominance
  Visual state 'on_rough_mat' occupies 42.0% of video. Maximum: 30%.
  Actual: 42.0, Threshold: 30.0

[CRITICAL] PAYOFF_001 — Not Repeat of Opening
  Final beat repeats opening action without escalation. Payoff must be unique or bigger.
  Actual: True, Threshold: False
```

## Scoring Algorithm

### Family Score Calculation
For each family:
```python
if rule.result == "PASS":
    if rule.severity == "PASS":
        score = 100
    elif rule.severity == "WARNING":
        score = 85
elif rule.result == "FAIL":
    if rule.severity == "BLOCKER":
        score = 0
    elif rule.severity == "CRITICAL":
        score = 40
    elif rule.severity == "WARNING":
        score = 70

family_score = average(rule_scores)
```

### Overall Score Calculation
```python
weighted_sum = sum(family_score * family_weight)
overall_score = weighted_sum / total_weight
```

**Family Weights:**
- concept_strength: 0.12
- hook_strength: 0.12
- visual_novelty: 0.14
- progression: 0.11
- escalation: 0.10
- motion_quality: 0.09
- readability: 0.08
- ai_producibility: 0.10
- consistency: 0.07
- final_payoff: 0.09
- render_risk: 0.08

## Extending the Engine

### Adding a New Rule

1. **Add rule to RULESET_1.0.yaml**
2. **Implement evaluator method:**

```python
def _evaluate_new_rule_id(self, video_plan_ir: Dict, rule: Dict) -> RuleEvaluation:
    """NEW_RULE_ID: Rule Description"""
    # Extract relevant data
    value = video_plan_ir.get("some_field")

    # Apply logic
    if value < threshold:
        return RuleEvaluation(
            rule_id="NEW_RULE_ID",
            rule_name="Rule Name",
            family="family_name",
            severity="CRITICAL",
            result="FAIL",
            message="Failure message",
            actual_value=value,
            threshold_value=threshold,
        )
    else:
        return RuleEvaluation(
            rule_id="NEW_RULE_ID",
            rule_name="Rule Name",
            family="family_name",
            severity="PASS",
            result="PASS",
            message="Success message",
            actual_value=value,
        )
```

3. **Register in evaluators dict:**
```python
self.evaluators = {
    ...
    "NEW_RULE_ID": self._evaluate_new_rule_id,
}
```

## Testing

```bash
cd ml-service
python -m pytest tests/rules/
```

## Integration Points

- **Parser** → Provides Video Plan IR
- **Analyzers** → Provide metrics for rules
- **Scoring System** (Task #8) → Uses QualityReport
- **Spring API** (Task #12) → Exposes validation endpoint
- **Angular UI** (Task #14) → Displays report

## Performance

- Single video validation: < 50ms
- Ruleset loading: < 10ms (cached after first load)
- All 10 rules: O(n) where n = beat count

No database required for validation (stateless).


---

## Rule Versioning System

### Overview

RuleVersionManager tracks ruleset evolution, maintains backward compatibility, and manages rule changes.

```python
from app.rules import RuleVersionManager

# Initialize manager
manager = RuleVersionManager("data/rules")

# Load specific version
engine_v1 = manager.load_version("1.0")

# Load latest version
engine_latest = manager.load_latest()

# List all versions
versions = manager.list_versions()
for v in versions:
    print(f"v{v.version}: {v.description}")

# Compare versions
comparison = manager.compare_versions("1.0", "1.1")
print(comparison.migration_notes)
```

### Directory Structure

```
data/rules/
  ├── RULESET_1.0.yaml       # Initial ruleset
  ├── RULESET_1.1.yaml       # Minor update
  ├── RULESET_2.0.yaml       # Major update (breaking)
  └── versions.yaml          # Version metadata
```

### versions.yaml Format

```yaml
versions:
  - version: '1.0'
    release_date: '2026-09-14'
    description: 'Initial ruleset'
    ruleset_path: 'RULESET_1.0.yaml'
    learned_from: ['FAIL_001', 'FAIL_002']
    is_breaking: false
    changes:
      - rule_id: 'CONCEPT_006'
        change_type: 'added'
        reason: 'Prevent low-consequence scenarios'
```

### Semantic Versioning

- **Major (2.0)**: Breaking changes (rules removed, thresholds stricter)
- **Minor (1.1)**: New rules, non-breaking adjustments
- **Patch (1.0.1)**: Bug fixes only

### Creating New Versions

```python
from app.rules import RuleChange

changes = [
    RuleChange(
        rule_id="BEAT_005",
        change_type="added",
        new_value={"threshold": 0.20},
        reason="Additional variety check",
        breaking_change=False,
    )
]

new_path = manager.create_new_version(
    new_version="1.1", description="Enhanced checks", changes=changes, learned_from=["FAIL_004"]
)
```

### Version Comparison

```python
comparison = manager.compare_versions("1.0", "1.1")

if not comparison.is_backward_compatible:
    print("⚠️  Breaking changes!")
    for change in comparison.breaking_changes:
        print(f"  {change.rule_id}: {change.reason}")

print(f"New rules: {comparison.new_rules}")
print(f"Modified: {comparison.modified_rules}")
```

### Integration with Database

```sql
CREATE TABLE prompt_validations (
    id SERIAL PRIMARY KEY,
    prompt_id INT,
    ruleset_version VARCHAR(10) NOT NULL,
    overall_score NUMERIC(5,2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

Track which version validated each prompt, enabling:
- Re-validation with new rulesets
- A/B testing rule changes
- Performance tracking per version
