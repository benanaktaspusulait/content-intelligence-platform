# Post-Render Assessment and Insights

## Purpose

Post-render assessment is a deterministic summary of persisted render evidence and post-render rule outcomes. It is not a performance prediction and it never uses views, likes, reach, or follower data to assign a creative grade.

## Evidence contract

`render-evidence-v2` preserves the existing motion-v3 semantics. The extractor adds a separate payoff block. A payoff window is resolved only when the immutable render prompt snapshot contains one explicit, timestamped line marked as payoff, punchline, reveal, ending, resolution, or equivalent. Missing or conflicting declarations remain `NOT_AVAILABLE` or `AMBIGUOUS`; motion is never used to invent a payoff timestamp.

## Assessment

`post-render-assessment-v1` produces one immutable snapshot associated with each post-render evaluation. It contains an ordinal grade, evidence coverage percentage, human-readable verdict, strengths, concerns, evidence insights, and one recommended controlled experiment.

Grade order is deterministic. Blocker failures produce `F`; blocker service errors or low evidence coverage produce `INCOMPLETE`; critical failures produce `D`; review-required or warning failures produce `C`; minor failures produce `B`; a clean evaluated result produces `A`.

## Persistence and API

The assessment is stored in `post_render_assessments` with its own version and JSON snapshot. Existing evaluations are not rewritten. `GET /api/v1/post-render/evaluations/{id}` returns the assessment when one exists and continues to return raw rule results below it.

## UI

The render dashboard presents the assessment summary first, followed by strengths, concerns, insights, and the recommended experiment. Raw rule results remain available for auditability.

## Deliberate limits

The current extractor does not claim semantic story understanding, character identity, dialogue quality, or retention. Those remain unavailable until a versioned analyzer supplies explicit evidence. This prevents an attractive but unsupported grade from replacing an auditable incomplete result.
