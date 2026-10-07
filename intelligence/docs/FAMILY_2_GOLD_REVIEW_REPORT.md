# FAMILY 2 — Escalation Gold Review Report

**Status:** HUMAN-REVIEW PREPARATION — ENGINE NOT CHANGED

**Golden Set:** `POMPOM_GOLDEN_V1`

**Scope:** Escalation only. This review does not retune attempts, strategy families, temporal policy, payoff policy, producibility policy, grades, or family scores.

## Escalation Definition

Escalation is a meaningful increase in force, consequence magnitude, deformation, affected-object scope, difficulty, stakes, recurrence pressure, or persistence of the established mechanic.

Escalation is not restricted to:

```text
attemptIntensity[n+1] > attemptIntensity[n]
```

A stronger execution of the same strategy can be escalation without creating a new attempt family or distinct strategy.

## 1. Luca Sticky Ball

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| 3.0–6.0s | ATTEMPT | Ball stretches while center remains stuck; snap-back persists | PULL | Intermediate baseline | HIGH | “The ball stretches toward him like soft chewing gum ... instantly returns to the wall.” |
| 6.0–9.0s | ESCALATION | Affected scope expands from ball deformation to the wooden wall flexing | Yes — stronger PULL | STRONG | HIGH | “the WOODEN WALL itself flexes slightly toward Luca” |
| 14.0–15.0s | FINAL TWIST | Same sticky mechanic reaches Luca’s cheek | Same mechanic, larger character consequence | Strong payoff consequence, not a new attempt | HIGH | “It drops directly onto his CHEEK and sticks there” |

**Decision:** `ESCALATION = STRONG`. Wall-flex evidence is independent of attempt intensity and must not increase distinct strategies.

## 2. Luca Ball-Multiplying Crocodile

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| 0.8–3.5s | FIRST ACTION | One input produces three outputs | THROW/TOSS | Strong | HIGH | “ONE ... spits out THREE” |
| 3.5–6.5s | ESCALATION | Two inputs produce six outputs; ball count doubles the prior output | Same THROW/TOSS | Strong | HIGH | “A burst of SIX soft balls” |
| 11.5–15.0s | FINAL TWIST | Same rule produces a fountain and surrounds Luca | Same multiplication rule | Strong | HIGH | “FOUNTAIN of colourful soft balls ... surrounded up to his shoulders” |

**Decision:** `ESCALATION = STRONG`. Numeric consequence magnitude is canonical evidence; a new strategy is not required.

## 3. Upside-Down Chair

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| 6.0–8.5s | ESCALATION | Chair flips autonomously when Kiko turns away | Same inversion rule | MODERATE | MEDIUM | “The chair turns upside down by itself” |
| 8.5–11.5s | ESCALATION | Recurrence continues despite direct watching and correction | FLIP / GUARD remain same rule | MODERATE | MEDIUM | “Chair stays normal ... FLIP ... Chair is upside down” |
| 14.5–17.0s | TWIST | Entire chair flips with Kiko on it | Same rule affects character and raises stakes | STRONG | HIGH | “WITH Kiko on it ... Kiko ends upside down” |

**Decision:** `ESCALATION = STRONG` across the full arc; the middle recurrence is moderate, while the final character-attached consequence is strong. It is not a new strategy family.

## 4. Kiko And The Lamp That Hates Being Watched

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| 0.0–8.0s | TESTS | Lamp repeatedly switches off when unwatched | OBSERVE_CONTROL_VISIBILITY | Weak/flat | HIGH | “It switches off again” |
| 8.0–11.5s | TEST | Mirror changes observation geometry but not the underlying method | Same observation family | Moderate | MEDIUM | “watch the lamp indirectly” |
| 11.5–15.0s | PAYOFF | A second light becomes involved | Scope expands, but consequence remains a similar light-state gag | MODERATE | MEDIUM | “a second small light ... flickers” |

**Decision:** `ESCALATION = MODERATE`, not STRONG. Repeated observation alone must not produce a strong escalation score.

## 5. Mimi And The Snack Box That Keeps Changing

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| 0.0–8.0s | TESTS | Contents vary across openings | REOPEN/TEST | MODERATE | MEDIUM | “apple ... banana or spoon ... sock or block” |
| 8.0–11.5s | TEST | Controlled tap/turn/reopen finally produces cracker | New execution variant, same box rule | MODERATE | MEDIUM | “turns the box slightly, taps it ... cracker appears” |
| 11.5–15.0s | PAYOFF/RECURRENCE | Apparent success fails and wrong item returns | Same changing-contents rule | MODERATE | HIGH | “box still wins ... another wrong item again” |

**Decision:** `ESCALATION = MODERATE`. Result variety and recurrence matter; attempt intensity is not required.

## 6. Luca And The Box Cat

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| Attempt 1 → 2 | ATTEMPTS | Cat reclaims box after displacement, then after relocation | Methods differ; rule persists | MODERATE | MEDIUM | “cat ... steps back inside” / “cat ... sitting inside again” |
| Attempt 3 | ATTEMPT | Cat reclaims despite direct guarding and brief look-away | GUARD method; recurrence pressure rises | MODERATE | MEDIUM | “cat has claimed the box again” |
| Fake win | FAKE_RESOLUTION | Same rule defeats final approach | Same mechanic, stronger timing consequence | MODERATE | HIGH | “Just before his hands reach the box” |

**Decision:** `ESCALATION = MODERATE`. Recurrence and timing pressure are evidence; do not require increasing force or a new strategy.

## 7. Kiko And The Spot-Stealing Cat

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| Attempt 1 → 3 | ATTEMPTS | Cat claims each committed target; target location changes only | COMMIT_TO_TARGET | WEAK | HIGH | “cat ... settles into that second spot” / “claims ... real target spot” |
| Fake win | FAKE_RESOLUTION | Final claim repeats the same consequence without larger scope/stakes | Same claim | WEAK | HIGH | “cat makes one final short move into the spot” |

**Decision:** `ESCALATION = WEAK`. More repetitions and different spots must not be mistaken for stronger escalation.

## 8. Mimi Vs. The Sneaky Door

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| Shot 1 → 2 | ATTEMPTS | Door closes/opens across controlled clip handoffs | Methods vary; same door behavior | MODERATE | MEDIUM | “door opens once ... door closes once” |
| Shot 3 | PAYOFF | Spring-back and door-to-lens wipe increase visual consequence | DECOY/CAPTURE remains door-control arc | MODERATE | MEDIUM | “spring-back ... controlled door-to-lens wipe” |

**Decision:** `ESCALATION = MODERATE`. Cross-clip complexity is not itself escalation; only the visible consequence progression is counted.

## 9. Luca And The Island Journal

| Evidence beat | Beat role | Escalation evidence | Same strategy? | Gold escalation | Confidence | Evidence reference |
|---|---|---|---|---|---|---|
| Comedy montage | MONTAGE | Coconut, fishing, shelter, cave, and journal events are loosely connected | No single central mechanic | NOT_APPLICABLE | HIGH | “COMEDY MONTAGE” / multiple unrelated activities |
| Dream twist | TWIST | Journal persists after waking, but not as a central established rule | N/A | NOT_APPLICABLE | HIGH | “same journal in his hand” |

**Decision:** `ESCALATION = NOT_APPLICABLE`. There is no single local mechanic whose magnitude or stakes can be measured.

## Family 2 Gold Summary

| Asset | Gold escalation | Confidence | Review status |
|---|---|---|---|
| Sticky Ball | STRONG | HIGH | APPROVED |
| Ball-Multiplying Crocodile | STRONG | HIGH | APPROVED |
| Upside-Down Chair | STRONG | MEDIUM | APPROVED |
| Lamp | MODERATE | MEDIUM | APPROVED |
| Snack Box | MODERATE | MEDIUM | APPROVED |
| Box Cat | MODERATE | MEDIUM | APPROVED |
| Spot-Stealing Cat | WEAK | HIGH | APPROVED |
| Sneaky Door | MODERATE | MEDIUM | APPROVED |
| Island Journal | NOT_APPLICABLE | HIGH | APPROVED |

## Baseline Comparison

Current v1.7 baseline observations:

- Sticky Ball canonical escalation sees wall-flex/resistance evidence, but the assessment dimension remains `NEEDS_ATTENTION`; this is the primary Family 2 divergence.
- Crocodile canonical evidence sees consequence expansion from quantity output, but parser attempt evidence is incomplete and the assessment remains `UNKNOWN`.
- Chair has the bounded parser timeout baseline and therefore no current escalation evidence.
- Lamp, Snack Box, Box Cat, Spot Cat, and Sneaky Door retain partial/unknown parser escalation evidence.
- Island Journal remains `NOT_APPLICABLE` by Gold Truth and has no central mechanic escalation sequence.

No escalation code or policy has changed in this review step.

## Family 2 Review Lock

The nine escalation labels are human-approved and now locked in Gold Truth. Confidence values remain independent from review status. The current v1.7 baseline is preserved; implementation may now begin with escalation evidence only.
