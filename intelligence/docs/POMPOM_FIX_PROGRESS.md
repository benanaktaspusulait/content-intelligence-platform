# Pompom audit corrections — implementation progress

Implementation is authorized and runs in the primary checkout on `master`, without a new worktree. The audit remains historical. This document distinguishes implemented code from full journey acceptance; it does not mark the 17-item backlog complete.

| Item | Current implementation | Outstanding acceptance / work |
|---|---|---|
| B01 | Folder versions are unverified candidates; explicit ORIGINAL/RECONSTRUCTED resolution is append-only and video-hash bound. Resolver reads disk bytes, rejects multiple exact sidecars, supports Unicode. Render lineage takes precedence. | Complete rendered-version/newer-version fixture and UI resolution/reopen evidence. |
| B02 | Paginated canonical choices, explicit variant/reason confirmation, cross-video rejection, clearing variant when original selected; variant included in row DTO/audit. | Real UI preview → exact variant → commit → reopen verification. |
| B03 | Existing local patch remains available. | Persistent bounded provider repair session, best candidate acceptance/cancellation/independent validation orchestration remains unimplemented. |
| B04 | Revision updates URL; parent source path/version preserved; exact saved review/settings/QA restore through GET, mismatched edited source is stale. | More-than-200 historical records and video association on direct prompt route need completion. |
| B05 | Actual-only QA endpoint/UI; original fidelity NOT_EVALUATED while actual grounded experience can be assessed. | Saved actual-only QA reopen and complete clip/UI verification. |
| B06 | Manual edited-file import verifies file/hash/duration and same-video parent, preserves original, registers variant and separate artifact video for review. | End-to-end real edited file verification and original hash comparison. Operations remain honestly OPERATOR_REPORTED. |
| B07 | Existing queue/attempt protections preserved. | Exact parent video/variant → authorized regenerated attempt → artifact/performance lineage wiring remains unimplemented. |
| B08 | Scope/duration/model-filtered approved lesson retrieval; latest revocation excludes record, evidence IDs checked; requests re-resolve lessons and bind provenance; text critic receives lessons. | Repair/builder role integration and stronger audience-specific maturity/settings filtering. |
| B09 | Version-specific cache and active identity; expired RUNNING job becomes provider-outcome-unknown FAILED; blind retry prohibited. Prior fixtures fixed. | Provider/result reconciliation checkpoint recovery and UI presentation for ambiguous outcomes. |
| B10 | Frozen policy retained. | Versioned applicable-rule canonical admission projection and authorized queue positive fixture remain unimplemented. |
| B11 | Optional DeepSeek STORY / OpenAI BUILD_PROMPT and MINIMAL_REPAIR text role port/UI; schema/quote validation; disabled-by-default paid execution with configured model/prices and budget; drafts never self-approve. | Durable paid attempt reconciliation, bounded session integration (B03), full UI/mock acceptance. |
| B12 | UNKNOWN source dimensions/reasons/references visible; existing structured evidence form retained. | Full source quote/coverage diagnostics and grounded enrichment UI journey. |
| B13 | Train stub returns 501 rather than claiming trained artifact; insufficient rows 409; promotion 501 without changing champion; UI shows unavailable active training/promotion. | Dedicated promotion no-mutation transport fixture. B17 is separate. |
| B14 | Existing capabilities and role preflight are separate from live verification; no paid call made. | Explicit live-test budget/account scope required; live verification NOT DONE. |
| B15 | Configurable relative UI root, Unicode folders, empty folder persistence, consistent txt/md/json/yaml/yml scan/read contract. | Prompt move/alias reconciliation and more filesystem boundary fixtures. |
| B16 | Identical bytes/context replay preserved; changed platform/timezone explicitly rejected; batch URL reopen implemented. | correction_of export lineage, context display and safe corrected-value workflow. |
| B17 | Cold-start remains honestly active. | Real statistical train/eval/artifact/registry inference/rollback pipeline remains unimplemented; enough verified mature data is an external prerequisite. |

## Verification to date

- Backend first acceptance batch: 18 tests passed (5 import, 1 lineage, 12 analysis jobs). Later expanded suite also includes source-disk/Unicode, lesson revocation, duplicate context and empty workspace fixtures; record fresh results after completion.
- Frontend: 13 targeted tests passed, including paginated choices and saved exact review via GET; development build passed after optional roles were added.
- ML: 74 targeted tests passed, including actual-only fidelity/usability and creative role fixtures; no live provider calls.
- Browser: content 5 / prompt version 8 loaded its saved operational profile. Save revision changed URL to prompt version 9; reload retained version 9. All are disposable fixtures in isolated `pompom_workflow_local`, not production mutations.

Active local runtimes are owned ports 4215/8085/8015. Backend must be stopped before Maven recompiles target/classes. Existing production ports 4200/8080/8000 remain untouched.
