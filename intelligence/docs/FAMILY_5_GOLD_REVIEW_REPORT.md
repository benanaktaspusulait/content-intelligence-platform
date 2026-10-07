# FAMILY 5 — Specialized Rule Applicability Gold Review

**Golden Set:** `POMPOM_GOLDEN_V1`  
**Ruleset under review:** `RULESET_1.7`  
**Status:** **HUMAN-REVIEW PREPARATION — ENGINE AND GOLD TRUTH NOT CHANGED**  
**Scope:** Family 5 only — specialized rule applicability.  
**Next family:** Family 6 and all later families have not started.

## 1. Scope and non-goals

This review asks only whether a specialized rule belongs to the semantic domain of a concept. It does not judge whether an applicable rule passes or fails.

No files were changed in the parser, canonical evidence, RuleEngine, scorer, assessment aggregation, ruleset, policy expectations, creative grading, render authorization, or Golden Truth. No performance data, corpus role, Meta/public-comment work, or nearby issue was used.

The exact nine frozen prompts remain the only Golden assets. Prompt bytes and hashes are governed by:

- `intelligence/data/golden/pompom-golden-v1/manifest.yaml`
- `intelligence/data/golden/pompom-golden-v1/approved_hashes.yaml`

## 2. Definition and taxonomy

### Specialized rule

A rule is specialized when it requires semantic preconditions beyond the generic fact that the input is a short video. The preconditions must describe a rule domain—such as one-object autonomous return across a usable/blocked boundary—not merely consume a semantic field or match an object/character keyword.

`RULE APPLICABILITY != RULE OUTCOME`.

A concept may be:

- `APPLICABLE` and then produce `PASS`, `FAIL`, or `UNKNOWN` as the rule outcome;
- `NOT_APPLICABLE` because the concept is outside the rule domain;
- `UNKNOWN` because the concept may belong to the domain but the required evidence is insufficient.

`NOT_APPLICABLE` is not `FAIL`, a creative zero, missing evidence, a blocker, a warning, or a weak concept. `UNKNOWN` is not `NOT_APPLICABLE` and is not `FAIL`.

### Review labels

The matrix below uses only the requested taxonomy:

- **APPLICABLE:** all mandatory semantic preconditions are established by the frozen source and trusted Family 1–4 evidence. This is a proposed review label, not an engine activation.
- **NOT_APPLICABLE:** positive semantic evidence places the concept outside the specialized rule domain.
- **UNKNOWN:** a meaningful candidate or near-match exists, but a mandatory condition or the high-confidence activation boundary cannot be decided safely.

Every proposed label in this report is `REVIEW_REQUIRED`. No `reviewStatus: APPROVED` was added.

## 3. Actual specialized-rule inventory

### 3.1 Effective RULESET_1.7 inventory

The runtime audit confirms that `RULESET_1.7.yaml` extends `RULESET_1.6.yaml`, and the current loader merges only that immediate base. The effective RULESET 1.7 contains eight rule entries:

```text
MINI_STORY_LOCK
GOAL_VISIBLE_EARLY
TEMPORAL_COMPLEXITY_SPLIT_GATE
BEAT_DENSITY_RULE
CONTINUATION_LOCK
STUBBORN_RETURN_LOOP
STUBBORN_RETURN_HOOK
STUBBORN_RETURN_PAYOFF
```

Only the three `STUBBORN_RETURN_*` entries are specialized Family 5 targets. They are declared with global outer scope, but their evaluators perform profile-specific applicability gating. A global outer scope therefore does not mean that the specialized semantic domain applies to every concept.

| Rule ID | Rule name | Severity | Family | Classification | Current applicability condition | Evidence inputs | Current non-applicable behavior | Known risks |
|---|---|---:|---|---|---|---|---|---|
| `STUBBORN_RETURN_LOOP` | Stubborn Return Loop | `BLOCKER` | `progression` | **SPECIALIZED** profile rule | `engine_profile_evidence(ir).active` must be true. Explicit valid profile requires every profile signal; inferred activation requires HIGH confidence. MEDIUM remains candidate-only. | `engine_profile_evidence`: dominant object, visible boundary, safe state, autonomous return, recurrence, intervention, escalation, no dead reset, and state-memory signals. | Active → `PASS`; candidate-only → `UNKNOWN`; no candidate → `NOT_APPLICABLE`. | Current selector is lexical/field based. It can under-detect a true source-backed profile and can produce candidate-only evidence from superficial return-like terms. |
| `STUBBORN_RETURN_HOOK` | Stubborn Return Hook | `CRITICAL` | `hook_strength` | **SPECIALIZED** dependent exception | Applies only when the same stubborn-return profile is active. Active profile then requires an immediate visible problem/boundary or textual first-frame evidence. | Profile evidence plus `ir.hook.visibleProblem`, `textualFirstFrameIntent`, and fixed-boundary signal. | Inactive profile, including candidate-only profile, → `NOT_APPLICABLE`; active profile can produce `PASS` or `FAIL`. | The evaluator does not require the `characterAlreadyEngaged` field supplied by a focused synthetic test. “Access obstruction” versus “physical threat” remains a semantic boundary. |
| `STUBBORN_RETURN_PAYOFF` | Stubborn Return Payoff | `CRITICAL` | `final_payoff` | **SPECIALIZED** dependent exception | Applies only when the profile is active. Active profile then requires final same-rule evidence, active character engagement at the cut, final intensity at least the earlier maximum, and a non-empty `finalPayoff`. | Profile evidence, final beat action/consequence, beat intensities, and `finalPayoff`. | Inactive profile → `NOT_APPLICABLE`; active profile with incomplete final evidence → `FAIL`. | The evaluator uses a separate lexical definition of same-rule payoff rather than the frozen Family 4 canonical mechanic/payoff evidence. A moderate same-rule payoff is not automatically a specialized strong-stalemate payoff. |

### 3.2 Related rules that are not Family 5 specialized targets

These rules were inspected so a generic global rule is not incorrectly promoted into Family 5:

- `MINI_STORY_LOCK`, `GOAL_VISIBLE_EARLY`, `TEMPORAL_COMPLEXITY_SPLIT_GATE`, `BEAT_DENSITY_RULE`, and `CONTINUATION_LOCK` are generic story/plan-structure rules in the effective immediate 1.6 base. Some consume profile evidence for an exception, but their semantic domain is not a specialized return/reclaim profile.
- `CONCEPT_009` (`Single-Agent Object Mechanic`) is a genuinely specialized `CONTENT_FAMILY: social_reel` rule declared in `RULESET_1.5.yaml`, but it is **not effective in the current RULESET_1.7 runtime** because the loader does not recursively load the 1.5 base through 1.6. It is recorded as a historical/non-effective declaration, not as a current Family 5 target.
- `HOOK_002` and `ATTEMPT_002` are global rules with historical/profile exception branches, not separate specialized applicability domains. They are also not effective entries in the current one-level RULESET_1.7 load.
- `PAYOFF_001` is a global “not repeat of opening” rule. Historical metadata lists it as an exception target, but its evaluator has no profile-specific applicability branch and it is not effective in the current RULESET_1.7 load.

The one-level inheritance behavior is a repository/runtime fact recorded here, not a change request.

## 4. Rule-specific mandatory preconditions

### 4.1 Base profile — `STUBBORN_RETURN_LOOP`

All of the following are mandatory for proposed `APPLICABLE` status:

1. One dominant object or entity carries the local rule.
2. One visible, stable safe/danger or usable/blocked boundary exists.
3. The same entity autonomously returns or reasserts after displacement/control; ordinary recurrence of a property is insufficient.
4. The return/reassertion is established more than once or is an explicit repeated structural rule.
5. The character actively intervenes against the same local boundary at least twice.
6. Resistance, consequence, scope, difficulty, or stakes materially escalate.
7. There is no dead reset that breaks the return-loop structure.
8. An observable safe/usable state exists, and the profile remains low enough in state memory to match the rule’s intended one-generation domain.

Activation policy observed in RULESET 1.7 is separate from Gold applicability: explicit valid evidence or inferred HIGH evidence may activate the engine; MEDIUM remains candidate-only.

### 4.2 Dependent hook — `STUBBORN_RETURN_HOOK`

Mandatory conditions:

1. The base specialized return profile is applicable/active under its own semantic conditions.
2. The opening contains an immediate visible physical threat or boundary conflict.
3. The character is already engaged with that conflict in the opening window.

The source must not become applicable merely because an opening contains a door, cat, chair, sticky object, or ordinary obstruction.

### 4.3 Dependent payoff — `STUBBORN_RETURN_PAYOFF`

Mandatory conditions:

1. The base specialized return profile is applicable/active under its own semantic conditions.
2. The final consequence is causally tied to the same return/reclaim rule.
3. The character remains actively engaged at the cut.
4. The final state is materially stronger than the earlier relevant state.
5. A final payoff payload exists.

A Family 4 `SAME_RULE` payoff is evidence for causal consistency, not automatic proof that this narrower specialized payoff profile applies.

## 5. Frozen evidence register

The review uses the exact prompt files and frozen Family 1–4 evidence. Corpus role and performance data are excluded.

| Key | Frozen source / evidence used |
|---|---|
| `SB` | `prompts/sticky-ball-01.txt`; explicit sticky physical rule; Family 1 `PULL` + `TEST_SQUEEZE`; Family 4 `STICKY_DEFORMATION`, recurrence, strong same-rule cheek payoff. |
| `CROC` | `prompts/ball-crocodile-01.txt`; explicit `more balls than received` rule; Family 1 `THROW_TOSS` + `ROLL/TEST`; Family 4 `QUANTITY_MULTIPLICATION`, fake resolution, fountain payoff. |
| `CHAIR` | `prompts/upside-chair-01.md`; chair flips autonomously when Kiko looks away and with Kiko on it; Family 1 `FLIP` + `GUARD_AND_APPROACH`; Family 4 autonomous inversion, recurrence, strong same-rule payoff. Runtime asset is a parser-timeout known issue. |
| `LAMP` | `prompts/lamp-01.md`; watched lamp behaves and unwatched lamp switches off; Family 1 observation-control strategy; Family 4 observation-dependent light. |
| `SNACK` | `prompts/snack-box-01.md`; contents change between openings while the box remains stable; Family 1 reopen/control strategies; Family 4 changing contents. |
| `BOX` | `prompts/box-cat-01.md`; “whenever the box becomes empty and usable, the cat claims it again”; Family 1 `DISPLACE`, `RELOCATE`, `GUARD`; Family 4 `STUBBORN_RETURN_ANIMAL_CLAIM`, fake resolution, recurrence, moderate same-rule payoff. |
| `SPOT` | `prompts/spot-cat-01.md`; cat claims the exact spot Kiko commits to; Family 1 three attempts but one `COMMIT_TO_TARGET` strategy; Family 2 weak escalation; Family 4 repeated target claim. |
| `DOOR` | `prompts/sneaky-door-01.md`; three image-linked clips, door opens/closes against controlled movement, final door-to-lens wipe; Family 4 autonomous sneaky door and multi-clip boundary. |
| `ISLAND` | `prompts/island-journal-01.txt`; coconut/fishing/shelter montage and final journal dream reveal; Family 1 zero attempts; Family 3 no established goal/realization; Family 4 no central mechanic, recurrence, or payoff. |

## 6. Nine-asset proposed applicability review

The following is the proposed Family 5 review matrix. `Current` is the actual v1.7 RuleEngine outcome for that specialized rule, not a proposed Gold label. For the eight parsed assets, current outcomes are consistently `LOOP=UNKNOWN`, `HOOK=NOT_APPLICABLE`, and `PAYOFF=NOT_APPLICABLE`; the Chair timeout has no rule evaluations. `goldVsCurrent` uses the requested categories and is intentionally not a release assertion.

| Asset | Rule | Proposed applicability | Confidence | Mandatory-precondition evidence / reasoning | Current engine applicability | Gold vs current | First likely root layer |
|---|---|---|---|---|---|---|---|
| Sticky Ball | `STUBBORN_RETURN_LOOP` | `NOT_APPLICABLE` | HIGH | `SB`: sticky deformation, not one entity reclaiming a fixed usable/blocked boundary. Snap-back and cheek recurrence are Family 4 recurrence/payoff only. | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT` — candidate, not active false-positive rule outcome | Canonical profile selector |
| Sticky Ball | `STUBBORN_RETURN_HOOK` | `NOT_APPLICABLE` | HIGH | Opening is already a static stuck-ball anomaly; no specialized active-threat exception is needed. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Sticky Ball | `STUBBORN_RETURN_PAYOFF` | `NOT_APPLICABLE` | HIGH | Cheek stick is a strong sticky same-rule payoff, not a specialized return-loop stalemate. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Ball-Multiplying Crocodile | `STUBBORN_RETURN_LOOP` | `NOT_APPLICABLE` | HIGH | `CROC`: quantity output `1→3→6→fountain`; multiple balls and multiplication are not autonomous return of one bounded entity. | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT` — recurrence was over-read as profile candidacy, but no active rule fired | Canonical profile selector |
| Ball-Multiplying Crocodile | `STUBBORN_RETURN_HOOK` | `NOT_APPLICABLE` | HIGH | Strong ordinary visual hook; no stubborn-return physical-threat exception. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Ball-Multiplying Crocodile | `STUBBORN_RETURN_PAYOFF` | `NOT_APPLICABLE` | HIGH | Fountain is a Family 4 same-rule quantity payoff, not a same-object return stalemate. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Upside-Down Chair | `STUBBORN_RETURN_LOOP` | `UNKNOWN` | MEDIUM | `CHAIR`: one object, usable/upside-down boundary, autonomous inversion, recurrence, intervention, and escalation are all source-supported; whether inversion is this narrower low-memory return domain remains unresolved. | No evaluation; `PARSER_TIMEOUT` | `UNKNOWN_CURRENT` | Parser / Golden runner timeout |
| Upside-Down Chair | `STUBBORN_RETURN_HOOK` | `UNKNOWN` | MEDIUM | Kiko is already entering a sitting action against a visible unsafe chair, but “physical threat” versus access/safety obstruction is unresolved. | No evaluation; `PARSER_TIMEOUT` | `UNKNOWN_CURRENT` | Parser / Golden runner timeout |
| Upside-Down Chair | `STUBBORN_RETURN_PAYOFF` | `UNKNOWN` | MEDIUM | Final chair-with-Kiko inversion is an active same-rule consequence, but dependent activation and the specialized strong-stalemate interpretation remain unresolved. | No evaluation; `PARSER_TIMEOUT` | `UNKNOWN_CURRENT` | Parser / Golden runner timeout |
| Lamp | `STUBBORN_RETURN_LOOP` | `NOT_APPLICABLE` | HIGH | `LAMP`: observation-dependent on/off state, not one entity autonomously reclaiming a fixed boundary. | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT` — candidate-only, not active failure | Canonical profile selector |
| Lamp | `STUBBORN_RETURN_HOOK` | `NOT_APPLICABLE` | HIGH | Opening is an observation test; no immediate specialized physical-threat exception. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Lamp | `STUBBORN_RETURN_PAYOFF` | `NOT_APPLICABLE` | HIGH | Second-light expansion is a moderate light-state payoff, not a specialized active return stalemate. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Snack Box | `STUBBORN_RETURN_LOOP` | `NOT_APPLICABLE` | HIGH | `SNACK`: changing contents recur on reopen; the box itself does not autonomously return or reclaim a fixed boundary. | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT` — candidate-only, not active failure | Canonical profile selector |
| Snack Box | `STUBBORN_RETURN_HOOK` | `NOT_APPLICABLE` | HIGH | Opening is an expectation/content mismatch, not a specialized physical threat. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Snack Box | `STUBBORN_RETURN_PAYOFF` | `NOT_APPLICABLE` | HIGH | Wrong contents after apparent cracker success are Family 4 changing-contents payoff, not a return-loop stalemate. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Box Cat | `STUBBORN_RETURN_LOOP` | `APPLICABLE` | HIGH | `BOX`: one usable empty box, one cat repeatedly reclaims it, three directed interventions, apparent empty safe state, re-claim at the use boundary. This satisfies the base semantic domain. | `UNKNOWN` candidate-only | `FALSE_NEGATIVE_APPLICABILITY` at activation evidence, with current result correctly remaining UNKNOWN rather than FAIL | Canonical profile selector; parser IR lacks required structured profile signals |
| Box Cat | `STUBBORN_RETURN_HOOK` | `UNKNOWN` | MEDIUM | Immediate reach/conflict is clear, but the specialized rule says physical threat; access obstruction may or may not qualify. | `NOT_APPLICABLE` because base profile is inactive | `UNKNOWN_CURRENT` | Dependent RuleEngine gate |
| Box Cat | `STUBBORN_RETURN_PAYOFF` | `APPLICABLE` | MEDIUM | Final cat reclaims the empty box immediately before Luca uses it; Luca remains engaged and the timing is a stronger same-rule stalemate. | `NOT_APPLICABLE` because base profile is inactive | `FALSE_NEGATIVE_APPLICABILITY` at dependent gate | Canonical profile selector / dependent RuleEngine gate |
| Spot Cat | `STUBBORN_RETURN_LOOP` | `UNKNOWN` | MEDIUM | `SPOT`: repeated target claims are a near-match, but targets move and the source does not establish one fixed boundary or autonomous return of one entity. | `UNKNOWN` candidate-only | `MATCH` at taxonomy level, but aggregate projection is missing | Canonical profile selector; semantic boundary remains unresolved |
| Spot Cat | `STUBBORN_RETURN_HOOK` | `UNKNOWN` | MEDIUM | Immediate target conflict and character engagement exist; physical-threat and fixed-boundary conditions do not. | `NOT_APPLICABLE` because base profile is inactive | `UNKNOWN_CURRENT` | Dependent RuleEngine gate |
| Spot Cat | `STUBBORN_RETURN_PAYOFF` | `UNKNOWN` | MEDIUM | Final suspended squat is an active same-rule target claim, but escalation is weak and specialized payoff strength is not established. | `NOT_APPLICABLE` because base profile is inactive | `UNKNOWN_CURRENT` | Dependent RuleEngine gate |
| Sneaky Door | `STUBBORN_RETURN_LOOP` | `NOT_APPLICABLE` | HIGH | `DOOR`: multi-clip continuation/continuity contract and door behavior are distinct from a low-memory one-shot return loop. | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT` — current candidate does not mean active applicability | Canonical profile selector |
| Sneaky Door | `STUBBORN_RETURN_HOOK` | `NOT_APPLICABLE` | HIGH | Immediate door action is ordinary door/continuation evidence, not the specialized threat exception. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Sneaky Door | `STUBBORN_RETURN_PAYOFF` | `NOT_APPLICABLE` | HIGH | Door-to-lens wipe is a strong Family 4 same-rule loop bridge, not the specialized active return stalemate. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Island Journal | `STUBBORN_RETURN_LOOP` | `NOT_APPLICABLE` | HIGH | `ISLAND`: no central mechanic, no focused attempts, no recurrence, and no same-rule payoff; the journal reveal is narrative. | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT` — candidate-only, not active applicability | Canonical profile selector |
| Island Journal | `STUBBORN_RETURN_HOOK` | `NOT_APPLICABLE` | HIGH | Adventure opening has no specialized immediate physical-threat boundary. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| Island Journal | `STUBBORN_RETURN_PAYOFF` | `NOT_APPLICABLE` | HIGH | Same journal after waking is a narrative twist, not a payoff derived from an established mechanic. | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |

### 6.1 Detailed applicable review records

#### `BOX / STUBBORN_RETURN_LOOP`

- **Applicability:** `APPLICABLE` — `HIGH` source confidence; proposed status remains `REVIEW_REQUIRED`.
- **Source evidence:** `box-cat-01.md` states that whenever the box is empty and usable, the cat claims it again. The frozen Family 1 record shows `DISPLACE`, `RELOCATE`, and `GUARD`; Family 4 records `STUBBORN_RETURN_ANIMAL_CLAIM`, fake resolution, recurrence, and same-rule payoff.
- **Mandatory preconditions:** dominant box/entity `ESTABLISHED`; usable/blocked boundary `ESTABLISHED`; autonomous re-claim `ESTABLISHED`; repeated return/reassertion `ESTABLISHED`; active intervention `ESTABLISHED`; escalation through repeated timing/pressure `ESTABLISHED`; no dead reset `ESTABLISHED`; usable safe state `ESTABLISHED`.
- **Reasoning:** This is the clearest source-backed member of the specialized return/reclaim domain. It is not applicable merely because the concept contains a cat or recurrence; the causal empty-box boundary and repeated displacement/control attempts are explicit.
- **Current engine applicability:** `STUBBORN_RETURN_LOOP=UNKNOWN`, with an inferred LOW/`DEFAULT` candidate and `candidate_only=true`. No specialized PASS/FAIL is emitted.
- **Gold vs current:** `FALSE_NEGATIVE_APPLICABILITY` at the profile activation evidence layer, while preserving `UNKNOWN` as the current rule outcome rather than converting it to `FAIL`.

#### `BOX / STUBBORN_RETURN_PAYOFF`

- **Applicability:** `APPLICABLE` — `MEDIUM` confidence; proposed status remains `REVIEW_REQUIRED`.
- **Source evidence:** After the cat stays away and Luca approaches the empty box, the cat moves into the box immediately before Luca’s hands reach it. Family 4 marks the final claim as a moderate same-rule payoff.
- **Mandatory preconditions:** base return/reclaim domain `ESTABLISHED`; same-rule final consequence `ESTABLISHED`; Luca remains actively engaged at the cut `ESTABLISHED`; final timing is stronger than earlier claims `ESTABLISHED`; final payoff payload `ESTABLISHED`.
- **Reasoning:** The final cat claim is a causal active stalemate, but the evidence is MEDIUM for the narrower “stronger specialized payoff” interpretation because Family 4 deliberately labels the payoff `MODERATE`.
- **Current engine applicability:** `NOT_APPLICABLE` because the current base profile is inactive.
- **Gold vs current:** `FALSE_NEGATIVE_APPLICABILITY` at the dependent profile gate; this is not a rule outcome failure.

No Hook rule receives `APPLICABLE` in this review. Box Cat and Chair are `UNKNOWN` because the source establishes immediate engagement/access conflict but the exact Hook domain says physical threat and the implementation does not formally define whether usable-access obstruction qualifies.

## 7. Existing Gold Truth and proposed Family 5 Gold matrix

The current `gold_truth.yaml` already contains the aggregate `SPECIALIZED_RULE_APPLICABILITY` dimension. It was inspected but **not modified**. Its existing labels are:

| Asset | Existing Gold Truth aggregate | Existing confidence | Proposed rule-level interpretation | Review status |
|---|---|---|---|---|
| Sticky Ball | `NOT_APPLICABLE` | HIGH | All three specialized rules `NOT_APPLICABLE` | `REVIEW_REQUIRED` |
| Ball-Multiplying Crocodile | `NOT_APPLICABLE` | HIGH | All three `NOT_APPLICABLE` | `REVIEW_REQUIRED` |
| Upside-Down Chair | `CANDIDATE_REVIEW` | MEDIUM | Loop, Hook, and Payoff `UNKNOWN` | `REVIEW_REQUIRED` |
| Lamp | `NOT_APPLICABLE` | HIGH | All three `NOT_APPLICABLE` | `REVIEW_REQUIRED` |
| Snack Box | `NOT_APPLICABLE` | HIGH | All three `NOT_APPLICABLE` | `REVIEW_REQUIRED` |
| Box Cat | `APPLICABLE_CANDIDATE` | HIGH | Loop `APPLICABLE`; Hook `UNKNOWN`; Payoff `APPLICABLE` | `REVIEW_REQUIRED` |
| Spot Cat | `APPLICABLE_CANDIDATE` | MEDIUM | Loop, Hook, and Payoff `UNKNOWN` pending fixed-boundary decision | `REVIEW_REQUIRED` |
| Sneaky Door | `NOT_APPLICABLE` | HIGH | All three `NOT_APPLICABLE` | `REVIEW_REQUIRED` |
| Island Journal | `NOT_APPLICABLE` | HIGH | All three `NOT_APPLICABLE` | `REVIEW_REQUIRED` |

This is a proposed decomposition of the existing aggregate review dimension. It is not a Gold Truth lock and does not authorize replacing `CANDIDATE_REVIEW` or `APPLICABLE_CANDIDATE` in the frozen file.

## 8. Positive, negative, boundary, and UNKNOWN coverage

| Rule | Positive coverage | Negative coverage | Boundary coverage | UNKNOWN coverage | Assessment |
|---|---|---|---|---|---|
| `STUBBORN_RETURN_LOOP` | Box Cat provides a direct source-backed positive candidate. | Sticky, Crocodile, Lamp, Snack Box, Sneaky Door, Island Journal are semantically excluded. | Chair and Spot Cat test autonomous inversion and repeated target claims against the narrower fixed-boundary return domain. | Chair and Spot Cat preserve meaningful ambiguity; runtime parser/profile gaps add current UNKNOWN behavior. | Good semantic coverage for review; runtime positive activation is not represented by a Golden asset. |
| `STUBBORN_RETURN_HOOK` | No high-confidence positive Golden fixture. | Sticky, Crocodile, Lamp, Snack Box, Sneaky Door, Island Journal. | Box Cat and Spot Cat access/target conflicts; Chair’s unsafe sitting action. | Box Cat, Spot Cat, Chair. | Positive semantic Hook coverage is missing; do not manufacture an active label. |
| `STUBBORN_RETURN_PAYOFF` | Box Cat is a positive active same-rule stalemate candidate. | Sticky, Crocodile, Lamp, Snack Box, Sneaky Door, Island Journal. | Chair and Spot Cat have same-rule final consequences but unresolved specialized strength/domain. | Chair and Spot Cat, plus current parser/profile gaps. | Moderate positive coverage; no high-confidence Hook/payoff activation fixture. |

No tenth Golden prompt is recommended in this review. The existing Box Cat source is the necessary positive semantic candidate, while the existing focused synthetic RULESET 1.7 test fixture covers explicit/high-confidence engine activation without changing the Golden corpus. Any future calibration fixture requires separate approval.

## 9. Current v1.7 baseline and applicability divergences

The frozen v1.7 report is evidence of current behavior, not a Family 5 acceptance result:

- 9 assets and 261 Golden assertions;
- 22 semantic passes, 10 semantic failures, 70 unchanged known issues;
- 62 Gold-review-required rows;
- 0 new semantic regressions and 0 unexpected policy regressions;
- release gate `PASS`.

The three specialized rule outcomes in the eight parsed assets are:

```text
STUBBORN_RETURN_LOOP   = UNKNOWN
STUBBORN_RETURN_HOOK   = NOT_APPLICABLE
STUBBORN_RETURN_PAYOFF = NOT_APPLICABLE
```

`upside-chair-01` is a `PARSER_TIMEOUT`, so no specialized evaluation exists for it. The v1.7 snapshots also show `SPECIALIZED_RULE_APPLICABILITY = null` for all nine assets in both baseline/current projection.

| Rule | Asset group | Proposed Gold | Current v1.7 | Divergence type | First likely root layer |
|---|---|---|---|---|---|
| `STUBBORN_RETURN_LOOP` | Sticky, Crocodile, Lamp, Snack, Sneaky, Island | `NOT_APPLICABLE` | `UNKNOWN` candidate-only | `UNKNOWN_CURRENT`; candidate evidence is not active applicability | Canonical profile selector |
| `STUBBORN_RETURN_LOOP` | Box Cat | `APPLICABLE` | `UNKNOWN` candidate-only | `FALSE_NEGATIVE_APPLICABILITY` at activation evidence | Canonical profile selector / parser IR shape |
| `STUBBORN_RETURN_LOOP` | Spot Cat | `UNKNOWN` | `UNKNOWN` candidate-only | `MATCH` at taxonomy level; source boundary still unresolved | Canonical profile selector |
| `STUBBORN_RETURN_LOOP` | Upside-Down Chair | `UNKNOWN` | no evaluation | `UNKNOWN_CURRENT` | Parser / Golden runner timeout |
| `STUBBORN_RETURN_HOOK` | All parsed assets except Chair | Mostly `NOT_APPLICABLE`; Box/Spot `UNKNOWN` | `NOT_APPLICABLE` for every parsed asset | `MATCH` for negative assets; `UNKNOWN_CURRENT` for Box/Spot | Dependent RuleEngine gate |
| `STUBBORN_RETURN_HOOK` | Upside-Down Chair | `UNKNOWN` | no evaluation | `UNKNOWN_CURRENT` | Parser / Golden runner timeout |
| `STUBBORN_RETURN_PAYOFF` | Sticky, Crocodile, Lamp, Snack, Sneaky, Island | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `MATCH` | Rule evaluator gate |
| `STUBBORN_RETURN_PAYOFF` | Box Cat | `APPLICABLE` | `NOT_APPLICABLE` | `FALSE_NEGATIVE_APPLICABILITY` at dependent gate | Canonical profile selector / RuleEngine gate |
| `STUBBORN_RETURN_PAYOFF` | Spot Cat | `UNKNOWN` | `NOT_APPLICABLE` | `UNKNOWN_CURRENT` | Dependent RuleEngine gate |
| `STUBBORN_RETURN_PAYOFF` | Upside-Down Chair | `UNKNOWN` | no evaluation | `UNKNOWN_CURRENT` | Parser / Golden runner timeout |

### 9.1 Applicability is not currently compared as a rule-level value

The current assessment exposes `engine_profile` at the top level, but its `dimensions` list has no `ENGINE_PROFILE` entry. The Golden comparator reads `dimensions.get("ENGINE_PROFILE")`, then falls back to stored `dimensionValues`; both baseline and current therefore become `null` for `SPECIALIZED_RULE_APPLICABILITY`.

The comparator also does not emit separate assertions for `STUBBORN_RETURN_LOOP`, `STUBBORN_RETURN_HOOK`, and `STUBBORN_RETURN_PAYOFF`. Existing aggregate Gold rows can be short-circuited as `NOT_APPLICABLE` when Gold says `applicable: false`, so a passing release gate does not prove the runtime applicability path is correct.

This is an identified Family 5 observation only. It is not being fixed in this review.

## 10. First divergence and root-layer observations

The first divergence depends on which contract is being compared:

1. **Runtime profile activation:** For Box Cat and other parsed assets, the first divergence is in the parser/canonical profile selector. The frozen source contains richer causal semantics than the parsed IR/profile signals expose. The current selector therefore produces a LOW/`DEFAULT` candidate or a MEDIUM candidate-only profile rather than active HIGH evidence.
2. **Specialized dependent outcomes:** Hook and payoff rules gate entirely on `profile.active`; they return `NOT_APPLICABLE` when the base profile is inactive. This preserves the outcome taxonomy but hides unresolved dependent applicability behind the base selector.
3. **Chair:** The parser/Golden runner timeout occurs before canonical evidence or RuleEngine evaluation; no applicability status may safely be inferred from missing output.
4. **Aggregate Golden representation:** Assessment construction is the first projection divergence. `engine_profile` exists at the top level, but `ENGINE_PROFILE` is absent from `assessment.dimensions`; the comparator then projects `null` and falls back to stale/null stored values.
5. **Ruleset inventory:** One-level `extends` loading omits historical 1.5 rules from effective 1.7. This is a separate runtime inventory divergence, not a reason to invent a Family 5 label for an inactive rule.

The current scoring and API layers preserve the key taxonomy: `UNKNOWN` and `SERVICE_ERROR` are evidence gaps, `NOT_APPLICABLE` remains distinct, non-applicable outcomes are excluded from scored subsets, and the API exposes separate `unknown_rules` and `not_applicable_rules`. No evidence shows `NOT_APPLICABLE` being converted into a creative zero or blocker in the inspected path.

## 11. Family 5 invariants to lock in review

1. Specialized rule applicability is not rule pass/fail.
2. Recurrence is not return-loop applicability.
3. A same-rule payoff is not automatically a specialized profile.
4. Keyword overlap is not domain membership.
5. Object type is not domain membership.
6. Character type is not domain membership.
7. Multiple attempts are not specialized applicability.
8. `NOT_APPLICABLE` must not penalize creative score.
9. `UNKNOWN` must not silently become `FAIL`.
10. Every specialized rule must state mandatory semantic preconditions.
11. All mandatory preconditions must be established before `APPLICABLE`.
12. Missing one mandatory precondition is `NOT_APPLICABLE` only when the source positively excludes the domain; otherwise it is `UNKNOWN`.
13. Performance data must never influence applicability.
14. Winner/middle/negative corpus role must never influence applicability.
15. Family 1–4 outputs are frozen evidence inputs, not calibration targets in this phase.

## 12. Human-review-required decisions

Human approval is required for these proposed labels before any Gold Truth update:

1. Whether Box Cat’s empty/usable-box and cat-reclaim pattern satisfies the exact `STUBBORN_RETURN_LOOP` domain (`APPLICABLE`, HIGH).
2. Whether Box Cat’s final cat reclaim satisfies the narrower `STUBBORN_RETURN_PAYOFF` domain (`APPLICABLE`, MEDIUM), despite Family 4 payoff being `MODERATE`.
3. Whether Box Cat’s immediate access conflict qualifies as the specialized physical-threat Hook (`UNKNOWN`, MEDIUM).
4. Whether Upside-Down Chair should remain `UNKNOWN` rather than become applicable: it has the strongest non-animal structural near-match, but the frozen source does not establish that autonomous inversion is the intended low-memory stubborn-return domain.
5. Whether Spot Cat remains `UNKNOWN`: repeated target claims, moving locations, and weak escalation should not be silently promoted to a fixed-boundary autonomous-return profile.
6. Whether the absence of a high-confidence positive Hook fixture is acceptable for the nine-asset review. This report recommends keeping it as a documented coverage gap rather than adding a tenth prompt.
7. Whether the aggregate existing Gold labels `CANDIDATE_REVIEW` and `APPLICABLE_CANDIDATE` should later be decomposed into rule-level Family 5 labels. No decomposition has been written to `gold_truth.yaml`.

## 13. Validation and stop condition

Read-only repository checks completed:

- Effective RULESET 1.7 inventory inspected.
- Existing specialized-rule, applicability, API outcome, Golden schema, comparator, and related boundary tests: **35 passed**.
- Frozen v1.7 baseline/current snapshots and Golden report inspected.
- Nine frozen prompt paths, hashes, known issues, and Family 1–4 evidence inspected.

No Golden runner, baseline capture, policy regeneration, scorer threshold, or engine implementation was changed. No Family 5 calibration logic was implemented.

**Review stop:** this report and the proposed applicability matrix are the only Family 5 deliverables. Wait for human approval before modifying `gold_truth.yaml`, any ruleset, or any runtime behavior.
