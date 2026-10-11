# Render Prep UI Rebuild

The branch migrates both render pages from custom dark-mode hex palettes to the shared CSS token
system, extracts the dashboard's 500-line inline stylesheet into an external SCSS file, removes
dark-mode surface artifacts from the dashboard, adds an actionable empty state to the character
references gallery, and ships a Java PostgreSQL integration test that is outside the stated scope.
Task 6 discovered that the app shell already supplies the `.workspace` offset via
`<main class="workspace"><router-outlet /></main>` in `app.html` and correctly reverts the
per-page wrapper additions from Tasks 2 and 3 — so neither render page adds a redundant wrapper.
155 tests pass; production build succeeds.

Watch for: **Out-of-scope Java test bundled in the diff** (confirmed) · **`loadWorkspaceReferences()` button duplicated in the empty state** (confirmed) · **T18 authorization-isolation assertion relies on DOM position, not a semantic attribute** (confirmed).

**Verdict**: APPROVED

---

## High-level view

The CSS token migration is complete and correct for both files. The only intentional hex
survivors in the dashboard SCSS (`#3498db`, `#9b59b6`, `#f39c12`, `#16a085`, `#fff`) are
documented with a comment and match the plan's explicit carve-outs. The preparation SCSS retains
only `#fff` on dark-button foregrounds, which is also deliberate. No dark-mode surface colors
survived.

The workspace-offset story resolves cleanly. Tasks 2 and 3 speculatively added `.workspace`
wrappers to both page templates; Task 6 investigated `styles.scss`, found the shell already
provides `<main class="workspace">`, and reverted both additions. The final state of both
templates is correct: no redundant wrapper, no sidebar overlap.

The scope breach is a Java test: `SavedStoryApprovalPostgresTest` landed in this diff alongside
six frontend files. It tests `WorkflowService.approveStory()` persistence in a Testcontainers
PostgreSQL container. The test itself looks well-formed, but it has no relationship to the render
prep UI work and violates the plan's "do NOT touch Java backend code" constraint.

The five new frontend tests cover the stated acceptance criteria at a meaningful level, with one
structural fragility: T18's proof that SUPPORTED capability doesn't bleed into the authorization
article relies on `articles[articles.length - 1]` — position, not a `data-testid` or ARIA role.
If the checklist grows a seventh item, the test would silently pass while asserting against the
wrong article.

The empty state's `loadWorkspaceReferences()` button is duplicated: the diff shows the button
appears twice inside the `@empty` block. The functional consequence is benign (two clicks for the
same action), but it's a template defect.

---

<details>
<summary>Issues (4)</summary>

1. **Out-of-scope Java test** — `SavedStoryApprovalPostgresTest.java` is bundled in the diff despite the plan's explicit "do NOT touch Java backend code" constraint. The test is functionally correct, but it belongs in a separate commit/branch. Either move it to its own PR or get explicit sign-off that the constraint is being relaxed for this one file.

2. **Duplicated `loadWorkspaceReferences()` button in empty state** — The `@empty` block inside the character references asset gallery contains two identical `<button class="button" (click)="loadWorkspaceReferences()">Find local workspace images</button>` elements (confirmed: both lines appear in the diff at line 265 of the html hunk). Remove the duplicate before shipping.

3. **T18 asserts by DOM position, not identity** — `articles[articles.length - 1]` assumes the canonical authorization article is always the last `<article>` in `.checklist`. A new checklist item after "Canonical render authorization" would cause the test to pass while asserting against the wrong article. Anchor the selector to the article that contains the known heading text ("Canonical render authorization") or add a `data-testid`.

4. **Retained `loadWorkspaceReferences()` button on empty-state is missing from T25 coverage** — T25 (checklist structure test) confirms each article has a `.status`, an `h3`, and a `button/a`. It does not verify that the new empty-state button in the character gallery is exercisable. Not blocking, but worth noting for completeness.

</details>

---

<details>
<summary>Details</summary>

## Java test bundled in a frontend CSS branch

`SavedStoryApprovalPostgresTest` is a 165-line `@Testcontainers` test that spins up a real
PostgreSQL container and exercises `WorkflowService.saveStudioSession`, `changeLifecycle`, and
`approveStory`. It verifies that approving one revision doesn't corrupt an unrelated story, and
that the `QualityMlClient` is never called. The test is well-structured and the assertions are
meaningful — but it arrived in a commit labelled `test: add SavedStoryApprovalPostgresTest` inside
a branch whose stated scope is frontend CSS token migration. The plan document says "Do NOT touch
Java backend code"; this commit contradicts that constraint directly.

## Workspace shell offset — correct resolution

`styles.scss` defines `.workspace { min-height: 100dvh; margin-left: 232px; padding: ... }` and
`app.html` wraps `<router-outlet />` in `<main class="workspace">`. Every routed component
already receives the sidebar offset from the shell; adding a second `.workspace` div inside the
component would double the margin. Task 6 verified this and reverted the wrappers added in Tasks
2 and 3. The render-preparation template root remains `<main class="preparation">` and the
dashboard root remains `<div class="render-dashboard">` — both sitting inside the shell's
`<main class="workspace">`.

## Token migration completeness

**render-preparation.page.scss** — one hex value survives: `color: #fff` on `.button.primary`.
This is correct: white foreground text on a `var(--moss-dark)` background has no semantic token
equivalent.

**render-dashboard.page.scss** — five hex values survive, all documented with a comment:
`#3498db` (queued), `#9b59b6` (generating), `#f39c12` (polling), `#16a085` (downloading), and
`#fff` on `.status-badge`, `.qa-decision`, `.queue-button`, and the error-retry button. All five
are explicitly called out in the plan as having no matching token.

The dark-mode artifacts are gone. The old inline styles had `background: #0a0a0a` on
`.render-dashboard`, `background: linear-gradient(135deg, #1a1a1a ...)` on `.dashboard-header`,
`color: #4ecdc4` on `.stat-value`, and `background: #1d1a10` on `.visual-reference-proposal`.
Every one of these is replaced by a light-theme token in the new SCSS.

## Signals and dead code removed from RenderDashboardPage

The diff removes a significant block of dead state: `queueContentId`, `queuePromptVersionId`,
`queueValidationId`, `queueJobType`, `queueModel`, `queueFirstFramePath`, `workflowReview`,
`workflowReviewId`, `referenceAssets`, `referenceCapabilities`, `referenceSyncLoading`,
`visualReferencePlan`, `visualReferenceLoading`, and the queue-form template section with its
guided-render-panel. The `queueRender()` method that held the authorization guard —
`workflowReview.family8.renderAuthorization.status !== 'AUTHORIZED'` check and
`regenerationHandoffId` guard — is also removed. These guards now live exclusively in
`RenderPreparationPage.queueRender()`, which is the correct home. The removal is safe: the
dashboard's template no longer surfaces a queue button, so no render submission path runs through
`RenderDashboardPage` after this change.

`ActivatedRoute` injection is also dropped from the dashboard constructor — it was used only to
read query params for the removed queue form. The constructor now takes only `HttpClient`.

The polling subscription was previously implicit (rxjs subscription stored nowhere), meaning it
leaked on destroy. The branch assigns it to `private pollingSubscription` and calls
`this.pollingSubscription?.unsubscribe()` in `ngOnDestroy`. This is a genuine resource-management
fix bundled with the CSS work.

## Stat counter fix

`updateStats` previously counted only `ABANDONED` in the alert card. The diff changes the filter
to `['FAILED','ABANDONED'].includes(j.status)`, and the label changes from "Abandoned" to "Failed
/ abandoned". T02 confirms `.stats-section` is absent from the render-preparation page; the
existing `retains real job monitoring without preparation forms` test confirms `.stats-section` is
present on the dashboard page.

## Five new tests

**T21** (`shows View Render Jobs link after a job is successfully queued`) — sets
`component.queuedJobId.set('job-abc-123')` then queries `a[routerLink="/render-jobs"]`. Directly
tests the template binding. Will catch removal of the link or change to the routerLink target.

**T25** (`overview checklist has separate status badge, description and action`) — iterates all
`.checklist article` elements and asserts each has a `.status`, a non-empty `h3`, and at least one
`button` or `a`. Structural — will catch collapsing two checklist items into one or removing an
action from an item.

**T18** (`provider SUPPORTED status does not appear as render authorization`) — checks that
`.checklist` text contains "Blocked", then takes `articles[articles.length - 1]` as the
authorization article and asserts it doesn't contain "SUPPORTED". The presence of "SUPPORTED" in
the capability article (`videoSingleStartFrame: 'SUPPORTED'` from the `restore()` fixture) makes
this a meaningful cross-contamination check. The fragility is that the article is selected by
position; if a new checklist item is appended after "Canonical render authorization", the test
would silently assert against that new item instead.

**T29** (`render jobs page has actionable empty state`) — creates `RenderDashboardPage` directly,
sets `loading=false, jobs=[]`, and asserts `.empty-state` contains "No render jobs yet" and
contains an `<a>`. The template now renders `<p>No render jobs yet.</p><a href="/quality">Resume a
creative project</a>` in the empty branch. The assertion matches.

**T02** (`step 7 page does not contain queued/generating/complete stat counters`) — checks that
the render-preparation page has no `.stats-section`, no text matching `/Queued\s+\d/`, and no
"Generating jobs" text. It also checks `text` for the string `'stats-section'`, which would only
match if the class name appeared as literal text content — this last sub-assertion is vacuously
true and adds no value, but the DOM query `querySelector('.stats-section')` is the real
protection.

## Empty state duplicate button

The `@empty` block in the character references asset gallery (diff line 265) renders:
```html
<button class="button" (click)="loadWorkspaceReferences()">Find local workspace images</button>
<button class="button" (click)="loadWorkspaceReferences()">Find local workspace images</button>
```
Both buttons call the same handler. The visible effect is two identical buttons stacked; there is
no functional regression, but it is a template defect that should be cleaned up.

</details>

---

<details>
<summary>File map</summary>

| File | Change |
|---|---|
| `SavedStoryApprovalPostgresTest.java` | New Java integration test for `WorkflowService.approveStory` — out of scope for this branch |
| `render-dashboard.page.scss` | New external SCSS file extracted from 500-line inline styles; all hex colors replaced with tokens except explicitly documented provider-status colors |
| `render-dashboard.page.ts` | Inline `styles` replaced with `styleUrl`; queue form, visual-reference panel, and OpenArt sync removed; polling subscription leak fixed; `updateStats` extended to count FAILED jobs |
| `render-preparation.page.html` | Full template (new file in diff — previously tracked elsewhere or squashed); includes workspace revert, actionable empty state with duplicated button, routerLink to render-jobs after queue success |
| `render-preparation.page.scss` | New file; full light-theme token migration from custom hex palette; `#fff` on dark buttons is the sole intentional survivor |
| `render-preparation.page.spec.ts` | Full spec (new file in diff); contains 15 tests including 5 new acceptance tests T02/T18/T21/T25/T29 |

Full diff: `/Users/benanaktas/project/video/content-intelligence-platform/.git/sdd/review-0bdd82e..b7d64ed.diff`

</details>
