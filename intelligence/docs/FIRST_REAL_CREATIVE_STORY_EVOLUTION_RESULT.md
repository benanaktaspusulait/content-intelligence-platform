EXPERIMENT: REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1

OWNER_AUTHORIZATION: NO
AUTHORIZED_CAP_USD: 0.017966

REAL_DEEPSEEK_STORY_CALL: NO
REAL_OPENAI_STORY_REVIEW_CALL: NO

PROVIDER_REQUESTS_ATTEMPTED: 0
PROVIDER_REQUESTS_COMPLETED: 0
ACTUAL_SPEND_USD: 0
UNRESOLVED_BILLING: NO

STORY_ALTERNATIVES_GENERATED: 0
INDEPENDENT_REVIEW_COMPLETED: NO

CANDIDATE_1_CREATIVE_ASSESSMENT: NOT_GENERATED
CANDIDATE_2_CREATIVE_ASSESSMENT: NOT_GENERATED

CREATIVE_WINNER: NONE

SOURCE_FIDELITY: ORIGINAL_SOURCE_BINDING_VERIFIED; CANDIDATES_NOT_GENERATED
OWNER_STORY_APPROVAL: PENDING

NEW_CANONICAL_PROMPT_SCORE: NOT_EVALUATED
OFFICIAL_A_PLUS: INACTIVE

PRODUCTION_DB_WRITES: 0
IMAGE_CALLS: 0
VIDEO_RENDERS: 0
PUBLICATIONS: 0

EXPERIMENT_STATUS: PREFLIGHT_BLOCKED_NO_DISPATCH

# First real creative story experiment — preflight result

The exact existing P2 source is available and the configured price envelope matches the prepared experiment. The current execution path does not satisfy all mandatory acceptance conditions. No provider was constructed for inference, no paid authorization was requested, and no run was created. The task explicitly requires all checks to pass before requesting this experiment's separate owner authorization.

`AUTHORIZED_CAP_USD` above records the requested maximum scope, **not a received spending authorization**. The attachment and “devam” are engineering instructions; the attachment expressly says they are not paid-inference consent.

## Verified source and environment

The existing `backend/target/disposable-owner-http/run-oT9HS7/disposable-real-provider.dump` was restored into a newly created disposable PostgreSQL container using `--network none`, without publishing a port. The original snapshot was reused; no source IDs were regenerated. The restored source, approval and analysis were queried read-only and compared against the prepared manifest. The disposable container was removed afterward.

- Story ID: `ca40c11a-7831-476e-9f50-646a61a1ec9c`.
- Revision: `candidate-1-revision-04c8c36b`.
- Approval ID: `af738239-99c3-4a9e-90b5-a1bee4295cd0`.
- Analysis ID: `10fc4c38-7cdf-4f71-b8dc-05b14315352a`.
- Story SHA-256: `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d`.
- Prompt SHA-256: `1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5`.
- Existing canonical result: Ruleset 1.11, **93.42708333333334 / numerical A**, with creative risk still unresolved.
- Prepared pilot idempotency-key records in that restored snapshot: **0**. No new dispatch occurred in this task.
- Snapshot file SHA-256: `14dcbfd5758826183846010702288b9308dcd184f42f7188c8def9ea5fbc0ac1`.

The first restore invocation stopped on an existing-schema conflict; the disposable container was removed. Restoring with the existing documented `--clean --if-exists` options succeeded in a separate disposable container. No production database was contacted or changed.

See [source verification](FIRST_REAL_CREATIVE_STORY_PREFLIGHT_SOURCE.json).

## Exact prepared request and pricing

The provider-free effective STORY request exactly matches `CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json`.

- Effective STORY system SHA-256: `fa653c92ae3d37dbe8f886ca7552ebe54ec36c9267b305989fa27ee15f1046ce`.
- Serialized STORY user-payload SHA-256: `4cc587f35c15ae20465c24c4f74d28b2608468aea7caa7af3428694520e9e8cd`.
- Prepared manifest file SHA-256: `3eecf0c1a790edbb6ef96b3261a84ab241ea649fdac3aaac9dacdbcb8c151d5c`.

| Role | Configured model | Input/output USD per million | Output maximum | Request reservation |
|---|---|---|---|---|
| STORY | DeepSeek `deepseek-chat` | 0.30 / 1.20 | 4,000 tokens | $0.008983 |
| STORY_REVIEW | OpenAI `gpt-4o-mini-2024-07-18` | 0.15 / 0.60 | 4,000 tokens | $0.008983 |

Maximum total reservation remains **$0.017966**, one round and at most two calls. The STORY upper-bound calculation is $0.00898230. The future review's enforced 24,000-byte input envelope yields $0.00670215. Exact review content and its fingerprint cannot exist until genuine candidates have been generated; the envelope is priced without inventing them. Current model availability was not probed with inference. Production's real-dispatch flag remains false.

See [profile verification](FIRST_REAL_CREATIVE_STORY_PREFLIGHT_PROFILES.json).

## Blocking contract findings

These are non-billable negative contract probes and code-path findings, **not mock experimental stories or evidence of creative success**.

### 1. Exactly two complete usable alternatives is not enforced

`perform_role`'s STORY branch accepts one to three alternatives even when `requestedAlternativeCount=2`. The negative probe returned one candidate; the current boundary accepted it. `StoryEvolutionService.step` then permits any nonempty `valid` list and can proceed to paid STORY_REVIEW with one candidate.

This violates the experiment's two-alternative scope. The existing path needs a strict experiment-bound count/identity/completeness check before the second request. No count check was relaxed or code edited here.

### 2. Obvious protected-source violations do not block the second request

A negative probe supplied two unrelated stories: a dragon named Rex flying to the moon and a human chef named Ada cooking soup. Both omit Pip, sticky notes, the physical rule, cabinet and established ending. The STORY boundary accepted them, returning advisory `storyQuality` rather than a blocking source verdict.

The backend's immediate pre-review filter checks blank/equal text, not the protected character/mechanic/ending contract. Thus the existing flow can spend the review request on an unusable source-invalid generation. This is distinct from allowing explicitly labelled owner-reviewable protected-change proposals. The required protected-change status is not presently enforced at this boundary.

### 3. Full genuine first response is not durably saved before review

`StoryEvolutionService.dispatch` persists a reservation and a completion summary. It returns the complete generation response to a local variable, but does not persist that full response/usage envelope before dispatching STORY_REVIEW. A transport or validation failure in review reaches `processNext`'s catch, which reloads persisted progress and stops with exception text. The original alternatives and raw first response can be lost from durable run evidence.

Received malformed STORY/STORY_REVIEW responses also take the generic role error path rather than a complete recoverable response-and-usage envelope. The model response can have incurred a real charge before this local rejection. The acceptance requires authentic responses and actual usage to survive those failures; a reservation summary is insufficient.

### 4. Scope fingerprints are prepared but not independently enforced by this run's dispatch

The existing Story Evolution authorization stores source IDs, objective and monetary/request limits. It does not bind and revalidate these exact role/model/system/payload fingerprints immediately before each request. Paid role configuration is read from the current environment. A prepared hash alone does not enforce the instruction/configuration-change stop requirement.

This can be addressed narrowly in the existing execution path; a separate generator, scoring system, dashboard or governance architecture is unnecessary. No implementation expansion was performed during this execution task.

See [negative probes and request fingerprints](FIRST_REAL_CREATIVE_STORY_PREFLIGHT_CONTRACTS.json). Relevant code is `ml-service/app/workflow/creative_roles.py` (STORY validation and generic failure handling), `ml-service/app/workflow/api.py` (creative-role errors), and `backend/src/main/java/com/pompomhills/intelligence/workflow/StoryEvolutionService.java` (`step`, `dispatch`, `processNext`).

The previous readiness result established focused-test and offline integration readiness. It did not demonstrate these stricter failure-path guarantees. This preflight narrows that earlier readiness claim; the paid experiment is blocked until the concrete conditions above are enforced.

## Full ORIGINAL story

Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched. Pip tries to peel the note away with the free hand, but it splits into two notes, one on each hand. Pip tries to press both notes onto the cabinet, but they spring back and double into four notes. Pip tries to push the four notes off against the cabinet door edge, but they split into eight and cover Pip's arms and face. Pip sees the four-to-eight change finish, realizes that every removal or transfer attempt multiplies the notes, deliberately stops struggling, and turns the still note-covered face toward the mirror. Pip remains covered until a sneeze scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy.

## Full REAL DeepSeek candidate 1

NOT_GENERATED — no inference dispatched. No prepared or mock answer substitutes for a real response.

## Full REAL DeepSeek candidate 2

NOT_GENERATED — no inference dispatched.

## Full REAL OpenAI independent review

NOT_EXECUTED — no candidates exist from this experiment and no review request was sent.

## Six-dimension comparison

| CPQ dimension | Baseline concern | Candidate 1 | Candidate 2 |
|---|---|---|---|
| SCROLL_STOP_VISUAL_PROMISE | First visible state/scroll-stop strength unverified | NOT_GENERATED | NOT_GENERATED |
| CAUSAL_PROGRESSION | Different manipulations often produce similar multiplication consequences | NOT_GENERATED | NOT_GENERATED |
| VISUAL_STORYTELLING | Textual causal structure exists; actual visual clarity unobserved | NOT_GENERATED | NOT_GENERATED |
| PRODUCTION_EXECUTABILITY | Thin note/contact/count/face continuity risks | NOT_GENERATED | NOT_GENERATED |
| ENDING_REPLAY | Overloaded final window; payoff and replay unverified | NOT_GENERATED | NOT_GENERATED |
| DISTINCTIVE_CREATIVE_VALUE | Structural compliance does not establish viewer-visible originality | NOT_GENERATED | NOT_GENERATED |

There are no genuine candidate changes, comparative pacing findings or justified winner to report. Baseline first-frame and final-window concerns remain unchanged. No canonical story score is fabricated. Official creative A+ remains inactive.

## Usage, durable accounting and approval choices

Real request attempts/completions: **0/0**. Actual new spend: **$0**. Unresolved billing: **NO**. No new authorized run, reservation, response or candidate was inserted into a production database. The isolated source restore was the only database preparation; it created no experimental provider evidence.

Owner story approval remains **PENDING**. There is no genuine candidate to approve. Following narrowly scoped corrections and a passing non-billable preflight, the owner may separately authorize exactly the DeepSeek STORY and OpenAI STORY_REVIEW calls with the current source/instruction/profile fingerprints and $0.017966 ceiling. If that exact envelope changes, fresh exact authorization is required. Story approval and any later BUILD_PROMPT remain separate decisions.

## Git and production integrity

At task start the worktree was clean on `master`; HEAD was `bbe086fc6e7be6ae27674cb2a3665ea0339bd524`, authored by Auto. That differs from the previous task's final HEAD and confirms an external history change between tasks. HEAD stayed at this hash during the preflight. No commit, amend, reset, push, Git configuration change or process interruption was performed here. This task added only this report and three non-secret preflight JSON artifacts.

No source-code changes, production deployment, production database writes, story approval, prompt creation, scoring change, image generation, render or publication occurred. Execution stopped before paid inference because mandatory checks did not pass.
