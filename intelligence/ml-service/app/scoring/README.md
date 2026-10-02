# Quality Scoring System

Enhanced scoring with detailed breakdowns, visualization data, and actionable recommendations.

## Purpose

Builds on top of `QualityReport` from rule engine to provide:
- Detailed score breakdowns per family
- Visual representation data (cards, timelines, radar charts)
- Actionable insights and priority fixes
- Version tracking and trend analysis

## Usage

```python
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import validate_video_plan
from app.scoring.quality_scorer import create_enhanced_report

# Parse and validate
result = parse_prompt(prompt_text)
video_plan_ir = result["videoPlanIR"]
parser_metadata = result["parserMetadata"]

quality_report = validate_video_plan(video_plan_ir)

# Create enhanced report
enhanced = create_enhanced_report(quality_report, video_plan_ir, parser_metadata)

# Access detailed scoring
print(f"Overall: {enhanced.overall_score:.1f}/100")
print(f"Status: {enhanced.status}")

# View score breakdowns
for breakdown in enhanced.score_breakdowns:
    print(f"\n{breakdown.family}: {breakdown.score:.0f}/100")
    print(f"  Weight: {breakdown.weight}, Contribution: {breakdown.weighted_contribution:.1f}")
    print(f"  Passed: {breakdown.rules_passed}, Failed: {breakdown.rules_failed}")
    
    if breakdown.recommendations:
        print(f"  Recommendations:")
        for rec in breakdown.recommendations:
            print(f"    - {rec}")

# View top insights
print(f"\n=== TOP 3 STRENGTHS ===")
for strength in enhanced.top_3_strengths:
    print(f"✓ {strength}")

print(f"\n=== TOP 3 WEAKNESSES ===")
for weakness in enhanced.top_3_weaknesses:
    print(f"✗ {weakness}")

# Get priority fixes
print(f"\n=== PRIORITY FIXES ===")
for fix in enhanced.priority_fixes:
    print(f"{fix['priority']}. [{fix['severity']}] {fix['rule_name']}")
    print(f"   Issue: {fix['issue']}")
    print(f"   Fix: {fix['recommendation']}")
    print(f"   Impact: {fix['impact']}")
```

## Data Structures

### EnhancedQualityReport

```python
@dataclass
class EnhancedQualityReport:
    # Basic scores
    overall_score: float
    status: str
    version: int
    
    # Detailed breakdowns
    score_breakdowns: List[ScoreBreakdown]
    
    # Visualization data
    score_card: Dict[str, Any]
    timeline_data: Dict[str, Any]
    family_radar: Dict[str, List[float]]
    
    # Insights
    top_3_strengths: List[str]
    top_3_weaknesses: List[str]
    priority_fixes: List[Dict[str, Any]]
    
    # Metadata
    evaluated_at: str
    parser_confidence: float
    ruleset_version: str
```

### ScoreBreakdown

```python
@dataclass
class ScoreBreakdown:
    family: str
    score: float
    weight: float
    weighted_contribution: float
    
    rules_passed: int
    rules_failed: int
    rules_warning: int
    
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
```

## Visualization Data

### Score Card
```python
{
    "score": 58.3,
    "label": "Poor",  # Excellent/Good/Acceptable/Weak/Poor
    "color": "red",  # green/blue/yellow/orange/red
    "status": "BLOCKED",
    "blockers": 1,
    "criticals": 2,
    "warnings": 1,
    "passes": 6,
    "is_render_ready": false,
}
```

### Timeline Data
```python
{
    "duration": 15.0,
    "beats": [
        {
            "id": "beat_01",
            "start": 0.0,
            "end": 1.0,
            "intensity": 8,
            "action": "slides on floor",
            "isNew": true,
        },
        ...,
    ],
    "consequence_markers": [
        {"time": 0.0, "action": "slides on floor"},
        {"time": 3.2, "action": "reaches mat"},
    ],
    "state_segments": [
        {"state": "on_slippery_floor", "start": 0.0, "end": 3.2},
        {"state": "on_rough_mat", "start": 3.2, "end": 11.5},
    ],
}
```

### Family Radar
```python
{
    "labels": ["Concept Strength", "Hook Strength", "Visual Novelty", ...],
    "scores": [72, 96, 42, 65, 58, 71, 88, 85, 94, 45, 78],
    "thresholds": {"excellent": 90, "good": 80, "acceptable": 70},
}
```

## Priority Fixes

System generates prioritized, actionable fixes:

```python
[
    {
        "priority": 1,
        "severity": "BLOCKER",
        "rule_id": "CONCEPT_006",
        "rule_name": "Consequence Capacity",
        "family": "concept_strength",
        "issue": "Only 2 distinct visual consequences detected. Minimum: 4.",
        "recommendation": "Add 2 more visually distinct consequences. Consider introducing new obstacles or props.",
        "impact": "Critical - Required for render",
    },
    {
        "priority": 2,
        "severity": "CRITICAL",
        "rule_id": "BEAT_004",
        "rule_name": "Static State Dominance",
        "family": "visual_novelty",
        "issue": "Visual state 'on_rough_mat' occupies 42.0% of video. Maximum: 30%.",
        "recommendation": "Reduce time in 'on_rough_mat' by ~17%. Add transitions or new visual states.",
        "impact": "High - Major score improvement",
    },
]
```

## Recommendations Map

System provides specific, actionable recommendations per rule:

| Rule | Recommendation |
|------|----------------|
| CONCEPT_006 | Add N more visually distinct consequences. Consider new obstacles or props. |
| BEAT_004 | Reduce time in dominant state by X%. Add transitions or new visual states. |
| REPETITION_002 | Reduce repeated action from N to 2-3 occurrences with escalation. |
| REPETITION_003 | Break the cycle after 2 iterations. Introduce new physical element. |
| NOVELTY_001 | Add 1-2 new consequences between Xs and Ys. |
| PROGRESSION_005 | Add new physical consequences in middle section (4-11s). |
| ESCALATION_004 | Move final escalation earlier or strengthen middle section. |
| PAYOFF_001 | Change final beat. Make it bigger, add twist, or don't repeat opening. |
| PRODUCIBILITY_001 | Simplify complex operations. Reduce simultaneous interactions. |
| CONSISTENCY_001 | Maintain consistent physics rule or justify change as part of concept. |

## Version Tracking

Track quality improvements across iterations:

```python
from app.scoring.quality_scorer import QualityScorer

scorer = QualityScorer()

# Version 1
report_v1 = create_enhanced_report(quality_v1, ir_v1, parser_v1)
trend_v1 = scorer.track_version(report_v1)

# Version 2 (after fixes)
report_v2 = create_enhanced_report(quality_v2, ir_v2, parser_v2)
trend_v2 = scorer.track_version(report_v2, previous_report=report_v1)

print(f"Score change: {trend_v2.score_delta:+.1f}")
print(f"Improved families: {trend_v2.improved_families}")
print(f"Regressed families: {trend_v2.regressed_families}")

# Get full history
history = scorer.get_version_history()
for trend in history:
    print(f"v{trend.version}: {trend.score:.1f} ({trend.status})")
```

**Example Output:**
```
Score change: +23.5
Improved families: ['visual_novelty', 'concept_strength', 'final_payoff']
Regressed families: []

v1: 58.3 (BLOCKED)
v2: 81.8 (NEEDS_REVISION)
v3: 93.2 (RENDER_READY)
```

## Score Thresholds

```python
EXCELLENT_THRESHOLD = 90  # Green, top quality
GOOD_THRESHOLD = 80  # Blue, solid quality
ACCEPTABLE_THRESHOLD = 70  # Yellow, minimal acceptable
WEAK_THRESHOLD = 60  # Orange, needs work
# < 60 = Poor (Red)
```

## Integration with UI

The enhanced report is designed for Angular dashboard:

### Score Card Component
```typescript
// Display overall score with color coding
<quality-score-card [data]="enhanced.score_card"></quality-score-card>
```

### Timeline Visualization
```typescript
// Show beat timeline with consequence markers
<quality-timeline [data]="enhanced.timeline_data"></quality-timeline>
```

### Family Radar Chart
```typescript
// Display radar chart of all 11 families
<quality-radar [data]="enhanced.family_radar"></quality-radar>
```

### Priority Fixes List
```typescript
// Show actionable fixes ordered by priority
<priority-fixes-list [fixes]="enhanced.priority_fixes"></priority-fixes-list>
```

## Example: Complete Flow

```python
from app.parser.prompt_parser import parse_prompt
from app.rules.rule_engine import validate_video_plan
from app.scoring.quality_scorer import create_enhanced_report, QualityScorer

# Initialize
scorer = QualityScorer()

# Parse prompt
result = parse_prompt(prompt_text)
video_plan_ir = result["videoPlanIR"]
parser_metadata = result["parserMetadata"]

# Validate
quality_report = validate_video_plan(video_plan_ir)

# Create enhanced report
enhanced = create_enhanced_report(quality_report, video_plan_ir, parser_metadata)

# Display summary
print(f"\n{'=' * 60}")
print(f"QUALITY REPORT - Version {enhanced.version}")
print(f"{'=' * 60}")
print(f"\nOverall Score: {enhanced.overall_score:.1f}/100 ({enhanced.score_card['label']})")
print(f"Status: {enhanced.status}")
print(f"Parser Confidence: {enhanced.parser_confidence:.0%}")

# Show family breakdown
print(f"\n{'=' * 60}")
print(f"FAMILY SCORES")
print(f"{'=' * 60}")
for breakdown in enhanced.score_breakdowns:
    symbol = "✓" if breakdown.score >= 80 else "✗"
    print(f"{symbol} {breakdown.family:20s} {breakdown.score:5.1f}/100 (weight: {breakdown.weight:.2f})")

# Show insights
print(f"\n{'=' * 60}")
print(f"TOP STRENGTHS")
print(f"{'=' * 60}")
for i, strength in enumerate(enhanced.top_3_strengths, 1):
    print(f"{i}. {strength}")

print(f"\n{'=' * 60}")
print(f"TOP WEAKNESSES")
print(f"{'=' * 60}")
for i, weakness in enumerate(enhanced.top_3_weaknesses, 1):
    print(f"{i}. {weakness}")

# Show fixes
print(f"\n{'=' * 60}")
print(f"PRIORITY FIXES")
print(f"{'=' * 60}")
for fix in enhanced.priority_fixes:
    print(f"\n[{fix['priority']}] {fix['rule_name']} ({fix['severity']})")
    print(f"    Issue: {fix['issue']}")
    print(f"    Fix: {fix['recommendation']}")
    print(f"    Impact: {fix['impact']}")

# Track version
if previous_enhanced_report:
    trend = scorer.track_version(enhanced, previous_enhanced_report)
    print(f"\n{'=' * 60}")
    print(f"VERSION TREND")
    print(f"{'=' * 60}")
    print(f"Score change: {trend.score_delta:+.1f}")
    print(f"Improved: {', '.join(trend.improved_families)}")
    print(f"Regressed: {', '.join(trend.regressed_families)}")
```

## Performance

- Enhanced report generation: < 10ms additional overhead
- All data pre-computed for UI rendering
- No database queries needed (stateless)
- Version tracking: O(n) where n = number of versions

## Next Steps

1. Integrate with Spring API (Task #12)
2. Build Angular UI components (Task #14)
3. Add performance feedback loop (Task #18)
4. Enable rule learning from real performance data
