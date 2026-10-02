# Validation Module

Regression checking and version comparison for prompt revisions.

## Purpose

When applying fixes to a prompt (e.g., "add more consequences" to fix CONCEPT_006), we need to ensure the fix doesn't break other rules. The regression checker compares two versions and flags:

- **Critical Regressions**: A passing rule now fails at CRITICAL/BLOCKER level
- **Warning Regressions**: A passing rule now fails at WARNING level
- **Concerns**: Overall score drops significantly without specific rule failures
- **Improvements**: Rules fixed, families improved, status upgraded

## Components

### RegressionChecker

Main class that compares two `QualityReport` objects.

```python
from app.validation import RegressionChecker
from app.rules import RuleEngine

engine = RuleEngine("data/rules/RULESET_1.0.yaml")

# Evaluate original
report_v1 = engine.evaluate(ir_original)

# Evaluate after applying fix
report_v2 = engine.evaluate(ir_fixed)

# Check for regressions
checker = RegressionChecker()
regression = checker.check(report_v1, report_v2, "original", "fixed")

if regression.has_regressions:
    print(f"Critical: {len(regression.critical_regressions)}")
    print(f"Warnings: {len(regression.warning_regressions)}")
    print(f"Recommendation: {regression.recommendation}")
```

### RegressionReport

Complete analysis with:

- **Overall metrics**: Score delta, status change
- **Regressions**: Critical, warning, concerns
- **Improvements**: Fixed rules, improved families
- **Recommendation**: ACCEPT / REVISE / REJECT

### Severity Levels

1. **CRITICAL**: Passing rule → BLOCKER/CRITICAL fail (must reject)
2. **WARNING**: Passing rule → WARNING fail (needs attention)
3. **CONCERN**: Score drop without specific rule fail (investigate)

## Decision Logic

```
IF critical_regressions > 0:
    → REJECT (fix broke critical rules)

ELIF warning_regressions > fixed_rules:
    → REVISE (more harm than good)

ELIF net_improvement:
    → ACCEPT (fixes > regressions, score improved)

ELSE:
    → REVISE (mixed results, try different approach)
```

## Integration with Auto-Fix Loop

```python
# Pseudo-code for iterative fix workflow
while status != "RENDER_READY" and iterations < MAX_ITERATIONS:
    # 1. Get priority fixes
    fixes = quality_scorer.get_priority_fixes(report)
    
    # 2. Apply top fix
    ir_revised = apply_fix(ir_current, fixes[0])
    
    # 3. Re-evaluate
    report_revised = engine.evaluate(ir_revised)
    
    # 4. Check regression
    regression = checker.check(report_current, report_revised)
    
    if regression.recommendation == "ACCEPT":
        ir_current = ir_revised
        report_current = report_revised
    elif regression.recommendation == "REJECT":
        # Try next fix
        continue
    else:  # REVISE
        # Apply fix with different parameters
        continue
```

## Thresholds

- **Score drop concern**: 5+ points without rule fail
- **Family degradation**: 10+ point drop in family score

## Output Format

```
============================================================
REGRESSION CHECK: original → fixed
============================================================

Overall Score:  68.5 → 75.2 (+6.7)
Status:         BLOCKED → NEEDS_REVISION
Recommendation: ACCEPT

Net improvement: 2 fixes, +6.7 points, status improved.

✅ FIXED RULES (2):
  • CONCEPT_006
  • BEAT_004

⚡ WARNING REGRESSIONS (1):
  • Rule NOVELTY_001 degraded to WARNING: Longest gap 5.2s exceeds 4.5s

📈 IMPROVED FAMILIES: Concept Strength, Visual Novelty
============================================================
```

## Performance

- O(n) where n = number of rules
- <5ms for typical 10-rule comparison
- Stateless, can run in parallel for multiple revision candidates
