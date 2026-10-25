# Long-form story premise engine v1

Adds `STORY_PREMISE_ENGINE` to the existing creative validation pipeline. It screens
concepts for active contradiction and a deliberate, costly change of goal. It does
not replace the canonical ruleset, source-fidelity checks, visual checks, or render
authorization. No provider or media runtime is used by this layer.

## Activation and compatibility

- Requested duration of 45 seconds or longer, or explicit `storyType` /
  `seriesType` / `narrativeMode` of `POMPOM_STORIES`, `POMPOM_STORY`, `LONG_FORM`,
  `LONG_FORM_STORY`, or `LONG_NARRATIVE`.
- Requested context takes precedence over a duration declaration in the text.
  Target configuration, metadata, and source timing are supported.
- The calibrated range is 45–75 seconds; other explicitly selected long-form
  durations receive a warning.
- Short-form calls return no new assessment field and retain existing scoring,
  gates, and serialization. Absent story mode does not change request binding.
- There is no migration, historical result rewrite, or frozen fixture update.

## Evidence and policy

The engine returns eleven structured checks: premise strength, driving goal,
role contradiction, hidden intent, moral choice, cost, trait repurposing, status
reversal, predictability, meaning-shift density, and payoff density. Separate
outputs provide duration suitability and the story-engine summary.

All supporting passages have exact source offsets and quotes. Recognized events
also have matched offsets, so a decision written before its opportunity cannot
establish the required chronological arc. Opportunities, decisions, and costs
must link to the driving actor and original goal/stake. An unrelated character's
decision or late new ability cannot fill those gaps. Restoring the original prize
removes the claimed lasting cost.

The moral-arc screen also needs textual support for an original selfish,
predatory, reward-seeking, or self-interested goal. Merely helping the same person
in a different way does not establish sacrifice of that goal.

The 100-point score is a **premise heuristic, separate from canonical scoring**.
Weights are 12/10/8/5/20/12/10/8/5/6/4 in the check order above. Choice and cost
are hard gates; missing either caps the score at 59. Passive misunderstanding
caps it at 39. Missing driving goal, unresolved dramatic question, deliberate
choice, or lasting cost requires story revision. Accidental transformation and
an explicitly early resolution also require revision. A passing long-form screen
needs at least 70 points and no hard-gate failure.

Hidden intent is a positive signal, not mandatory. Weak trait linkage, sparse
meaning changes, decorative guests, unclear visible choices, and long payoff gaps
are reported as warnings. Relationship, information, goal, moral-choice, meaning,
status, and consequence dimensions are exposed. Running, looking, chasing, and
repeated attempts earn no meaning-change credit. Payoff gaps longer than the
greater of 15 seconds or one quarter of the duration are flagged. Without a
complete, contiguous timecoded plan, payoff timing stays UNKNOWN.

This is conservative **English text-pattern screening**, not independent semantic
verification. Unsupported wording, pronouns, roles, and traits may require
editorial review. Early-solve risk is an editorial inference; it does not prove
what viewers will predict at second 15. Textual PASS never verifies visuals,
audience outcomes, official creative calibration, or permission to render.

## Integration and reports

- STORY candidate evaluation: `storyQuality.candidates[].assessment.storyPremiseEngine`.
  Long-form editorial preference favors an eligible active arc; the existing
  mandatory canonical gates still apply. STORY_REVIEW cannot recommend a
  premise-blocked candidate even if its canonical rows pass.
- Creative validity and optimization diagnostics: `storyPremiseEngine`.
- Workflow review: `storyPremiseEngine`, operator-report explanation, and an
  additive Family 8 creative blocker when revision is required.
- Quality validation: `pre_render_assessment.story_premise_engine`; failed
  premise screening blocks story/first-frame readiness without rewriting
  canonical scores or removing existing technical/evidence blockers.
- The existing quality and workflow UI displays the saved report, source
  evidence, and all three duration classifications. It performs no local grading.
- The three existing PDF export paths include the same textual report when
  present. PDF text projection was tested without rendering a document.
- Concept-only endpoint: `POST /api/v1/workflow/story-premise/evaluate`, accepting
  `{ "text": "...", "desiredDuration": 60, "storyType": "POMPOM_STORIES" }`.
  This endpoint never invokes canonical semantic evaluators or providers.

## Examples

[examples.json](examples.json) contains the complete actual deterministic outputs.
Its narratives are explicitly authored test fixtures illustrating the user's
archetypes, not reconstructed production validation results.

| Fixture | Premise score | Long-form result | Meaning changes |
| --- | ---: | --- | ---: |
| Garden Guardian | 0 | STORY_REVISION_REQUIRED | 0 |
| Boogeyman's Exam | 91 | PASS_WITH_WARNINGS | 6 |
| Predator becomes protector | 96 | PASS_WITH_WARNINGS | 6 |
| Thief becomes guard | 96 | PASS_WITH_WARNINGS | 6 |

Garden Guardian remains suitable for a 10–20s setup/reveal, while its 45–75s
classification requires revision. Its zero is a premise-screen score, not an
execution score. Boogeyman's Exam has an explicit original task, opportunity,
conscious rejection, exam loss, reused roar, and emotional status reversal. The
fixture still receives a payoff-spacing warning: the first relationship change
arrives too late. Strong premise does not conceal a pacing concern.

## Verification

See [verification.json](verification.json) for results, commands, the precise
existing failure list, the disabled-layer comparison, and changed files.

From `intelligence/ml-service`:

```sh
.venv/bin/python ../scripts/test-story-premise-offline.py
```

The runner strips provider keys, denies outbound sockets and media subprocesses,
uses disposable configuration copies, and protects original data/docs against
writes. It permits only the read-only Git revision lookup used by golden
provenance. Video/image-synthesizing QA tests are excluded.

New tests cover seven strong/weak archetypes, chronology, actor/goal linkage,
negation, sacrifice, early resolution, unrelated twists, payoff gaps, duration
activation, real report/workflow integration, and exact evidence offsets. The
real 15s report and all nine frozen short-form IR projections are byte-for-byte
identical with this layer enabled or disabled.

The broader suite is not green. Its existing failures also reproduce with the
premise layer disabled; the frozen results and unrelated parser/idea work were
left intact. UI tests and PDF text-projection tests pass. No image, video, or PDF
was rendered for verification.

## Files

Implementation: `ml-service/app/workflow/story_premise_engine.py`,
`assessment/pre_render_assessment.py`, `api/quality.py`, `workflow/api.py`,
`workflow/review.py`, `workflow/story_quality.py`, `workflow/creative_validity.py`,
`workflow/creative_roles.py`, and `workflow/optimization_loop.py`.

Reports: `frontend/src/app/pages/story-premise-report.component.ts`, the existing
quality-validator component/template and post-family workflow component, and
`backend/.../quality/QualityReportPdfService.java`.

Tests: the two `test_story_premise_*.py` modules, `fixtures/story_premise_cases.json`,
the new report component spec, `StoryPremiseReportTest.java`, and the offline test
runner. Pre-existing uncommitted parser and idea-batch changes were preserved.
