REAL_DEEPSEEK_GENERATIONS: 0
REAL_OPENAI_GENERATIONS: 0

CURRENT_GENERATION_PAYLOAD_AUDITED: YES
RULESET_CONTEXT_INCLUDED: COMPLETE
FAILED_RULE_FEEDBACK_INCLUDED: YES
PREVIOUS_ROUND_CONTEXT_INCLUDED: YES
SOURCE_CONSTRAINTS_INCLUDED: YES

INSTRUCTION_GAPS_FOUND: YES
PARSER_RECOGNITION_ISSUES_FOUND: YES

ELIGIBLE_COMPARISON_SUBJECT: NOT_FOUND

OPENAI_PROFILE_VALID: YES
DEEPSEEK_PROFILE_VALID: YES
REVIEW_ROLE_INDEPENDENCE: VALID

REAL_MODEL_COMPARISON: NOT_EXECUTED
OWNER_PAID_AUTHORIZATION: NOT_RECEIVED

CANONICAL_A_REACHED_BY_REAL_MODEL: NOT_VERIFIED
OFFICIAL_A_PLUS: INACTIVE

# DeepSeek/OpenAI rule-context audit

Date: 2026-10-16. This was a no-egress instruction audit. No provider SDK was constructed, no paid request was dispatched and no production record was written. “Profile valid” means the checked-in capability/profile contract passes local validation; live availability remains `UNVERIFIED_NO_PROVIDER_CALL`. Neither API key is present in this shell environment. No secret, credential, cookie or HMAC value is recorded here.

## Baseline and conclusion

The Pip baseline is `82.54166666666669/B`; the fixture-generated prompt is `79.78645833333334/C`; the Canonical A threshold is 92. The P1 run used seven isolated fixture role responses and zero real DeepSeek/OpenAI calls. It proves orchestration and validation readiness, not either model's creative performance.

The actual optimization request was not devoid of feedback. Before this correction, `escalationEvidence.remainingWeaknesses.remainingFindings` carried up to 20 rows with `ruleId`, outcome, severity and message, and carried prior-round rejection/source-fidelity state. That delivery was **partial**: it had no authoritative Ruleset identity/hash, baseline score/grade/target, evaluator recommendation, prompt-versus-evidence distinction, protected-story conflict classification, mandatory-blocker list, or explicit permitted/prohibited changes. The full `baselineCanonicalEvaluation` and `baselineCanonicalFailures` existed in server context but were not serialized to the provider payload.

The correction adds one versioned `canonicalImprovementContext` compiled directly from the actual Ruleset 1.11 result. It does not evaluate, rescore or reinterpret a prompt. For the exact P1 Pip prompt it carries all **19 FAIL/UNKNOWN rows**, baseline `79.78645833333334/C`, target `92/A`, mandatory blockers, each evaluator message/recommendation, and a rule-specific classification:

- `SOURCE_BOUND_TEXT_REPAIRABLE`: source-bound staging, choreography, continuity, composition or relative-presentation changes may be proposed and must be re-evaluated.
- `EVIDENCE_REQUIRED_NOT_PROMPT_PROOF`: UNKNOWN or evidence-incomplete findings remain UNKNOWN; prompt prose cannot establish visual/audience evidence.
- `PROTECTED_STORY_CHANGE_REQUIRED`: `ATTEMPT_001` cannot be repaired by inventing or relabelling attempts; it requires owner-approved Story Evolution if the source lacks genuine strategies.

The context also explicitly forbids invented evidence, UNKNOWN→PASS conversion, protected-event additions, scoring changes, and render/audience-success claims. Its exact P1 context SHA-256 is `c784c351a8335ebb3eca240d19002026573dcf58948d04130f3ab3cbd0fb8c8b`.

## Effective outbound instructions

These are the effective messages at the final `provider.complete(system=..., prompt=...)` boundary. Provider adapters then place them in Chat Completions `system` and `user` messages. DeepSeek JSON mode also appends the same response schema to the system message; OpenAI receives it as strict `json_schema`. Both generator profiles receive byte-equivalent task content and schema.

| Role | Actual system instruction and outbound data | Rules/evidence delivery | Audit finding |
|---|---|---|---|
| STORY | Generate the requested number of materially different complete stories; honor input mode, exploration/improvement mode and only the explicit locks; preserve characters and intent; JSON only. The user JSON is source text plus safe context. Final P1 system SHA `885821cf...386a`, user SHA `c47fffeb...9c8`. | Round 1/2 carry exact source/approved story, source fingerprint, prior best, prior assessment, accepted changes and rejected candidates. They do not carry Ruleset 1.11 findings, target score, generator settings or target feasibility. | Suitable for general story evolution, insufficient by itself for target-aware A feasibility. Story changes still require owner approval and a fresh evaluator/preflight. |
| STORY_REVIEW | Compare all supplied story candidates for coherence, opening promise, causal consistency, progression, sibling originality, curiosity, generator difficulty, source constraints and ending/payoff; cite text, preserve uncertainty, never authorize render. P1 system SHA `50b2607f...aef4`, user SHA `32fc662e...920`. | Exact candidates, approved story, source/request fingerprints, round number, prior best and previous assessment are present. No Ruleset row contract or target ceiling is present. | Independent story review is qualitative and source-aware, not Canonical A feasibility review. |
| BUILD_PROMPT | Convert the approved story into a complete OpenArt production prompt and structured production plan; preserve character, mechanism, essential progression, protected events and ending; cover full duration; use exact source quotes; separate facts from execution hypotheses; identify risks and limitations; never authorize render. P1 system SHA `6526429b...0a96`, user SHA `2f90722e...0c94`. | Approved story is the entire input text. Source/story identity, character record/references, target generator, duration/aspect ratio/profile and generator capabilities are present. It receives no previous canonical score because it creates the first prompt from that approved story. | Strong source and production contract. It cannot optimize toward unseen post-build rule findings; the resulting prompt must be evaluated before optimization. |
| Autonomous GENERATION | Diagnose and author a bounded production execution intervention, preserve the protected story, reject camera/timestamp-only changes, use exact reference IDs, treat benefits as hypotheses, and return the strict reconstruction plan. A new exact sentence requires reading `canonicalImprovementContext` as authoritative and forbids using prose to “resolve” evidence-only or protected-story findings. System SHA changed from `2693467e...c022` to `41e59087...696b`. Exact P1 user payload SHA changed from `1c08143a...6338` to `5f51e755...aa18`. | Complete versioned context described above, plus protected story contract, source reference catalog, current prompt diagnosis, prior-round assessment/rejections, profile/generator/settings and strict response schema. | The important instruction gap is corrected. This is instruction readiness, not evidence that a model can produce A quality. |
| SOURCE_FIDELITY | Review exactly one complete candidate against exact approved-story spans; echo exact source binding; map every required event, six anchors and every changed beat; missing support remains UNKNOWN; owner decisions never replace the raw verdict. Exact P1-shaped system SHA `8e981472...1fdf`, user SHA `046ace79...4da1`. | Exact story, story/prompt/settings hashes, complete required source events, changed beats, candidate prompt and production settings. It intentionally receives no canonical score. | Correct separation: fidelity review is not score coaching. |
| Independent CRITIC | Blindly compare original/candidate on six creative dimensions; require literal excerpts or explicit absent-evidence explanations; do not award calibrated grades, source PASS, generator success, retention or render observations. System SHA `97eed81d...4fe`, P1-shaped user SHA `8167c28d...b2f`. | Both full texts and shared settings; no intended winner and no canonical score. It intentionally receives no Ruleset context. | Correct independence: creative critique is not allowed to echo the generator's canonical objective. |

The full instruction sources are `creative_roles.py`, `creative_reconstruction.py`, `optimization_loop.py`, `owner_machine_pilot.py`, and `draft_comparative_review.py`. The P1 logical requests/responses are retained in `p1-autonomous-generated-prompt-evidence/provider-trace.jsonl`; the HMAC-verified HTTP envelope trace is `ml-role-http.jsonl`. These traces contain no provider secrets.

## Exact rule/evidence now received by generation

For every actual FAIL or UNKNOWN row the provider receives: rule ID, outcome, severity, evaluator reason, evaluator recommendation (or reason when absent), classification, permitted change, and whether prompt rewriting can establish PASS. It also receives:

- Ruleset `1.11`, current score/grade, A threshold 92 and the mandatory-blocker condition.
- Approved events/order, identity, physical rule, ending and authoritative settings as protected requirements.
- The previous round's rejection, source-fidelity status, rejected failure modes and remaining findings.
- The existing creative diagnosis and beat-local source reference catalog.
- A SHA-256 over the canonical serialized improvement context.

The compiler reads only the existing evaluator output. It does not include weights, alter applicability, fabricate evidence, or calculate a replacement score.

## Missing or contradictory instructions

Before the correction, the provider could see raw remaining findings but could not reliably tell which were prompt-repairable, evidence-only or story-blocked. “Pursue a source-supported canonical A production plan” therefore conflicted with `ATTEMPT_001` and visual-evidence blockers: A was requested while the protected story and missing evidence made A unattainable. The new contract communicates that conflict and instructs the model to return no justified prompt-only improvement rather than manufacture an attempt or PASS.

STORY and STORY_REVIEW remain target-agnostic. That is acceptable for general ideation, but they cannot alone establish that a newly evolved story has a path to A. The authoritative target-aware preflight must be rerun after owner approval. BUILD_PROMPT similarly remains a source-to-production compiler, followed by actual evaluation. SOURCE_FIDELITY and CRITIC intentionally remain unanchored to the canonical score so their judgments are independent.

## Attempt parser analysis

The baseline beat says: `Pip continues to pull; each pull doubles ...`. `actor-source-bound-v2` binds `Pip` + `continues to` + `pull` and returns one source-bound PULL attempt. The generated beat says: `Each pull doubles ...`. It expresses an object/consequence pattern, but has no explicit actor subject. The parser therefore returns no character action and no attempt for that beat. The preceding PEEL beat remains the generated prompt's only recognized attempt.

This explains the score shift affecting `ATTEMPT_001`, `ATTEMPT_002`, `CHAR_002`, `REPETITION_004`, `ESCALATION_005` and `CONTINUOUS_ACTION_MOMENTUM`. It is not evidence of a distinct strategy: both texts still describe the same peel/pull chain, and even the baseline has only two active attempts against a minimum of three. The conservative actor requirement prevents an object-event sentence from being misattributed to a character. No parser or scoring policy was changed. A focused regression proves actor-bound wording is recognized and the actorless consequence is not.

## Target feasibility and eligible subject

The authoritative P1 preflight returned `TARGET_BLOCKED_BY_STORY_CONSTRAINT`, `generationAllowed=false`, current `79.78645833333334/C`, conditional ceiling `89.234375`, and `ATTEMPT_001` protected-story conflict. The earlier Pip baseline was also below a defensible A path. The established Mimi source is independently documented as blocked below 92 by its protected story. Therefore no approved, same-source comparison subject is currently eligible.

The next legitimate step is Story Evolution proposing genuine additional strategies/realization while preserving the concept, followed by explicit owner approval, BUILD_PROMPT, actual Ruleset 1.11 evaluation and a fresh target-aware preflight. This audit does not approve any story change.

## Provider profiles and fair comparison design

Checked-in profile catalog SHA-256: `3835f28c3b960d5e4bfe2b6cf0b7184013672a0c7da24c377244304d522fb1ed`.

| Profile | Generation configuration | Validation status |
|---|---|---|
| `deepseek-primary` | DeepSeek `deepseek-v4-pro`, documented `DeepSeek-V4-Pro-0813`, Chat Completions, JSON object plus transmitted strict schema, reasoning `none` for this comparison, 6,000 max output tokens, no retry/fallback | Local catalog and request preflight valid; live availability unverified |
| `openai-escalation` | OpenAI `gpt-6.1-sol`, Chat Completions, strict JSON schema, reasoning `low`, 8,000 max completion/reasoning tokens, no retry/fallback | Local catalog and request preflight valid; live availability unverified |

For a future eligible source, use two separate one-round runs with identical approved story, exact prompt/settings, Ruleset context SHA, target, compiler and stop conditions:

1. DeepSeek generates; OpenAI performs SOURCE_FIDELITY and CRITIC.
2. OpenAI generates; DeepSeek performs SOURCE_FIDELITY and CRITIC.

The backend enforces that SOURCE_FIDELITY and CRITIC use a profile different from the generator. Thus no generator reviews its own output. The comparison records canonical score/grade, blockers, fidelity, materiality, equivalence, parser-integrity warnings, execution risks, tokens, cost and latency. Numeric score alone cannot select a winner.

Using the exact current Pip-sized payload only to calculate a conservative pre-authorization bound, the six request maxima are:

| Run/role | Maximum output tokens | Calculated worst-case USD |
|---|---:|---:|
| DeepSeek generation | 6,000 | 0.104180 |
| OpenAI source fidelity | 8,000 | 0.103005 |
| OpenAI critic | 8,000 | 0.111458 |
| OpenAI generation | 8,000 | 0.232310 |
| DeepSeek source fidelity | 6,000 | 0.035907 |
| DeepSeek critic | 6,000 | 0.040370 |
| **Total** | **42,000** | **0.627228** |

These are preflight upper bounds, not predicted spend. A future grant should cap the roles at `$0.11/$0.11/$0.12/$0.24/$0.04/$0.05`, total `$0.67`, six requests, one generation round per model, 120 seconds per request and 15 minutes total. It must be recomputed against the exact eligible source; if any estimate exceeds its cap, dispatch stops. No retry, fallback, model substitution, second generation round, prompt approval or render is allowed.

## Authorization decision

**NO — do not authorize paid inference yet.** `ELIGIBLE_COMPARISON_SUBJECT` is `NOT_FOUND`, so an exact story/version/source SHA cannot honestly be bound to a paid grant. After an owner-approved evolved story returns `generationAllowed=true`, prepare a fresh YES/NO request containing that exact story ID/revision/SHA, prompt/version/SHA, analysis ID, settings hash, instruction-context SHA, the six role/profile bindings above and a recomputed total cap. This document is not paid authorization.

## Verification

- No-egress final-boundary compilation reproduced exact system/user payloads and hashes for STORY, STORY_REVIEW, BUILD_PROMPT, GENERATION, SOURCE_FIDELITY and CRITIC.
- Focused optimization/reconstruction/story/source/critic suite: **84 passed**, 0 failed. Backend `OptimizationLoopTest`: **12 passed**, 0 failed.
- Canonical engine, weights, parser and profile hashes were recorded. Rules, weights, threshold and parser behavior were unchanged.
- No production DB mutation, deployment, provider call, image/video generation, prompt approval, commit or push occurred.

Canonical A remains unverified by a real model. Official Creative A+ remains inactive and cannot be inferred from text scoring. Real video impact remains unknown until the separately governed visual/render evidence stages.
