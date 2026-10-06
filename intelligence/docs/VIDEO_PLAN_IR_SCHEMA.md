# Video Plan IR (Intermediate Representation) Schema

## Purpose

The Video Plan IR is a **structured JSON representation** of a 15-second video prompt that enables:
- Automated quality analysis
- Rule engine validation
- Consequence counting
- Static state detection
- Repetition analysis
- Escalation measurement

**Key principle:** Rules operate on structured data, not free text.

---

## Schema Definition

```typescript
interface VideoPlanIR {
  // Metadata
  metadata: {
    title: string;                    // e.g., "Kiko — Slippery / Rough"
    duration: number;                 // Total seconds (typically 15)
    format: "9:16" | "16:9";         // Aspect ratio
    seriesType: "opposites" | "whats_wrong" | "discovery" | "feelings" | "music" | "stories" | "social_reel";
    createdAt: string;                // ISO timestamp
    version: number;                  // Iteration count (1, 2, 3...)
    previousVersion?: string;         // Link to prior version if exists
  };

  // Characters
  characters: {
    primary: string;                  // e.g., "Kiko"
    secondary?: string[];             // e.g., ["Mimi"] if applicable
    characterRefs: string[];          // File paths to character sheets
  };

  // Location & Props
  setting: {
    location: string;                 // e.g., "Warm Pompom Hills hallway"
    locationRef?: string;             // File path to location reference
    mainProps: string[];              // e.g., ["yellow pencil", "pencil sharpener"]
    visualEnvironment: string;        // Brief description for AI producibility check
  };

  // Learning Objective (if applicable)
  learningObjective?: {
    concepts: string[];               // e.g., ["SLIPPERY", "ROUGH"]
    pedagogicalGoal: string;          // e.g., "Teach opposite textures through physical experience"
    soundOffReadable: boolean;        // Must be understandable without audio
  };

  // Core Mechanic
  coreMechanic: {
    physicalRule: string;             // e.g., "Smooth floor = slide, Rough mat = stop"
    causeEffect: string;              // e.g., "Stepping on surface → movement consequence"
    consistency: "consistent" | "evolving" | "breaking";  // Does rule stay same or change?
    mechanicCount: number;            // Number of independent physical/magical
                                       // rules active in the concept, as claimed
                                       // by the author. Verified (not trusted) by
                                       // CONCEPT_007 via semantic evaluation.
                                       // Optional; defaults to 1 when absent.
    primaryObject?: string;            // Primary non-living object carrying the mechanic
    mechanicCarrier?: "OBJECT" | "OBJECT_INTERACTION" | "PRIMARY_AGENT" |
                      "SECONDARY_AGENT" | "MULTI_AGENT" | "UNKNOWN";
    causalParticipants?: string[];    // Living agents causally participating in the mechanic
  };

  // Hook
  hook: {
    anomaly: string;                  // What's unusual in frame 1?
    startsAt: number;                 // Timestamp (typically 0)
    startsMidAction: boolean;         // True if no setup
    visualStrength: 1 | 2 | 3 | 4 | 5;  // How attention-grabbing (1=weak, 5=strong)
    soundOffClear: boolean;           // Understandable without audio?
  };

  // Timeline Beats
  beats: Beat[];

  // Final Payoff
  finalPayoff: {
    type: "escalation" | "twist" | "loop" | "reveal" | "callback";
    startsAt: number;                 // When final beat begins
    endsAt: number;                   // When it ends (typically 15)
    isPeakIntensity: boolean;         // Is this the strongest moment?
    isHardCut: boolean;               // Cuts mid-action vs holds pose
    isRepeatOfOpening: boolean;       // True if final = opening (bad)
    loopsToOpening: boolean;          // True if the final state visually/
                                       // narratively connects back to the
                                       // opening, inviting replay. Optional;
                                       // defaults to false when absent.
    loopQuality: "strong" | "weak" | "none";  // Quality of the loop if present.
                                       // Optional; defaults to "none" when absent.
  };

  // AI Producibility Assessment
  producibility: {
    overallComplexity: "low" | "medium" | "high" | "very_high";
    riskFactors: string[];            // e.g., ["hand-object precision", "morphing texture"]
    estimatedRenderQuality: 1 | 2 | 3 | 4 | 5;  // 1=high risk, 5=confident
  };
}

interface Beat {
  // Timing
  id: string;                         // e.g., "beat_01"
  startTime: number;                  // Seconds (e.g., 0.0)
  endTime: number;                    // Seconds (e.g., 1.0)
  duration: number;                   // Calculated: endTime - startTime

  // Action
  action: string;                     // What character does, e.g., "slides on floor"
  actionType: "motion" | "interaction" | "reaction" | "transition" | "idle";
  
  // Visual State
  visualState: string;                // What viewer sees, e.g., "character on slippery floor"
  visualStateId: string;              // Normalized ID for comparison, e.g., "on_slippery_floor"
  
  // Consequence
  consequence: string;                // Physical result, e.g., "shoe glides forward, arms spread"
  consequenceType: "new" | "continuation" | "repeat" | "escalation" | "fake_win";
                                       // "fake_win": the problem appears solved,
                                       // optional bonus beat consumed by
                                       // PAYOFF_002/PAYOFF_005.
  
  // Intensity
  intensity: number;                  // 1-10 scale of visual/emotional energy
  motionAmount: "none" | "minimal" | "moderate" | "high" | "extreme";
  
  // Dialogue (if any)
  dialogue?: {
    speaker: string;
    text: string;
    isLearningWord: boolean;          // True if part of pedagogical goal
  };

  // Readability
  readabilityDuration: number;        // How long state is held for comprehension
  isReadable: boolean;                // True if >= 0.6s

  // Relationships
  isNewConsequence: boolean;          // True if distinct from all prior beats
  similarToBeats: string[];           // IDs of similar beats (for repetition detection)
  cycleGroup?: string;                // If part of repeated cycle, e.g., "sharpen_draw_blunt"
  isAttempt: boolean;                // True if this beat represents the character
                                      // actively trying a new strategy against the
                                      // established problem. Defaults to false.
  primaryVerb: string;               // Normalized (upper-case) primary action verb
                                      // for this attempt, e.g. "CATCH", "BLOCK".
                                      // Required (non-empty) when isAttempt is true;
                                      // empty string otherwise.
  relatesToCoreProblem: boolean;     // True if this beat advances/stays engaged
                                      // with the established core mechanic/problem.
                                      // False if it cuts away to story-irrelevant
                                      // content (scenery, unrelated reaction, etc).
                                      // Optional; defaults to true when absent
                                      // (pre-1.2 IRs are assumed on-topic).
}
```

The optional `primaryObject`, `mechanicCarrier`, and `causalParticipants` fields
provide explicit evidence for the scoped `CONCEPT_009` rule. They describe causal
participation, not every character visible in a frame; absent or ambiguous fields
are evaluated semantically and must not be guessed as a pass.

---

## Example: Kiko Slippery/Rough (FAIL_001)

```json
{
  "metadata": {
    "title": "Kiko — Slippery / Rough",
    "duration": 15,
    "format": "9:16",
    "seriesType": "opposites",
    "createdAt": "2026-09-09T00:00:00Z",
    "version": 1
  },
  "characters": {
    "primary": "Kiko",
    "characterRefs": ["01-CHARACTERS/drawings/kiko.png"]
  },
  "setting": {
    "location": "Warm Pompom Hills hallway",
    "mainProps": ["dark wooden floor", "light beige coir mat"],
    "visualEnvironment": "Simple indoor hallway, two fixed floor surfaces"
  },
  "learningObjective": {
    "concepts": ["SLIPPERY", "ROUGH"],
    "pedagogicalGoal": "Teach opposite surface textures through physical experience",
    "soundOffReadable": true
  },
  "coreMechanic": {
    "physicalRule": "Smooth floor = slide, Rough mat = stop",
    "causeEffect": "Surface texture determines movement type",
    "consistency": "consistent"
  },
  "hook": {
    "anomaly": "Kiko already sliding with wide eyes",
    "startsAt": 0.0,
    "startsMidAction": true,
    "visualStrength": 5,
    "soundOffClear": true
  },
  "beats": [
    {
      "id": "beat_01",
      "startTime": 0.0,
      "endTime": 1.0,
      "duration": 1.0,
      "action": "slides on glossy floor",
      "actionType": "motion",
      "visualState": "character sliding on slippery floor",
      "visualStateId": "on_slippery_floor",
      "consequence": "shoe glides forward, arms spread for balance",
      "consequenceType": "new",
      "intensity": 8,
      "motionAmount": "high",
      "dialogue": {
        "speaker": "Kiko",
        "text": "SLIPPERY!",
        "isLearningWord": true
      },
      "readabilityDuration": 1.0,
      "isReadable": true,
      "isNewConsequence": true,
      "similarToBeats": [],
      "cycleGroup": null
    },
    {
      "id": "beat_02",
      "startTime": 1.0,
      "endTime": 3.2,
      "duration": 2.2,
      "action": "tries corrective step",
      "actionType": "interaction",
      "visualState": "character still on slippery floor",
      "visualStateId": "on_slippery_floor",
      "consequence": "front shoe glides further, body shifts",
      "consequenceType": "continuation",
      "intensity": 6,
      "motionAmount": "moderate",
      "readabilityDuration": 2.2,
      "isReadable": true,
      "isNewConsequence": false,
      "similarToBeats": ["beat_01"],
      "cycleGroup": null
    },
    {
      "id": "beat_03",
      "startTime": 3.2,
      "endTime": 5.2,
      "duration": 2.0,
      "action": "reaches rough mat, stops sliding",
      "actionType": "transition",
      "visualState": "character on rough mat",
      "visualStateId": "on_rough_mat",
      "consequence": "sliding stops, tiny bounce, looks at mat",
      "consequenceType": "new",
      "intensity": 7,
      "motionAmount": "moderate",
      "dialogue": {
        "speaker": "Kiko",
        "text": "ROUGH!",
        "isLearningWord": true
      },
      "readabilityDuration": 2.0,
      "isReadable": true,
      "isNewConsequence": true,
      "similarToBeats": [],
      "cycleGroup": null
    },
    {
      "id": "beat_04",
      "startTime": 5.2,
      "endTime": 7.5,
      "duration": 2.3,
      "action": "tests mat by moving shoe",
      "actionType": "interaction",
      "visualState": "character on rough mat",
      "visualStateId": "on_rough_mat",
      "consequence": "shoe barely slides, presses down",
      "consequenceType": "continuation",
      "intensity": 4,
      "motionAmount": "minimal",
      "readabilityDuration": 2.3,
      "isReadable": true,
      "isNewConsequence": false,
      "similarToBeats": ["beat_03"],
      "cycleGroup": null
    },
    {
      "id": "beat_05",
      "startTime": 7.5,
      "endTime": 9.5,
      "duration": 2.0,
      "action": "extends shoe to floor, tests contrast",
      "actionType": "interaction",
      "visualState": "character on rough mat",
      "visualStateId": "on_rough_mat",
      "consequence": "shoe glides on floor, pulls back to mat",
      "consequenceType": "continuation",
      "intensity": 5,
      "motionAmount": "moderate",
      "readabilityDuration": 2.0,
      "isReadable": true,
      "isNewConsequence": false,
      "similarToBeats": ["beat_03", "beat_04"],
      "cycleGroup": null
    },
    {
      "id": "beat_06",
      "startTime": 9.5,
      "endTime": 11.5,
      "duration": 2.0,
      "action": "walks comfortably on mat",
      "actionType": "motion",
      "visualState": "character on rough mat",
      "visualStateId": "on_rough_mat",
      "consequence": "takes two tiny steps, no sliding, looks relieved",
      "consequenceType": "continuation",
      "intensity": 3,
      "motionAmount": "minimal",
      "readabilityDuration": 2.0,
      "isReadable": true,
      "isNewConsequence": false,
      "similarToBeats": ["beat_03", "beat_04", "beat_05"],
      "cycleGroup": null
    },
    {
      "id": "beat_07",
      "startTime": 11.5,
      "endTime": 12.6,
      "duration": 1.1,
      "action": "steps back onto slippery floor",
      "actionType": "transition",
      "visualState": "character on slippery floor",
      "visualStateId": "on_slippery_floor",
      "consequence": "shoe begins to glide, eyes widen",
      "consequenceType": "repeat",
      "intensity": 7,
      "motionAmount": "moderate",
      "readabilityDuration": 1.1,
      "isReadable": true,
      "isNewConsequence": false,
      "similarToBeats": ["beat_01", "beat_02"],
      "cycleGroup": null
    },
    {
      "id": "beat_08",
      "startTime": 12.6,
      "endTime": 15.0,
      "duration": 2.4,
      "action": "slides sideways",
      "actionType": "motion",
      "visualState": "character sliding on slippery floor",
      "visualStateId": "on_slippery_floor",
      "consequence": "controlled slide, arms out, panicked expression",
      "consequenceType": "repeat",
      "intensity": 8,
      "motionAmount": "high",
      "dialogue": {
        "speaker": "Kiko",
        "text": "SLIPPERY!",
        "isLearningWord": true
      },
      "readabilityDuration": 2.4,
      "isReadable": true,
      "isNewConsequence": false,
      "similarToBeats": ["beat_01", "beat_02", "beat_07"],
      "cycleGroup": null
    }
  ],
  "finalPayoff": {
    "type": "callback",
    "startsAt": 12.6,
    "endsAt": 15.0,
    "isPeakIntensity": false,
    "isHardCut": true,
    "isRepeatOfOpening": true
  },
  "producibility": {
    "overallComplexity": "low",
    "riskFactors": ["foot-floor contact consistency"],
    "estimatedRenderQuality": 4
  }
}
```

---

## Key Fields for Quality Analysis

### For Static State Detection
- `beat.visualStateId`: Normalized identifier
- `beat.duration`: How long state persists
- Group consecutive beats with same `visualStateId`
- Calculate total duration per unique state

### For Consequence Counting
- `beat.isNewConsequence`: Boolean flag
- `beat.consequenceType`: "new" vs "repeat"
- Count beats where `isNewConsequence === true`

### For Repetition Detection
- `beat.similarToBeats`: Array of beat IDs
- `beat.cycleGroup`: Identifier for repeated cycles
- Track action frequency across timeline

### For Escalation Measurement
- `beat.intensity`: 1-10 scale
- Plot intensity over time
- Detect drops, plateaus, or steady rises

### For AI Producibility
- `producibility.overallComplexity`
- `producibility.riskFactors`
- `beat.actionType` and `motionAmount`

---

## Duration Tiers

Rules that scale with video length (ATTEMPT_001, ATTEMPT_002, CHAR_002,
PRODUCIBILITY_002 — see RULESET_1.1) derive a tier from `metadata.duration`
rather than reading a stored field:

- **short tier**: `duration <= 20` seconds — minimum 3 distinct attempts,
  minimum 50% active-character ratio, maximum 2 main props.
- **long tier**: `duration > 20` seconds — minimum 7 distinct attempts,
  minimum 60% active-character ratio, maximum 4 main props.

A 30-45 second concept must not simply stretch a short-form idea — the
longer duration must be earned by genuinely more distinct problem-solving
strategies, not by slowing down the same number of attempts.

---

## Backward Compatibility (v1.2)

Three fields were added in schema v1.2: `beats[].relatesToCoreProblem`,
`coreMechanic.mechanicCount`, `finalPayoff.loopsToOpening`/`loopQuality`.
All three are optional. A v1.0/v1.1-shaped IR that omits them is handled
identically to a v1.2 IR that includes them with these default values:

- `beats[].relatesToCoreProblem` → `true` (assumed on-topic)
- `coreMechanic.mechanicCount` → `1` (assumed single-mechanic)
- `finalPayoff.loopsToOpening` → `false`, `finalPayoff.loopQuality` → `"none"`

No rule introduced in RULESET 1.2 produces a false FAIL purely from these
fields being absent on an older IR.

---

## Schema Validation Rules

```yaml
required:
  - metadata.duration must be between 10 and 45 seconds
  - durationTier is derived at evaluation time, not stored on the IR:
    duration <= 20 -> "short" tier, duration > 20 -> "long" tier
  - beats array must not be empty
  - beats must cover 0 to metadata.duration with no gaps
  - each beat.duration must be >= 0.4 seconds (minimum readability)
  - finalPayoff.endsAt must equal metadata.duration

consistency:
  - sum(beat.duration) must equal metadata.duration
  - beat[n].endTime must equal beat[n+1].startTime
  - visualStateId must be normalized (lowercase, underscores)

quality:
  - at least 4 beats with isNewConsequence === true
  - no single visualStateId should exceed 30% of total duration
  - intensity should generally increase or maintain (not drop mid-video)
```

---

## Parser Output Format

When the parser converts a text prompt → IR, it should also output:

```json
{
  "videoPlanIR": { ... },
  "parserMetadata": {
    "confidence": 0.85,
    "ambiguities": [
      "Beat timing for 'tests mat' unclear, estimated 2.3s"
    ],
    "assumptions": [
      "Assumed 'tiny steps' = minimal motion amount"
    ],
    "warnings": [
      "No explicit intensity specified, inferred from action descriptions"
    ]
  }
}
```

This allows the system to flag **low-confidence parses** that need human review.

---

## Next Steps

1. Use this schema to build the Python parser (Task #5)
2. Define rule engine operations on this structure (Task #7)
3. Create test fixtures from FAIL_001, FAIL_002, FAIL_003 (Task #16)

---

**This schema is versioned.**

Current version: **1.5**

v1.4 added canonical beat evidence to each beat. v1.5 adds strategy/goal evidence and
nullable evidence projections; these are parser/evidence plumbing changes and do not mutate
historical rulesets:

- `beatLabel` / `beatRole`: the author's structural label after the timestamp (for example
  `FIRST ATTEMPT`) and its canonical role (`HOOK`, `REACTION`, `ATTEMPT`, `ESCALATION`,
  `FAKE_RESOLUTION`, `TWIST`, `PAYOFF`). The label is metadata; action, consequence, intensity
  and hook anomaly are derived from the body.
- `attemptSource`: `EXPLICIT_ATTEMPT_LABEL` (`[ATTEMPT: VERB]`), `STRUCTURED_PLAN_ROLE`
  (an explicit `FIRST/SECOND/... ATTEMPT` role), `SEMANTIC_INFERENCE` or `NONE`. A leading
  physical verb is only an `attemptCandidate` with source `LEADING_VERB_INFERENCE`; it never
  sets `isAttempt=true` on its own. Narrative `ESCALATION` is therefore not an attempt unless
  it also has explicit attempt evidence.
- `strategyFamily`: conservative mechanical normalization (`PULL`, `PUSH`, `SQUEEZE`,
  `CATCH`, `THROW_TOSS`, etc.). Force, angle and synonym variants can share a family. Rules
  track `activeAttemptCount` separately from `distinctStrategyCount`.
- Attempt beats carry additive `actor`, `goal`, `targetObject`, `intendedEffect`, `result`,
  `attemptConfidence`, `distinctFromPreviousAttempt` and `attemptReason` fields. Missing
  semantic evidence remains null; it is not fabricated from performance history.
- `goalEvidence` carries `goalExplicitness` (`EXPLICIT`, `IMPLICIT_BUT_OBSERVABLE`,
  `UNSUPPORTED`, `UNKNOWN`), `goalType`, target and obstruction. `coreMechanic` may carry
  `abnormalProperty`, `trigger`, `persistence`, `releaseCondition` and `recurrence`, so a
  declared fake resolution can be distinguished from an uncontrolled rule change.

All attempt consumers read `app/quality/canonical_evidence.py` (`attempt_beats` and
`attempt_evidence`). `timeline_data.state_segments[].percentage` is a percent (0-100), not a
0-1 ratio. Family assessments represent UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR with a nullable
score and status; they never encode missing evidence as a measured numeric zero.
v1.1 adds `Beat.isAttempt` / `Beat.primaryVerb` and relaxes the duration ceiling to
support 30-45s long-form concepts.

v1.2 adds `Beat.relatesToCoreProblem`, `coreMechanic.mechanicCount`, and
`finalPayoff.loopsToOpening`/`loopQuality`, all optional with backward-compatible
defaults.

v1.3 adds no new IR fields — it adds 8 new rules (GOAL_001, CONCEPT_008,
PROGRESSION_006, ESCALATION_005, HOOK_004, PERFORMANCE_001, PRODUCIBILITY_003,
GENERATION_EXECUTABLE_ATTEMPTS) that evaluate existing fields (`Beat.action`,
`Beat.consequence`, `Beat.primaryVerb`, `Beat.isAttempt`, `Beat.intensity`,
`coreMechanic.physicalRule`, `hook.anomaly`) more deeply, plus corrects the
semantics of 9 existing rules (renames, a tolerance window, a timeline-aware
check, prompt strengthening, cross-rule correlation tagging) without changing
their IR dependencies. See `RULESET_1.3.yaml` for the full rule-level detail.
Two new rule families are introduced: `character_performance`
(PERFORMANCE_001) and `generation_executability`
(GENERATION_EXECUTABLE_ATTEMPTS) — see `RuleEngine._calculate_overall_score`'s
weight table in `rule_engine.py`.

### Backward Compatibility (v1.3)

No new required fields were added. `GENERATION_EXECUTABLE_ATTEMPTS` and the
four new LLM-semantic-check rules (`GOAL_001`, `CONCEPT_008`, `HOOK_004`,
`PERFORMANCE_001`) all read only pre-existing fields (`Beat.action`,
`Beat.consequence`, `Beat.primaryVerb`, `hook.anomaly`,
`coreMechanic.physicalRule`, `characters.primary`) — a video plan authored
before v1.3 is fully evaluable by every v1.3 rule with no missing-field
false FAILs, since nothing new was added to be missing.

Future versions may add:
- Camera movement tracking
- Character interaction complexity
- Prop state changes
- Multi-character coordination metrics
