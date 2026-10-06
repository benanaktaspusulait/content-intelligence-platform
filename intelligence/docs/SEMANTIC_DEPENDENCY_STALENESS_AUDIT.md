# Semantic Dependency Staleness Audit

## Scope

Benchmark video: `07_luca_ball_spitting_crocodile_hd.mp4`

The persisted V5 row contained valid semantic evidence with `status=CACHE_HIT` and
`providerCallCount=0`. The semantic quality gate also recorded payoff and loop as resolved.

## First stale layer

The first incorrect layer was the local canonical fusion read model, not the VLM evidence:

- `ml-service/app/semantic_fusion.py` did not map semantic payoff `COMPLETED` to a resolved
  canonical payoff.
- It did not map semantic loop `CONSISTENT` to an available canonical loop.
- Coverage used canonical strength being non-`UNKNOWN` as a proxy for evidence availability.
- `backend/.../VideoService.ensureCanonicalAssessments` returned immediately whenever any
  `canonicalAssessments` object existed, and its availability check omitted `CACHE_HIT`.

This allowed a valid semantic cache result to coexist with an older dependent snapshot.

## Dependency path

The intended path is:

`persisted V5 + semantic evidence -> local semantic fusion -> coverage -> platform readiness -> video detail`

The fix keeps the path local after semantic evidence is available. It does not invoke a provider.

## Targeted audit result

Before recomputation, the target row showed semantic payoff `COMPLETED` and loop `consistent`,
but canonical payoff and loop were `UNKNOWN` and canonical coverage was `60%`. After local
recomputation, payoff and loop are both available and canonical coverage is `100%`.

The semantic observation `Child, Toy Alligator` remains an observation from the semantic model;
it is not promoted to a canonical Pompom character identity by this fix.
