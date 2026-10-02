# Golden Test Suite

**Regression prevention system for Pompom Ruleset Engine**

## Purpose

Every time a rule is added, modified, or parameters are tuned, run the golden test suite.

Expected results are frozen. If a ruleset change causes a regression (positive concept now fails, or negative concept now passes), the change must be reviewed.

---

## Positive Examples (MUST PASS)

### GOLDEN_POS_001: Giant Spoon

```yaml
id: GOLDEN_POS_001
name: Giant Spoon
category: POSITIVE
conceptText: |
  Giant spoon that gets bigger with every pour.
  Kiko pours water, spoon grows.
  Adds ingredient, spoon grows more.
  Stirs, spoon is now huge.
  Tries to drink, spoon too big for mouth.
  Final: spoon fills entire kitchen.
expectedApproved: true
expectedScore:
  min: 85.0
  max: 100.0
expectedPassingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY
  - CONCEPT_002_ONE_DOMINANT_MECHANIC
  - CONCEPT_003_CONSEQUENCE_CAPACITY
  - BEAT_001_ATTEMPT_DIVERSITY
  - FINAL_001_NEW_CONSEQUENCE
  - LOOPABILITY_001_LOOP_STRUCTURE
notes: |
  This is THE canonical winner. If this fails validation, something is very wrong.
  
  Strengths:
  - Immediate visual (giant spoon)
  - One rule (size growth)
  - Diverse actions (pour, add, stir, drink)
  - New final (fills kitchen, not seen before)
  - Strong loop (can start again with new pour)
```

---

### GOLDEN_POS_002: Kirli Mimi (Clean/Dirty)

```yaml
id: GOLDEN_POS_002
name: Kirli Mimi Clean/Dirty
category: POSITIVE
conceptText: |
  Mimi has dirty hands. Water makes them dirtier. Soap cleans them.
  
  Opening: Mimi's hands are dirty.
  Beat 1: Tries to wash with water - hands get MORE dirty.
  Beat 2: Looks at hands, confused.
  Beat 3: Uses soap - hands become clean.
  Beat 4: Touches dirty surface - hands dirty again.
  Final: Major scrub with soap, water splashing.
expectedApproved: true
expectedScore:
  min: 90.0
  max: 100.0
expectedPassingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY
  - CONCEPT_002_ONE_DOMINANT_MECHANIC
  - BEAT_001_ATTEMPT_DIVERSITY
  - STORY_001_FAKE_RESOLUTION
  - FINAL_001_NEW_CONSEQUENCE
  - LOOPABILITY_001_LOOP_STRUCTURE
performanceBenchmark:
  platform: META_FACEBOOK
  views: 31000
  avgWatchRatio: 1.12
  entryProxy: 0.79
  endRetention: 0.54
  classification: STRONG
notes: |
  Proven winner with actual performance data.
  
  Key pattern: WATER → DIRTY, SOAP → CLEAN (one rule, two states)
  Fake win: hands clean → dirty again
  Final: escalated scrub (new intensity)
  Perfect loopability: dirty again → need to wash
```

---

### GOLDEN_POS_003: Runaway Toothbrush

```yaml
id: GOLDEN_POS_003
name: Runaway Toothbrush
category: POSITIVE
conceptText: |
  Toothbrush that won't stop moving once started.
  
  Opening: Arda activates electric toothbrush.
  Beat 1: Brush starts moving in hand.
  Beat 2: Brush pulls away, moving on its own.
  Beat 3: Arda chases it around bathroom.
  Beat 4: Brush zooms under sink, over counter.
  Final: Brush spinning wildly in mid-air, Arda lunging.
expectedApproved: true
expectedScore:
  min: 85.0
  max: 100.0
expectedPassingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY
  - CONCEPT_002_ONE_DOMINANT_MECHANIC
  - BEAT_001_ATTEMPT_DIVERSITY
  - MOTION_001_MEANINGFUL_MOTION
  - FINAL_001_NEW_CONSEQUENCE
performanceBenchmark:
  platform: META_FACEBOOK
  views: 28000
  avgWatchRatio: 1.08
  classification: STRONG
notes: |
  One mechanic: unstoppable motion.
  Diverse attempts: hold, chase, lunge, etc.
  Final: mid-air spin (new escalation)
```

---

### GOLDEN_POS_004: Giant Sock

```yaml
id: GOLDEN_POS_004
name: Giant Sock
category: POSITIVE
conceptText: |
  Sock that grows every time Noah tries to put it on.
  
  Opening: Normal sock in hand.
  Beat 1: Pulls sock onto foot - sock grows.
  Beat 2: Pulls higher - sock grows more, past knee.
  Beat 3: Keeps pulling - sock now body-length.
  Beat 4: Struggles with giant sock.
  Final: Sock is room-sized, Noah tangled inside.
expectedApproved: true
expectedScore:
  min: 85.0
  max: 95.0
expectedPassingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY
  - CONCEPT_002_ONE_DOMINANT_MECHANIC
  - BEAT_001_ATTEMPT_DIVERSITY
  - FINAL_001_NEW_CONSEQUENCE
  - LOOPABILITY_001_LOOP_STRUCTURE
performanceBenchmark:
  platform: META_FACEBOOK
  views: 26500
  avgWatchRatio: 1.14
  viewsPerViewer: 3.5
  entryProxy: 0.795
  classification: STRONG
notes: |
  Exceptional replay signal (views/viewer = 3.5)
  One rule: size growth with action
  Strong loopability: can try again with new sock
```

---

### GOLDEN_POS_005: Water Flows Upward

```yaml
id: GOLDEN_POS_005
name: Water Flows Upward
category: POSITIVE
conceptText: |
  In Opa's lab, water flows up instead of down.
  
  Opening: Opa pours water from pitcher - water goes UP.
  Beat 1: Water floats to ceiling.
  Beat 2: Opa tries to catch it with cup from below - misses.
  Beat 3: Climbs on stool, holds cup above.
  Beat 4: Water flows up into cup.
  Final: Entire ceiling covered in floating water globules.
expectedApproved: true
expectedScore:
  min: 85.0
  max: 95.0
expectedPassingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY
  - CONCEPT_002_ONE_DOMINANT_MECHANIC
  - BEAT_001_ATTEMPT_DIVERSITY
  - BEAT_002_ACTIVITY_NOT_PROGRESSION
  - FINAL_001_NEW_CONSEQUENCE
notes: |
  Physics violation (gravity reversed)
  Progression: pour → miss → climb → catch → globules (each is new strategy)
  Final: ceiling full (new consequence, not just "more up")
```

---

### GOLDEN_POS_006: Table/Ceiling Switch

```yaml
id: GOLDEN_POS_006
name: Table Ceiling Switch
category: POSITIVE
conceptText: |
  Objects on table fall to ceiling instead of floor.
  
  Opening: Luca places ball on table, ball rolls off.
  Beat 1: Ball floats up and sticks to ceiling.
  Beat 2: Places cup on table edge - cup falls up.
  Beat 3: Tries to catch falling-up objects.
  Beat 4: Multiple objects floating to ceiling.
  Final: Entire table's contents now on ceiling, Luca looking up.
expectedApproved: true
expectedScore:
  min: 80.0
  max: 95.0
expectedPassingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY
  - CONCEPT_002_ONE_DOMINANT_MECHANIC
  - BEAT_001_ATTEMPT_DIVERSITY
  - FINAL_001_NEW_CONSEQUENCE
notes: |
  Clear physics rule reversal.
  Multiple object types = consequence variety, not mechanic variety.
  Final: complete inversion (new scale)
```

---

## Negative Examples (MUST FAIL or WARN)

### GOLDEN_NEG_001: Door Push

```yaml
id: GOLDEN_NEG_001
name: Door Push Failure
category: NEGATIVE
conceptText: |
  Characters try to open a stuck door.
  
  Opening: Kiko pushes door, doesn't open.
  Beat 1: Kiko pushes harder.
  Beat 2: Mimi joins, both push.
  Beat 3: Arda joins, all three push.
  Beat 4: Cut to scenic landscape for 2 seconds.
  Beat 5: Back to door, everyone pushing.
  Final: Door finally opens.
expectedApproved: false
expectedScore:
  max: 50.0
expectedFailingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY  # Door looks normal initially
  - BEAT_002_ACTIVITY_NOT_PROGRESSION  # More pushing ≠ new strategy
  - BEAT_003_STORY_DETACHED_GAP  # Scenic landscape = detached
  - FINAL_001_NEW_CONSEQUENCE  # Door opens = predictable
notes: |
  Multiple failure modes:
  1. No immediate visual anomaly (door looks normal)
  2. Activity increase without progression (push → push harder → more people push)
  3. Story-detached scenic insert
  4. Final is expected resolution, not new consequence
  
  This is THE canonical failure case from actual production.
```

---

### GOLDEN_NEG_002: Backpack Weight

```yaml
id: GOLDEN_NEG_002
name: Backpack Weight
category: NEGATIVE
conceptText: |
  Backpack gets heavier as items are added.
  
  Opening: Sofia puts book in backpack.
  Beat 1: Backpack feels heavier.
  Beat 2: Adds pencil case, heavier still.
  Beat 3: Adds lunch box, very heavy now.
  Beat 4: Struggles to lift backpack.
  Final: Backpack too heavy to carry.
expectedApproved: false
expectedScore:
  max: 40.0
expectedFailingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY  # Weight is not visually immediate
  - BEAT_001_ATTEMPT_DIVERSITY  # Just keeps adding, same action
  - FINAL_001_NEW_CONSEQUENCE  # "Too heavy" is just MORE, not NEW
notes: |
  Fails because:
  1. Weight change is not visually immediate (need to see struggle)
  2. Repetitive action: add → add → add
  3. Linear escalation without new consequence type
  
  This is NOT a physics violation viewers can see instantly.
```

---

### GOLDEN_NEG_003: Growing Carrot

```yaml
id: GOLDEN_NEG_003
name: Growing Carrot (slow growth)
category: NEGATIVE
conceptText: |
  Carrot slowly grows bigger while character watches.
  
  Opening: Tiny carrot on plate.
  Beat 1: Carrot grows slightly.
  Beat 2: Character looks surprised.
  Beat 3: Carrot grows more.
  Beat 4: Character reaches for it.
  Beat 5: Carrot is now medium-sized.
  Final: Carrot fills plate.
expectedApproved: false
expectedScore:
  max: 50.0
expectedFailingRules:
  - BEAT_001_ATTEMPT_DIVERSITY  # Character is passive, no varied attempts
  - BEAT_002_ACTIVITY_NOT_PROGRESSION  # Growth is gradual, not distinct beats
  - MOTION_001_MEANINGFUL_MOTION  # Character mostly static/watching
notes: |
  Fails because:
  1. Character is passive (watching growth, not attempting solutions)
  2. No attempt diversity (look → reach is weak)
  3. Gradual change without distinct progression beats
  
  Actual production showed weak performance.
```

---

### GOLDEN_NEG_004: Milk Pouring Execution

```yaml
id: GOLDEN_NEG_004
name: Milk Pouring (execution issue)
category: NEGATIVE
conceptText: |
  Milk pours but fills glass in reverse (bottom to top).
  
  Opening: Kiko pours milk from carton.
  Beat 1: Milk stream visible, glass starts filling from bottom.
  Beat 2: Milk continues to fill upward.
  Beat 3: Glass is half full, filling continues.
  Beat 4: Glass nearly full.
  Final: Glass completely full, Kiko drinks.
expectedApproved: false
expectedScore:
  max: 45.0
expectedFailingRules:
  - BEAT_001_ATTEMPT_DIVERSITY  # One continuous action: POUR
  - BEAT_002_ACTIVITY_NOT_PROGRESSION  # No strategy change, just continued pour
  - FINAL_001_NEW_CONSEQUENCE  # "Full glass" is just completion, not new
notes: |
  Concept might seem okay (reverse fill is unusual), but execution failed:
  1. Entire video is ONE action: continuous pour
  2. No attempt diversity
  3. No progression beats, just process completion
  
  Actual video performance was weak (~3K views).
```

---

### GOLDEN_NEG_005: Slippery vs Rough (Educational)

```yaml
id: GOLDEN_NEG_005
name: Slippery vs Rough Surfaces
category: NEGATIVE
intent: EDUCATIONAL
conceptText: |
  Kiko explores slippery vs rough surfaces.
  
  Opening: Kiko slides toy on smooth table - slides far.
  Beat 1: Tries same on rough carpet - stops immediately.
  Beat 2: Learns "smooth = slippery, rough = grip"
  Beat 3: Tries balloon on smooth - slides.
  Beat 4: Tries balloon on rough - sticks.
  Final: Educational moment showing word "FRICTION"
expectedApproved: false
expectedScore:
  max: 55.0
expectedFailingRules:
  - CONCEPT_002_ONE_DOMINANT_MECHANIC  # Two mechanics: slippery AND rough
  - BEAT_001_ATTEMPT_DIVERSITY  # Repetitive: slide smooth → slide rough → repeat
  - LOOPABILITY_001_LOOP_STRUCTURE  # Educational conclusion = no loop
notes: |
  Educational intent but structural issues:
  1. Two opposing mechanics (slippery, rough) instead of one
  2. A-B comparison structure = repetitive
  3. Educational conclusion breaks loopability
  
  Educational videos have lower benchmarks, but structure still matters.
  
  **Important: If intent=EDUCATIONAL, score against EDUCATIONAL benchmarks,
  not GROWTH benchmarks.**
```

---

### GOLDEN_NEG_006: Sharp vs Blunt (Educational)

```yaml
id: GOLDEN_NEG_006
name: Sharp vs Blunt Tools
category: NEGATIVE
intent: EDUCATIONAL
conceptText: |
  Arda learns about sharp and blunt edges.
  
  Opening: Arda tries to cut paper with blunt scissors - doesn't cut.
  Beat 1: Switches to sharp scissors - cuts easily.
  Beat 2: Tries blunt knife on playdough - struggles.
  Beat 3: Sharp knife cuts smoothly.
  Beat 4: Educational word "SHARP" appears.
  Final: Shows safety message about sharp objects.
expectedApproved: false
expectedScore:
  max: 50.0
expectedFailingRules:
  - CONCEPT_002_ONE_DOMINANT_MECHANIC  # Two mechanics: sharp vs blunt
  - BEAT_001_ATTEMPT_DIVERSITY  # Repetitive A-B comparison
  - FINAL_001_NEW_CONSEQUENCE  # Safety message = didactic ending
  - LOOPABILITY_001_LOOP_STRUCTURE  # Message ending = no loop
notes: |
  Same structural issue as Slippery/Rough:
  1. Comparison structure (A vs B)
  2. Two opposing mechanics
  3. Educational conclusion
  
  Even with EDUCATIONAL intent, these structural weaknesses hurt engagement.
```

---

### GOLDEN_NEG_007: Old vs New (Educational)

```yaml
id: GOLDEN_NEG_007
name: Old vs New Items
category: NEGATIVE
intent: EDUCATIONAL
conceptText: |
  Opa compares old and new versions of objects.
  
  Opening: Old book (worn) vs new book (pristine).
  Beat 1: Old toy (broken) vs new toy (working).
  Beat 2: Old shoe (scuffed) vs new shoe (shiny).
  Beat 3: Educational moment: "OLD → time and use"
  Final: Message about taking care of belongings.
expectedApproved: false
expectedScore:
  max: 40.0
expectedFailingRules:
  - CONCEPT_001_IMMEDIATE_ANOMALY  # Comparison is conceptual, not visually immediate
  - CONCEPT_002_ONE_DOMINANT_MECHANIC  # State comparison, not a single rule
  - BEAT_001_ATTEMPT_DIVERSITY  # Just showing pairs, no attempts
  - LOOPABILITY_001_LOOP_STRUCTURE  # Message ending
notes: |
  Weakest of the educational concepts tested:
  1. No immediate visual hook (comparison is abstract)
  2. No character attempting anything (just showing examples)
  3. Static presentation format
  
  Even EDUCATIONAL content needs character agency and visual hooks.
```

---

## Test Execution

### Automated Test Flow

```java
@Test
void testGoldenSuite() {
    List<GoldenTestCase> goldenCases = goldenTestRepository.findAll();
    
    for (GoldenTestCase testCase : goldenCases) {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText(testCase.getConceptText())
            .intent(testCase.getIntent())
            .build();
        
        ConceptValidationResponse response = validationService.validate(request);
        
        // Check approval expectation
        assertEquals(testCase.getExpectedApproved(), response.isApproved(),
            "Test case " + testCase.getTestName() + " approval mismatch");
        
        // Check score range (if specified)
        if (testCase.getExpectedMinScore() != null) {
            assertTrue(response.getOverallScore() >= testCase.getExpectedMinScore(),
                "Test case " + testCase.getTestName() + " score too low");
        }
        
        if (testCase.getExpectedMaxScore() != null) {
            assertTrue(response.getOverallScore() <= testCase.getExpectedMaxScore(),
                "Test case " + testCase.getTestName() + " score too high");
        }
        
        // Check specific rules
        if (testCase.getExpectedFailingRules() != null) {
            for (String ruleCode : testCase.getExpectedFailingRules()) {
                RuleResult result = response.getRuleResults().stream()
                    .filter(r -> r.getRuleCode().equals(ruleCode))
                    .findFirst()
                    .orElseThrow();
                
                assertFalse(result.isPassed(),
                    "Test case " + testCase.getTestName() + 
                    " expected rule " + ruleCode + " to fail");
            }
        }
    }
}
```

### Regression Detection

When a rule change is proposed:

1. Run golden suite with CURRENT ruleset → baseline results
2. Apply rule change
3. Run golden suite with NEW ruleset → new results
4. Compare:
   - Any POSITIVE case now fails? → **REGRESSION**
   - Any NEGATIVE case now passes? → **REGRESSION**
   - Score shifts >10 points? → **REVIEW REQUIRED**

If regression detected, require human review and explanation before merge.

---

## Maintenance

### Adding New Golden Cases

When a video performs exceptionally well or poorly:

1. Extract concept text
2. Record actual performance metrics
3. Add to golden suite with appropriate expectations
4. Run regression test
5. Commit if no regressions

### Updating Expectations

If a rule legitimately changes (e.g., evidence level upgraded), expectations may need adjustment:

1. Document WHY expectation is changing
2. Update golden case
3. Re-run full suite
4. Verify no unintended regressions

---

## Coverage Goals

Golden suite should cover:

- ✅ All critical concept patterns (size growth, physics violation, state transfer, unstoppable motion)
- ✅ All major failure modes (no anomaly, activity≠progression, detached elements, repetitive actions)
- ✅ Different content intents (GROWTH, EDUCATIONAL)
- ✅ Both immediate hooks and delayed hooks
- ✅ Both loopable and conclusion-based structures
- ✅ Multi-wave vs early-rejection patterns

Current coverage: **13 cases** (6 positive, 7 negative)

Target: **20+ cases** as more patterns emerge

---

## Performance Benchmarks in Tests

Some golden cases include actual performance data.

These benchmarks are NOT used to fail/pass validation (validation is pre-render).

They ARE used to:
1. Validate that performance rules correctly classify actual results
2. Train correlation detection in learning engine
3. Build evidence for rule strength

Example:

```java
@Test
void testPerformanceRulesAgainstGolden() {
    GoldenTestCase goldenCase = goldenTestRepository.findByName("Kirli Mimi");
    
    PerformanceMetrics actualMetrics = PerformanceMetrics.builder()
        .views(31000L)
        .avgWatchRatio(1.12)
        .entryProxy(0.79)
        .build();
    
    PerformanceScore score = performanceService.analyze(actualMetrics);
    
    assertEquals("STRONG", score.getClassification());
    assertTrue(score.getLoopabilityScore() >= 90.0);
}
```

This ensures performance rules stay calibrated to real-world winner patterns.
