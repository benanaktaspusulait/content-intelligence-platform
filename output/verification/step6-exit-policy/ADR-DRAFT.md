# DRAFT — Step 6 text acceptance, evidence preparation and rule exceptions

Status: **PROPOSED / NOT APPROVED / NOT ACTIVE**. This document creates no operator authority and grants no production permission.

## Decisions requiring an architecture owner

1. Define whether the short-tier ATTEMPT_001 minimum is an unwaivable render precondition or admits a documented exception. Present architecture says BLOCKER must be fixed before render consideration; rule minimum3 is explicit, and no rule-specific waiver policy exists. The master architecture sketches manual override with audit trail but does not define eligible rules, authority or precedence over later hard queue checks. Default remains blocked. This decision must not change the count or score.
2. Define whether an operator may record TEXT_ACCEPTED_RENDER_BLOCKED when no supported text repair is established but a policy violation remains. This must mean acceptance of the exact text for further evidence work, not successful Step6 production clearance or a waiver of ATTEMPT_001. Alternatively keep text acceptance blocked and authorize only evidence preparation; the existing Step7 reference/upload route already supports this separation.
3. Define the operator role and scope for production-risk acknowledgement. PRODUCIBILITY_003 explicitly calls for human review rather than an outright render block, but the general zero-CRITICAL render architecture and current admission checks are stricter. An acknowledgement must be auditable without silently satisfying either gate.

## Proposed typed metadata contract

After approval, use governed metadata for every rule, independent of content identity:

- resolutionType: TEXT_REPAIR_REQUIRED | EVIDENCE_REQUIRED | PRODUCTION_RISK_REVIEW | POLICY_EXCEPTION_REQUIRED | CONFIRMED_HARD_BLOCKER | EVALUATOR_DEFECT
- failureBasis: measured source defect | missing evidence | verified visual failure | technical error | unresolved policy
- requiredEvidence, earliestResolutionStage, blocksTextAcceptance, blocksEvidenceCollection, blocksRender
- operatorAction: NONE | ACKNOWLEDGE_RISK | REQUEST_POLICY_EXCEPTION
- exceptionPolicy: FORBIDDEN | EXPLICIT_POLICY_ID_REQUIRED; missing policy fails closed

A resolution classification never overwrites canonical outcome, severity, score, evidence or historic analysis. Missing visual evidence and verified negative evidence must classify differently using existing failureBasis/missingEvidence/evidenceSource fields. An UNKNOWN classification cannot become an approval default. Evidence acquisition cannot satisfy a confirmed hard failure.

Version this eligibility policy independently (`step6-resolution-v2`, proposed). Parser/evaluator corrections require a new immutable ruleset (proposed1.11); no frozen1.10 edit. Metadata additions should be reviewed with rule governance, not inferred from hardcoded Mimi-specific IDs or severity alone.

## Proposed four operations

A. TEXT_ACCEPTANCE: explicit NO_TEXT_REPAIR_JUSTIFIED attests only that no supported text change is justified. Reject when an actionable text defect or evaluator/technical uncertainty prevents that conclusion. Whether unresolved policy violations permit this record is Decision2 above; until decided, preserve current rejection.

B. EVIDENCE_PREPARATION: inspect/associate verified references and prepare or upload start-frame evidence using existing scoped services, exact prompt/settings binding and their own validation. Merely entering Step7 requires no paid consent and grants no render authorization. Paid first-frame generation retains its separate consent/budget/eligibility checks.

C. RISK_REVIEW: accept/reject a specific production risk only under the approved authority and policy. This cannot waive hard rules. Any exception must name a governing exception policy; there is no implicit override.

D. RENDER_AUTHORIZATION: canonical F8 plus queue admission remain authoritative; exact prompt/settings/reference/start-frame bindings, semantic/independent/visual evidence and unexpired validation must pass. Neither A, B nor C can synthesize AUTHORIZED or clear counts.

## Proposed authoritative decision response

One server-side policy evaluator should supply the UI and command handlers with policyVersion, analysisId, rulesetVersion, promptVersionId, promptSha256, bindingHash, findings and allowedActions with reasons. GET responses are advisory; POST recomputes against latest saved evidence, current ruleset and authenticated operator identity. A newer analysis/ruleset/settings invalidates eligibility.

If an approved action is recorded, persist exact unresolved findings, accepted risk IDs, pending evidence, applicable policy, operator acknowledgement, timestamp and authenticated provenance. Never trust an operator-supplied classification or role. Do not conflate risk acknowledgement with a passed rule.

## Acceptance required before activation

The twelve requested cases must be tested against this approved contract, including negative transitions, stale bindings, missing confirmation, genuine hard blockers, scoped evidence collection and eventual F8 admission. Existing tests prove today's gates; they do not prove this unimplemented proposal.
