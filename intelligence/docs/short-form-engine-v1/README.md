# SHORT_FORM_ENGINE v1

Additive, opt-in editorial screening for the primary ~15-second Pompom format. This extends the existing workflow/story-quality checks with a dedicated deterministic assessor, using the existing canonical strategy normalizer. It does not replace or modify STORY_PREMISE_ENGINE, canonical scores, CPQ calibration, rulesets, or frozen evidence.

## Activation and architecture

- **Offline concept surface:** `POST /api/v1/workflow/short-form/evaluate`, body `{ "text": "<complete timed plan>", "desiredDuration": 15 }`. Duration is optional; otherwise read from the timed plan. This route runs no canonical evaluation and constructs no AI provider.
- **Browser/backend surface:** `POST /api/v1/intelligence/workflow/short-form/evaluate`, same body. The new controller forwards only to the offline operation, without saving/regrading historical records.
- **Prompt validation:** explicitly set `workflow_context.shortFormEvaluation: true` alongside the normal valid workflow context (`sourceId`, `sourceVersion`, `profile`, etc.). The optional report appears at `pre_render_assessment.short_form_engine`. Removing this property gives exactly the ordinary report. Existing authorization/readiness and scores remain unchanged.
- **Workflow review/candidate/creative-validity:** set `shortFormEvaluation: true` in the existing request/context. The optional report is `shortFormEngine`; candidate and creative-validity surfaces flag short-form revision risks. Candidate preference uses independent short-form scores only in the new surface, and cannot clear any existing blocking gate. STORY_REVIEW cannot recommend a candidate that fails the opted-in short-form assessment.
- **CPQ preview:** `POST /api/v1/workflow/creative-prompt-quality/assess` accepts explicit `shortFormEvaluation: true`. Independent `shortFormEngine.original` and `.candidate` reports are added; CPQ's uncalibrated grade/aggregate remain unchanged.
- **UI:** an expandable “15-second short-form assessment” panel precedes the long-form report. Clicking “Evaluate short-form plan” explicitly requests the offline report. No automatic provider/generation call, source edit or saved-report migration occurs. Source changes cancel pending requests and clear stale results.
- **Export:** optional source-evidence text projections in existing report export paths; only pure text projection tests were run. No PDF was generated.

The assessor is inert unless the context contains the exact boolean opt-in. Optional response fields are omitted when absent; false/null/omitted opt-in preserves old fingerprints. True is included in workflow binding. Primary duration calibration is 10–20 seconds, centered on 15. Out-of-range or incomplete timing requires revision; changing duration metadata cannot magically compress a long plan.

## Evidence and scoring

Scores are independent English-language editorial heuristics, not calibrated retention probabilities, canonical grades or video observations. Source spans, exact quotes, source SHA-256 and per-block progression reasons are returned. Described time blocks and major causal developments are separate counts. A block can contain several physical actions but earn no development credit.

The report covers immediate goal/anomaly legibility, frame-zero trouble, concrete everyday goal, dominant rule, materially changing attempts, causal beat density, progress density, escalation gaps, continuation value, physical payoff, optional replay, structural duplication, silent clarity, dialogue, staging and production risk. Early understanding of the rule is beneficial; no moral arc is required.

Major beats earn support for understanding, strategy, escalation, consequence or payoff. Motion/reactions alone do not qualify. New magnitude, position, information, constraint and visible stakes can advance the same action. Explicit growing consequences can continue to progress; identical pushes with the same outcome cannot. Four to five causal beats are preferred; six is acceptable; fewer than four needs revision and more than six warns about overload. Timing gaps over four seconds warn about plateaus. Missing timing stays unverified rather than receiving invented timestamps.

The weighted short-form score uses hook 20%, goal 12%, rule 12%, causal beat density 10%, progress density 14%, escalation 10%, payoff 16% and silent legibility 6%. Under 25 is REJECT; explicit revision findings or scores below 70 require revision; otherwise warnings distinguish PASS_WITH_WARNINGS from PASS. A high score can still require revision, for example a structural duplicate.

Production feasibility and optional replay scores are returned separately and do not veto a sound premise. Presenter blocking is an execution warning. Production risk screening is labeled TEXT_RISK_SCREEN_ONLY; a high score does not verify AI-video execution. Speech can be brief and useful; explanatory/audio-dependent causality, long lines and lip-sync load are flagged. Recreated-problem payoffs need a broken resolution; “again” alone earns no payoff. Unrelated reveals and negated/quoted quality claims supply no positive causal evidence.

Duplicate screening compares opening rule/silhouette family, ordered strategy progression and ending physical function against two curated frozen production references. Catalog entries carry exact hashes and source paths; reproducibility is tested. Character/object names are excluded, so a chair-to-stool rename remains HIGH risk. A familiar mechanism alone is insufficient for rejection. Exact source self-comparison is excluded. No match means **NO_MATCH_IN_LIMITED_CORPUS**, never verified originality. Other historical winners and paraphrases beyond supported patterns still require editorial comparison.

Unsupported wording, implicit goals, unfamiliar mechanics and relationships outside the implemented patterns can be missed or misclassified. This is conservative source-plan screening, not semantic verification. Human review remains necessary; no visual adherence, audience success, render authorization or model capability is asserted.

## Deterministic examples

Full source plans, outputs, source hashes and evidence spans: [examples.json](examples.json).

| Concept | Provenance | Short-form result | Score | Causal beats |
| --- | --- | --- | ---: | ---: |
| Upside-Down Chair | Unchanged frozen real production prompt, existing WINNER label | PASS_WITH_WARNINGS | 94 | 6 |
| Different lid recurrence | Synthetic short fixture | PASS | 100 | 5 |
| Garden Guardian, compact adaptation | Synthetic new visual plan using the scary-costume/birds premise | PASS | 100 | 5 |
| Boogeyman's Exam, badly compressed | Synthetic failed 15s compression | REJECT | 18 | 0 |
| Busy repetitive motion | Synthetic weak control | REVISION_REQUIRED | 56 | 1 |
| Beautiful unclear opening | Synthetic weak control | REVISION_REQUIRED | 41 | 2 |
| Identical attempts | Synthetic weak control | REVISION_REQUIRED | 59 | 2 |
| Unrelated rules | Synthetic weak control | REVISION_REQUIRED | 52 | 3 |
| Chair renamed stool | Synthetic derivative of frozen source | REVISION_REQUIRED | 94 | 6 |

The unchanged chair source retains an escalation plateau warning despite its historical winner label. The Garden short is an explicitly rewritten test plan, not a claim that the old 60-second plan already passes. The unchanged original Garden long-form result remains STORY_REVISION_REQUIRED, 0/100. Original Boogeyman remains PASS_WITH_WARNINGS, 91/100; its separate bad short compression scores 18. The same unchanged long source can also expose both engines independently, with the short engine refusing to treat 60 seconds as a ready 15-second plan.

## Verification

- New Python tests: **73 passed**, 1 warning.
- Focused new/creative/CPQ/accepted-long-form tests: **181 passed**, 37 warnings.
- Full non-media ML regression: **1,784 passed, 36 failed, 2 skipped**, 3,030 warnings. All 36 failure IDs exactly match the accepted prior verification; no additional failures.
- Disabled-short-engine control: the same **36 failures** reproduce, 253 warnings.
- Angular: **82 passed**, three files, including accepted long-form and workflow tests.
- Java: **5 passed**, ShortFormReportTest (3) and accepted StoryPremiseReportTest (2). Projection/dispatch only, no PDF/media rendering.
- Ruff F checks pass for the new engine/tests. An expanded check also found three preexisting unused imports/variables in shared assessment/creative-role files; all three reproduce from HEAD. `git diff --check` passes.
- All **51** tracked golden files, accepted long-form verification artifacts and accepted engine source retain their pre-change SHA-256 values. Nine frozen IR report projections compare byte-for-byte with the new layer disabled; opted-in projection differs only by its added property.

[verification.json](verification.json) lists changed files, commands, exact summaries and baseline failure IDs. [immutable-before.json](immutable-before.json) records the hashes before implementation. Test output is stored alongside this document. An initial direct parse of the chair source was interrupted at the source's already-documented parser timeout; the compatibility test uses its frozen IR and independently assesses the unchanged text. The parser was not modified.

Python verification removes provider credentials, disables paid execution flags, denies outbound sockets/media subprocesses, protects original data/docs from test writes and uses disposable configuration copies. Image/video QA tests were excluded because they synthesize media. No external provider calls, paid evaluations, image/video/PDF generation or historical evidence mutation occurred.
