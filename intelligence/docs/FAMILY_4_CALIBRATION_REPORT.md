# FAMILY 4 — Mechanic / Fake Resolution / Recurrence / Payoff Calibration Report

**Golden Set:** `POMPOM_GOLDEN_V1`  
**Ruleset:** `1.7`  
**Status:** **FAMILY 4 COMPLETE — APPROVED / FROZEN**  
**Next family:** Family 5 has not started.

## Scope lock

This calibration covers only:

- `CENTRAL_MECHANIC`
- `MECHANIC_INTERACTION`
- `FAKE_RESOLUTION`
- `RECURRENCE`
- `PAYOFF`
- `PAYOFF_RELATION` (`SAME_RULE`)

No new parser, Rule Engine, scoring subsystem, performance signal, policy threshold, or Family 5+ behavior was added.

## Gold Truth lock

The independently reviewed Gold Truth remains the authority for the nine frozen prompts:

| Asset | Central mechanic | Fake resolution | Recurrence | Payoff | Same-rule relation |
|---|---|---|---|---|---|
| Sticky Ball | `STICKY_DEFORMATION` | `PRESENT` | `PRESENT` | `STRONG` | `SAME_RULE` |
| Ball-Multiplying Crocodile | `QUANTITY_MULTIPLICATION` | `PRESENT` | `PRESENT` | `STRONG` | `SAME_RULE` |
| Upside-Down Chair | `AUTONOMOUS_CHAIR_INVERSION` | `PRESENT` | `PRESENT` | `STRONG` | `SAME_RULE` |
| Lamp | `OBSERVATION_DEPENDENT_LIGHT` | `PRESENT` | `PRESENT` | `MODERATE` | `SAME_RULE` |
| Snack Box | `CHANGING_CONTENTS` | `PRESENT` | `PRESENT` | `MODERATE` | `SAME_RULE` |
| Box Cat | `STUBBORN_RETURN_ANIMAL_CLAIM` | `PRESENT` | `PRESENT` | `MODERATE` | `SAME_RULE` |
| Spot Cat | `REPEATED_TARGET_CLAIM` | `PRESENT` | `PRESENT` | `MODERATE` | `SAME_RULE` |
| Sneaky Door | `AUTONOMOUS_SNEAKY_DOOR` | `PRESENT` | `PRESENT` | `STRONG` | `SAME_RULE` |
| Island Journal | `NOT_ESTABLISHED` | `NOT_ESTABLISHED` | `NOT_ESTABLISHED` | `NOT_ESTABLISHED` | `NOT_ESTABLISHED` |

`NOT_ESTABLISHED` is a reviewed negative structural result, not `UNKNOWN`. Island Journal’s narrative twist is not treated as a mechanic payoff.

## Comparator correction

`extract_dimension_values` now keeps one projection path for baseline and current snapshots:

1. When usable `videoPlanIR` exists, Family 4 values are recomputed through the existing `mechanic_payoff_evidence` canonical evidence helper.
2. `CENTRAL_MECHANIC` uses normalized `mechanic_family`; it never exposes raw physical-rule prose or the status token `ESTABLISHED`.
3. Canonical non-null values take precedence over stale serialized `dimensionValues`.
4. Stored `dimensionValues` are used only for fields unavailable in the canonical projection.
5. A snapshot without `videoPlanIR` returns stored values unchanged. This preserves parser-timeout values and keeps known parser issues classified as `UNCHANGED_KNOWN_ISSUE` rather than inventing `NOT_ESTABLISHED` evidence.

This fixes the baseline/current representation mismatch without changing Family 1–3 semantics or introducing a second evidence system.

## Family 4 invariants

The implementation and focused tests preserve these boundaries:

- Temporary normal state is not mechanic inconsistency.
- Fake resolution is not final resolution and is not itself the payoff.
- Recurrence means the established mechanic returns or reasserts.
- A new consequence does not create a new mechanic.
- Same-rule payoff may use a different visual consequence.
- A random final twist is not a same-rule payoff.
- Narrative twist is not mechanic payoff.
- `NOT_ESTABLISHED` is distinct from `UNKNOWN`.

## Golden gate result

Generated artifacts:

- `intelligence/data/golden/pompom-golden-v1/reports/family4-current/golden-regression-report.json`
- `intelligence/data/golden/pompom-golden-v1/reports/family4-current/golden-regression-report.md`

| Metric | Result |
|---|---:|
| Assets | 9 |
| Golden assertions | 296 |
| Semantic passed | 53 |
| Semantic failed | 5 |
| Improved from baseline | 26 |
| Unchanged known issues | 53 |
| Gold review required | 60 |
| New semantic regressions | **0** |
| Expected policy changes | 4 |
| Unexpected policy regressions | **0** |
| Release gate | **PASS** |

`GOLD_REVIEW_REQUIRED` remains an intentional classification for non-high-confidence truth disagreements; it is not converted into a semantic regression and no policy threshold was loosened. The known `upside-chair-01` parser timeout remains unavailable on both sides and is unchanged.

## Validation

- Family 4 comparator and mechanic/payoff tests: **19 passed**.
- Full ML service suite: **482 passed**; no test failures.
- ML representation contract: **2 passed**.
- Backend representation tests (`QualityReportPdfServiceTest`, `QualityReportDtoTest`): **passed**.
- Frontend representation spec (`state-share.spec.ts`): **4 passed**.
- Frontend production build: **completed** with existing bundle/style budget warnings.

The full frontend suite was also executed. Its unrelated pre-existing failures cover an analysis URL expectation (`?force=false`) and Video Detail DOM/polling fixtures; the Family 4/frontend representation spec passed independently. No frontend or backend implementation was changed for Family 4.

## Completion decision

Family 4 is ready to remain **APPROVED / FROZEN**. The comparator correction is narrowly scoped, the Golden release gate is green, and work must stop here until a separate Family 5 scope is explicitly opened.
