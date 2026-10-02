# Pompom Ruleset v1.0 — Rule Definitions

All 22 rules from the conversation, formalized with YAML schema and implementation guidance.

## Rule Structure

```yaml
id: RULE_CODE
name: Human Readable Name
category: CONCEPT | BEAT | MOTION | STORY | FINAL | PROMPT | PLATFORM
severity: CRITICAL | HIGH | MEDIUM | LOW | INFO
evaluationType: CODE | LLM | HYBRID
evidenceLevel: THEORETICAL | OBSERVED | SUPPORTED | STRONGLY_SUPPORTED
active: true
description: |
  What this rule checks and why it matters.
parameters:
  paramName: value
threshold:
  min: 0.0
  max: 1.0
prompt: |
  (if evaluationType includes LLM)
  LLM evaluation prompt template
```

---

## Pre-Render Creative Rules

### CONCEPT_001: Immediate Visual Anomaly

```yaml
id: CONCEPT_001_IMMEDIATE_ANOMALY
name: Immediate Visual Anomaly
category: CONCEPT
severity: CRITICAL
evaluationType: HYBRID
evidenceLevel: STRONGLY_SUPPORTED
active: true
description: |
  The core concept anomaly must be visible within 0.5-0.8 seconds.
  
  Pass examples:
  - Giant spoon (immediately unusual)
  - Water flowing upward (physics violation visible)
  - Dirty hands (visual state clear)
  
  Fail example:
  - Door video (first frame looks like normal door)
  
  This is THE most important concept gate rule.
parameters:
  anomalyVisibleBeforeSec: 0.8
  soundOffRequired: true
threshold:
  minScore: 70.0
prompt: |
  Evaluate if the concept's core anomaly is immediately visible.
  
  Concept: {{conceptText}}
  
  Questions:
  1. Can a viewer understand "something is wrong/unusual" within 0.8 seconds?
  2. Is the anomaly visual (not dependent on sound or text)?
  3. Is the anomaly the PRIMARY focus, not a background detail?
  
  Score 0-100:
  - 90-100: Anomaly is instant and unmistakable
  - 70-89: Anomaly is clear within 0.8sec
  - 50-69: Anomaly takes 1-2 seconds to register
  - Below 50: Anomaly is subtle or delayed
  
  Return JSON: {"score": 0-100, "reason": "explanation"}
```

**Java Evaluator:**
```java
public RuleResult evaluate(ConceptValidationRequest request) {
    String concept = request.getConceptText().toLowerCase();
    
    // Positive signals
    boolean hasVisualAnomaly = 
        concept.contains("giant") || concept.contains("huge") ||
        concept.contains("tiny") || concept.contains("upside down") ||
        concept.contains("floating") || concept.contains("upward") ||
        concept.contains("dirty") || concept.contains("clean") ||
        concept.contains("reversed") || concept.contains("backward");
    
    // Negative signals
    boolean mightBeSubtle =
        concept.contains("slowly") || concept.contains("gradually") ||
        concept.contains("eventually") || concept.contains("later");
    
    if (!hasVisualAnomaly) {
        return RuleResult.fail("No immediate visual anomaly detected in concept");
    }
    
    if (mightBeSubtle) {
        return RuleResult.warn("Anomaly may be gradual rather than immediate");
    }
    
    return RuleResult.pass("Visual anomaly is immediate");
}
```

---

### CONCEPT_002: One Dominant Mechanic

```yaml
id: CONCEPT_002_ONE_DOMINANT_MECHANIC
name: One Dominant Mechanic
category: CONCEPT
severity: HIGH
evaluationType: LLM
evidenceLevel: SUPPORTED
active: true
description: |
  Video should have ONE clear physical/comedy rule.
  
  Good: WATER → DIRTY, SOAP → CLEAN
  
  Bad: 
  - One beat pulls
  - Other beat pushes
  - Then flies
  - Then grows
  
  Multiple mechanics dilute the concept.
parameters:
  maxDominantMechanics: 1
threshold:
  minScore: 60.0
prompt: |
  Count distinct physical or comedy mechanics in the concept.
  
  Concept: {{conceptText}}
  
  Examples of mechanics:
  - Size change (giant spoon)
  - Gravity reversal (water up)
  - State transfer (dirty/clean)
  - Unstoppable motion (runaway brush)
  
  How many DIFFERENT core mechanics are described?
  
  Score:
  - 1 mechanic: 100
  - 2 mechanics: 50
  - 3+ mechanics: 0
  
  Return JSON: {"mechanicCount": N, "mechanics": ["list"], "score": 0-100, "reason": "explanation"}
```

---

### CONCEPT_003: Consequence Capacity

```yaml
id: CONCEPT_003_CONSEQUENCE_CAPACITY
name: Consequence Capacity
category: CONCEPT
severity: HIGH
evaluationType: LLM
evidenceLevel: SUPPORTED
active: true
description: |
  The concept must naturally generate 3-4 meaningful consequences or attempts
  without feeling artificially extended.
  
  We do NOT enforce "must have exactly 4 verbs" - that over-constrains generation.
  
  Instead: can this concept naturally fill 15 seconds with progression?
parameters:
  minimumMeaningfulAttempts: 3
  preferredMeaningfulAttempts: 4
  hardMaximumNotRequired: true
threshold:
  minScore: 60.0
prompt: |
  Evaluate if the concept can naturally generate 3-4 meaningful progression points.
  
  Concept: {{conceptText}}
  
  Questions:
  1. Can you list 3-4 distinct things that would happen?
  2. Does each feel like a natural consequence, not forced repetition?
  3. Would the concept feel complete in 15 seconds, or rushed/padded?
  
  Score:
  - 80-100: Concept naturally generates 4+ rich progressions
  - 60-79: Concept can produce 3 solid progressions
  - 40-59: Concept feels thin, might need padding
  - Below 40: Concept is too simple, one-note
  
  Return JSON: {"potentialAttempts": ["list"], "score": 0-100, "reason": "explanation"}
```

---

### BEAT_001: Attempt Diversity

```yaml
id: BEAT_001_ATTEMPT_DIVERSITY
name: Attempt Diversity
category: BEAT
severity: HIGH
evaluationType: HYBRID
evidenceLevel: STRONGLY_SUPPORTED
active: true
description: |
  **Most important creative insight from analysis:**
  
  Old thinking: SAME RULE + DIFFERENT CONSEQUENCE
  New standard: SAME PROBLEM + DIFFERENT ATTEMPT + DIFFERENT CONSEQUENCE
  
  Example strong structure:
  POUR → ADD → STIR → DRINK → EMPTY
  
  Example weak structure:
  POUR → POUR → POUR → POUR (even if consequences vary)
  
  We do NOT require exactly 4 verbs or hardcode action lists.
  We DO penalize consecutive repetition of the same action.
parameters:
  maxConsecutiveSamePrimaryAction: 1
  maxDominantActionRatio: 0.55
threshold:
  minScore: 60.0
prompt: |
  Analyze action diversity in the concept.
  
  Concept: {{conceptText}}
  
  Extract the sequence of PRIMARY ACTIONS (verbs the character takes).
  
  Questions:
  1. Are there 2+ consecutive identical actions? (BAD)
  2. Does one action dominate >55% of the video? (WEAK)
  3. Are the attempts genuinely different problem-solving strategies?
  
  Score:
  - 90-100: Diverse, distinct solving strategies
  - 70-89: Good variety with minor repetition
  - 50-69: One action dominates or 2 consecutive repeats
  - Below 50: Repetitive structure
  
  Return JSON: {"actions": ["list"], "consecutiveRepeats": N, "dominantAction": "verb", "dominantRatio": 0.0-1.0, "score": 0-100, "reason": "explanation"}
```

**Java Evaluator:**
```java
public RuleResult evaluate(ConceptValidationRequest request, LLMAnalysis llmResult) {
    List<String> actions = llmResult.getActions();
    
    // Check consecutive repeats
    int consecutiveRepeats = 0;
    for (int i = 1; i < actions.size(); i++) {
        if (actions.get(i).equalsIgnoreCase(actions.get(i-1))) {
            consecutiveRepeats++;
        }
    }
    
    if (consecutiveRepeats > 1) {
        return RuleResult.fail("Too many consecutive repeated actions: " + consecutiveRepeats);
    }
    
    // Check dominant action ratio
    double dominantRatio = llmResult.getDominantRatio();
    if (dominantRatio > 0.55) {
        return RuleResult.warn("One action dominates " + (dominantRatio * 100) + "% of video");
    }
    
    return RuleResult.pass("Good attempt diversity");
}
```

---

### BEAT_002: Activity Is Not Progression

```yaml
id: BEAT_002_ACTIVITY_NOT_PROGRESSION
name: Activity Is Not Progression
category: BEAT
severity: CRITICAL
evaluationType: LLM
evidenceLevel: SUPPORTED
active: true
description: |
  **Direct lesson from Door video failure:**
  
  Characters moving ≠ story progressing
  
  Example fail:
  PUSH → MORE PUSH → MORE PEOPLE PUSHING
  (Activity increases, but solving strategy unchanged)
  
  New character entering does NOT automatically mean progression.
  
  Progression = new strategy OR new consequence.
parameters: {}
threshold:
  minScore: 70.0
prompt: |
  Evaluate if the concept shows true progression or just increased activity.
  
  Concept: {{conceptText}}
  
  For each described beat/action:
  1. Does it represent a NEW solving strategy?
  2. Does it produce a NEW type of consequence?
  3. Or is it just "more of the same with extra characters/force"?
  
  Red flags:
  - "they push harder"
  - "more friends join"
  - "they try again"
  - WITHOUT a strategy change
  
  Score:
  - 90-100: Clear progression with strategy evolution
  - 70-89: Decent progression with minor repetition
  - 50-69: Some beats are just "more activity"
  - Below 50: Mostly increased effort without strategy change
  
  Return JSON: {"progressionBeats": ["list"], "activityBeats": ["list"], "score": 0-100, "reason": "explanation"}
```

---

### BEAT_003: Story Detached Gap

```yaml
id: BEAT_003_STORY_DETACHED_GAP
name: Story Detached Gap
category: BEAT
severity: CRITICAL
evaluationType: CODE
evidenceLevel: SUPPORTED
active: true
description: |
  **From Door video's manzara section:**
  
  If the main problem is ongoing, there must NOT be unrelated scenic shots.
  
  Example fail:
  - Characters struggling with door
  - Cut to scenic landscape for 2 seconds
  - Back to door struggle
  
  Important distinction: this is NOT about motion absence.
  It's about STORY RELEVANCE absence.
  
  Allowed: character pause to think (0.5-0.8sec)
  Not allowed: detached scenery while problem is active
parameters:
  maxDetachedDurationSec: 0.5
threshold: {}
```

**Java Evaluator:**
```java
public RuleResult evaluate(ConceptValidationRequest request) {
    String concept = request.getConceptText().toLowerCase();
    
    // Red flags for detached elements
    boolean hasDetachedScenery =
        (concept.contains("landscape") || concept.contains("scenery") || 
         concept.contains("pan to") || concept.contains("cut to")) &&
        !concept.contains("relevant") && !concept.contains("related");
    
    boolean hasUnrelatedInsert =
        concept.contains("meanwhile") || concept.contains("elsewhere") ||
        concept.contains("unrelated");
    
    if (hasDetachedScenery || hasUnrelatedInsert) {
        return RuleResult.fail("Concept includes story-detached elements");
    }
    
    return RuleResult.pass("All elements are story-relevant");
}
```

---

### MOTION_001: Meaningful Motion

```yaml
id: MOTION_001_MEANINGFUL_MOTION
name: Meaningful Motion
category: MOTION
severity: HIGH
evaluationType: CODE
evidenceLevel: SUPPORTED
active: true
description: |
  **Softening of old "ZERO DEAD AIR" rule:**
  
  We NO LONGER require:
  - Hands moving EVERY frame
  - Next action starting 0.2sec before previous ends
  - Secondary motion always present
  
  These over-constrain AI generation and create unnatural choreography.
  
  New standard: CONTINUOUS MEANINGFUL PROGRESSION
  
  Allowed:
  - 0.7-1.0sec static reaction for educational word reading
  - Brief pause for fake win realization
  - Character looking/thinking without motion
  
  Not allowed:
  - 2+ seconds of no change while problem is active
  - Extended static holds with no story reason
parameters:
  staticReactionMaxSec: 0.8
  meaningfulChangePreferredEverySec: 1.5
threshold: {}
```

**Java Evaluator:**
```java
public RuleResult evaluate(ConceptValidationRequest request) {
    String concept = request.getConceptText().toLowerCase();
    
    // Red flags for dead air
    boolean hasLongPauses =
        concept.contains("long pause") || concept.contains("wait") ||
        concept.contains("static for") || concept.contains("freeze");
    
    // Allowed pauses
    boolean hasEducationalPause =
        concept.contains("reads") || concept.contains("learning") ||
        concept.contains("educational moment");
    
    boolean hasFakeWinPause =
        concept.contains("realizes") || concept.contains("fake win") ||
        concept.contains("brief celebration");
    
    if (hasLongPauses && !hasEducationalPause && !hasFakeWinPause) {
        return RuleResult.warn("Concept may include unmotivated static moments");
    }
    
    return RuleResult.pass("Motion/progression pacing is appropriate");
}
```

---

### STORY_001: Fake Resolution

```yaml
id: STORY_001_FAKE_RESOLUTION
name: Fake Resolution
category: STORY
severity: MEDIUM
evaluationType: LLM
evidenceLevel: SUPPORTED
active: true
description: |
  Fake win works well but we should NOT micro-manage its duration.
  
  Preferred range: 0.4-1.0 seconds
  
  Key rule: problem after fake win must be STRONGER than before.
parameters:
  preferredMinSec: 0.4
  preferredMaxSec: 1.0
  requireStrongerProblem: true
threshold:
  minScore: 50.0
prompt: |
  Check if the concept includes a fake resolution followed by escalation.
  
  Concept: {{conceptText}}
  
  Questions:
  1. Is there a moment where the problem seems solved?
  2. Does the problem return worse than before?
  3. Is the fake win duration appropriate (0.4-1.0 sec ideal)?
  
  Score:
  - 100: Perfect fake win → escalation
  - 70-99: Fake win present, minor issues
  - 40-69: Weak or missing fake win
  - Below 40: No tension release structure
  
  Return JSON: {"hasFakeWin": boolean, "escalationStrength": "weak|medium|strong", "score": 0-100, "reason": "explanation"}
```

---

### FINAL_001: New Consequence

```yaml
id: FINAL_001_NEW_CONSEQUENCE
name: Final New Consequence
category: FINAL
severity: HIGH
evaluationType: LLM
evidenceLevel: SUPPORTED
active: true
description: |
  Final must NOT be just a bigger version of the opening.
  
  Preferred: the rule's consequence we haven't seen yet.
  
  Good examples:
  - Dirty Mimi: single drop → re-dirty → FINAL SCRUB (new!)
  - Cup: refill → refill → BEYOND FULL FOUNTAIN (new!)
  
  Bad example:
  - Opening: spoon is big
  - Final: spoon is bigger (just more of same)
parameters:
  finalMustIntroduceNewConsequence: true
  finalIntensityMustBePeak: true
  hardCutMidMotionPreferred: true
threshold:
  minScore: 60.0
prompt: |
  Evaluate if the final moment introduces a new consequence.
  
  Concept: {{conceptText}}
  
  Questions:
  1. What is the opening consequence?
  2. What is the final consequence?
  3. Is the final a NEW type of consequence, or just "more" of the same?
  4. Is the final the PEAK intensity?
  
  Score:
  - 90-100: Final introduces genuinely new consequence at peak
  - 70-89: Final is strong but somewhat predictable
  - 50-69: Final is just "bigger" version of opening
  - Below 50: Final is weak or repetitive
  
  Return JSON: {"openingConsequence": "description", "finalConsequence": "description", "isNewType": boolean, "score": 0-100, "reason": "explanation"}
```

---

### LOOPABILITY_001: Loop Structure

```yaml
id: LOOPABILITY_001_LOOP_STRUCTURE
name: Loopability
category: FINAL
severity: MEDIUM
evaluationType: LLM
evidenceLevel: STRONGLY_SUPPORTED
active: true
description: |
  **Key insight from Meta export analysis:**
  
  15-16 second winner videos had 16-23 second average watch.
  This means: REPLAY.
  
  Loopability is now a separate quality dimension, equal to hookStrength and finalPayoff.
  
  Factors:
  - Final → opening continuity
  - Unfinished final action
  - No fade out
  - Camera continuity
  - Final motion connects to opening
  - Replay curiosity (does rule still apply?)
parameters: {}
threshold:
  minScore: 50.0
prompt: |
  Evaluate loopability potential.
  
  Concept: {{conceptText}}
  
  Questions:
  1. Does the final state naturally lead back to the opening?
  2. Is there an unfinished action at the end?
  3. Would a viewer be curious to watch again immediately?
  4. Does the concept create a natural cycle?
  
  Red flags for loops:
  - "Fade out"
  - "The end"
  - "Problem is solved permanently"
  - "Character walks away"
  
  Score:
  - 90-100: Perfect loop structure, final feeds opening
  - 70-89: Good loop potential with minor gaps
  - 50-69: Weak loop, some continuity
  - Below 50: Designed as one-time narrative
  
  Return JSON: {"loopQuality": "strong|medium|weak|none", "loopMechanism": "description", "score": 0-100, "reason": "explanation"}
```

---

### PROMPT_001: Over Constraint Risk

```yaml
id: PROMPT_001_OVER_CONSTRAINT
name: Over Constraint Risk
category: PROMPT
severity: HIGH
evaluationType: CODE
evidenceLevel: SUPPORTED
active: true
description: |
  **Key lesson: longer/more detailed prompt ≠ better video**
  
  Over-constrained prompts:
  - Excessive MUST statements
  - Excessive micro-timing (0.2sec choreography)
  - Frame-by-frame body-part direction
  - Too many guardrails for same action
  - Contradictions
  - Duplicate negative instructions
  
  Principle: **Concept gate strict, generation prompt lean**
parameters:
  maxMicroTimingRules: 6
  maxBodyPartChoreographyRules: 8
  maxMustStatements: 10
threshold: {}
```

**Java Evaluator:**
```java
public RuleResult evaluate(PromptText prompt) {
    String text = prompt.getText();
    
    // Count MUST statements
    int mustCount = countOccurrences(text, "MUST");
    
    // Count micro-timing references
    Pattern timingPattern = Pattern.compile("\\d+\\.\\d+\\s*(sec|seconds|s)");
    int microTimingCount = countMatches(text, timingPattern);
    
    // Count body-part choreography
    Pattern bodyPartPattern = Pattern.compile("(left hand|right hand|fingers|wrist|elbow|shoulder)");
    int bodyPartCount = countMatches(text, bodyPartPattern);
    
    List<String> warnings = new ArrayList<>();
    
    if (mustCount > 10) {
        warnings.add("Excessive MUST statements: " + mustCount);
    }
    
    if (microTimingCount > 6) {
        warnings.add("Excessive micro-timing rules: " + microTimingCount);
    }
    
    if (bodyPartCount > 8) {
        warnings.add("Excessive body-part choreography: " + bodyPartCount);
    }
    
    if (warnings.isEmpty()) {
        return RuleResult.pass("Prompt constraint level is appropriate");
    } else {
        return RuleResult.warn("Over-constraint detected: " + String.join(", ", warnings));
    }
}
```

---

## Post-Publish Performance Rules

### META_FB_001: Entry Proxy

```yaml
id: META_FB_001_ENTRY_PROXY
name: Facebook Entry Proxy
category: PLATFORM
platform: META_FACEBOOK
severity: INFO
evaluationType: CODE
evidenceLevel: OBSERVED
active: true
description: |
  3-second views / reach
  
  Account-observed thresholds (not algorithmic truth):
  - danger: <0.60
  - viable: 0.60-0.75
  - strong: >=0.75
  
  Examples:
  - Milk: ~49% (weak)
  - Carrot: ~71% (viable)
  - Kirli Mimi: ~79% (strong)
  - Sock: ~79.5% (strong)
  - Brush: ~80.6% (strong)
parameters:
  metric: "threeSecondViews / reach"
thresholds:
  danger: 0.60
  viable: 0.75
  strong: 0.80
```

---

### PERFORMANCE_001: Average Watch Ratio

```yaml
id: PERFORMANCE_001_AVG_WATCH_RATIO
name: Average Watch Ratio
category: PERFORMANCE
severity: HIGH
evaluationType: CODE
evidenceLevel: STRONGLY_SUPPORTED
active: true
description: |
  avgWatchSeconds / videoDurationSeconds
  
  Much more important than raw seconds.
  
  Thresholds:
  - good: >=0.90
  - replay_candidate: >=1.00
  - strong_replay: >=1.10
  - exceptional: >=1.20
  
  15-16 sec winners with >100% = strong replay signal
parameters:
  metric: "avgWatchSeconds / durationSeconds"
thresholds:
  good: 0.90
  replayCandidate: 1.00
  strongReplay: 1.10
  exceptional: 1.20
```

---

### PERFORMANCE_002: End Retention

```yaml
id: PERFORMANCE_002_END_RETENTION
name: End Retention
category: PERFORMANCE
severity: MEDIUM
evaluationType: CODE
evidenceLevel: OBSERVED
active: true
description: |
  Last interval retention (if available from export).
  
  Account-observed thresholds:
  - weak: <0.45
  - healthy: 0.45-0.55
  - strong: >=0.55
  
  Examples:
  - Milk: ~40% (weak)
  - Carrot: ~41% (weak)
  - Mimi: ~54% (healthy)
  - Brush: ~58% (strong)
  - Sock: ~60% (strong)
parameters:
  metric: "endRetentionRate"
thresholds:
  weak: 0.45
  healthy: 0.55
  strong: 0.60
```

---

### PERFORMANCE_003: Replay Proxy

```yaml
id: PERFORMANCE_003_REPLAY_PROXY
name: Replay Proxy (Views Per Viewer)
category: PERFORMANCE
severity: HIGH
evaluationType: CODE
evidenceLevel: SUPPORTED
active: true
description: |
  views / uniqueViewers
  
  Historical examples:
  - Brush: ~2.9
  - Sock: ~3.5
  
  Thresholds:
  - strong: >=2.0
  - exceptional: >=3.0
parameters:
  metric: "views / uniqueViewers"
thresholds:
  strong: 2.0
  exceptional: 3.0
```

---

### VELOCITY_001: Wave Detection

```yaml
id: VELOCITY_001_WAVE_DETECTION
name: Velocity Wave Detection
category: PERFORMANCE
severity: INFO
evaluationType: CODE
evidenceLevel: SUPPORTED
active: true
description: |
  Analyze velocity patterns from snapshot series.
  
  Snapshots:
  - T+30m, T+1h, T+2h, T+3h, T+4h, T+6h, T+12h, T+24h, T+48h, T+7d
  
  Calculate:
  - viewsPerHour
  - deltaViews
  - acceleration
  - deceleration
  
  Classifications:
  - EARLY_REJECTION
  - EARLY_PLATEAU
  - STRONG_START
  - SECOND_WAVE
  - THIRD_WAVE
  - DELAYED_BREAKOUT
  - MULTI_WAVE
  - TAIL
  - PERSISTENT_WINNER
  - EVERGREEN_BREAKOUT
  
  Examples:
  - Kirli Mimi: STRONG_START → SECOND_WAVE → TAIL
  - Sock: MEDIUM_START → DELAYED_ACCELERATION → MULTI_WAVE
  - Brush: NIGHT_TEST → BREAKOUT → TAIL
parameters: {}
```

---

### REACH_FURTHER_001: Observation Only

```yaml
id: REACH_FURTHER_001_OBSERVATION
name: Reach Further Observation
category: PLATFORM
platform: META_FACEBOOK
severity: INFO
evaluationType: CODE
evidenceLevel: OBSERVED
active: true
description: |
  **CRITICAL: This is NOT a quality score component.**
  
  Reach Further is a state observation, not a winner badge.
  
  We track:
  - reachFurtherObserved: boolean
  - firstObservedAt: timestamp
  - lastObservedAt: timestamp
  
  But we do NOT use it for scoring.
parameters:
  trackStateOnly: true
  includeInScore: false
```

---

### GEOGRAPHY_001: Regional Analysis

```yaml
id: GEOGRAPHY_001_REGIONAL_ANALYSIS
name: Geographic Distribution Analysis
category: PERFORMANCE
severity: INFO
evaluationType: CODE
evidenceLevel: OBSERVED
active: true
description: |
  Track country-level performance.
  
  Key metric: US share delta (Meta pattern shows US rising significantly)
  
  Store:
  - countryShare.US
  - countryShare.UK
  - countryShare.MX
  - etc.
  
  Calculate:
  - USShareDelta7d
  - USShareDelta30d
  
  Two separate scores:
  - engagementQuality (how people interact)
  - monetizationValue (geographic CPM implications)
  
  High engagement in one country ≠ automatically high monetization value.
parameters:
  trackCountries: ["US", "UK", "CA", "AU", "MX", "BR", "IN"]
  separateEngagementAndMonetization: true
```

---

### TIKTOK_001: Platform-Specific Evaluation

```yaml
id: TIKTOK_001_EVALUATION
name: TikTok Performance Evaluation
category: PLATFORM
platform: TIKTOK
severity: INFO
evaluationType: CODE
evidenceLevel: OBSERVED
active: true
description: |
  **Key lesson: high average watch ≠ winner**
  
  TikTok metrics:
  - views trajectory
  - completion
  - average watch ratio
  - followers / 1000 views
  - likes / 1000
  - comments / 1000
  - shares / 1000
  - saves / 1000
  - wave count
  
  TikTok Studio warning "Most viewers stopped at 0:02" is INFO severity.
  
  Kirli Mimi had this warning but got 3.7K views → not auto-fail.
parameters:
  dropPointWarningIsCritical: false
  dropPointWarningSeverity: INFO
```

---

## Dimension Scores

All videos analyzed get scored on these dimensions (0-100 each):

```yaml
dimensions:
  hookStrength:
    description: "How quickly the anomaly grabs attention"
    weight: 1.2
  
  progression:
    description: "Quality of story/consequence progression"
    weight: 1.0
  
  attemptDiversity:
    description: "Variety of problem-solving attempts"
    weight: 1.0
  
  educationalClarity:
    description: "Is the learning point clear (if educational)"
    weight: 0.8
  
  aiProducibility:
    description: "Can AI reliably produce this concept"
    weight: 1.0
  
  finalPayoff:
    description: "Final moment delivers new peak consequence"
    weight: 1.0
  
  loopability:
    description: "Does final flow back to opening for replay"
    weight: 1.0
```

**Overall Quality Score:**
```
overallQuality = weightedAverage(dimensionScores)
```

---

## Content Intent Classification

```yaml
contentIntents:
  GROWTH:
    description: "Maximize reach, non-follower views, replay"
    benchmarks:
      META_FB:
        views: 20000
        entryProxy: 0.75
        avgWatchRatio: 1.0
    
  EDUCATIONAL:
    description: "Profile quality, learning, follower trust"
    benchmarks:
      META_FB:
        views: 2000
        entryProxy: 0.60
        avgWatchRatio: 0.85
    
  EXPERIMENT:
    description: "Test new format/concept/character"
    benchmarks:
      META_FB:
        views: 1000
        entryProxy: 0.50
        note: "Lower bar, data gathering phase"
    
  STOCK:
    description: "Content library, not optimized for viral"
    benchmarks:
      META_FB:
        views: 500
        note: "Acceptable baseline"
```

**DO NOT compare EDUCATIONAL videos to GROWTH benchmarks.**

---

## Evidence Levels

Every rule tracks its evidence strength:

```yaml
evidenceLevels:
  THEORETICAL:
    description: "Hypothesis, not yet tested in production"
    autoActivate: false
    requiresApproval: true
  
  OBSERVED:
    description: "Seen in limited data (1-3 examples)"
    autoActivate: false
    requiresApproval: true
  
  SUPPORTED:
    description: "Consistent across multiple examples (4-10)"
    autoActivate: false
    requiresApproval: true
  
  STRONGLY_SUPPORTED:
    description: "Repeatedly validated (10+ examples)"
    autoActivate: false
    requiresApproval: true
```

**Golden rule: correlation → candidate rule → human review → production**

NEVER auto-activate rules from correlation alone.

---

## Rule Versioning

When updating a rule:

```yaml
- Create new version with incremented rule_code (e.g., CONCEPT_001 → CONCEPT_001_V2)
- Mark old version as active: false
- Preserve old version for historical analysis
- All RuleEvaluation records reference specific rule version
```

This allows:
- Regression testing (compare old vs new rule on golden set)
- Historical analysis (why did concept X pass in Jan but fail in Mar?)
- Safe rollback

---

## Implementation Priority

1. **CONCEPT_001** — Immediate Anomaly (most critical gate)
2. **ContentIntent** — classification system
3. **BEAT_001** — Attempt Diversity
4. **BEAT_002** — Activity Not Progression
5. **BEAT_003** — Story Detached Gap
6. **FINAL_001** — New Consequence
7. **LOOPABILITY_001** — Loop Structure
8. **PERFORMANCE_001** — Avg Watch Ratio
9. **PERFORMANCE_003** — Replay Proxy
10. **VELOCITY_001** — Wave Detection

Then layer in remaining rules progressively.
