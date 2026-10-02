# Pompom Creative Quality Engine - Usage Guide

**Step-by-step guide for content creators and developers**

---

## Table of Contents

1. [For Content Creators](#for-content-creators)
2. [For Developers](#for-developers)
3. [Common Workflows](#common-workflows)
4. [Interpreting Results](#interpreting-results)
5. [Best Practices](#best-practices)
6. [FAQ](#faq)

---

## For Content Creators

### Workflow 1: Validate Before Rendering

**Goal:** Check if your prompt is ready for production before spending time on rendering.

#### Step 1: Write Your Prompt

Create a 15-second video prompt following the standard format:

```markdown
## Title
Kiko's Colorful Discovery

## Duration
15 seconds

## Characters
- Kiko: Curious, energetic, creative

## Timeline
0.0-2.0 SEC: Kiko — spots a colorful box in the park
2.0-5.0 SEC: Kiko — opens the box and gasps in surprise
5.0-8.0 SEC: Kiko — pulls out rainbow ribbons that float
8.0-11.0 SEC: Kiko — twirls with the ribbons creating patterns
11.0-15.0 SEC: Kiko — throws ribbons up, they form a rainbow arch
```

#### Step 2: Validate via UI

1. Open Angular dashboard: `http://localhost:4200/quality-validator`
2. Paste your prompt into the textarea
3. Click **"Validate Prompt"**
4. Wait 2-3 seconds for analysis

#### Step 3: Read the Report

**Score Card:**
- **85/100 (GOOD)** → Ready for production ✅
- **68/100 (WEAK, BLOCKED)** → Needs fixes ❌
- **77/100 (ACCEPTABLE, NEEDS_REVISION)** → Minor improvements needed ⚠️

**Status Meanings:**
- **RENDER_READY** (92+, no blockers): Go ahead and render!
- **NEEDS_REVISION** (80-91): Apply suggested fixes
- **BLOCKED** (<80 or blockers>0): Major issues, rewrite needed

#### Step 4: Apply Fixes

**Option A: Auto-Fix (Recommended)**
1. Click **"Auto-Fix"** button
2. System will try 5 iterations to improve the prompt
3. Review the improved version
4. Copy and use for rendering

**Option B: Manual Fix**
1. Read "Priority Fixes" section
2. Most important fixes are listed first
3. Follow recommendations:
   - "Add 1 more consequence" → Insert new beat with novel outcome
   - "Reduce static state from 42% to <30%" → Add variety to visual states
   - "Break repetition after 2nd occurrence" → Change 3rd repeated action

#### Step 5: Re-Validate

After making changes:
1. Paste updated prompt
2. Click "Validate" again
3. Confirm score improved
4. Repeat until RENDER_READY

---

### Workflow 2: Diagnose a Failed Video

**Goal:** Understand why a rendered video performed poorly.

#### Step 1: Locate Original Prompt

Find the prompt used for the failed video in your production files.

#### Step 2: Validate the Prompt

Run it through the quality engine and note the score + failed rules.

#### Step 3: Compare with Successful Videos

- Failed video: Score 65, BLOCKED, 2 blockers
- Successful video: Score 88, RENDER_READY, 0 blockers

Identify which rules the failed video broke that successful ones passed.

#### Step 4: Learn the Pattern

Example findings:
- **Failed:** Only 3 consequences, 45% static state
- **Successful:** 5+ consequences, max 28% static state

Apply this learning to future prompts.

---

### Workflow 3: Batch Validation

**Goal:** Validate multiple prompts at once to prioritize which to render first.

#### Via API (requires curl/Postman):

```bash
curl -X POST http://localhost:8080/api/quality/validateBatch \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": [
      {"id": "prompt_001", "text": "## Title\n..."},
      {"id": "prompt_002", "text": "## Title\n..."},
      {"id": "prompt_003", "text": "## Title\n..."}
    ]
  }'
```

#### Response:

```json
{
  "results": [
    {"id": "prompt_001", "score": 92, "status": "RENDER_READY"},
    {"id": "prompt_002", "score": 78, "status": "NEEDS_REVISION"},
    {"id": "prompt_003", "score": 65, "status": "BLOCKED"}
  ]
}
```

**Action:** Render prompt_001 first, fix prompt_002, rewrite prompt_003.

---

## For Developers

### Setup Development Environment

#### 1. Python ML Service

```bash
cd ml-service

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
python tests/test_failed_cases.py
python tests/test_autofix_loop.py

# Start service
uvicorn app.api.quality:app --reload --port 8000
```

#### 2. Spring Boot Backend

```bash
cd backend

# Build
./mvnw clean package

# Run
./mvnw spring-boot:run

# Or run JAR
java -jar target/pompom-intelligence-1.0.0.jar
```

#### 3. PostgreSQL Database

```bash
# Start PostgreSQL
docker run --name pompom-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=pompom_intelligence \
  -p 5432:5432 \
  -d postgres:15

# Run migrations
./mvnw flyway:migrate

# Verify
psql -d pompom_intelligence -c "SELECT * FROM quality_validations LIMIT 5;"
```

#### 4. Angular Frontend

```bash
cd frontend

# Install
npm install

# Run dev server
ng serve --port 4200

# Build for production
ng build --configuration production
```

---

### Extending the System

#### Add a New Rule

**1. Define Rule in YAML (`data/rules/RULESET_X.Y.yaml`):**

```yaml
- id: "MY_NEW_RULE_001"
  name: "My New Quality Check"
  family: "concept_strength"
  severity: "WARNING"
  description: "Checks for specific pattern"
  measurement:
    type: "beat_count"
    threshold:
      min: 5
```

**2. Implement Evaluator (`ml-service/app/rules/rule_engine.py`):**

```python
def evaluate_my_new_rule_001(self, ir: Dict) -> RuleEvaluation:
    """Evaluate MY_NEW_RULE_001: minimum beat count"""
    beat_count = len(ir['timeline'])
    threshold = 5
    
    result = beat_count >= threshold
    severity = "WARNING"
    
    message = (
        f"Beat count: {beat_count} (minimum {threshold})"
        if result
        else f"Insufficient beats: {beat_count} (need {threshold}+)"
    )
    
    return RuleEvaluation(
        rule_id="MY_NEW_RULE_001",
        family="concept_strength",
        severity=severity,
        result=result,
        message=message,
        actual_value=beat_count,
        threshold_value=threshold
    )
```

**3. Register in Rule Engine:**

```python
self.evaluators = {
    # ... existing rules ...
    'MY_NEW_RULE_001': self.evaluate_my_new_rule_001,
}
```

**4. Add Fix Strategy (`ml-service/app/autofix/prompt_fixer.py`):**

```python
def fix_my_new_rule_001(self, prompt, fix, ir):
    """Fix MY_NEW_RULE_001: add more beats"""
    # Implementation
    return FixResult(...)
```

**5. Test:**

```python
def test_my_new_rule():
    prompt = "..."  # Test prompt
    result = parse_prompt(prompt)
    ir = result["videoPlanIR"]
    
    engine = RuleEngine("data/rules/RULESET_X.Y.yaml")
    report = engine.evaluate(ir)
    
    my_rule_eval = [e for e in report.evaluations if e.rule_id == "MY_NEW_RULE_001"][0]
    assert my_rule_eval.result == False  # Should fail
```

#### Adjust Rule Thresholds

**Scenario:** Videos with 30-32% static state are performing well, current threshold (30%) too strict.

**1. Analyze Performance Data:**

```python
from app.feedback.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer()
insights = analyzer.analyze_performance_data(performance_data)

print(f"False negatives: {insights.false_negatives}")
# Output: False negatives: 12 (videos blocked but performed GOOD)
```

**2. Propose Adjustment:**

```python
from app.feedback.rule_learner import RuleLearner

learner = RuleLearner(min_samples=50)
adjustments = learner.learn_from_performance(performance_data, "1.0")

for adj in adjustments:
    if adj.rule_id == "BEAT_004":
        print(f"{adj.rule_id}: {adj.current_value}% → {adj.proposed_value}%")
        print(f"Confidence: {adj.confidence:.0%}")
        print(f"Requires approval: {adj.requires_approval}")
```

**3. Create New Ruleset Version:**

Edit `data/rules/RULESET_1.1.yaml`:

```yaml
- id: "BEAT_004"
  # ... other fields ...
  measurement:
    threshold:
      max_percentage: 35  # Changed from 30
```

Update `data/rules/versions.yaml`:

```yaml
- version: "1.1"
  release_date: "2026-10-01"
  description: "Relaxed BEAT_004 threshold based on performance data"
  changes:
    - rule_id: "BEAT_004"
      change_type: "THRESHOLD_ADJUST"
      old_value: 30
      new_value: 35
      reason: "12 false negatives - videos with 30-35% static state performing well"
```

**4. Deploy and Monitor:**

```bash
# Test new version
python tests/test_failed_cases.py --ruleset 1.1

# Deploy
git add data/rules/RULESET_1.1.yaml data/rules/versions.yaml
git commit -m "Release RULESET 1.1: relaxed BEAT_004 threshold"
git push

# Monitor
curl http://localhost:8080/api/quality/rulesets/1.1
```

---

## Common Workflows

### Developer Workflow: Debug Failed Test

**Symptom:** `test_failed_cases.py` failing on FAIL_001

```bash
python tests/test_failed_cases.py
# Output: AssertionError: Expected BEAT_004 to fail, but it passed
```

**Debug Steps:**

1. **Read the test prompt:**

```python
test_file = Path("data/test_cases/FAIL_001_KIKO_STATIC_STATE_DOMINANCE.md")
with open(test_file) as f:
    prompt = f.read()
print(prompt)
```

2. **Parse and inspect IR:**

```python
from app.parser.prompt_parser import parse_prompt

result = parse_prompt(prompt)
ir = result["videoPlanIR"]

# Check static state analysis
from app.analyzer.static_state_analyzer import StaticStateAnalyzer

analyzer = StaticStateAnalyzer()
metrics = analyzer.analyze(ir['timeline'])

print(f"Dominant state: {metrics.dominant_state}")
print(f"Percentage: {metrics.state_percentages[metrics.dominant_state]:.1f}%")
```

3. **Manually evaluate rule:**

```python
from app.rules.rule_engine import RuleEngine

engine = RuleEngine("data/rules/RULESET_1.0.yaml")
report = engine.evaluate(ir)

beat_004 = [e for e in report.evaluations if e.rule_id == "BEAT_004"][0]
print(f"BEAT_004 result: {beat_004.result}")
print(f"Message: {beat_004.message}")
```

4. **Fix the bug:** Adjust parser, analyzer, or rule logic based on findings.

### Content Creator Workflow: Iterative Refinement

**Goal:** Take a BLOCKED prompt to RENDER_READY through iterations.

**Initial Prompt:** Score 65, BLOCKED

**Iteration 1: Add Consequences**
- Fix: Add 2 new beats with novel consequences
- Result: Score 72, NEEDS_REVISION (CONCEPT_006 now passes)

**Iteration 2: Reduce Static State**
- Fix: Split longest static beat into 2 sub-actions
- Result: Score 81, NEEDS_REVISION (BEAT_004 now passes)

**Iteration 3: Improve Escalation**
- Fix: Increase intensity values for later beats
- Result: Score 88, NEEDS_REVISION (ESCALATION_004 now passes)

**Iteration 4: Enhance Payoff**
- Fix: Make final beat more dramatic and unique
- Result: Score 93, RENDER_READY ✅

**Learning:** Most prompts need 2-4 iterations to reach RENDER_READY.

---

## Interpreting Results

### Score Ranges

| Score | Label | Meaning | Action |
|-------|-------|---------|--------|
| 92-100 | Excellent | Top-tier creative structure | Render immediately |
| 80-91 | Good | Solid structure, minor issues | Quick fixes or proceed |
| 70-79 | Acceptable | Functional but improvable | Apply fixes recommended |
| 60-69 | Weak | Significant structural gaps | Major revision needed |
| 0-59 | Poor | Critical failures | Rewrite from scratch |

### Rule Severities

**BLOCKER** 🚫
- Prompt CANNOT be rendered
- Must be fixed before proceeding
- Examples: Insufficient consequences (<4), very high complexity

**CRITICAL** ⚠️
- Serious quality issue
- High risk of poor performance
- Examples: Static state >30%, action repetition 3x

**WARNING** ⚠️
- Moderate quality issue
- May hurt performance
- Examples: Novelty gap >4.5s, flat progression

**PASS** ✅
- Rule satisfied
- No action needed

### Family Scores

Each of the 11 quality families contributes to overall score:

**High Impact Families (>15% weight):**
- **Concept Strength (20%):** Consequence capacity, clarity
- **Visual Novelty (18%):** Distinct outcomes, state variety
- **Hook Strength (15%):** Opening engagement

**Medium Impact (10-15%):**
- **Escalation (12%):** Intensity progression
- **Progression (10%):** Narrative arc
- **Motion Quality (10%):** Continuous action

**Low Impact (<10%):**
- **Readability, Producibility, Consistency, Payoff, Render Risk**

**Interpretation:**
- Low Concept Strength score → Add more consequences
- Low Visual Novelty score → Reduce repetition/static state
- Low Hook Strength score → Improve opening beat
- Low Escalation score → Increase intensity progression

### Timeline Visualization

**Intensity Curve (Blue Line):**
- Should trend upward from left to right
- Peak should be at end (final payoff)
- Flat line = PROGRESSION_005 warning

**Visual State Blocks (Background):**
- Each color = different visual state
- Red border = state dominates >30%
- Many small blocks = good variety

**Consequence Markers (Green Lines):**
- Solid green = new consequence
- Dashed gray = repeat consequence
- Even distribution preferred
- Large gap = NOVELTY_001 warning

---

## Best Practices

### For Content Creators

1. **Start with 4+ Consequences**
   - Minimum requirement for CONCEPT_006
   - Aim for 5-6 for flexibility

2. **Vary Visual States**
   - No single state >30% of timeline
   - Change location, position, action every 3-4 seconds

3. **Escalate Intensity**
   - Start calm (intensity 3-5)
   - Build to peak (intensity 8-10)
   - End with payoff

4. **Hook in First 2 Seconds**
   - Mid-action start
   - Visual surprise
   - Clear without sound

5. **Use Auto-Fix First**
   - Let system try automatic improvements
   - Review suggested fixes
   - Manually adjust for creative intent

### For Developers

1. **Read Before Writing**
   - Check existing rules before adding new ones
   - Avoid duplicate logic

2. **Test with Real Prompts**
   - Use FAIL_001/002/003 as regression tests
   - Add new test cases for new rules

3. **Document Decisions**
   - Every rule threshold should have rationale
   - Link to failed cases that motivated the rule

4. **Version Conservatively**
   - Patch (X.Y.1): Threshold tweaks <10%
   - Minor (X.1.0): New rules, weight adjustments
   - Major (2.0.0): Breaking changes only

5. **Monitor Performance**
   - Track prediction accuracy weekly
   - Adjust thresholds if false positive/negative rate >15%

---

## FAQ

### Q: Why is my good prompt scoring low?

**A:** Common causes:
1. **Insufficient consequences** - Need 4+ distinct outcomes
2. **Static state dominance** - One state >30% of timeline
3. **Flat intensity** - No escalation toward payoff
4. **Weak hook** - First 2 seconds not engaging

Run validator and check "Failed Rules" section for specifics.

### Q: Can I override a BLOCKED status?

**A:** Yes, but not recommended. BLOCKED means:
- Score <80 OR
- 1+ BLOCKER rules failed

Rendering may technically succeed but video will likely perform poorly. If you believe the validator is wrong:
1. Override and render anyway
2. Record performance feedback
3. System will learn from the misprediction

### Q: How accurate is the validator?

**A:** Current metrics (RULESET 1.0):
- **Validation accuracy:** 100% on known failed cases
- **False positive rate:** <10% (estimated, needs performance data)
- **False negative rate:** <5% (estimated)
- **Prediction-performance correlation:** r>0.6 (target)

Accuracy improves as system learns from more video performance data.

### Q: Why did auto-fix not reach RENDER_READY?

**A:** Phase 1 auto-fix has limitations:
- Template-based fixes only
- No semantic understanding
- Can't rewrite entire narrative

Some prompts have structural problems requiring human creativity. Auto-fix aims for 60→75 improvement, not 60→95.

Phase 2 (LLM-powered) will handle complex rewrites.

### Q: How often should rules be updated?

**A:** Update triggers:
- **Monthly:** Review performance data, propose adjustments
- **Quarterly:** Release new minor version if 50+ samples support change
- **Annually:** Major version with breaking changes if needed

Avoid over-tuning (<50 samples or <3 months between changes).

### Q: Can I use this for non-15-second videos?

**A:** Current system optimized for 15-second shorts. For other durations:
- **Adjustments needed:** Beat count thresholds, novelty gap timing, state dominance %
- **Core principles same:** Consequence capacity, visual variety, escalation

Contact dev team for multi-duration support (Phase 2 feature).

---

## Getting Help

### Report Issues
- **GitHub Issues:** File bug reports with prompt text (anonymized)
- **Slack:** #pompom-quality-engine channel
- **Email:** eng-team@pompomhills.com

### Request Features
- New quality families
- Platform-specific rules (YouTube vs TikTok)
- Integration with rendering pipeline
- Performance dashboards

### Office Hours
- **When:** Every Tuesday 2-3 PM
- **Where:** Zoom (link in Slack)
- **Topics:** Rule adjustments, troubleshooting, feature planning

---

**Version:** 1.0  
**Last Updated:** September 14, 2026  
**Maintained by:** Pompom Hills Engineering Team
