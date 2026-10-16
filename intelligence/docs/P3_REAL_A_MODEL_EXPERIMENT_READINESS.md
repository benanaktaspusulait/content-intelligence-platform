P2_NUMERICAL_A_SCORE: 93.42708333333334
P2_NUMERICAL_A_GRADE: A

FULL_CANONICAL_A_ADMITTED: NO
REAL_PROVIDER_A_VERIFIED: NO

STAGE_DEPENDENCY_AUDITED: YES
CIRCULAR_GATE_FOUND: YES
CIRCULAR_GATE_RESOLVED: YES

STORY_STRUCTURAL_FEASIBILITY: STRUCTURALLY_PROMISING_WITH_3_SOURCE_BOUND_ATTEMPTS
TEXT_RESEARCH_GENERATION_ELIGIBILITY: ELIGIBLE_FOR_EXPLICIT_OWNER_AUTHORIZATION
FINAL_CANONICAL_A_ADMISSION: BLOCKED_BY_REQUIRED_SEMANTIC_AND_VISUAL_EVIDENCE
FIRST_FRAME_READINESS: MISSING
STEP_7_READINESS: BLOCKED_UNTIL_VERIFIED_CHARACTER_REFERENCE_ACCEPTED_FIRST_FRAME_AND_VISUAL_QA

DEEPSEEK_CONTEXT_VERIFIED: YES
OPENAI_CONTEXT_VERIFIED: YES
CROSS_MODEL_REVIEW_VALID: YES

SAME_SOURCE_COMPARISON_READY: YES
REAL_PROVIDER_AUTHORIZATION: NOT_GRANTED

REAL_PROVIDER_CALLS: 0
REAL_IMAGE_CALLS: 0
REAL_VIDEO_CALLS: 0

PRODUCTION_DATABASE_WRITES: 0
OFFICIAL_A_PLUS: INACTIVE

# Finding

The existing `generationAllowed` decision correctly means that the full target-aware generation/admission contract is open. It was also the only gate used by the bounded optimization worker. The P2 prompt has a numerical A and a fixed-evidence ceiling above 92, but its missing first-frame evidence makes `generationAllowed=false`. That created a circular stage dependency: an authorized text-only model capability experiment could not run until visual evidence existed, even though the visual evidence can only be prepared against a selected prompt.

The fix does not change `generationAllowed`. A separate, versioned `canonical-a-text-research-eligibility-v1` decision now permits only a source-bound, text-only capability experiment when:

- the current Ruleset 1.11 evaluation and aggregate are valid;
- the fixed-evidence ceiling is at least 92;
- no protected ATTEMPT_001 story conflict exists;
- the authenticated owner supplies the exact research grant;
- the generator is independently reviewed by the other model for both source fidelity and creative quality.

The research decision always returns `finalCanonicalAAdmitted=false`, `promptApprovalAllowed=false`, `imageGenerationAllowed=false`, `renderPreparationAllowed=false`, and `renderAuthorized=false`. The original final admission and render gates remain unchanged.

# Dependency graph and enforcement

```text
approved source revision + owner approval
  -> Story Evolution (optional; source story only)
  -> BUILD_PROMPT (exact approved revision)
  -> immutable prompt version + Ruleset 1.11 REVIEW
  -> story structural feasibility
       | protected story conflict / ceiling < 92 -> research denied
       | structurally promising + downstream evidence pending
       v
     TEXT-ONLY RESEARCH ELIGIBILITY
       -> one generator call
       -> other model SOURCE_FIDELITY
       -> other model CRITIC
       -> diagnostic draft only; no prompt approval
  -> independent semantic canonical evidence
  -> verified character reference
  -> first-frame preparation/upload/technical validation
  -> first-frame and silhouette semantic verification
  -> fresh Ruleset 1.11 evaluation and final Canonical A admission
  -> Step 7 render preparation
  -> separate owner render authorization
  -> render queue admission
```

The concrete gates are:

- Story generation and independent story review: `StoryEvolutionService.step`, lines 54-92.
- Exact approved revision to BUILD_PROMPT and normal prompt/REVIEW persistence: `StoryEvolutionService.handoff`, lines 98-185.
- Read-only Ruleset 1.11 feasibility: `WorkflowService.adaptiveOptimizationPreflight`, lines 185-211.
- Separate research policy: `adaptive_optimization.py`, `research_eligibility` and `feasibility`, lines 21-141.
- Same-source preflight and bounded comparison plan: `OptimizationLoopService.preflight/researchComparisonPlan`, lines 62-94.
- Exact grant, configured-provider, cross-model independence and one-round/three-request limit: `OptimizationLoopService.validateGrant`, lines 97-121.
- Worker-side fresh scope, eligibility, budget and request revalidation: `OptimizationLoopService.step`, lines 179-224.
- Research prompt-approval denial: `OptimizationLoopService.accept`, lines 141-145.
- Canonical render admission: `WorkflowService.admission`, lines 885-950.
- First-frame bytes, dimensions, storage hash and prompt binding: `VisualReferencePlanningService`, lines 266-301 and 490-520.
- Append-only semantic visual evidence and exact validation binding: `VisualEvidenceSubmissionService`, lines 46-163.

# P2 blocker classification

No UNKNOWN was converted to PASS. `ATTEMPT_001` remains PASS with three genuine source-bound attempts.

| Rule | Current result | Missing evidence / defect | Earliest legitimate resolution | Text-only repair? | Independent semantic assessment? | Image evidence? | True source constraint? | Blocks research? | Blocks final A? | Blocks render? |
|---|---|---|---|---|---|---|---|---|---|---|
| PRODUCIBILITY_003 | FAIL / CRITICAL | Thin sticky-note contact risk; no independent risk-reduction evidence | Prompt production planning, then production-risk review | Possibly, only through source-faithful staging | Useful | Render evidence may confirm risk, but is not required to detect it | No; the object mechanic is protected | No | Risk remains; it is not an evidence-incomplete hard blocker by itself | Requires explicit risk handling; rule text says it is not an outright render block |
| INSTANT_VISUAL_ABSURDITY_GATE | FAIL / BLOCKER, evidence incomplete | Static wrongness, history independence, micro-comparison independence, large signal, character already engaged | First-frame semantic visual QA | Text may specify intent but cannot prove PASS | Yes, as visual verification | Yes, exact first-frame bytes | No | No | Yes | Yes |
| ENGINE_SILHOUETTE_DUPLICATE | FAIL / BLOCKER, evidence incomplete | Verified visual-engine/silhouette comparison | First-frame semantic visual QA | No | Yes, as visual comparison | Yes, the same prompt-bound first-frame asset | No | No | Yes | Yes |
| CONSISTENCY_001 | UNKNOWN / WARNING | Explicit mechanic-consistency evidence | Independent semantic canonical review | A text clarification may help | Yes for authoritative result | No | No | No | Evidence remains unresolved | Not alone |
| HOOK_003 | UNKNOWN / CRITICAL | Sound-off clarity evidence | Independent semantic review; visual confirmation later | A text clarification may help | Yes | Helpful, not sufficient alone | No | No | Yes while required evidence is absent | Yes under current canonical admission |
| ATTEMPT_002 | UNKNOWN / CRITICAL | Verified semantic judgment that peel, press and push are mechanically distinct | Independent semantic canonical review | Text can clarify choreography; cannot self-certify | Yes | Helpful later | No | No | Yes | Yes under current canonical admission |
| PAYOFF_003 | UNKNOWN / CRITICAL | Verified semantic judgment that sneeze payoff derives from the same rule | Independent semantic canonical review | Text can clarify causality; cannot self-certify | Yes | Helpful later | No | No | Yes | Yes under current canonical admission |
| CONCEPT_007 | UNKNOWN / BLOCKER | Verified single-mechanic judgment | Independent semantic canonical review | Text can clarify; cannot self-certify | Yes | No | No | No | Yes | Yes |
| GOAL_001 | UNKNOWN / BLOCKER | Verified natural-goal/obstruction judgment | Independent semantic canonical review | Text can clarify; cannot self-certify | Yes | No | No | No | Yes | Yes |
| CONCEPT_008 | UNKNOWN / CRITICAL | Verified predictable-rule judgment | Independent semantic canonical review | Text can clarify; cannot self-certify | Yes | Helpful later | No | No | Yes | Yes under current canonical admission |
| HOOK_004 | UNKNOWN / CRITICAL | Verified opening goal/problem legibility | Independent semantic review, then first-frame QA | Text can clarify; cannot prove visual result | Yes | Yes for actual opening legibility | No | No | Yes | Yes |
| PERFORMANCE_001 | UNKNOWN / WARNING | Verified readable character-performance judgment | Independent semantic review; render evidence later | Text can improve direction | Yes | Helpful later | No | No | Evidence remains unresolved | Not alone |
| GENERATION_EXECUTABLE_ATTEMPTS | UNKNOWN / BLOCKER | Verified judgment that each attempt is visually distinct and Seedance-executable | Independent semantic/execution review; render evidence later | Text can clarify staging; cannot self-certify | Yes | Helpful later | No | No | Yes | Yes |

# Outbound context equivalence

Both generator previews were compiled by the same production request builder. They have identical values for:

- approved story SHA-256: `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d`;
- prompt SHA-256: `1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5`;
- settings SHA-256: `e6aedfab391d7ee0a7e753b3dc8f4e8d57c31d8b2ada4b9f8b130b95b2689937`;
- source scope SHA-256: `d8ab3e71743196a1dd642e100a07bb0f6f7818af1b2158aabe269762d8216bda`;
- generation system SHA-256: `41e590871450708bd59f94041efeb6fe8e1253847a8c4e3560db90ce10c0696b`;
- generation user payload SHA-256: `8d55f5c4d306bf3ba3e7e836c8d13c9612c17d32623dd8eec3babb8cc07fac6b`;
- generation response schema SHA-256: `09678f0396e1c8e8034eb22bd71d9b8bfaf7a87b76f30c44195783b0b7f06a04`;
- generation instruction/context SHA-256: `91561d8983a38b0d247451e8f1d22fc3051145a6b3ca1308a4b196f326959a3f`.

The SOURCE_FIDELITY and CRITIC roles use separate schemas and prompts. Their cross-run instruction/context fingerprints are identical between models: source fidelity `6f3b285a3dd0c79f6a56f0752409e72004716aaae81a49844f6dd5cdb543d724`, critic `9d807dfb276b9ee196d5703ac3979b8965208454479534166ff39333a0037042`. The actual reviewer user payload is recomputed from the generated candidate and durably fingerprinted before dispatch.

# Prepared comparison and fresh budget

The last disposable preflight used story ID `5cd3785b-10cd-4b84-b3f4-ed73e8baa45a`, approval record `b46b4676-bcc4-49b8-93c9-96df0de8dac0`, revision `candidate-1-revision-04c8c36b`, prompt version `2`, and analysis `639c59fa-9149-4ef1-b330-c2abad94cae4`. These UUIDs belong to the disposable acceptance database; the immutable story/prompt/settings SHA values above are the portable source identity. Any future live/disposable execution must recompute and bind its current UUIDs and exact scope SHA before reservation.

| Run / role | Profile and model | Reasoning | Max output | Conservative input-unit bound | USD cap |
|---|---|---:|---:|---:|---:|
| A generation | `deepseek-primary` / `deepseek-v4-pro` | none | 4,000 | 55,034 | 0.088485 |
| A source fidelity | `openai-escalation` / `gpt-6.1-sol` | low | 4,000 | 37,272 | 0.133180 |
| A critic | `openai-escalation` / `gpt-6.1-sol` | low | 4,000 | 40,522 | 0.141305 |
| B generation | `openai-escalation` / `gpt-6.1-sol` | low | 4,000 | 55,034 | 0.177585 |
| B source fidelity | `deepseek-primary` / `deepseek-v4-pro` | none | 4,000 | 37,272 | 0.065040 |
| B critic | `deepseek-primary` / `deepseek-v4-pro` | none | 4,000 | 40,522 | 0.069330 |

Run A maximum is USD `0.362970`; Run B maximum is USD `0.311955`; combined maximum is USD `0.674925`. Maximum requests: `6`. Maximum aggregate output: `24,000` tokens. Per-request timeout: `120` seconds. Per-run deadline: `600` seconds. Automatic retries: disabled. Fallback: disabled. A failed or ambiguous request, incomplete accounting, changed scope, changed model, budget excess, timeout, source violation, contract failure, or missing independent review stops the affected run.

The input figure is the existing conservative preflight billing bound: exact generation request bytes plus safety margin, and a 30,000-character maximum candidate for reviewer reservations. It is charged as if every bound unit were an uncached input token, so it is an upper bound rather than an actual tokenizer count. Provider context limits remain 1,000,000 tokens for DeepSeek and 1,050,000 for OpenAI.

Both provider credentials are configured in the local ML container without exposing their values. `CPQ_PILOT_REAL_ENABLED=false`; network availability is `UNVERIFIED_NO_PROVIDER_CALL`. The worker will reject an unconfigured profile before creating a run. No availability claim is made until an authorized call returns.

# First-frame evidence path

Already provider-free from real local bytes:

- MIME family, decodability, 20 MB size limit, dimensions and aspect ratio;
- SHA-256 and safe content-scoped persistence;
- immutable prompt/version binding and stale-plan rejection;
- character-reference asset identity in the acceptance contract;
- candidate rejection/acceptance and owner-selected first-frame binding;
- re-reading bytes and hash before render queue admission.

Still semantic and not proven by metadata:

- instant visual absurdity and history-free legibility;
- approved-story alignment and character identity;
- physical mechanic visibility;
- silhouette/visual-engine originality;
- generation executability and render quality.

The silhouette evidence gate does not require a finished video. Its append-only contract requires the same prompt-bound FIRST_FRAME asset identity as the first-frame gate. This permits semantic comparison before video render and avoids a render-authorization cycle. The current P2 run has no Mimi/Pip production image; synthetic fixture images were not treated as evidence.

# Isolated verification

- Python adaptive-policy and optimization request tests: `42 passed`.
- Backend bounded-ledger/Testcontainers suite: passed, including protected-story denial, research-only three-call execution, missing-grant rejection, idempotency, budgets, ambiguous accounting, and prompt-approval denial.
- Disposable HTTP `--story-feasibility` harness: exit `0`, evidence directory `intelligence/backend/target/disposable-owner-http/run-TuwfxR`; no external egress and no provider/image/video calls.
- Visual reference planning and engine regression tests: passed.
- Visual evidence submission and validation projection tests: passed.
- Current source score reproduced as `93.42708333333334 / A`; full admission remained blocked and `generationAllowed` remained `false`.

Scenarios A-E passed: an ATTEMPT_001-protected story remains denied; the P2 source is research-eligible while final admission remains blocked; Step 7 remains blocked; incomplete owner grants fail before dispatch; request limits, budget reservations and idempotency remain enforced.

# Exact owner authorization request

Approve **YES or NO** for `REAL_MODEL_A_CAPABILITY_RESEARCH_V1` on the immutable story, prompt, settings, source-scope and instruction fingerprints listed above, with exactly two runs and at most six requests:

- Run A: DeepSeek generation; OpenAI source-fidelity and critic review; USD 0.362970 maximum.
- Run B: OpenAI generation; DeepSeek source-fidelity and critic review; USD 0.311955 maximum.
- Combined maximum: USD 0.674925.
- 4,000 output tokens per request; 120-second request timeout; 600-second run deadline.
- No retries, fallback, prompt approval, prompt-version creation, image generation, rendering, publishing, canonical rule changes or A+ activation.
- Stop on any ambiguous dispatch/accounting result. Do not issue a replacement call.

Authorization must be re-bound by the backend to a fresh current preflight whose immutable SHA values exactly match this report. A changed SHA, model/profile, instruction context, cost cap or source identity invalidates the grant before dispatch.
