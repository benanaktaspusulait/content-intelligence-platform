# Auto-Fix Module

The auto-fix module implements iterative prompt improvement workflow using quality validation feedback.

## Architecture

```
Initial Prompt
     ↓
[Validate] → QualityReport
     ↓
[Auto-Fix] → Modified Prompt
     ↓
[Validate] → QualityReport
     ↓
[Regression Check] → Decision (ACCEPT/REVISE/REJECT)
     ↓
   Loop (max iterations) or Complete
```

## Components

### `prompt_fixer.py`
Core auto-fix engine that applies rule-specific transformations to prompts based on priority_fixes from QualityReport.

**Key Methods:**
- `apply_fix()` - Applies single fix to prompt based on rule_id
- `fix_concept_006()` - Adds consequences to reach minimum threshold
- `fix_beat_004()` - Reduces dominant visual state duration
- `fix_repetition_002()` - Breaks action repetition patterns
- `fix_repetition_003()` - Breaks A-B-C cycle patterns

### `iteration_loop.py`
Orchestrates multi-iteration improvement workflow with regression checking.

**Workflow:**
1. Validate initial prompt
2. If not RENDER_READY, apply top priority fix
3. Re-validate fixed prompt
4. Check for regressions (RegressionChecker)
5. If ACCEPT: commit fix and continue
6. If REVISE: try next priority fix
7. If REJECT: rollback to previous version
8. Repeat until RENDER_READY or max iterations

**Parameters:**
- `max_iterations` - Default 5, prevents infinite loops
- `min_improvement_threshold` - Minimum score increase to accept fix (default 2.0)
- `allow_score_plateau` - Accept fix if score stable but fixes critical issues

## Fix Strategies

### CONCEPT_006 (Consequence Insufficiency)
**Problem:** <4 distinct consequences  
**Strategy:**
1. Identify existing consequences
2. Generate N new consequences that:
   - Are thematically related to existing narrative
   - Create visual variety
   - Maintain character consistency
   - Don't break existing good beats

**Implementation:** Insert new beats between existing ones, interpolate timing

### BEAT_004 (Static State Dominance)
**Problem:** Single visual state >30% timeline  
**Strategy:**
1. Identify dominant state and duration
2. Split long static sections into 2-3 sub-states with visual variety
3. Add transitional actions between static moments
4. Preserve consequence count

**Implementation:** Parse dominant state beats, inject micro-actions

### REPETITION_002 (Action Repetition)
**Problem:** Same action repeats 3+ times without escalation  
**Strategy:**
1. Detect repeated action pattern
2. On 3rd+ occurrence, replace with escalation or break pattern
3. Ensure each repetition has meaningful consequence change

**Implementation:** Pattern matching, replace 3rd beat with contrasting action

### REPETITION_003 (Cycle Repetition)
**Problem:** A-B-C cycle repeats 3x  
**Strategy:**
1. Detect A-B-C cycle using similarity thresholds
2. On 3rd cycle, inject unexpected outcome (D)
3. Break cycle structure while maintaining theme

**Implementation:** Cycle detection via beat similarity clustering, inject novelty

## Safety Features

### Regression Prevention
- Every fix is validated against previous version
- Critical regressions (PASS→BLOCKER/CRITICAL) trigger rollback
- Score drops >5pts without rule improvements trigger review

### Content Preservation
- Character identity unchanged (name, personality traits)
- World/setting consistency maintained
- Core learning objective preserved
- Duration constraints respected (15s)

### Iteration Limits
- Max 5 iterations default (configurable)
- Diminishing returns detection (3 consecutive fixes with <1pt improvement)
- Circular fix detection (same rule fails repeatedly)

## Usage

```python
from app.autofix.iteration_loop import AutoFixIterationLoop

loop = AutoFixIterationLoop(ruleset_version="1.0", max_iterations=5, min_improvement_threshold=2.0)

result = loop.run(prompt_text)

print(f"Status: {result.final_status}")
print(f"Score: {result.initial_score} → {result.final_score}")
print(f"Iterations: {result.iteration_count}")
print(f"Fixes applied: {len(result.applied_fixes)}")
print(f"Final prompt:\n{result.final_prompt}")
```

## Output

`AutoFixResult` dataclass:
- `final_prompt` - Improved prompt text
- `final_report` - Final QualityReport
- `initial_score` / `final_score` - Score trajectory
- `iteration_count` - Number of fix iterations
- `applied_fixes` - List of successful fixes with details
- `rejected_fixes` - List of fixes that caused regressions
- `improvement_history` - Score progression per iteration

## Limitations (Phase 1)

1. **Text-only fixes:** Parser v1 is regex-based, so fixes are string manipulations
2. **No semantic understanding:** Doesn't understand narrative coherence deeply
3. **Fixed templates:** Fix strategies are rule-based, not creative
4. **No multi-fix coordination:** Applies one fix at a time sequentially

## Phase 2 Enhancements

1. **LLM-powered fixes:** Use GPT-4 to generate semantically coherent improvements
2. **Multi-fix optimization:** Try multiple fix combinations in parallel
3. **Style preservation:** Learn and maintain writer's voice/style
4. **A/B testing:** Generate multiple fixed versions, pick best
5. **Feedback loop integration:** Learn from actual video performance (Task #18)

## Performance

- Single fix application: <20ms
- Full iteration loop (5 iterations): <500ms
- Regression check per iteration: <5ms
- Total throughput: ~2 prompts/second

## Testing

See `ml-service/tests/test_autofix_loop.py` for comprehensive test suite covering:
- All fix strategies
- Regression detection
- Iteration limits
- Content preservation
- Edge cases (empty prompts, perfect prompts, unfixable prompts)
