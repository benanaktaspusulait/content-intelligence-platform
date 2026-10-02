# Quality Family Rule Schemas

## Overview

The Creative Quality Engine evaluates prompts across **11 quality families**. Each family has:
- **Score range:** 0–100
- **Minimum threshold:** Pass/fail cutoff
- **Weight:** Contribution to overall score
- **Severity levels:** BLOCKER, CRITICAL, WARNING, PASS

**Philosophy:** Rules enforce **positive qualities** rather than just detecting errors.

---

## Quality Families

### 1. Concept Strength

**What it measures:** Whether the core idea can sustain 15 seconds of engaging content.

```yaml
family: concept_strength
weight: 0.12
minimum_threshold: 85

criteria:
  - name: consequence_capacity
    description: Core mechanic can generate 4+ visually distinct consequences
    measurement: Count unique physical outcomes from the mechanic
    pass_threshold: 4
    weight: 0.35
    
  - name: concept_clarity
    description: Single dominant mechanic (not multiple competing rules)
    measurement: Count of distinct physical rules introduced
    pass_threshold: 1
    weight: 0.25
    
  - name: concept_unusualness
    description: Problem is unusual enough to stop scrolling
    measurement: Subjective rating 1-5 (or learned from performance data)
    pass_threshold: 3
    weight: 0.20
    
  - name: teaching_contrast_sufficiency
    description: If pedagogical, contrast is rich enough for 15s
    measurement: For two-state contrast (sharp/blunt), flag as insufficient
    pass_threshold: true
    weight: 0.20

scoring:
  excellent: 90-100  # Novel concept, 6+ consequences, single clear rule
  good: 80-89        # Solid concept, 4-5 consequences, clear rule
  acceptable: 70-79  # Workable concept, 3-4 consequences, mostly clear
  weak: 60-69        # Thin concept, 2-3 consequences, needs work
  failing: 0-59      # Insufficient concept, <2 consequences

severity_rules:
  - if consequence_capacity < 4: BLOCKER
  - if concept_clarity > 1: CRITICAL
  - if teaching_contrast_sufficiency == false: WARNING
```

**Implementation status (RULESET 1.1):** A new criterion not originally speced here,
`attempt_count`, is implemented as `ATTEMPT_001` — tier-aware minimum count of beats
with `isAttempt == true` (3 for short tier, 7 for long tier).

---

### 2. Hook Strength

**What it measures:** Whether the opening stops scrolling and establishes the problem immediately.

```yaml
family: hook_strength
weight: 0.12
minimum_threshold: 85

criteria:
  - name: starts_mid_action
    description: No setup, problem visible in frame 1
    measurement: Boolean check of hook.startsMidAction
    pass_threshold: true
    weight: 0.30
    
  - name: visual_strength
    description: Anomaly is visually striking (not subtle)
    measurement: hook.visualStrength rating 1-5
    pass_threshold: 4
    weight: 0.30
    
  - name: sound_off_clarity
    description: Problem understandable without audio
    measurement: Boolean check of hook.soundOffClear
    pass_threshold: true
    weight: 0.25
    
  - name: immediate_engagement
    description: Hook duration is brief (< 1.5s to establish problem)
    measurement: Time from 0s to first consequence
    pass_threshold: <= 1.5
    weight: 0.15

scoring:
  excellent: 90-100  # Mid-action start, striking visual, sound-off clear, <1s
  good: 80-89        # Mid-action, clear visual, sound-off OK, <1.5s
  acceptable: 70-79  # Mostly immediate, visible problem, slight setup
  weak: 60-69        # Slow start or weak visual or audio-dependent
  failing: 0-59      # No hook, slow intro, or unclear problem

severity_rules:
  - if not starts_mid_action: CRITICAL
  - if visual_strength < 3: WARNING
  - if not sound_off_clarity: WARNING
```

**Implementation status (RULESET 1.1):** `starts_mid_action` + `visual_strength` are
implemented as `HOOK_002` (First Frame Anomaly). `sound_off_clarity` is implemented as
`HOOK_003` (Sound Independence). `immediate_engagement` remains unimplemented.

---

### 3. Visual Novelty

**What it measures:** How much genuinely new visual information appears throughout the video.

```yaml
family: visual_novelty
weight: 0.14
minimum_threshold: 80

criteria:
  - name: distinct_consequence_count
    description: Number of materially different visual consequences
    measurement: Count beats where isNewConsequence == true
    pass_threshold: 5
    weight: 0.35
    
  - name: static_state_duration
    description: No single visual state dominates (< 30% of video)
    measurement: Max % duration of any visualStateId
    pass_threshold: <= 30
    weight: 0.25
    
  - name: novelty_timeline_distribution
    description: New consequences spread across timeline, not clustered
    measurement: Longest gap without new consequence
    pass_threshold: <= 4.5s
    weight: 0.20
    
  - name: action_repetition_frequency
    description: Same action doesn't appear 3+ times without variation
    measurement: Count of most frequent action
    pass_threshold: <= 2
    weight: 0.20

scoring:
  excellent: 90-100  # 6+ consequences, <25% static, even distribution
  good: 80-89        # 5 consequences, <30% static, good distribution
  acceptable: 70-79  # 4 consequences, <35% static, some gaps
  weak: 60-69        # 3 consequences, <40% static, noticeable gaps
  failing: 0-59      # <3 consequences or >40% static state

severity_rules:
  - if distinct_consequence_count < 4: BLOCKER
  - if static_state_duration > 30: CRITICAL
  - if action_repetition_frequency > 2: CRITICAL
  - if novelty_timeline_distribution > 5: WARNING
```

**Implementation status (RULESET 1.1):** A new criterion not originally speced here,
`distinct_attempts`, is implemented as `ATTEMPT_002` — attempts sharing an identical
`primaryVerb` are an automatic deterministic fail; verb-distinct attempts are checked
for semantic duplication via LLM. This is a stricter, attempt-focused companion to the
existing `action_repetition_frequency` criterion (REPETITION_002), not a replacement.

---

### 4. Progression

**What it measures:** Whether the video builds logically from problem → attempts → escalation → payoff.

```yaml
family: progression
weight: 0.11
minimum_threshold: 85

criteria:
  - name: narrative_arc_present
    description: Clear problem → reaction → attempt → escalation structure
    measurement: Validate beat sequence has logical flow
    pass_threshold: true
    weight: 0.35
    
  - name: beat_dependency
    description: Each beat follows logically from previous
    measurement: Check if beat[n] consequence enables beat[n+1] action
    pass_threshold: >= 70% of beats
    weight: 0.30
    
  - name: false_resolution_present
    description: Includes fake win before final twist (if applicable)
    measurement: Boolean check for consequenceType == "fake_win"
    pass_threshold: optional but bonus
    weight: 0.15
    
  - name: middle_stagnation
    description: Middle section (4-11s) shows progression, not repetition
    measurement: Check consequence novelty in middle beats
    pass_threshold: >= 2 new consequences in middle
    weight: 0.20

scoring:
  excellent: 90-100  # Strong arc, tight dependencies, fake win, active middle
  good: 80-89        # Clear arc, good dependencies, active middle
  acceptable: 70-79  # Visible arc, most beats connected, some middle stagnation
  weak: 60-69        # Weak arc, loose dependencies, stagnant middle
  failing: 0-59      # No arc, disconnected beats, repetitive middle

severity_rules:
  - if not narrative_arc_present: CRITICAL
  - if beat_dependency < 60%: WARNING
  - if middle_stagnation fails: WARNING
```

**Implementation status (RULESET 1.1):** `false_resolution_present` is implemented as
`PAYOFF_002` (non-blocking bonus, matching this schema's `pass_threshold: optional but
bonus`). A new criterion not originally speced here, `active_character_ratio`, is
implemented as `CHAR_002` — the character must be actively attempting a solution for at
least 50% (short tier) or 60% (long tier) of the runtime. `narrative_arc_present` and
`beat_dependency` remain unimplemented.

---

### 5. Escalation

**What it measures:** Whether intensity builds toward a peak, avoiding drops or plateaus.

```yaml
family: escalation
weight: 0.10
minimum_threshold: 80

criteria:
  - name: intensity_trajectory
    description: Intensity generally increases (allows brief dips for contrast)
    measurement: Analyze beat.intensity timeline
    pass_threshold: upward trend with R² > 0.5
    weight: 0.40
    
  - name: no_major_drops
    description: Intensity doesn't drop >3 points except before final escalation
    measurement: Detect drops in intensity sequence
    pass_threshold: max_drop <= 3
    weight: 0.25
    
  - name: peak_at_end
    description: Highest intensity in final 3 seconds
    measurement: max(intensity) in beats 12-15s
    pass_threshold: true
    weight: 0.20
    
  - name: middle_plateau_avoidance
    description: Middle section (4-11s) doesn't flatline in intensity
    measurement: Variance of intensity in middle beats
    pass_threshold: variance > 2
    weight: 0.15

scoring:
  excellent: 90-100  # Steady rise, peak at end, no major drops, active middle
  good: 80-89        # Generally rising, peak near end, small dips OK
  acceptable: 70-79  # Mostly rising, peak present, some plateau
  weak: 60-69        # Flat or declining stretches, peak weak or early
  failing: 0-59      # No escalation, drops mid-video, peak absent

severity_rules:
  - if intensity_trajectory R² < 0.3: CRITICAL
  - if no_major_drops fails: WARNING
  - if not peak_at_end: WARNING
```

---

### 6. Motion Quality

**What it measures:** Whether motion is continuous, meaningful, and advances the story.

```yaml
family: motion_quality
weight: 0.09
minimum_threshold: 85

criteria:
  - name: continuous_meaningful_motion
    description: Motion reveals, changes, escalates or resolves the problem
    measurement: Check beat.motionAmount != "none" and action advances story
    pass_threshold: >= 90% of beats
    weight: 0.40
    
  - name: no_dead_air
    description: No beat has motionAmount == "none" for >1.5s
    measurement: Find longest static beat
    pass_threshold: <= 1.5s
    weight: 0.25
    
  - name: motion_readability_balance
    description: Motion active but not chaotic (readable state duration >= 0.6s)
    measurement: Check beat.isReadable == true for all beats
    pass_threshold: 100%
    weight: 0.20
    
  - name: cosmetic_vs_functional
    description: Motion is functional (advances plot), not just cosmetic (head turns)
    measurement: Subjective or keyword check (avoid "tiny", "small", "slight")
    pass_threshold: >= 80% functional
    weight: 0.15

scoring:
  excellent: 90-100  # All motion meaningful, no dead air, readable, functional
  good: 80-89        # Mostly meaningful, minimal dead air, readable
  acceptable: 70-79  # Generally active, some cosmetic motion, mostly readable
  weak: 60-69        # Noticeable dead air or cosmetic motion dominance
  failing: 0-59      # Significant dead air or chaotic unreadable motion

severity_rules:
  - if continuous_meaningful_motion < 80%: CRITICAL
  - if no_dead_air fails: WARNING
  - if motion_readability_balance < 90%: WARNING
```

**Implementation status (RULESET 1.1):** `no_dead_air` is implemented as `MOTION_001`.
`continuous_meaningful_motion`, `motion_readability_balance`, and
`cosmetic_vs_functional` remain unimplemented.

---

### 7. Readability

**What it measures:** Whether key moments are held long enough to be understood (especially for education).

```yaml
family: readability
weight: 0.08
minimum_threshold: 85

criteria:
  - name: minimum_beat_duration
    description: Each beat >= 0.6s (especially learning word states)
    measurement: Check all beat.duration values
    pass_threshold: >= 0.6s for all beats
    weight: 0.35
    
  - name: learning_word_visibility
    description: Learning words held >= 0.8s with clear visual
    measurement: Check beats with dialogue.isLearningWord == true
    pass_threshold: >= 0.8s
    weight: 0.30
    
  - name: consequence_clarity
    description: Physical consequences are visually obvious (not subtle)
    measurement: Keyword check in consequence descriptions (avoid "slightly", "barely")
    pass_threshold: 90% clear
    weight: 0.20
    
  - name: visual_dialogue_alignment
    description: Dialogue matches visible action (sound-off reinforcement)
    measurement: Check dialogue timing aligns with visualState
    pass_threshold: 100%
    weight: 0.15

scoring:
  excellent: 90-100  # All beats readable, learning words clear, consequences obvious
  good: 80-89        # Beats readable, learning words good, mostly clear
  acceptable: 70-79  # Most beats readable, learning words adequate
  weak: 60-69        # Some beats too brief, learning words rushed
  failing: 0-59      # Many beats unreadable, learning words unclear

severity_rules:
  - if minimum_beat_duration fails: CRITICAL
  - if learning_word_visibility < 0.8s: CRITICAL
  - if consequence_clarity < 80%: WARNING
```

---

### 8. AI Producibility

**What it measures:** Whether the video is technically feasible to render with current AI video models.

```yaml
family: ai_producibility
weight: 0.10
minimum_threshold: 80

criteria:
  - name: overall_complexity_acceptable
    description: Prompt doesn't require "very_high" complexity
    measurement: Check producibility.overallComplexity
    pass_threshold: != "very_high"
    weight: 0.30
    
  - name: high_risk_factor_count
    description: Limit simultaneous high-risk operations per beat
    measurement: Count risk factors per beat (hand-object, morph, liquid, etc.)
    pass_threshold: <= 2 per beat
    weight: 0.25
    
  - name: character_consistency_maintainable
    description: Character doesn't deform, duplicate, or change costume
    measurement: Check for multi-character coordination, costume changes
    pass_threshold: true
    weight: 0.20
    
  - name: physics_simplicity
    description: Physics is simple and predictable (not complex cloth/liquid)
    measurement: Keyword check for "liquid", "fabric", "complex physics"
    pass_threshold: true
    weight: 0.15
    
  - name: camera_stability
    description: Camera is stable or simple (no complex rotation/tracking)
    measurement: Check for camera cuts, rotations, tracking shots
    pass_threshold: true
    weight: 0.10

scoring:
  excellent: 90-100  # Low/medium complexity, <2 risk factors, simple physics
  good: 80-89        # Medium complexity, some risk factors, manageable
  acceptable: 70-79  # Medium-high complexity, several risk factors
  weak: 60-69        # High complexity, many risk factors, uncertain outcome
  failing: 0-59      # Very high complexity, multiple simultaneous risks

severity_rules:
  - if overall_complexity == "very_high": BLOCKER
  - if high_risk_factor_count > 3 in any beat: CRITICAL
  - if not character_consistency_maintainable: CRITICAL
```

**Implementation status (RULESET 1.1):** A new criterion not originally speced here,
`prop_economy`, is implemented as `PRODUCIBILITY_002` — tier-aware maximum main-prop
count (2 for short tier, 4 for long tier).

---

### 9. Consistency

**What it measures:** Whether objects, characters, physics, and environment remain stable.

```yaml
family: consistency
weight: 0.07
minimum_threshold: 90

criteria:
  - name: character_identity_locked
    description: Character appearance unchanged throughout
    measurement: Check for explicit locks in character description
    pass_threshold: true
    weight: 0.30
    
  - name: object_stability
    description: Main props don't duplicate, disappear, or morph unexpectedly
    measurement: Count of props, check for "SAME pencil throughout"
    pass_threshold: true
    weight: 0.25
    
  - name: physics_rule_consistency
    description: Physical rules established in hook remain consistent
    measurement: Check coreMechanic.consistency == "consistent"
    pass_threshold: true
    weight: 0.25
    
  - name: environment_stability
    description: Background/location doesn't change mid-video
    measurement: Check for location changes in beat descriptions
    pass_threshold: true
    weight: 0.20

scoring:
  excellent: 95-100  # All locked, no drift, consistent physics
  good: 90-94        # Minor cosmetic variations acceptable
  acceptable: 85-89  # Mostly consistent, small inconsistencies
  weak: 70-84        # Noticeable inconsistencies
  failing: 0-69      # Major consistency breaks

severity_rules:
  - if not character_identity_locked: CRITICAL
  - if not object_stability: CRITICAL
  - if physics_rule_consistency != "consistent": WARNING
```

**Implementation status (RULESET 1.1):** `character_identity_locked` is implemented as
`CONSISTENCY_002` (Character Continuity Lock), extending `CharacterVerifier` to sample
first/middle/last frame via vision LLM. This rule requires a rendered video and reports
`UNKNOWN` (not a pass or fail) at the pure-text concept stage, before any video exists —
it is not a pre-render check like the other rules in this family.

---

### 10. Final Payoff

**What it measures:** Whether the ending is strong, surprising, and loop-ready (or hard-cut ready).

```yaml
family: final_payoff
weight: 0.09
minimum_threshold: 80

criteria:
  - name: is_peak_moment
    description: Final beat is strongest/biggest visual moment
    measurement: Check finalPayoff.isPeakIntensity == true
    pass_threshold: true
    weight: 0.35
    
  - name: not_repeat_of_opening
    description: Final beat is not identical to opening
    measurement: Check finalPayoff.isRepeatOfOpening == false
    pass_threshold: true
    weight: 0.30
    
  - name: hard_cut_readiness
    description: Ends mid-action (no static final pose)
    measurement: Check finalPayoff.isHardCut == true
    pass_threshold: true
    weight: 0.20
    
  - name: payoff_timing
    description: Final escalation starts by 12s (not delayed to 13-14s)
    measurement: Check finalPayoff.startsAt <= 12
    pass_threshold: true
    weight: 0.15

scoring:
  excellent: 90-100  # Peak moment, unique, hard cut, good timing
  good: 80-89        # Strong moment, not repeat, good execution
  acceptable: 70-79  # Decent payoff, some weaknesses
  weak: 60-69        # Weak payoff or repeat of opening
  failing: 0-59      # No payoff or static ending

severity_rules:
  - if is_repeat_of_opening: CRITICAL
  - if not is_peak_moment: WARNING
  - if payoff_timing > 13: WARNING
```

**Implementation status (RULESET 1.1):** A new criterion not originally speced here,
`rule_consistent_twist`, is implemented as `PAYOFF_003` — an LLM semantic check that the
final twist derives from the same `coreMechanic.physicalRule` established earlier,
rather than introducing an unrelated, disconnected joke.

---

### 11. Render Risk

**What it measures:** Overall likelihood of successful render given all factors.

```yaml
family: render_risk
weight: 0.08
minimum_threshold: 70

criteria:
  - name: technical_feasibility
    description: No known hard blockers for current video models
    measurement: producibility.estimatedRenderQuality
    pass_threshold: >= 3
    weight: 0.40
    
  - name: failure_mode_prediction
    description: Avoid known failure patterns (foot-floor contact, hand-object precision)
    measurement: Check producibility.riskFactors against known failures
    pass_threshold: <= 2 known failure patterns
    weight: 0.30
    
  - name: complexity_budget
    description: Overall prompt complexity within model capacity
    measurement: Sum of all complexity factors
    pass_threshold: <= "medium-high"
    weight: 0.30

scoring:
  excellent: 90-100  # High confidence, no known risks, simple execution
  good: 80-89        # Good confidence, minimal risks, manageable
  acceptable: 70-79  # Moderate confidence, some risks, uncertain
  weak: 60-69        # Low confidence, multiple risks, risky
  failing: 0-59      # Very low confidence, many risks, likely to fail

severity_rules:
  - if technical_feasibility < 3: BLOCKER
  - if failure_mode_prediction > 3: CRITICAL
```

---

## Aggregate Scoring

```yaml
overall_quality_score:
  calculation: weighted_sum(family_scores * family_weights)
  
  thresholds:
    render_ready: >= 92 AND zero BLOCKERS AND zero CRITICAL
    needs_revision: 80-91 OR has CRITICAL
    needs_redesign: < 80 OR has BLOCKER

severity_hierarchy:
  BLOCKER: Must fix before any render consideration
  CRITICAL: Must fix before render, but concept salvageable
  WARNING: Should fix but not blocking
  PASS: Meets or exceeds threshold
```

---

## Example Score Output

```json
{
  "overallScore": 58,
  "status": "BLOCKED",
  "familyScores": {
    "conceptStrength": 72,
    "hookStrength": 96,
    "visualNovelty": 42,
    "progression": 65,
    "escalation": 58,
    "motionQuality": 71,
    "readability": 88,
    "aiProducibility": 85,
    "consistency": 94,
    "finalPayoff": 45,
    "renderRisk": 78
  },
  "severityCounts": {
    "BLOCKER": 1,
    "CRITICAL": 2,
    "WARNING": 3,
    "PASS": 5
  },
  "failedRules": [
    {
      "family": "visualNovelty",
      "rule": "distinct_consequence_count",
      "severity": "BLOCKER",
      "actual": 2,
      "required": 4,
      "message": "Only 2 distinct visual consequences detected. Minimum: 4."
    },
    {
      "family": "visualNovelty",
      "rule": "static_state_duration",
      "severity": "CRITICAL",
      "actual": 42,
      "required": 30,
      "message": "Visual state 'on_rough_mat' occupies 42% of video. Maximum: 30%."
    },
    {
      "family": "finalPayoff",
      "rule": "not_repeat_of_opening",
      "severity": "CRITICAL",
      "actual": true,
      "required": false,
      "message": "Final beat repeats opening action. Payoff must be unique."
    }
  ]
}
```

---

## Next Steps

1. Use these schemas to implement specific rules (Task #4)
2. Build rule engine that evaluates IR against these families (Task #7)
3. Generate structured feedback for fix suggestions (Task #9)

---

**Schema Version: 1.1**
