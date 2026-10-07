# POMPOM GOLDEN V1 — Candidate Curation Review

**Status:** CANDIDATE REVIEW ONLY — NOT FROZEN

**Review date:** 2026-10-06

**Source authority:** Mounted Pompom library at `/Users/benanaktas/project/video/yuvarlak-dunya`, equivalent to the Docker Compose default `${POMPOM_LIBRARY_ROOT:-../../yuvarlak-dunya}`.

**Engine status:** No parser, canonical evidence, rule, ruleset, scorer, assessment, PDF, frontend, or persistence behavior was changed during this curation pass.

**Performance isolation:** No views, reach, watch time, likes, shares, publication outcomes, or prediction tables were read or used for candidate selection. `WINNER_CANDIDATE`, `MIDDLE_CANDIDATE`, and `NEGATIVE_CANDIDATE` below are structural curation labels only.

**Database status:** The local backend was queried for the mounted source directory and returned no matching `contents`/`prompt_versions` rows. Therefore the current canonical source identity is the mounted relative path plus SHA-256 hash. No `contentId` or `promptVersionId` was invented.

## 1. Discovery Summary

| Item | Result |
|---|---:|
| Candidate prompts reviewed | 15 |
| Recommended winner candidates | 3 |
| Recommended middle candidates | 3 |
| Recommended negative candidates | 3 |
| Alternates retained | 6 |
| Real mounted prompt sources | 15 |
| Controlled fixtures used to fill slots | 0 |
| Database prompt identities resolved | 0 |
| Performance metadata inspected | 0 |
| Golden Set frozen | NO |
| Baseline captured | NO |
| Ruleset or engine modified | NO |

The candidate set is intentionally broader than the final nine. The final nine require human approval before any manifest, Gold Truth, policy expectation, baseline, or release gate is created.

## 2. Source and Lineage Caveats

- Mounted file identity is strong: every candidate below has an existing source file and SHA-256 hash.
- Database lineage is currently unavailable: the local backend lookup for `library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026` returned zero imported prompt records.
- Several real prompts use formats that the current parser does not fully recognize. That is a calibration observation, not a reason to change the parser during this phase.
- A bounded parser discovery probe used a 12-second limit per file. The following complete prompt sources exceeded that limit: Giant Spoon, Upside-Down Chair, Wrong Shoes, and Running Backpack. They remain human-review candidates with `PARSER_COMPATIBILITY_REVIEW`.
- Box Cat and Spot-Stealing Cat are structurally complete prompts, but their prose is not timestamp-labelled in the format the current parser expects; the parser returned zero timeline beats. This is a representation/ingestion gap, not evidence that the prompts are empty.
- Crocodile, Snack Box, Balloon, Lamp, Tiny Door, and Tail Trap parse partially or structurally, but the current parser does not extract all of their prose-level attempts. Their candidate labels below are based on direct prompt inspection and are not engine output.
- No final candidate is being called a historical winner or loser. The corpus roles are benchmark-balance metadata only.

## 3. Candidate Table

`Source` values use `REAL_PRODUCTION_PROMPT` for a mounted production prompt and `REAL_PRODUCTION_PROMPT_ARCHIVE` for the archived multi-clip production prompt. `Lineage` describes source-file identity, not performance.

| ID | Candidate / source path | SHA-256 | Source | Recommended slot | Mechanic family | Structural calibration value | Completeness | Lineage |
|---|---|---|---|---|---|---|---|---|
| `sticky-ball-01` | `09_SOCIAL_REELS/new14092026/Absurd_Moments/01_luca_sticky_ball/01_video_prompt.txt` | `378a39e7d625d5e4e36cd23436b53b0d410b326f02a3c77406853cc51e965e01` | REAL_PRODUCTION_PROMPT | WINNER_CANDIDATE | sticky / deformation | Canonical Luca benchmark; two attempts; reactive CATCH versus intended SQUEEZE; wall-flex escalation; fake resolution; same-rule cheek payoff | HIGH | HIGH file identity; DB row not imported |
| `ball-crocodile-01` | `09_SOCIAL_REELS/new14092026/Absurd_Moments/07_luca_ball_spitting_crocodile/01_video_prompt.txt` | `a4f76d88158463b989250ddfec943677d1f848db3a86bbae9200871516c8ccba` | REAL_PRODUCTION_PROMPT | WINNER_CANDIDATE | quantity multiplication / object interaction | One stable rule with measurable escalation: 1 → 3 → 6 → fountain; fake resolution; sound-off physical readability | HIGH | HIGH file identity; DB row not imported |
| `upside-chair-01` | `09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/1-The Upside-Down Chair/prompt.md` | `6db5f744f51dca45b4be2133e8d88648b839e5d1fb5b742be5f1aaa3d016502a` | REAL_PRODUCTION_PROMPT | WINNER_CANDIDATE | spatial inversion / autonomous recurrence | Immediate anomaly; repeated chair return; character intervention; stronger final stalemate; explicit loop | HIGH | HIGH file identity; parser compatibility review |
| `giant-spoon-01` | `09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/3-The Giant Spoon/prompt.md` | `f191e44aae623bfc0124f1684821ad679179f9b823b6d6a333a094135fdea132` | REAL_PRODUCTION_PROMPT | WINNER_ALTERNATE | oversized-object deformation / size changes | Strong first frame; large → micro → normal spoon progression; final bowl-size twist; sound-off anomaly | HIGH, 18-second plan | HIGH file identity; parser compatibility review |
| `box-cat-01` | `09_SOCIAL_REELS/new14092026/pompom_vs_animals/03_luca_vs_box_cat/prompt.md` | `d93add25456b009ad9937920d1d40d56cbbd517ba6883b743f99a6c6f60bb854` | REAL_PRODUCTION_PROMPT | MIDDLE_CANDIDATE | stubborn return / animal-object claim | Three repeated interventions under one explicit rule; clear fake win; tests specialized return-loop applicability and strategy-diversity policy | HIGH prose; parser timeline gap | HIGH file identity; DB row not imported |
| `spot-cat-01` | `09_SOCIAL_REELS/new14092026/pompom_vs_animals/04_kiko_vs_spot_stealing_cat/prompt.md` | `76ea701ceb81d9bc4bc0ac6b9ed6998cea84c8423bb4fa1fa9793d9c523622e5` | REAL_PRODUCTION_PROMPT | NEGATIVE_CANDIDATE | repeated target-claim / animal-object interaction | Three target switches plus decoy, but the cat uses the same claim mechanism; useful negative for Beat ≠ Attempt and repeated strategy ≠ diversity | HIGH prose; parser timeline gap | HIGH file identity; DB row not imported |
| `snack-box-01` | `09_SOCIAL_REELS/new14092026/easy uploaded/2- Mimi and the Snack Box That Keeps Changing/prompt.md` | `513554d245fefa31659587f26144ec53cbc099b867da9180114305dc845b1154` | REAL_PRODUCTION_PROMPT | MIDDLE_CANDIDATE | changing contents / object-state recurrence | Clear desire, repeated tests, normal-looking fake win, immediate recurrence; moderate payoff and strategy semantics | HIGH | HIGH file identity; DB row not imported |
| `balloon-01` | `09_SOCIAL_REELS/new14092026/easy uploaded/1- Arda and the Balloon That Won’t Come Down/prompt.md` | `7a9d3ef6c22d4b7a921ed61e7aa6e05ab5f9d149aa42496fd694758bc4c2770b` | REAL_PRODUCTION_PROMPT | MIDDLE_CANDIDATE | autonomous floating object / pursuit | Clear anomaly and explicit goal; several physical attempts; final hat consequence; useful producibility pressure from stool/grabber/hat/object motion | HIGH | HIGH file identity; DB row not imported |
| `lamp-01` | `09_SOCIAL_REELS/new14092026/easy uploaded/4- Kiko and the Lamp That Hates Being Watched /prompt.md` | `e2a4c2b2e3ab5ed7927831c2c264e779c9d9b251b6e979e997c1c271bd7ff0bc` | REAL_PRODUCTION_PROMPT | MIDDLE_CANDIDATE | observation-dependent state change | Strong first-frame-readable rule; repeated watch/unwatch tests; possible plateau; secondary light expansion tests mechanic/payoff consistency | HIGH | HIGH file identity; DB row not imported |
| `tiny-door-01` | `09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/4-The Tiny Door/prompt.md` | `8270013d8030e43e862a4c51992cfcce6576795a1baf30a9091d729a2f47f3fe` | REAL_PRODUCTION_PROMPT | WINNER_ALTERNATE | spatial size transformation / nested recurrence | Immediate shrink anomaly; size escalation; normal-size fake win; nested tiny-door payoff and loop | HIGH, 17-second plan | HIGH file identity; DB row not imported |
| `wrong-shoes-01` | `09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/2- The Wrong Shoes/prompt.md` | `89b941d1cdb6e3e9b60d7b5f6ed4c5f9fd46b8bfbe74d8f2461b931faadda210` | REAL_PRODUCTION_PROMPT | MIDDLE_ALTERNATE | directional opposition / autonomous footwear | Immediate anomaly; explicit left/right semantics; repeated correction; backward final motion; parser compatibility review | HIGH, 17-second plan | HIGH file identity; parser compatibility review |
| `running-backpack-01` | `09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/5-The Running Backpack/prompt.md` | `1f843a33e1d5314fabeed7ccf642f81188e7a4b74934c755f0623c6decc8156f` | REAL_PRODUCTION_PROMPT | WINNER/MIDDLE ALTERNATE | autonomous object / command inversion | Immediate autonomous object; learned STOP/GO rule; object carries character at final; strong producibility and contact-continuity test | HIGH, 17-second plan | HIGH file identity; parser compatibility review |
| `sneaky-door-01` | `09_SOCIAL_REELS/archive/MIMI_VS_THE_SNEAKY_DOOR/mimi-sneaky-door-compact-generation-prompt.md` | `f85635f1f10b4834ade72f8091a4a2f2698525d474f02285fa374b56c9c14392` | REAL_PRODUCTION_PROMPT_ARCHIVE | NEGATIVE_CANDIDATE | autonomous door / multi-clip continuity | Three 5-second clips, state handoff anchors, two characters across later clip, door-to-lens wipe; useful generation/continuity stress case | HIGH production contract; multi-clip | HIGH file identity; archived DB row not imported |
| `tail-trap-01` | `09_SOCIAL_REELS/new14092026/animals /4-The Tail Trap — Crocodile or Lizard?/prompt.md` | `269d936718b8531a9d2535894e6431873a4588ef02bea9d46271b3de6878666c` | REAL_PRODUCTION_PROMPT | MIDDLE/NEGATIVE ALTERNATE | delayed identity reveal / scale joke | Giant-tail hook, delayed lizard reveal, educational goal, long-tail payoff; 18-second high temporal-load candidate | HIGH, 18-second plan | HIGH file identity; DB row not imported |
| `island-journal-01` | `09_SOCIAL_REELS/new14092026/classic story-1/03_luca_and_the_island_journal/01_video_prompt.txt` | `2ef992226b13e968e43f065a6cad606039c3d7af27e92577ec754d9d342830de` | REAL_PRODUCTION_PROMPT | NEGATIVE_CANDIDATE | montage / late dream twist | 25.5-second plan with several loosely connected activities and a late dream reveal; useful setup/pacing/central-mechanic negative | HIGH source text; long-form for reel target | HIGH file identity; DB row not imported |

## 4. Coverage Matrix

The matrix below is a **human curation map**, not engine output and not Gold Truth. `Y` means the prompt visibly exercises the dimension; `M` means it exercises it moderately or with a known ambiguity; `G` means the source is a useful gap/negative case; `R` means the dimension needs review after parser-compatible ingestion.

| Candidate | Hook / first-frame anomaly | Goal | Central mechanic | Active attempts / distinct strategies | Escalation / progression | Realization / fake resolution | Payoff / loop | Producibility / temporal | Specialized applicability / evidence |
|---|---|---|---|---|---|---|---|---|---|
| Sticky Ball | Y | Implicit observable | Sticky deformation | 2 / PULL + TEST-SQUEEZE | Y, wall scope expands | Y / Y | Strong / no explicit loop | Low–moderate / 15s | Return-loop candidate; high evidence |
| Ball-Multiplying Crocodile | Y | Explicit physical action | Input count produces larger output count | Repeated count actions / quantity, not new strategy | Strong measurable 1→3→6→fountain | M / Y | Strong / hard cut | Moderate ball-contact load / 15s | No specialized profile; parser gap |
| Upside-Down Chair | Y | Sit/use chair | Chair flips autonomously | Repeated correction / same rule | Strong recurrence and final state | Y / Y | Strong / explicit loop | Moderate / 17s | Stubborn-return candidate; parser timeout |
| Giant Spoon | Y | Use spoon / size vocabulary | Object size changes | Multiple interaction beats / size strategy | Strong size progression | M / Y | Strong / loop | Moderate-high / 18s | Size/temporal review; parser timeout |
| Luca Box Cat | Y | Use empty box | Cat reclaims empty box | 3 / repeated claim intervention | Resistance through recurrence | Y / Y | Moderate / hard cut | Low–moderate / 15s | Stubborn-return applicability; parser gap |
| Kiko Spot Cat | Y | Sit in open spot | Cat claims committed target | 3 + decoy / same claim strategy | Moderate repetition | Y / Y | Weak–moderate / hard cut | Moderate / 15s | Negative strategy-diversity case; parser gap |
| Snack Box | Y | Get cracker | Contents change between openings | Repeated tests / semantics need review | Moderate state progression | M / Y | Moderate / immediate recurrence | Moderate / 15s | General rules; parser partial |
| Arda Balloon | Y | Catch balloon | Balloon stays out of reach | Several physical attempts / tool changes | Strong escape and hat consequence | M / Y | Strong / loop | High contact/object load / 15s | Producibility stress case |
| Kiko Lamp | Y | Read/use lamp | Lamp changes state when unwatched | Repeated watch tests / mostly same strategy | Plateau then second light | M / Y | Moderate / loop | Moderate / 15s | Scope/applicability and payoff consistency |
| Tiny Door | Y | Use door | Door changes size / nested doors | Repeated size interaction / size not strategy | Strong size escalation | Y / Y | Strong / loop | Moderate / 17s | General; parser partial |
| Wrong Shoes | Y | Walk normally | Shoes choose conflicting directions | Corrections / direction control | Strong direction escalation | M / Y | Strong / loop | Moderate / 17s | General; parser timeout |
| Running Backpack | Y | Retrieve/wear backpack | Object obeys inverted commands and moves itself | Repeated command tests / command strategy | Strong final attached motion | Y / Y | Strong / loop | High contact/continuity / 17s | Producibility stress case; parser timeout |
| Sneaky Door | Y | Keep door controlled | Door closes/opens against character | Multi-clip actions / cross-clip state | Moderate recurrence | Y / Y | Strong / visual loop bridge | High multi-clip continuity / 3×5s | Continuation-lock and visual continuity candidate |
| Tail Trap | Y | Identify animal | Huge tail masks tiny lizard identity | Few actions / reveal rather than problem-solving | Tail length is final escalation | M / N/A | Strong / loop | High 18s temporal load | Educational family; parser high load |
| Island Journal | M | Explore/survive island | No single central impossible rule | Many montage activities / low strategy coherence | Weakly connected montage | M / N/A | Late dream twist / no clear loop | High 25.5s pacing load | Negative central-mechanic/evidence case |

## 5. Recommended Final 9 — NOT YET FROZEN

### Winner-corpus proposal

#### W1 — Luca Sticky Ball

Retain as the primary canonical benchmark. It directly exercises the recently fixed strategy, escalation, realization, fake-resolution, payoff, temporal-load, specialized-applicability, confidence, PDF, and representation paths.

#### W2 — Luca Ball-Multiplying Crocodile

Adds a materially different mechanic: a deterministic quantity transformation. It tests whether escalation can be strong without a new strategy, whether numeric consequence magnitude remains tied to one rule, and whether a final fountain is judged as same-rule payoff rather than a random new mechanic.

#### W3 — Upside-Down Chair

Adds a spatial inversion and autonomous recurrence family. It exercises first-frame anomaly, repeated return behavior, character intervention, stronger final stalemate, loop evidence, and specialized-rule applicability without reusing deformation or multiplication.

### Middle-corpus proposal

#### M1 — Kiko and the Lamp That Hates Being Watched

The opening rule is immediately readable and the character tests it repeatedly. The second-light expansion is structurally interesting but can produce a moderate payoff or mechanic-consistency judgment. This is useful for distinguishing plateau from failure and for scope/applicability checks.

#### M2 — Mimi and the Snack Box That Keeps Changing

The prompt has a clear object goal, repeated testing, an apparent normal-state win, and an immediate recurrence. It is a good middle case for realization, fake resolution, consequence variety, and the difference between a changing result and a distinct strategy.

#### M3 — Luca and the Box Cat

The central rule is explicit and visually testable, but the three attempts are deliberately close variants of the same claim intervention. It exercises the boundary between valid recurrence/escalation and insufficient strategy diversity, including the `STUBBORN_RETURN_LOOP` candidate path.

### Negative-corpus proposal

#### N1 — Kiko and the Spot-Stealing Cat

The prompt repeats the same target-claim behavior over multiple spots, including a decoy. It is a direct negative for counting repeated choreography as distinct strategies and for confusing more attempts with more problem-solving variety.

#### N2 — Mimi vs. the Sneaky Door

The archived production prompt requires three separate five-second clips, state handoffs, exact end-frame anchors, two-character continuity in the final clip, and a controlled door-to-lens transition. It is a real technical complexity/continuation-lock negative candidate rather than a synthetic failure.

#### N3 — Luca and the Island Journal

The 25.5-second prompt contains several loosely connected montage activities and a late dream reveal rather than one crisp central impossible rule. It exercises setup/pacing overload, central-mechanic clarity, payoff causality, evidence completeness, and the distinction between a long story prompt and a short-form creative mechanic.

## 6. Alternates

1. **Giant Spoon** — strong winner alternate for oversized-object/scale mechanics. It is a good candidate, but its 18-second plan and current parser timeout make it a less clean first winner than Upside-Down Chair.
2. **Tiny Door** — strong winner/middle alternate for spatial scale and nested recurrence. It is structurally complete, but overlaps with Upside-Down Chair on immediate physical impossibility and educational dialogue.
3. **Running Backpack** — strong winner/middle alternate for autonomous-object and command inversion. It exercises high contact/continuity complexity and overlaps with the recurrence family.
4. **Wrong Shoes** — middle alternate for directional opposition and sound-off readability. It has a strong prompt but the current parser exceeded the bounded discovery timeout.
5. **Tail Trap — Crocodile or Lizard?** — middle/negative alternate for delayed identity reveal and long-form educational pacing. It is useful if the final set needs explicit content-family coverage.
6. **Luca Softening Steps** — negative/coverage alternate. The source is real, but it is closer to a first-frame anomaly prompt than a complete 15-second story: no explicit attempt sequence, payoff, or loop is supplied.
7. **Wrong Destination — REJECTED** — structural negative reference only. It explicitly has no production prompt and therefore should not enter the first frozen nine unless human review approves a rejected-concept source as a negative fixture.
8. **Grow/Rebound Combo — REJECTED** — structural negative reference only. It also has no production prompt and should remain outside the first nine unless explicitly approved.

## 7. Duplicate and Overlap Risks

- Box Cat and Spot-Stealing Cat are close animal/object recurrence cases. Keeping both would be valuable only if the cohort intentionally contrasts a specialized-return candidate with a negative strategy-diversity case.
- Upside-Down Chair, Tiny Door, Wrong Shoes, and Giant Spoon all belong to the high-readability `What’s Wrong?` family. The proposal keeps only Chair in the winners and retains the others as alternates to avoid overrepresenting the same series grammar.
- Sticky Ball and Ball-Multiplying Crocodile are both Absurd Moments but exercise different mechanics: deformation/persistence versus quantity multiplication. Both are retained because the rule families are materially different.
- Snack Box and Lamp both use repeated tests followed by a fake or apparent resolution. Their object-state mechanisms differ, so the pair is useful for realization/fake-resolution calibration.
- Sneaky Door and Island Journal are both negative for production shape, but one is technical multi-clip continuity while the other is central-mechanic/pacing overload.

## 8. Missing or Weak Rule-Family Coverage

The proposed nine cover strategy canonicalization, recurrence, escalation, payoff, loop, fake resolution, goal/realization, quantity escalation, deformation, spatial impossibility, autonomous objects, sound-off readability, and producibility pressure.

Still weak or missing before freeze:

- A clean real prompt with explicit `REALIZATION`/`DECISION` language but no fake resolution.
- A clean real prompt whose final payoff is a new consequence that is clearly same-rule derived without recurrence.
- A strong sound-off prompt with no mandatory dialogue and no text overlay beyond Sticky Ball/Crocodile.
- A real prompt with a clearly applicable specialized rule other than stubborn return.
- A parser-compatible real source for Box Cat/Spot Cat; both currently need a prose-to-IR ingestion decision.
- A database-linked `contentId`/`promptVersionId` for every candidate.

These gaps should be handled in the human review decision, not by inventing prompts or modifying the parser now.

## 9. Source/Lineage Concerns

1. The mounted source path and hash are available for all 15 candidates.
2. The local backend database currently contains no matching imported prompt records for the mounted social-reel directory; canonical database IDs are therefore unresolved.
3. Four complete prompts exceeded the bounded 12-second parser discovery probe: Giant Spoon, Upside-Down Chair, Wrong Shoes, and Running Backpack. This is a candidate-review warning and a future parser/performance investigation item, not a curation-time engine change.
4. Box Cat and Spot Cat are complete real prompt files but not timestamp-labelled for the current parser, so their parser-derived canonical evidence is not reliable without a separate ingestion decision.
5. Rejected concept documents are source artifacts, not production prompts. They remain alternates only.
6. No social or platform performance fields were read for any candidate.

## 10. Proposed Final 9 — Approval Required

| Slot | Proposed candidate | Status |
|---|---|---|
| W1 | Luca Sticky Ball | PROPOSED — human approval required |
| W2 | Luca Ball-Multiplying Crocodile | PROPOSED — human approval required |
| W3 | Upside-Down Chair | PROPOSED — human approval required |
| M1 | Kiko and the Lamp That Hates Being Watched | PROPOSED — human approval required |
| M2 | Mimi and the Snack Box That Keeps Changing | PROPOSED — human approval required |
| M3 | Luca and the Box Cat | PROPOSED — human approval required |
| N1 | Kiko and the Spot-Stealing Cat | PROPOSED — human approval required |
| N2 | Mimi vs. the Sneaky Door | PROPOSED — human approval required |
| N3 | Luca and the Island Journal | PROPOSED — human approval required |

**Nothing in this table is frozen.** No `POMPOM_GOLDEN_V1` manifest, Gold Truth, policy expectation, v1.7 baseline, comparator, or CI release gate has been created.

## 11. Infrastructure Work After Human Approval

After the final nine are approved, the next infrastructure plan should explicitly cover:

- tracked calibration artifacts under `intelligence/docs` rather than ignored root `/docs`;
- manifest and hash-drift detection;
- separate structural Gold Truth and ruleset-scoped Policy Expectation files;
- a deterministic no-network runner using frozen prompt text and frozen semantic evidence where needed;
- complete parser/canonical/ruleset/engine/assessment/scoring/semantic/report/frontend/git fingerprinting;
- one coherent calibration-run/snapshot persistence contract, reusing existing prompt hash and report snapshot primitives instead of another validation table;
- a Golden Regression Comparator that classifies semantic and policy changes separately;
- a source-controlled CI gate requiring `NEW SEMANTIC REGRESSIONS = 0` and `UNEXPECTED POLICY REGRESSIONS = 0`;
- a performance-import architecture test for the pre-render quality package boundary;
- end-to-end ML JSON → backend DTO/PDF → frontend representation checks;
- human Gold Truth review for all MEDIUM/LOW-confidence assertions before freezing.

## 12. Human Decision Needed

Please approve, replace, or reorder the proposed nine above. In particular, decide whether:

1. Upside-Down Chair should be the third winner, or Giant Spoon/Tiny Door should replace it;
2. Box Cat belongs in the middle cohort, or should be the negative repeated-strategy case;
3. Island Journal is acceptable as a real long-form/setup negative, or should be replaced by the real archived Sneaky Door complexity case;
4. the database-not-imported source-path lineage is sufficient for V1 curation, or whether the prompt library must first be imported into canonical `contents`/`prompt_versions` rows.

**STOP CONDITION:** Candidate discovery ends here. No freeze or engine calibration proceeds until the human-approved nine are explicit.
