# Semantic Evidence Adapter V1 — stored-response analysis

The adapter distinguishes source evidence presence from taxonomy classification and from scoring-validator recognition. It creates no ideas, assigns no scores, and changes no admission thresholds. All analysis uses the first live response and existing mock regression fixtures. The original live record remains immutable.

The result is **33 explicit, consistent terminal payoff declarations; zero missing payoffs; 33 present-but-unclassified payoffs**. The canonical Creative Shape output remains UNKNOWN for all 33, and the canonical scores remain 18–46 (mean 27.6364, median 28). Projection completeness must not be reported as complete recognition by SHORT_FORM_ENGINE.

## Architecture and boundary

Stored raw response → accepted semantic parser/normalizer → source-only normalized evidence fields → `SEMANTIC_EVIDENCE_ADAPTER_V1` → unchanged accepted ranking input → unchanged validators. Typed canonical evidence and recognition/loss diagnostics travel beside the accepted plan.

The adapter reconstructs a lossless field view from already-stored semantic schema fields. It preserves the legacy normalized candidate separately, so recovery does not conceal earlier loss. It excludes provider rationale, suggested payoff labels, provider scores and eligibility assertions from the evidence domain. Raw views retain these as untrusted source metadata.

`SourceEvidence` records sourceType `SEMANTIC_NORMALIZED_FIELD`, sourceField, exact/whitespace-normalized sourceText, a versioned projectionRule, and confidence (`EXPLICIT`, `STRUCTURED_INFERENCE`, or `AMBIGUOUS`). Declared text is explicit evidence of a declaration, not proof of coherent causality or visibility. Known classifications are obtained from the existing normalizer/Creative Shape; no taxonomy is expanded.

The accepted SFE/ranking interface consumes timed prose; it has **no structured evidence override input**. This adapter preserves that canonical plan, including matching frame-zero/payoff carriers required by ranking. It projects goal/object/rule into accepted explicit input fields and retains unsupported evidence slots in the typed contract. It does not insert marker words, rewrite scenes, monkeypatch feature extraction, or pass an ignored context dictionary while claiming recognition improved.

Consequently the adapter establishes that source evidence is present, but it does not make the unchanged scoring engine understand all semantic prose. The remaining SFE integration/semantic-classification gap is explicit. It would require a separately reviewed future change. This task stops before that change.

The canonical domain schema contains no vendor-specific fields; a later manual-source normalizer can target the same field/evidence design. No manual provider is implemented.

## Source mapping and schema

See `canonical-evidence-schema-v1.json` and `mapping-rules-v1.json` for exact machine-readable contracts. Mappings include:

| Source field | Evidence field |
|---|---|
| everydayGoal | visibleGoalEvidence |
| primaryObject | primaryObjectEvidence |
| normalExpectation | expectedAffordanceEvidence |
| impossibleRule | coreRuleEvidence |
| visibleTrigger | triggerEvidence |
| frameZeroDescription | openingProblemEvidence |
| beats[].strategy | beatStrategyEvidence |
| beats[].visibleConsequence | consequenceEvidence |
| beats[].newInformation | progressionEvidence |
| finalPayoff | payoffEvidence |
| loopPotential | loopEvidence / providerDeclaredLoop |
| whyThisObject | affordanceRelationshipEvidence |
| goalRuleRelationship | goalRuleRelationshipEvidence |

The source-only projection counts described and fully specified beats, not valid causal developments. The live data contains 165 described/fully specified beats; SFE supports 38 causal beats. Provider-declared loops remain distinct from independently supported intentional loops. Each opening audit separately retains raw-frame lexical features, the declared goal/relationship, and the existing raw-opening naturalness result. No actual video is inspected.

## Baseline and adapter replay

The control replays the saved response before enabling the adapter and compares the entire baseline result against the original stored validation. It matches exactly. Both paths are semantic stored-response replay; hybrid and deterministic regeneration are rejected.

| Metric | Control | Adapter replay / evidence |
|---|---:|---:|
| Raw / schema-valid / normalized | 40 / 38 / 33 | 40 / 38 / 33 |
| Canonical goal recognized | 3/33 | 3/33; projected declaration 33/33 |
| Canonical opening trouble recognized | 0/33 | 0/33; opening field present 33/33 |
| Canonical rule recognized | 21/33 | 21/33; declared rule present 33/33 |
| Canonical trigger recognized | 13/33 | 13/33; declared trigger present 33/33 |
| Supported / described causal beats | 38/165 | 38/165 |
| Canonical qualifying payoff recognized | 0/33 | 0/33; declared payoff present 33/33 |
| Canonical payoff classified | 0/33 | 0/33 |
| Intentional loop supported | 0/33 | 0/33; loop declaration preserved 33/33 |
| SFE min / max / mean / median | 18 / 46 / 27.6364 / 28 | unchanged |
| Revision / reject / malformed | 21 / 12 / 7 | unchanged |
| Existing review set | 0 | 0 |
| Expanded diagnostic review set | — | 13 |
| Production candidates | 0 | 0 |

Payoff audit: MISSING **0**, PRESENT_CLASSIFIED **0**, PRESENT_UNCLASSIFIED **33**, AMBIGUOUS **0**. Each candidate audit includes finalPayoff, last visibleConsequence, last newInformation and the untrusted suggested payoff family; the latter never supplies a classification.

The old semantic plan adapter yields 32 terminal `CHARACTER_ATTEMPTS_CONTROL` relationships and one `OBJECT_DISPLACES_BODY`. Those relations do not enter the accepted Creative Shape terminal branches, so they produce UNKNOWN. This is classification/extraction coverage, not disappearance of the raw ending. SFE independently has narrow goal/rule/payoff patterns. Both layers can fail to read semantic wording.

## Field loss, diagnoses and review

Every candidate has RAW → legacy NORMALIZED → lossless normalized fields → PROJECTED → VALIDATOR RECOGNITION rows. Statuses distinguish preservation, normalization loss, projection loss, validator extraction loss, ambiguous source, and missing source. The original normalizer preserves the other inspected source fragments but loses the verbatim visibleTrigger for all 33 (it keeps a coarse trigger token); replay recovers that declaration from stored source. No field is silently repaired with a new action.

All 33 source projections are complete, but **zero candidates have complete SFE recognition** under the separately counted goal/opening/rule/trigger/payoff/beat criteria. Therefore the unchanged low scores cannot be treated as a controlled test of fully understood semantic ideas. Presence also cannot establish that the ideas are good.

All 33 scores are still below 60. No canonical score or outcome changes, and no material score changes occur. Re-diagnosis has 60 dimension transitions from UNKNOWN to EVIDENCE_EXTRACTION_FAILURE (27 declared-goal wording gaps plus 33 terminal-payoff recognition gaps). There are no evidence-failure-to-content-failure transitions automatically established. This classification is observational: it identifies unsupported recognition, not a promise of creative quality. Some source endings introduce additional behaviors; human review must assess coherence independently.

The expanded review policy adds candidates only if an unclassified payoff/engine has complete source evidence, 4–5 fully specified beats, at least four distinct visible consequences, and existing BG strategy diversity ≥75 and information gain ≥60. These are review-only filters; all BG scores remain as computed, and canonical ranking/admission is untouched. Thirteen candidates qualify: raw-001, 003, 005, 006, 007, 009, 013, 015, 016, 020, 026, 031, 032.

All 33 present-unclassified payoff cases, all 28 present-unclassified engine cases, every low-score candidate, every diagnosis change, and the review-set entries are explicitly listed in `results-summary.json` and the complete candidate report.

## Existing regression fixtures

No fixture content changes. Towel: 18 → 18; Eraser: 19 → 19; both declare goal/rule/trigger/beats/payoff explicitly, and existing Creative Shape identifies PROPERTY_TRANSFER, while SFE remains unable to support their full causal/payoff evidence. Lid environmental takeover: 100 → 100, ELIGIBLE, with identical production selection and canonical ranking. This is evidence for future SFE semantic-generalization review, not a reason to modify it here.

## API, CLI and UI

ML route: `POST /api/v1/workflow/concepts/semantic/replay`. Java forwards the corresponding `/api/v1/intelligence/workflow/concepts/semantic/replay` request without injecting cast or invoking generation. The request accepts only the fixed experimentId, optional `semanticEvidenceAdapterVersion: "v1"` (default off), and `allowExternalGeneration: false`. Provider options, custom source payloads and filesystem paths are rejected.

The existing concept page adds an explicit stored-reanalysis button and Raw / Normalized / Projected Evidence / Validator Recognition detail panels with loss highlighting. There are no requests on page load and no generation/production changes.

The dedicated CLI has no provider/generation flags. It strips credential variables and denies socket/address-resolution/subprocess activity before replay. It writes into a new output directory only. Example:

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/reanalyze-semantic-evidence.py \
  --semantic-evidence-adapter-version v1 --output /new/derived-analysis-directory
```

## Verification and artifacts

Tests use only stored live/mock concepts and existing authored validator fixtures. Generator-regeneration suites are not run for this task. Python tests use the credential-stripping, network-denying existing offline harness. UI verification uses npm offline mode with update checks disabled. Java uses Maven offline mode. Exact results and hashes are in `verification.json` and `protected-after.json`.

Final evidence: `replay-final/analysis.json`. Independent hash-seed replay: `replay-repro/analysis.json`. Full human-readable three-view audit of all 33 normalized candidates: `all-33-three-view-audit.txt`. The seven original excluded raw entries remain in the derived JSON without repair or admission. `replay/` is an intermediate diagnostic draft retained separately, not the final result.

The original live run, previous accepted sources/fixtures, and all 282 protected file hashes remain unchanged. No scoring engine, threshold, taxonomy, historical rule or protected source is edited. No provider request, new concept, production prompt or media is generated.
