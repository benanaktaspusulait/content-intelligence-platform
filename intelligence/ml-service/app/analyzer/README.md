# Video Plan IR Analyzers

Core analysis modules for evaluating Video Plan IR quality.

## Modules

### 1. Consequence Analyzer

Counts and analyzes visual consequences across the video timeline.

**Key Metrics:**
- `distinct_consequence_count`: Number of truly new visual consequences
- `longest_novelty_gap_seconds`: Longest time between new consequences
- `distinct_percentage`: % of beats that are visually new

**Usage:**
```python
from app.analyzer.consequence_analyzer import analyze_consequences

metrics = analyze_consequences(video_plan_ir)

print(f"Distinct consequences: {metrics.distinct_consequence_count}")
print(f"Passes minimum threshold (4): {metrics.passes_minimum_threshold}")
print(f"Longest novelty gap: {metrics.longest_novelty_gap_seconds}s")
```

**Rule Enforcement:**
- CONCEPT_006: `distinct_consequence_count >= 4` (BLOCKER)
- NOVELTY_001: `longest_novelty_gap_seconds <= 4.5` (WARNING)

### 2. Static State Analyzer

Detects when a single visual state dominates too much of the video.

**Key Metrics:**
- `dominant_state_percentage`: % of video spent in most common state
- `unique_state_count`: Number of distinct visual states
- `state_durations`: Breakdown of time per state

**Usage:**
```python
from app.analyzer.static_state_analyzer import analyze_static_states, detect_static_state_issues

metrics = analyze_static_states(video_plan_ir)

print(f"Dominant state: {metrics.dominant_state_id}")
print(f"Percentage: {metrics.dominant_state_percentage:.1f}%")
print(f"Passes standard threshold (30%): {metrics.passes_standard_threshold}")

# Get detailed issues
issues = detect_static_state_issues(video_plan_ir)
for issue in issues:
    print(f"{issue['severity']}: {issue['message']}")
```

**Rule Enforcement:**
- BEAT_004: `dominant_state_percentage <= 30%` (CRITICAL)
- BEAT_004: `dominant_state_percentage <= 25%` (WARNING if 25-30%)

## Example: Analyzing FAIL_001 (Kiko)

```python
from app.parser.prompt_parser import parse_prompt
from app.analyzer.consequence_analyzer import analyze_consequences
from app.analyzer.static_state_analyzer import analyze_static_states, detect_static_state_issues

# Load and parse Kiko prompt
with open("prompts/kiko_slippery_rough.txt", "r") as f:
    prompt_text = f.read()

result = parse_prompt(prompt_text)
video_plan_ir = result["videoPlanIR"]

# Analyze consequences
cons_metrics = analyze_consequences(video_plan_ir)
print(f"\n=== Consequence Analysis ===")
print(f"Distinct consequences: {cons_metrics.distinct_consequence_count}")
print(f"Total beats: {cons_metrics.total_beats}")
print(f"Distinct %: {cons_metrics.distinct_percentage:.1f}%")
print(
    f"Longest gap: {cons_metrics.longest_novelty_gap_seconds:.1f}s at {cons_metrics.longest_gap_start_time}s-{cons_metrics.longest_gap_end_time}s"
)
print(f"PASSES: {cons_metrics.passes_minimum_threshold}")

# Analyze static states
state_metrics = analyze_static_states(video_plan_ir)
print(f"\n=== Static State Analysis ===")
print(f"Unique states: {state_metrics.unique_state_count}")
print(f"Dominant state: {state_metrics.dominant_state_id}")
print(f"Dominant %: {state_metrics.dominant_state_percentage:.1f}%")
print(f"PASSES: {state_metrics.passes_standard_threshold}")

# Detect issues
issues = detect_static_state_issues(video_plan_ir)
print(f"\n=== Issues Detected ===")
for issue in issues:
    print(f"[{issue['severity']}] {issue['rule']}: {issue['message']}")
```

**Expected Output for FAIL_001:**
```
=== Consequence Analysis ===
Distinct consequences: 2
Total beats: 8
Distinct %: 25.0%
Longest gap: 9.3s at 3.2s-12.5s
PASSES: False

=== Static State Analysis ===
Unique states: 2
Dominant state: on_rough_mat
Dominant %: 42.0%
PASSES: False

=== Issues Detected ===
[CRITICAL] BEAT_004: Visual state 'on_rough_mat' occupies 42.0% of video. Maximum: 30%.
[WARNING] VISUAL_NOVELTY: Only 2 unique visual states. Recommend 4+ for engaging video.
```

## Visualization Support

Both analyzers provide methods for timeline visualization:

### Consequence Timeline
```python
from app.analyzer.consequence_analyzer import ConsequenceAnalyzer

analyzer = ConsequenceAnalyzer()
timeline = analyzer.get_consequence_timeline(video_plan_ir)

# Returns:
# [
#   {"time": 0.0, "type": "new", "action": "slides on floor", "isNew": true, "intensity": 8},
#   {"time": 1.0, "type": "continuation", "action": "tries corrective step", "isNew": false, "intensity": 6},
#   ...
# ]
```

### State Segments
```python
from app.analyzer.static_state_analyzer import StaticStateAnalyzer

analyzer = StaticStateAnalyzer()
segments = analyzer.get_state_segments(video_plan_ir)

# Returns:
# [
#   {
#     "stateId": "on_slippery_floor",
#     "startTime": 0.0,
#     "endTime": 3.2,
#     "duration": 3.2,
#     "percentage": 21.3,
#     "beatIds": ["beat_01", "beat_02"]
#   },
#   ...
# ]
```

## Integration with Rule Engine

These analyzers are used by the rule engine to evaluate specific rules:

```python
from app.analyzer.consequence_analyzer import analyze_consequences
from app.analyzer.static_state_analyzer import analyze_static_states


def evaluate_concept_006(video_plan_ir):
    """CONCEPT_006: Consequence Capacity"""
    metrics = analyze_consequences(video_plan_ir)

    if metrics.distinct_consequence_count < 4:
        return {
            "result": "FAIL",
            "severity": "BLOCKER",
            "message": f"Only {metrics.distinct_consequence_count} distinct visual consequences detected. Minimum: 4.",
        }
    elif metrics.distinct_consequence_count == 4:
        return {
            "result": "PASS",
            "severity": "WARNING",
            "message": "Exactly 4 consequences. Consider adding 1-2 more for stronger engagement.",
        }
    else:
        return {
            "result": "PASS",
            "severity": "PASS",
            "message": f"Sufficient consequence variety: {metrics.distinct_consequence_count} distinct consequences.",
        }


def evaluate_beat_004(video_plan_ir):
    """BEAT_004: Static State Dominance"""
    metrics = analyze_static_states(video_plan_ir)

    if metrics.dominant_state_percentage > 30:
        return {
            "result": "FAIL",
            "severity": "CRITICAL",
            "message": f"Visual state '{metrics.dominant_state_id}' occupies {metrics.dominant_state_percentage:.1f}% of video. Maximum: 30%.",
        }
    elif metrics.dominant_state_percentage > 25:
        return {
            "result": "PASS",
            "severity": "WARNING",
            "message": f"Visual state '{metrics.dominant_state_id}' occupies {metrics.dominant_state_percentage:.1f}% of video. Consider adding variation.",
        }
    else:
        return {
            "result": "PASS",
            "severity": "PASS",
            "message": f"Good visual state distribution. Max state: {metrics.dominant_state_percentage:.1f}%.",
        }
```

## Testing

```bash
cd ml-service
python -m pytest tests/analyzer/
```

See `tests/analyzer/test_consequence_analyzer.py` and `tests/analyzer/test_static_state_analyzer.py`.

## Performance

Both analyzers are O(n) where n = number of beats:
- Consequence analyzer: Single pass through beats
- Static state analyzer: Single pass + grouping operation

Typical performance:
- 8-10 beat video: <1ms
- 20 beat video: <2ms

No external dependencies beyond Python stdlib.
