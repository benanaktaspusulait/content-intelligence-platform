# FAMILY 1 — Strategy / Attempt Gold Review Report

**Status:** HUMAN-REVIEW PREPARATION — ENGINE NOT CHANGED

**Golden Set:** `POMPOM_GOLDEN_V1`

**Scope:** Only `GOAL`, `INTENDED_EFFECT`, `BEAT_ROLE_ACTION_EVIDENCE`, `ACTIVE_ATTEMPT_COUNT`, `DISTINCT_STRATEGY_COUNT`, and `DISTINCT_STRATEGIES`.

**Excluded from this review:** escalation policy tuning, temporal policy, payoff policy, score thresholds, producibility policy, and any performance data.

## Review Rules

An active attempt requires an intentional character action directed toward solving, controlling, testing, restoring, obtaining, or progressing against the local problem/obstruction. A verb, movement, touch, reaction, escalation label, or character emotion is not sufficient.

A strategy family is the underlying problem-solving method. Similar executions remain one family when the intended mechanism is unchanged. Reactive `CATCH`, `LOOK`, `SMILE`, `WAIT`, `WALK`, and `REACT` actions are not strategies without goal/intended-effect evidence.

## 1. Luca Sticky Ball

Source: `Absurd_Moments/01_luca_sticky_ball/01_video_prompt.txt`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.8–3.0s | REACTION | Walks to ball, pulls one hand, then both hands | Control/retrieve stuck ball | Make ball move / establish obstruction | NO — setup/contact candidate | Role is REACTION; this establishes the failed object relationship before the labelled attempt | Walks and pulls | PULL candidate only | N/A | MEDIUM | “walks straight to the ball and pulls it with one hand” |
| 3.0–6.0s | ATTEMPT / FIRST ATTEMPT | Pulls harder; ball stretches; releases | Control/retrieve stuck ball | Move or free ball | YES | Explicit labelled attempt with deliberate force and visible result | Pulls harder | PULL | YES | HIGH | “Luca pulls harder” |
| 6.0–9.0s | ESCALATION | Grabs with both hands and leans backward; wall flexes | Same local goal | Apply stronger force / test resistance | NO — escalation of prior method | Same pull method with larger affected scope; escalation is not a new attempt or strategy | Grabs and leans backward | PULL continuation | NO | HIGH | “WOODEN WALL itself flexes” |
| 9.0–12.0s | ATTEMPT / SECOND ATTEMPT | Catches dropped ball, squeezes it, observes normal behavior, smiles | Determine whether object is usable/normal again | Test object behavior and restore controlled use | YES | The catch is reactive setup; squeezing/observing is the intentional test | Catches, then squeezes | TEST / SQUEEZE | YES | HIGH | “Luca catches it. He squeezes it gently. It behaves like a normal ball.” |
| 12.0–14.0s | FAKE_RESOLUTION | Tosses normally and relaxes | Confirm normal use | Apparent resolution | NO — payoff/fake-resolution continuation | No new problem-solving method | Tosses | NONE / continuation | N/A | HIGH | “Normal. He relaxes.” |

**Family 1 Gold recommendation:** active attempts `2`; distinct strategies `2`; families `{PULL, TEST_SQUEEZE}`. Reactive `CATCH` is not a distinct strategy. This is HIGH confidence except the REACTION-versus-preliminary-attempt boundary, which remains MEDIUM for human review.

## 2. Luca Ball-Multiplying Crocodile

Source: `Absurd_Moments/07_luca_ball_spitting_crocodile/01_video_prompt.txt`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0–0.8s | HOOK / REACTION | Catches or blocks one ball | Understand/manage ball machine | Prevent immediate hit | NO | Reactive response to the opening output | Catches/blocks | NONE | N/A | HIGH | “Luca flinches and catches/blocks it” |
| 0.8–3.5s | FIRST ACTION | Tosses one ball back into mouth | Control the output rule | Test or manage input/output | YES | Intentional return action directed at the established rule | Tosses | THROW_TOSS | YES | HIGH | “Luca quickly tosses that ONE ball back” |
| 3.5–6.5s | ESCALATION | Throws two balls back | Same goal | Increase/control test magnitude | YES | Deliberate repeat of same method with greater input; separate attempt event, not new strategy | Throws | THROW_TOSS | NO | HIGH | “Luca grabs TWO nearby balls and throws BOTH back” |
| 6.5–9.5s | STOP ATTEMPT | Rolls one ball instead of throwing | Stop or understand machine response | Test a gentler input mode | YES | Deliberate alternative input method | Rolls | ROLL / TEST | YES | MEDIUM | “He slowly rolls it toward the crocodile” |
| 9.5–11.5s | FAKE_RESOLUTION | Catches returned one ball; relaxes | Believe output is controlled | Apparent stabilization | NO | Reaction to apparent success; no new method | Catches | NONE / reaction | N/A | HIGH | “The crocodile returns exactly ONE ball. Luca catches it.” |
| 11.5–15.0s | FINAL PAYOFF | Dodges fountain of balls | Survive consequence | N/A | NO | Consequence magnitude, not a new attempt | Dodges | NONE | N/A | HIGH | “FOUNTAIN of colourful soft balls” |

**Family 1 Gold recommendation:** active attempts `3`; distinct strategies `2`; families `{THROW_TOSS, ROLL/TEST}`. Throwing one versus two is the same family. Goal/intended-effect interpretation is MEDIUM because the prompt describes actions and machine control more clearly than a named local goal.

## 3. Upside-Down Chair

Source: `What’s Wrong? uploaded/1-The Upside-Down Chair/prompt.md`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0–0.8s | HOOK | Runs to sit; freezes above inverted chair | Sit down safely | Use chair | NO — failed setup action | Detects anomaly; no solving method yet | Runs/sits | NONE | N/A | HIGH | “Kiko runs toward a chair to sit down. BUT THE CHAIR IS COMPLETELY UPSIDE DOWN.” |
| 0.8–3.5s | CORRECTION | Grabs and flips chair correctly | Sit down | Restore usable chair state | YES | Intentional physical correction | Flips chair | FLIP | YES | HIGH | “She grabs the chair and flips it correctly” |
| 6.0–8.5s | FIRST ESCALATION | Chair flips while Kiko turns; catches herself | Sit down safely | Respond to autonomous return | NO — reaction | Character catches herself; no new directed method | Catches herself | NONE | N/A | HIGH | “Kiko sits toward empty space and catches herself” |
| 8.5–11.5s | CORRECTION | Flips chair back and watches it | Sit down | Restore and verify stable state | YES | Deliberate correction/verification; same FLIP family | Flips and watches | FLIP | NO | MEDIUM | “Kiko flips it back. She stares directly at the chair.” |
| 11.5–14.5s | PAYOFF BUILD | Guards chair by staring and walking backward | Sit down | Prevent chair from changing while approaching | YES | New control method, not just flipping | Guards/approaches | GUARD_AND_APPROACH | YES | MEDIUM | “She keeps staring ... walks backward toward it” |
| 14.5–17.0s | TWIST | Chair flips with Kiko on it | Sit down | N/A | NO | Consequence of the same rule | Flips with character | NONE | N/A | HIGH | “The ENTIRE chair suddenly flips upside down WITH Kiko on it” |

**Family 1 Gold recommendation:** active attempts `3`; distinct strategies `2`; families `{FLIP, GUARD_AND_APPROACH}`. The initial sit action is a failed goal action, not a distinct problem-solving strategy. Confidence is HIGH for count boundary and MEDIUM for whether verification is a separate attempt.

## 4. Kiko And The Lamp That Hates Being Watched

Source: `easy uploaded/4- Kiko and the Lamp That Hates Being Watched /prompt.md`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0–2.0s | HOOK / TEST 1 | Turns on lamp, reads, looks away, lamp switches off | Read/use lamp | Verify and keep light on | YES | Intentional observation test against local rule | Watches / looks away | OBSERVE_CONTROL_VISIBILITY | YES | MEDIUM | “When she looks away, it switches off” |
| 2.0–8.0s | TEST 2 | Switches on, stares, looks away, points | Keep light stable | Reproduce and confirm behavior | YES | Repeated deliberate test; same method | Stares/watches | OBSERVE_CONTROL_VISIBILITY | NO | MEDIUM | “Kiko switches it on again and stares at it” |
| 8.0–11.5s | TEST 3 | Uses mirror to watch indirectly | Control lamp while not looking directly | Test indirect observation | YES | Execution variant of the same visibility-control method | Uses mirror | OBSERVE_CONTROL_VISIBILITY | NO | MEDIUM | “She uses a small mirror ... to watch the lamp indirectly” |
| 11.5–15.0s | PAYOFF / REACTION | Second light flickers; returns to main lamp | N/A | N/A | NO | Consequence and loop setup | Turns back/lunges | NONE | N/A | MEDIUM | “a second small light ... instead” |

**Family 1 Gold recommendation:** active attempts `3`; distinct strategies `1`; family `{OBSERVE_CONTROL_VISIBILITY}`. Direct watching and mirror watching are execution variants of one visibility-control strategy. Confidence is MEDIUM; human review is APPROVED.

## 5. Mimi And The Snack Box That Keeps Changing

Source: `easy uploaded/2- Mimi and the Snack Box That Keeps Changing/prompt.md`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0–2.0s | TEST 1 | Opens box expecting cracker; sees apple | Get cracker | Inspect contents | YES | Direct goal-directed test | Opens box | REOPEN / TEST | YES | MEDIUM | “Mimi wants a cracker ... opens it ... apple instead” |
| 2.0–5.0s | TEST 2 | Closes and reopens; sees banana/spoon | Get cracker | Retry same test | YES | Same method repeated | Reopens | REOPEN / TEST | NO | HIGH | “Mimi closes and reopens the box” |
| 5.0–8.0s | TEST 3 | Opens again; wrong sock/block appears | Get cracker | Retry same test | YES | Same method, new result | Reopens | REOPEN / TEST | NO | HIGH | “Mimi closes and opens it again” |
| 8.0–11.5s | TEST 4 | Turns/taps/closes carefully/opens; cracker appears | Get cracker | Control the box and obtain desired item | YES | New manipulation/testing variation | Taps/turns and reopens | TAP_TURN / CONTROLLED_REOPEN | YES | MEDIUM | “turns the box slightly, taps it, closes it carefully” |
| 11.5–15.0s | FAKE RESOLUTION / REACTION | Reaches for cracker; lid shuts; wrong item returns | Get cracker | N/A | NO — consequence continuation | Reach is payoff attempt continuation, not a new family | Reaches | NONE / continuation | N/A | MEDIUM | “box still wins” |

**Family 1 Gold recommendation:** active attempts `4`; distinct strategies `2`; families `{REOPEN/TEST, TAP_TURN/CONTROLLED_REOPEN}`. The count boundary around the final reach is MEDIUM and requires human confirmation.

## 6. Luca And The Box Cat

Source: `pompom_vs_animals/03_luca_vs_box_cat/prompt.md`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Frame zero | HOOK | Reaches toward box while cat occupies it | Use empty toy box | Clear access | NO — conflict setup | Reaching is interrupted before a complete method is applied | Reaches | NONE | N/A | HIGH | “cat is already curled up inside it” |
| Attempt 1 | ATTEMPT | Gestures cat out; cat returns | Use empty box | Remove obstruction | YES | Intentional displacement directed at the rule | Gestures cat out | DISPLACE | YES | HIGH | “gently gestures the cat out ... cat ... steps back inside” |
| Attempt 2 | ATTEMPT | Lifts and moves rigid box; cat returns | Use empty box | Change object location | YES | Different physical method directed at same goal | Moves box | RELOCATE | YES | HIGH | “Luca lifts the rigid empty box, moves it” |
| Attempt 3 | ATTEMPT | Stays beside box and watches; cat returns | Use empty box | Prevent/restrain obstruction | YES | Deliberate guarding/control method | Guards box | GUARD | YES | HIGH | “Luca stays beside the empty box and watches carefully” |
| Fake win / payoff | FAKE_RESOLUTION | Approaches empty box; cat reclaims it | Use empty box | Apparent success fails | NO | Consequence of the same rule, not a new method | Bends toward box | NONE | N/A | HIGH | “Just before his hands reach the box, the cat ... moves into the box” |

**Family 1 Gold recommendation:** active attempts `3`; distinct strategies `3`; families `{DISPLACE, RELOCATE, GUARD}`. This is a deliberate boundary case: repeated rule recurrence does not by itself collapse genuinely different character methods into one family. Confidence is HIGH for the three labelled interventions; the policy interpretation of `GUARD` as a strategy remains MEDIUM.

## 7. Kiko And The Spot-Stealing Cat

Source: `pompom_vs_animals/04_kiko_vs_spot_stealing_cat/prompt.md`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Frame zero | HOOK | Lowers toward empty spot while cat claims it | Sit down | Secure target spot | NO — setup conflict | Initial interrupted sitting action is not a completed method | Lowers/sits | NONE | N/A | HIGH | “cat is curling into that exact spot just before Kiko sits” |
| Attempt 1 | ATTEMPT | Switches to second spot; cat claims it | Sit down | Choose a usable target | YES | Goal-directed target selection | Switches spot | COMMIT_TO_TARGET | YES | HIGH | “Kiko immediately changes to a second nearby sitting spot” |
| Attempt 2 | ATTEMPT | Goes to opposite spot; cat claims it | Sit down | Choose a different usable target | YES | Another attempt event, same underlying mechanism | Changes target | COMMIT_TO_TARGET | NO | HIGH | “walks to a third open spot ... starts to sit” |
| Attempt 3 | ATTEMPT | Uses decoy; cat claims real target | Sit down | Mislead cat and secure target | YES | Deliberate tactic, but still same underlying target-claim problem-solving family | Decoys then commits | COMMIT_TO_TARGET | NO | MEDIUM | “pretends to sit ... commits to another” |
| Fake win / payoff | FAKE_RESOLUTION | Cat looks away; Kiko smiles; cat claims spot | Sit down | Apparent success fails | NO | Reaction/consequence continuation | Begins lowering | NONE | N/A | HIGH | “At the exact moment she truly commits, the cat ... moves into the spot” |

**Family 1 Gold recommendation:** active attempts `3`; distinct strategies `1`; family `{COMMIT_TO_TARGET}`. This is the negative regression boundary: target changes and a decoy do not automatically make new problem-solving families. Confidence is HIGH for repeated same-family interpretation; the decoy classification is MEDIUM.

## 8. Mimi Vs. The Sneaky Door

Source: `archive/MIMI_VS_THE_SNEAKY_DOOR/mimi-sneaky-door-compact-generation-prompt.md`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Shot 01 | ATTEMPT | Strong pull after door closes | Control door / keep passage usable | Open or stabilize door | YES | Deliberate physical intervention | Pulls door | PULL | YES | MEDIUM | “door closes → Mimi ‘Huh?’ → strong pull” |
| Shot 02 | ATTEMPT | Steps away; observes open/close behavior | Control/understand door | Test recurrence | YES | Intentional distance/observation test | Steps away / watches | OBSERVE_TEST | YES | MEDIUM | “door opens once ... Mimi turns ... door closes once” |
| Shot 03 | ATTEMPT | Fake steps; springs back; tries to catch door | Control door | Decoy and capture timing | YES | Deliberate alternate tactic | Decoys/catches | DECOY_CAPTURE | YES | MEDIUM | “two fake steps → spring-back and ‘Got you!’” |
| End bridge | LOOP / PAYOFF | Door-to-lens wipe | N/A | Visual loop bridge | NO | Continuity/payoff, not a new attempt | Door wipe | NONE | N/A | HIGH | “controlled door-to-lens wipe” |

**Family 1 Gold recommendation:** active attempts `3`; distinct strategies `3` provisionally; families `{PULL, OBSERVE_TEST, DECOY_CAPTURE}`. Confidence remains MEDIUM because this is a multi-clip production contract rather than one timestamp-labelled prompt timeline.

## 9. Luca And The Island Journal

Source: `classic story-1/03_luca_and_the_island_journal/01_video_prompt.txt`

| Relevant beat | Beat role | Observed action | Character goal | Intended effect | Active attempt? | Why? | Primary action | Strategy family | Distinct from previous? | Confidence | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.0–5.0s | HOOK / SETUP | Wakes, looks around, reacts to island | Broad adventure/survival | Understand setting | NO | No focused local obstruction or method | Looks around | NONE | N/A | HIGH | “Luca lies on soft sand ... island” |
| 5.0–10.0s | MONTAGE | Opens coconut, fishes, builds shelter | Survive/explore | Try unrelated activities | NO | Activities do not target one established impossible problem | Opens/fishes/builds | NONE | N/A | HIGH | “COMEDY MONTAGE” |
| 10.0–16.0s | DISCOVERY | Finds cave/chest; opens chest | Find treasure/story | Inspect contents | NO | Narrative discovery, not a local problem-solving attempt | Opens chest | NONE | N/A | HIGH | “Inside: a blank journal and pencil” |
| 16.0–21.5s | RESOLUTION | Writes journal | Tell adventure story | Record experience | NO | No established impossible mechanic to solve | Writes | NONE | N/A | MEDIUM | “Today... I became an island explorer” |
| 21.5–25.5s | TWIST | Wakes in bed; sees same journal | N/A | N/A | NO | Final twist/consequence, not an attempt | Wakes/stares | NONE | N/A | HIGH | “A dream? ... SAME journal” |

**Family 1 Gold recommendation:** active attempts `0`; distinct strategies `0`; no strategy families. This is HIGH confidence for the absence of a single local problem-solving sequence. It is intentionally negative for central-mechanic/short-form coherence, not because of corpus role.

## Family 1 Gold Confidence Summary

| Asset | Active attempts | Distinct strategies | Strategy families | Confidence status |
|---|---:|---:|---|---|
| Sticky Ball | 2 | 2 | PULL, TEST_SQUEEZE | HIGH except setup boundary MEDIUM |
| Ball-Multiplying Crocodile | 3 | 2 | THROW_TOSS, ROLL/TEST | MEDIUM for goal/attempt boundary |
| Upside-Down Chair | 3 | 2 | FLIP, GUARD_AND_APPROACH | HIGH/MEDIUM boundary |
| Lamp | 3 | 1 | OBSERVE_CONTROL_VISIBILITY | MEDIUM · APPROVED |
| Snack Box | 4 | 2 | REOPEN/TEST, TAP_TURN/CONTROLLED_REOPEN | MEDIUM |
| Box Cat | 3 | 3 | DISPLACE, RELOCATE, GUARD | HIGH/MEDIUM policy boundary |
| Spot-Stealing Cat | 3 | 1 | COMMIT_TO_TARGET | HIGH/MEDIUM decoy boundary |
| Sneaky Door | 3 | 3 | PULL, OBSERVE_TEST, DECOY_CAPTURE | MEDIUM |
| Island Journal | 0 | 0 | — | HIGH for no central strategy |

## Family 1 Baseline Matrix

This compares the human-review recommendation with the captured deterministic v1.7 baseline. `KNOWN_BASELINE_ISSUE` means the current mismatch is preserved for calibration; it is not a new regression.

| Asset | Gold attempts | v1.7 attempts | Gold distinct | v1.7 distinct | Gold families | v1.7 families | Classification | Known issue |
|---|---:|---:|---:|---:|---|---|---|---|
| Sticky Ball | 2 | 2 | 2 | 2 | PULL, TEST_SQUEEZE | PULL, SQUEEZE | PASS_AFTER_NORMALIZATION | No |
| Ball-Multiplying Crocodile | 3 | 0 | 2 | 0 | THROW_TOSS, ROLL/TEST | — | KNOWN_BASELINE_ISSUE | Parser structured timeline gap |
| Upside-Down Chair | 3 | unavailable | 2 | unavailable | FLIP, GUARD_AND_APPROACH | — | KNOWN_BASELINE_ISSUE | Parser discovery timeout |
| Lamp | 3 | 0 | 1 | 0 | OBSERVE_CONTROL_VISIBILITY | — | KNOWN_BASELINE_ISSUE | Parser partial structured evidence |
| Snack Box | 4 | 0 | 2 | 0 | REOPEN/TEST, TAP_TURN/CONTROLLED_REOPEN | — | KNOWN_BASELINE_ISSUE | Parser partial structured evidence |
| Box Cat | 3 | 0 | 3 | 0 | DISPLACE, RELOCATE, GUARD | — | KNOWN_BASELINE_ISSUE | Timeline parser incompatibility |
| Spot-Stealing Cat | 3 | 0 | 1 | 0 | COMMIT_TO_TARGET | — | KNOWN_BASELINE_ISSUE | Timeline parser incompatibility |
| Sneaky Door | 3 | 0 | 3 | 0 | PULL, OBSERVE_TEST, DECOY_CAPTURE | — | KNOWN_BASELINE_ISSUE | Multi-clip/parser gap |
| Island Journal | 0 | 0 | 0 | 0 | — | — | PASS | No strategy sequence expected |

## Review Decision

There is sufficient HIGH-confidence coverage to begin a narrowly scoped Family 1 engine calibration. The following human-approved MEDIUM-confidence labels are locked for Family 1 and remain MEDIUM as confidence rather than review status:

- Crocodile attempt 3 and `ROLL/TEST` boundary
- Upside-Down Chair verification as a separate attempt
- Snack Box final controlled reopen boundary
- Box Cat `GUARD` as a distinct strategy family
- Sneaky Door multi-clip strategy partition

No engine behavior, Gold Truth confidence, or policy output was changed in this preparation step.
