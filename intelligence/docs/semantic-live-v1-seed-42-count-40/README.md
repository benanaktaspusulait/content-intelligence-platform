# Controlled live semantic experiment V1

This additive experiment keeps the accepted semantic V1 path mock-only. Normal API/UI/CLI dispatch remains unchanged and defaults to `allowExternalGeneration=false`. Only the dedicated experiment CLI can opt into live transport. Import and stored-response replay do not construct a provider.

## Execution boundary

The selected capability profile is `deepseek-primary` from `intelligence/data/workflow/creative-provider-profiles-v3.json`: provider `deepseek`, model `deepseek-v4-pro`. The legacy `.env` story-model setting says `deepseek-chat`; it is not used to override the current explicit capability profile. Credentials are loaded through the existing `ml-service/.env` mechanism; no credentials are persisted.

One experiment, at most one provider completion request, 40 requested raw ideas, 64,000 output-token ceiling (including provider reasoning if billed within output), 90-second request timeout, no SDK retries, no fallback, and a $2 ceiling using a conservative configuration-price estimate. The general reconstruction profile's 4,000-token experiment limit is not changed; this separate semantic experiment explicitly records its larger bounded output allowance. Actual billing is reported only if supplied by the provider; a configured-price bound is not an actual charge.

The command defaults to a plan. Live execution requires both `--execute-live` and `--allow-external-generation`. An atomic `live-attempt` directory is claimed before transport construction. Existing attempts, including failures, cannot be executed again into that record. An interrupted attempt remains claimed. There is no scheduler, background generation, or retry loop.

## Prompt and downstream interpretation

`semantic-concept-prompt-v1.1` wraps the unchanged V1 system instructions and schema. Its versioned additions broaden causal directions, request varied object/trigger/progression/payoff/silhouette combinations, and add reset-to-start shoe caution alongside the two accepted historical references. The exact prompt, request, configured model and cast are stored before transport execution.

Stored-response replay uses the unchanged parser and normalization adapter, then the unchanged semantic orchestration for fingerprinting, naturalness, Beat Grammar, SHORT_FORM_ENGINE, Creative Shape, historical comparison, canonical ranking and production selection. No raw candidate is silently repaired. Malformed entries and duplicate identifiers remain in the evidence. The replay's inherited V1 MOCK ONLY labels and zero provider counters describe the accepted downstream implementation; the outer provider-metadata record is the authority for actual live transport usage and actual prompt version.

Diagnostics run after canonical analysis. They cannot feed scores or ranking. Every score below 60 receives failed dimensions, exact raw/validator evidence, canonical warnings, penalties and a diagnostic classification. `EVIDENCE_EXTRACTION_FAILURE` means a supplied rule produced no recognized SFE rule; it does not establish that the rule is good. Ambiguous content-versus-extraction failures stay `UNKNOWN`. Exact repeated consequences can support `CONTENT_FAILURE`; missing evidence supports `STRUCTURE_FAILURE`.

Opening audit keeps raw-opening naturalness separate from SFE's combined first beat. Loop recognition remains ambiguous where only an unverified provider suggestion/rewatch score exists. All canonical outcomes are retained.

`HUMAN_REVIEW_SET` includes canonical eligible ideas, scores at least 75, and strong-naturalness ideas with revision/rejection reasons. This observational set does not promote candidates into canonical ranking. Final display buckets are production candidate, human review, revision required, rejected, or malformed; canonical status is also retained independently.

Unmapped rules are marked `UNCLASSIFIED_CAUSAL_ENGINE` and kept for downstream inspection. No taxonomy is added. Shape comparison searches all 480 candidates from the frozen deterministic Creative Shape seed-42 pool, rather than only its nine finalists. Structured differences, nearest candidate and weighted distance are evidence of representation differences only. Unknown/default adapter dimensions may inflate distance; no automatically certified novelty or semantic-superiority claim is made.

## Evidence and verification

`protected-before.json` records 249 hashes, extending the prior protected history with the accepted semantic V1 implementation, fixtures, tests, evidence and provider profile. The final protected comparison is recorded separately. Only four new Python files implement this task; existing source files are not edited by this task.

Tests run through the existing offline harness: credentials stripped, outbound network blocked, data/docs protected, media subprocesses blocked. QA/video fixture synthesis is excluded as in prior accepted verification. Test logs and baseline failure-ID comparison are separate from live evidence.

The live record preserves request arguments, exact response text, provider usage, timestamps, immutable file hashes and downstream output. Replay is deterministic analysis of stored text; live model output is not claimed to be byte deterministic. No image/video/render or production-prompt operation is performed.

## Commands

From the repository root (plan only):

```sh
intelligence/ml-service/.venv/bin/python intelligence/scripts/run-semantic-live-experiment.py
```

The authorized live invocation is recorded in `live-execution.log`. Do not rerun it; the one experiment is intentionally bounded. For an existing record, replay uses `--replay /absolute/path/to/live-attempt --output /new/absolute/path` and cannot be combined with live flags.
