TASK: STORY_REVIEW_STRUCTURED_OUTPUT_AND_SEMANTIC_CONTRACT_FIX

HISTORICAL_REAL_OPENAI_CALLS: 1
HISTORICAL_REAL_RESULT: STOPPED
HISTORICAL_COST_USD_TOKEN_RATE: 0.0015756
HISTORICAL_INVOICE_STATUS: UNVERIFIED

ORIGINAL_OUTPUT_DEFECTS: 13
ORIGINAL_OUTPUT_ACCEPTED: NO
ORIGINAL_RECEIPT_UNCHANGED: YES

MODEL: gpt-4o-mini-2024-07-18
STRICT_STRUCTURED_OUTPUT_SUPPORTED: YES
STRICT_SCHEMA_IMPLEMENTED: YES
SCHEMA_AND_VALIDATOR_ALIGNED: YES

REQUIRED_SEMANTIC_CHECKS_PER_CANDIDATE: 9
REQUIRED_CREATIVE_DIMENSIONS_PER_CANDIDATE: 6
SEMANTIC_PARAPHRASE_HANDLING: VERIFIED
UNSUPPORTED_FAIL_HANDLING: VERIFIED
CREATIVE_IMPROVEMENT_EVIDENCE: VERIFIED

FOUR_AUTHENTIC_NARRATIVES_PRESERVED: YES
SELECTED_REVIEW_CANDIDATES: 2

HISTORICAL_FAILED_RESPONSE_REPLAY: PASS
ML_REGRESSION_TESTS: 316_PASSED_EXIT_0
BACKEND_REGRESSION_TESTS: 46_PASSED_EXIT_0
DISPOSABLE_E2E: PASS

NEW_PAID_PROVIDER_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0

CURRENT_PRODUCTION_GATES_WEAKENED: NO
STORY_APPROVALS: 0
BUILD_PROMPT_CALLS: 0
VIDEO_RENDERS: 0
PRODUCTION_DATABASE_WRITES: 0
GIT_HISTORY_MODIFICATIONS_BY_AGENT: 0

REVISED_REQUEST_SHA: c786389ce1ff749f7e92ce5c6b928ac7f0592fa3daf4d03ea00d7ea78bd8caf5
REVISED_SCHEMA_SHA: 36c41a078f0826c0ce310710068d7543ad8813335b161106634f1b0a08890bc8
REVISED_SYSTEM_SHA: f7cfd303d2c6929256b68702334843080f9ad815800ec5ec29fb74d769690636
REVISED_IMPLEMENTATION_SHA: 36d859a398f2de62d7d0c945b76ef65059004d52d789f5578627364703f8e9e2

NEXT_MAX_PROVIDER_REQUESTS: 1
NEXT_RECOMPUTED_MAX_USD: 0.004755
NEXT_OWNER_SPENDING_AUTHORIZATION: NOT_GRANTED
READY_FOR_REAL_REVIEW: YES

# A. Root cause

The actual real call succeeded at transport and returned finish_reason=stop with only 1,737 completion tokens. Its 13 observed defects were output/evaluation failures, not demonstrated token exhaustion. The pinned model, source, narratives, old receipt, STOPPED run and original USD 0.0015756 rate calculation remain unchanged.

| Category | Proven observation and design gap | Repair |
|---|---|---|
| A: hierarchy | The user payload embedded an output-shaped `responseContract` object; the model returned its candidate array inside that exact wrapper. The transport specified json_object, so no hierarchy was provider-enforced. | Remove pseudo-response from payload; strict root schema and fixed candidate keys A/B. |
| B: eight missing checks | The output example had one generic findings entry, while five protected anchors and four additional checks were listed separately. Only the five anchors appeared in the real response. Completeness existed in prose/local rejection logic, not provider structure. | Nine required keys under each candidate’s semanticChecks, with no extras. |
| C: three unsupported FAILs | Empty candidate quotations accompanied A.rule, A.continuity and B.continuity FAILs. The old prompt warned against assuming paraphrase but did not operationally distinguish contradiction, substantive omission and missing literal wording. | Explicit outcome/evidence basis and authentic quotations; absent identical wording alone cannot justify FAIL. |
| D: preference enum | The pseudo-response contained the literal string `A \| B \| NO_CREATIVE_WINNER`; the model copied it. | A true schema enum; no literal alternatives example. |
| E: unsupported creativity | Both MATERIAL_IMPROVEMENT reasons were the same generic criticism. The old validator required a nonempty reason but no baseline/change/consequence evidence. | Mandatory comparative fields plus conservative local materiality evidence checks; no eligible preference from generic claims. |

The matching responseContract wrapper and enum-copy pattern support the inference that the example format encouraged literal copying. Internal model reasoning was not observed, so this is an evidence-based design diagnosis, not a claim about its hidden cognition. Correctly refusing the old response remains required.

The old messages repeated the response description across system instructions and a nested pseudo-schema, required check identifiers partly through prose, and supplied derived evidence containing repeated narrative/source excerpts. Generator SOURCE_COMPLIANT labels were already excluded from authority; invalid-citation lists remain explicitly unusable. The previous contract did not require the comparative evidence now required for materiality. The repaired payload contains the original once, authentic candidates once, protected facts, compact literal positions, invalid claims and historical provenance. It does not contain a sample output object or the JSON Schema.

# B. Exact before/after provider request

Old real request, preserved unchanged:
```json
{"model":"gpt-4o-mini-2024-07-18","max_tokens":4000,"temperature":0,"response_format":{"type":"json_object"}}
```

[Complete historical prepared messages](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/authentic-story-independent-review-result-evidence/exact-proposed-openai-request.json); [historical system](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/authentic-story-independent-review-result-evidence/reviewer-system.txt); [historical user](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/authentic-story-independent-review-result-evidence/reviewer-user.txt). These are saved application request bindings, not a provider echo or network capture.

Repaired transport configuration:
```json
{"model":"gpt-4o-mini-2024-07-18","max_tokens":4000,"temperature":0,"response_format":{"type":"json_schema","json_schema":{"name":"independent_story_review_v2","strict":true,"schema":"SEE COMPLETE ACTUAL SCHEMA BELOW"}}}
```
The quoted SEE marker is explanatory only; the actual request contains the complete schema object. [Complete actual future SDK body](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/next-exact-sdk-request.json); [exact system](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/next-system.txt); [exact user](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/next-user.txt).

The official documentation lists this exact snapshot as supporting strict Structured Outputs. All fields must be required and objects closed. The implementation uses only the common supported object/string/boolean/enum/local-reference subset, with five expanded object levels; it avoids conditional schemas, tuple arrays, patterns, length constraints and root unions. [Official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).

Installed OpenAI SDK **3.32.0**, httpx **0.28.1**, and jsonschema **4.26.0** were exercised offline. The genuine SDK serialized the exact pinned model and complete response_format schema in all 10 final HTTP E2E scenarios. No SDK upgrade was necessary. The adapter already supported an explicit response_format; this review now supplies it, with no JSON-object fallback. The adapter’s only additional shared change records provider refusal metadata. The snapshot is documented deprecated, so future account availability is unproven and any unavailable-model response must stop without substitution. [Pinned model documentation](https://developers.openai.com/api/docs/models/gpt-4o-mini).

# C. Complete response schema

The schema below is passed unchanged to the provider and used by the local Draft202012Validator. candidateAssessments is an object keyed by A and B; each has fixed semantic and creative keys. Unknown fields, missing keys, extra candidates and copied enum alternatives fail locally even if a provider violates its contract.
```json
{
  "type": "object",
  "properties": {
    "schemaVersion": {
      "type": "string",
      "enum": [
        "assessment-only-story-review-v2"
      ]
    },
    "candidateAssessments": {
      "type": "object",
      "properties": {
        "A": {
          "$ref": "#/$defs/candidate"
        },
        "B": {
          "$ref": "#/$defs/candidate"
        }
      },
      "required": [
        "A",
        "B"
      ],
      "additionalProperties": false
    },
    "researchPreference": {
      "type": "string",
      "enum": [
        "A",
        "B",
        "NO_CREATIVE_WINNER"
      ]
    },
    "reason": {
      "type": "string"
    },
    "evidenceLimitations": {
      "type": "string"
    }
  },
  "required": [
    "schemaVersion",
    "candidateAssessments",
    "researchPreference",
    "reason",
    "evidenceLimitations"
  ],
  "additionalProperties": false,
  "$defs": {
    "semantic": {
      "type": "object",
      "properties": {
        "outcome": {
          "type": "string",
          "enum": [
            "PASS",
            "FAIL",
            "UNKNOWN"
          ]
        },
        "basis": {
          "type": "string",
          "enum": [
            "SEMANTIC_SUPPORT",
            "CONTRADICTION",
            "SUBSTANTIVE_OMISSION",
            "INSUFFICIENT"
          ]
        },
        "sourceQuote": {
          "type": "string"
        },
        "candidateQuote": {
          "type": "string"
        },
        "reason": {
          "type": "string"
        }
      },
      "required": [
        "outcome",
        "basis",
        "sourceQuote",
        "candidateQuote",
        "reason"
      ],
      "additionalProperties": false
    },
    "dimension": {
      "type": "object",
      "properties": {
        "quote": {
          "type": "string"
        },
        "strength": {
          "type": "string"
        },
        "weakness": {
          "type": "string"
        },
        "risk": {
          "type": "string"
        }
      },
      "required": [
        "quote",
        "strength",
        "weakness",
        "risk"
      ],
      "additionalProperties": false
    },
    "comparison": {
      "type": "object",
      "properties": {
        "outcome": {
          "type": "string",
          "enum": [
            "MATERIAL_IMPROVEMENT",
            "MINOR_VARIATION",
            "NO_MATERIAL_IMPROVEMENT",
            "UNKNOWN"
          ]
        },
        "baselineQuote": {
          "type": "string"
        },
        "candidateQuote": {
          "type": "string"
        },
        "change": {
          "type": "string"
        },
        "visibleConsequence": {
          "type": "string"
        },
        "addressedWeakness": {
          "type": "string"
        },
        "newRisk": {
          "type": "string"
        },
        "materialityReason": {
          "type": "string"
        }
      },
      "required": [
        "outcome",
        "baselineQuote",
        "candidateQuote",
        "change",
        "visibleConsequence",
        "addressedWeakness",
        "newRisk",
        "materialityReason"
      ],
      "additionalProperties": false
    },
    "candidate": {
      "type": "object",
      "properties": {
        "semanticChecks": {
          "type": "object",
          "properties": {
            "identity": {
              "$ref": "#/$defs/semantic"
            },
            "premise": {
              "$ref": "#/$defs/semantic"
            },
            "rule": {
              "$ref": "#/$defs/semantic"
            },
            "continuity": {
              "$ref": "#/$defs/semantic"
            },
            "ending": {
              "$ref": "#/$defs/semantic"
            },
            "trigger_conditions": {
              "$ref": "#/$defs/semantic"
            },
            "single_mechanic": {
              "$ref": "#/$defs/semantic"
            },
            "causal_clarity": {
              "$ref": "#/$defs/semantic"
            },
            "protected_events": {
              "$ref": "#/$defs/semantic"
            }
          },
          "required": [
            "identity",
            "premise",
            "rule",
            "continuity",
            "ending",
            "trigger_conditions",
            "single_mechanic",
            "causal_clarity",
            "protected_events"
          ],
          "additionalProperties": false
        },
        "semanticOutcome": {
          "type": "string",
          "enum": [
            "SEMANTIC_SOURCE_PASS",
            "SEMANTIC_SOURCE_FAIL",
            "SEMANTIC_SOURCE_UNKNOWN"
          ]
        },
        "sourceUnknowns": {
          "type": "string"
        },
        "creativeDimensions": {
          "type": "object",
          "properties": {
            "SCROLL_STOP_VISUAL_PROMISE": {
              "$ref": "#/$defs/dimension"
            },
            "CAUSAL_PROGRESSION": {
              "$ref": "#/$defs/dimension"
            },
            "VISUAL_STORYTELLING": {
              "$ref": "#/$defs/dimension"
            },
            "PRODUCTION_EXECUTABILITY": {
              "$ref": "#/$defs/dimension"
            },
            "ENDING_REPLAY": {
              "$ref": "#/$defs/dimension"
            },
            "DISTINCTIVE_CREATIVE_VALUE": {
              "$ref": "#/$defs/dimension"
            }
          },
          "required": [
            "SCROLL_STOP_VISUAL_PROMISE",
            "CAUSAL_PROGRESSION",
            "VISUAL_STORYTELLING",
            "PRODUCTION_EXECUTABILITY",
            "ENDING_REPLAY",
            "DISTINCTIVE_CREATIVE_VALUE"
          ],
          "additionalProperties": false
        },
        "creativeConclusion": {
          "$ref": "#/$defs/comparison"
        },
        "eligibleForOwnerProposal": {
          "type": "boolean"
        }
      },
      "required": [
        "semanticChecks",
        "semanticOutcome",
        "sourceUnknowns",
        "creativeDimensions",
        "creativeConclusion",
        "eligibleForOwnerProposal"
      ],
      "additionalProperties": false
    }
  }
}
```

[Standalone machine-readable schema](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/strict-response-schema.json); [Actual SDK-serialized test requests](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/actual-serialized-sdk-requests.jsonl).

# D. Semantic evaluation repair

| Decision | Required basis and evidence |
|---|---|
| PASS | SEMANTIC_SUPPORT: affirmative candidate meaning, including paraphrase; exact excerpts from source and candidate. |
| FAIL | CONTRADICTION or SUBSTANTIVE_OMISSION: identify the conflicting fact or substantive narrative-level omission, quote the protected source and relevant actual candidate context, and explain the violation. |
| UNKNOWN | INSUFFICIENT: preservation/contradiction unresolved; empty evidence is allowed; a specific open source question is mandatory. |

Literal location remains the deterministic extractor’s responsibility; semantic preservation is a reviewer opinion. The independent reviewer cannot paste the source clause into a candidate quotation that does not exist. Definite judgments require both nonempty quotations, all nonempty quotations must occur in the corresponding authentic text, and an absence-only exact-wording FAIL is rejected. Missing a mandatory structural check never becomes UNKNOWN or PASS automatically: the whole output is rejected.

Aggregation remains any FAIL → SEMANTIC_SOURCE_FAIL; otherwise any UNKNOWN → SEMANTIC_SOURCE_UNKNOWN; only all PASS → SEMANTIC_SOURCE_PASS. Contradictory aggregation, unsupported eligibility and an eligible research preference from source FAIL/UNKNOWN are rejected. The new sourceUnknowns field exposes unresolved questions rather than silently clearing them.

Offline cases accept evidence-bearing paraphrase such as A’s “The notes stay put.” followed by sneeze release without requiring a copied continuity sentence. They preserve UNKNOWN where the trigger/removal intention is unresolved. Isolated synthetic contradiction and unauthorized-trigger tests exercise negative admission with real conflicting quotations in their test narrative; they do not alter or certify the authentic candidates. These tests prove contract handling of supplied opinions, not machine understanding of arbitrary prose.

The original P2 protection catalog contains five locks. Its incidental mirror staging is not independently locked. The new protected_events instruction checks substantive realization of the protected facts, not every original verb/action. An omitted mirror alone is not a protected-story violation. No source event was added, removed or rewritten by this task.

# E. Creative improvement evidence

Fidelity and creative merit remain separate. Each of six fixed dimensions requires a candidate excerpt, strength, weakness and risk/uncertainty; unsupported dimensions can explicitly stay UNKNOWN. creativeConclusion independently records outcome, baselineQuote, candidateQuote, change, visibleConsequence, addressedWeakness, newRisk and materialityReason.

MATERIAL_IMPROVEMENT requires all comparative evidence fields, authentic source/candidate excerpts, a source-specific change/consequence, an addressed baseline weakness and an explicit new risk. A conservative existing-vocabulary guard rejects identical/synonym-only evidence, generic ungrounded claims and cosmetic-only change descriptions. Missing support causes rejection, not silent downgrading or server-authored replacement opinions. NO_MATERIAL_IMPROVEMENT, MINOR_VARIATION, UNKNOWN and NO_CREATIVE_WINNER are valid. Definite invented audience/render/A+ claims are rejected; statements that audience evidence is absent remain valid uncertainty.

These are bounded evidence/claim guards, not another creative scoring engine. Lexical grounding can still miss subtle paraphrases or false implications; convincing prose with exact quotations can still be wrong. No deterministic token test can establish genuine creative merit. The historical generic MATERIAL_IMPROVEMENT labels cannot create a winner or owner eligibility under this contract. A new real independent review is still needed to establish whether either authentic narrative actually improves on the source.

# F. Historical replay and preservation

Historical real run `STOPPED` / `59f47fec-59fb-42e3-b3a4-c9f7d83c7ffc`; raw SHA `7963c59ce4401e0945780d6d935800d4dbd54514e62612620d661f6074621e7f`. Original validator replay rejects it with `Both independent candidate assessments required`. The repaired strict validator also rejects the exact same bytes. It does not unwrap responseContract, add checks, invent quotes, choose a preference, relabel the old FAIL or reinterpret the creative labels as accepted findings.

[historical-failed-response-replay.json](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/historical-failed-response-replay.json); [Archived original validator used only for offline replay](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/legacy-validator.py.txt); [historical-integrity.json](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/historical-integrity.json).

All 33 historical generation-artifact hashes, all four narrative hashes, all preexisting real-review result artifacts, the original prepared manifest/source catalog and the original real-review DB dump were verified unchanged. Candidate A’s historic requested/returned model mismatch remains failed; B’s historic invalid continuity citation remains invalid.

# G. Actual regression results

| Verification | Actual result |
|---|---|
| ML: existing relevant suites + strict contract adversarial coverage | 316 passed; 343 existing warnings; exit 0 |
| Java StoryExperimentContractTest | 39 passed |
| Java StoryEvolutionServiceTest | 5 passed |
| Java StoryReviewIndependenceTest | 2 passed |
| Backend total | 46 passed; zero failures/errors/skips; exit 0 |
| Disposable full HTTP integration | 10 final scenarios passed; exit 0 |
| Revised request preparation | Matched final application proof; exit 0; no dispatch |

[Exact commands and counts](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/test-results.json); [ml-regression.log](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/ml-regression.log); [backend-regression.log](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/backend-regression.log). Initial local failures are recorded: the legacy replay test omitted a constant from its namespace; an overbroad performance-claim guard initially rejected a negative evidence statement. Both were corrected with regression coverage; final runs above passed.

| Requested coverage | Actual tests/evidence |
|---|---|
| Correct topology/identities/all required fields/closed objects/enums | Fixed-key schema audit; 18 missing-check and 12 missing-dimension mutations; missing/extra candidate/field and copied-enum negatives. |
| Exact source/candidate excerpts, paraphrase and uncertainty | Verbatim/paraphrase/UNKNOWN examples; fake source/candidate quotes; empty FAIL; literal-absence FAIL; evidence-basis and aggregation negatives. |
| Contradiction and unauthorized trigger | Isolated synthetic conflicting narrative cases, never substituted for the authentic stories. |
| Creative integrity | Generic/empty/fake comparison evidence, synonymous/cosmetic evidence, invented audience/A+ claims; concrete hypothesis accepted without eligibility; conservative no-improvement accepted. |
| Existing security and paid boundaries | Old paid grant rejected before provider construction/reservation; drift/model/price/instruction changes rejected; unsigned HMAC path rejected; no repeat dispatch marker. |
| Genuine SDK behavior | Actual installed SDK request serialization with external HTTP mocked only; refusal, length, malformed, schema, quotation and timeout receipts. |
| Production safety | Actual Java/FastAPI source reads, OWNER/CSRF/HMAC, one ledger reservation/receipt per scenario, no drafts, rejected approval/BUILD_PROMPT, no render authorization. |

# H. Disposable E2E

The final integration used the actual Java app and FastAPI service, the existing genuine P2 snapshot and archive readers, normal owner authentication, CSRF, HMAC and V71 immutable ledger. Only the external OpenAI HTTP transport was mocked through httpx.MockTransport; the existing OpenAIProvider and installed SDK performed normal serialization/decoding. No provider client or application service was replaced. No real credentials were loaded into ML: only an explicitly fake placeholder, with all external sockets denied.

| SDK response scenario | Actual terminal state |
|---|---|
| positive | ASSESSMENT_COMPLETE_OWNER_DECISION_PENDING |
| historical | STOPPED |
| missing-check | STOPPED |
| fake-quote | STOPPED |
| invalid-enum | STOPPED |
| aggregation | STOPPED |
| refusal | STOPPED |
| incomplete | STOPPED |
| malformed | STOPPED |
| timeout | STOPPED |

Every final scenario issued exactly one mocked external request, persisted one REQUEST_RESERVED and one PROVIDER_RECEIPT, and retained full returned SDK data before parsing. Timeout had no received SDK response and correctly retained unknown spend. Successful integration stayed owner-decision-pending with UNKNOWN semantic/creative fixture judgments and no drafts. Idempotent re-POST and subsequent scheduler intervals did not dispatch another request. Actual approve and prompt-handoff commands were rejected with 409. The old real paid grant was rejected before reservation. All non-ledger table counts were unchanged, including 12 source workflow records.

[Complete scenario results](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/http-e2e-results.json); [Positive actual application proof](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/http-positive-proof.json); [Historical response replay in actual workflow](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/http-historical-run.json); all per-case run/checkpoint files are in the same evidence folder.

After evidence capture, only this task’s test processes/containers were stopped. Final dump: [post-http-e2e.dump](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/backend/target/structured-story-review-http-v5/post-http-e2e.dump); SHA `25a83e45c04eb0a228504bf20777249f66440ff407e39fc480dc206af44a6432`. The dump has owner-only file permissions. No production database or deployment was used. Earlier intermediate test runtimes were stopped as well; other services were untouched.

A successful mocked E2E establishes implementation readiness only. It does not prove that a real model will produce correct semantic judgments or a thoughtful creative comparison.

# I. Revised one-request authorization scope

[New disabled prepared manifest](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/STORY_REVIEW_STRUCTURED_OUTPUT_REVIEW_MANIFEST.json). The historical manifest was not overwritten.

| Field | Fresh exact value |
|---|---|
| Policy | ASSESSMENT_ONLY_UNKNOWN_SOURCE_V1; already owner approved |
| Provider / model | openai / gpt-4o-mini-2024-07-18 |
| Role | STORY_REVIEW only |
| Mode | json_schema; strict=true |
| Output cap | 4,000 tokens |
| SDK / backend timeout | 20s / 25s, unchanged |
| Run cap | 600s |
| Maximum requests | 1 |
| Generation / retry / fallback / automatic paid resume | Prohibited |
| Fresh owner spending authorization | NOT_GRANTED |
| Source scope SHA | `5be45f1966d1a2ab8c8fa03e4570f67c090024fa038a34c6ba012055e0e3fcac` |
| User request SHA | `c786389ce1ff749f7e92ce5c6b928ac7f0592fa3daf4d03ea00d7ea78bd8caf5` |
| System SHA | `f7cfd303d2c6929256b68702334843080f9ad815800ec5ec29fb74d769690636` |
| Schema SHA | `36c41a078f0826c0ce310710068d7543ad8813335b161106634f1b0a08890bc8` |
| Response format SHA | `ebf4f3794cf6488e55e03814e5a1dd23f7100d5805ffc40ad1224141ada0b1ff` |
| Whole SDK request SHA | `895a8798f74933c2d1a278eceb8ef676ae8e6b94fe3e76b537e2499860ab6280` |
| ML implementation SHA | `36d859a398f2de62d7d0c945b76ef65059004d52d789f5578627364703f8e9e2` |
| Backend authority SHA | `e6f7ba5c22899e3098fb9f409f3ad7bc50b1b87e540986b65e88e68ef70974f1` |
| Source catalog SHA | `e62351dfea8677da427296312a6a1bccd4ff2c1aa8acfd4cc6defc735915b665` |
| Candidate A SHA | `50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088` |
| Candidate B SHA | `4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739` |

Source bytes, two narratives, historical IDs and protected settings remain identical. The source scope SHA therefore remains unchanged; operation/system/schema/implementation and whole-request bindings changed, so the old authorization cannot apply. The new grant has a different operation-derived idempotency key and both paid-confirmation booleans false. All 10 actual SDK-serialized final test bodies equal the new prepared providerRequest.

The revised user payload is 7,498 bytes, system 2,999 bytes, schema 3,381 bytes and complete serialized request 14,695 bytes including escaped messages, schema and transport fields. The entire request fits the unchanged 24,000-byte ceiling. Current configured rates match documented input/output rates of USD 0.15/0.60 per million. The existing conservative byte-per-token bound now counts the full SDK envelope and its schema, plus 1,000 framing bytes:
```text
((14695 + 1000) × 0.15 + 4000 × 0.60) / 1,000,000
= USD 0.00475425
Reservation rounded upward to six decimals = USD 0.004755
```

No account billing or invoice was inspected; this is a conservative configured-rate reservation, not a billed charge. It does not reuse any part of the historical USD 0.004867 grant. No configuration, input envelope, token cap or timeout was increased.

The complete representative **synthetic offline** review contains 18 checks and 12 creative dimensions plus source questions and comparative conclusions. o200k_base measured 1,931 output tokens compact or 2,577 with indentation, below 4,000. This demonstrates room for concise meaningful findings, not a worst-case proof that every real response will fit. The actual provider may tokenize schema/transport overhead differently; local estimates are not verified provider usage. A future refusal or length-limited answer will stop without repair calls.

[Complete offline capacity example](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/representative-offline-review.json); [Tokenizer measurements](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/story-review-contract-fix-evidence/token-envelope.json).

# J. Remaining limitations and stop boundary

- Documented model support plus successful installed-SDK serialization does not prove current account availability; no real provider request was made in this task.
- Provider-enforced schema controls shape, not semantic accuracy, physical causality, reliable quotations or creative merit; local evidence checks remain authoritative but cannot prove every implication in prose.
- Materiality grounding and explicit-claim guards are conservative checks with possible false positives/negatives. Source-specific comparative prose can still be misleading; no new semantic oracle or scoring engine is claimed.
- The positive fixture, synthetic contradiction tests and representative capacity example are labelled test data. They are not real OpenAI judgments and not proof of autonomous creative effectiveness.
- A real review would still be MACHINE_REVIEW and cannot establish rendered success, audience performance, canonical A/A+, production source admission or story approval.
- Schema and prompt changes invalidate the previous paid authorization. A separately authorized future single review is required; no automatic retry, fallback or dispatch is scheduled.

# Implementation paths and operational record

| File | Focused change |
|---|---|
| intelligence/ml-service/app/workflow/story_assessment.py | Strict v2 schema, compact evidence payload, semantic/materiality validation, full-request fingerprints/budget, explicit refusal/incomplete stop. |
| intelligence/ml-service/app/llm/openai_provider.py | Preserve refusal in response metadata; reuse existing response_format support. |
| intelligence/scripts/prepare-creative-story-experiment.py | Separate structured-review preparation output and exact schema/messages; disabled fresh grant. |
| intelligence/ml-service/tests/story_experiment_fixture.py | Adapt explicitly synthetic review fixture to fixed keys; preserve authentic archived inputs. |
| intelligence/ml-service/tests/story_experiment_bridge.py | Existing Java test bridge adapted to v2 fields. |
| intelligence/ml-service/tests/test_story_assessment.py | Existing contract regression updates. |
| intelligence/ml-service/tests/test_story_assessment_strict_contract.py | Fixed schema, archived response, evidence/creative/security and actual SDK transport regressions. |
| intelligence/ml-service/tests/story_assessment_cases.py | Labelled offline scenario responses and materiality hypothesis. |
| intelligence/ml-service/tests/story_assessment_http_sdk.py | Test-only actual SDK/HTTP transport mock server with external network denied. |
| intelligence/backend/src/test/java/com/pompomhills/intelligence/workflow/StoryExperimentContractTest.java | Read fixed-key candidate A in existing admission assertion; production Java unchanged. |

The existing Java authorization and scheduler continue to re-read sources, compare the complete bound operation, reserve durably and prevent assessment approval/BUILD_PROMPT. No new service, engine, endpoint, table or migration was introduced. Ruleset 1.11 and production gates were not changed.

Observed Git HEAD at report writing: `cf3bbb969ebddb6ec9a98321e5cec24979b44a86`. HEAD changed externally during the work; its actor is not attributed. The agent performed no commit, amend, reset or push, and did not revert external changes.

The repair is technically ready for a separately authorized real review. This task stops with **zero new paid calls**, no production deployment, no story/prompt approval and no generation.
