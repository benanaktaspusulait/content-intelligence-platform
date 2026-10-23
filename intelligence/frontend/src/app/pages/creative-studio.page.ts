import { CanonicalFindingsComponent } from './canonical-findings.component';
import { CommonModule } from '@angular/common';
import {
  AfterViewChecked,
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  ViewChild,
  inject,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

type Stage =
  'IDEA' | 'STORY' | 'PROMPT' | 'PRODUCTION_REVIEW' | 'ANALYSIS' | 'REPAIR' | 'RENDER' | 'VIDEO_QA';
type InputMode = 'IDEA' | 'DETAILED_STORY' | 'EXISTING_PROMPT';
type Journey = 'RESUME' | 'SAVED' | 'NEW';
interface StoryCandidate {
  candidateId: string;
  title: string;
  text: string;
  structuralEvidence?: any;
  preflight?: any;
  assessment?: any;
}
interface CharacterOption {
  id: string;
  name: string;
  raw?: any;
}
interface WorkspaceOption {
  folderPath: string;
  creativeName: string;
}
interface SavedStoryRecord {
  recordId: string;
  createdAt?: string;
  updatedAt?: string;
  idea?: string;
  title?: string;
  result: any;
  sourceType?: string;
  revisionId?: string;
  sourceRecordId?: string;
  candidateCount?: number;
  workspacePath?: string;
  contentId?: string;
  sourceContext?: any;
  lifecycleStatus?: string;
}

@Component({
  selector: 'app-creative-studio',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, CanonicalFindingsComponent],
  template: ` <main class="studio" aria-labelledby="studio-title">
    <header class="studio-header">
      <div>
        <span class="eyebrow">CREATIVE PRODUCTION STUDIO</span>
        <h1 id="studio-title">Create New Video</h1>
        <p>Turn an idea into a validated production prompt, step by step.</p>
      </div>
      <button class="button button--secondary" type="button" (click)="startExistingPrompt()">
        I Have an Existing Prompt
      </button>
    </header>
    <section class="journey-map" aria-label="Guided creative workflow">
      <h2>Your creative workflow</h2>
      <ol>
        <li>
          <button type="button" (click)="stage = 'IDEA'">IDEA</button> ·
          {{ ideaDraftRevision ? 'Saved revision ' + ideaDraftRevision : 'Not saved' }}
        </li>
        <li>
          <button
            type="button"
            [disabled]="!ideaDraftId || draftDirty"
            (click)="stage = 'IDEA'; openExploration()"
          >
            VISUAL EXPLORATION
          </button>
          ·
          {{
            visualDirection
              ? 'Direction selected; not production approved'
              : 'Upload or explore an image'
          }}
        </li>
        <li>
          <button type="button" [disabled]="!candidates.length" (click)="stage = 'STORY'">
            STORY
          </button>
          ·
          {{ storyRecordId ? 'Saved; edits create a new revision' : 'Develop from the saved IDEA' }}
        </li>
        <li>
          <button
            type="button"
            [disabled]="!storyRecordId"
            (click)="stage = 'STORY'; loadStoryValidation()"
          >
            CREATIVE VALIDATION
          </button>
          · {{ storyProductionDecision }}
        </li>
        <li>
          FIRST-FRAME APPROVAL ·
          {{
            promptVersionId
              ? 'Use the exact saved prompt in Visual Preparation'
              : 'Pending saved motion prompt; required by official image gates'
          }}
        </li>
        <li>
          <button type="button" [disabled]="!canVisit('PROMPT')" (click)="goTo('PROMPT')">
            MOTION PROMPT
          </button>
          ·
          {{
            promptVersionId
              ? 'Saved; validate this exact version in Production Review'
              : builderRecordId
                ? 'Draft ready to inspect and save'
                : 'Pending story approval'
          }}
        </li>
        <li>
          <a *ngIf="promptVersionId" [href]="detailUrl">PRE-RENDER VALIDATION / FIRST FRAME</a
          ><span *ngIf="!promptVersionId">PRE-RENDER VALIDATION · Pending saved prompt</span>
        </li>
        <li>
          RENDER · BLOCKED until the exact production screen reports GO_TO_RENDER and you explicitly
          authorize payment
        </li>
        <li>
          VIDEO QC · Pending a real render; inspect it in
          <a routerLink="/render-jobs">Render Jobs</a> /
          <a routerLink="/videos">Video Library</a> before editorial approval
        </li>
      </ol>
    </section>
    <details>
      <summary>Detailed production stages</summary>
      <nav class="studio-steps" aria-label="Production stages">
        <button
          *ngFor="let item of stages; let i = index"
          type="button"
          [class.is-active]="stage === item.key"
          [class.is-complete]="stageStatus(item.key).includes('Complete')"
          [class.is-draft-available]="stageStatus(item.key).includes('Draft available')"
          [class.is-needs-review]="stageStatus(item.key).includes('Needs review')"
          [class.is-locked]="stageStatus(item.key).includes('Locked')"
          [attr.aria-label]="
            item.label +
            ': ' +
            stageStatus(item.key) +
            (canVisit(item.key) ? '' : ' — ' + stageAvailabilityReason(item.key))
          "
          [attr.title]="canVisit(item.key) ? null : stageAvailabilityReason(item.key)"
          [disabled]="item.key !== stage && !canVisit(item.key)"
          (click)="goTo(item.key)"
        >
          <span>{{ i + 1 }}</span
          ><strong>{{ item.label }}</strong
          ><small>{{ stageStatus(item.key) }}</small>
        </button>
      </nav>
    </details>
    <section class="studio-layout">
      <section class="studio-main" [attr.aria-busy]="busy">
        <div *ngIf="error" class="studio-error" role="alert">
          <strong>Action could not be completed</strong>
          <p>{{ error }}</p>
          <details *ngIf="technicalError">
            <summary>Technical details</summary>
            <code>{{ technicalError }}</code>
          </details>
          <button type="button" (click)="dismissError()">Dismiss</button>
        </div>
        <ng-container [ngSwitch]="stage">
          <section *ngSwitchCase="'IDEA'" class="stage-panel">
            <span class="stage-kicker">1 · IDEA</span>
            <section
              *ngIf="ideaCandidates.length || ideaBatches.length"
              aria-label="Saved IDEA candidates"
              class="stage-panel"
            >
              <h2>Compare IDEA candidates</h2>
              <p *ngIf="noIdeaApproved" role="status">
                {{ ideaOverallStatus }} — no eligible IDEA is selected. Missing evaluation is not creative rejection.
              </p>
              <p>
                Each concept retains its original receipt. Selection stays in IDEA; STORY requires a
                separate later action.
              </p>
              <article *ngFor="let batch of ideaBatches">
                <small
                  >Request {{ batch.requestId }} · {{ batch.status }} ·
                  {{ batch.candidateCount }} saved</small
                >
                <button
                  *ngIf="batch.recoverable"
                  type="button"
                  [disabled]="ideaCandidateBusy"
                  (click)="recoverIdeaBatch(batch)"
                >
                  Recover saved response (no provider call)
                </button>
                <p *ngIf="batch.error">{{ batch.error }}</p>
              </article>
              <section aria-label="Independent IDEA semantic review" class="stage-panel">
                <h3>Independent semantic creative review</h3>
                <p>Review the three saved sources in one request. No new content is generated. Text judgments do not verify images, rendered motion or audience performance.</p>
                <button type="button" (click)="prepareIdeaReview()" [disabled]="ideaCandidates.length !== 3 || ideaReviewBusy">Review 3 Existing IDEAs</button>
                <p *ngIf="ideaReviewError" role="alert">{{ ideaReviewError }}</p>
                <p *ngIf="ideaReviewResult" role="status">{{ ideaReviewResult.status }} · receipt {{ ideaReviewResult.receiptId }}</p>
                <div *ngIf="ideaReviewQuote as quote">
                  <p>Reviewer: {{ quote.provider }} · {{ quote.model }} · {{ quote.policyVersion }}.<br>
                    Maximum one provider call, no retries. Estimated upper bound: {{ quote.estimatedUpperBoundUsd | number:'1.4-6' }} USD.<br>{{ quote.estimateBasis }}</p>
                  <strong *ngIf="quote.fixture">ISOLATED TEST FIXTURE — zero provider calls; synthetic results cannot approve production candidates.</strong>
                  <p *ngFor="let source of quote.sources">{{ source.candidateId }} · source SHA256 {{ source.sourcePayloadSha256 }} · original evaluation {{ source.originalEvaluationRevision }}</p>
                  <label>Maximum review budget (USD)
                    <input type="number" min="0" step="0.01" aria-label="Maximum IDEA review budget USD" [(ngModel)]="ideaReviewBudget" (ngModelChange)="ideaReviewConsent = false">
                  </label>
                  <label><input type="checkbox" aria-label="Authorize one IDEA semantic review" [(ngModel)]="ideaReviewConsent">
                    {{ quote.fixture ? 'Simulate owner authorization in this isolated test environment' : 'I authorize exactly one semantic review of these sources with the disclosed reviewer and my maximum budget' }}
                  </label>
                  <button type="button" (click)="runIdeaReview()" [disabled]="ideaReviewBusy || !ideaReviewConsent || ideaReviewBudget <= 0 || ideaReviewBudget < quote.estimatedUpperBoundUsd || (!quote.configured && !quote.fixture)">
                    {{ quote.fixture ? 'Run isolated review fixture' : 'Run authorized semantic review' }}
                  </button>
                </div>
                <details *ngIf="ideaReviewHistory.length"><summary>Semantic review receipt and result history</summary><pre>{{ ideaReviewHistory | json }}</pre></details>
              </section>
              <div class="story-candidates">
                <article
                  *ngFor="let candidate of ideaCandidates"
                  class="stage-panel"
                  [attr.data-idea-candidate]="candidate.candidateId"
                >
                  <h3>{{ candidate.payload.title }}</h3>
                  <strong
                    >Decision: {{ candidate.state }} · Evaluation:
                    {{ candidate.evaluation?.status || 'NOT_EVALUATED' }}</strong
                  >
                  <dl>
                    <dt>Concept</dt>
                    <dd>{{ candidate.payload.concept }}</dd>
                    <dt>Everyday goal</dt>
                    <dd>
                      {{
                        candidate.payload.everydayGoal || 'UNKNOWN — explicit goal evidence absent'
                      }}
                    </dd>
                    <dt>Frame-zero problem</dt>
                    <dd>
                      {{ candidate.payload.frameZeroProblem || candidate.payload.firstStaticFrame }}
                    </dd>
                    <dt>Impossible rule</dt>
                    <dd>
                      {{
                        candidate.payload.impossibleRule ||
                          'UNKNOWN — explicit rule evidence absent'
                      }}
                    </dd>
                    <dt>Proposed progression</dt>
                    <dd>
                      {{ candidate.payload.proposedProgression || candidate.payload.discovery }}
                    </dd>
                    <dt>Final payoff</dt>
                    <dd>{{ candidate.payload.payoff }}</dd>
                  </dl>
                  <details>
                    <summary>Inspect evaluation and evidence gaps</summary>
                    <p *ngIf="candidate.evaluation?.summary as summary">
                      Mandatory creative checks: {{ summary.mandatoryChecks }} ·
                      Creative PASS: {{ summary.creativeOutcomes?.PASS }} · FAIL: {{ summary.creativeOutcomes?.FAIL }} ·
                      UNKNOWN: {{ summary.creativeOutcomes?.UNKNOWN }} · N/A: {{ summary.creativeOutcomes?.NOT_APPLICABLE }}<br>
                      Exact source bindings verified: {{ summary.sourceBindingPasses }}/{{ summary.sourceBindingChecksExecuted }} (source presence only; not creative PASS).<br>
                      Existing evaluator invocations: {{ summary.canonicalEvaluatorsInvoked }} · completed diagnostics: {{ summary.canonicalEvaluatorsCompleted }} ·
                      unable to complete: {{ summary.canonicalChecksUnableToComplete }}.<br>
                      Source IDEA revision {{ candidate.evaluation.sourceIdeaRevision }} · Evaluation revision {{ candidate.evaluation.revision }} ·
                      {{ candidate.evaluation.policyVersion }} · canonical rules {{ candidate.evaluation.canonicalRulesetVersion }}.
                    </p>
                    <article *ngFor="let gate of candidate.evaluation?.gates" class="idea-rule-evidence" [attr.data-idea-gate]="gate.gate">
                      <strong>{{ gate.gate }} · {{ gate.status === 'NOT_APPLICABLE' ? 'N/A' : gate.status }}</strong>
                      <p>{{ gate.reason }}</p>
                      <small>{{ gate.policy }} · {{ gate.category }} · {{ gate.reasonCode }}<br>
                        Evaluator {{ gate.evaluator?.registered ? 'registered' : 'not registered' }} ·
                        {{ gate.evaluator?.invoked ? 'invoked' : 'not invoked' }} ·
                        {{ gate.evaluator?.completed ? 'diagnostic completed' : 'judgment not completed' }} · Provider calls: {{ gate.evaluator?.providerCalls || 0 }}</small>
                      <p *ngIf="gate.sourceCheck">Source binding: {{ gate.sourceCheck.status }} — {{ gate.sourceCheck.reason }}</p>
                      <p *ngIf="!gate.sourceSpans?.length">{{ gate.evidence || 'No source evidence' }}</p>
                      <blockquote *ngFor="let span of gate.sourceSpans">
                        <small>{{ span.path }} [{{ span.start }}, {{ span.end }}) · {{ span.offsetUnit }}</small><br>{{ span.quote }}
                      </blockquote>
                      <p *ngIf="gate.applicability">{{ gate.applicability.stage }} · {{ gate.applicability.profile }} · {{ gate.applicability.status }}.
                        Canonical contract: {{ gate.applicability.declaredRuleStage }}.</p>
                      <p *ngFor="let requirement of gate.laterStageEvidence">Later-stage evidence: {{ requirement }}</p>
                      <p *ngIf="gate.visualEvidenceRequirement">Visual evidence: {{ gate.visualEvidenceRequirement }}</p>
                      <details *ngIf="gate.concerns?.length"><summary>Heuristic concerns — not confirmed creative failures</summary>
                        <p *ngFor="let concern of gate.concerns">{{ concern.kind }} · {{ concern.riskTag }} · {{ concern.reason }}</p>
                      </details>
                    </article>
                    <p>{{ candidate.evaluation?.smallestSupportedNextStep }}</p>
                    <details><summary>Original immutable IDEA source</summary><pre>{{ candidate.payload | json }}</pre></details>
                  </details>
                  <details *ngIf="candidate.semanticReview || candidate.fixtureSemanticReview">
                    <summary>Independent semantic findings{{ candidate.fixtureSemanticReview && !candidate.semanticReview ? ' — ISOLATED FIXTURE ONLY' : '' }}</summary>
                    <ng-container *ngIf="candidate.semanticReview || candidate.fixtureSemanticReview as review">
                      <p>{{ review.semanticStatus }} · reviewer {{ review.reviewerModel }} · {{ review.reviewerVersion }} · receipt {{ review.receiptId }} · original evaluation {{ review.originalEvaluationRevision }}</p>
                      <strong *ngIf="review.fixture">SYNTHETIC TEST FINDINGS — not production judgments or approval</strong>
                      <strong *ngIf="review.stale">STALE SOURCE — this review is not applicable</strong>
                      <p>Text-supported judgments only. Actual visual legibility, silhouette comparison and motion execution remain unverified. Decision: {{ candidate.state }}. Eligible: {{ eligibleIdeaCandidate(candidate) }}.</p>
                      <article *ngFor="let judgment of review.judgments" [attr.data-idea-semantic-dimension]="judgment.dimension">
                        <strong>{{ judgment.dimension }} · {{ judgment.ruleId }} · {{ judgment.verdict }}</strong>
                        <p>{{ judgment.reason }} · Confidence: {{ judgment.confidence }}</p>
                        <blockquote *ngFor="let span of judgment.sourceSpans"><small>{{ span.path }} [{{ span.start }}, {{ span.end }})</small><br>{{ span.quote }}</blockquote>
                      </article>
                    </ng-container>
                  </details>
                  <small
                    >Candidate {{ candidate.candidateId }} · index {{ candidate.candidateIndex }} ·
                    draft {{ candidate.draftId }} · revision {{ candidate.sourceIdeaRevision }} ·
                    request {{ candidate.requestId }} · provider request
                    {{ candidate.providerRequestId }} · receipt {{ candidate.receiptId }}</small
                  >
                  <div class="stage-actions">
                    <button
                      type="button"
                      [disabled]="ideaCandidateBusy"
                      (click)="evaluateIdeaCandidate(candidate)"
                    >
                      Evaluate IDEA
                    </button>
                    <button
                      type="button"
                      [disabled]="ideaCandidateBusy || !eligibleIdeaCandidate(candidate)"
                      (click)="decideIdeaCandidate(candidate, 'SELECTED')"
                    >
                      {{ candidate.state === 'SELECTED' ? 'Selected IDEA' : 'Select IDEA' }}
                    </button>
                    <button
                      type="button"
                      [disabled]="ideaCandidateBusy || candidate.state === 'REJECTED'"
                      (click)="decideIdeaCandidate(candidate, 'REJECTED')"
                    >
                      Reject IDEA
                    </button>
                  </div>
                </article>
              </div>
            </section>

            <h2>What would you like to create?</h2>
            <details>
              <summary>Generate one idea</summary>
              <p>
                One text-only concept. No STORY, image or render is generated. Model: gpt-6-sol;
                estimated conservative ceiling $0.10.
              </p>
              <label class="field"
                >Creative brief<textarea [(ngModel)]="ideaBrief"></textarea></label
              ><label
                >Idea cost ceiling (USD)<input
                  type="number"
                  [(ngModel)]="ideaBudget"
                  min="0"
                  step="0.01" /></label
              ><label
                ><input type="checkbox" [(ngModel)]="ideaConsent" /> Authorize one paid IDEA
                generation</label
              ><button
                type="button"
                [disabled]="
                  busy || !ideaConsent || !ideaBrief.trim() || !mainCharacterId || ideaBudget <= 0
                "
                (click)="generateOneIdea()"
              >
                Generate One IDEA
              </button>
              <p>
                Select a canonical character below first. Existing saved work is never overwritten.
              </p>
              <article *ngIf="generatedIdea">
                <h3>{{ generatedIdea.title }}</h3>
                <pre>{{ generatedIdea | json }}</pre>
                <button type="button" (click)="useGeneratedIdea()">
                  Use this idea as a new draft
                </button>
              </article>
            </details>
            <p class="stage-intro">
              Choose one path. Reusing saved work never makes a provider call.
            </p>
            <section
              *ngIf="resumeAvailable && activeJourney !== 'NEW'"
              class="resume-panel"
              aria-label="Continue existing work"
            >
              <div>
                <span class="eyebrow">CONTINUE YOUR WORK</span><strong>{{ resumeHeadline }}</strong
                ><small>{{ resumeDescription }}</small
                ><small *ngIf="savedStoriesLoading" role="status"
                  >Verifying saved project records…</small
                ><small *ngIf="savedIndexLoadFailed" role="alert"
                  >Saved project records could not be verified. Refresh before continuing.</small
                >
              </div>
              <div class="resume-actions">
                <button
                  *ngIf="activeSavedStory && !savedApprovalVerified(activeSavedStory)"
                  class="button button--primary"
                  type="button"
                  [disabled]="!savedIndexesReady"
                  (click)="reviewSavedStory()"
                >
                  Review Story →</button
                ><button
                  *ngIf="savedPromptVersionVerified || (!storyRecordId && promptVersionId)"
                  class="button button--primary"
                  type="button"
                  [disabled]="!savedIndexesReady"
                  (click)="continueQualityAnalysis()"
                >
                  Continue to Production Review →</button
                ><button
                  *ngIf="
                    !savedPromptVersionVerified &&
                    (!storyRecordId || savedIndexesReady) &&
                    !promptVersionId &&
                    (builderRecordId || draftPrompt)
                  "
                  class="button button--secondary"
                  type="button"
                  [disabled]="savedIndexLoadFailed"
                  (click)="openSavedPrompt()"
                >
                  Open Saved Prompt →</button
                ><button
                  *ngIf="
                    !promptVersionId &&
                    !builderRecordId &&
                    !draftPrompt &&
                    approvalRecordId &&
                    !canonicalSavedPrompt
                  "
                  class="button button--primary"
                  type="button"
                  [disabled]="!savedIndexesReady"
                  (click)="continueApprovedStory()"
                >
                  Continue to Prompt →</button
                ><button
                  *ngIf="
                    !promptVersionId && !builderRecordId && !draftPrompt && canonicalSavedPrompt
                  "
                  class="button button--secondary"
                  type="button"
                  [disabled]="!savedIndexesReady"
                  (click)="openCanonicalSavedPrompt()"
                >
                  Open Saved Prompt →
                </button>
              </div>
            </section>

            <section
              class="journey-section"
              [class.library-empty]="!allSavedProjectCount"
              aria-labelledby="existing-content-title"
            >
              <div class="section-heading">
                <div>
                  <span class="eyebrow">SAVED WORK</span>
                  <h3 id="existing-content-title">Saved Projects</h3>
                  <p>Open, resume and manage saved work without another provider call.</p>
                </div>
                <span *ngIf="!savedStoriesLoading && allSavedProjectCount" class="section-count"
                  >{{ filteredSavedStories.length + filteredIdeaDrafts.length }} shown</span
                >
              </div>
              <div *ngIf="allSavedProjectCount" class="draft-library-toolbar">
                <input
                  type="search"
                  [(ngModel)]="savedStoryQuery"
                  placeholder="Search saved projects"
                  aria-label="Search saved projects"
                /><select [(ngModel)]="savedStoryFilter" aria-label="Filter saved projects">
                  <option value="ALL">All statuses</option>
                  <option value="DRAFT">Drafts</option>
                  <option value="IN_REVIEW">In review</option>
                  <option value="APPROVED">Approved</option>
                  <option value="ARCHIVED">Archived</option></select
                ><select [(ngModel)]="savedStorySort" aria-label="Sort saved projects">
                  <option value="UPDATED">Last updated</option>
                  <option value="NEWEST">Newest first</option>
                </select>
              </div>
              <div *ngIf="savedStoriesLoading" class="saved-story-empty">
                Loading saved projects…
              </div>
              <div
                *ngIf="!savedStoriesLoading && !savedIndexLoadFailed && filteredSavedStories.length"
                class="draft-library"
                role="table"
                aria-label="Saved projects"
              >
                <div class="draft-library-row draft-library-header" role="row">
                  <span>Project</span><span>Status</span><span>Checkpoint</span
                  ><span>Last updated</span><span>Actions</span>
                </div>
                <article
                  *ngFor="let story of filteredSavedStories"
                  class="draft-library-row"
                  [class.is-selected]="story.recordId === storyRecordId"
                  role="row"
                >
                  <div>
                    <strong
                      [title]="storyTitle(story)"
                      [attr.aria-label]="storyTitle(story) + ', ' + storySessionLabel(story)"
                      >{{ storyTitle(story) }}</strong
                    ><small
                      >{{ storySessionLabel(story) }} ·
                      {{ storyCandidates(story).length }} candidate{{
                        storyCandidates(story).length === 1 ? '' : 's'
                      }}</small
                    >
                  </div>
                  <span
                    class="lifecycle-badge"
                    [class.lifecycle-badge--approved]="savedLifecycle(story) === 'APPROVED'"
                    [class.lifecycle-badge--archived]="savedLifecycle(story) === 'ARCHIVED'"
                    >{{ savedLifecycleLabel(story) }}</span
                  ><span>{{ savedCheckpoint(story) }}</span
                  ><time>{{ storyDate(story) }}</time>
                  <div class="draft-library-actions">
                    <button
                      class="button button--primary"
                      type="button"
                      [disabled]="savedStoriesLoading || savedIndexLoadFailed"
                      (click)="openSavedProject(story)"
                    >
                      {{ savedPrimaryAction(story) }}</button
                    ><button
                      class="button button--secondary"
                      type="button"
                      [disabled]="savedStoriesLoading || savedIndexLoadFailed"
                      (click)="duplicateSavedStory(story)"
                    >
                      Duplicate</button
                    ><button
                      class="button button--secondary"
                      type="button"
                      [disabled]="savedStoriesLoading || savedIndexLoadFailed"
                      (click)="toggleSavedMenu(story.recordId)"
                    >
                      More
                    </button>
                    <div *ngIf="savedMenuRecordId === story.recordId" class="saved-actions-menu">
                      <button type="button" (click)="renameSavedStory(story)">Rename</button
                      ><button
                        type="button"
                        *ngIf="savedLifecycle(story) !== 'ARCHIVED'"
                        (click)="archiveSavedStory(story)"
                      >
                        Archive</button
                      ><button
                        type="button"
                        *ngIf="savedLifecycle(story) === 'ARCHIVED'"
                        (click)="restoreSavedStory(story)"
                      >
                        Restore</button
                      ><button
                        type="button"
                        *ngIf="canDeleteSavedStory(story)"
                        (click)="deleteSavedStory(story)"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </article>
              </div>
              <div
                *ngIf="!savedStoriesLoading && !savedIndexLoadFailed && !allSavedProjectCount"
                class="saved-story-empty"
              >
                <strong>No saved projects yet</strong>
                <p>
                  Your saved stories and production workflows will appear here. Start with an idea,
                  a detailed story or an existing production prompt.
                </p>
                <button
                  *ngIf="!newStoryOpen"
                  type="button"
                  class="button button--secondary"
                  (click)="selectJourney('NEW')"
                >
                  Start a new draft
                </button>
              </div>
              <div
                *ngIf="
                  !savedStoriesLoading &&
                  !savedIndexLoadFailed &&
                  allSavedProjectCount &&
                  !filteredSavedStories.length &&
                  !filteredIdeaDrafts.length
                "
                class="saved-story-empty"
              >
                No saved projects match these filters.<button
                  type="button"
                  class="button button--secondary"
                  (click)="clearSavedFilters()"
                >
                  Clear Filters
                </button>
              </div>
              <div
                *ngIf="!savedStoriesLoading && !savedIndexLoadFailed && filteredIdeaDrafts.length"
                class="idea-draft-list"
              >
                <article *ngFor="let draft of filteredIdeaDrafts" class="idea-draft-row">
                  <div>
                    <strong>{{ draft.state.title || 'Untitled draft' }}</strong
                    ><small
                      >{{ draftModeLabel(draft.state.inputMode) }} ·
                      {{
                        draft.checkpoint === 'IDEA'
                          ? 'Idea'
                          : draft.checkpoint === 'STORY'
                            ? 'Story review'
                            : 'Production review'
                      }}</small
                    >
                  </div>
                  <span class="lifecycle-badge">{{
                    draft.checkpoint === 'IDEA' ? 'Draft' : 'Needs review'
                  }}</span
                  ><time>{{ draft.updatedAt | date: 'short' }}</time
                  ><button
                    type="button"
                    class="button button--secondary"
                    [disabled]="draftLoading || draftSaving"
                    (click)="openIdeaDraft(draft)"
                  >
                    Open draft →
                  </button>
                </article>
              </div>
              <p *ngIf="savedIndexLoadFailed" class="library-message" role="alert">
                Saved projects could not be loaded or verified.<button
                  type="button"
                  class="button button--secondary"
                  (click)="retrySavedProjects()"
                >
                  Retry
                </button>
              </p>
              <p
                *ngIf="savedLibraryMessage && !savedIndexLoadFailed"
                class="library-message"
                role="status"
              >
                {{ savedLibraryMessage }}
              </p>
            </section>

            <section class="journey-section create-section" aria-labelledby="new-content-title">
              <div class="section-heading">
                <div>
                  <span class="eyebrow">CREATE SOMETHING NEW</span>
                  <h3 id="new-content-title">Start a new draft</h3>
                  <p>Start with an idea, your story or a production prompt. Saving is free.</p>
                </div>
                <button
                  *ngIf="!newStoryOpen || activeJourney !== 'NEW'"
                  class="button button--primary"
                  type="button"
                  [disabled]="draftSaving"
                  (click)="startNewDraft()"
                >
                  Create New Draft →
                </button>
              </div>
              <div *ngIf="activeJourney === 'NEW' && newStoryOpen" class="new-story-form">
                <div class="new-story-form-header">
                  <strong>{{
                    ideaDraftRevision
                      ? draftDirty
                        ? 'Saved draft · unsaved changes'
                        : 'Saved draft'
                      : 'New unsaved draft'
                  }}</strong
                  ><button
                    class="button button--secondary"
                    type="button"
                    (click)="collapseNewStory()"
                  >
                    Close draft
                  </button>
                </div>
                <small class="draft-origin">{{
                  newDraftSnapshot
                    ? 'Restored from your unsaved draft.'
                    : 'This draft is separate from every saved story.'
                }}</small>
                <div class="mode-picker" role="radiogroup" aria-label="What do you already have?">
                  <label
                    *ngFor="let option of inputModes"
                    [class.is-selected]="inputMode === option.value"
                    ><input
                      type="radio"
                      name="inputMode"
                      [value]="option.value"
                      [(ngModel)]="inputMode"
                      (change)="onModeChange()"
                    /><strong>{{ option.label }}</strong
                    ><small>{{ option.help }}</small></label
                  >
                </div>
                <div
                  *ngIf="inputMode === 'IDEA' || generationDialogOpen"
                  class="story-generation-controls"
                >
                  <label class="field"
                    >Generation Strategy<select
                      [(ngModel)]="storyMode"
                      (ngModelChange)="onStoryModeChange()"
                    >
                      <option value="EXPLORE_DIFFERENT_STORIES">Explore Different Stories</option>
                      <option value="IMPROVE_EXISTING_STORY">
                        Improve My Existing Story
                      </option></select
                    ><small>{{
                      storyMode === 'IMPROVE_EXISTING_STORY'
                        ? 'Refine the supplied story while preserving only the constraints you choose.'
                        : 'Explore different narrative directions from the supplied idea.'
                    }}</small></label
                  >
                  <fieldset
                    class="freedom-fieldset"
                    *ngIf="storyMode === 'IMPROVE_EXISTING_STORY' || inputMode === 'DETAILED_STORY'"
                  >
                    <legend>Creative Freedom</legend>
                    <small
                      >Choose what the refinement must preserve. These settings are sent with the
                      request.</small
                    ><label *ngFor="let option of freedomOptions"
                      ><input
                        type="checkbox"
                        [value]="option.value"
                        [checked]="lockedRequirements.includes(option.value)"
                        (change)="toggleLockedRequirement(option.value)"
                      /><span>{{ option.label }}</span></label
                    >
                  </fieldset>
                </div>
                <label class="field field-wide"
                  >{{
                    inputMode === 'DETAILED_STORY'
                      ? 'Detailed Story'
                      : inputMode === 'EXISTING_PROMPT'
                        ? 'Production Prompt'
                        : 'Idea'
                  }}<textarea
                    [(ngModel)]="sourceText"
                    rows="5"
                    [placeholder]="
                      inputMode === 'IDEA'
                        ? 'Describe a concept you would like to explore.'
                        : inputMode === 'DETAILED_STORY'
                          ? 'Enter your complete story, with its action and ending.'
                          : 'Paste your production prompt for review.'
                    "
                  ></textarea>
                </label>
                <div
                  *ngIf="inputMode === 'IDEA' && ideaLooksDetailed"
                  class="mode-suggestion"
                  role="status"
                >
                  <strong>This looks like a detailed story.</strong
                  ><span>Your current text will stay unchanged.</span
                  ><button type="button" (click)="useDetailedStoryMode()">
                    Use Detailed Story mode
                  </button>
                </div>
                <div class="field-grid">
                  <label class="field"
                    >Video Title<input
                      [(ngModel)]="title"
                      (ngModelChange)="persist()"
                      placeholder="Optional project title" /></label
                  ><label class="field"
                    >Main Character<select
                      [(ngModel)]="mainCharacterId"
                      (ngModelChange)="persist()"
                    >
                      <option value="">Select a registered character</option>
                      <option *ngFor="let character of characters" [value]="character.id">
                        {{ character.name }}
                      </option></select
                    ><small>{{ characterGuidance }}</small
                    ><small *ngIf="characterError" role="alert">{{ characterError }}</small
                    ><button
                      *ngIf="suggestedCharacter && !mainCharacterId"
                      type="button"
                      (click)="chooseSuggestedCharacter()"
                    >
                      Use {{ suggestedCharacter.name }} from catalog
                    </button></label
                  ><label class="field"
                    >Content Profile<select [(ngModel)]="profile" (ngModelChange)="persist()">
                      <option value="AUTO">Auto / Recommend</option>
                      <option value="ABSURD_PHYSICS">Absurd Physics</option>
                      <option value="CURIOSITY_ADVENTURE">Curiosity &amp; Discovery</option>
                      <option value="EDUCATIONAL">Educational</option></select
                    ><small *ngIf="profile === 'AUTO'"
                      >Recommendation pending; no profile is confirmed.</small
                    ></label
                  >
                  <details class="field workspace-settings">
                    <summary>Advanced Settings / Destination</summary>
                    <div class="workspace-destination">
                      <label for="workspace-select">Workspace</label
                      ><select
                        id="workspace-select"
                        [(ngModel)]="workspacePath"
                        [disabled]="ideaDraftRevision > 0"
                        (ngModelChange)="persist()"
                      >
                        <option value="">Default workspace will be created on first save</option>
                        <option
                          *ngFor="let workspace of workspaces"
                          [value]="workspace.folderPath"
                          [title]="workspace.folderPath"
                        >
                          {{ workspace.creativeName }}
                        </option></select
                      ><small *ngIf="workspaceLoading" role="status">Loading workspaces…</small
                      ><small *ngIf="workspaceError" role="alert"
                        >{{ workspaceError }}
                        <button type="button" (click)="loadWorkspaces()">Retry</button></small
                      ><button
                        *ngIf="!workspaceLoading"
                        type="button"
                        class="button button--secondary"
                        (click)="createWorkspace()"
                      >
                        Create additional workspace</button
                      ><small *ngIf="workspacePath"
                        >{{ ideaDraftRevision ? 'Saved destination:' : 'Selected destination:' }}
                        {{ selectedWorkspaceName }}</small
                      >
                    </div>
                  </details>
                  <label class="field"
                    >Target Duration<select
                      [(ngModel)]="durationPreset"
                      (change)="applyDurationPreset()"
                    >
                      <option *ngFor="let preset of durationPresets" [value]="preset.value">
                        {{ preset.label }}
                      </option>
                      <option value="CUSTOM">Custom duration</option>
                    </select></label
                  ><label *ngIf="durationPreset === 'CUSTOM'" class="field"
                    >Custom Duration (seconds)<input
                      type="number"
                      min="1"
                      max="60"
                      [(ngModel)]="duration"
                      (ngModelChange)="persist()" /></label
                  ><label class="field"
                    >Aspect Ratio<select [(ngModel)]="aspectRatio" (ngModelChange)="persist()">
                      <option>9:16</option>
                      <option>16:9</option>
                      <option>1:1</option>
                    </select></label
                  ><label class="field"
                    >{{ inputMode === 'IDEA' ? 'IDEA Provider' : 'Story Provider'
                    }}<select
                      [ngModel]="generationProvider"
                      [disabled]="inputMode === 'IDEA'"
                      (ngModelChange)="storyProvider = $event; cancelStoryGeneration(); persist()"
                    >
                      <option value="DEEPSEEK">DeepSeek</option>
                      <option value="OPENAI">OpenAI · GPT-6 Sol</option>
                    </select></label
                  ><label *ngIf="inputMode === 'IDEA' || generationDialogOpen" class="field"
                    ><span>{{
                      inputMode === 'IDEA'
                        ? 'IDEA Candidate Count (exactly 3)'
                        : 'Story Candidate Count'
                    }}</span
                    ><select
                      [ngModel]="inputMode === 'IDEA' ? 3 : candidateCount"
                      [disabled]="inputMode === 'IDEA'"
                      (ngModelChange)="candidateCount = $event; persist()"
                    >
                      <option [ngValue]="1">1</option>
                      <option [ngValue]="2">2</option>
                      <option [ngValue]="3">3</option>
                    </select></label
                  >
                </div>
                <section
                  class="field field-wide preference-picker"
                  aria-label="Creative Preferences"
                >
                  <div class="preference-picker-header">
                    <span>Creative Preferences</span
                    ><small>Optional guidance for the selected strategy.</small>
                  </div>
                  <div
                    class="preference-trigger"
                    role="combobox"
                    aria-controls="creative-preference-list"
                    tabindex="0"
                    [attr.aria-expanded]="preferencesOpen"
                    aria-haspopup="listbox"
                    (click)="togglePreferences()"
                    (keydown.enter)="togglePreferences()"
                    (keydown.space)="togglePreferences(); $event.preventDefault()"
                    (keydown.escape)="closePreferences()"
                  >
                    <span *ngIf="!preferences.length" class="preference-placeholder"
                      >Search and select preferences</span
                    ><span *ngIf="preferences.length" class="preference-chips"
                      ><span *ngFor="let preference of preferences" class="preference-chip"
                        >{{ preference
                        }}<button
                          type="button"
                          aria-label="Remove preference {{ preference }}"
                          (click)="removePreference(preference); $event.stopPropagation()"
                        >
                          ×
                        </button></span
                      ></span
                    ><span class="preference-chevron">⌄</span>
                  </div>
                  <div
                    *ngIf="preferencesOpen"
                    id="creative-preference-list"
                    class="preference-menu"
                    [class.is-above]="preferencePlacement === 'above'"
                    role="listbox"
                    aria-multiselectable="true"
                  >
                    <input
                      #preferenceSearch
                      type="search"
                      [(ngModel)]="preferenceQuery"
                      (click)="$event.stopPropagation()"
                      placeholder="Search preferences…"
                      aria-label="Search creative preferences"
                    /><button
                      *ngFor="let preference of filteredPreferences"
                      type="button"
                      class="preference-option"
                      role="option"
                      [attr.aria-selected]="preferences.includes(preference)"
                      [class.is-selected]="preferences.includes(preference)"
                      (click)="togglePreference(preference)"
                      (keydown.enter)="togglePreference(preference)"
                      (keydown.space)="togglePreference(preference); $event.preventDefault()"
                    >
                      <span class="preference-check">{{
                        preferences.includes(preference) ? '✓' : ''
                      }}</span
                      >{{ preference }}</button
                    ><small *ngIf="!filteredPreferences.length">No matching preferences.</small>
                  </div>
                  <small>Preferences are guidance, not universal rules.</small>
                </section>
                <div *ngIf="mismatchMessage" class="mismatch" role="status">
                  <strong>Possible title mismatch</strong>
                  <p>{{ mismatchMessage }}</p>
                  <button type="button" (click)="title = suggestedTitle; mismatchMessage = ''">
                    Update Title</button
                  ><button type="button" (click)="mismatchMessage = ''">Keep My Title</button>
                </div>
                <label class="field"
                  >Supported text model<select [ngModel]="storyModel" disabled>
                    <option [value]="storyModel">
                      {{ storyModel || 'Not configured' }}
                    </option></select
                  ><small
                    >Model is bound to the selected provider configuration. No fallback.</small
                  ></label
                ><label class="field"
                  >Video generator<select [(ngModel)]="targetGenerator" (ngModelChange)="persist()">
                    <option value="SEEDANCE_2_5">Seedance 2.5 Draft</option>
                    <option value="SEEDANCE_2_0_MINI">Seedance 2.0 Mini</option></select
                  ><small
                    >Actual duration and format support is checked in Production Review.</small
                  ></label
                ><label *ngIf="inputMode === 'IDEA'" class="field"
                  >First-frame description<textarea
                    [(ngModel)]="firstFrameDescription"
                    (ngModelChange)="persist()"
                    placeholder="Describe the exact static opening; save it with the IDEA. Structured saved ideas can use their original firstStaticFrame."
                  ></textarea>
                </label>
                <div class="stage-actions idea-actions">
                  <button
                    class="button button--secondary"
                    type="button"
                    [disabled]="draftSaving || draftLoading || busy || !idea.trim()"
                    (click)="saveIdeaDraft()"
                  >
                    {{ draftSaving ? 'Saving…' : 'Save Draft' }}</button
                  ><button
                    *ngIf="inputMode === 'IDEA'"
                    class="button button--secondary"
                    type="button"
                    (click)="openExploration()"
                    [disabled]="
                      !ideaDraftId || draftDirty || draftSaving || busy || explorationBusy
                    "
                  >
                    Explore First Frame</button
                  ><button
                    *ngIf="inputMode === 'IDEA' && !generationDialogOpen"
                    class="button button--primary"
                    type="button"
                    [disabled]="draftSaving || busy || !idea.trim()"
                    (click)="prepareStoryGeneration()"
                  >
                    {{
                      inputMode !== 'IDEA' && storyMode === 'IMPROVE_EXISTING_STORY'
                        ? 'Refine Story →'
                        : 'Generate 3 IDEA Candidates →'
                    }}</button
                  ><button
                    *ngIf="inputMode === 'DETAILED_STORY' && !generationDialogOpen"
                    class="button button--primary"
                    type="button"
                    [disabled]="draftSaving || busy || !idea.trim()"
                    (click)="useManualStory()"
                  >
                    Save Story &amp; Continue →</button
                  ><button
                    *ngIf="inputMode === 'EXISTING_PROMPT'"
                    class="button button--primary"
                    type="button"
                    [disabled]="draftSaving || busy || !idea.trim()"
                    (click)="useExistingPrompt()"
                  >
                    Save Prompt &amp; Continue →</button
                  ><button
                    *ngIf="inputMode === 'DETAILED_STORY' && !generationDialogOpen"
                    class="button button--secondary"
                    type="button"
                    [disabled]="draftSaving || busy || !idea.trim()"
                    (click)="prepareStoryGeneration()"
                  >
                    Optional AI refinement
                  </button>
                </div>
                <section *ngIf="recoverableStoryResponse?.recoverable" class="provider-note">
                  <strong>Saved provider response available</strong>
                  <p>
                    Open the retained response for preview. This revalidates saved bytes only; it
                    does not call OpenAI or save a story revision.
                  </p>
                  <button
                    type="button"
                    class="button button--secondary"
                    [disabled]="busy"
                    (click)="previewRecoveredStory()"
                  >
                    Preview recovered response
                  </button>
                </section>
                <p class="draft-origin" role="status">{{ draftSaveMessage }}</p>
                <section
                  *ngIf="explorationOpen && inputMode === 'IDEA'"
                  class="exploration-panel"
                  aria-label="IDEA visual exploration"
                >
                  <button type="button" (click)="findLinkedStories()">
                    Open linked STORY / correction history
                  </button>
                  <div *ngFor="let story of linkedIdeaStories">
                    <button type="button" (click)="openSavedProject(story)">
                      {{ storyTitle(story) }} ·
                      {{ story.sourceRecordId ? 'Edited continuation' : 'Original saved story' }} ·
                      {{ story.createdAt | date: 'short' }} · {{ story.lifecycleStatus || 'DRAFT' }}
                    </button>
                  </div>
                  <h3>Visual Exploration</h3>
                  <strong>EXPLORATORY — NOT PRODUCTION APPROVED</strong>
                  <label class="field"
                    >Image source / provenance<input
                      [(ngModel)]="uploadSourceNote"
                      placeholder="Who supplied this image and where it came from"
                  /></label>
                  <label class="field"
                    >Upload an existing exploratory image (PNG / JPEG, up to 15 MB; no provider
                    cost)<input
                      type="file"
                      accept="image/png,image/jpeg"
                      [disabled]="explorationBusy || draftDirty || !uploadSourceNote.trim()"
                      (change)="uploadExploration($event)"
                  /></label>
                  <p *ngIf="visualDirection">
                    Selected visual direction:
                    {{ visualDirection.originalFilename || visualDirection.explorationId }}. This is
                    not an approved production first frame.
                  </p>
                  <div class="visual-versions">
                    <article *ngFor="let version of explorations">
                      <button type="button" (click)="selectedExplorationId = version.explorationId">
                        {{ version.originalFilename || version.explorationId }} · revision
                        {{ version.ideaRevision }} · {{ version.assetStatus || version.status
                        }}{{ version.selectedDirection ? ' · SELECTED DIRECTION' : '' }}</button
                      ><img
                        *ngIf="version.assetStatus === 'AVAILABLE'"
                        [src]="explorationImageUrl(version)"
                        style="width:100px"
                        alt="Exploratory version thumbnail"
                      />
                    </article>
                  </div>
                  <p>
                    IDEA revision {{ ideaDraftRevision }} · Hook potential is separate from story
                    potential. This image cannot approve a story, rendering or publishing.
                  </p>
                  <p *ngIf="draftDirty" role="alert">
                    Save the changed IDEA before exploring its new revision.
                  </p>
                  <label class="field"
                    >Verified canonical reference<select [(ngModel)]="explorationReferenceId">
                      <option value="">Select an approved reference</option>
                      <option *ngFor="let ref of explorationReferences" [value]="ref.id">
                        {{ ref.label || ref.id }}
                      </option>
                    </select></label
                  >
                  <p *ngIf="!explorationReferences.length">
                    No verified canonical reference is available. Add and verify one in Character
                    Lab.
                  </p>
                  <label class="field"
                    >Cost ceiling (USD)<input
                      type="number"
                      min="0.001"
                      max="5"
                      step="0.01"
                      [(ngModel)]="explorationBudget"
                  /></label>
                  <label
                    ><input type="checkbox" [(ngModel)]="explorationConsent" /> I authorize one
                    exploratory image.</label
                  >
                  <button
                    type="button"
                    class="button button--primary"
                    (click)="generateExploration()"
                    [disabled]="
                      explorationBusy ||
                      draftDirty ||
                      !explorationConsent ||
                      !explorationReferenceId ||
                      explorationBudget <= 0
                    "
                  >
                    {{
                      explorationBusy ? 'Generating one image…' : 'Generate One Exploratory Image'
                    }}
                  </button>
                  <p *ngIf="explorationError" role="alert">{{ explorationError }}</p>
                  <label *ngIf="explorations.length" class="field"
                    >Saved explorations<select [(ngModel)]="selectedExplorationId">
                      <option *ngFor="let item of explorations" [value]="item.explorationId">
                        Revision {{ item.ideaRevision }} · {{ item.status }}
                      </option>
                    </select></label
                  >
                  <article *ngIf="selectedExploration as item">
                    <strong>{{ item.label }}</strong>
                    <p *ngIf="item.sourceType === 'OPERATOR_UPLOAD'">
                      {{ item.originalFilename }} · {{ item.sourceNote }} · User-supplied image, not
                      an OpenAI generation.
                    </p>
                    <p>
                      Source IDEA revision {{ item.ideaRevision
                      }}{{ item.ideaRevision !== ideaDraftRevision ? ' — older revision' : '' }}
                    </p>
                    <p>{{ item.sourceFirstFrame }}</p>
                    <p>
                      {{ item.provider || 'Provider unknown' }} · Requested model:
                      {{ item.requestedModel || item.model || 'UNKNOWN' }} · Returned model:
                      {{ item.providerResponseMetadata?.returnedModel || 'NOT REPORTED' }} ·
                      Calculated cost:
                      {{
                        item.calculatedCostUsd == null ? 'UNKNOWN' : '$' + item.calculatedCostUsd
                      }}
                      <small>{{ item.costBasis }}</small>
                    </p>
                    <p *ngIf="item.assetStatus === 'UNAVAILABLE'" role="alert">
                      {{ item.assetError }}. Upload the replacement as a new version; the original
                      provider receipt is preserved.
                    </p>
                    <ng-container
                      *ngIf="
                        (item.status === 'GENERATED' || item.status === 'UPLOADED') &&
                        item.assetStatus !== 'UNAVAILABLE'
                      "
                      ><a [href]="explorationImageUrl(item)" target="_blank"
                        >Inspect original image</a
                      >
                      <div class="exploration-previews">
                        <figure>
                          <img
                            [src]="explorationImageUrl(item)"
                            alt="Exploratory IDEA opening — not production approved"
                            style="max-width:100%;width:480px"
                          />
                          <figcaption>Normal preview</figcaption>
                        </figure>
                        <figure>
                          <img
                            [src]="explorationImageUrl(item)"
                            alt="Phone-size exploratory preview"
                            style="width:180px;max-width:100%"
                          />
                          <figcaption>Phone preview</figcaption>
                        </figure>
                      </div>
                      <p>
                        Hook potential: {{ item.editorialDecision?.decision || 'NOT ASSESSED' }} ·
                        Story potential: NOT ASSESSED by this image.
                      </p>
                      <label class="field"
                        >Visual assessment note<textarea [(ngModel)]="explorationNote"></textarea>
                      </label>
                      <div class="stage-actions">
                        <button
                          *ngFor="let decision of explorationDecisions"
                          type="button"
                          (click)="decideExploration(item, decision)"
                        >
                          {{
                            decision === 'PROMISING_HOOK'
                              ? 'PROMISING'
                              : decision === 'NEEDS_VISUAL_REVISION'
                                ? 'REVISE'
                                : 'REJECT'
                          }}</button
                        ><button
                          type="button"
                          [disabled]="item.ideaRevision !== ideaDraftRevision"
                          (click)="selectVisualDirection(item)"
                        >
                          Use as visual direction
                        </button>
                      </div></ng-container
                    >
                    <p *ngIf="item.status !== 'GENERATED'">
                      {{ item.status }}. No automatic retry. {{ item.error }}
                    </p>
                  </article>
                </section>
                <section
                  *ngIf="generationDialogOpen"
                  class="generation-authorization"
                  aria-label="Authorize one creative generation"
                >
                  <div class="provider-note">
                    <strong
                      >{{ inputMode === 'IDEA' ? 'IDEA' : 'STORY' }} ·
                      {{ generationProvider }}</strong
                    ><span
                      >{{ storyModel || 'Model unavailable' }} ·
                      {{ storyReady ? 'Connection configured' : 'Unavailable' }}</span
                    ><small>{{
                      readiness?.liveVerified
                        ? 'Verified by the server.'
                        : 'Verification not performed.'
                    }}</small>
                  </div>
                  <p>
                    {{
                      inputMode === 'DETAILED_STORY'
                        ? 'Optionally refine your story in one paid request. Your original story remains unchanged.'
                        : 'One OpenAI IDEA request returns exactly 3 concepts. Each is saved and evaluated independently. No automatic retry.'
                    }}
                  </p>
                  <p>
                    Final request cost is checked by the server against your ceiling. No call is
                    made until you authorize and confirm.
                  </p>
                  <div class="guidance" *ngIf="budget <= 0 || !generationConsent || !storyReady">
                    <span *ngIf="budget <= 0"
                      >Enter an authorised budget greater than $0 to enable this call.</span
                    ><span *ngIf="budget > 0 && !generationConsent"
                      >Confirm this single generation request.</span
                    ><span *ngIf="!storyReady"
                      >The selected provider is unavailable for this creative role.</span
                    >
                  </div>
                  <div class="stage-actions">
                    <label class="consent"
                      ><input type="checkbox" [(ngModel)]="generationConsent" />
                      <span
                        >I authorise one {{ generationProvider }}
                        {{
                          inputMode === 'IDEA'
                            ? 'IDEA-generation request for exactly 3 candidates'
                            : 'story-generation request'
                        }}
                        within this budget.</span
                      ></label
                    ><label class="budget"
                      >Maximum authorised spend (USD)<input
                        type="number"
                        min="0"
                        step="0.001"
                        [(ngModel)]="budget" /></label
                    ><button
                      class="button button--primary"
                      type="button"
                      [disabled]="
                        busy || !idea.trim() || !generationConsent || budget <= 0 || !storyReady
                      "
                      (click)="requestStories()"
                    >
                      Confirm generation</button
                    ><button
                      class="button button--secondary"
                      type="button"
                      (click)="cancelStoryGeneration()"
                    >
                      Cancel
                    </button>
                  </div>
                </section>
              </div>
            </section>
          </section>
          <section *ngSwitchCase="'STORY'" class="stage-panel">
            <section class="story-validation" aria-label="Creative validation">
              <h2>Creative Validation</h2>
              <p>
                Save edits before validation. STORY evidence and VIDEO PROMPT evidence are separate.
                Text cannot prove an actual first frame.
              </p>
              <button
                type="button"
                [disabled]="busy || !storyRecordId || hasSelectedStoryEdits()"
                (click)="validateStory()"
              >
                Run canonical STORY validation</button
              ><button type="button" [disabled]="!storyRecordId" (click)="loadStoryValidation()">
                Load saved validation
              </button>
              <p *ngIf="canonicalStoryResult && !canonicalStoryCurrent" role="alert">
                Previous validation is stale for this selected text. Save and validate this
                revision.
              </p>
              <p
                *ngIf="canonicalStoryResult?.canonicalRuleEvaluation?.validationStage === 'STORY'"
                class="context-note"
              >
                Narrative evidence is assessed here. Attempt counts, active-time percentages, beat
                density and execution timing remain pending until a source-backed motion prompt is
                saved; they are not failures of this STORY.
              </p>
              <app-canonical-findings
                [evaluation]="canonicalStoryResult?.canonicalRuleEvaluation"
                (correct)="focusStoryEditor()"
              ></app-canonical-findings>
              <p>Production decision: {{ storyProductionDecision }}</p>
              <button
                type="button"
                (click)="prepareSingleRevision()"
                [disabled]="busy || !storyRecordId || hasSelectedStoryEdits()"
              >
                Request one explicit AI revision…
              </button>
              <p *ngIf="revisionParentId">
                Correction source: {{ revisionParentId }}. One candidate, separate authorization
                required.
              </p>
            </section>
            <span class="stage-kicker">2 · STORY</span>
            <h2>
              {{
                storyMode === 'IMPROVE_EXISTING_STORY'
                  ? 'Review story refinements'
                  : 'Compare different stories'
              }}
            </h2>
            <p class="stage-intro">
              {{
                storyMode === 'IMPROVE_EXISTING_STORY'
                  ? 'These are refinements of your detailed story. Locked events and the ending remain visible.'
                  : 'These candidates are compared by supported narrative structure, not wording alone.'
              }}
            </p>
            <div *ngIf="fixtureMode" class="fixture-banner" role="alert">
              <strong>⚠ TEST FIXTURE MODE</strong
              ><span
                >This page is displaying <strong>hardcoded test data</strong>, not real DeepSeek
                provider output. The candidates have identical story bodies with different titles.
                Remove <code>?fixture=story-review</code> from the URL to use real data.</span
              >
            </div>
            <section class="story-review-controls">
              <div>
                <strong>OpenAI Story Review</strong
                ><small
                  >Optional independent comparison; it does not approve or authorize
                  rendering.</small
                ><span *ngIf="storyReviewStatus === 'STALE'" class="review-stale"
                  >Previous review outdated</span
                >
              </div>
              <label class="budget"
                >Cost ceiling (USD)<input
                  type="number"
                  min="0"
                  step="0.001"
                  [(ngModel)]="reviewBudget" /></label
              ><label class="consent"
                ><input type="checkbox" [(ngModel)]="reviewConsent" /> I authorise one OpenAI story
                review.</label
              ><button
                class="button button--secondary"
                type="button"
                (click)="reviewStories()"
                [disabled]="reviewBusy || !reviewConsent || reviewBudget <= 0 || !candidates.length"
              >
                {{
                  reviewBusy
                    ? 'Reviewing stories…'
                    : storyReviewStatus === 'STALE'
                      ? 'Review Updated Story'
                      : storyReviewStatus === 'CURRENT'
                        ? 'Review Stories Again'
                        : 'Review Stories with OpenAI'
                }}</button
              ><small
                >{{ reviewModel || promptModel || 'OpenAI model unavailable' }} ·
                {{ candidates.length }} stories ·
                {{ storyReviewStatus.replaceAll('_', ' ') }}</small
              >
              <p *ngIf="reviewError" class="review-error">{{ reviewError }}</p>
            </section>
            <div *ngIf="storyReview" class="openai-review-summary">
              <div class="review-summary-heading">
                <div>
                  <strong>OpenAI Story Comparison</strong
                  ><small
                    >{{ storyReview.reviewStatus || 'COMPLETED' }} ·
                    {{ storyReview.reviewModel || reviewModel || 'OpenAI' }}</small
                  >
                </div>
                <button
                  class="button button--secondary"
                  type="button"
                  (click)="reviewDialogOpen = true; reviewDialogTab = ''"
                >
                  Open full review
                </button>
              </div>
              <p class="review-recommendation">
                <strong>Provider suggestion</strong> ·
                {{ storyReview.recommendationReason || 'Evidence unavailable.'
                }}<small
                  *ngIf="
                    storyQuality?.classification === 'NEAR_DUPLICATE' ||
                    storyQuality?.classification === 'INSUFFICIENT_EVIDENCE'
                  "
                  class="review-evidence-limit"
                >
                  · Canonical evidence does not support a winner</small
                >
              </p>
              <p class="review-disagreement">
                <strong>Canonical comparison:</strong> {{ reviewComparisonLabel() }} ·
                {{ recommendedStoryLabel() }}
              </p>
              <p *ngIf="reviewDisagreement()" class="review-disagreement">
                {{ reviewDisagreement() }}
              </p>
              <div class="review-stat-grid">
                <div>
                  <span>Alternatives</span><strong>{{ candidates.length }}</strong>
                </div>
                <div>
                  <span>Recommended</span><strong>{{ recommendedStoryLabel() }}</strong>
                </div>
                <div>
                  <span>Concerns</span><strong>{{ reviewConcernsLabel() }}</strong>
                </div>
              </div>
              <div class="review-columns">
                <section>
                  <h3>Similarities</h3>
                  <ul>
                    <li *ngFor="let item of reviewSimilarities()">{{ item }}</li>
                  </ul>
                  <p *ngIf="!reviewSimilarities().length">No shared structure recorded.</p>
                </section>
                <section>
                  <h3>Differences</h3>
                  <ul>
                    <li *ngFor="let item of reviewDifferences()">{{ item }}</li>
                  </ul>
                  <p *ngIf="!reviewDifferences().length">No material differences recorded.</p>
                </section>
              </div>
              <div *ngIf="reviewOverallConcerns().length" class="review-concerns">
                <strong>Concerns</strong>
                <ul>
                  <li *ngFor="let item of reviewOverallConcerns()">{{ item }}</li>
                </ul>
              </div>
            </div>
            <div
              *ngIf="reviewDialogOpen"
              class="review-dialog-backdrop"
              role="presentation"
              (click)="closeReviewDialog()"
            >
              <section
                class="review-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby="review-dialog-title"
                (click)="$event.stopPropagation()"
              >
                <header class="review-dialog-header">
                  <div>
                    <span class="stage-kicker">OPENAI STORY REVIEW</span>
                    <h2 id="review-dialog-title">Story comparison</h2>
                    <small
                      >{{ reviewTimestampLabel() }} ·
                      {{ storyReview.reviewPolicyVersion || 'story-review-v1' }}</small
                    >
                  </div>
                  <button
                    type="button"
                    class="review-dialog-close"
                    aria-label="Close review"
                    (click)="closeReviewDialog()"
                  >
                    ×
                  </button>
                </header>
                <div class="review-dialog-body">
                  <section class="review-comparison-summary">
                    <div class="review-summary-row">
                      <span class="review-summary-label">Canonical comparison</span
                      ><span class="review-canonical-badge">{{
                        reviewComparisonLabel().replaceAll('_', ' ')
                      }}</span>
                    </div>
                    <p class="review-summary-text">{{ reviewComparisonSummary() }}</p>
                    <p
                      *ngIf="
                        reviewComparisonLabel() === 'NEAR_DUPLICATE' ||
                        reviewComparisonLabel() === 'INSUFFICIENT_EVIDENCE'
                      "
                      class="review-stale"
                    >
                      {{
                        reviewComparisonLabel() === 'NEAR_DUPLICATE'
                          ? 'These candidates share the same body text after normalization. No independent narrative superiority is established.'
                          : 'Lexical evidence alone cannot establish material differences. Select the exact text you prefer.'
                      }}
                    </p>
                    <div class="review-provider-suggestion">
                      <span class="review-summary-label">Provider suggestion</span
                      ><span>{{
                        storyReview.recommendationReason || 'Provider returned no preference.'
                      }}</span>
                    </div>
                    <p *ngIf="reviewDisagreement()" class="review-disagreement">
                      {{ reviewDisagreement() }}
                    </p>
                    <div *ngIf="reviewOverallConcerns().length" class="review-concerns-inline">
                      <span class="review-summary-label"
                        >Overall concerns ({{ reviewConcernsLabel() }})</span
                      >
                      <ul>
                        <li *ngFor="let item of reviewOverallConcerns()">{{ item }}</li>
                      </ul>
                    </div>
                    <div
                      *ngIf="storyReview.evidenceLimitations?.length"
                      class="review-evidence-limits"
                    >
                      <span class="review-summary-label">Evidence limitations</span>
                      <ul>
                        <li *ngFor="let item of storyReview.evidenceLimitations">{{ item }}</li>
                      </ul>
                    </div>
                  </section>
                  <nav
                    class="review-candidate-tabs"
                    role="tablist"
                    aria-label="Candidate selection"
                  >
                    <button
                      *ngFor="let candidate of candidates; let i = index"
                      type="button"
                      role="tab"
                      [id]="'review-tab-' + candidate.candidateId"
                      [attr.aria-selected]="reviewDialogSelectedId === candidate.candidateId"
                      [attr.tabindex]="reviewDialogSelectedId === candidate.candidateId ? 0 : -1"
                      [class.is-active]="reviewDialogSelectedId === candidate.candidateId"
                      (click)="selectReviewTab(candidate.candidateId)"
                      (keydown.ArrowRight)="
                        selectReviewTab(candidates[(i + 1) % candidates.length].candidateId)
                      "
                      (keydown.ArrowLeft)="
                        selectReviewTab(
                          candidates[(i + candidates.length - 1) % candidates.length].candidateId
                        )
                      "
                    >
                      <span class="review-tab-number">{{ i + 1 }}</span
                      ><span class="review-tab-title">{{
                        candidate.title || 'Alternative ' + (i + 1)
                      }}</span
                      ><span
                        *ngIf="isRecommendedCandidate(candidate, i)"
                        class="review-tab-ai-badge"
                        >AI suggested</span
                      ><span class="review-tab-status">{{
                        candidateReview(candidate.candidateId)?.editorialRecommendation?.replaceAll(
                          '_',
                          ' '
                        ) || '—'
                      }}</span>
                    </button>
                  </nav>
                  <section
                    *ngFor="let candidate of candidates; let i = index"
                    [hidden]="reviewDialogSelectedId !== candidate.candidateId"
                    [id]="'review-panel-' + candidate.candidateId"
                    role="tabpanel"
                    [attr.aria-labelledby]="'review-tab-' + candidate.candidateId"
                    class="review-candidate-detail"
                  >
                    <div class="review-candidate-header">
                      <strong>{{ candidate.title || 'Alternative ' + (i + 1) }}</strong
                      ><span
                        *ngIf="isRecommendedCandidate(candidate, i)"
                        class="review-badge-advisory"
                        >AI suggested</span
                      ><span class="review-score">{{
                        candidateReview(candidate.candidateId)?.editorialRecommendation?.replaceAll(
                          '_',
                          ' '
                        ) ||
                          candidateReview(candidate.candidateId)?.overallStatus ||
                          '—'
                      }}</span>
                    </div>
                    <div class="review-text-assessment-disclaimer">
                      <span>TEXT ASSESSMENT</span> Story text only · not observed video evidence
                    </div>
                    <p class="review-story-text">{{ candidate.text }}</p>
                    <div
                      *ngIf="candidateReview(candidate.candidateId)?.strengths?.length"
                      class="review-strengths"
                    >
                      <span class="review-summary-label">Strengths</span>
                      <ul>
                        <li *ngFor="let item of candidateReview(candidate.candidateId).strengths">
                          {{ item }}
                        </li>
                      </ul>
                    </div>
                    <div
                      *ngIf="candidateReview(candidate.candidateId)?.concerns?.length"
                      class="review-candidate-concerns"
                    >
                      <span class="review-summary-label">Concerns</span>
                      <ul>
                        <li *ngFor="let item of candidateReview(candidate.candidateId).concerns">
                          {{ item }}
                        </li>
                      </ul>
                    </div>
                    <div
                      *ngIf="candidateReview(candidate.candidateId)?.materialFindings?.length"
                      class="review-material-findings"
                    >
                      <span class="review-summary-label">Material findings</span>
                      <ul>
                        <li
                          *ngFor="
                            let item of candidateReview(candidate.candidateId).materialFindings
                          "
                        >
                          {{ item }}
                        </li>
                      </ul>
                    </div>
                    <div
                      *ngIf="
                        candidateReview(candidate.candidateId)?.suggestedMinimalImprovements?.length
                      "
                      class="review-improvements"
                    >
                      <span class="review-summary-label">Suggested improvements</span>
                      <ul>
                        <li
                          *ngFor="
                            let item of candidateReview(candidate.candidateId)
                              .suggestedMinimalImprovements
                          "
                        >
                          {{ item }}
                        </li>
                      </ul>
                    </div>
                    <div
                      *ngIf="normalizedReviewFindings(candidate.candidateId).length"
                      class="review-findings-section"
                    >
                      <span class="review-summary-label"
                        >Structured findings ({{
                          normalizedReviewFindings(candidate.candidateId).length
                        }})</span
                      >
                      <details
                        *ngFor="let finding of normalizedReviewFindings(candidate.candidateId)"
                        class="review-finding-item"
                        [class.review-finding-item--strength]="finding.findingType === 'STRENGTH'"
                        [class.review-finding-item--concern]="finding.findingType === 'CONCERN'"
                        [class.review-finding-item--observation]="
                          finding.findingType === 'OBSERVATION'
                        "
                        [class.review-finding-item--unknown]="finding.findingType === 'UNKNOWN'"
                      >
                        <summary class="review-finding-summary">
                          <span
                            class="review-finding-type-badge"
                            [class.review-finding-type--strength]="
                              finding.findingType === 'STRENGTH'
                            "
                            [class.review-finding-type--concern]="finding.findingType === 'CONCERN'"
                            [class.review-finding-type--observation]="
                              finding.findingType === 'OBSERVATION'
                            "
                            [class.review-finding-type--unknown]="finding.findingType === 'UNKNOWN'"
                            >{{ finding.findingType }}</span
                          ><span class="review-finding-headline">{{ finding.finding }}</span
                          ><span
                            *ngIf="finding.dimension && finding.dimension !== 'Unknown'"
                            class="review-finding-dim"
                            >{{ finding.dimension }}</span
                          ><span
                            *ngIf="finding.severity"
                            class="review-finding-sev"
                            [class.review-finding-sev--low]="finding.severity === 'low'"
                            [class.review-finding-sev--medium]="finding.severity === 'medium'"
                            [class.review-finding-sev--high]="finding.severity === 'high'"
                            [class.review-finding-sev--critical]="finding.severity === 'critical'"
                            >{{ finding.severity }}</span
                          >
                        </summary>
                        <div class="review-finding-body">
                          <div
                            *ngIf="
                              finding.supportingText?.length &&
                              finding.supportingText[0] !== 'Evidence unavailable'
                            "
                            class="review-finding-row"
                          >
                            <span class="review-summary-label">Supporting text</span>
                            <ul>
                              <li *ngFor="let quote of finding.supportingText">{{ quote }}</li>
                            </ul>
                          </div>
                          <div
                            *ngIf="
                              finding.improvement && finding.improvement !== 'Evidence unavailable'
                            "
                            class="review-finding-row"
                          >
                            <span class="review-summary-label">Suggested improvement</span>
                            <p>{{ finding.improvement }}</p>
                          </div>
                          <div class="review-finding-row">
                            <span class="review-summary-label">Provider confidence</span>
                            <p>{{ finding.confidence }}</p>
                          </div>
                        </div>
                      </details>
                    </div>
                    <details class="review-provenance">
                      <summary>Technical provenance</summary>
                      <dl class="review-provenance-facts">
                        <div>
                          <dt>Review ID</dt>
                          <dd>
                            {{
                              storyReview.reviewId || storyReview.persistedRecordId || 'Unavailable'
                            }}
                          </dd>
                        </div>
                        <div>
                          <dt>Persisted at</dt>
                          <dd>{{ reviewTimestampLabel() }}</dd>
                        </div>
                        <div>
                          <dt>Policy version</dt>
                          <dd>{{ storyReview.reviewPolicyVersion || 'story-review-v1' }}</dd>
                        </div>
                        <div>
                          <dt>Provider confidence</dt>
                          <dd>
                            {{
                              candidateReview(candidate.candidateId)?.confidenceOrEvidenceStatus ||
                                'Unavailable'
                            }}
                          </dd>
                        </div>
                      </dl>
                    </details>
                    <small class="review-no-finding" *ngIf="!candidateReview(candidate.candidateId)"
                      >No candidate-specific finding was returned by the provider.</small
                    >
                  </section>
                  <section
                    *ngIf="
                      storyMode === 'IMPROVE_EXISTING_STORY' &&
                      storyQuality?.originalComparisons?.length
                    "
                    class="review-original-source"
                  >
                    <span class="review-summary-label">ORIGINAL_SOURCE comparison</span>
                    <div
                      *ngFor="let pair of storyQuality.originalComparisons"
                      class="review-original-pair"
                    >
                      <span
                        >Alternative {{ pair.candidate }} vs original:
                        {{ pair.lexicalSimilarity * 100 | number: '1.0-1' }}% lexical similarity ·
                        {{ pair.evidenceState }}</span
                      >
                    </div>
                  </section>
                </div>
              </section>
            </div>
            <div *ngIf="storyQuality?.recommendation" class="recommendation-summary">
              <strong>PRELIMINARY RECOMMENDATION</strong>
              <p class="recommendation-label">
                Story-text-only assessment · not production approval
              </p>
              <ng-container *ngIf="storyQuality.recommendation.bestCandidateId; else recTied">
                <div class="recommendation-winner">
                  <span class="recommendation-winner-label">Best supported candidate</span>
                  <strong>{{
                    getRecommendationLabel(storyQuality.recommendation.bestCandidateId)
                  }}</strong>
                </div>
                <div class="recommendation-why">
                  <strong>Why</strong>
                  <ul>
                    <li>{{ storyQuality.recommendation.reason }}</li>
                  </ul>
                </div>
                <div
                  *ngIf="storyQuality.recommendation.whyNot?.length"
                  class="recommendation-why-not"
                >
                  <strong>Other candidates</strong>
                  <ul>
                    <li *ngFor="let wn of storyQuality.recommendation.whyNot">
                      {{ wn.candidateIndex }}. {{ wn.reason }}
                    </li>
                  </ul>
                </div>
              </ng-container>
              <ng-template #recTied>
                <p class="recommendation-tied">
                  <em>{{ storyQuality.recommendation.reason }}</em>
                </p>
              </ng-template>
              <div
                *ngIf="storyQuality.recommendation.stillUnknown?.length"
                class="recommendation-unknown"
              >
                <strong>Still unknown</strong>
                <ul>
                  <li *ngFor="let u of storyQuality.recommendation.stillUnknown">
                    {{ readableDimension(u) }}
                  </li>
                </ul>
              </div>
            </div>
            <div *ngIf="storyQuality" class="diversity-summary">
              <strong>How Are These Stories Different?</strong
              ><span>{{ reviewComparisonLabel().replaceAll('_', ' ') }}</span>
              <p>{{ reviewComparisonSummary() }}</p>
              <p *ngIf="reviewComparisonLabel() === 'NEAR_DUPLICATE'" class="review-stale">
                These refinements are very similar. No further AI call is required: select, edit or
                approve the exact text you prefer.
              </p>
              <ul>
                <li *ngFor="let difference of storyQuality.differences">
                  {{ readableDifference(difference) }}
                </li>
              </ul>
              <div *ngIf="storyQuality.pairs?.length" class="pairwise-ending-details">
                <ng-container *ngFor="let pair of storyQuality.pairs">
                  <div *ngIf="hasEndingDescription(pair)">
                    <strong>Alternative {{ pair.left }} vs {{ pair.right }}:</strong>
                    <p>{{ getPairDifferenceText(pair) }}</p>
                  </div>
                </ng-container>
              </div>
              <details class="evidence-details">
                <summary>Technical evidence</summary>
                <div class="evidence-grid">
                  <div>
                    <span>Comparison method</span
                    ><strong>{{ storyQuality.method || 'Story structure comparison' }}</strong>
                  </div>
                  <div>
                    <span>Pairs compared</span
                    ><strong>{{ storyQuality.pairs?.length || 0 }}</strong>
                  </div>
                </div>
                <div class="evidence-pairs">
                  <article *ngFor="let pair of storyQuality.pairs || []">
                    <header>
                      <strong>Alternative {{ pair.left }} vs {{ pair.right }}</strong
                      ><span
                        >{{ pair.lexicalSimilarity * 100 | number: '1.0-1' }}% wording
                        similarity</span
                      >
                    </header>
                    <div *ngIf="pair.differentDimensions?.length">
                      <small>Different dimensions</small>
                      <p>{{ readableDimensions(pair.differentDimensions) }}</p>
                    </div>
                    <div *ngIf="pair.sharedDimensions?.length">
                      <small>Shared dimensions</small>
                      <p>{{ readableDimensions(pair.sharedDimensions) }}</p>
                    </div>
                    <p *ngIf="hasEndingDescription(pair)" class="dimension-detail">
                      {{ getPairDifferenceText(pair) }}
                    </p>
                  </article>
                </div>
                <div *ngIf="storyQuality.originalComparisons?.length" class="evidence-pairs">
                  <small>Improve mode · original source comparison</small>
                  <article *ngFor="let pair of storyQuality.originalComparisons">
                    <header>
                      <strong>Original Story vs {{ pair.candidateId }}</strong
                      ><span
                        >{{ pair.lexicalSimilarity * 100 | number: '1.0-1' }}% wording similarity ·
                        {{ pair.evidenceState }}</span
                      >
                    </header>
                    <p *ngIf="!pair.supportedDifferences?.length">
                      No supported material difference recorded.
                    </p>
                  </article>
                </div>
              </details>
            </div>
            <div class="story-list">
              <article
                *ngIf="storyMode === 'IMPROVE_EXISTING_STORY' && idea"
                class="story-card"
                [class.is-selected]="selectedCandidateIdValue === 'ORIGINAL_SOURCE'"
              >
                <div class="story-card-heading">
                  <span>Original Story · No AI changes</span
                  ><button type="button" (click)="selectOriginalStory()">
                    {{
                      selectedCandidateIdValue === 'ORIGINAL_SOURCE'
                        ? 'Selected'
                        : 'Select original'
                    }}
                  </button>
                </div>
                <p class="candidate-premise">
                  Immutable source evidence for Improve My Existing Story.
                </p>
                <p>{{ idea }}</p>
                <div class="candidate-actions">
                  <button type="button" (click)="selectOriginalStory()">
                    {{
                      selectedCandidateIdValue === 'ORIGINAL_SOURCE'
                        ? 'Selected'
                        : 'Select Original Story'
                    }}
                  </button>
                </div>
              </article>
              <article
                *ngFor="let candidate of candidates; let i = index"
                class="story-card"
                [class.is-selected]="selectedStory === candidate.text"
              >
                <div class="story-card-heading">
                  <span>{{ candidate.title || 'Alternative ' + (i + 1) }}</span
                  ><button type="button" (click)="selectStory(candidate)">
                    {{ selectedStory === candidate.text ? 'Selected' : 'Select this story' }}
                  </button>
                </div>
                <p class="candidate-premise">
                  {{
                    candidate.structuralEvidence?.centralPremise ||
                      (storyMode === 'IMPROVE_EXISTING_STORY'
                        ? 'Refinement of the supplied story'
                        : 'Candidate narrative direction')
                  }}
                </p>
                <p>{{ candidate.text }}</p>
                <div
                  *ngIf="storyReview && candidateReview(candidate.candidateId) as review"
                  class="candidate-review-compact"
                >
                  <strong>{{ candidateReviewLabel(candidate.candidateId) }}</strong
                  ><span *ngIf="review.concerns?.length"
                    >{{ review.concerns.length }} concern(s)</span
                  >
                </div>
                <div *ngIf="candidate.preflight" class="candidate-evidence">
                  <strong>Opening:</strong> {{ candidate.preflight.opening }} ·
                  <strong>Progression quality:</strong> {{ candidate.preflight.progression
                  }}<small
                    *ngIf="candidate.preflight.progression === 'INSUFFICIENT_EVIDENCE'"
                    class="progression-note"
                  >
                    · Some progression signals may exist, but meaningful beat-to-beat progression is
                    not yet established.</small
                  ><small *ngIf="candidate.preflight.concerns?.length">
                    · Concern: {{ candidate.preflight.concerns.join(' ') }}</small
                  ><small *ngIf="candidate.preflight.productionRisks?.length">
                    · Production risk: {{ candidate.preflight.productionRisks.join(' ') }}</small
                  >
                </div>
                <div class="candidate-ending-evidence">
                  <strong>Ending:</strong> {{ reviewEndingStatus(candidate) }} ·
                  {{ reviewEndingQuality(candidate.candidateId) }}
                </div>
                <div *ngIf="candidate.assessment" class="candidate-assessment">
                  <div class="assessment-disclaimer"><span>PRELIMINARY</span> Story text only</div>
                  <div *ngIf="candidateStrengths(candidate).length" class="assessment-strengths">
                    <span class="assessment-label">Strengths</span>
                    <ul>
                      <li *ngFor="let s of candidateStrengths(candidate)">{{ s.message }}</li>
                    </ul>
                  </div>
                  <div *ngIf="candidateRisks(candidate).length" class="assessment-risks">
                    <span class="assessment-label">Risks</span>
                    <ul>
                      <li *ngFor="let r of candidateRisks(candidate)">{{ r.message }}</li>
                    </ul>
                  </div>
                  <div *ngIf="candidateUnknowns(candidate).length" class="assessment-unknown">
                    <span class="assessment-label">Unknown</span>
                    <ul>
                      <li *ngFor="let u of candidateUnknowns(candidate)">{{ u.message }}</li>
                    </ul>
                  </div>
                </div>
                <div class="candidate-actions">
                  <button type="button" (click)="selectStory(candidate)">
                    {{ selectedStory === candidate.text ? 'Selected' : 'Select Story' }}</button
                  ><button type="button" (click)="editCandidate(candidate)">Edit Story</button
                  ><button type="button" (click)="refineCandidate(candidate)">
                    Refine This Story
                  </button>
                </div>
              </article>
            </div>
            <section class="story-editor" [class.is-editing]="storyEditing">
              <header class="story-editor-header">
                <div>
                  <strong>Selected Story</strong
                  ><small>{{
                    storyEditing
                      ? 'Editing draft — save creates a new revision and does not approve it.'
                      : 'Preview only — select Edit Story to make a draft.'
                  }}</small>
                </div>
                <span class="story-editor-state">{{
                  storyEditing ? (hasStoryTextChanges() ? 'Unsaved changes' : 'Editing') : 'Preview'
                }}</span>
              </header>
              <details *ngIf="parentStory" class="parent-story-comparison">
                <summary>Compare with preserved parent story</summary>
                <pre>{{ parentStory.result?.alternatives?.[0]?.text || parentStory.idea }}</pre>
                <small
                  >Parent record {{ parentStory.recordId }}; previous reviews remain
                  unchanged.</small
                >
              </details>
              <ol *ngIf="selectedStoryBeats.length" aria-label="Timecoded story beats">
                <li *ngFor="let beat of selectedStoryBeats">{{ beat }}</li>
              </ol>
              <textarea
                aria-label="Selected story"
                [(ngModel)]="selectedStory"
                (ngModelChange)="onSelectedStoryChange($event)"
                rows="8"
                [disabled]="!storyRecordId"
                [readonly]="!storyEditing"
              ></textarea
              ><small *ngIf="storyReviewStatus === 'STALE'" class="review-stale"
                >Story modified since the previous review. Save and validate this revision before
                relying on old findings.</small
              >
            </section>
            <div class="stage-actions story-editor-actions">
              <button class="button button--secondary" type="button" (click)="stage = 'IDEA'">
                Back to Idea</button
              ><button
                class="button button--secondary"
                type="button"
                [disabled]="busy || !storyRecordId"
                (click)="startStoryEditing()"
              >
                {{ storyEditing ? 'Continue Editing' : 'Edit Story' }}</button
              ><button
                class="button button--secondary"
                type="button"
                [disabled]="busy || !storyEditing || !hasStoryTextChanges()"
                (click)="saveStoryRevision()"
              >
                {{ busy ? 'Saving draft…' : 'Save Draft Revision' }}</button
              ><button
                *ngIf="storyEditing"
                class="button button--secondary"
                type="button"
                [disabled]="busy"
                (click)="discardStoryEdits()"
              >
                Discard edits</button
              ><button
                class="button button--secondary"
                type="button"
                (click)="requestMoreDistinct()"
                [disabled]="busy || storyMode === 'IMPROVE_EXISTING_STORY'"
              >
                Generate More Distinct Alternatives</button
              ><button
                class="button button--primary"
                type="button"
                [disabled]="
                  busy ||
                  !selectedStory.trim() ||
                  hasSelectedStoryEdits() ||
                  (canonicalStoryCurrent && storyProductionDecision === 'BLOCKED')
                "
                (click)="approveStory()"
              >
                {{ busy ? 'Saving approval…' : 'Approve Story and Continue to Prompt' }}
              </button>
            </div>
          </section>
          <section *ngSwitchCase="'PROMPT'" class="stage-panel">
            <span class="stage-kicker">3 · PROMPT</span>
            <h2>Build a production prompt from the approved story</h2>
            <p class="stage-intro">
              OpenAI uses only the approved story revision, selected profile and target settings.
            </p>
            <div *ngIf="savedPromptRecoveryRequired" class="guidance" role="status">
              <strong>Production prompt needs to be created</strong
              ><span
                >Your approved story is available, but no compatible saved production prompt was
                found. You can create a new prompt without losing your approved story. A new
                provider request requires the authorization and budget below.</span
              >
            </div>
            <div class="lineage">
              <span>Approved Story</span><strong>{{ selectedStory }}</strong>
            </div>
            <div class="provider-note">
              <strong>BUILD_PROMPT · OpenAI</strong
              ><span
                >{{ promptModel || 'Model unavailable' }} ·
                {{ promptReady ? 'Connection configured' : 'Connection unavailable' }}</span
              ><small>This creates a draft; it does not authorise rendering.</small>
            </div>
            <div
              *ngIf="buildAttemptState !== 'NOT_STARTED'"
              class="build-attempt"
              [class.build-attempt--error]="
                buildAttemptState === 'FAILED_NO_RESULT' ||
                buildAttemptState === 'PROVIDER_RESULT_REJECTED' ||
                buildAttemptState === 'PROVIDER_OUTCOME_UNKNOWN'
              "
              role="status"
            >
              <strong>Prompt build: {{ buildAttemptState }}</strong
              ><small *ngIf="buildAttemptState === 'REUSED_SAVED_RESULT'"
                >A saved result for this exact story revision and target settings was reused. No
                provider call was made.</small
              ><small *ngIf="buildAttemptDiagnostics"
                >Historical provider calls:
                {{
                  buildAttemptDiagnostics.providerOutcome === 'UNKNOWN'
                    ? 'UNKNOWN'
                    : buildAttemptDiagnostics.calls || 0
                }}
                · Calls this action:
                {{
                  buildAttemptDiagnostics.callsThisAction ??
                    (buildAttemptState === 'REUSED_SAVED_RESULT'
                      ? 0
                      : buildAttemptDiagnostics.calls || 0)
                }}
                · Saved result reused:
                {{ buildAttemptState === 'REUSED_SAVED_RESULT' ? 'yes' : 'no' }} · Persisted:
                {{ buildAttemptDiagnostics.persisted ? 'yes' : 'no' }}</small
              >
              <small *ngIf="buildAttemptState === 'RECOVERED_REJECTED_PROVIDER_RESPONSE'"
                >The paid response is open as an editable draft. Its original contract rejection is
                preserved; add only source-supported missing execution details before saving a new
                prompt version.</small
              >
              <small
                *ngIf="
                  buildAttemptState === 'RECOVERED_REJECTED_PROVIDER_RESPONSE' &&
                  builderResult?.productionPlan?.recovery?.storyFidelity?.status ===
                    'STORY_FIDELITY_FAIL'
                "
                >STORY_FIDELITY_FAIL:
                {{ builderResult.productionPlan.recovery.storyFidelity.detail }}</small
              >
              <ul
                *ngIf="
                  buildAttemptState === 'RECOVERED_REJECTED_PROVIDER_RESPONSE' &&
                  builderResult?.productionPlan?.recovery?.missingEvidence?.length
                "
                class="recovery-missing-evidence"
              >
                <li *ngFor="let missing of builderResult.productionPlan.recovery.missingEvidence">
                  MISSING_EVIDENCE: {{ missing }}
                </li>
              </ul>
              <small *ngIf="buildAttemptDiagnostics?.error"
                >Original build result: {{ buildAttemptDiagnostics.error }}</small
              >
            </div>
            <label class="field generator-field"
              >Target generator<select
                [(ngModel)]="targetGenerator"
                (ngModelChange)="onPromptTargetGeneratorChange()"
              >
                <option value="SEEDANCE_2_0_MINI">Seedance 2.0 Mini</option>
                <option value="SEEDANCE_2_0">Seedance 2.0</option>
                <option value="SEEDANCE_2_5">Seedance 2.5</option></select
              ><small
                >Capability and risk details are recorded with this prompt build.</small
              ></label
            ><label class="consent"
              ><input type="checkbox" [(ngModel)]="promptConsent" />
              <span>I authorise one prompt-building request within this budget.</span></label
            ><label class="budget"
              >Maximum prompt cost (USD)<input
                type="number"
                min="0"
                step="0.001"
                [(ngModel)]="promptBudget"
                (ngModelChange)="persist()"
            /></label>
            <div class="stage-actions">
              <button class="button button--secondary" type="button" (click)="stage = 'STORY'">
                Edit Story</button
              ><button
                class="button button--primary"
                type="button"
                [disabled]="busy || !promptReady || !promptConsent || promptBudget <= 0"
                (click)="buildPrompt()"
              >
                {{ busy ? 'Building prompt…' : 'Build Production Prompt' }}
              </button>
            </div>
            <section
              *ngIf="builderRecordId && draftPrompt"
              class="saved-draft-state"
              aria-label="Saved prompt state"
            >
              <header>
                <strong>Saved prompt recovery</strong
                ><span>{{
                  builderMigration
                    ? 'Locally revalidated'
                    : builderInputMismatch
                      ? 'Legacy specification'
                      : 'Saved specification'
                }}</span>
              </header>
              <div class="saved-draft-facts">
                <p>
                  <strong>Prompt:</strong> Available · {{ builderRecordId }} · reopening made no
                  provider call
                </p>
                <p>
                  <strong>Specification:</strong>
                  {{
                    builderMigration
                      ? 'Current read model created locally; not provider validated'
                      : builderInputMismatch
                        ? 'Legacy contract; local revalidation required'
                        : 'Current contract'
                  }}
                </p>
                <p>
                  <strong>Evidence:</strong>
                  {{
                    builderMigration
                      ? (builderResult?.productionPlan?.evidenceLimitations?.length || 0) +
                        ' explicit limitation(s); UNKNOWN fields retained'
                      : 'See specification provenance'
                  }}
                </p>
                <p>
                  <strong>Workflow:</strong>
                  {{
                    builderMigration
                      ? 'Preliminary Production Review may continue'
                      : 'Not validated'
                  }}
                  · <strong>Render authorization:</strong> Not granted by migration or review
                  navigation
                </p>
              </div>
              <div class="stage-actions">
                <button
                  *ngIf="
                    !builderPromptTextMismatch &&
                    (builderInputMismatch || builderMigrationRefreshAvailable)
                  "
                  class="button button--secondary"
                  type="button"
                  [disabled]="busy"
                  (click)="revalidateSavedDraft()"
                >
                  {{
                    builderMigration
                      ? 'Refresh Local Evidence — No AI Call'
                      : 'Revalidate Saved Draft — No AI Call'
                  }}</button
                ><button
                  *ngIf="builderMigration && builderInputMismatch && !builderPromptTextMismatch"
                  class="button button--secondary"
                  type="button"
                  (click)="restoreMigratedSettings()"
                >
                  Restore Saved Production Settings</button
                ><button
                  *ngIf="builderPromptTextMismatch"
                  class="button button--secondary"
                  type="button"
                  (click)="restoreSavedPromptText()"
                >
                  Restore Exact Saved Prompt Text</button
                ><button
                  *ngIf="builderMigration"
                  class="button button--secondary"
                  type="button"
                  [disabled]="builderInputMismatch"
                  (click)="openExistingDraftForReview()"
                >
                  Review Existing Draft</button
                ><small
                  *ngIf="builderInputMismatch && !builderMigration && !builderPromptTextMismatch"
                  >This legacy record needs deterministic local migration before it can continue.
                  Rebuilding with OpenAI remains a separately authorized action.</small
                ><small *ngIf="builderPromptTextMismatch"
                  >The editor differs from the saved prompt used by this specification. Restore the
                  exact saved text before local migration or review.</small
                ><small
                  *ngIf="builderMigration && builderInputMismatch && !builderPromptTextMismatch"
                  >Restore the saved settings shown in the specification before reviewing this
                  draft.</small
                ><small *ngIf="builderMigration"
                  >Migration {{ builderMigration.migrationVersion }} ·
                  {{ builderMigration.createdAt }} · provider calls:
                  {{ builderMigration.providerCalls }}</small
                ><small *ngIf="builderMigrationRefreshAvailable"
                  >A newer local evidence recovery is available. Refreshing preserves the original
                  prompt and makes no AI call.</small
                >
              </div>
            </section>
            <div *ngIf="builderInputMismatch && !builderMigration" class="mismatch" role="status">
              <strong>Saved specification needs local revalidation</strong>
              <p>
                The saved prompt remains available. Revalidate it from its exact saved story and
                settings; this preserves the original prompt and creates no provider request.
              </p>
            </div>
            <div *ngIf="draftPrompt" class="prompt-draft">
              <label class="field field-wide"
                >OpenArt Production Prompt<small
                  >Editable Markdown prompt. Each section is separated for direct review and copy
                  into OpenArt.</small
                >
                <div
                  #promptMonaco
                  class="prompt-monaco"
                  aria-label="OpenArt production prompt editor"
                ></div>
                <details>
                  <summary>Plain text motion prompt editor</summary>
                  <textarea
                    aria-label="Motion prompt text"
                    [(ngModel)]="draftPrompt"
                    (ngModelChange)="persist()"
                    rows="14"
                  ></textarea></details
              ></label>
              <section
                *ngIf="builderResult?.productionPlan"
                class="production-plan"
                aria-label="Production prompt specification"
              >
                <header>
                  <div>
                    <span class="eyebrow">PRODUCTION SPECIFICATION</span>
                    <h3>What the prompt is required to preserve</h3>
                  </div>
                  <span class="plan-generator">{{ targetGenerator }}</span>
                </header>
                <div class="plan-grid">
                  <div
                    *ngIf="builderResult.productionPlan?.promptTextEdited"
                    class="stale-plan-warning"
                    role="alert"
                  >
                    <strong>⚠ Production Specification is STALE</strong>
                    <p>
                      The prompt text has been manually edited since this production plan was
                      generated. The structured analysis below reflects the original prompt, not
                      your current edits.
                    </p>
                    <p>
                      After saving your edited prompt, re-run Production Review to get updated
                      analysis.
                    </p>
                  </div>
                  <article>
                    <h4>Creative objective</h4>
                    <p>{{ builderResult.productionPlan.creativeObjective || 'Not established' }}</p>
                    <small
                      >AI-derived interpretation · use the approved profile and source intent as
                      authority.</small
                    >
                  </article>
                  <article>
                    <h4>Source identity</h4>
                    <p>
                      <strong>Project:</strong>
                      {{ builderResult.productionPlan.sourceIdentity?.projectTitle || 'UNKNOWN' }}
                    </p>
                    <p>
                      <strong>Story title:</strong>
                      {{ builderResult.productionPlan.sourceIdentity?.narrativeTitle || 'UNKNOWN' }}
                    </p>
                    <small
                      >Source record and revision:
                      {{ builderResult.productionPlan.sourceIdentity?.storyRecordId || 'UNKNOWN' }}
                      ·
                      {{
                        builderResult.productionPlan.sourceIdentity?.storyRevisionId || 'UNKNOWN'
                      }}</small
                    >
                  </article>
                  <article>
                    <h4>Character identity and references</h4>
                    <div class="plan-item" *ngFor="let binding of productionCharacterBindings">
                      <strong>{{ binding.name || binding.characterName || 'Character' }}</strong>
                      <p>
                        {{
                          binding.identityRequirement ||
                            binding.identityDescription ||
                            'Preserve the supplied character identity.'
                        }}
                      </p>
                      <small
                        >Identity:
                        {{
                          readableProductionValue(
                            binding.identityProvenance || binding.identityStatus || 'UNKNOWN'
                          )
                        }}
                        · visual reference:
                        {{ readableProductionValue(binding.referenceStatus || 'UNKNOWN') }}</small
                      ><small
                        *ngIf="
                          binding.visualDescriptionStatus ===
                            'UNKNOWN_WITHOUT_APPROVED_REFERENCE' ||
                          binding.visualAppearanceStatus === 'UNKNOWN_NO_APPROVED_VISUAL_REFERENCE'
                        "
                        >Appearance has no approved visual-reference evidence. Text-only review can
                        continue; the render gate remains in force.</small
                      >
                    </div>
                  </article>
                  <article>
                    <h4>Selected production settings</h4>
                    <div class="plan-facts">
                      <span>Generator</span
                      ><strong>{{
                        builderResult.productionPlan.productionConstraints?.generator ||
                          targetGenerator
                      }}</strong
                      ><span>Duration</span
                      ><strong
                        >{{
                          builderResult.productionPlan.productionConstraints?.duration || duration
                        }}s</strong
                      ><span>Aspect ratio</span
                      ><strong>{{
                        builderResult.productionPlan.productionConstraints?.aspectRatio ||
                          aspectRatio
                      }}</strong
                      ><span>Profile</span
                      ><strong>{{
                        builderResult.productionPlan.productionConstraints?.contentProfile ||
                          profile
                      }}</strong>
                    </div>
                    <small
                      >Settings provenance:
                      {{
                        builderResult.productionPlan.productionConstraints?.provenance || 'UNKNOWN'
                      }}</small
                    >
                  </article>
                  <article class="plan-wide">
                    <h4>Approved-story fidelity</h4>
                    <p>
                      <strong>{{
                        readableProductionValue(
                          builderResult.productionPlan.storyPromptFidelity?.status || 'UNKNOWN'
                        )
                      }}</strong
                      ><ng-container
                        *ngIf="
                          builderResult.productionPlan.storyPromptFidelity
                            ?.traceableSentenceCount != null &&
                          builderResult.productionPlan.storyPromptFidelity?.sourceSentenceCount !=
                            null
                        "
                      >
                        ·
                        {{
                          builderResult.productionPlan.storyPromptFidelity.traceableSentenceCount
                        }}
                        /
                        {{ builderResult.productionPlan.storyPromptFidelity.sourceSentenceCount }}
                        source sentences traceable</ng-container
                      >
                    </p>
                    <p
                      *ngFor="
                        let sourceEvent of builderResult.productionPlan.storyPromptFidelity
                          ?.unmappedSourceSentences || []
                      "
                    >
                      Unmapped source event: {{ sourceEvent }}
                    </p>
                    <small
                      >Semantic relationship labels are AI-derived and quoted, not independent
                      semantic approval.</small
                    >
                  </article>
                  <article class="plan-wide">
                    <h4>Opening assessment · planned text only</h4>
                    <p>
                      <strong>{{
                        readableProductionValue(
                          builderResult.productionPlan.openingAssessment?.status ||
                            builderResult.productionPlan.openingAssessment?.classification ||
                            'UNKNOWN'
                        )
                      }}</strong
                      ><span *ngIf="builderResult.productionPlan.openingAssessment?.framework">
                        · {{ builderResult.productionPlan.openingAssessment.framework }}</span
                      >
                    </p>
                    <p>
                      {{
                        builderResult.productionPlan.openingAssessment?.openingText ||
                          builderResult.productionPlan.openingAssessment?.visiblePromise ||
                          'No opening text was recovered from the saved prompt.'
                      }}
                    </p>
                    <small
                      >Image evidence:
                      {{
                        readableProductionValue(
                          builderResult.productionPlan.openingAssessment?.imageEvidence ||
                            'UNKNOWN_NOT_GENERATED'
                        )
                      }}. Planned text does not prove a generated first frame.</small
                    >
                  </article>
                  <article
                    *ngIf="builderResult.productionPlan.mechanismAssessment"
                    class="plan-wide"
                  >
                    <h4>Cause and effect</h4>
                    <p>
                      <strong>Core mechanism:</strong>
                      {{ builderResult.productionPlan.mechanismAssessment.coreMechanism }}
                    </p>
                    <p>
                      <strong>Direct consequences:</strong>
                      {{
                        (
                          builderResult.productionPlan.mechanismAssessment.directConsequences || []
                        ).join(' · ') || 'UNKNOWN'
                      }}
                    </p>
                    <p>
                      <strong>Causal status:</strong>
                      {{
                        readableProductionValue(
                          builderResult.productionPlan.mechanismAssessment.causalStatus
                        )
                      }}
                    </p>
                    <p>
                      {{
                        builderResult.productionPlan.mechanismAssessment.viewerComprehensionImpact
                      }}
                    </p>
                    <small
                      >Smallest clarification:
                      {{
                        builderResult.productionPlan.mechanismAssessment.smallestClarification
                      }}</small
                    >
                  </article>
                  <article class="plan-wide">
                    <h4>
                      Timed visual execution · {{ productionBeats.length }} event(s) ·
                      {{
                        readableProductionValue(
                          builderResult.productionPlan.visualExecution?.timelineIntegrity?.status ||
                            'UNKNOWN'
                        )
                      }}
                    </h4>
                    <div class="beat-list">
                      <article *ngFor="let beat of productionBeats">
                        <header>
                          <strong>{{ beat.time || 'Time unknown' }}</strong
                          ><span>{{
                            readableProductionValue(beat.evidenceStatus || 'UNKNOWN')
                          }}</span>
                        </header>
                        <p>
                          <strong>{{ beat.subject || 'Subject not specified' }}:</strong>
                          {{ beat.action || 'Action unknown' }}
                        </p>
                        <p>
                          <strong>Object:</strong> {{ beat.object || 'Not specified in prompt' }}
                        </p>
                        <p>
                          <strong>Prompt-described state change:</strong>
                          {{ beat.stateChange || 'UNKNOWN'
                          }}<small *ngIf="beat.stateChangeStatus">
                            · {{ readableProductionValue(beat.stateChangeStatus) }}</small
                          >
                        </p>
                        <small
                          >{{ readableProductionValue(beat.framing || 'UNKNOWN') }} ·
                          {{ beat.staging || 'Staging unknown' }}</small
                        ><small
                          >Source relationship:
                          {{ readableProductionValue(beat.sourceRelationship || 'UNKNOWN') }} ·
                          exact source quote:
                          {{ beat.sourceEvidence ? 'available' : 'not recovered' }}</small
                        >
                        <details>
                          <summary>Source evidence</summary>
                          <p>
                            {{
                              beat.sourceEvidence ||
                                'No exact source quote supplied. Source relationship remains UNKNOWN.'
                            }}
                          </p>
                        </details>
                      </article>
                    </div>
                    <p *ngIf="!productionBeats.length" class="missing-plan">
                      No timed events were returned. The production plan is incomplete.
                    </p>
                    <small
                      >Coverage:
                      {{
                        builderResult.productionPlan.visualExecution?.timelineIntegrity
                          ?.coveredFromSeconds ?? 'UNKNOWN'
                      }}–{{
                        builderResult.productionPlan.visualExecution?.timelineIntegrity
                          ?.coveredToSeconds ?? 'UNKNOWN'
                      }}s · time ranges are not treated as confirmed semantic major beats.</small
                    >
                  </article>
                  <article class="plan-wide">
                    <h4>Generator execution risks · advisory</h4>
                    <div class="risk-list">
                      <div *ngFor="let risk of productionRisks">
                        <strong>{{ risk.risk || risk.event || 'Risk' }}</strong>
                        <p>
                          {{
                            risk.mitigation || risk.smallestMitigation || 'No mitigation provided.'
                          }}
                        </p>
                        <small
                          >Evidence: {{ risk.sourceEvidence || 'UNKNOWN' }} · event:
                          {{ risk.affectedEvent || 'UNKNOWN' }} · confidence:
                          {{ risk.confidence || 'UNKNOWN' }} · next:
                          {{ readableProductionValue(risk.nextAction || 'LATER_VISUAL_QA') }}</small
                        >
                      </div>
                    </div>
                    <small
                      >Risks do not become hard blockers unless required evidence establishes a
                      blocker.</small
                    >
                  </article>
                  <article>
                    <h4>Provider capability snapshot</h4>
                    <p>
                      {{
                        builderResult.productionPlan.generatorCapabilityAssessment?.apiModelId ||
                          targetGenerator
                      }}
                    </p>
                    <small
                      >Duration:
                      {{
                        builderResult.productionPlan.generatorCapabilityAssessment?.duration
                          ?.supported === true
                          ? 'supported'
                          : builderResult.productionPlan.generatorCapabilityAssessment?.duration
                                ?.supported === false
                            ? 'unsupported'
                            : 'UNKNOWN'
                      }}
                      · aspect ratio:
                      {{
                        builderResult.productionPlan.generatorCapabilityAssessment?.aspectRatio
                          ?.status || 'UNKNOWN'
                      }}
                      · start frame field:
                      {{
                        builderResult.productionPlan.generatorCapabilityAssessment
                          ?.startFrameFieldSupported === true
                          ? 'supported'
                          : 'UNKNOWN'
                      }}</small
                    ><small
                      >Snapshot:
                      {{
                        builderResult.productionPlan.generatorCapabilityAssessment?.source ||
                          'UNKNOWN'
                      }}
                      · capability and creative suitability are separate checks.</small
                    >
                  </article>
                  <article>
                    <h4>Evidence and reference limits</h4>
                    <p>
                      Character identity:
                      {{
                        readableProductionValue(
                          productionCharacterBindings[0]?.identityStatus || 'UNKNOWN'
                        )
                      }}
                      · approved visual reference:
                      {{
                        readableProductionValue(
                          productionCharacterBindings[0]?.referenceStatus || 'UNKNOWN'
                        )
                      }}
                      · first frame:
                      {{
                        readableProductionValue(
                          builderResult.productionPlan.referencePlan?.firstFrameStatus || 'UNKNOWN'
                        )
                      }}
                    </p>
                    <ul>
                      <li
                        *ngFor="let item of builderResult.productionPlan.evidenceLimitations || []"
                      >
                        {{ item }}
                      </li>
                    </ul>
                  </article>
                  <article class="plan-wide">
                    <h4>Field provenance</h4>
                    <div class="provenance-list">
                      <div *ngFor="let item of productionProvenance">
                        <span>{{ readableProductionValue(item[0]) }}</span
                        ><strong>{{ readableProductionValue(item[1]) }}</strong>
                      </div>
                    </div>
                    <details>
                      <summary>Developer JSON</summary>
                      <pre>{{ builderResult.productionPlan | json }}</pre>
                    </details>
                  </article>
                </div>
              </section>
              <button
                class="button button--primary"
                type="button"
                [disabled]="
                  busy ||
                  draftPrompt.trim().length < 20 ||
                  (builderInputMismatch &&
                    !builderMigration &&
                    buildAttemptState !== 'RECOVERED_REJECTED_PROVIDER_RESPONSE')
                "
                (click)="savePrompt()"
              >
                {{
                  promptVersionId && !promptDirty
                    ? 'Continue to Production Review →'
                    : 'Save Draft & Continue to Production Review →'
                }}</button
              ><small *ngIf="builderInputMismatch && !builderMigration" class="action-prerequisite"
                >Disabled: run “Revalidate Saved Draft — No AI Call” above.</small
              >
            </div>
          </section>
          <section *ngSwitchDefault class="stage-panel">
            <span class="stage-kicker">{{ stageLabel(stage) }}</span>
            <h2>
              {{
                stage === 'PRODUCTION_REVIEW'
                  ? 'Review production requirements'
                  : 'Continue in the quality workflow'
              }}
            </h2>
            <p class="stage-intro">
              The saved prompt opens at Production Review. Quality Analysis, Repair, Render
              Preparation and Video QA follow in order; analysis does not authorize rendering.
            </p>
            <div class="stage-actions">
              <a class="button button--primary" [routerLink]="detailUrl"
                >Open Production Review →</a
              >
            </div>
          </section>
        </ng-container>
      </section>
      <aside class="studio-context">
        <h2>Workflow Summary</h2>
        <div class="context-mode" [class.context-mode--new]="activeJourney === 'NEW'">
          <strong>{{
            activeJourney === 'NEW'
              ? ideaDraftRevision
                ? draftDirty
                  ? 'Saved Draft · Unsaved Changes'
                  : 'Saved Draft'
                : 'New Unsaved Draft'
              : activeJourney === 'SAVED'
                ? 'Selected Saved Story'
                : 'Current Saved Workflow'
          }}</strong
          ><span>{{
            activeJourney === 'NEW'
              ? 'Provider call only after explicit confirmation.'
              : 'Saved state is reused without a provider call.'
          }}</span>
        </div>
        <dl>
          <div>
            <dt>Next Action</dt>
            <dd>{{ nextAction }}</dd>
          </div>
          <div>
            <dt>Video Title</dt>
            <dd>{{ activeContextTitle }}</dd>
          </div>
          <div>
            <dt>Main Character</dt>
            <dd>{{ activeContextCharacter }}</dd>
          </div>
          <div>
            <dt>Profile</dt>
            <dd>
              {{
                activeContextProfile === 'AUTO'
                  ? 'Auto · recommendation pending'
                  : readableProductionValue(activeContextProfile)
              }}
            </dd>
          </div>
          <div>
            <dt>Target Duration</dt>
            <dd>
              {{ activeContextDuration }}s{{
                activeJourney === 'NEW' && duration === 15 ? ' · default' : ''
              }}
            </dd>
          </div>
          <div>
            <dt>Aspect Ratio</dt>
            <dd>
              {{ activeContextAspectRatio
              }}{{ activeJourney === 'NEW' && aspectRatio === '9:16' ? ' · default' : '' }}
            </dd>
          </div>
          <div *ngIf="activeSavedStory">
            <dt>Project Review</dt>
            <dd>{{ projectReviewStatus }}</dd>
          </div>
          <div>
            <dt>Story Approval</dt>
            <dd>{{ readableProductionValue(storyApprovalStatus) }}</dd>
          </div>
          <div>
            <dt>Prompt Status</dt>
            <dd>{{ readableProductionValue(promptAcceptanceStatus) }}</dd>
          </div>
          <div>
            <dt>Provider</dt>
            <dd>{{ providerStatus }}{{ readiness?.liveVerified ? '' : ' · not verified' }}</dd>
          </div>
        </dl>
        <details *ngIf="idea">
          <summary>Show source content</summary>
          <p class="idea-preview">{{ idea }}</p>
        </details>
        <p class="context-note">
          Story approval, prompt acceptance and render authorisation are separate decisions.
        </p>
      </aside>
    </section>
    <div
      *ngIf="workspaceDialogOpen"
      class="workspace-dialog-backdrop"
      role="presentation"
      (click)="closeWorkspaceDialog()"
    >
      <section
        class="workspace-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workspace-dialog-title"
        (click)="$event.stopPropagation()"
      >
        <header>
          <div>
            <span class="eyebrow">DESTINATION</span>
            <h2 id="workspace-dialog-title">Create additional workspace</h2>
          </div>
          <button
            type="button"
            class="workspace-dialog-close"
            aria-label="Close"
            (click)="closeWorkspaceDialog()"
          >
            ×
          </button>
        </header>
        <div class="workspace-dialog-body">
          <label class="field" for="workspace-name"
            >Workspace name<input
              id="workspace-name"
              #workspaceNameInput
              [(ngModel)]="workspaceName"
              (ngModelChange)="workspaceNameError = ''"
              (keydown.enter)="submitWorkspace()"
              maxlength="100"
              autocomplete="off" /></label
          ><small *ngIf="workspaceNameError" class="workspace-dialog-error" role="alert">{{
            workspaceNameError
          }}</small
          ><small>Use letters, numbers, spaces, dot, underscore or hyphen.</small>
          <div class="stage-actions">
            <button
              type="button"
              class="button button--secondary"
              [disabled]="workspaceCreating"
              (click)="closeWorkspaceDialog()"
            >
              Cancel</button
            ><button
              type="button"
              class="button button--primary"
              [disabled]="workspaceCreating"
              (click)="submitWorkspace()"
            >
              {{ workspaceCreating ? 'Creating…' : 'Create workspace' }}
            </button>
          </div>
        </div>
      </section>
    </div>
    <div
      *ngIf="renameDialogOpen"
      class="workspace-dialog-backdrop"
      role="presentation"
      (click)="closeRenameDialog()"
    >
      <section
        class="workspace-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rename-dialog-title"
        (click)="$event.stopPropagation()"
      >
        <header>
          <div>
            <span class="eyebrow">SAVED PROJECT</span>
            <h2 id="rename-dialog-title">Rename project</h2>
          </div>
          <button
            type="button"
            class="workspace-dialog-close"
            aria-label="Close"
            (click)="closeRenameDialog()"
          >
            ×
          </button>
        </header>
        <div class="workspace-dialog-body">
          <label class="field" for="rename-project-name"
            >Project name<input
              id="rename-project-name"
              [(ngModel)]="renameName"
              (ngModelChange)="renameError = ''"
              (keydown.enter)="submitRename()"
              maxlength="120"
              autocomplete="off" /></label
          ><small *ngIf="renameError" class="workspace-dialog-error" role="alert">{{
            renameError
          }}</small>
          <div class="stage-actions">
            <button type="button" class="button button--secondary" (click)="closeRenameDialog()">
              Cancel</button
            ><button type="button" class="button button--primary" (click)="submitRename()">
              Rename project
            </button>
          </div>
        </div>
      </section>
    </div>
    <div *ngIf="confirmDialogOpen" class="workspace-dialog-backdrop" role="presentation">
      <section
        class="workspace-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        (click)="$event.stopPropagation()"
      >
        <header>
          <div>
            <span class="eyebrow">CONFIRM ACTION</span>
            <h2 id="confirm-dialog-title">{{ confirmDialogTitle }}</h2>
          </div>
        </header>
        <div class="workspace-dialog-body">
          <p>{{ confirmDialogMessage }}</p>
          <div class="stage-actions">
            <button
              type="button"
              class="button button--secondary"
              (click)="resolveConfirmation(false)"
            >
              Cancel</button
            ><button
              type="button"
              class="button button--primary"
              (click)="resolveConfirmation(true)"
            >
              Continue
            </button>
          </div>
        </div>
      </section>
    </div>
  </main>`,
  styles: [
    `
      .journey-map {
        padding: 1rem;
        border: 1px solid #d8e1d9;
        border-radius: 10px;
        margin: 1rem 0;
        background: #f8fbf6;
      }
      .journey-map ol {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.7rem;
        padding-left: 1.2rem;
      }
      .journey-map li {
        padding: 0.5rem;
        font-size: 0.78rem;
      }
      .journey-map button {
        font-weight: 700;
        color: #31583b;
        border: 0;
        background: transparent;
        cursor: pointer;
      }
      .visual-versions {
        display: flex;
        gap: 0.5rem;
        overflow: auto;
      }
      .visual-versions article {
        display: grid;
        flex: 0 0 180px;
      }
      .visual-versions button {
        overflow-wrap: anywhere;
      }
      .visual-versions img {
        justify-self: center;
      }
      .story-validation {
        padding: 1rem;
        background: #f7faf4;
        border: 1px solid #d8e1d9;
        border-radius: 8px;
        margin-bottom: 1rem;
      }
      .resume-panel {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #8fbd36;
        border-radius: 9px;
        background: linear-gradient(135deg, #f4fae8, #fff);
      }
      .resume-panel > div:first-child {
        display: grid;
        gap: 0.25rem;
      }
      .resume-panel strong {
        color: #31583b;
      }
      .resume-panel small {
        color: #52616b;
        font-size: 0.75rem;
      }
      .resume-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: flex-end;
      }
      .saved-story-library {
        display: grid;
        gap: 0.65rem;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #d6e7b5;
        border-radius: 8px;
        background: #f7fbef;
      }
      .saved-story-heading {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
      }
      .saved-story-heading div {
        display: grid;
        gap: 0.2rem;
      }
      .saved-story-heading small,
      .saved-story-heading span,
      .saved-story-card small {
        color: #68747c;
        font-size: 0.7rem;
      }
      .saved-story-card {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
        padding: 0.75rem;
        border: 1px solid #dfe5e8;
        border-radius: 7px;
        background: #fff;
      }
      .saved-story-card div {
        min-width: 0;
      }
      .saved-story-card p {
        margin: 0.25rem 0 0;
        overflow: hidden;
        color: #40515a;
        font-size: 0.75rem;
        line-height: 1.35;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .saved-story-empty {
        margin: 1rem 0;
        color: #68747c;
        font-size: 0.78rem;
      }
      .story-review-controls {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto auto auto;
        align-items: center;
        gap: 0.75rem;
        margin: 1rem 0;
        padding: 0.85rem;
        border: 1px solid #dfe5e8;
        border-radius: 8px;
        background: #fbfcfd;
      }
      .story-review-controls > div {
        display: grid;
        gap: 0.2rem;
      }
      .story-review-controls small {
        color: #68747c;
        font-size: 0.7rem;
      }
      .review-stale {
        color: #9a6416;
        font-weight: 800;
      }
      .review-error {
        grid-column: 1/-1;
        margin: 0;
        color: #9c3f3f;
        font-size: 0.75rem;
      }
      .review-summary-heading {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
      }
      .review-summary-heading div {
        display: grid;
        gap: 0.2rem;
      }
      .review-summary-heading small {
        color: #68747c;
        font-size: 0.7rem;
      }
      .review-recommendation {
        font-weight: 700;
      }
      .review-stat-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.6rem;
      }
      .review-stat-grid div {
        display: grid;
        gap: 0.2rem;
        padding: 0.65rem;
        border-radius: 6px;
        background: #fff;
      }
      .review-stat-grid span {
        font-size: 0.68rem;
        color: #68747c;
      }
      .review-stat-grid strong {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .review-columns {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
      }
      .review-columns h3,
      .review-detail-block h3 {
        margin: 0;
        font-size: 0.8rem;
      }
      .review-columns ul,
      .review-concerns ul {
        margin: 0.4rem 0 0;
        padding-left: 1.1rem;
      }
      .review-columns p {
        margin: 0.4rem 0;
        color: #68747c;
        font-size: 0.75rem;
      }
      .review-disagreement {
        margin: 0;
        padding: 0.65rem;
        border-radius: 6px;
        background: #fff9ed;
        color: #855b15;
        font-size: 0.75rem;
        line-height: 1.4;
      }
      .review-concerns {
        padding: 0.7rem;
        border-radius: 6px;
        background: #fff9ed;
        color: #855b15;
      }
      .review-dialog-backdrop {
        position: fixed;
        inset: 0;
        z-index: 1000;
        display: grid;
        place-items: center;
        padding: 1rem;
        background: rgba(21, 34, 28, 0.52);
      }
      .review-dialog {
        width: min(880px, 100%);
        max-height: min(88vh, 820px);
        overflow: hidden;
        display: flex;
        flex-direction: column;
        border-radius: 12px;
        background: #fff;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.22);
      }
      .review-dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        padding: 1.1rem 1.4rem;
        border-bottom: 1px solid #e4e9e5;
        flex-shrink: 0;
      }
      .review-dialog-header h2 {
        margin: 0.2rem 0 0;
        font-size: 1.25rem;
      }
      .review-dialog-header small {
        color: #68747c;
        font-size: 0.72rem;
      }
      .review-dialog-close {
        border: 0;
        background: transparent;
        color: #52616b;
        font-size: 1.6rem;
        line-height: 1;
        cursor: pointer;
        padding: 0.25rem 0.4rem;
        border-radius: 5px;
      }
      .review-dialog-close:hover {
        background: #f0f4f2;
      }
      .review-dialog-body {
        flex: 1;
        overflow: auto;
        padding: 1.1rem 1.4rem;
        display: grid;
        gap: 0.9rem;
      }
      .review-comparison-summary {
        display: grid;
        gap: 0.5rem;
        padding: 0.9rem;
        background: #f6f8f9;
        border: 1px solid #e4e9e5;
        border-radius: 8px;
      }
      .review-summary-label {
        display: block;
        color: #68747c;
        font-size: 0.65rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .review-summary-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        flex-wrap: wrap;
      }
      .review-summary-text {
        margin: 0;
        font-size: 0.82rem;
        color: #40515a;
        line-height: 1.45;
      }
      .review-canonical-badge {
        display: inline-flex;
        padding: 0.2rem 0.5rem;
        border-radius: 999px;
        background: #eef2f4;
        color: #40515a;
        font-size: 0.65rem;
        font-weight: 800;
      }
      .review-provider-suggestion {
        display: grid;
        gap: 0.25rem;
        padding: 0.6rem;
        border-left: 3px solid #d0d8dc;
        background: #fff;
        border-radius: 0 6px 6px 0;
        font-size: 0.82rem;
        color: #40515a;
      }
      .review-concerns-inline {
        display: grid;
        gap: 0.3rem;
      }
      .review-concerns-inline ul,
      .review-evidence-limits ul {
        margin: 0.25rem 0 0;
        padding-left: 1.2rem;
        font-size: 0.78rem;
        color: #40515a;
      }
      .review-evidence-limits {
        display: grid;
        gap: 0.3rem;
      }
      .review-disagreement {
        margin: 0;
        padding: 0.5rem 0.65rem;
        border-radius: 5px;
        background: #fff5ed;
        color: #855b15;
        font-size: 0.78rem;
        line-height: 1.45;
      }
      .review-candidate-tabs {
        display: flex;
        gap: 0.35rem;
        border-bottom: 1px solid #e4e9e5;
        overflow-x: auto;
        flex-shrink: 0;
      }
      .review-candidate-tabs button {
        flex: 1 1 auto;
        min-width: 100px;
        display: grid;
        gap: 0.2rem;
        padding: 0.6rem 0.8rem;
        background: transparent;
        border: 0;
        border-bottom: 3px solid transparent;
        cursor: pointer;
        text-align: left;
        transition:
          border-color 0.12s ease,
          background 0.12s ease;
      }
      .review-candidate-tabs button:hover {
        background: #f6f8f9;
      }
      .review-candidate-tabs button.is-active {
        border-bottom-color: #6ba43a;
        background: #fafcf7;
      }
      .review-tab-number {
        font-size: 0.62rem;
        font-weight: 800;
        color: #8399a2;
      }
      .review-tab-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #263f56;
      }
      .review-tab-ai-badge {
        display: inline-flex;
        padding: 0.15rem 0.35rem;
        border-radius: 999px;
        background: #f0f4ed;
        color: #4a7a5a;
        font-size: 0.6rem;
        font-weight: 800;
      }
      .review-tab-status {
        font-size: 0.65rem;
        color: #68747c;
      }
      .review-candidate-detail {
        display: grid;
        gap: 0.7rem;
      }
      .review-candidate-header {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        flex-wrap: wrap;
      }
      .review-candidate-header strong {
        font-size: 0.95rem;
        color: #263f56;
      }
      .review-badge-advisory {
        padding: 0.2rem 0.45rem;
        border-radius: 999px;
        background: #e8f2ec;
        color: #3e6e50;
        font-size: 0.65rem;
        font-weight: 800;
      }
      .review-score {
        padding: 0.2rem 0.45rem;
        border-radius: 999px;
        background: #eef2f4;
        color: #52616b;
        font-size: 0.65rem;
        font-weight: 800;
      }
      .review-text-assessment-disclaimer {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.6rem;
        border-radius: 4px;
        background: #f0f4f7;
        font-size: 0.68rem;
        color: #52616b;
      }
      .review-text-assessment-disclaimer span {
        font-weight: 800;
        color: #8399a2;
        font-size: 0.62rem;
        letter-spacing: 0.04em;
      }
      .review-story-text {
        margin: 0 !important;
        padding: 0.7rem;
        border-left: 3px solid #dfe5e8;
        color: #40515a;
        font-size: 0.82rem;
        line-height: 1.5;
      }
      .review-strengths {
        display: grid;
        gap: 0.25rem;
      }
      .review-strengths ul {
        margin: 0.2rem 0 0;
        padding-left: 1.2rem;
        font-size: 0.78rem;
        color: #31583b;
      }
      .review-candidate-concerns {
        padding: 0.55rem 0.65rem;
        border-radius: 6px;
        background: #fff5ed;
        color: #855b15;
        display: grid;
        gap: 0.3rem;
      }
      .review-candidate-concerns ul {
        margin: 0.2rem 0 0;
        padding-left: 1.2rem;
        font-size: 0.78rem;
      }
      .review-material-findings,
      .review-improvements {
        display: grid;
        gap: 0.25rem;
      }
      .review-material-findings ul,
      .review-improvements ul {
        margin: 0.2rem 0 0;
        padding-left: 1.2rem;
        font-size: 0.78rem;
        color: #40515a;
      }
      .review-findings-section {
        display: grid;
        gap: 0.4rem;
      }
      .review-finding-item {
        border: 1px solid #e4e9e5;
        border-radius: 7px;
        overflow: hidden;
      }
      .review-finding-item[open] {
        border-color: #cdd8dc;
      }
      .review-finding-summary {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        padding: 0.55rem 0.75rem;
        cursor: pointer;
        font-size: 0.82rem;
        list-style: none;
        background: #f9fafb;
      }
      .review-finding-summary::-webkit-details-marker {
        display: none;
      }
      .review-finding-summary::before {
        content: '›';
        font-size: 0.9rem;
        color: #8399a2;
        flex-shrink: 0;
        transition: transform 0.12s ease;
      }
      .review-finding-item[open] .review-finding-summary::before {
        transform: rotate(90deg);
      }
      .review-finding-headline {
        flex: 1;
        min-width: 0;
        font-weight: 600;
        color: #263f56;
        overflow-wrap: anywhere;
      }
      .review-finding-dim {
        padding: 0.15rem 0.35rem;
        border-radius: 999px;
        background: #eef2f4;
        color: #52616b;
        font-size: 0.65rem;
        font-weight: 700;
        white-space: nowrap;
      }
      .review-finding-sev {
        padding: 0.15rem 0.35rem;
        border-radius: 999px;
        background: #fff0e8;
        color: #9a4e1a;
        font-size: 0.65rem;
        font-weight: 800;
      }
      .review-finding-sev--low {
        background: #f0f7f2;
        color: #3e6e50;
      }
      .review-finding-sev--medium {
        background: #ffe0b2;
        color: #e65100;
      }
      .review-finding-sev--high {
        background: #ffcdd2;
        color: #c62828;
      }
      .review-finding-sev--critical {
        background: #f44336;
        color: #fff;
        font-weight: 700;
      }
      .review-finding-type-badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-right: 4px;
      }
      .review-finding-type--strength {
        background: #c8e6c9;
        color: #2e7d32;
      }
      .review-finding-type--concern {
        background: #ffcdd2;
        color: #c62828;
      }
      .review-finding-type--observation {
        background: #e3f2fd;
        color: #1565c0;
      }
      .review-finding-type--unknown {
        background: #e0e0e0;
        color: #616161;
      }
      .review-finding-type--mixed {
        background: #fff3e0;
        color: #e65100;
      }
      .fixture-banner {
        display: grid;
        gap: 0.4rem;
        padding: 0.75rem 1rem;
        border: 2px solid #ff9800;
        border-radius: 8px;
        background: #fff3e0;
        color: #e65100;
        font-size: 0.82rem;
        margin: 0.5rem 0;
      }
      .fixture-banner strong {
        font-size: 0.9rem;
      }
      .fixture-banner code {
        background: #ffe0b2;
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 0.78rem;
      }

      .review-finding-item--strength > .review-finding-summary {
        border-left: 3px solid #4caf50;
      }
      .review-finding-item--concern > .review-finding-summary {
        border-left: 3px solid #f44336;
      }
      .review-finding-item--observation > .review-finding-summary {
        border-left: 3px solid #2196f3;
      }
      .review-finding-item--mixed > .review-finding-summary {
        border-left: 3px solid #ff9800;
      }
      .review-finding-item--unknown > .review-finding-summary {
        border-left: 3px solid #9e9e9e;
      }
      .review-evidence-limit {
        color: #c62828;
        font-weight: 600;
      }
      .review-finding-body {
        display: grid;
        gap: 0.5rem;
        padding: 0.65rem 0.75rem;
        border-top: 1px solid #e4e9e5;
      }
      .review-finding-row {
        display: grid;
        gap: 0.2rem;
      }
      .review-finding-row p {
        margin: 0;
        font-size: 0.78rem;
        color: #40515a;
        line-height: 1.45;
      }
      .review-finding-row ul {
        margin: 0.15rem 0 0;
        padding-left: 1.2rem;
        font-size: 0.78rem;
        color: #40515a;
      }
      .review-provenance {
        margin-top: 0.25rem;
        font-size: 0.78rem;
      }
      .review-provenance summary {
        cursor: pointer;
        color: #68747c;
        font-weight: 700;
      }
      .review-provenance-facts {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.3rem 0.75rem;
        margin-top: 0.5rem;
      }
      .review-provenance-facts > div {
        display: grid;
        gap: 0.1rem;
      }
      .review-provenance-facts dt {
        font-size: 0.65rem;
        font-weight: 800;
        color: #8399a2;
        text-transform: uppercase;
      }
      .review-provenance-facts dd {
        margin: 0;
        font-size: 0.72rem;
        color: #40515a;
        overflow-wrap: anywhere;
      }
      .review-no-finding {
        display: block;
        color: #8399a2;
        font-size: 0.75rem;
      }
      .review-original-source {
        display: grid;
        gap: 0.4rem;
        padding: 0.75rem;
        border: 1px solid #e4e9e5;
        border-radius: 7px;
        background: #f9fafb;
      }
      .review-original-pair {
        font-size: 0.75rem;
        color: #40515a;
      }
      @media (max-width: 600px) {
        .review-dialog {
          max-height: 96dvh;
          border-radius: 10px 10px 0 0;
        }
        .review-dialog-backdrop {
          padding: 0.4rem 0.4rem 0;
        }
        .review-candidate-tabs button {
          min-width: 80px;
          padding: 0.5rem 0.5rem;
        }
        .review-provenance-facts {
          grid-template-columns: 1fr;
        }
      }
      .openai-review-summary {
        display: grid;
        gap: 0.4rem;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #cbdced;
        border-radius: 8px;
        background: #f5f9fd;
        color: #263f56;
      }
      .openai-review-summary p {
        margin: 0;
        color: #40515a;
      }
      .review-finding-changes {
        display: grid;
        gap: 0.25rem;
        color: #40515a;
        font-size: 0.75rem;
      }
      .openai-review-summary pre {
        max-height: 260px;
        overflow: auto;
        white-space: pre-wrap;
        font-size: 0.68rem;
      }
      .story-generation-controls {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 1rem;
        margin: 1rem 0;
      }
      .freedom-fieldset {
        display: grid;
        gap: 0.45rem;
        margin: 0;
        padding: 0.75rem;
        border: 1px solid #dfe5e8;
        border-radius: 7px;
        color: #40515a;
        font-size: 0.78rem;
      }
      .freedom-fieldset legend {
        padding: 0 0.25rem;
        font-weight: 800;
      }
      .freedom-fieldset label {
        display: flex;
        gap: 0.45rem;
        align-items: center;
      }
      .evidence-details {
        margin-top: 0.65rem;
        padding-top: 0.65rem;
        border-top: 1px solid #d6e7b5;
      }
      .evidence-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.55rem;
        margin: 0.7rem 0;
      }
      .evidence-grid div {
        display: grid;
        gap: 0.2rem;
        padding: 0.6rem;
        border-radius: 6px;
        background: #fff;
      }
      .evidence-grid span,
      .evidence-pairs small {
        color: #68747c;
        font-size: 0.65rem;
        font-weight: 800;
        text-transform: uppercase;
      }
      .evidence-grid strong {
        color: #31583b;
        font-size: 0.78rem;
      }
      .evidence-pairs {
        display: grid;
        gap: 0.55rem;
      }
      .evidence-pairs article {
        display: grid;
        gap: 0.35rem;
        padding: 0.65rem;
        border: 1px solid #d6e7b5;
        border-radius: 6px;
        background: #fff;
      }
      .evidence-pairs header {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        align-items: center;
      }
      .evidence-pairs header strong {
        font-size: 0.75rem;
        color: #31583b;
      }
      .evidence-pairs header span {
        font-size: 0.68rem;
        color: #68747c;
      }
      .evidence-pairs p {
        margin: 0;
        color: #40515a;
        font-size: 0.75rem;
        line-height: 1.4;
      }
      @media (max-width: 600px) {
        .evidence-grid {
          grid-template-columns: 1fr;
        }
        .evidence-pairs header {
          display: grid;
          align-items: start;
        }
      }
      .recommendation-summary {
        display: grid;
        gap: 0.6rem;
        padding: 1rem;
        border: 1px solid #8fbd36;
        border-radius: 8px;
        background: linear-gradient(135deg, #f4fae8, #fff);
        margin: 1rem 0;
        color: #31583b;
      }
      .recommendation-summary strong {
        color: #26352c;
      }
      .recommendation-label {
        font-size: 0.72rem;
        color: #68747c;
        font-style: italic;
      }
      .recommendation-winner {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        background: #e8f5e9;
        border-radius: 6px;
        border: 1px solid #a5d6a7;
      }
      .recommendation-winner-label {
        font-size: 0.78rem;
        color: #52616b;
      }
      .recommendation-winner strong {
        font-size: 0.95rem;
        color: #2e7d32;
      }
      .recommendation-why,
      .recommendation-why-not,
      .recommendation-unknown {
        display: grid;
        gap: 0.3rem;
        padding: 0.5rem 0;
      }
      .recommendation-why strong,
      .recommendation-why-not strong,
      .recommendation-unknown strong {
        font-size: 0.78rem;
        color: #52616b;
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }
      .recommendation-why ul,
      .recommendation-why-not ul,
      .recommendation-unknown ul {
        margin: 0;
        padding-left: 1.2rem;
        font-size: 0.82rem;
        color: #40515a;
      }
      .recommendation-why li {
        color: #2e7d32;
      }
      .recommendation-why-not li {
        color: #e65100;
      }
      .recommendation-unknown li {
        color: #616161;
      }
      .recommendation-tied {
        font-size: 0.85rem;
        color: #52616b;
        padding: 0.5rem 0;
      }
      .diversity-summary {
        display: grid;
        gap: 0.5rem;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #d6e7b5;
        border-radius: 8px;
        background: #f5faed;
        color: #31583b;
      }
      .diversity-summary p {
        margin: 0;
        color: #40515a;
      }
      .diversity-summary ul {
        margin: 0.25rem 0;
        padding-left: 1.2rem;
        color: #52616b;
      }
      .diversity-summary pre {
        max-height: 220px;
        overflow: auto;
        white-space: pre-wrap;
        color: #52616b;
        font-size: 0.68rem;
      }
      .candidate-premise {
        font-size: 0.78rem;
        font-weight: 700;
      }
      .candidate-review-compact {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.65rem;
        color: #31583b;
        font-size: 0.72rem;
      }
      .candidate-review-compact span {
        color: #9a6416;
      }
      .candidate-evidence {
        display: grid;
        gap: 0.25rem;
        margin-top: 0.7rem;
        padding: 0.65rem;
        border-top: 1px solid #e4e9e5;
        color: #52616b;
        font-size: 0.72rem;
      }
      .candidate-assessment {
        display: grid;
        gap: 0.3rem;
        margin-top: 0.7rem;
        padding: 0.65rem;
        border: 1px solid #e4e9e5;
        border-radius: 6px;
        background: #f9fafb;
        font-size: 0.78rem;
      }
      .assessment-disclaimer {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        background: #f0f4f7;
        font-size: 0.65rem;
        color: #52616b;
      }
      .assessment-disclaimer span {
        font-weight: 800;
        color: #8399a2;
        font-size: 0.6rem;
        letter-spacing: 0.04em;
      }
      .assessment-label {
        font-weight: 700;
        font-size: 0.72rem;
        display: block;
        margin-bottom: 0.15rem;
      }
      .assessment-strengths {
        color: #2e7d32;
      }
      .assessment-strengths .assessment-label {
        color: #1b5e20;
      }
      .assessment-strengths ul {
        margin: 0.15rem 0 0;
        padding-left: 1rem;
        font-size: 0.75rem;
      }
      .assessment-risks {
        color: #e65100;
      }
      .assessment-risks .assessment-label {
        color: #bf360c;
      }
      .assessment-risks ul {
        margin: 0.15rem 0 0;
        padding-left: 1rem;
        font-size: 0.75rem;
      }
      .assessment-unknown {
        color: #616161;
      }
      .stale-plan-warning {
        display: grid;
        gap: 0.4rem;
        padding: 0.75rem 1rem;
        border: 2px solid #ff9800;
        border-radius: 8px;
        background: #fff3e0;
        color: #e65100;
        font-size: 0.82rem;
        margin: 0.75rem 0;
      }
      .stale-plan-warning strong {
        font-size: 0.9rem;
      }
      .stale-plan-warning p {
        margin: 0;
        color: #bf360c;
        font-size: 0.78rem;
      }
      .pairwise-ending-details {
        margin: 0.5rem 0;
        padding: 0.5rem;
        border-left: 3px solid #d6e7b5;
        background: #f5faed;
        border-radius: 4px;
      }
      .pairwise-ending-details strong {
        color: #31583b;
        font-size: 0.85rem;
      }
      .pairwise-ending-details p {
        margin: 0.25rem 0;
        color: #52616b;
        font-size: 0.82rem;
        font-style: italic;
      }
      .dimension-detail {
        margin: 0.25rem 0;
        color: #52616b;
        font-size: 0.82rem;
        font-style: italic;
      }
      .progression-note {
        color: #8a6d3b;
        font-style: italic;
      }
      .assessment-unknown .assessment-label {
        color: #424242;
      }
      .assessment-unknown ul {
        margin: 0.15rem 0 0;
        padding-left: 1rem;
        font-size: 0.75rem;
      }
      .candidate-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.7rem;
      }
      .candidate-actions button {
        border: 0;
        background: transparent;
        color: #31583b;
        cursor: pointer;
        font-weight: 800;
        font-size: 0.72rem;
      }
      .studio {
        max-width: 1280px;
        margin: 0 auto;
        padding: 2rem 2.5rem;
        color: #26352c;
      }
      .studio-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 2rem;
        margin-bottom: 1.5rem;
      }
      .studio-header h1 {
        margin: 0.25rem 0;
        font-size: 2.3rem;
      }
      .studio-header p,
      .stage-intro {
        color: #68747c;
        line-height: 1.55;
      }
      .eyebrow,
      .stage-kicker {
        color: #5f8435;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
      }
      .studio-steps {
        display: grid;
        grid-template-columns: repeat(8, minmax(0, 1fr));
        gap: 0.5rem;
        margin-bottom: 1.25rem;
      }
      .studio-steps button {
        display: grid;
        gap: 0.25rem;
        min-width: 0;
        padding: 0.7rem;
        border: 1px solid #dfe5e8;
        border-radius: 8px;
        background: #fff;
        color: #52616b;
        text-align: left;
        cursor: pointer;
      }
      .studio-steps button.is-active {
        border-color: #8fbd36;
        box-shadow: 0 0 0 2px #eaf3d7;
      }
      .studio-steps button.is-complete {
        background: #f4f9ec;
      }
      .studio-steps button:disabled {
        cursor: default;
        opacity: 0.55;
      }
      .studio-steps span {
        color: #31583b;
        font-weight: 800;
      }
      .studio-steps strong {
        overflow: hidden;
        font-size: 0.75rem;
        text-overflow: ellipsis;
      }
      .studio-steps small {
        font-size: 0.65rem;
      }
      .studio-layout {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 280px;
        gap: 1.25rem;
        align-items: start;
      }
      .studio-main,
      .studio-context,
      .stage-panel {
        border: 1px solid #dfe5e8;
        border-radius: 10px;
        background: #fff;
      }
      .stage-panel {
        padding: 1.5rem;
      }
      .stage-panel h2 {
        margin: 0.45rem 0 0.5rem;
        font-size: 1.55rem;
      }
      .field {
        display: grid;
        gap: 0.4rem;
        color: #40515a;
        font-size: 0.78rem;
        font-weight: 700;
      }
      .field input,
      .field textarea,
      .field select {
        width: 100%;
        padding: 0.7rem 0.75rem;
        border: 1px solid #cbd6ce;
        border-radius: 6px;
        background: #fff;
        color: #2c3e50;
        font: inherit;
        font-weight: 400;
      }
      .field textarea {
        resize: vertical;
      }
      .field-wide {
        margin: 1rem 0;
      }
      .preference-picker {
        position: relative;
      }
      .preference-picker-header {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        align-items: baseline;
      }
      .preference-picker-header > span {
        font-weight: 700;
      }
      .preference-picker-header small {
        font-weight: 400;
        color: #68747c;
      }
      .preference-trigger {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        flex-wrap: wrap;
        min-height: 44px;
        width: 100%;
        padding: 0.45rem 0.6rem;
        border: 1px solid #cbd6ce;
        border-radius: 7px;
        background: #fff;
        color: #2c3e50;
        cursor: pointer;
        text-align: left;
      }
      .preference-placeholder {
        color: #87939b;
        font-weight: 400;
      }
      .preference-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        flex: 1;
      }
      .preference-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.25rem 0.45rem;
        border-radius: 999px;
        background: #e8f2dc;
        color: #31583b;
        font-size: 0.7rem;
        font-weight: 800;
      }
      .preference-chip button {
        border: 0;
        background: transparent;
        color: #31583b;
        cursor: pointer;
        font-weight: 900;
        padding: 0;
        line-height: 1;
      }
      .preference-chevron {
        margin-left: auto;
        color: #68747c;
      }
      .preference-menu {
        position: absolute;
        z-index: 20;
        top: calc(100% - 0.5rem);
        left: 0;
        right: 0;
        display: grid;
        gap: 0.3rem;
        padding: 0.55rem;
        border: 1px solid #cbd6ce;
        border-radius: 8px;
        background: #fff;
        box-shadow: 0 12px 28px rgba(21, 34, 28, 0.18);
        max-height: 250px;
        overflow: auto;
      }
      .preference-menu input {
        width: 100%;
        padding: 0.55rem;
        border: 1px solid #dfe5e8;
        border-radius: 5px;
      }
      .preference-option {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        border: 0;
        background: transparent;
        padding: 0.55rem;
        text-align: left;
        color: #40515a;
        cursor: pointer;
        border-radius: 5px;
      }
      .preference-option:hover,
      .preference-option.is-selected {
        background: #f1f7e9;
        color: #31583b;
      }
      .preference-check {
        width: 1rem;
        color: #5f8435;
        font-weight: 900;
      }
      .studio,
      .studio-main,
      .stage-panel,
      .studio-layout,
      .field-grid,
      .field,
      .saved-story-library,
      .saved-story-card {
        min-width: 0;
      }
      .studio {
        overflow-x: clip;
      }
      .studio-main {
        overflow: hidden;
      }
      .saved-story-card {
        align-items: flex-start;
        overflow: hidden;
      }
      .saved-story-card p {
        white-space: normal;
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3;
        overflow: hidden;
        word-break: break-word;
      }
      .field-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
      }
      .mode-picker {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.65rem;
        margin: 1rem 0;
      }
      .mode-picker label {
        display: grid;
        gap: 0.3rem;
        padding: 0.75rem;
        border: 1px solid #dfe5e8;
        border-radius: 7px;
        cursor: pointer;
      }
      .mode-picker label.is-selected {
        border-color: #8fbd36;
        background: #f5faed;
      }
      .mode-picker input {
        accent-color: #31583b;
      }
      .mode-picker strong {
        font-size: 0.78rem;
      }
      .mode-picker small {
        color: #68747c;
        font-size: 0.7rem;
      }
      .provider-note,
      .lineage {
        display: grid;
        gap: 0.25rem;
        padding: 0.85rem;
        margin: 1rem 0;
        border-radius: 7px;
        background: #f5f9f1;
      }
      .build-attempt {
        display: grid;
        gap: 0.2rem;
        padding: 0.7rem 0.85rem;
        margin: 1rem 0;
        border: 1px solid #cbdced;
        border-radius: 7px;
        background: #f5f9fd;
        color: #263f56;
        font-size: 0.78rem;
      }
      .build-attempt small {
        color: #52616b;
      }
      .build-attempt--error {
        border-color: #e6b7ad;
        background: #fff5f2;
        color: #8c362b;
      }
      .provider-note strong {
        color: #31583b;
      }
      .provider-note span,
      .provider-note small {
        color: #68747c;
      }
      .guidance {
        display: grid;
        gap: 0.25rem;
        padding: 0.75rem;
        border: 1px solid #d6e7b5;
        border-radius: 7px;
        background: #f5faed;
        color: #31583b;
        font-size: 0.78rem;
      }
      .guidance--error {
        border-color: #ecd2a2;
        background: #fff9ed;
        color: #855b15;
      }
      .mode-suggestion {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.55rem;
        margin: 1rem 0;
        padding: 0.7rem 0.8rem;
        border: 1px solid #cbdced;
        border-radius: 7px;
        background: #f5f9fd;
        color: #263f56;
        font-size: 0.76rem;
      }
      .mode-suggestion span {
        flex: 1;
        min-width: 220px;
      }
      .mode-suggestion button {
        border: 0;
        background: transparent;
        color: #31583b;
        font-weight: 800;
        cursor: pointer;
      }
      .mismatch {
        display: grid;
        gap: 0.4rem;
        padding: 0.8rem;
        border: 1px solid #e4c77e;
        border-radius: 7px;
        background: #fff9ed;
        color: #765317;
      }
      .mismatch p {
        margin: 0;
      }
      .mismatch button {
        width: max-content;
        border: 0;
        background: transparent;
        color: #31583b;
        cursor: pointer;
        font-weight: 800;
      }
      .saved-draft-state {
        display: grid;
        gap: 0.65rem;
        margin: 1rem 0;
        padding: 0.9rem 1rem;
        border: 1px solid #b9d69b;
        border-radius: 8px;
        background: #f5faef;
        color: #31583b;
      }
      .saved-draft-state > header {
        display: flex;
        justify-content: space-between;
        gap: 0.8rem;
        align-items: center;
      }
      .saved-draft-state > header span {
        padding: 0.25rem 0.5rem;
        border-radius: 99px;
        background: #e3efd8;
        font-size: 0.7rem;
        font-weight: 800;
      }
      .saved-draft-facts {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.15rem 1rem;
      }
      .saved-draft-facts p {
        margin: 0;
        color: #52616b;
        font-size: 0.75rem;
        line-height: 1.4;
      }
      .saved-draft-state .stage-actions {
        margin-top: 0.25rem;
      }
      .saved-draft-state small,
      .action-prerequisite {
        color: #68747c;
        font-size: 0.72rem;
      }
      .action-prerequisite {
        display: block;
        margin-top: 0.4rem;
      }
      .advanced {
        margin: 1rem 0;
        color: #52616b;
      }
      .stage-actions {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.75rem;
        margin-top: 1.25rem;
      }
      .consent {
        display: flex;
        align-items: flex-start;
        gap: 0.45rem;
        color: #52616b;
        font-size: 0.78rem;
      }
      .budget {
        display: grid;
        gap: 0.25rem;
        color: #52616b;
        font-size: 0.72rem;
        font-weight: 700;
      }
      .budget input {
        width: 100px;
        padding: 0.5rem;
        border: 1px solid #cbd6ce;
        border-radius: 5px;
      }
      .story-list {
        display: grid;
        gap: 0.8rem;
        margin: 1.25rem 0;
      }
      .story-card {
        padding: 1rem;
        border: 1px solid #dfe5e8;
        border-radius: 8px;
      }
      .story-card.is-selected {
        border-color: #8fbd36;
        background: #f7fbef;
      }
      .story-card-heading {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        color: #68747c;
        font-size: 0.72rem;
      }
      .story-card-heading button,
      .studio-error button {
        border: 0;
        background: transparent;
        color: #31583b;
        font-weight: 800;
        cursor: pointer;
      }
      .story-card h3 {
        margin: 0.55rem 0;
        font-size: 1rem;
      }
      .story-card p {
        margin: 0;
        color: #40515a;
        line-height: 1.5;
      }
      .lineage strong {
        white-space: pre-wrap;
        font-weight: 500;
        line-height: 1.45;
      }
      .prompt-monaco {
        height: 460px;
        width: 100%;
        border: 1px solid #33443b;
        border-radius: 7px;
        overflow: hidden;
        margin-top: 0.4rem;
      }
      .prompt-draft {
        margin-top: 1.25rem;
        padding-top: 1.25rem;
        border-top: 1px solid #e4e9e5;
      }
      .production-plan {
        display: grid;
        gap: 0.9rem;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #cbdced;
        border-radius: 9px;
        background: #f6f9fd;
        color: #263f56;
      }
      .production-plan header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
      }
      .production-plan h3 {
        margin: 0.25rem 0 0;
        font-size: 1rem;
      }
      .plan-generator {
        padding: 0.25rem 0.5rem;
        border-radius: 999px;
        background: #e5f2d8;
        color: #31583b;
        font-size: 0.68rem;
        font-weight: 800;
      }
      .plan-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.7rem;
      }
      .plan-grid article {
        min-width: 0;
        padding: 0.7rem;
        border: 1px solid #dce7ef;
        border-radius: 7px;
        background: #fff;
      }
      .plan-grid h4 {
        margin: 0 0 0.35rem;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .plan-grid p {
        margin: 0;
        color: #40515a;
        font-size: 0.78rem;
        line-height: 1.4;
      }
      .plan-grid pre {
        max-height: 160px;
        overflow: auto;
        margin: 0;
        color: #52616b;
        font-size: 0.68rem;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .plan-wide {
        grid-column: 1/-1;
      }
      .plan-facts {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.3rem 0.65rem;
        font-size: 0.75rem;
      }
      .plan-facts span,
      .plan-grid small {
        color: #68747c;
        font-size: 0.7rem;
        line-height: 1.4;
      }
      .plan-item,
      .risk-list > div {
        display: grid;
        gap: 0.3rem;
        padding: 0.5rem 0;
        border-top: 1px solid #edf1f4;
      }
      .beat-list article header {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
      }
      .beat-list article p {
        margin: 0.15rem 0;
      }
      .beat-list article small {
        display: block;
      }
      .beat-list details summary,
      .plan-grid details summary {
        cursor: pointer;
        color: #31583b;
        font-weight: 700;
        font-size: 0.72rem;
      }
      .beat-list details p {
        white-space: pre-wrap;
      }
      .provenance-list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.4rem;
      }
      .provenance-list div {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        padding: 0.4rem;
        background: #f6f8f9;
        border-radius: 5px;
        font-size: 0.7rem;
      }
      .missing-plan {
        padding: 0.6rem;
        background: #fff5df;
        color: #855b15;
      }
      @media (max-width: 600px) {
        .plan-grid {
          grid-template-columns: 1fr;
        }
      }
      .studio-context {
        position: sticky;
        top: 1rem;
        padding: 1.1rem;
      }
      .studio-context h2 {
        margin: 0 0 1rem;
        font-size: 1rem;
      }
      .studio-context dl {
        display: grid;
        gap: 0.85rem;
        margin: 0;
      }
      .studio-context dl div {
        display: grid;
        gap: 0.2rem;
      }
      .studio-context dt {
        color: #7b8790;
        font-size: 0.68rem;
        font-weight: 800;
        text-transform: uppercase;
      }
      .studio-context dd {
        margin: 0;
        overflow-wrap: anywhere;
        color: #40515a;
        font-size: 0.78rem;
      }
      .idea-preview {
        display: -webkit-box;
        overflow: hidden;
        color: #68747c;
        font-size: 0.78rem;
        line-height: 1.4;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 3;
      }
      .context-note {
        padding-top: 1rem;
        border-top: 1px solid #e4e9e5;
        color: #68747c;
        font-size: 0.72rem;
        line-height: 1.45;
      }
      .studio-error {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1rem;
        padding: 0.8rem 1rem;
        border: 1px solid #e6b7ad;
        border-radius: 7px;
        background: #fff5f2;
        color: #8c362b;
      }
      .studio-error p {
        margin: 0;
        flex: 1;
      }
      .studio-error strong {
        white-space: nowrap;
      }
      .studio-error details {
        flex: 1;
        min-width: 0;
      }
      .studio-error summary {
        cursor: pointer;
        color: #6d3a31;
        font-size: 0.75rem;
      }
      .studio-error code {
        display: block;
        overflow: auto;
        margin-top: 0.35rem;
        padding: 0.45rem;
        background: #fff;
        color: #6d3a31;
        font-size: 0.68rem;
        white-space: pre-wrap;
      }
      .button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.7rem 0.9rem;
        border: 1px solid #cbd6ce;
        border-radius: 6px;
        text-decoration: none;
        font: inherit;
        font-weight: 800;
        cursor: pointer;
      }
      .button--primary {
        background: #31583b;
        color: #fff;
        border-color: #31583b;
      }
      .button--secondary {
        background: #fff;
        color: #31583b;
      }
      .button:disabled {
        cursor: default;
        opacity: 0.55;
      }
      @media (max-width: 1000px) {
        .studio {
          padding: 1.5rem;
        }
        .studio-steps {
          grid-template-columns: repeat(4, 1fr);
        }
        .studio-layout {
          grid-template-columns: 1fr;
        }
        .studio-context {
          position: static;
        }
      }
      @media (max-width: 600px) {
        .saved-draft-facts {
          grid-template-columns: 1fr;
        }
        .resume-panel {
          display: grid;
        }
        .resume-actions {
          justify-content: stretch;
        }
        .resume-actions .button {
          width: 100%;
        }
        .preference-menu {
          position: fixed;
          left: 1rem;
          right: 1rem;
          top: auto;
          bottom: 1rem;
          max-height: 45vh;
        }
        .saved-story-card {
          display: grid;
        }
        .review-columns {
          grid-template-columns: 1fr;
        }
        .studio {
          padding: 1rem;
        }
        .studio-header {
          display: grid;
        }
        .studio-header h1 {
          font-size: 1.8rem;
        }
        .studio-steps {
          grid-template-columns: repeat(2, 1fr);
        }
        .mode-picker {
          grid-template-columns: 1fr;
        }
        .field-grid {
          grid-template-columns: 1fr;
        }
        .stage-panel {
          padding: 1rem;
        }
        .stage-actions {
          align-items: stretch;
        }
        .stage-actions .button {
          width: 100%;
        }
        .studio-error {
          display: grid;
        }
        .budget input {
          width: 100%;
        }
      }
      .journey-section {
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #dfe5e8;
        border-radius: 9px;
        background: #fff;
      }
      .create-section {
        background: #fbfdf9;
      }
      .section-heading {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
      }
      .section-heading h3 {
        margin: 0.25rem 0;
        font-size: 1.05rem;
        color: #26352c;
      }
      .section-heading p {
        margin: 0.25rem 0 0;
        color: #68747c;
        font-size: 0.78rem;
      }
      .section-count {
        color: #68747c;
        font-size: 0.72rem;
        font-weight: 800;
      }
      .new-story-form {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid #e4e9e5;
      }
      .new-story-form-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.25rem;
      }
      .draft-origin {
        display: block;
        color: #68747c;
        font-size: 0.72rem;
      }
      .workspace-details {
        margin-top: 0.25rem;
        color: #68747c;
        font-size: 0.68rem;
        font-weight: 400;
      }
      .workspace-details summary {
        cursor: pointer;
      }
      .workspace-details code {
        display: block;
        overflow-wrap: anywhere;
        margin-top: 0.25rem;
        padding: 0.35rem;
        border-radius: 4px;
        background: #f5f7f8;
        font-size: 0.65rem;
        font-weight: 400;
      }
      .saved-story-list {
        display: grid;
        gap: 0.65rem;
        margin-top: 0.8rem;
      }
      .saved-story-card {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        padding: 0.85rem;
        border: 1px solid #dfe5e8;
        border-radius: 8px;
        background: #fff;
      }
      .saved-story-card.is-selected {
        border-color: #8fbd36;
        background: #f7fbef;
        box-shadow: 0 0 0 2px #eaf3d7;
      }
      .saved-story-content {
        min-width: 0;
        display: grid;
        gap: 0.25rem;
      }
      .saved-story-title {
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }
      .saved-story-title strong {
        color: #26352c;
      }
      .saved-story-content p {
        margin: 0.2rem 0;
        color: #40515a;
        font-size: 0.78rem;
        line-height: 1.45;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .saved-story-content small {
        color: #68747c;
        font-size: 0.7rem;
      }
      .saved-story-id {
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .saved-story-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: flex-end;
        flex-shrink: 0;
      }
      .saved-story-actions .button,
      .resume-actions .button {
        min-width: 132px;
        min-height: 42px;
        white-space: nowrap;
      }
      .selection-badge {
        padding: 0.2rem 0.45rem;
        border-radius: 999px;
        background: #e5f2d8;
        color: #31583b;
        font-size: 0.65rem;
        font-weight: 800;
      }
      .provider-policy-note {
        display: grid;
        gap: 0.2rem;
        margin: 1rem 0;
        padding: 0.75rem 0.85rem;
        border: 1px solid #dfe5e8;
        border-radius: 7px;
        background: #f8fafb;
        color: #52616b;
        font-size: 0.75rem;
      }
      .provider-policy-note strong {
        color: #31583b;
      }
      .provider-policy-note span {
        line-height: 1.4;
      }
      .context-mode {
        display: grid;
        gap: 0.2rem;
        margin-bottom: 1rem;
        padding: 0.65rem 0.7rem;
        border-radius: 7px;
        background: #f5f9f1;
        color: #31583b;
      }
      .context-mode--new {
        background: #f5f9fd;
        color: #263f56;
      }
      .context-mode span {
        font-size: 0.7rem;
        color: #68747c;
      }
      .field select,
      .field input,
      .field textarea {
        appearance: auto;
        box-sizing: border-box;
        min-height: 42px;
        line-height: 1.25;
        padding: 0.55rem 0.75rem;
      }
      .story-generation-controls .field select {
        padding-right: 2rem;
      }
      .stage-actions .button {
        white-space: nowrap;
        min-height: 42px;
      }
      .button {
        white-space: nowrap;
      }
      .section-heading .button {
        flex-shrink: 0;
      }
      @media (max-width: 700px) {
        .saved-story-card,
        .section-heading {
          display: grid;
        }
        .saved-story-actions {
          justify-content: stretch;
        }
        .saved-story-actions .button {
          width: 100%;
        }
        .section-heading .button {
          width: 100%;
        }
      }
      .draft-library-toolbar {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 150px 150px;
        gap: 0.5rem;
        margin: 0.8rem 0;
      }
      .draft-library-toolbar input,
      .draft-library-toolbar select {
        min-height: 40px;
        padding: 0.55rem 0.65rem;
        border: 1px solid #cbd6ce;
        border-radius: 6px;
        background: #fff;
        color: #2c3e50;
        font: inherit;
      }
      .draft-library {
        display: grid;
        gap: 0.35rem;
        min-width: 0;
      }
      .draft-library-row {
        display: grid;
        grid-template-columns:
          minmax(145px, 1.35fr) minmax(72px, 0.65fr) minmax(96px, 0.9fr)
          minmax(112px, 1fr) minmax(230px, 1.7fr);
        gap: 0.55rem;
        align-items: center;
        width: 100%;
        min-width: 0;
        box-sizing: border-box;
        padding: 0.65rem 0.7rem;
        border: 1px solid #e2e8e4;
        border-radius: 7px;
        background: #fff;
        color: #40515a;
        font-size: 0.75rem;
      }
      .draft-library-row.is-selected {
        border-color: #8fbd36;
        background: #f7fbef;
      }
      .draft-library-row > div:first-child {
        display: grid;
        gap: 0.2rem;
        min-width: 0;
      }
      .draft-library-row strong {
        overflow: hidden;
        color: #26352c;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .draft-library-row small,
      .draft-library-row time {
        color: #68747c;
        font-size: 0.68rem;
      }
      .draft-library-header {
        border: 0;
        background: #f5f9f1;
        color: #52616b;
        font-size: 0.68rem;
        font-weight: 800;
        text-transform: uppercase;
      }
      .lifecycle-badge {
        width: max-content;
        padding: 0.25rem 0.45rem;
        border-radius: 999px;
        background: #eef2f4;
        color: #52616b;
        font-size: 0.66rem;
        font-weight: 800;
      }
      .lifecycle-badge--approved {
        background: #e5f2d8;
        color: #31583b;
      }
      .lifecycle-badge--archived {
        background: #f1e8dc;
        color: #855b15;
      }
      .draft-library-actions {
        position: relative;
        display: flex;
        flex-wrap: nowrap;
        align-items: center;
        justify-content: flex-end;
        gap: 0.35rem;
        min-width: 0;
      }
      .draft-library-actions .button {
        min-height: 34px;
        min-width: 0;
        padding: 0.45rem 0.5rem;
        font-size: 0.66rem;
        white-space: nowrap;
      }
      .saved-actions-menu {
        position: absolute;
        z-index: 30;
        right: 0;
        top: calc(100% + 0.25rem);
        display: grid;
        min-width: 140px;
        padding: 0.3rem;
        border: 1px solid #cbd6ce;
        border-radius: 6px;
        background: #fff;
        box-shadow: 0 10px 24px rgba(21, 34, 28, 0.18);
      }
      .saved-actions-menu button {
        border: 0;
        background: #fff;
        padding: 0.5rem;
        text-align: left;
        color: #40515a;
        cursor: pointer;
        font: inherit;
        font-size: 0.72rem;
      }
      .saved-actions-menu button:hover {
        background: #f1f7e9;
        color: #31583b;
      }
      .library-message {
        margin: 0.7rem 0 0;
        color: #31583b;
        font-size: 0.75rem;
      }
      @media (max-width: 900px) {
        .draft-library-row {
          grid-template-columns:
            minmax(135px, 1.35fr) minmax(72px, 0.65fr) minmax(95px, 0.9fr)
            minmax(230px, 1.7fr);
        }
        .draft-library-row > time {
          display: none;
        }
      }
      @media (max-width: 700px) {
        .draft-library-toolbar {
          grid-template-columns: 1fr;
        }
        .draft-library-header {
          display: none;
        }
        .draft-library-row {
          grid-template-columns: 1fr;
          gap: 0.4rem;
        }
        .draft-library-actions {
          justify-content: flex-start;
        }
        .draft-library-actions .button {
          flex: 1;
        }
        .saved-actions-menu {
          left: 0;
          right: auto;
        }
      }
      .new-story-form .field {
        align-content: start;
      }
      .new-story-form .field input,
      .new-story-form .field select {
        height: 42px;
        min-height: 42px;
      }
      .library-empty {
        padding: 1rem;
      }
      .library-empty .section-heading {
        margin-bottom: 0.4rem;
        padding-bottom: 0.5rem;
      }
      .library-empty .section-heading p {
        display: none;
      }
      .library-empty .saved-story-empty {
        padding: 0.8rem 1rem;
        text-align: left;
      }
      .saved-story-empty strong {
        display: block;
        color: #31583b;
      }
      .saved-story-empty p {
        margin: 0.3rem 0;
        font-size: 0.8rem;
      }
      .idea-draft-list {
        display: grid;
        gap: 0.45rem;
        margin-top: 0.7rem;
      }
      .idea-draft-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem;
        border: 1px solid #d6e1ce;
        border-radius: 7px;
        min-width: 0;
      }
      .idea-draft-row > div {
        flex: 1;
        min-width: 0;
        display: grid;
        gap: 0.3rem;
      }
      .idea-draft-row strong {
        overflow-wrap: anywhere;
      }
      .idea-draft-row small,
      .idea-draft-row time {
        font-size: 0.72rem;
        color: #52616b;
      }
      .generation-authorization {
        padding: 1rem;
        border: 1px solid #b6caa5;
        border-radius: 8px;
        background: #f8fbf4;
      }
      .generation-authorization p {
        font-size: 0.8rem;
        color: #40515a;
      }
      .idea-actions {
        flex-wrap: wrap;
      }
      .field small button {
        font: inherit;
      }
      .new-story-form input:focus-visible,
      .new-story-form select:focus-visible,
      .new-story-form textarea:focus-visible,
      .button:focus-visible {
        outline: 2px solid #668b28;
        outline-offset: 2px;
      }
      @media (max-width: 700px) {
        .idea-draft-row {
          flex-wrap: wrap;
        }
        .idea-draft-row > div {
          flex-basis: 100%;
        }
        .idea-draft-row time {
          display: none;
        }
      }
    `,
    `
      .preference-picker {
        overflow: visible;
      }
      .stage-panel,
      .studio-main {
        overflow: visible;
      }
      .preference-menu {
        top: calc(100% + 0.35rem);
        max-height: min(280px, 42vh);
        overflow-y: auto;
        overscroll-behavior: contain;
      }
      .preference-menu.is-above {
        top: auto;
        bottom: calc(100% + 0.35rem);
      }
      .preference-option {
        min-height: 38px;
        font-size: 0.76rem;
        line-height: 1.3;
        white-space: normal;
      }
      .workspace-settings {
        grid-column: 1/-1;
        padding: 0.65rem 0.75rem;
        border: 1px solid #dfe5e8;
        border-radius: 7px;
      }
      .workspace-settings summary {
        cursor: pointer;
        color: #31583b;
        font-weight: 800;
      }
      .workspace-destination {
        display: grid;
        gap: 0.45rem;
        margin-top: 0.65rem;
      }
      .workspace-dialog-backdrop {
        position: fixed;
        inset: 0;
        z-index: 1000;
        display: grid;
        place-items: center;
        padding: 1rem;
        background: rgba(21, 34, 28, 0.48);
      }
      .workspace-dialog {
        width: min(500px, 100%);
        border-radius: 12px;
        background: #fff;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
      }
      .workspace-dialog header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.15rem 1.3rem;
        border-bottom: 1px solid #e4e9e5;
      }
      .workspace-dialog h2 {
        margin: 0.2rem 0 0;
        font-size: 1.15rem;
      }
      .workspace-dialog-close {
        border: 0;
        background: transparent;
        color: #52616b;
        font-size: 1.5rem;
        cursor: pointer;
      }
      .workspace-dialog-body {
        display: grid;
        gap: 0.55rem;
        padding: 1.25rem 1.3rem;
      }
      .workspace-dialog-body small {
        color: #68747c;
        font-size: 0.72rem;
      }
      .workspace-dialog-error {
        color: #9c3f3f !important;
        font-weight: 700;
      }
      @media (max-width: 600px) {
        .preference-menu,
        .preference-menu.is-above {
          top: auto;
          bottom: 1rem;
        }
      }
    `,
    `
      .story-list,
      .story-card,
      .story-card p,
      .story-editor {
        min-width: 0;
        max-width: 100%;
      }
      .story-card p,
      .parent-story-comparison pre {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        word-break: break-word;
      }
      .story-editor {
        display: grid;
        gap: 0.75rem;
        margin: 1rem 0;
        padding: 1rem;
        border: 1px solid #dfe5e8;
        border-radius: 8px;
        background: #fbfdf9;
        overflow: hidden;
      }
      .story-editor.is-editing {
        border-color: #8fbd36;
        box-shadow: 0 0 0 2px #eaf3d7;
      }
      .story-editor-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.75rem;
      }
      .story-editor-header div {
        display: grid;
        gap: 0.2rem;
        min-width: 0;
      }
      .story-editor-header strong {
        color: #26352c;
      }
      .story-editor-header small {
        color: #68747c;
        font-size: 0.72rem;
        line-height: 1.4;
      }
      .story-editor-state {
        flex: none;
        padding: 0.25rem 0.5rem;
        border-radius: 999px;
        background: #eef2f4;
        color: #52616b;
        font-size: 0.66rem;
        font-weight: 800;
      }
      .story-editor.is-editing .story-editor-state {
        background: #e5f2d8;
        color: #31583b;
      }
      .parent-story-comparison {
        min-width: 0;
      }
      .parent-story-comparison pre {
        max-width: 100%;
        max-height: 240px;
        box-sizing: border-box;
        overflow: auto;
        margin: 0.55rem 0;
        padding: 0.75rem;
        border: 1px solid #dfe5e8;
        border-radius: 6px;
        background: #f8fafb;
      }
      .story-editor textarea[aria-label='Selected story'] {
        display: block;
        width: 100%;
        max-width: 100%;
        min-width: 0;
        box-sizing: border-box;
        min-height: 220px;
        max-height: 60vh;
        resize: vertical;
        overflow: auto;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        word-break: break-word;
        line-height: 1.55;
      }
      .story-editor textarea[readonly] {
        background: #f6f8f9;
        color: #52616b;
        cursor: default;
      }
      .story-editor textarea[aria-label='Selected story']:focus {
        outline: 2px solid #668b28;
        outline-offset: 2px;
      }
      .stage-panel {
        min-width: 0;
      }
      .story-list {
        overflow: hidden;
      }
      .story-editor-actions {
        margin-top: 0;
      }
      @media (max-width: 1000px) {
        .story-editor textarea[aria-label='Selected story'] {
          max-height: 50vh;
        }
      }
      @media (max-width: 600px) {
        .story-editor-header {
          display: grid;
        }
        .story-editor textarea[aria-label='Selected story'] {
          min-height: 180px;
          max-height: 45vh;
        }
        .parent-story-comparison pre {
          max-height: 180px;
        }
      }
    `,
  ],
})
export class CreativeStudioPage implements AfterViewInit, AfterViewChecked, OnDestroy {
  @ViewChild('promptMonaco') private promptMonaco?: ElementRef<HTMLDivElement>;
  private promptEditor: any = null;
  private promptEditorLoading = false;
  private updatingPromptEditor = false;
  private http = inject(HttpClient);
  private router = inject(Router);
  private changeDetector = inject(ChangeDetectorRef);
  stages: Array<{ key: Stage; label: string }> = [
    { key: 'IDEA', label: 'Idea' },
    { key: 'STORY', label: 'Story' },
    { key: 'PROMPT', label: 'Prompt' },
    { key: 'PRODUCTION_REVIEW', label: 'Production Review' },
    { key: 'ANALYSIS', label: 'Quality Analysis' },
    { key: 'REPAIR', label: 'Repair' },
    { key: 'RENDER', label: 'Render Preparation' },
    { key: 'VIDEO_QA', label: 'Video QA' },
  ];
  inputModes: Array<{ value: InputMode; label: string; help: string }> = [
    { value: 'IDEA', label: 'Just an Idea', help: 'A short concept is enough.' },
    { value: 'DETAILED_STORY', label: 'A Detailed Story', help: 'Use or refine a complete story.' },
    {
      value: 'EXISTING_PROMPT',
      label: 'An Existing Production Prompt',
      help: 'Skip story generation.',
    },
  ];
  durationPresets = [
    { value: '5', label: '5 seconds' },
    { value: '8', label: '8 seconds' },
    { value: '10', label: '10 seconds' },
    { value: '12', label: '12 seconds' },
    { value: '15', label: '15 seconds' },
    { value: '20', label: '20 seconds' },
    { value: '25', label: '25 seconds' },
    { value: '30', label: '30 seconds' },
  ];
  preferenceOptions = [
    'Strong visual opening',
    'Minimal dialogue',
    'Sound-off understandable',
    'Search and reveal',
    'Physical comedy',
    'Emotional discovery',
    'Visual surprise',
    'Loop-friendly ending',
    'Educational clarity',
  ];
  preferencePlacement: 'above' | 'below' = 'below';
  workspaceDialogOpen = false;
  workspaceName = '';
  workspaceNameError = '';
  workspaceCreating = false;
  renameDialogOpen = false;
  renameName = '';
  renameError = '';
  private renameTarget: SavedStoryRecord | null = null;
  confirmDialogOpen = false;
  confirmDialogTitle = '';
  confirmDialogMessage = '';
  private pendingConfirmation: (() => void) | null = null;
  characters: CharacterOption[] = [];
  workspaces: WorkspaceOption[] = [];
  savedStories: SavedStoryRecord[] = [];
  savedApprovals: any[] = [];
  savedStudioSessions: any[] = [];
  private savedBuildRecords: any[] = [];
  savedStoriesLoading = true;
  savedIndexLoadFailed = false;
  private savedIndexesPending = 4;
  savedStoryQuery = '';
  savedStoryFilter = 'ALL';
  savedStorySort = 'UPDATED';
  savedMenuRecordId = '';
  savedLibraryMessage = '';
  inputMode: InputMode = 'IDEA';
  mainCharacterId = '';
  workspacePath = '';
  durationPreset = '15';
  ideaCandidates: any[] = [];
  ideaBatches: any[] = [];
  ideaCandidateBusy = false;
  ideaBatchConsent = false;
  candidateCount = 3;
  storyProvider: 'DEEPSEEK' | 'OPENAI' = 'DEEPSEEK';
  preferences: string[] = [];
  preferencesOpen = false;
  preferenceQuery = '';
  storyMode: 'EXPLORE_DIFFERENT_STORIES' | 'IMPROVE_EXISTING_STORY' = 'EXPLORE_DIFFERENT_STORIES';
  lockedRequirements: string[] = ['PRESERVE_CORE_PREMISE'];
  storyQuality: any = null;
  storyReview: any = null;
  storyReviewHistory: any[] = [];
  storyReviewStatus = 'NOT_REVIEWED';
  selectedCandidateIdValue = '';
  reviewConsent = false;
  reviewBudget = 0.01;
  reviewBusy = false;
  reviewError = '';
  reviewedStoryFingerprints: Record<string, string> = {};
  freedomOptions = [
    { value: 'PRESERVE_CORE_PREMISE', label: 'Preserve Core Premise' },
    { value: 'PRESERVE_KEY_EVENTS', label: 'Preserve Key Events' },
    { value: 'PRESERVE_ENDING', label: 'Preserve Ending' },
  ];
  mismatchMessage = '';
  suggestedTitle = '';
  reviewDialogOpen = false;
  reviewDialogTab = '';
  activeJourney: Journey = 'NEW';
  newStoryOpen = true;
  storyModeTouched = false;
  newDraftSnapshot: any = null;
  private savedContextSnapshot: any = null;
  private draftBaseline: any = null;
  stage: Stage = 'IDEA';
  promptBudget = 0.01;
  idea = '';
  title = '';
  profile = 'AUTO';
  duration = 15;
  aspectRatio = '9:16';
  targetGenerator = 'SEEDANCE_2_0_MINI';
  constraints = '';
  budget = 0;
  storyConsent = false;
  promptConsent = false;
  busy = false;
  error = '';
  technicalError = '';
  readiness: any = null;
  candidates: StoryCandidate[] = [];
  selectedStory = '';
  storyEditing = false;
  storyRecordId = '';
  approvalRecordId = '';
  builderRecordId = '';
  builderResult: any = null;
  builderMigration: any = null;
  draftPrompt = '';
  savedPromptBaseline = '';
  savedPromptTargetSnapshot: any = null;
  contentId = '';
  promptVersionId = '';
  detailUrl = '/quality/detail';
  sessionId = '';
  restoredCharacterName = '';
  buildAttemptState = 'NOT_STARTED';
  buildAttemptDiagnostics: any = null;
  firstFrameDescription = '';
  explorationOpen = false;
  explorationBusy = false;
  explorationConsent = false;
  explorationBudget = 0.1;
  explorationReferenceId = '';
  explorationReferences: any[] = [];
  explorations: any[] = [];
  selectedExplorationId = '';
  explorationError = '';
  explorationNote = '';
  explorationDecisions = ['PROMISING_HOOK', 'NEEDS_VISUAL_REVISION', 'REJECT'];
  ideaDraftId = '';
  ideaDraftRevision = 0;
  savedIdeaDrafts: any[] = [];
  sourceTexts: Record<InputMode, string> = { IDEA: '', DETAILED_STORY: '', EXISTING_PROMPT: '' };
  generationDialogOpen = false;
  draftSaving = false;
  draftLoading = false;
  workspaceLoading = true;
  workspaceError = '';
  characterError = '';
  private editorEpoch = 0;
  private activeSourceMode: InputMode = 'IDEA';
  private readonly storageKey = 'pompom.creative-studio.v1';
  fixtureMode = false;
  constructor() {
    this.fixtureMode =
      new URLSearchParams(window.location.search).get('fixture') === 'story-review';
    this.restore();
    this.cancelStoryGeneration();
    this.draftBaseline = this.captureDraft();
    if (this.fixtureMode) this.loadStoryReviewFixture();
    this.loadCatalogues();
    this.loadSavedStories();
    this.loadSavedApprovals();
    this.loadSavedStudioSessions();
    this.loadIdeaDrafts();
    this.loadIdeaCandidates();
    if (this.sessionId && !this.ideaDraftId && this.storyRecordId)
      this.http
        .get<any>(`/api/v1/intelligence/workflow/studio-sessions/${this.sessionId}`)
        .subscribe({
          next: (s) => {
            if (!this.draftDirty) {
              this.restoreServer(s);
              this.changeDetector.markForCheck();
            }
          },
        });
    this.http.get<any>('/api/v1/intelligence/workflow/creative-role/readiness').subscribe({
      next: (r) => {
        this.readiness = r;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.readiness = null;
        this.changeDetector.markForCheck();
      },
    });
  }
  get selectedCharacterName() {
    return (
      this.characters.find((item) => item.id === this.mainCharacterId)?.name ||
      this.restoredCharacterName ||
      ''
    );
  }
  get selectedCharacter() {
    return this.characters.find((item) => item.id === this.mainCharacterId)?.raw || null;
  }
  get characterGuidance() {
    if (!this.mainCharacterId)
      return 'Selection may be deferred. Confirm a catalog identity before any applicable render gate.';
    const name = this.selectedCharacterName || 'Selected character';
    const raw = this.selectedCharacter || {};
    const status = String(raw.referenceStatus || raw.visualReferenceStatus || '').toUpperCase();
    const refs =
      raw.references || raw.referenceAssets || raw.visualReferences || raw.approvedReferences;
    const available = Array.isArray(refs) && refs.length > 0;
    if (status.includes('APPROVED') || status.includes('AVAILABLE'))
      return `${name} selected. An authoritative visual reference is available; approval remains a separate gate.`;
    if (available)
      return `${name} selected. Reference data exists, but an authoritative visual reference is not confirmed approved.`;
    return `${name} selected. No authoritative visual reference is confirmed.`;
  }
  private currentPromptTarget() {
    return {
      duration: this.duration,
      aspectRatio: this.aspectRatio,
      selectedGenerator: this.targetGenerator,
      contentProfile: this.profile,
      mainCharacter: this.selectedCharacterName || null,
      mainCharacterId: this.mainCharacterId || null,
    };
  }
  get promptDirty() {
    return Boolean(
      this.promptVersionId &&
      (this.draftPrompt !== this.savedPromptBaseline ||
        (this.savedPromptTargetSnapshot &&
          JSON.stringify(this.currentPromptTarget()) !==
            JSON.stringify(this.savedPromptTargetSnapshot))),
    );
  }
  get builderPromptTextMismatch() {
    return Boolean(
      this.builderResult?.prompt &&
      this.draftPrompt !== this.formatPromptForEditor(String(this.builderResult.prompt)),
    );
  }
  get builderMigrationRefreshAvailable() {
    return Boolean(
      this.builderMigration &&
      this.builderMigration.migrationVersion !==
        'openart-production-prompt-v2-legacy-migration-evidence-v7',
    );
  }
  get builderInputMismatch() {
    const plan = this.builderResult?.productionPlan;
    if (!plan) return false;
    const settings = plan.productionConstraints || {};
    return (
      this.builderPromptTextMismatch ||
      plan.builderContractVersion !== 'openart-production-prompt-v2' ||
      settings.duration == null ||
      !settings.aspectRatio ||
      !settings.generator ||
      !settings.contentProfile ||
      Number(settings.duration) !== Number(this.duration) ||
      String(settings.aspectRatio || '') !== this.aspectRatio ||
      String(settings.generator || settings.targetGenerator || '') !== this.targetGenerator ||
      String(settings.contentProfile || '') !== this.profile ||
      (Boolean(this.selectedCharacterName) &&
        String(settings.mainCharacter || plan.characterBindings?.[0]?.name || '') !==
          this.selectedCharacterName)
    );
  }
  get productionBeats(): any[] {
    const beats = this.builderResult?.productionPlan?.visualExecution?.beats;
    return Array.isArray(beats) ? beats : [];
  }
  get productionRisks(): any[] {
    const risks = this.builderResult?.productionPlan?.generatorRisks;
    return Array.isArray(risks) ? risks : risks ? [{ risk: String(risks) }] : [];
  }
  get productionCharacterBindings(): any[] {
    const bindings = this.builderResult?.productionPlan?.characterBindings;
    return Array.isArray(bindings) ? bindings : bindings ? [bindings] : [];
  }
  get productionProvenance(): [string, string][] {
    const values = this.builderResult?.productionPlan?.fieldProvenance || {};
    return Object.entries(values).map(([key, value]) => [key, String(value)]);
  }
  readableProductionValue(value: any) {
    return String(value ?? 'UNKNOWN')
      .replaceAll('_', ' ')
      .replace(/([a-z])([A-Z])/g, '$1 $2');
  }
  get storyRole() {
    if (this.inputMode === 'IDEA')
      return this.readiness?.roles?.find((role: any) => role.role === 'IDEA') || null;
    return (
      this.readiness?.storyProviders?.find((item: any) => item.provider === this.storyProvider) ||
      (this.storyProvider === 'DEEPSEEK'
        ? this.readiness?.roles?.find((role: any) => role.role === 'STORY')
        : null) ||
      null
    );
  }
  get generationConsent() {
    return this.inputMode === 'IDEA' ? this.ideaBatchConsent : this.storyConsent;
  }
  set generationConsent(value: boolean) {
    if (this.inputMode === 'IDEA') this.ideaBatchConsent = value;
    else this.storyConsent = value;
  }
  get generationProvider() {
    return this.inputMode === 'IDEA' ? 'OPENAI' : this.storyProvider;
  }
  get noIdeaApproved() {
    return (
      this.ideaCandidates.length > 0 &&
      !this.ideaCandidates.some((c) => this.eligibleIdeaCandidate(c))
    );
  }
  get ideaOverallStatus() {
    if (this.ideaCandidates.some(c => c.state === 'SELECTED' && this.eligibleIdeaCandidate(c))) return 'IDEA_SELECTED';
    return this.ideaCandidates.length && this.ideaCandidates.every(c => c.state === 'REJECTED' || c.evaluation?.status === 'REJECTED') ? 'NO_IDEA_APPROVED' : 'PENDING_EVIDENCE';
  }
  eligibleIdeaCandidate(c: any) {
    return (
      c.state !== 'REJECTED' &&
      c.sourceIdeaRevision === this.ideaDraftRevision &&
      c.evaluation?.eligible === true &&
      c.evaluation?.status === 'EVALUATED' &&
      c.evaluation?.gates?.length > 0 &&
      c.evaluation.gates.every((g: any) => !g.mandatory || g.status === 'PASS' || (g.status === 'NOT_APPLICABLE' && g.applicability?.policyExcluded === true))
    );
  }
  get storyModel() {
    return this.storyRole?.model || '';
  }
  get storyReady() {
    return Boolean(this.readiness?.enabled && this.storyRole?.configured);
  }
  get providerStatus() {
    return this.readiness?.liveVerified
      ? 'Verified'
      : this.storyReady
        ? 'Configured'
        : 'Unavailable';
  }
  get promptModel() {
    return this.readiness?.roles?.find((role: any) => role.role === 'BUILD_PROMPT')?.model || '';
  }
  get promptReady() {
    return Boolean(
      this.readiness?.enabled &&
      this.readiness?.roles?.find((role: any) => role.role === 'BUILD_PROMPT')?.configured,
    );
  }
  get reviewModel() {
    return this.readiness?.roles?.find((role: any) => role.role === 'STORY_REVIEW')?.model || '';
  }
  get stageIndex() {
    return this.stages.findIndex((item) => item.key === this.stage);
  }
  get ideaLooksDetailed() {
    return this.idea.trim().length > 280 || this.idea.split(/[.!?]+/).filter(Boolean).length >= 4;
  }
  get storyApprovalStatus() {
    if (this.activeJourney === 'NEW' && this.stage === 'IDEA') return 'NOT_STARTED';
    if (this.activeSavedStory) {
      if (this.savedApprovalVerified(this.activeSavedStory)) return 'APPROVED';
      return this.savedApprovalRecordsFor(this.activeSavedStory).length ||
        this.savedLifecycle(this.activeSavedStory) === 'IN_REVIEW'
        ? 'REVIEW_REQUIRED'
        : this.storyRecordId
          ? 'DRAFT'
          : 'NOT_STARTED';
    }
    return this.approvalRecordId ? 'APPROVED' : this.storyRecordId ? 'DRAFT' : 'NOT_STARTED';
  }
  get promptAcceptanceStatus() {
    if (this.activeJourney === 'NEW' && this.stage === 'IDEA') return 'NOT_STARTED';
    if (this.promptVersionId)
      return !this.storyRecordId || this.savedPromptVersionVerified ? 'SAVED' : 'RECOVERY_REQUIRED';
    if (this.builderRecordId || this.canonicalSavedPrompt) return 'DRAFT_BUILT';
    return 'NOT_STARTED';
  }
  get resumeAvailable() {
    return Boolean(
      (this.promptVersionId && (!this.storyRecordId || this.savedPromptVersionVerified)) ||
      this.builderRecordId ||
      this.canonicalSavedPrompt ||
      this.approvalRecordId ||
      (this.activeJourney !== 'NEW' && this.storyRecordId),
    );
  }
  get canonicalSavedPrompt() {
    if (!this.storyRecordId) return null;
    if (
      this.activeSavedStory
        ? !this.savedApprovalVerified(this.activeSavedStory)
        : !this.approvalRecordId
    )
      return null;
    const selected = this.candidates.find((item) => item.candidateId === this.selectedCandidateId);
    if (!selected) return null;
    const revision = `${this.selectedCandidateId}-revision-${this.storyFingerprint(selected.text.trim())}`;
    return (
      this.savedBuildRecords.find((row) => {
        const context = row.sourceRequest?.context || row.payload?.sourceRequest?.context || {};
        const result = row.result || row.payload?.result || {};
        const target = context.targetConfiguration || {};
        return (
          (row.role === 'BUILD_PROMPT' || result.role === 'BUILD_PROMPT') &&
          Boolean(String(result.prompt || '').trim()) &&
          Boolean(row.requestFingerprint) &&
          String(context.sourceStoryRecordId || '') === String(this.storyRecordId) &&
          String(context.storyRevisionId || '') === revision &&
          Number(target.duration) === Number(this.duration) &&
          String(target.aspectRatio || '') === this.aspectRatio &&
          String(target.selectedGenerator || '') === this.targetGenerator &&
          String(target.contentProfile || '') === this.profile &&
          String(target.mainCharacter || '') === String(this.selectedCharacterName || '')
        );
      }) || null
    );
  }
  get savedPromptVersionVerified() {
    const story = this.activeSavedStory;
    if (!story || !this.savedApprovalVerified(story) || !this.promptVersionId || !this.contentId)
      return false;
    const build = this.canonicalSavedPrompt;
    const session = this.storyStudioSession(story);
    return Boolean(
      build &&
      String(this.builderRecordId) === String(build.recordId || build.id) &&
      session &&
      String(session.builderRecordId) === String(this.builderRecordId) &&
      String(session.approvalRecordId) === String(this.approvalRecordId) &&
      String(session.selectedCandidateIdValue) === String(this.selectedCandidateId) &&
      String(session.contentId) === String(this.contentId) &&
      String(session.promptVersionId) === String(this.promptVersionId),
    );
  }
  get savedIndexesReady() {
    return !this.savedStoriesLoading && !this.savedIndexLoadFailed;
  }
  get resumeHeadline() {
    if (this.activeSavedStory && !this.savedApprovalVerified(this.activeSavedStory))
      return 'Story review required';
    return this.savedPromptVersionVerified || (!this.storyRecordId && this.promptVersionId)
      ? 'Saved prompt and quality workflow available'
      : this.builderRecordId || this.draftPrompt || this.canonicalSavedPrompt
        ? 'Saved production prompt available'
        : this.approvalRecordId
          ? 'Approved story available'
          : 'Saved story available';
  }
  get resumeDescription() {
    if (this.savedStoriesLoading)
      return 'Verifying the saved story, approval and prompt lineage before continuing.';
    if (this.savedIndexLoadFailed)
      return 'Saved workflow records could not be fully verified. Refresh before continuing.';
    if (this.activeSavedStory && !this.savedApprovalVerified(this.activeSavedStory))
      return 'Review the saved candidates and approve the exact story revision before continuing.';
    return this.savedPromptVersionVerified || (!this.storyRecordId && this.promptVersionId)
      ? 'Resume without rebuilding the prompt or restarting analysis.'
      : this.builderRecordId || this.draftPrompt || this.canonicalSavedPrompt
        ? 'Open the exact saved draft without another OpenAI request.'
        : 'Continue to Prompt without another story-generation request.';
  }
  get projectReviewStatus() {
    return this.activeSavedStory
      ? this.savedLifecycleLabel(this.activeSavedStory)
      : 'Not applicable';
  }
  get nextAction() {
    if (
      this.stage === 'STORY' &&
      this.activeSavedStory &&
      !this.savedApprovalVerified(this.activeSavedStory)
    )
      return 'Review Story';
    if (this.stage === 'IDEA') {
      if (this.activeJourney === 'RESUME' && this.promptVersionId)
        return 'Continue saved quality workflow';
      if (
        this.activeJourney === 'RESUME' &&
        (this.builderRecordId || this.draftPrompt || this.canonicalSavedPrompt)
      )
        return 'Open saved production prompt';
      if (
        this.activeJourney === 'SAVED' &&
        this.activeSavedStory &&
        !this.savedApprovalVerified(this.activeSavedStory)
      )
        return 'Review Story';
      if (this.activeJourney === 'RESUME' && this.approvalRecordId)
        return 'Continue approved story to Prompt';
      if (this.activeJourney === 'SAVED')
        return this.canonicalSavedPrompt
          ? 'Open saved production prompt'
          : this.approvalRecordId
            ? 'Continue approved story to Prompt'
            : 'Review Story';
      if (this.activeJourney === 'NEW')
        return this.inputMode === 'EXISTING_PROMPT'
          ? 'Save and review your production prompt.'
          : this.inputMode === 'DETAILED_STORY'
            ? 'Save and review your story.'
            : this.ideaCandidates.length
              ? 'Compare saved IDEA candidates and resolve admission evidence.'
              : 'Save your idea or explicitly authorize three IDEA candidates.';
      return 'Choose a workflow';
    }
    return this.stage === 'STORY'
      ? 'Select, edit and approve a story'
      : this.stage === 'PROMPT'
        ? this.builderMigration
          ? 'Review locally recovered saved prompt'
          : this.canonicalSavedPrompt
            ? 'Review saved production prompt'
            : 'Build a production prompt'
        : 'Open the quality workflow';
  }
  get savedPromptRecoveryRequired() {
    return (
      this.savedIndexesReady &&
      this.stage === 'PROMPT' &&
      this.activeJourney === 'RESUME' &&
      !!this.activeSavedStory &&
      this.savedApprovalVerified(this.activeSavedStory) &&
      !this.promptVersionId &&
      !this.builderRecordId &&
      !this.draftPrompt &&
      !this.canonicalSavedPrompt
    );
  }
  get activeSavedStory() {
    return (
      this.savedStories.find((item) => String(item.recordId) === String(this.storyRecordId)) || null
    );
  }
  get activeStudioSession() {
    if (!(
      this.storyRecordId ||
      this.approvalRecordId ||
      this.builderRecordId ||
      this.promptVersionId
    ))
      return null;
    return (
      this.savedStudioSessions
        .filter(
          (row) =>
            String(row.sessionId || '') === String(this.sessionId || '') &&
            String(row.title || '').trim(),
        )
        .sort(
          (a, b) =>
            (Date.parse(b.updatedAt || b.createdAt || '') || 0) -
            (Date.parse(a.updatedAt || a.createdAt || '') || 0),
        )[0] || null
    );
  }
  private savedContextValue(key: string) {
    const session = this.activeSavedStory
      ? this.storyStudioSession(this.activeSavedStory)
      : this.activeStudioSession;
    const context =
      this.activeSavedStory?.sourceContext ||
      this.activeSavedStory?.result?.sourceRequest?.context ||
      this.activeSavedStory?.result?.context ||
      {};
    const target = context.targetConfiguration || {};
    return (
      session?.[key] ?? context[key] ?? target[key] ?? this.activeSavedStory?.result?.[key] ?? null
    );
  }
  get activeContextTitle() {
    const migrated =
      this.builderMigration?.result?.productionPlan?.sourceIdentity?.projectTitle ||
      this.builderResult?.productionPlan?.sourceIdentity?.projectTitle;
    if (migrated) return String(migrated);
    return this.activeJourney === 'NEW'
      ? this.title || 'Not set'
      : this.activeSavedStory
        ? this.storyTitle(this.activeSavedStory)
        : this.activeStudioSession?.title || this.title || 'Not set';
  }
  get activeContextCharacter() {
    const id = String(this.savedContextValue('mainCharacterId') || '');
    const character = this.characters.find((item) => item.id === id)?.name;
    const migrated = this.productionCharacterBindings[0]?.name;
    const saved =
      this.savedContextValue('mainCharacter') ||
      this.savedContextValue('mainCharacterName') ||
      this.savedContextValue('targetConfiguration')?.mainCharacter ||
      character ||
      migrated;
    if (saved) return String(saved);
    return this.activeJourney === 'NEW'
      ? this.selectedCharacterName || 'Not selected / Let AI suggest'
      : 'Not recorded';
  }
  get activeContextProfile() {
    const saved =
      this.savedContextValue('contentProfile') ||
      this.savedContextValue('targetConfiguration')?.contentProfile ||
      this.savedContextValue('profile') ||
      this.builderMigration?.result?.productionPlan?.productionConstraints?.contentProfile ||
      this.builderResult?.productionPlan?.productionConstraints?.contentProfile;
    return String(saved || (this.activeJourney === 'NEW' ? this.profile : 'Not recorded'));
  }
  get activeContextDuration() {
    const saved =
      this.savedContextValue('duration') ||
      this.savedContextValue('targetConfiguration')?.duration ||
      this.builderMigration?.result?.productionPlan?.productionConstraints?.duration ||
      this.builderResult?.productionPlan?.productionConstraints?.duration;
    return Number(saved || (this.activeJourney === 'NEW' ? this.duration : 0));
  }
  get activeContextAspectRatio() {
    const saved =
      this.savedContextValue('aspectRatio') ||
      this.savedContextValue('targetConfiguration')?.aspectRatio ||
      this.builderMigration?.result?.productionPlan?.productionConstraints?.aspectRatio ||
      this.builderResult?.productionPlan?.productionConstraints?.aspectRatio;
    return String(saved || (this.activeJourney === 'NEW' ? this.aspectRatio : 'Not recorded'));
  }
  get filteredSavedStories() {
    const query = this.savedStoryQuery.trim().toLowerCase();
    const rows = this.savedStories.filter(
      (story) =>
        !this.savedIdeaDrafts.some(
          (draft) => String(draft.storyRecordId || '') === story.recordId,
        ) &&
        this.savedLifecycle(story) !== 'DELETED' &&
        (!query || `${this.storyTitle(story)} ${story.idea || ''}`.toLowerCase().includes(query)) &&
        (this.savedStoryFilter === 'ALL' || this.savedLifecycle(story) === this.savedStoryFilter),
    );
    return [...rows].sort(
      (a, b) =>
        (Date.parse((this.savedStorySort === 'UPDATED' ? b.updatedAt : b.createdAt) || '') || 0) -
        (Date.parse((this.savedStorySort === 'UPDATED' ? a.updatedAt : a.createdAt) || '') || 0),
    );
  }
  stageLabel(value: Stage) {
    return this.stages.find((item) => item.key === value)?.label || value;
  }
  stageStatus(value: Stage) {
    let state: string;
    if (value === 'IDEA')
      state =
        this.storyRecordId || this.promptVersionId
          ? 'Complete'
          : this.ideaDraftRevision
            ? 'Draft available'
            : 'Not started';
    else if (value === 'STORY')
      state =
        this.storyApprovalStatus === 'APPROVED'
          ? 'Complete'
          : this.storyRecordId
            ? 'Needs review'
            : 'Locked';
    else if (value === 'PROMPT')
      state =
        this.promptVersionId && (!this.storyRecordId || this.savedPromptVersionVerified)
          ? 'Complete'
          : this.canonicalSavedPrompt || this.builderRecordId
            ? 'Draft available'
            : this.approvalRecordId
              ? 'Not started'
              : 'Locked';
    else if (value === 'PRODUCTION_REVIEW') state = this.canVisit(value) ? 'Current' : 'Locked';
    else state = this.canVisit(value) ? 'Not started' : 'Locked';
    if (value !== this.stage) return state;
    if (state === 'Complete') return 'Current · Complete';
    if (state === 'Draft available') return 'Current · Draft available';
    if (state === 'Needs review') return 'Current · Needs review';
    return 'Current';
  }
  get savedEmptyMessage() {
    if (!this.allSavedProjectCount) return 'No saved projects yet';
    return this.savedStoryFilter === 'DRAFT'
      ? 'No drafts saved yet.'
      : this.savedStoryFilter === 'IN_REVIEW'
        ? 'No stories need review.'
        : this.savedStoryFilter === 'APPROVED'
          ? 'No approved stories found.'
          : this.savedStoryFilter === 'ARCHIVED'
            ? 'No archived projects found.'
            : 'No saved projects match this filter.';
  }
  hasStoryTextChanges() {
    const base =
      this.selectedCandidateId === 'ORIGINAL_SOURCE'
        ? this.idea
        : this.candidates.find((item) => item.candidateId === this.selectedCandidateId)?.text;
    return Boolean(
      this.storyRecordId &&
      base &&
      this.selectedStory.trim() &&
      this.selectedStory.trim() !== String(base).trim(),
    );
  }
  hasSelectedStoryEdits() {
    return this.storyEditing || this.hasStoryTextChanges();
  }
  canVisit(value: Stage) {
    const approved = this.storyRecordId
      ? Boolean(this.activeSavedStory && this.savedApprovalVerified(this.activeSavedStory))
      : Boolean(this.approvalRecordId);
    return (
      value === 'IDEA' ||
      (value === 'STORY' && this.candidates.length > 0) ||
      (value === 'PROMPT' && approved) ||
      (value === 'PRODUCTION_REVIEW' &&
        !!this.promptVersionId &&
        (!this.storyRecordId || this.savedPromptVersionVerified))
    );
  }
  stageAvailabilityReason(value: Stage) {
    if (value === 'STORY')
      return 'Save and continue a detailed story, generate alternatives or reopen saved work.';
    if (value === 'PROMPT') return 'Approve the exact saved story revision first.';
    if (value === 'PRODUCTION_REVIEW') return 'Save the production prompt version first.';
    if (value === 'ANALYSIS')
      return 'Complete Production Review from the saved prompt workspace first.';
    if (value === 'REPAIR') return 'Complete Quality Analysis and persist its findings first.';
    if (value === 'RENDER') return 'Complete analysis and any required repair evidence first.';
    if (value === 'VIDEO_QA')
      return 'A rendered video and its persisted evidence are required first.';
    return 'This stage is not available yet.';
  }
  goTo(value: Stage) {
    if (this.canVisit(value)) this.stage = value;
  }
  private captureDraft() {
    return {
      originIdeaDraftId: this.originIdeaDraftId,
      originIdeaRevision: this.originIdeaRevision,
      revisionParentId: this.revisionParentId,
      firstFrameDescription: this.firstFrameDescription,
      idea: this.idea,
      sourceTexts: { ...this.sourceTexts, [this.inputMode]: this.idea },
      durationPreset: this.durationPreset,
      targetGenerator: this.targetGenerator,
      title: this.title,
      inputMode: this.inputMode,
      storyMode: this.storyMode,
      storyModeTouched: this.storyModeTouched,
      lockedRequirements: [...this.lockedRequirements],
      preferences: [...this.preferences],
      workspacePath: this.workspacePath,
      mainCharacterId: this.mainCharacterId,
      profile: this.profile,
      duration: this.duration,
      aspectRatio: this.aspectRatio,
      candidateCount: this.candidateCount,
      storyProvider: this.storyProvider,
    };
  }
  get draftDirty() {
    return (
      JSON.stringify(this.captureDraft()) !==
      JSON.stringify(this.draftBaseline || this.captureDraft())
    );
  }
  private preserveNewDraft() {
    if ((this.activeJourney === 'NEW' || !this.storyRecordId) && this.draftDirty)
      this.newDraftSnapshot = this.captureDraft();
  }
  private restoreNewDraft() {
    if (!this.newDraftSnapshot) return;
    Object.assign(this, this.newDraftSnapshot);
    this.draftBaseline = this.captureDraft();
  }
  private captureSavedContext() {
    return {
      storyRecordId: this.storyRecordId,
      approvalRecordId: this.approvalRecordId,
      builderRecordId: this.builderRecordId,
      builderResult: this.builderResult,
      builderMigration: this.builderMigration,
      buildAttemptState: this.buildAttemptState,
      buildAttemptDiagnostics: this.buildAttemptDiagnostics,
      draftPrompt: this.draftPrompt,
      contentId: this.contentId,
      promptVersionId: this.promptVersionId,
      detailUrl: this.detailUrl,
      candidates: this.candidates,
      selectedStory: this.selectedStory,
      selectedCandidateIdValue: this.selectedCandidateIdValue,
      storyQuality: this.storyQuality,
      storyReview: this.storyReview,
      storyReviewHistory: this.storyReviewHistory,
      storyReviewStatus: this.storyReviewStatus,
      stage: this.stage,
      targetGenerator: this.targetGenerator,
    };
  }
  private clearSavedContext() {
    this.ideaCandidates = [];
    this.ideaBatches = [];
    this.restoredCharacterName = '';
    this.storyRecordId = '';
    this.approvalRecordId = '';
    this.builderRecordId = '';
    this.builderResult = null;
    this.builderMigration = null;
    this.buildAttemptState = 'NOT_STARTED';
    this.buildAttemptDiagnostics = null;
    this.draftPrompt = '';
    this.contentId = '';
    this.promptVersionId = '';
    this.detailUrl = '/quality/detail';
    this.candidates = [];
    this.selectedStory = '';
    this.selectedCandidateIdValue = '';
    this.storyQuality = null;
    this.storyReview = null;
    this.storyReviewHistory = [];
    this.storyReviewStatus = 'NOT_REVIEWED';
    this.stage = 'IDEA';
  }
  private restoreSavedContext(snapshot: any) {
    if (!snapshot) return;
    Object.assign(this, snapshot);
    this.hydrateSavedStoryAssessment();
  }
  selectJourney(value: Journey) {
    this.editorEpoch++;
    this.cancelStoryGeneration();
    if (value === 'NEW') {
      if (this.activeJourney !== 'NEW') {
        this.inputMode = 'IDEA';
        this.firstFrameDescription = '';
        this.explorationOpen = false;
        this.storyMode = 'EXPLORE_DIFFERENT_STORIES';
        this.storyModeTouched = false;
        this.profile = 'AUTO';
        this.duration = 15;
        this.durationPreset = '15';
        this.aspectRatio = '9:16';
        this.candidateCount = 3;
        this.storyProvider = 'DEEPSEEK';
        this.lockedRequirements = ['PRESERVE_CORE_PREMISE'];
        this.constraints = '';
        this.ideaDraftId = '';
        this.ideaDraftRevision = 0;
        this.sessionId = crypto.randomUUID();
        this.workspacePath = '';
        this.mainCharacterId = '';
        this.restoredCharacterName = '';
        this.preferences = [];
        this.idea = '';
        this.title = '';
        this.sourceTexts = { IDEA: '', DETAILED_STORY: '', EXISTING_PROMPT: '' };
      }
      if (this.storyRecordId) this.savedContextSnapshot = this.captureSavedContext();
      if (this.activeJourney === 'NEW') this.preserveNewDraft();
      this.restoreNewDraft();
      this.clearSavedContext();
      this.activeJourney = 'NEW';
      this.newStoryOpen = true;
      this.activeSourceMode = this.inputMode;
      this.draftBaseline = this.captureDraft();
    } else {
      this.preserveNewDraft();
      if (value === 'SAVED' && this.savedContextSnapshot)
        this.restoreSavedContext(this.savedContextSnapshot);
      this.activeJourney = value;
      this.newStoryOpen = false;
      this.stage = value === 'SAVED' ? 'STORY' : this.stage === 'IDEA' ? 'IDEA' : this.stage;
    }
    this.error = '';
    this.technicalError = '';
    this.persist();
  }
  collapseNewStory() {
    if (this.draftSaving) return;
    if (this.draftDirty) {
      this.askConfirmation(
        'Close this editor?',
        'Unsaved browser changes will be retained; the saved project will not be deleted.',
        () => this.collapseNewStoryNow(),
      );
      return;
    }
    this.collapseNewStoryNow();
  }
  private collapseNewStoryNow() {
    this.editorEpoch++;
    this.cancelStoryGeneration();
    this.preserveNewDraft();
    this.newStoryOpen = false;
    this.persist();
    this.changeDetector.markForCheck();
  }

  onStoryModeChange() {
    this.storyModeTouched = true;
    if (this.storyMode === 'EXPLORE_DIFFERENT_STORIES' && this.inputMode === 'IDEA')
      this.lockedRequirements = this.lockedRequirements.filter(
        (item) => item === 'PRESERVE_CORE_PREMISE',
      );
    this.persist();
  }
  requestStories() {
    if (
      this.busy ||
      !this.generationDialogOpen ||
      !this.idea.trim() ||
      !this.generationConsent ||
      !Number.isFinite(Number(this.budget)) ||
      Number(this.budget) <= 0 ||
      !this.storyReady ||
      this.inputMode === 'EXISTING_PROMPT'
    )
      return;
    if (!this.mainCharacterId) {
      this.error = 'Select a registered Pompom Hills character before requesting story generation.';
      return;
    }
    if (!this.workspacePath) {
      this.generationDialogOpen = false;
      this.error = 'Select a workspace before requesting story generation.';
      return;
    }
    if (this.inputMode === 'IDEA' && (!this.ideaDraftId || this.draftDirty)) {
      this.error = 'Save the exact IDEA draft before authorizing generation.';
      return;
    }
    this.generationDialogOpen = false;
    this.activeJourney = 'NEW';
    this.checkMismatch();
    this.runStoryRole();
  }
  private savedIndexLoaded(failed = false) {
    this.savedIndexesPending = Math.max(0, this.savedIndexesPending - 1);
    this.savedIndexLoadFailed = this.savedIndexLoadFailed || failed;
    this.savedStoriesLoading = this.savedIndexesPending > 0;
    if (!this.savedStoriesLoading && this.savedIndexLoadFailed)
      this.savedLibraryMessage =
        'Saved project details could not be fully verified. Refresh before continuing this project.';
  }
  private loadSavedStories() {
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').subscribe({
      next: (rows) => {
        const records = rows || [];
        this.savedBuildRecords = records.filter(
          (row) =>
            row.role === 'BUILD_PROMPT' ||
            row.result?.role === 'BUILD_PROMPT' ||
            row.payload?.role === 'BUILD_PROMPT',
        );
        this.savedStories = records
          .filter(
            (row) =>
              row.role === 'STORY' || row.result?.role === 'STORY' || row.payload?.role === 'STORY',
          )
          .map((row) => ({
            recordId: String(row.recordId || row.id),
            title: row.title,
            createdAt: row.createdAt || row.created_at,
            updatedAt: row.lifecycleChangedAt || row.createdAt || row.created_at,
            idea: row.text || row.idea || row.sourceRequest?.text || row.payload?.text || '',
            sourceType:
              row.sourceType ||
              row.sourceRequest?.context?.inputMode ||
              row.sourceRequest?.context?.sourceType ||
              row.payload?.sourceType ||
              'STORY',
            revisionId:
              row.result?.revisionId ||
              row.payload?.result?.revisionId ||
              row.payload?.revisionId ||
              row.revisionId,
            sourceRecordId:
              row.sourceRecordId ||
              row.result?.parentStoryRecordId ||
              row.sourceRequest?.context?.parentStoryRecordId ||
              row.sourceRequest?.context?.sourceStoryRecordId,
            candidateCount: Array.isArray(
              row.result?.alternatives ||
                row.payload?.result?.alternatives ||
                row.result?.candidates,
            )
              ? (
                  row.result?.alternatives ||
                  row.payload?.result?.alternatives ||
                  row.result?.candidates
                ).length
              : undefined,
            workspacePath:
              row.sourceRequest?.context?.workspacePath ||
              row.payload?.sourceRequest?.context?.workspacePath,
            contentId:
              row.sourceRequest?.context?.contentId ||
              row.payload?.sourceRequest?.context?.contentId,
            sourceContext: row.sourceRequest?.context || row.payload?.sourceRequest?.context || {},
            lifecycleStatus: row.lifecycleStatus || 'DRAFT',
            result: row.result || row.payload?.result || row,
          }))
          .filter((row) => this.storyCandidates(row).length > 0); // P0 fix: if storyRecordId exists but is not found in backend saved stories,
        // the localStorage state is stale (e.g., database was reset) and must be cleared.
        const hasStoryRecord = !!this.storyRecordId;
        const recordExistsInBackend =
          hasStoryRecord && this.savedStories.some((s) => s.recordId === this.storyRecordId);
        if (hasStoryRecord && !recordExistsInBackend && this.candidates?.length > 0) {
          this.storyRecordId = '';
          this.approvalRecordId = '';
          this.candidates = [];
          this.selectedStory = '';
          this.selectedCandidateIdValue = '';
          this.storyQuality = null;
          this.storyReview = null;
          this.storyReviewHistory = [];
          this.storyReviewStatus = 'NOT_REVIEWED';
          this.stage = 'IDEA';
          this.persistLocal();
        }
        if (
          !this.savedStories.length &&
          !this.savedBuildRecords.length &&
          !this.storyRecordId &&
          !this.promptVersionId
        ) {
          this.activeJourney = 'NEW';
          this.newStoryOpen = true;
        }
        this.hydrateSavedStoryAssessment();
        const authoritative = this.savedStories.find(
          (row) => String(row.recordId) === String(this.storyRecordId),
        );
        if (authoritative) this.useSavedStory(authoritative);
        this.savedIndexLoaded();
        if (this.storyRecordId) this.loadSavedBuilder();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.savedIndexLoaded(true);
        this.changeDetector.markForCheck();
      },
    });
  }
  private hydrateSavedStoryAssessment() {
    const story = this.activeSavedStory;
    if (!story?.result?.storyQuality?.candidates || !this.candidates.length) return;
    const saved = this.storyCandidates(story);
    // The quality array belongs to this immutable record's alternatives in their original order.
    // Session IDs alone cannot authorize attaching evidence to edited text or another revision.
    if (
      saved.length !== this.candidates.length ||
      !saved.every((item: any, i: number) => {
        const id =
          typeof item === 'string'
            ? `${story.recordId}-candidate-${i + 1}`
            : item.candidateId && item.candidateId !== 'None' && item.candidateId !== 'null'
              ? item.candidateId
              : `${story.recordId}-candidate-${i + 1}`;
        const text =
          typeof item === 'string' ? item : item.text || item.description || JSON.stringify(item);
        return this.candidates[i].candidateId === id && this.candidates[i].text === text;
      })
    )
      return;
    this.storyQuality = story.result.storyQuality;
    this.candidates = this.candidates.map((candidate, i) => ({
      ...candidate,
      assessment: this.storyQuality.candidates[i]?.assessment,
    }));
    this.reconcileStoryComparison();
    this.persistLocal();
  }
  private loadSavedApprovals() {
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').subscribe({
      next: (rows) => {
        this.savedApprovals = rows || [];
        this.savedIndexLoaded();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.savedApprovals = [];
        this.savedIndexLoaded(true);
        this.changeDetector.markForCheck();
      },
    });
  }
  private loadSavedStudioSessions() {
    this.http
      .get<any[]>('/api/v1/intelligence/workflow/records?kind=CREATIVE_STUDIO_SESSION')
      .subscribe({
        next: (rows) => {
          this.savedStudioSessions = rows || [];
          this.savedIndexLoaded();
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.savedStudioSessions = [];
          this.savedIndexLoaded(true);
          this.changeDetector.markForCheck();
        },
      });
  }
  private loadSavedBuilder() {
    const storyId = String(this.storyRecordId || '');
    const candidateId = String(this.selectedCandidateId || '');
    const selectedText = this.selectedStory.trim();
    if (!storyId || !candidateId || !selectedText) return;
    const revision = `${candidateId}-revision-${this.storyFingerprint(selectedText)}`;
    const rows = this.savedBuildRecords;
    {
      if (
        String(this.storyRecordId) !== storyId ||
        String(this.selectedCandidateId) !== candidateId ||
        this.selectedStory.trim() !== selectedText
      )
        return;
      const lineage = (rows || [])
        .filter((row) => {
          const context = row.sourceRequest?.context || row.payload?.sourceRequest?.context || {};
          const result = row.result || row.payload?.result || {};
          return (
            String(context.sourceStoryRecordId || '') === storyId &&
            String(context.storyRevisionId || '') === revision &&
            Boolean(String(result.prompt || '').trim())
          );
        })
        .sort(
          (a, b) =>
            (Date.parse(b.createdAt || b.created_at || '') || 0) -
            (Date.parse(a.createdAt || a.created_at || '') || 0),
        )[0];
      const lineageContext =
        lineage?.sourceRequest?.context || lineage?.payload?.sourceRequest?.context || {};
      const savedTarget = lineageContext.targetConfiguration || {};
      if (lineage && !this.draftPrompt) {
        if (savedTarget.duration != null) this.duration = Number(savedTarget.duration);
        if (savedTarget.aspectRatio) this.aspectRatio = String(savedTarget.aspectRatio);
        if (savedTarget.selectedGenerator)
          this.targetGenerator = String(savedTarget.selectedGenerator);
        if (savedTarget.contentProfile) this.profile = String(savedTarget.contentProfile);
        if (savedTarget.mainCharacter)
          this.restoredCharacterName = String(savedTarget.mainCharacter);
      }
      const matches = (rows || []).filter((row) => {
        const context = row.sourceRequest?.context || row.payload?.sourceRequest?.context || {};
        const target = context.targetConfiguration || {};
        const result = row.result || row.payload?.result || {};
        return (
          (row.role === 'BUILD_PROMPT' || result.role === 'BUILD_PROMPT') &&
          Boolean(String(result.prompt || '').trim()) &&
          Boolean(row.requestFingerprint) &&
          String(context.sourceStoryRecordId || '') === storyId &&
          String(context.storyRevisionId || '') === revision &&
          Number(target.duration) === Number(this.duration) &&
          String(target.aspectRatio || '') === this.aspectRatio &&
          String(target.selectedGenerator || '') === this.targetGenerator &&
          String(target.contentProfile || '') === this.profile &&
          String(target.mainCharacter || '') === String(this.selectedCharacterName || '')
        );
      });
      const match = matches[0];
      const failed = (rows || []).find((row) => {
        const context = row.sourceRequest?.context || row.payload?.sourceRequest?.context || {};
        return (
          (row.attemptState === 'FAILED' || row.attemptState === 'PROVIDER_RESULT_REJECTED') &&
          String(context.sourceStoryRecordId || '') === storyId &&
          String(context.storyRevisionId || '') === revision
        );
      });
      if (
        match &&
        (!this.builderRecordId ||
          String(this.builderRecordId) === String(match.recordId || match.id))
      ) {
        const result = match.result || match.payload?.result;
        const savedText = result.productionPlan?.promptTextEdited
          ? String(result.prompt)
          : this.formatPromptForEditor(result.prompt);
        const hasUnsavedEdits = Boolean(
          this.draftPrompt && this.draftPrompt !== this.savedPromptBaseline,
        );
        this.builderRecordId = String(match.recordId || match.id);
        this.builderResult = result;
        if (!hasUnsavedEdits) this.draftPrompt = savedText;
        this.savedPromptBaseline = savedText;
        this.savedPromptTargetSnapshot = this.currentPromptTarget();
        this.buildAttemptState = 'REUSED_SAVED_RESULT';
        this.buildAttemptDiagnostics = match.attemptDiagnostics || {
          calls: 0,
          reused: true,
          persisted: true,
        };
        this.persistLocal();
        this.changeDetector.markForCheck();
      } else if (!match && failed && !this.builderRecordId && !this.draftPrompt) {
        const recovered = this.recoverRejectedBuildPrompt(failed);
        if (recovered) {
          const recoveredTarget =
            failed.sourceRequest?.context?.targetConfiguration ||
            failed.payload?.sourceRequest?.context?.targetConfiguration ||
            {};
          if (recoveredTarget.duration != null) this.duration = Number(recoveredTarget.duration);
          if (recoveredTarget.aspectRatio) this.aspectRatio = String(recoveredTarget.aspectRatio);
          if (recoveredTarget.selectedGenerator)
            this.targetGenerator = String(recoveredTarget.selectedGenerator);
          if (recoveredTarget.contentProfile) this.profile = String(recoveredTarget.contentProfile);
          this.builderRecordId = String(failed.recordId || failed.id);
          this.builderResult = recovered.result;
          this.draftPrompt = recovered.prompt;
          this.savedPromptBaseline = recovered.prompt;
          this.savedPromptTargetSnapshot = this.currentPromptTarget();
          this.buildAttemptState = 'RECOVERED_REJECTED_PROVIDER_RESPONSE';
          this.buildAttemptDiagnostics = {
            ...(failed.attemptDiagnostics || {}),
            calls: failed.calls || 1,
            persisted: true,
            recoveredFrom: String(failed.recordId || failed.id),
            providerCallsThisOperation: 0,
          };
          this.error = '';
          this.persistLocal();
        } else {
          this.buildAttemptState = 'PREVIOUS_ATTEMPT_FAILED';
          this.buildAttemptDiagnostics = failed.attemptDiagnostics || null;
          this.technicalError = String(failed.attemptDiagnostics?.error || '');
          this.error =
            'A previous prompt build failed. The saved story is preserved; retry requires explicit authorization.';
        }
        this.changeDetector.markForCheck();
      }
    }
  }
  private recoverRejectedBuildPrompt(record: any) {
    const raw = String(
      record?.rejectedProviderResponse || record?.payload?.rejectedProviderResponse || '',
    );
    if (!raw.trim()) return null;
    try {
      const response = JSON.parse(raw);
      const prompt = response?.prompt;
      if (!prompt || typeof prompt !== 'object' || Array.isArray(prompt)) return null;
      const sections = Object.entries(prompt).map(
        ([heading, value]) =>
          `${heading}\n${typeof value === 'string' ? value : JSON.stringify(value, null, 2)}`,
      );
      const text = sections.join('\n\n').trim();
      if (!text) return null;
      const containsUnsupportedMirror = /\bmirror\b/i.test(JSON.stringify(prompt));
      return {
        prompt: text,
        result: {
          prompt: text,
          productionPlan: {
            ...(response?.productionPlan || {}),
            recovery: {
              status: 'RECOVERED_REJECTED_PROVIDER_RESPONSE',
              source: 'SAVED_PROVIDER_RESPONSE',
              originalRecordId: String(record.recordId || record.id),
              missingEvidence: [
                'Explicit camera direction was not recovered as a contract field.',
                'First-frame and object-position continuity remain unverified.',
              ],
              storyFidelity: containsUnsupportedMirror
                ? {
                    status: 'STORY_FIDELITY_FAIL',
                    detail:
                      'The saved provider response introduces a mirror that is absent from the approved STORY. Remove it in this draft before saving if it is unsupported.',
                  }
                : {
                    status: 'UNKNOWN',
                    detail: 'No automatic story-fidelity conclusion was recovered.',
                  },
            },
          },
        },
      };
    } catch {
      return null;
    }
  }
  onPromptTargetGeneratorChange() {
    this.persist();
    this.loadSavedBuilder();
  }
  storyCandidates(story: SavedStoryRecord): any[] {
    return story.result?.alternatives || story.result?.candidates || story.result?.stories || [];
  }
  private studioSessionMatchesStory(story: SavedStoryRecord, session: any) {
    const context = story.sourceContext || story.result?.sourceRequest?.context || {};
    const target = context.targetConfiguration || {};
    return (
      String(session?.storyRecordId || '') === String(story.recordId) &&
      (!context.mainCharacterId ||
        String(session?.mainCharacterId || '') === String(context.mainCharacterId)) &&
      (!target.contentProfile || String(session?.profile || '') === String(target.contentProfile))
    );
  }
  storyStudioSession(story: SavedStoryRecord) {
    return (
      this.savedStudioSessions
        .filter((row) => this.studioSessionMatchesStory(story, row))
        .sort(
          (a, b) =>
            (Date.parse(b.updatedAt || b.createdAt || '') || 0) -
            (Date.parse(a.updatedAt || a.createdAt || '') || 0),
        )[0] || null
    );
  }
  private hasSharedSession(sessionId: string) {
    const storyIds = new Set(
      this.savedStudioSessions
        .filter((row) => String(row.sessionId || '') === String(sessionId))
        .map((row) => String(row.storyRecordId || ''))
        .filter(Boolean),
    );
    return storyIds.size > 1;
  }
  storyTitle(story: SavedStoryRecord) {
    const context =
      story.sourceContext || story.result?.sourceRequest?.context || story.result?.context || {};
    const candidates = this.storyCandidates(story);
    const candidateTitle = Array.isArray(candidates)
      ? candidates.find((item: any) => typeof item !== 'string' && item?.title)?.title
      : '';
    return String(
      candidateTitle ||
        story.title ||
        story.result?.title ||
        story.result?.storyTitle ||
        story.result?.sourceTitle ||
        context.title ||
        context.videoTitle ||
        context.contentTitle ||
        'Untitled story session',
    ).trim();
  }
  storySessionLabel(story: SavedStoryRecord) {
    if (story.sourceType === 'OPERATOR') return 'Operator-supplied story';
    const parent =
      story.sourceRecordId ||
      story.result?.parentStoryRecordId ||
      story.sourceContext?.parentStoryRecordId;
    if (parent) return `Edited revision · parent ${String(parent).slice(0, 8)}`;
    const at = story.createdAt ? new Date(story.createdAt) : null;
    return `Generation session${at && !Number.isNaN(at.valueOf()) ? ` · ${at.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}` : ''}`;
  }
  storyPreview(story: SavedStoryRecord) {
    const first = this.storyCandidates(story)[0];
    return typeof first === 'string'
      ? first
      : first?.text || first?.description || 'Saved story alternatives ready to review.';
  }
  storyDate(story: SavedStoryRecord) {
    const at = story.updatedAt || story.createdAt;
    return at ? new Date(at).toLocaleString() : 'Previously generated';
  }
  storySource(story: SavedStoryRecord) {
    return story.sourceType === 'DETAILED_STORY'
      ? 'Detailed story'
      : story.sourceType === 'IDEA'
        ? 'Generated idea'
        : 'Saved story';
  }
  storyRevision(story: SavedStoryRecord) {
    return story.revisionId ? `Revision ${story.revisionId}` : 'Generation session';
  }
  savedApprovalRecordsFor(story: SavedStoryRecord) {
    return this.savedApprovals
      .filter(
        (item) =>
          String(item.storyRecordId || item.payload?.storyRecordId) === String(story.recordId),
      )
      .sort(
        (a, b) =>
          (Date.parse(b.approvedAt || b.createdAt || '') || 0) -
          (Date.parse(a.approvedAt || a.createdAt || '') || 0),
      );
  }
  private approvalMatchesCandidate(story: SavedStoryRecord, approval: any) {
    const candidateId = String(
      approval?.candidateId || approval?.payload?.candidateId || '',
    ).trim();
    const revisionId = String(approval?.revisionId || approval?.payload?.revisionId || '').trim();
    const fingerprint = String(
      approval?.contentFingerprint || approval?.payload?.contentFingerprint || '',
    ).trim();
    const approvedText = String(
      approval?.approvedText || approval?.payload?.approvedText || '',
    ).trim();
    if (!candidateId || !revisionId || !fingerprint || !approvedText) return false;
    return this.storyCandidates(story).some((item: any, i: number) => {
      const id =
        typeof item === 'string'
          ? `${story.recordId}-candidate-${i + 1}`
          : String(item.candidateId || '');
      const text = typeof item === 'string' ? item : String(item.text || item.description || '');
      const hash = this.storyFingerprint(text.trim());
      return (
        id === candidateId &&
        text.trim() === approvedText &&
        fingerprint === hash &&
        revisionId === `${id}-revision-${hash}`
      );
    });
  }
  savedApprovalVerified(story: SavedStoryRecord) {
    return this.savedApprovalRecordsFor(story).some((item) =>
      this.approvalMatchesCandidate(story, item),
    );
  }
  savedLifecycle(story: SavedStoryRecord) {
    const status = String((story as any).lifecycleStatus || 'DRAFT').toUpperCase();
    const approvals = this.savedApprovalRecordsFor(story);
    const verified = this.savedApprovalVerified(story);
    if (status === 'ARCHIVED' || status === 'DELETED' || status === 'IN_REVIEW') return status;
    if (verified) return 'APPROVED';
    return status === 'APPROVED' || (status === 'DRAFT' && approvals.length > 0)
      ? 'IN_REVIEW'
      : status;
  }
  savedLifecycleLabel(story: SavedStoryRecord) {
    const status = this.savedLifecycle(story);
    return status === 'IN_REVIEW' ? 'In review' : status.charAt(0) + status.slice(1).toLowerCase();
  }
  savedCheckpoint(story: SavedStoryRecord) {
    const status = this.savedLifecycle(story);
    if (status === 'ARCHIVED') return 'Archived';
    if (status === 'APPROVED' && this.savedBuildForStory(story)) {
      const session = this.storyStudioSession(story);
      return session?.promptVersionId &&
        String(session.builderRecordId) ===
          String(this.savedBuildForStory(story)?.recordId || this.savedBuildForStory(story)?.id)
        ? 'Production review'
        : 'Production prompt';
    }
    if (status === 'APPROVED') return 'Prompt step';
    if (
      this.savedBuildRecords.some(
        (row) =>
          String(
            (row.sourceRequest?.context || row.payload?.sourceRequest?.context || {})
              .sourceStoryRecordId || '',
          ) === String(story.recordId),
      )
    )
      return 'Prompt draft · review lineage';
    return status === 'DRAFT' ? 'Story draft' : 'Story review';
  }
  private savedBuildForStory(story: SavedStoryRecord) {
    const approval = this.savedApprovalRecordsFor(story).find((row) =>
      this.approvalMatchesCandidate(story, row),
    );
    if (!approval) return null;
    const candidateId = String(approval.candidateId || approval.payload?.candidateId);
    const revisionId = String(approval.revisionId || approval.payload?.revisionId);
    return (
      this.savedBuildRecords.find((row) => {
        const context = row.sourceRequest?.context || row.payload?.sourceRequest?.context || {};
        const result = row.result || row.payload?.result || {};
        const target = context.targetConfiguration || {};
        return (
          Boolean(row.requestFingerprint) &&
          Boolean(String(result.prompt || '').trim()) &&
          String(context.sourceStoryRecordId || '') === String(story.recordId) &&
          String(context.candidateId || candidateId) === candidateId &&
          String(context.storyRevisionId || '') === revisionId &&
          revisionId.startsWith(`${candidateId}-revision-`) &&
          Number(target.duration) > 0 &&
          Boolean(target.aspectRatio) &&
          Boolean(target.selectedGenerator) &&
          Boolean(target.contentProfile)
        );
      }) || null
    );
  }
  savedPrimaryAction(story: SavedStoryRecord) {
    return this.savedLifecycle(story) === 'ARCHIVED'
      ? 'Restore'
      : this.savedCheckpoint(story) === 'Production review'
        ? 'Open Production Review'
        : this.savedCheckpoint(story) === 'Production prompt'
          ? 'Open Prompt'
          : this.savedLifecycle(story) === 'APPROVED'
            ? 'Continue to Prompt'
            : 'Review Story';
  }
  canDeleteSavedStory(story: SavedStoryRecord) {
    return this.savedLifecycle(story) === 'DRAFT' && !this.savedApprovalFor(story);
  }
  toggleSavedMenu(recordId: string) {
    this.savedMenuRecordId = this.savedMenuRecordId === recordId ? '' : recordId;
  }
  openSavedProject(story: SavedStoryRecord) {
    if (this.savedLifecycle(story) === 'ARCHIVED') {
      this.restoreSavedStory(story);
      return;
    }
    this.useSavedStory(story);
    if (this.approvalRecordId) this.continueApprovedStory();
  }
  reviewSavedStory() {
    this.activeJourney = 'SAVED';
    this.stage = 'STORY';
    this.error = '';
    this.persistLocal();
    this.changeDetector.markForCheck();
  }
  renameSavedStory(story: SavedStoryRecord) {
    this.renameTarget = story;
    this.renameName = this.storyTitle(story);
    this.renameError = '';
    this.renameDialogOpen = true;
    setTimeout(() => document.getElementById('rename-project-name')?.focus(), 0);
  }
  submitRename() {
    const story = this.renameTarget;
    const name = this.renameName.trim();
    if (!story) return;
    if (!name) {
      this.renameError = 'Enter a project name.';
      return;
    }
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${story.recordId}/lifecycle`, {
        status: this.savedLifecycle(story),
        title: name,
        reason: `Rename: ${name}`,
      })
      .subscribe({
        next: (response) => {
          story.title = name;
          story.updatedAt = response.changedAt || new Date().toISOString();
          this.savedMenuRecordId = '';
          this.savedLibraryMessage = 'Project name updated.';
          this.closeRenameDialog();
          this.persist();
          this.changeDetector.markForCheck();
        },
        error: (e) =>
          (this.renameError = String(e?.error?.detail || 'Project could not be renamed.')),
      });
  }
  closeRenameDialog() {
    this.renameDialogOpen = false;
    this.renameTarget = null;
    this.renameName = '';
    this.renameError = '';
  }
  archiveSavedStory(story: SavedStoryRecord) {
    this.askConfirmation('Archive this project?', 'It will remain recoverable in Archived.', () =>
      this.changeSavedLifecycle(story, 'ARCHIVED'),
    );
  }
  restoreSavedStory(story: SavedStoryRecord) {
    this.changeSavedLifecycle(story, 'DRAFT');
  }
  deleteSavedStory(story: SavedStoryRecord) {
    if (!this.canDeleteSavedStory(story)) return;
    this.askConfirmation(
      'Delete this independent draft?',
      'It will be removed from active projects and cannot be reopened from the active list.',
      () => this.changeSavedLifecycle(story, 'DELETED'),
    );
  }
  duplicateSavedStory(story: SavedStoryRecord) {
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${story.recordId}/duplicate`, {})
      .subscribe({
        next: (copy) => {
          this.savedLibraryMessage = 'Draft copy created without inheriting approval.';
          this.savedStories = [
            {
              ...story,
              recordId: String(copy.recordId),
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
              title: copy.title || `${this.storyTitle(story)} (Copy)`,
              result: copy.result || { alternatives: [] },
              idea: copy.idea || story.idea,
              lifecycleStatus: 'DRAFT',
            } as any,
            ...this.savedStories,
          ];
          this.changeDetector.markForCheck();
        },
        error: (e) =>
          (this.savedLibraryMessage = String(
            e?.error?.detail || 'Project could not be duplicated.',
          )),
      });
  }
  private changeSavedLifecycle(story: SavedStoryRecord, status: string) {
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${story.recordId}/lifecycle`, {
        status,
        reason: `Step 1 project library action: ${status}`,
      })
      .subscribe({
        next: (response) => {
          (story as any).lifecycleStatus = response.status || status;
          (story as any).updatedAt = response.changedAt || new Date().toISOString();
          if (
            String(story.recordId) === String(this.storyRecordId) &&
            (status === 'ARCHIVED' || status === 'DELETED')
          ) {
            this.clearSavedContext();
            this.activeJourney = 'RESUME';
            this.newStoryOpen = false;
            this.title = '';
            this.idea = '';
          }
          this.savedMenuRecordId = '';
          this.savedLibraryMessage =
            status === 'ARCHIVED'
              ? 'Project archived and recoverable.'
              : status === 'DELETED'
                ? 'Draft deleted from active projects.'
                : response.status === 'APPROVED'
                  ? 'Approved project restored.'
                  : 'Project restored.';
          this.persist();
          this.changeDetector.markForCheck();
        },
        error: (e) =>
          (this.savedLibraryMessage = String(
            e?.error?.detail ||
              'This lifecycle action was refused safely; no downstream evidence was changed.',
          )),
      });
  }
  savedApprovalFor(story: SavedStoryRecord) {
    const approval = this.savedApprovalRecordsFor(story).find((item) =>
      this.approvalMatchesCandidate(story, item),
    );
    if (!approval) return null;
    const approvedCandidate = approval.candidateId || approval.payload?.candidateId;
    const approvedRevision = approval.revisionId || approval.payload?.revisionId;
    return {
      ...approval,
      approvedCandidateId: approvedCandidate,
      approvedRevisionId: approvedRevision,
    };
  }
  savedApprovalLabel(story: SavedStoryRecord) {
    const approval = this.savedApprovalFor(story);
    if (!approval) return 'Approval required';
    if (!this.savedApprovalVerified(story)) return 'Approval linkage requires review';
    if (approval.approvedCandidateId) {
      const label = String(approval.approvedCandidateId).match(
        /(?:candidate|alternative)[-_ ]?(\d+)/i,
      )?.[1];
      return `Approved · candidate ${label || approval.approvedCandidateId}`;
    }
    return 'Approved · candidate unavailable';
  }
  private activeSavedLineageIsConsistent() {
    const active = this.activeSavedStory;
    return Boolean(
      active &&
      this.activeJourney === 'SAVED' &&
      String(active.recordId) === String(this.storyRecordId) &&
      this.candidates.some(
        (candidate) =>
          String(candidate.candidateId) === String(this.selectedCandidateId) &&
          candidate.text === this.selectedStory,
      ),
    );
  }
  private requireActiveSavedLineage(action: string) {
    if (this.activeSavedLineageIsConsistent()) return true;
    this.error = `${action} was blocked because the selected project lineage changed. Reopen the saved story and try again.`;
    this.changeDetector.markForCheck();
    return false;
  }
  useSavedStory(story: SavedStoryRecord) {
    this.preserveNewDraft();
    const targetStoryId = String(story.recordId);
    this.editorEpoch++;
    this.sessionId = crypto.randomUUID();
    this.ideaDraftId = '';
    this.ideaDraftRevision = 0;
    this.originIdeaDraftId = '';
    this.originIdeaRevision = 0;
    this.revisionParentId = '';
    this.recoverableStoryResponse = null;
    this.visualDirection = null;
    this.linkedIdeaStories = [];
    this.canonicalStoryResult = null;
    this.canonicalStoryText = '';
    this.storyEditing = false;
    this.reviewedStoryFingerprints = {};
    this.cancelStoryGeneration();
    this.activeJourney = 'SAVED';
    this.storyRecordId = targetStoryId;
    this.title = this.storyTitle(story);
    this.idea = String(story.idea || (story as any).sourceRequest?.text || '');
    this.workspacePath = story.workspacePath || '';
    this.storyQuality = story.result?.storyQuality || null;
    this.storyReview = null;
    this.storyReviewStatus = 'NOT_REVIEWED';
    this.approvalRecordId = '';
    this.builderRecordId = '';
    this.builderResult = null;
    this.builderMigration = null;
    this.draftPrompt = '';
    this.savedPromptBaseline = '';
    this.savedPromptTargetSnapshot = null;
    this.buildAttemptState = 'NOT_STARTED';
    this.buildAttemptDiagnostics = null;
    this.promptVersionId = '';
    this.contentId = '';
    this.detailUrl = '/quality/detail';
    this.restoredCharacterName = '';
    this.candidates = this.storyCandidates(story).map((item: any, i: number) => {
      const evidence = this.storyQuality?.candidates?.[i] || {};
      return typeof item === 'string'
        ? {
            candidateId: `${story.recordId}-candidate-${i + 1}`,
            title: `Alternative ${i + 1}`,
            text: item,
            structuralEvidence: evidence.structuralEvidence,
            preflight: evidence.preflight,
            assessment: evidence.assessment,
          }
        : {
            candidateId:
              item.candidateId && item.candidateId !== 'None' && item.candidateId !== 'null'
                ? item.candidateId
                : `${story.recordId}-candidate-${i + 1}`,
            title: item.title || `Alternative ${i + 1}`,
            text: item.text || item.description || JSON.stringify(item),
            structuralEvidence: item.structuralEvidence || evidence.structuralEvidence,
            preflight: item.preflight || evidence.preflight,
            assessment: item.assessment || evidence.assessment,
          };
    });
    const approval =
      this.savedApprovalRecordsFor(story).find((item) =>
        this.approvalMatchesCandidate(story, item),
      ) || null;
    const approvedText = String(approval?.approvedText || approval?.payload?.approvedText || '');
    const approved = approval
      ? this.candidates.find(
          (item) =>
            String(item.candidateId) ===
              String(approval.candidateId || approval.payload?.candidateId) &&
            String(`${item.candidateId}-revision-${this.storyFingerprint(item.text.trim())}`) ===
              String(approval.revisionId || approval.payload?.revisionId) &&
            item.text.trim() === approvedText.trim(),
        )
      : undefined;
    this.selectedCandidateIdValue = approved?.candidateId || this.candidates[0]?.candidateId || '';
    this.selectedStory = approved?.text || this.candidates[0]?.text || '';
    if (approved && approval)
      this.approvalRecordId = String(approval.recordId || approval.id || '');
    const context = story.sourceContext || story.result?.sourceRequest?.context || {};
    const target = context.targetConfiguration || {};
    if (context.mainCharacterId) this.mainCharacterId = String(context.mainCharacterId);
    if (context.mainCharacter) this.restoredCharacterName = String(context.mainCharacter);
    if (target.contentProfile) this.profile = String(target.contentProfile);
    if (target.duration != null) this.duration = Number(target.duration);
    if (target.aspectRatio) this.aspectRatio = String(target.aspectRatio);
    if (target.selectedGenerator) this.targetGenerator = String(target.selectedGenerator);
    this.stage = 'STORY';
    this.storyConsent = false;
    this.restoreVisualDirection();
    this.loadStoryValidation();
    this.draftBaseline = this.captureDraft();
    this.reconcileStoryComparison();
    this.persistLocal();
    this.loadSavedBuilder();
    this.changeDetector.markForCheck();
  }

  useSavedStoryAndContinue(story: SavedStoryRecord) {
    this.useSavedStory(story);
    if (this.approvalRecordId) this.continueApprovedStory();
  }
  continueApprovedStory() {
    if (
      !this.approvalRecordId ||
      (this.storyRecordId &&
        (!this.activeSavedStory || !this.savedApprovalVerified(this.activeSavedStory)))
    )
      return;
    if (
      this.promptVersionId &&
      this.contentId &&
      this.detailUrl &&
      (!this.storyRecordId || this.savedPromptVersionVerified)
    ) {
      this.continueQualityAnalysis();
      return;
    }
    if (this.storyRecordId && this.promptVersionId && !this.savedPromptVersionVerified) {
      this.promptVersionId = '';
      this.contentId = '';
      this.detailUrl = '/quality/detail';
      this.builderRecordId = '';
      this.builderResult = null;
      this.draftPrompt = '';
      this.buildAttemptState = 'NOT_STARTED';
    }
    if (this.canonicalSavedPrompt) {
      this.openCanonicalSavedPrompt();
      return;
    }
    this.activeJourney = 'RESUME';
    this.stage = 'PROMPT';
    this.promptConsent = false;
    this.error = '';
    this.persistLocal();
    this.changeDetector.markForCheck();
  }
  openSavedPrompt() {
    if (!this.builderRecordId && !this.draftPrompt) return;
    this.activeJourney = 'RESUME';
    this.stage = 'PROMPT';
    this.promptConsent = false;
    this.error = '';
    this.persistLocal();
    this.changeDetector.markForCheck();
  }
  openCanonicalSavedPrompt() {
    const row = this.canonicalSavedPrompt;
    if (!row) return;
    const result = row.result || row.payload?.result || {};
    this.builderRecordId = String(row.recordId || row.id);
    this.builderResult = result;
    this.builderMigration = null;
    this.draftPrompt = this.formatPromptForEditor(String(result.prompt || ''));
    this.savedPromptBaseline = this.draftPrompt;
    this.savedPromptTargetSnapshot = this.currentPromptTarget();
    this.buildAttemptState = 'REUSED_SAVED_RESULT';
    this.buildAttemptDiagnostics = row.attemptDiagnostics || {
      calls: 0,
      reused: true,
      persisted: true,
    };
    this.activeJourney = 'RESUME';
    this.stage = 'PROMPT';
    this.promptConsent = false;
    this.error = '';
    this.persistLocal();
    this.changeDetector.markForCheck();
  }
  revalidateSavedDraft() {
    if (!this.builderRecordId || this.busy) return;
    this.busy = true;
    this.error = '';
    this.http
      .post<any>(
        `/api/v1/intelligence/workflow/records/${this.builderRecordId}/revalidate-production-spec`,
        {},
      )
      .subscribe({
        next: (r) => {
          this.builderMigration = r;
          this.builderResult = r.result || null;
          this.savedPromptBaseline = this.draftPrompt;
          this.savedPromptTargetSnapshot = this.currentPromptTarget();
          this.persist();
          this.done();
        },
        error: (e) => this.fail(e, 'The saved draft could not be revalidated locally.'),
      });
  }
  restoreSavedPromptText() {
    if (!this.builderResult?.prompt) return;
    this.draftPrompt = this.formatPromptForEditor(String(this.builderResult.prompt));
    this.savedPromptBaseline = this.draftPrompt;
    this.persist();
    setTimeout(() => {
      this.syncPromptEditor();
      this.changeDetector.markForCheck();
    }, 0);
  }
  restoreMigratedSettings() {
    const settings = this.builderResult?.productionPlan?.productionConstraints || {};
    if (settings.duration != null && Number.isFinite(Number(settings.duration)))
      this.duration = Number(settings.duration);
    if (settings.aspectRatio && settings.aspectRatio !== 'UNKNOWN')
      this.aspectRatio = String(settings.aspectRatio);
    if (settings.generator && settings.generator !== 'UNKNOWN')
      this.targetGenerator = String(settings.generator);
    if (settings.contentProfile && settings.contentProfile !== 'UNKNOWN')
      this.profile = String(settings.contentProfile);
    const name = String(settings.mainCharacter || '');
    if (name)
      this.mainCharacterId =
        this.characters.find((item) => item.name === name)?.id || this.mainCharacterId;
    this.savedPromptTargetSnapshot = this.currentPromptTarget();
    this.persist();
    this.changeDetector.markForCheck();
  }
  openExistingDraftForReview() {
    if (this.builderInputMismatch) {
      this.error = 'Restore the exact saved production settings before continuing this draft.';
      return;
    }
    this.savePrompt();
  }
  continueQualityAnalysis() {
    if (
      !this.promptVersionId ||
      !this.detailUrl ||
      (this.storyRecordId && !this.savedPromptVersionVerified)
    )
      return;
    this.activeJourney = 'RESUME';
    this.stage = 'PRODUCTION_REVIEW';
    this.persistLocal();
    this.router.navigateByUrl(this.detailUrl);
  }

  ideaReviewQuote: any = null;
  ideaReviewBudget = 0;
  ideaReviewConsent = false;
  ideaReviewBusy = false;
  ideaReviewError = '';
  ideaReviewResult: any = null;
  ideaReviewHistory: any[] = [];

  prepareIdeaReview() {
    this.ideaReviewConsent = false;
    this.ideaReviewQuote = null;
    this.ideaReviewError = '';
    this.ideaReviewBusy = true;
    const id = this.ideaDraftId;
    this.http.post<any>(`/api/v1/intelligence/workflow/idea-drafts/${id}/semantic-review/preview`, { workspacePath: this.workspacePath }).subscribe({
      next: quote => { if (id === this.ideaDraftId) this.ideaReviewQuote = quote; this.ideaReviewBusy = false; this.changeDetector.markForCheck(); },
      error: e => { this.ideaReviewError = e.error?.message || 'Review preview unavailable; no provider call was made.'; this.ideaReviewBusy = false; this.changeDetector.markForCheck(); }
    });
  }

  runIdeaReview() {
    if (!this.ideaReviewConsent || !this.ideaReviewQuote || this.ideaReviewBudget <= 0 || this.ideaReviewBudget < this.ideaReviewQuote.estimatedUpperBoundUsd) return;
    const id = this.ideaDraftId;
    const payload = { workspacePath: this.workspacePath, quoteId: this.ideaReviewQuote.quoteId, ownerAuthorized: true,
      maxCostUsd: this.ideaReviewBudget, maximumProviderCalls: 1, model: this.ideaReviewQuote.model };
    this.ideaReviewConsent = false;
    this.ideaReviewBusy = true;
    this.ideaReviewError = '';
    this.http.post<any>(`/api/v1/intelligence/workflow/idea-drafts/${id}/semantic-review`,payload).subscribe({
      next: result => { this.ideaReviewBusy = false; if(id===this.ideaDraftId) {this.ideaReviewResult=result; this.ideaReviewQuote=null; this.loadIdeaCandidates();} this.changeDetector.markForCheck(); },
      error: e => { this.ideaReviewBusy = false; this.ideaReviewQuote=null; this.ideaReviewError=e.error?.message || 'Review failed. Inspect receipt history before any further action; no automatic retry.'; this.changeDetector.markForCheck(); }
    });
  }

  loadIdeaCandidates() {
    this.ideaReviewQuote = null;
    this.ideaReviewConsent = false;
    this.ideaReviewHistory = [];
    this.ideaCandidates = [];
    this.ideaBatches = [];
    if (!this.ideaDraftId || !this.workspacePath) return;
    const id = this.ideaDraftId;
    const params = { workspacePath: this.workspacePath };
    this.http.get<any[]>(`/api/v1/intelligence/workflow/idea-drafts/${id}/semantic-reviews`,{params}).subscribe({
      next: rows => {if(id===this.ideaDraftId) this.ideaReviewHistory=rows; this.changeDetector.markForCheck();},
      error: () => {this.ideaReviewError='Semantic review history unavailable.';this.changeDetector.markForCheck();}
    });
    this.http
      .get<any[]>(`/api/v1/intelligence/workflow/idea-drafts/${id}/candidates`, { params })
      .subscribe({
        next: (rows) => {
          if (id === this.ideaDraftId) {
            this.ideaCandidates = rows;
            this.changeDetector.markForCheck();
          }
        },
        error: (e) => {
          this.error = 'Saved IDEA candidates could not be loaded. Reload before generation.';
          this.changeDetector.markForCheck();
        },
      });
    this.http
      .get<any[]>(`/api/v1/intelligence/workflow/idea-drafts/${id}/batches`, { params })
      .subscribe({
        next: (rows) => {
          if (id === this.ideaDraftId) {
            this.ideaBatches = rows;
            this.changeDetector.markForCheck();
          }
        },
        error: () => {
          this.error = 'IDEA receipt history unavailable. Reload before generation.';
          this.changeDetector.markForCheck();
        },
      });
  }
  private ideaAction(url: string, body: any) {
    const id = this.ideaDraftId;
    this.ideaCandidateBusy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/idea-drafts/${id}/${url}`, {
        workspacePath: this.workspacePath,
        ...body,
      })
      .subscribe({
        next: () => {
          this.ideaCandidateBusy = false;
          if (id === this.ideaDraftId) this.loadIdeaCandidates();
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.ideaCandidateBusy = false;
          this.fail(e, 'IDEA action failed; saved receipt remains available. No provider retry.');
        },
      });
  }
  decideIdeaCandidate(candidate: any, state: string) {
    this.ideaAction(`candidates/${candidate.candidateId}/decision`, {
      state,
      expectedRevision: candidate.decisionRevision || 0,
    });
  }
  evaluateIdeaCandidate(candidate: any) {
    this.ideaAction(`candidates/${candidate.candidateId}/evaluate`, {});
  }
  recoverIdeaBatch(batch: any) {
    this.ideaAction('candidates/recover', { requestId: batch.requestId });
  }

  private runStoryRole() {
    const epoch = this.editorEpoch;
    const snapshot = JSON.stringify(this.captureDraft());
    this.busy = true;
    this.error = '';
    const authorizedCost = this.budget;
    this.generationConsent = false;
    this.http
      .post<any>('/api/v1/intelligence/workflow/creative-role', {
        role: this.inputMode === 'IDEA' ? 'IDEA' : 'STORY',
        text: this.idea.trim(),
        generationAuthorized: true,
        maxCostUsd: authorizedCost,
        context: {
          storyProvider: this.generationProvider,
          storyModel: this.storyModel,
          sourceStoryRecordId: this.revisionParentId || null,
          visualDirection: this.visualDirection,
          sourceIdeaDraftId:
            this.inputMode === 'IDEA'
              ? this.ideaDraftId
              : this.originIdeaDraftId || this.ideaDraftId || null,
          sourceIdeaRevision:
            this.inputMode === 'IDEA'
              ? this.ideaDraftRevision
              : this.originIdeaRevision || this.ideaDraftRevision || null,
          sourceSessionId: this.sessionId,
          constraints: this.constraints,
          mainCharacter: this.selectedCharacterName || null,
          mainCharacterId: this.mainCharacterId,
          preferences: this.preferences,
          inputMode: this.inputMode,
          storyGenerationMode: this.storyMode,
          lockedRequirements: this.lockedRequirements,
          permittedVariation:
            this.storyMode === 'IMPROVE_EXISTING_STORY'
              ? 'Refine clarity, staging, execution risk and presentation without inventing locked events or an ending. Unchecked requirements may vary.'
              : 'Explore opening, strategy, obstacle, escalation, reveal and ending structure',
          refinementDirections:
            this.storyMode === 'IMPROVE_EXISTING_STORY'
              ? [
                  'clarify the first visual promise',
                  'strengthen causal escalation',
                  'improve physical staging and readability',
                  'vary consequences or discovery without forced comedy',
                ]
              : [],
          workspacePath: this.workspacePath,
          requestedAlternativeCount: this.inputMode === 'IDEA' ? 3 : this.candidateCount,
          targetConfiguration: {
            aspectRatio: this.aspectRatio,
            duration: this.duration,
            selectedGenerator: this.targetGenerator,
            contentProfile: this.profile,
            mainCharacter: this.selectedCharacterName || null,
            mainCharacterId: this.mainCharacterId,
          },
          lessonContext: {
            contentProfile: this.profile,
            modelVersion: '',
            duration: this.duration,
            generator: this.targetGenerator,
            settings: { aspectRatio: this.aspectRatio, mode: 'image2video', resolution: '480p' },
          },
        },
      })
      .subscribe({
        next: (r) => {
          if (epoch !== this.editorEpoch || snapshot !== JSON.stringify(this.captureDraft())) {
            this.busy = false;
            this.changeDetector.markForCheck();
            return;
          }
          if (this.inputMode === 'IDEA') {
            this.ideaCandidates = r.ideaCandidates || [];
            this.stage = 'IDEA';
            this.ideaBatchConsent = false;
            this.loadIdeaCandidates();
            this.persistLocal();
            this.done();
            return;
          }
          this.storyRecordId = r.recordId;
          this.storyQuality = r.result?.storyQuality || null;
          this.storyReview = null;
          this.storyReviewStatus = 'NOT_REVIEWED';
          this.candidates = (r.result?.alternatives || [])
            .slice(0, this.candidateCount)
            .map((item: any, i: number) => {
              const evidence = this.storyQuality?.candidates?.[i] || {};
              return typeof item === 'string'
                ? {
                    candidateId: `${this.storyRecordId}-candidate-${i + 1}`,
                    title: `Alternative ${i + 1}`,
                    text: item,
                    structuralEvidence: evidence.structuralEvidence,
                    preflight: evidence.preflight,
                    assessment: evidence.assessment,
                  }
                : {
                    candidateId:
                      item.candidateId && item.candidateId !== 'None' && item.candidateId !== 'null'
                        ? item.candidateId
                        : `${this.storyRecordId}-candidate-${i + 1}`,
                    title: item.title || `Alternative ${i + 1}`,
                    text: item.text || item.description || JSON.stringify(item),
                    structuralEvidence: item.structuralEvidence || evidence.structuralEvidence,
                    preflight: item.preflight || evidence.preflight,
                    assessment: item.assessment || evidence.assessment,
                  };
            });
          this.reconcileStoryComparison();
          this.stage = 'STORY';
          this.storyConsent = false;
          this.persist();
          this.done();
        },
        error: (e) => {
          this.loadIdeaCandidates();
          this.fail(
            e,
            'Generation or persistence failed. Inspect saved IDEA receipts and recover without a provider retry.',
          );
        },
      });
  }
  selectStory(candidate: StoryCandidate) {
    this.selectedCandidateIdValue = candidate.candidateId;
    this.selectedStory = candidate.text;
    this.storyEditing = false;
    this.persist();
  }
  selectOriginalStory() {
    this.selectedCandidateIdValue = 'ORIGINAL_SOURCE';
    this.selectedStory = this.idea;
    this.storyEditing = false;
    this.persist();
  }
  candidateReview(candidateId: string) {
    return (
      this.storyReview?.candidateReviews?.find((item: any) => item.candidateId === candidateId) ||
      null
    );
  }
  candidateReviewLabel(candidateId: string): string {
    const review = this.candidateReview(candidateId);
    const value = review?.editorialRecommendation || review?.overallStatus;
    return value && String(value).toUpperCase().includes('RECOMMENDED')
      ? 'Provider suggestion'
      : value || 'Provider review';
  }
  selectReviewTab(candidateId: string) {
    this.reviewDialogTab = candidateId;
  }
  closeReviewDialog() {
    this.reviewDialogOpen = false;
    this.reviewDialogTab = '';
  }
  get reviewDialogSelectedId(): string {
    return (
      this.reviewDialogTab || this.selectedCandidateId || this.candidates[0]?.candidateId || ''
    );
  }
  recommendedStoryLabel() {
    const index = this.recommendedCandidateIndex();
    if (index < 0) return 'No supported winner';
    const label = this.reviewComparisonLabel();
    return label === 'NEAR_DUPLICATE' || label === 'INSUFFICIENT_EVIDENCE'
      ? `AI suggestion · Alternative ${index + 1}`
      : `Alternative ${index + 1}`;
  }
  recommendedCandidateIndex() {
    const id = this.storyReview?.recommendedCandidateId;
    const direct = this.candidates.findIndex((item) => item.candidateId === id);
    if (direct >= 0) return direct;
    const match = String(this.storyReview?.recommendationReason || '').match(/candidate\s*(\d+)/i);
    return match ? Number(match[1]) - 1 : -1;
  }
  isRecommendedCandidate(candidate: StoryCandidate, index: number) {
    return (
      this.reviewComparisonLabel() !== 'NEAR_DUPLICATE' &&
      this.recommendedCandidateIndex() === index
    );
  }
  reviewValueText(value: any): string {
    if (value === null || value === undefined || value === '') return 'Evidence unavailable';
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')
      return String(value);
    if (Array.isArray(value))
      return value.length
        ? value.map((item) => this.reviewValueText(item)).join(' · ')
        : 'Evidence unavailable';
    if (typeof value === 'object')
      return (
        Object.entries(value)
          .map(([key, item]) => `${this.readableDifference(key)}: ${this.reviewValueText(item)}`)
          .join(' · ') || 'Evidence unavailable'
      );
    return 'Evidence unavailable';
  }
  reviewFindingsText(value: any) {
    return this.reviewValueText(value);
  }
  normalizedReviewFindings(candidateId: string): any[] {
    const review = this.candidateReview(candidateId);
    const raw = review?.findings;
    const entries = Array.isArray(raw) ? raw : raw && typeof raw === 'object' ? [raw] : [];
    return entries.map((item: any) => {
      if (typeof item === 'string') {
        return {
          findingType: 'UNKNOWN',
          finding: item,
          dimension: 'Unknown',
          severity: null,
          supportingText: ['Evidence unavailable'],
          confidence: 'Unknown',
          improvement: 'Evidence unavailable',
          raw: item,
        };
      }
      const value = (...keys: string[]) => {
        for (const key of keys) {
          if (item && Object.prototype.hasOwnProperty.call(item, key)) return item[key];
        }
        return null;
      };
      const list = (...keys: string[]) => {
        const v = value(...keys);
        if (v === null || v === undefined) return ['Evidence unavailable'];
        return Array.isArray(v) ? v.map((x) => this.reviewValueText(x)) : [this.reviewValueText(v)];
      };
      const findingText = this.reviewValueText(value('finding', 'assessment', 'summary'));
      const dimensionText = this.reviewValueText(value('dimension', 'findingDimension'));
      const rawSeverity = value('severity');
      const severityText =
        rawSeverity != null && rawSeverity !== 'None' && rawSeverity !== 'null'
          ? this.reviewValueText(rawSeverity)
          : null;
      const findingType = this.classifyFindingType(item, findingText, dimensionText, severityText);
      // Severity only applies to CONCERN type. Strengths and Observations have no severity.
      const effectiveSeverity = findingType === 'CONCERN' ? severityText : null;
      return {
        findingType,
        finding: findingText,
        dimension: dimensionText,
        severity: effectiveSeverity,
        supportingText: list(
          'supportingTextEvidence',
          'supportingSourceText',
          'sourceTextEvidence',
          'evidence',
        ),
        confidence: this.reviewValueText(
          value('confidenceOrEvidenceStatus', 'confidence', 'evidenceStatus'),
        ),
        improvement: this.reviewValueText(
          value('suggestedMinimalImprovement', 'suggestedImprovement', 'improvement'),
        ),
        raw: item,
      };
    });
  }
  classifyFindingType(
    item: any,
    findingText: string,
    dimensionText: string,
    severityText: string | null,
  ): string {
    const v = (...keys: string[]) => {
      for (const key of keys) {
        if (item && Object.prototype.hasOwnProperty.call(item, key)) return item[key];
      }
      return null;
    };
    // Explicit type from provider takes precedence
    const explicitType = v('findingType', 'finding_type', 'type');
    if (explicitType) {
      const upper = String(explicitType).toUpperCase();
      if (['STRENGTH', 'CONCERN', 'OBSERVATION', 'UNKNOWN', 'MIXED'].includes(upper)) return upper;
    }
    const findingLower = findingText.toLowerCase();
    const dimensionLower = (dimensionText || '').toLowerCase();
    const combined = findingLower + ' ' + dimensionLower;
    // If severity is HIGH/CRITICAL, it's a CONCERN regardless of other signals
    if (severityText) {
      const sevUpper = severityText.toUpperCase();
      if (sevUpper === 'HIGH' || sevUpper === 'CRITICAL') return 'CONCERN';
    }
    // ── Mixed-sentiment detection ──
    // Detect sentences that contain BOTH positive and negative signals.
    // These are genuinely mixed findings: the positive aspect is real, but so is the negative qualification.
    const positiveSignal =
      /\b(clear|strong|well|good|effective|compelling|coherent|satisfying|engaging|vivid|consistent|solid|bright|vivid|powerful)\b/i;
    // Expanded weakness words: include "lacks", "lack", "lacking" and all forms
    const weaknessAfterConjunction =
      /\b(but|however|although|though|yet|unfortunately|sadly)\b.*\b(less|weaker|worse|poorer|inferior|lacks?|lacking|deficient|repetitive|repetit|redundant|boring|dull|flat|weak|unclear|ambiguous|confusing|inconsistent|broken|uncertain|risky|problem|issue|gap|insufficient|missing|underwhelming|thin|shallow|superficial)\b/i;
    const comparativeWeakness =
      /\b(less|not as|not.*as|worse|weaker|poorer|inferior|below|short of|lacks?|lacking|deficient)\b.*\b(engaging|compelling|clear|strong|effective|coherent|satisfying|vivid|consistent|solid|original|creative|interesting)\b/i;
    const repetitivePhrasing = /\b(repetitive|repetit|redundant|overused|clich|formulaic)\b/i;
    const lessOriginal =
      /\b(less|not as|not.*as)\b.*\b(original|creative|innovative|unique|fresh|novel)\b/i;
    // Check for mixed sentiment: positive word AND a weakness clause
    const hasPositive = positiveSignal.test(findingLower);
    const hasButWeakness = weaknessAfterConjunction.test(findingLower);
    const hasComparativeWeakness = comparativeWeakness.test(findingLower);
    const hasRepetitive = repetitivePhrasing.test(findingLower);
    const hasLessOriginal = lessOriginal.test(findingLower);
    // If there's a conjunction-based weakness (e.g., "but lacks"), it's genuinely mixed when positive signal is also present
    if (hasPositive && hasButWeakness) return 'MIXED';
    // Comparative weakness with positive signal is also mixed (e.g., "not as engaging as")
    if (hasPositive && hasComparativeWeakness) return 'MIXED';
    // Pure comparative weakness without positive signal => CONCERN
    if (hasComparativeWeakness && !hasPositive) return 'CONCERN';
    if (hasButWeakness && !hasPositive) return 'CONCERN';
    if (hasRepetitive) return 'CONCERN';
    if (hasLessOriginal) return 'CONCERN';
    // Pure negative patterns => CONCERN
    const negativeWithReason =
      /\b(weak|unclear|ambiguous|missing|lacks?|lacking|confusing|inconsistent|broken|uncertain|risky|problem|issue|gap|insufficient)\b/i;
    if (negativeWithReason.test(combined)) return 'CONCERN';
    // Positive patterns => STRENGTH (only after ruling out mixed/negative signals)
    if (positiveSignal.test(combined)) return 'STRENGTH';
    // Dimension hints
    if (dimensionLower.includes('strength')) return 'STRENGTH';
    if (
      dimensionLower.includes('concern') ||
      dimensionLower.includes('risk') ||
      dimensionLower.includes('issue')
    )
      return 'CONCERN';
    // Default to OBSERVATION for neutral findings
    return 'OBSERVATION';
  }
  reviewTimestampLabel(): string {
    const review = this.storyReview;
    if (!review) return 'Review time unavailable';
    if (review.reviewModel === 'local-mock' || review.reviewId === 'LOCAL_MOCK_REVIEW')
      return 'DEMO / FIXTURE · Review time unavailable';
    const value = String(review.reviewTimestamp || review.persistedAt || '');
    const parsed = Date.parse(value);
    if (!parsed) return 'Review time unavailable';
    const ageMs = Date.now() - parsed;
    const ageHours = ageMs / 3600000;
    if (ageHours < 2) return `Current review · ${new Date(parsed).toISOString()}`;
    if (ageHours < 168)
      return `Historical review · ${new Date(parsed).toISOString()} (${Math.round(ageHours / 24)}d old)`;
    return `Historical review · ${new Date(parsed).toISOString()} (${Math.round(ageHours / 168)}w old)`;
  }
  reviewSimilarities(): string[] {
    const value = this.storyReview?.comparativeFindings?.similarities;
    return Array.isArray(value) ? value.map((item) => this.reviewValueText(item)) : [];
  }
  reviewDifferences(): string[] {
    const value = this.storyReview?.comparativeFindings?.differences;
    return Array.isArray(value) ? value : [];
  }
  reviewOverallConcerns(): string[] {
    const value = this.storyReview?.overallConcerns;
    return Array.isArray(value) ? value.map((item) => this.reviewValueText(item)) : [];
  }
  reviewConcernsLabel(): string {
    // Count typed CONCERN findings across all candidates — these are canonical concerns derived from evidence
    if (!this.storyReview?.candidateReviews) return 'Unknown';
    let canonicalConcernCount = 0;
    for (const candidateReview of this.storyReview.candidateReviews) {
      const findings = this.normalizedReviewFindings(candidateReview.candidateId);
      canonicalConcernCount += findings.filter((f: any) => f.findingType === 'CONCERN').length;
    }
    // Provider-reported overall concerns are a separate source — not independent validation
    const providerConcerns = Array.isArray(this.storyReview?.overallConcerns)
      ? this.storyReview.overallConcerns.length
      : 0;
    // Show canonical count when we have typed findings; fall back to provider count only when canonical is zero
    // Keep UNKNOWN distinct from zero: zero canonical concerns with no provider concerns = Unknown
    if (canonicalConcernCount > 0) return String(canonicalConcernCount);
    if (providerConcerns > 0) return `Provider: ${providerConcerns}`;
    return 'Unknown';
  }
  reviewComparisonLabel(): string {
    // The reconciliation layer already corrects unsupported PARTIALLY_DISTINCT to INSUFFICIENT_EVIDENCE.
    // This method provides a safe display label that never contradicts the persisted evidence.
    const classification = this.storyQuality?.classification;
    const differences = this.storyQuality?.differences;
    const hasSupportedDifferences = Array.isArray(differences) && differences.length > 0;
    if (classification === 'PARTIALLY_DISTINCT' && !hasSupportedDifferences) {
      return 'INSUFFICIENT_EVIDENCE';
    }
    return classification || 'UNKNOWN';
  }
  reviewComparisonSummary(): string {
    const classification = this.storyQuality?.classification;
    const differences = this.storyQuality?.differences;
    const hasSupportedDifferences = Array.isArray(differences) && differences.length > 0;
    if (classification === 'PARTIALLY_DISTINCT' && !hasSupportedDifferences) {
      return 'Insufficient evidence to establish material narrative differences. Wording similarity alone cannot verify distinctness.';
    }
    return this.storyQuality?.summary || 'Comparison evidence is unavailable.';
  }
  reviewDisagreement(): string {
    const local = this.storyQuality?.variationClass || this.storyQuality?.classification;
    const external = this.storyReview?.diversityAssessment?.classification;
    return local &&
      external &&
      String(local).toLowerCase().replaceAll('_', ' ') !==
        String(external).toLowerCase().replaceAll('_', ' ')
      ? `Local structural comparison reports ${String(local).replaceAll('_', ' ')} while the independent review reports ${String(external).replaceAll('_', ' ')}. Review the source evidence before selecting a candidate.`
      : '';
  }
  reviewEndingStatus(candidate: StoryCandidate): string {
    // Separate ending existence from ending quality.
    // A story can have a final event (existence) without that event being creatively effective (quality).
    const preflight = candidate.preflight;
    if (preflight) {
      const endingValue = String(preflight.ending || '').toUpperCase();
      if (
        endingValue.includes('PRESENT') ||
        endingValue.includes('EXISTS') ||
        endingValue.includes('CLEAR')
      )
        return 'PRESENT';
      if (endingValue.includes('ABSENT') || endingValue.includes('MISSING')) return 'ABSENT';
    }
    // Heuristic: if the story text has a final sentence that describes a state change or resolution,
    // an ending event exists even if its creative quality is unknown.
    const text = (candidate.text || '').trim();
    if (text.length > 50) {
      // Split on sentence boundaries and filter out empty strings (e.g., trailing period)
      const sentences = text
        .split(/[.!?]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const lastSentence = sentences.length > 0 ? sentences[sentences.length - 1] : '';
      if (lastSentence.length > 10) return 'PRESENT';
    }
    return 'UNKNOWN';
  }
  reviewEndingQuality(candidateId: string): string {
    // Ending quality is the creative assessment from the provider review.
    // It is separate from ending existence: a story can have an ending that is creatively weak.
    const review = this.candidateReview(candidateId);
    if (!review) return 'Unknown';
    // Check findings for ending-related assessments
    const findings = this.normalizedReviewFindings(candidateId);
    const endingFinding = findings.find((f: any) => {
      const dim = (f.dimension || '').toLowerCase();
      const text = (f.finding || '').toLowerCase();
      return (
        dim.includes('ending') ||
        dim.includes('payoff') ||
        dim.includes('closure') ||
        text.includes('ending') ||
        text.includes('payoff') ||
        text.includes('closure')
      );
    });
    if (!endingFinding) return 'Not assessed';
    if (endingFinding.findingType === 'CONCERN') return 'Concern raised';
    if (endingFinding.findingType === 'STRENGTH') return 'Positive signal';
    if (endingFinding.findingType === 'MIXED') return 'Mixed signal';
    return endingFinding.finding || 'Not assessed';
  }
  candidateStrengths(candidate: StoryCandidate): any[] {
    const a = candidate.assessment;
    if (!a || !Array.isArray(a.strengths)) return [];
    return a.strengths;
  }
  candidateRisks(candidate: StoryCandidate): any[] {
    const a = candidate.assessment;
    if (!a || !Array.isArray(a.risks)) return [];
    return a.risks;
  }
  candidateUnknowns(candidate: StoryCandidate): any[] {
    const a = candidate.assessment;
    if (!a || !Array.isArray(a.unknown)) return [];
    return a.unknown;
  }

  getRecommendationLabel(candidateId: string): string {
    const c = this.candidates.find((c) => c.candidateId === candidateId);
    if (!c) return candidateId;
    const idx = this.candidates.indexOf(c) + 1;
    return c.title ? `${c.title} (Alternative ${idx})` : `Alternative ${idx}`;
  }
  readableDimension(dim: string): string {
    const map: Record<string, string> = {
      characterGoal: 'Character goal',
      obstacle: 'Obstacle',
      characterInitiative: 'Character initiative',
      progression: 'Progression',
      escalation: 'Escalation',
      distinctAttempts: 'Distinct attempts',
      endingEvent: 'Ending event',
      endingPayoff: 'Ending payoff quality',
      repetitionRisk: 'Repetition risk',
      ruleConsistency: 'Rule consistency',
      visualLegibility: 'Visual legibility',
      aiProducibility: 'AI producibility',
      pacing: 'Pacing',
    };
    return map[dim] || dim.replace(/([A-Z])/g, ' $1').replace(/^./, (s) => s.toUpperCase());
  }

  private normalizeStoryReview(value: any): any {
    if (!value) return value;
    let parsed = value;
    if (typeof value === 'string') {
      try {
        parsed = JSON.parse(value);
      } catch {
        return {
          reviewStatus: 'INVALID',
          reviewModel: 'Unknown',
          reviewPolicyVersion: 'Unknown',
          rawProviderResponse: value,
          evidenceLimitations: ['Evidence unavailable: malformed provider review response.'],
          candidateReviews: [],
          recommendedCandidateId: null,
        };
      }
    }
    if (!parsed || typeof parsed !== 'object')
      return {
        reviewStatus: 'INVALID',
        evidenceLimitations: ['Evidence unavailable: review response was not an object.'],
        candidateReviews: [],
        recommendedCandidateId: null,
      };
    const review = { ...parsed };
    review.candidateReviews = Array.isArray(review.candidateReviews)
      ? review.candidateReviews.map((item: any, i: number) => ({
          ...item,
          candidateId:
            item?.candidateId && item.candidateId !== 'None' && item.candidateId !== 'null'
              ? item.candidateId
              : this.candidates[i]?.candidateId,
        }))
      : [];
    if (
      !review.recommendedCandidateId ||
      review.recommendedCandidateId === 'None' ||
      review.recommendedCandidateId === 'null'
    )
      review.recommendedCandidateId = null;
    // Validate comparative claims against canonical evidence
    const classification = this.storyQuality?.classification;
    const differences = this.storyQuality?.differences;
    const hasSupportedDifferences = Array.isArray(differences) && differences.length > 0;
    // NEAR_DUPLICATE, INSUFFICIENT_EVIDENCE, and PARTIALLY_DISTINCT without supported dimensions
    // all indicate that canonical evidence cannot support a winner
    const unsupportedComparison =
      classification === 'NEAR_DUPLICATE' ||
      classification === 'INSUFFICIENT_EVIDENCE' ||
      (classification === 'PARTIALLY_DISTINCT' && !hasSupportedDifferences);
    if (unsupportedComparison) {
      const evidenceLabel =
        classification === 'PARTIALLY_DISTINCT' && !hasSupportedDifferences
          ? 'PARTIALLY DISTINCT but no supported different narrative dimensions were extracted'
          : `canonical comparison shows ${classification.replaceAll('_', ' ')}`;
      if (review.recommendedCandidateId) {
        review.evidenceLimitations = [
          ...(review.evidenceLimitations || []),
          `Provider recommends a candidate, but ${evidenceLabel}. No material difference is established; the recommendation is a suggestion, not verified evidence.`,
        ];
        review.recommendationReason = `Provider suggestion only · ${review.recommendationReason || 'No reason given'}. Canonical evidence does not support a winner.`;
      } else if (
        review.recommendationReason &&
        !review.recommendationReason.toLowerCase().includes('suggestion') &&
        !review.recommendationReason.toLowerCase().includes('no preference')
      ) {
        review.evidenceLimitations = [
          ...(review.evidenceLimitations || []),
          `Provider provides a recommendation reason, but ${evidenceLabel}. Evidence is insufficient to verify superiority claims.`,
        ];
      }
    }
    // Always mark provider recommendations as AI suggestions, never as verified conclusions
    if (review.recommendedCandidateId && review.recommendationReason) {
      const reasonLower = review.recommendationReason.toLowerCase();
      if (
        !reasonLower.includes('suggestion') &&
        !reasonLower.includes('ai') &&
        !reasonLower.includes('provider')
      ) {
        review.recommendationReason = `AI suggestion · ${review.recommendationReason}. This is a provider claim, not independently verified evidence.`;
      }
    }
    // Ensure confidence is not invented
    if (review.candidateReviews) {
      review.candidateReviews = (review.candidateReviews || []).map((item: any) => {
        const conf = item.confidenceOrEvidenceStatus || item.confidence;
        if (conf == null || conf === undefined || conf === '')
          item.confidenceOrEvidenceStatus = 'Evidence unavailable';
        return item;
      });
    }
    return review;
  }

  private storyFingerprint(value: string) {
    let hash = 2166136261;
    for (let i = 0; i < value.length; i++) {
      hash ^= value.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, '0');
  }
  private normalizeStoryBody(value: string) {
    return String(value || '')
      .normalize('NFC')
      .toLocaleLowerCase()
      .replace(/[\p{P}\p{S}]+/gu, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }
  private storyBodySimilarity(left: string, right: string) {
    const a = this.normalizeStoryBody(left).split(' ').filter(Boolean);
    const b = this.normalizeStoryBody(right).split(' ').filter(Boolean);
    if (!a.length && !b.length) return 1;
    if (!a.length || !b.length) return 0;
    const sa = new Set(a),
      sb = new Set(b);
    let overlap = 0;
    sa.forEach((token) => {
      if (sb.has(token)) overlap++;
    });
    return overlap / (sa.size + sb.size - overlap);
  }
  private reconcileStoryComparison() {
    const pairs: any[] = [];
    for (let i = 0; i < this.candidates.length; i++)
      for (let j = i + 1; j < this.candidates.length; j++) {
        const similarity = this.storyBodySimilarity(
          this.candidates[i].text,
          this.candidates[j].text,
        );
        pairs.push({
          left: i + 1,
          right: j + 1,
          lexicalSimilarity: similarity,
          evidenceState: similarity >= 0.82 ? 'SAME' : 'UNKNOWN',
          sharedDimensions: similarity >= 0.82 ? ['body text'] : [],
          differentDimensions: [],
        });
      }
    const originalComparisons =
      this.storyMode === 'IMPROVE_EXISTING_STORY' && this.idea
        ? this.candidates.map((candidate, index) => ({
            source: 'ORIGINAL_SOURCE',
            candidateId: candidate.candidateId,
            candidate: index + 1,
            lexicalSimilarity: this.storyBodySimilarity(this.idea, candidate.text),
            evidenceState:
              this.normalizeStoryBody(this.idea) === this.normalizeStoryBody(candidate.text)
                ? 'SAME'
                : 'UNKNOWN',
            supportedDifferences: [],
          }))
        : [];
    if (this.candidates.length < 2) {
      if (originalComparisons.length)
        this.storyQuality = { ...(this.storyQuality || {}), originalComparisons };
      return;
    }
    const allExact =
      this.candidates.length > 1 &&
      this.candidates.every(
        (candidate) =>
          this.normalizeStoryBody(candidate.text) ===
          this.normalizeStoryBody(this.candidates[0].text),
      );
    if (allExact) {
      this.storyQuality = {
        ...(this.storyQuality || {}),
        comparisonContractVersion: 'story-review-comparison-v1',
        classification: 'NEAR_DUPLICATE',
        variationClass: 'NEAR_DUPLICATE',
        summary:
          'These candidate bodies are identical after Unicode and punctuation normalization. Titles do not establish a narrative difference.',
        differences: [],
        pairs: pairs.map((pair) => ({ ...pair, evidenceState: 'SAME' })),
        originalComparisons,
        method: 'Unicode-normalized exact body comparison; titles excluded',
        evidenceState: 'SAME',
      };
      return;
    }
    const allNear = pairs.length > 0 && pairs.every((pair) => pair.lexicalSimilarity >= 0.82);
    if (allNear && !this.storyQuality?.semanticEvidence) {
      this.storyQuality = {
        ...(this.storyQuality || {}),
        comparisonContractVersion: 'story-review-comparison-v1',
        classification: 'INSUFFICIENT_EVIDENCE',
        variationClass: 'INSUFFICIENT_EVIDENCE',
        summary:
          'The candidate wording is similar, but lexical similarity alone cannot establish narrative equivalence.',
        differences: [],
        pairs: pairs.map((pair) => ({ ...pair, evidenceState: 'UNKNOWN' })),
        originalComparisons,
        method: 'Unicode-normalized body comparison; titles excluded',
        evidenceState: 'UNKNOWN',
      };
      return;
    }
    if (!this.storyQuality) {
      this.storyQuality = {
        comparisonContractVersion: 'story-review-comparison-v1',
        classification: 'INSUFFICIENT_EVIDENCE',
        variationClass: 'INSUFFICIENT_EVIDENCE',
        summary:
          'The supplied text does not contain enough evidence to claim material differences.',
        differences: [],
        pairs,
        method: 'Unicode-normalized body comparison; titles excluded',
        evidenceState: 'UNKNOWN',
      };
      return;
    }
    // P0 fix: When backend returns PARTIALLY_DISTINCT without supported narrative dimensions,
    // correct it to INSUFFICIENT_EVIDENCE. Wording similarity alone cannot establish narrative distinctness.
    let mergedQuality = this.storyQuality;
    if (mergedQuality.classification === 'PARTIALLY_DISTINCT') {
      const hasSupportedDifferences =
        Array.isArray(mergedQuality.differences) && mergedQuality.differences.length > 0;
      if (!hasSupportedDifferences) {
        mergedQuality = {
          ...mergedQuality,
          classification: 'INSUFFICIENT_EVIDENCE',
          variationClass: 'INSUFFICIENT_EVIDENCE',
          summary:
            'Insufficient evidence to establish material narrative differences. Wording similarity alone cannot verify distinctness.',
          evidenceState: 'UNKNOWN',
        };
      }
    }
    this.storyQuality = {
      ...mergedQuality,
      comparisonContractVersion:
        mergedQuality.comparisonContractVersion || 'story-review-comparison-v1',
      pairs: mergedQuality.pairs || pairs,
      originalComparisons: mergedQuality.originalComparisons || originalComparisons,
      method: mergedQuality.method || 'Unicode-normalized body comparison; titles excluded',
    };
  }
  onSelectedStoryChange(value: string) {
    this.selectedStory = value;
    const selected = this.candidates.find((item) => item.candidateId === this.selectedCandidateId);
    if (
      this.storyReview &&
      selected &&
      this.reviewedStoryFingerprints[selected.candidateId] !== this.storyFingerprint(value)
    ) {
      this.storyReviewStatus = 'STALE';
    }
    this.persist();
  }
  get selectedCandidateId() {
    return (
      this.selectedCandidateIdValue ||
      this.candidates.find((item) => item.text === this.selectedStory)?.candidateId ||
      ''
    );
  }
  private loadStoryReviewFixture() {
    this.storyRecordId = 'LOCAL_MOCK_STORY';
    this.idea = 'Mimi and sticky notes';
    this.title = "Mimi's Sticky Note Mystery";
    this.profile = 'ABSURD_PHYSICS';
    this.storyMode = 'IMPROVE_EXISTING_STORY';
    this.candidates = [
      {
        candidateId: 'candidate-1',
        title: 'A brighter route',
        text: 'Mimi opens the cabinet and the notes follow her to a hidden map.',
      },
      {
        candidateId: 'candidate-2',
        title: 'A quieter route',
        text: 'Mimi opens the cabinet and the notes follow her to a hidden map.',
      },
      {
        candidateId: 'candidate-3',
        title: 'A winding route',
        text: 'Mimi opens the cabinet and the notes follow her to a hidden map.',
      },
    ];
    this.selectedCandidateIdValue = 'candidate-2';
    this.selectedStory = this.candidates[1].text;
    this.storyQuality = null;
    this.reconcileStoryComparison();
    this.reviewBudget = 0.01;
    this.reviewConsent = false;
    this.stage = 'STORY';
  }
  private fixtureReview() {
    this.storyReview = {
      reviewId: 'LOCAL_MOCK_REVIEW',
      sourceRequestId: this.storyRecordId,
      sourceFingerprint: this.storyFingerprint(this.idea),
      reviewModel: 'local-mock',
      reviewModelVersion: 'fixture-v1',
      reviewPolicyVersion: 'story-review-v1',
      reviewTimestamp: new Date().toISOString(),
      reviewStatus: 'COMPLETED',
      diversityAssessment: {
        classification: this.storyQuality?.classification || 'UNKNOWN',
        summary: this.storyQuality?.summary || 'Comparison evidence is unavailable.',
      },
      candidateReviews: this.candidates.map((item) => ({
        candidateId: item.candidateId,
        overallStatus:
          item.candidateId === this.selectedCandidateId ? 'RECOMMENDED' : 'STRONG_CANDIDATE',
        strengths: [],
        concerns: [],
        materialFindings: [],
        editorialRecommendation:
          item.candidateId === this.selectedCandidateId ? 'RECOMMENDED' : 'STRONG_CANDIDATE',
        confidenceOrEvidenceStatus: 'LOCAL_MOCK',
      })),
      recommendedCandidateId: 'candidate-2',
      recommendationReason:
        'Local fixture suggestion only; no independently supported winner is established.',
      overallConcerns: ['Fixture evidence is text-only.'],
      usageAndCost: { provider: 'LOCAL_MOCK', costUpperBoundUsd: 0 },
      evidenceLimitations: ['No provider call or rendered media'],
      revisionComparison: { resolved: [], remaining: ['Keep action visible'], newFindings: [] },
    };
    this.reviewedStoryFingerprints = Object.fromEntries(
      this.candidates.map((item) => [item.candidateId, this.storyFingerprint(item.text)]),
    );
    this.storyReviewStatus = 'CURRENT';
    this.reviewConsent = false;
    this.reviewBusy = false;
    this.persist();
    this.changeDetector.markForCheck();
  }
  reviewStories() {
    if (this.fixtureMode) {
      this.fixtureReview();
      return;
    }
    if (this.reviewBudget <= 0 || !this.reviewConsent || !this.candidates.length) return;
    this.reviewBusy = true;
    this.reviewError = '';
    const payload = {
      role: 'STORY_REVIEW',
      text: this.idea.trim(),
      maxCostUsd: this.reviewBudget,
      context: {
        sourceRequestId: this.storyRecordId,
        sourceFingerprint: this.storyFingerprint(this.idea.trim()),
        storyGenerationMode: this.storyMode,
        lockedRequirements: this.lockedRequirements,
        profile: this.profile,
        mainCharacter: this.selectedCharacterName || null,
        targetDuration: this.duration,
        aspectRatio: this.aspectRatio,
        reviewPolicyVersion: 'story-review-v1',
        candidates: this.candidates.map((item) => ({
          candidateId: item.candidateId,
          text: item.text,
        })),
      },
    };
    this.http.post<any>('/api/v1/intelligence/workflow/creative-role', payload).subscribe({
      next: (r) => {
        if (this.storyReview)
          this.storyReviewHistory = [...this.storyReviewHistory, this.storyReview];
        this.storyReview = this.normalizeStoryReview({
          ...r.result,
          persistedRecordId: r.recordId,
          persistedAt: r.createdAt || r.result?.createdAt || new Date().toISOString(),
        });
        this.storyReviewStatus = 'CURRENT';
        this.reviewedStoryFingerprints = Object.fromEntries(
          this.candidates.map((item) => [item.candidateId, this.storyFingerprint(item.text)]),
        );
        this.reviewConsent = false;
        this.reviewBusy = false;
        this.persist();
        this.changeDetector.markForCheck();
      },
      error: (e) => {
        this.reviewError = this.userMessage(
          String(e?.error?.detail || ''),
          'OpenAI story review could not be completed.',
        );
        this.reviewBusy = false;
        this.changeDetector.markForCheck();
      },
    });
  }
  editCandidate(candidate: StoryCandidate) {
    this.selectStory(candidate);
    this.startStoryEditing();
  }
  startStoryEditing() {
    if (!this.storyRecordId || this.busy) return;
    this.storyEditing = true;
    this.changeDetector.markForCheck();
    setTimeout(() => {
      const editor = document.querySelector<HTMLTextAreaElement>(
        'textarea[aria-label="Selected story"]',
      );
      editor?.focus();
      editor?.setSelectionRange(editor.value.length, editor.value.length);
      editor?.scrollIntoView({ block: 'center' });
    }, 0);
  }
  discardStoryEdits() {
    const source =
      this.selectedCandidateId === 'ORIGINAL_SOURCE'
        ? this.idea
        : this.candidates.find((item) => item.candidateId === this.selectedCandidateId)?.text;
    if (source !== undefined) this.selectedStory = String(source);
    this.storyEditing = false;
    this.persist();
    this.changeDetector.markForCheck();
  }
  refineCandidate(candidate: StoryCandidate) {
    this.selectStory(candidate);
    this.prepareSingleRevision();
  }
  requestMoreDistinct() {
    if (this.storyMode === 'IMPROVE_EXISTING_STORY') return;
    this.stage = 'IDEA';
    this.error =
      'Generate More Distinct Alternatives will use the existing bounded story budget and preserve the current premise.';
  }
  readableDimensions(values: any): string {
    return Array.isArray(values)
      ? values.map((value: string) => this.readableDifference(value)).join(' · ')
      : '';
  }
  readableDifference(value: string): string {
    return String(value || '')
      .replace(/openingVisualPromise/g, 'opening visual promise')
      .replace(/characterGoal/g, 'character goal')
      .replace(/majorStoryChanges/g, 'major story changes')
      .replace(/centralObstacle/g, 'central obstacle')
      .replace(/endingFunction/g, 'ending function')
      .replace(/mainObjectOrSituation/g, 'main object or situation')
      .replace(/escalation/g, 'escalation')
      .replace(/([a-z])([A-Z])/g, '$1 $2')
      .replace(/\s+/g, ' ')
      .trim();
  }
  getPairDifferenceText(pair: any): string {
    if (!pair || !pair.dimensionDescriptions) return '';
    const dims: any = pair.dimensionDescriptions;
    const parts: string[] = [];
    for (const [dim, desc] of Object.entries(dims)) {
      const label = this.readableDimension(dim);
      const d = desc as any;
      const left = String(d[pair.left] || '');
      const right = String(d[pair.right] || '');
      if (left && right) {
        parts.push(`${label}: A${pair.left} "${left}" vs A${pair.right} "${right}"`);
      }
    }
    return parts.join(' · ');
  }
  hasEndingDescription(pair: any): boolean {
    return !!(pair && pair.dimensionDescriptions && pair.dimensionDescriptions.endingEvent);
  }
  get filteredPreferences(): string[] {
    const query = this.preferenceQuery.trim().toLowerCase();
    return this.preferenceOptions.filter((item) => !query || item.toLowerCase().includes(query));
  }
  private updatePreferencePlacement() {
    const picker = document.querySelector('.preference-picker') as HTMLElement | null;
    const rect = picker?.getBoundingClientRect();
    this.preferencePlacement = rect && window.innerHeight - rect.bottom < 300 ? 'above' : 'below';
  }
  togglePreferences() {
    this.preferencesOpen = !this.preferencesOpen;
    if (!this.preferencesOpen) {
      this.preferenceQuery = '';
      return;
    }
    this.updatePreferencePlacement();
  }
  closePreferences() {
    this.preferencesOpen = false;
    this.preferenceQuery = '';
  }
  togglePreference(value: string) {
    this.preferences = this.preferences.includes(value)
      ? this.preferences.filter((item) => item !== value)
      : [...this.preferences, value];
    this.persist();
  }
  removePreference(value: string) {
    this.preferences = this.preferences.filter((item) => item !== value);
    this.persist();
  }
  @HostListener('document:keydown.escape') onEscape() {
    this.closePreferences();
    if (this.reviewDialogOpen) {
      this.closeReviewDialog();
      return;
    }
    if (this.workspaceDialogOpen) this.closeWorkspaceDialog();
    if (this.renameDialogOpen) this.closeRenameDialog();
    if (this.confirmDialogOpen) this.resolveConfirmation(false);
  }
  @HostListener('window:resize') onPreferenceResize() {
    if (this.preferencesOpen) {
      this.updatePreferencePlacement();
      this.changeDetector.markForCheck();
    }
  }
  @HostListener('document:click', ['$event']) onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (this.preferencesOpen && !target.closest('.preference-picker')) {
      this.closePreferences();
      this.changeDetector.markForCheck();
    }
  }
  toggleLockedRequirement(value: string) {
    this.lockedRequirements = this.lockedRequirements.includes(value)
      ? this.lockedRequirements.filter((item) => item !== value)
      : [...this.lockedRequirements, value];
    this.persist();
  }
  saveStoryRevision() {
    if (!this.requireActiveSavedLineage('Save Draft Revision')) return;
    const parent =
      this.selectedCandidateId === 'ORIGINAL_SOURCE'
        ? { candidateId: 'ORIGINAL_SOURCE', title: 'Original Story', text: this.idea }
        : this.candidates.find((item) => item.candidateId === this.selectedCandidateId);
    if (!parent || !this.hasStoryTextChanges() || this.busy) return;
    const parentRevisionId = `${parent.candidateId}-revision-${this.storyFingerprint(parent.text.trim())}`;
    const title = this.storyTitle(this.activeSavedStory!);
    this.busy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.storyRecordId}/story-revisions`, {
        candidateId: parent.candidateId,
        revisionId: parentRevisionId,
        text: this.selectedStory.trim(),
        title,
        visualDirection: this.visualDirection,
      })
      .subscribe({
        next: (revision) => {
          const recordId = String(revision.recordId);
          const result = revision.result || {};
          const alternatives = result.alternatives || [];
          this.storyRecordId = recordId;
          this.approvalRecordId = '';
          this.builderRecordId = '';
          this.builderResult = null;
          this.builderMigration = null;
          this.draftPrompt = '';
          this.promptVersionId = '';
          this.contentId = '';
          this.detailUrl = '/quality/detail';
          this.candidates = alternatives.map((item: any, i: number) => ({
            candidateId: String(item.candidateId || `candidate-${i + 1}`),
            title: item.title || `Alternative ${i + 1}`,
            text: item.text || '',
          }));
          this.selectedCandidateIdValue = this.candidates[0]?.candidateId || '';
          this.selectedStory = this.candidates[0]?.text || '';
          this.storyEditing = false;
          this.storyReview = null;
          this.storyReviewStatus = 'NOT_REVIEWED';
          this.savedStories = [
            {
              recordId,
              title: String(revision.title || title),
              createdAt: revision.createdAt || new Date().toISOString(),
              updatedAt: revision.createdAt || new Date().toISOString(),
              idea: revision.sourceRequest?.text || this.idea,
              sourceType: 'STORY',
              sourceRecordId: revision.sourceRecordId || revision.result?.parentStoryRecordId,
              sourceContext: revision.sourceRequest?.context || {},
              lifecycleStatus: 'DRAFT',
              result,
            } as SavedStoryRecord,
            ...this.savedStories,
          ];
          this.stage = 'STORY';
          this.busy = false;
          this.reconcileStoryComparison();
          this.savedLibraryMessage =
            'Edited story saved as a new draft revision. The approved source remains unchanged.';
          this.persist();
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.busy = false;
          this.fail(e, 'Story revision could not be saved.');
        },
      });
  }
  approveStory() {
    if (!this.requireActiveSavedLineage('Approve Story')) return;
    if (this.fixtureMode) {
      this.approvalRecordId = 'LOCAL_MOCK_APPROVAL';
      this.stage = 'PROMPT';
      this.persist();
      return;
    }
    this.busy = true;
    const payload = {
      approvedText: this.selectedStory.trim(),
      candidateId: this.selectedCandidateId,
      sourceType:
        this.selectedCandidateId === 'ORIGINAL_SOURCE' ? 'ORIGINAL_SOURCE' : 'GENERATED_CANDIDATE',
      sourceRevisionId:
        this.selectedCandidateId === 'ORIGINAL_SOURCE' ? this.storyFingerprint(this.idea) : null,
      revisionId: `${this.selectedCandidateId}-revision-${this.storyFingerprint(this.selectedStory.trim())}`,
      contentFingerprint: this.storyFingerprint(this.selectedStory.trim()),
      reviewRecordId: this.storyReview?.reviewId || null,
      unresolvedEvidence: this.storyReview?.evidenceLimitations || [],
      comparisonClassification: this.storyQuality?.classification || 'UNKNOWN',
      reviewStatus: this.storyReviewStatus,
    };
    this.http
      .post<any>(
        `/api/v1/intelligence/workflow/creative-role/${this.storyRecordId}/approve-story`,
        payload,
      )
      .subscribe({
        next: (r) => {
          this.approvalRecordId = r.recordId;
          this.stage = 'PROMPT';
          this.persist();
          this.done();
        },
        error: (e) => this.fail(e, 'Story approval could not be saved.'),
      });
  }
  buildPrompt() {
    if (!this.requireActiveSavedLineage('Generate Motion Prompt')) return;
    if (this.busy) return;
    this.promptBudget = Number(this.promptBudget);
    if (!Number.isFinite(this.promptBudget) || this.promptBudget <= 0) {
      this.error = 'Enter a prompt budget greater than $0 before requesting OpenAI.';
      return;
    }
    if (this.fixtureMode) {
      this.builderRecordId = 'LOCAL_MOCK_BUILDER';
      this.buildAttemptState = 'LOCAL_MOCK';
      this.draftPrompt = 'LOCAL_MOCK production prompt from the exact approved story revision.';
      this.builderResult = {
        productionPlan: {
          creativeObjective: 'Make the approved action readable.',
          sourceIdentity: { status: 'LOCAL_MOCK' },
          characterBindings: [{ name: this.selectedCharacterName || 'Mimi', status: 'supplied' }],
          visualExecution: {
            openingState: 'Character visible in the opening frame.',
            beats: [],
            mechanism: 'Visible physical mechanism.',
            continuity: 'Identity remains stable.',
            endingState: 'Hard cut.',
          },
          productionConstraints: { duration: this.duration, aspectRatio: this.aspectRatio },
          generatorRisks: [],
          referencePlan: { status: 'NO_REFERENCE_SUPPLIED' },
          evidenceLimitations: ['Local fixture; no provider call.'],
        },
      };
      this.persist();
      return;
    }
    this.busy = true;
    this.promptConsent = false;
    this.error = '';
    this.builderMigration = null;
    this.buildAttemptState = 'REQUESTED';
    this.buildAttemptDiagnostics = null;
    this.http
      .post<any>('/api/v1/intelligence/workflow/creative-role', {
        role: 'BUILD_PROMPT',
        text: this.selectedStory.trim(),
        maxCostUsd: this.promptBudget,
        context: {
          visualDirection: this.visualDirection,
          sourceStoryRecordId: this.storyRecordId,
          candidateId: this.selectedCandidateId,
          approvalRecordId: this.approvalRecordId,
          storyRevisionId: `${this.selectedCandidateId}-revision-${this.storyFingerprint(this.selectedStory.trim())}`,
          storyTitle: this.activeContextTitle,
          storyReviewRecordId: this.storyReview?.reviewId || null,
          reviewConcerns:
            this.storyReview?.candidateReviews?.find(
              (item: any) => item.candidateId === this.selectedCandidateId,
            )?.materialFindings || [],
          constraints: this.constraints,
          mainCharacter: this.selectedCharacterName || null,
          characterRecord: this.selectedCharacter,
          characterReferences:
            this.selectedCharacter?.references || this.selectedCharacter?.referenceAssets || [],
          selectedGenerator: this.targetGenerator,
          targetConfiguration: {
            duration: this.duration,
            aspectRatio: this.aspectRatio,
            selectedGenerator: this.targetGenerator,
            contentProfile: this.profile,
            mainCharacter: this.selectedCharacterName || null,
          },
          promptBuilderContractVersion: 'openart-production-prompt-v2',
          lessonContext: {
            contentProfile: this.profile,
            modelVersion: '',
            duration: this.duration,
            generator: this.targetGenerator,
            settings: { aspectRatio: this.aspectRatio, mode: 'image2video', resolution: '480p' },
          },
        },
      })
      .subscribe({
        next: (r) => {
          if (
            r.attemptState === 'PROVIDER_RESULT_REJECTED' ||
            r.attemptState === 'PROVIDER_OUTCOME_UNKNOWN'
          ) {
            this.buildAttemptState = r.attemptState;
            this.buildAttemptDiagnostics = {
              ...r.attemptDiagnostics,
              recordId: r.recordId,
              reused: Boolean(r.reused),
              callsThisAction: r.reused
                ? 0
                : r.attemptState === 'PROVIDER_OUTCOME_UNKNOWN'
                  ? 'UNKNOWN'
                  : r.calls || 0,
            };
            this.persist();
            this.fail(
              {
                error: {
                  detail: r.attemptDiagnostics?.error || 'Production plan contract is invalid.',
                },
              },
              r.attemptState === 'PROVIDER_OUTCOME_UNKNOWN'
                ? 'OpenAI completion is unknown. This attempt was saved; this exact request will not call the provider again.'
                : 'OpenAI returned a response that failed production-plan validation. The rejected response was saved; this exact request will reuse it without another provider call.',
            );
            return;
          }
          this.builderRecordId = r.recordId;
          this.builderResult = r.result || null;
          this.buildAttemptState = r.reused ? 'REUSED_SAVED_RESULT' : r.attemptState || 'SAVED';
          this.buildAttemptDiagnostics = r.attemptDiagnostics || {
            calls: r.calls || 0,
            reused: Boolean(r.reused),
            persisted: Boolean(r.recordId),
          };
          this.draftPrompt = this.formatPromptForEditor(r.result?.prompt || '');
          this.savedPromptBaseline = this.draftPrompt;
          this.savedPromptTargetSnapshot = this.currentPromptTarget();
          this.promptConsent = false;
          this.persist();
          this.done();
        },
        error: (e) => {
          this.buildAttemptState = 'FAILED_NO_RESULT';
          this.buildAttemptDiagnostics = null;
          this.fail(e, 'OpenAI could not build the production prompt.');
        },
      });
  }
  private formatPromptForEditor(value: string) {
    if (this.builderResult?.productionPlan?.promptTextEdited) return value;
    // Older drafts were split by a single-digit range regex (10-13s became 1\n0-13s).
    // Repair that editor-only presentation while preserving the immutable stored version.
    const repaired = value.replace(
      /(\d)\s*\n(?=\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds)\s*:)/gi,
      '$1',
    );
    return repaired
      .replace(
        /\s+(TITLE \/ FORMAT|VISUAL STYLE|CHARACTER \/ CONTINUITY|TIMED SHOT PLAN|AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)/g,
        '\n\n$1',
      )
      .replace(/(\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds)\s*:)/gi, '\n$1')
      .replace(/^\n+/, '')
      .trim();
  }
  savePrompt() {
    if (this.busy) return;
    if (this.promptVersionId && !this.promptDirty) {
      this.stage = 'PRODUCTION_REVIEW';
      this.detailUrl = `/quality/detail?contentId=${this.contentId}&promptVersionId=${this.promptVersionId}&studio=1`;
      this.persist();
      this.router.navigateByUrl(this.detailUrl);
      return;
    }
    this.busy = true;
    const parent = this.promptVersionId ? Number(this.promptVersionId) : null;
    const saveVersion = (contentId: string, parentPromptVersionId: number | null = null) =>
      this.http.post<any>(`/api/v1/intelligence/contents/${contentId}/prompt-versions`, {
        rawText: this.draftPrompt,
        parsedIr: null,
        parentPromptVersionId,
        creativeRoleRecordId: this.builderRecordId || null,
      });
    const finish = (c: any) => {
      this.contentId = String(c.id || this.contentId);
      saveVersion(this.contentId, parent).subscribe({
        next: (p) => {
          this.promptVersionId = String(p.id);
          this.savedPromptBaseline = this.draftPrompt;
          this.savedPromptTargetSnapshot = this.currentPromptTarget();
          this.stage = 'PRODUCTION_REVIEW';
          this.detailUrl = `/quality/detail?contentId=${this.contentId}&promptVersionId=${p.id}&studio=1`;
          this.persist();
          this.done();
          this.router.navigateByUrl(this.detailUrl);
        },
        error: (e) => this.fail(e, 'Prompt version could not be saved.'),
      });
    };
    if (this.contentId) {
      finish({ id: this.contentId });
      return;
    }
    this.http
      .post<any>('/api/v1/intelligence/contents', {
        title:
          this.title.trim() ||
          (this.activeContextTitle !== 'Not set' ? this.activeContextTitle : '') ||
          this.selectedStory.trim().slice(0, 80) ||
          this.idea.trim().slice(0, 80) ||
          'New Pompom Video',
        description: this.idea.trim() || this.selectedStory.trim(),
        type: this.aspectRatio === '9:16' ? 'REEL' : 'SHORT',
      })
      .subscribe({
        next: finish,
        error: (e) => this.fail(e, 'The content workspace could not be created.'),
      });
  }

  private studioDestroyed = false;
  private initializePromptEditor() {
    if (this.studioDestroyed || this.promptEditor || this.promptEditorLoading || !this.promptMonaco)
      return;
    this.promptEditorLoading = true;
    import('monaco-editor/esm/vs/editor/editor.api')
      .then((monaco) => {
        this.promptEditorLoading = false;
        if (this.studioDestroyed || this.promptEditor || !this.promptMonaco) return;
        this.promptEditor = monaco.editor.create(this.promptMonaco.nativeElement, {
          value: this.draftPrompt,
          language: 'markdown',
          theme: 'vs-dark',
          automaticLayout: true,
          minimap: { enabled: false },
          wordWrap: 'on',
          lineNumbers: 'on',
          padding: { top: 14, bottom: 14 },
          fontSize: 13,
          scrollBeyondLastLine: false,
        });
        this.promptEditor.onDidChangeModelContent(() => {
          if (!this.updatingPromptEditor) {
            this.draftPrompt = this.promptEditor.getValue();
            this.persist();
            this.changeDetector.markForCheck();
          }
        });
      })
      .catch(() => {
        this.promptEditorLoading = false;
        if (!this.studioDestroyed) {
          this.error =
            'The rich editor is unavailable. Use the plain text motion prompt editor below; your draft is retained.';
          this.changeDetector.markForCheck();
        }
      });
  }

  ngAfterViewInit() {
    this.initializePromptEditor();
  }
  ngAfterViewChecked() {
    if (
      this.promptEditor &&
      this.promptEditor.getContainerDomNode() !== this.promptMonaco?.nativeElement
    ) {
      this.promptEditor.dispose();
      this.promptEditor = null;
    }
    this.initializePromptEditor();
  }

  ngOnDestroy() {
    this.studioDestroyed = true;
    this.promptEditor?.dispose();
  }
  private syncPromptEditor() {
    if (this.promptEditor && this.promptEditor.getValue() !== this.draftPrompt) {
      this.updatingPromptEditor = true;
      this.promptEditor.setValue(this.draftPrompt);
      this.updatingPromptEditor = false;
    }
  }
  private done() {
    this.busy = false;
    this.changeDetector.markForCheck();
    setTimeout(() => {
      if (this.studioDestroyed) return;
      this.initializePromptEditor();
      this.syncPromptEditor();
      this.changeDetector.markForCheck();
    }, 0);
  }
  useManualStory() {
    if (this.inputMode === 'DETAILED_STORY') this.saveIdeaDraft(true);
  }
  startNewDraft() {
    if (this.draftSaving || this.busy) return;
    if (this.draftDirty) {
      this.askConfirmation(
        'Start a new draft?',
        'Unsaved changes will be replaced; saved projects remain available.',
        () => this.startNewDraftNow(),
      );
      return;
    }
    this.startNewDraftNow();
  }
  private startNewDraftNow() {
    this.newDraftSnapshot = null;
    this.activeJourney = 'RESUME';
    this.selectJourney('NEW');
    this.persistLocal();
  }
  startExistingPrompt() {
    if (this.activeJourney !== 'NEW') this.selectJourney('NEW');
    this.newStoryOpen = true;
    this.inputMode = 'EXISTING_PROMPT';
    this.onModeChange();
  }
  useExistingPrompt() {
    if (this.inputMode === 'EXISTING_PROMPT') this.saveIdeaDraft(true);
  }
  onModeChange() {
    this.sourceTexts[this.activeSourceMode] = this.idea;
    this.idea = this.sourceTexts[this.inputMode] || '';
    this.activeSourceMode = this.inputMode;
    this.cancelStoryGeneration();
    this.mismatchMessage = '';
    if (!this.storyModeTouched) {
      if (this.inputMode === 'IDEA') this.storyMode = 'EXPLORE_DIFFERENT_STORIES';
      if (this.inputMode === 'DETAILED_STORY') this.storyMode = 'IMPROVE_EXISTING_STORY';
    }
    this.persist();
  }
  useDetailedStoryMode() {
    if (this.inputMode !== 'IDEA') return;
    this.askConfirmation(
      'Use Detailed Story mode?',
      'Your current idea will be copied into the detailed story field. The original idea remains preserved separately.',
      () => {
        this.sourceTexts.IDEA = this.idea;
        this.sourceTexts.DETAILED_STORY = this.idea;
        this.inputMode = 'DETAILED_STORY';
        this.storyMode = 'IMPROVE_EXISTING_STORY';
        this.storyModeTouched = true;
        this.onModeChange();
      },
    );
  }
  applyDurationPreset() {
    if (this.durationPreset !== 'CUSTOM') this.duration = Number(this.durationPreset);
    this.persist();
  }
  get sourceText() {
    return this.idea;
  }
  set sourceText(value: string) {
    this.idea = value;
    this.sourceTexts[this.inputMode] = value;
    this.cancelStoryGeneration();
    this.persist();
  }
  get allSavedProjectCount() {
    return (
      this.savedStories.filter(
        (row) =>
          !this.savedIdeaDrafts.some(
            (draft) => String(draft.storyRecordId || '') === row.recordId,
          ) && this.savedLifecycle(row) !== 'DELETED',
      ).length + this.savedIdeaDrafts.length
    );
  }
  get filteredIdeaDrafts() {
    const q = this.savedStoryQuery.trim().toLowerCase();
    return this.savedIdeaDrafts
      .filter(
        (row) =>
          (this.savedStoryFilter === 'ALL' || this.savedStoryFilter === 'DRAFT') &&
          (!q ||
            String(row.state?.title || '')
              .toLowerCase()
              .includes(q) ||
            String(row.state?.idea || '')
              .toLowerCase()
              .includes(q)),
      )
      .sort(
        (a, b) =>
          Date.parse((this.savedStorySort === 'NEWEST' ? b.createdAt : b.updatedAt) || '') -
          Date.parse((this.savedStorySort === 'NEWEST' ? a.createdAt : a.updatedAt) || ''),
      );
  }
  draftModeLabel(mode: string) {
    return this.inputModes.find((item) => item.value === mode)?.label || 'Draft';
  }
  clearSavedFilters() {
    this.savedStoryQuery = '';
    this.savedStoryFilter = 'ALL';
  }
  get selectedWorkspaceName() {
    return (
      this.workspaces.find((row) => row.folderPath === this.workspacePath)?.creativeName ||
      this.workspacePath
    );
  }
  get suggestedCharacter() {
    const names = this.characters.filter((row) =>
      new RegExp(
        '(^|[^\\p{L}\\p{N}])' +
          row.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') +
          '([^\\p{L}\\p{N}]|$)',
        'iu',
      ).test(this.idea),
    );
    return names.length === 1 ? names[0] : null;
  }
  chooseSuggestedCharacter() {
    if (this.suggestedCharacter) {
      this.mainCharacterId = this.suggestedCharacter.id;
      this.persist();
    }
  }
  get selectedExploration() {
    return this.explorations.find((item) => item.explorationId === this.selectedExplorationId);
  }
  explorationImageUrl(item: any) {
    return `/api/v1/intelligence/workflow/idea-drafts/${this.ideaDraftId}/explorations/${item.explorationId}/image?workspacePath=${encodeURIComponent(this.workspacePath)}`;
  }

  uploadSourceNote = '';
  visualDirection: any = null;
  linkedIdeaStories: SavedStoryRecord[] = [];
  revisionParentId = '';
  originIdeaDraftId = '';
  originIdeaRevision = 0;
  recoverableStoryResponse: any = null;
  canonicalStoryResult: any = null;
  canonicalStoryText = '';
  ideaBrief = '';
  ideaConsent = false;
  ideaBudget = 0.1;
  generatedIdea: any = null;
  generatedIdeaRecordId = '';
  get parentStory() {
    const id = this.activeSavedStory?.sourceRecordId || this.revisionParentId;
    return this.savedStories.find((s) => s.recordId === id) || null;
  }
  get selectedStoryBeats(): string[] {
    return (
      this.selectedStory.match(
        /\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*(?:SEC(?:ONDS)?|s)\s*:[\s\S]*?(?=\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*(?:SEC(?:ONDS)?|s)\s*:|$)/gi,
      ) || []
    );
  }
  get canonicalStoryCurrent() {
    return (
      !!this.canonicalStoryResult &&
      this.canonicalStoryText === this.selectedStory.trim() &&
      this.canonicalStoryResult.boundRequest?.sourceId?.startsWith(
        'draft:story:' + this.storyRecordId + '/',
      )
    );
  }
  get storyProductionDecision() {
    if (!this.canonicalStoryCurrent) return 'PENDING_EVIDENCE';
    const c = this.canonicalStoryResult.canonicalRuleEvaluation;
    if (c?.status !== 'EVALUATED') return 'PENDING_EVIDENCE';
    if (c.failedRules?.some((r: any) => r.severity === 'BLOCKER')) return 'BLOCKED';
    if (c.failedRules?.length) return 'NEEDS_REVISION / HUMAN REVIEW';
    return 'Continue to motion prompt; official first-frame and render gates remain pending';
  }
  focusStoryEditor() {
    document
      .querySelector('textarea[aria-label="Selected story"]')
      ?.scrollIntoView({ block: 'center' });
  }
  validateStory() {
    if (!this.requireActiveSavedLineage('Canonical STORY validation')) return;
    if (this.busy || !this.storyRecordId || this.hasSelectedStoryEdits()) return;
    const id = this.storyRecordId,
      text = this.selectedStory.trim();
    this.busy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${id}/story-validation`, {
        candidateId: this.selectedCandidateId,
      })
      .subscribe({
        next: (r) => {
          this.busy = false;
          if (this.storyRecordId === id) {
            this.canonicalStoryResult = r;
            this.canonicalStoryText = text;
            this.persist();
          }
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e, 'Canonical STORY validation failed to return evidence.'),
      });
  }

  restoreVisualDirection() {
    const context = this.activeSavedStory?.sourceContext || {};
    this.visualDirection = context.visualDirection || null;
    const draft = context.sourceIdeaDraftId,
      workspace = context.workspacePath;
    if (!draft || !workspace) return;
    const story = this.storyRecordId;
    this.http
      .get<any>(`/api/v1/intelligence/workflow/idea-drafts/${draft}/explorations/selection`, {
        params: { workspacePath: workspace },
      })
      .subscribe({
        next: (r) => {
          if (this.storyRecordId !== story) return;
          this.visualDirection = r.explorationId ? r : null;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.visualDirection = null;
          this.changeDetector.markForCheck();
        },
      });
  }

  loadStoryValidation() {
    if (!this.storyRecordId) return;
    const id = this.storyRecordId;
    this.http.get<any[]>(`/api/v1/intelligence/workflow/records/${id}/story-validation`).subscribe({
      next: (rows) => {
        if (this.storyRecordId !== id) return;
        this.canonicalStoryResult = rows[0] || null;
        this.canonicalStoryText = String(
          this.canonicalStoryResult?.boundRequest?.prompt || '',
        ).trim();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.canonicalStoryResult = null;
        this.changeDetector.markForCheck();
      },
    });
  }
  prepareSingleRevision() {
    if (this.busy || this.hasSelectedStoryEdits()) return;
    this.revisionParentId = this.storyRecordId;
    const context = this.activeSavedStory?.sourceContext || {};
    this.originIdeaDraftId = context.sourceIdeaDraftId || this.ideaDraftId;
    this.originIdeaRevision = Number(context.sourceIdeaRevision || this.ideaDraftRevision);
    this.ideaDraftId = '';
    this.ideaDraftRevision = 0;
    this.sessionId = crypto.randomUUID();
    this.activeJourney = 'NEW';
    this.newStoryOpen = true;
    this.inputMode = 'DETAILED_STORY';
    this.sourceTexts = { ...this.sourceTexts, DETAILED_STORY: this.selectedStory };
    this.idea = this.selectedStory;
    this.storyMode = 'IMPROVE_EXISTING_STORY';
    this.storyModeTouched = true;
    this.candidateCount = 1;
    this.stage = 'IDEA';
    this.loadRecoverableStoryResponse();
    this.prepareStoryGeneration();
    this.persist();
  }
  private loadRecoverableStoryResponse() {
    const source = this.revisionParentId;
    if (!source) return;
    this.http
      .get<any>(
        `/api/v1/intelligence/workflow/creative-role/${encodeURIComponent(source)}/recoverable-response`,
      )
      .subscribe({
        next: (r) => {
          if (this.revisionParentId === source) this.recoverableStoryResponse = r;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.recoverableStoryResponse = null;
        },
      });
  }
  previewRecoveredStory() {
    const failedId = String(this.recoverableStoryResponse?.failedRecordId || '');
    if (!failedId || this.busy) return;
    this.busy = true;
    this.http
      .post<any>(
        `/api/v1/intelligence/workflow/records/${encodeURIComponent(failedId)}/recover-provider-response`,
        {},
      )
      .subscribe({
        next: (r) => {
          this.storyRecordId = String(r.recordId);
          this.storyQuality = r.result?.storyQuality || null;
          this.candidates = (r.result?.alternatives || []).map((item: any, i: number) => ({
            candidateId: item.candidateId || `${this.storyRecordId}-candidate-${i + 1}`,
            title: item.title || `Alternative ${i + 1}`,
            text: item.text || '',
          }));
          this.selectedCandidateIdValue = this.candidates[0]?.candidateId || '';
          this.selectedStory = this.candidates[0]?.text || '';
          this.approvalRecordId = '';
          this.recoverableStoryResponse = null;
          this.stage = 'STORY';
          this.busy = false;
          this.reconcileStoryComparison();
          this.persist();
          this.changeDetector.markForCheck();
        },
        error: (e) =>
          this.fail(e, 'Saved response could not be revalidated. No provider call was made.'),
      });
  }
  findLinkedStories() {
    this.linkedIdeaStories = this.savedStories.filter(
      (s) =>
        String(s.sourceContext?.sourceIdeaDraftId || s.sourceContext?.sessionId || '') ===
        this.ideaDraftId,
    );
  }
  uploadExploration(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file || this.explorationBusy || this.draftDirty || !this.uploadSourceNote.trim()) return;
    const id = this.ideaDraftId;
    const data = new FormData();
    data.append('file', file);
    data.append('workspacePath', this.workspacePath);
    data.append('expectedRevision', String(this.ideaDraftRevision));
    data.append('sourceNote', this.uploadSourceNote.trim());
    this.explorationBusy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/idea-drafts/${id}/explorations/upload`, data)
      .subscribe({
        next: (r) => {
          this.explorationBusy = false;
          if (this.ideaDraftId === id) {
            this.explorations = [r, ...this.explorations];
            this.selectedExplorationId = r.explorationId;
          }
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.explorationBusy = false;
          this.explorationError =
            e.error?.detail ||
            e.error?.message ||
            'Image upload failed; no provider call was made.';
          this.changeDetector.markForCheck();
        },
      });
  }
  selectVisualDirection(item: any) {
    const id = this.ideaDraftId;
    this.http
      .post<any>(
        `/api/v1/intelligence/workflow/idea-drafts/${id}/explorations/${item.explorationId}/select`,
        { workspacePath: this.workspacePath },
      )
      .subscribe({
        next: (r) => {
          if (this.ideaDraftId !== id) return;
          this.visualDirection = r;
          this.explorations.forEach(
            (x) => (x.selectedDirection = x.explorationId === item.explorationId),
          );
          this.persist();
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.explorationError =
            e.error?.detail || e.error?.message || 'Visual direction could not be selected.';
          this.changeDetector.markForCheck();
        },
      });
  }
  generateOneIdea() {
    if (
      this.busy ||
      !this.ideaConsent ||
      !this.mainCharacterId ||
      !this.ideaBrief.trim() ||
      this.ideaBudget <= 0
    )
      return;
    this.busy = true;
    this.ideaConsent = false;
    this.http
      .post<any>('/api/v1/intelligence/workflow/creative-role', {
        role: 'IDEA',
        text: this.ideaBrief.trim(),
        maxCostUsd: this.ideaBudget,
        generationAuthorized: true,
        context: {
          mainCharacterId: this.mainCharacterId,
          profile: this.profile,
          targetConfiguration: { contentProfile: this.profile },
        },
      })
      .subscribe({
        next: (r) => {
          this.generatedIdea = r.result;
          this.generatedIdeaRecordId = r.recordId;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e, 'IDEA generation failed; no automatic retry.'),
      });
  }
  useGeneratedIdea() {
    if (!this.generatedIdea) return;
    this.ideaDraftId = '';
    this.ideaDraftRevision = 0;
    this.revisionParentId = '';
    this.originIdeaDraftId = '';
    this.originIdeaRevision = 0;
    this.inputMode = 'IDEA';
    this.idea = JSON.stringify(
      {
        rawProviderConcept: this.generatedIdea,
        sourceProviderRecordId: this.generatedIdeaRecordId,
      },
      null,
      2,
    );
    this.firstFrameDescription = this.generatedIdea.firstStaticFrame;
    this.title = this.generatedIdea.title;
    this.sourceTexts = { IDEA: this.idea, DETAILED_STORY: '', EXISTING_PROMPT: '' };
    this.clearSavedContext();
    this.activeJourney = 'NEW';
    this.newStoryOpen = true;
    this.stage = 'IDEA';
    this.visualDirection = null;
    this.persist();
  }

  openExploration() {
    if (!this.ideaDraftId || this.draftDirty || this.inputMode !== 'IDEA') return;
    this.explorationOpen = true;
    this.explorationConsent = false;
    this.explorationError = '';
    this.explorationReferenceId = '';
    this.explorationReferences = [];
    const id = this.ideaDraftId;
    this.loadExplorations();
    if (this.mainCharacterId)
      this.http.get<any[]>(`/api/v1/characters/${this.mainCharacterId}/references`).subscribe({
        next: (refs) => {
          if (this.ideaDraftId !== id) return;
          this.explorationReferences = (refs || []).filter((ref) =>
            ['VERIFIED', 'APPROVED'].includes(ref.approvalStatus),
          );
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.explorationError = 'Canonical references could not be loaded.';
          this.changeDetector.markForCheck();
        },
      });
  }
  private loadExplorations() {
    const id = this.ideaDraftId;
    this.http
      .get<any[]>(`/api/v1/intelligence/workflow/idea-drafts/${id}/explorations`, {
        params: { workspacePath: this.workspacePath },
      })
      .subscribe({
        next: (rows) => {
          if (this.ideaDraftId !== id) return;
          this.explorations = (rows || []).sort((a, b) =>
            String(b.updatedAt).localeCompare(String(a.updatedAt)),
          );
          this.selectedExplorationId =
            this.explorations.find((r: any) => r.selectedDirection)?.explorationId ||
            this.explorations[0]?.explorationId ||
            '';
          this.visualDirection =
            this.explorations.find(
              (r: any) => r.selectedDirection && r.ideaRevision === this.ideaDraftRevision,
            ) || null;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.explorationError = 'Saved explorations could not be loaded.';
          this.changeDetector.markForCheck();
        },
      });
  }
  generateExploration() {
    if (
      this.explorationBusy ||
      this.draftDirty ||
      !this.explorationConsent ||
      !this.explorationReferenceId ||
      this.explorationBudget <= 0 ||
      !this.ideaDraftId
    )
      return;
    const id = this.ideaDraftId;
    this.explorationBusy = true;
    this.explorationConsent = false;
    this.explorationError = '';
    this.http
      .post<any>(`/api/v1/intelligence/workflow/idea-drafts/${id}/explorations`, {
        explorationId: crypto.randomUUID(),
        workspacePath: this.workspacePath,
        expectedRevision: this.ideaDraftRevision,
        referenceId: this.explorationReferenceId,
        maxCostUsd: this.explorationBudget,
        generationAuthorized: true,
      })
      .subscribe({
        next: (r) => {
          this.explorationBusy = false;
          if (this.ideaDraftId === id) {
            this.explorations = [
              r,
              ...this.explorations.filter((item) => item.explorationId !== r.explorationId),
            ];
            this.selectedExplorationId = r.explorationId;
          }
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.explorationBusy = false;
          this.explorationError = String(
            e?.error?.message ||
              e?.error?.detail ||
              'Exploration did not return a confirmed result. Inspect saved records before any new explicit request; no automatic retry.',
          );
          if (this.ideaDraftId === id) this.loadExplorations();
          this.changeDetector.markForCheck();
        },
      });
  }
  decideExploration(item: any, decision: string) {
    if (!['GENERATED', 'UPLOADED'].includes(item.status)) return;
    this.http
      .post<any>(
        `/api/v1/intelligence/workflow/idea-drafts/${this.ideaDraftId}/explorations/${item.explorationId}/decision`,
        { workspacePath: this.workspacePath, decision, note: this.explorationNote },
      )
      .subscribe({
        next: (r) => {
          item.editorialDecision = r;
          this.changeDetector.markForCheck();
        },
        error: () => {
          this.explorationError = 'Editorial decision could not be saved.';
          this.changeDetector.markForCheck();
        },
      });
  }
  prepareStoryGeneration() {
    if (!this.idea.trim() || !this.workspacePath || this.draftSaving || this.busy) return;
    this.storyConsent = false;
    this.budget = 0;
    this.ideaBatchConsent = false;
    this.generationDialogOpen = true;
  }
  cancelStoryGeneration() {
    this.generationDialogOpen = false;
    this.ideaBatchConsent = false;
    this.storyConsent = false;
    this.budget = 0;
  }
  draftSaveMessage = '';
  private loadIdeaDrafts() {
    this.http.get<any[]>('/api/v1/intelligence/workflow/idea-drafts').subscribe({
      next: (rows) => {
        this.savedIdeaDrafts = rows || [];
        this.savedIndexLoaded();
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.savedIndexLoaded(true);
        this.changeDetector.markForCheck();
      },
    });
  }
  retrySavedProjects() {
    if (this.savedStoriesLoading) return;
    this.savedIndexesPending = 4;
    this.savedIndexLoadFailed = false;
    this.savedStoriesLoading = true;
    this.loadSavedStories();
    this.loadSavedApprovals();
    this.loadSavedStudioSessions();
    this.loadIdeaDrafts();
  }
  saveIdeaDraft(continueAfter = false) {
    if (this.draftSaving || this.draftLoading || this.busy || !this.idea.trim()) return;
    this.cancelStoryGeneration();
    if (!this.ideaDraftId) this.ideaDraftId = crypto.randomUUID();
    this.sessionId = this.ideaDraftId;
    const id = this.ideaDraftId;
    const epoch = this.editorEpoch;
    const state = {
      ...this.captureDraft(),
      storyText: this.inputMode === 'DETAILED_STORY' ? this.idea : undefined,
      promptText: this.inputMode === 'EXISTING_PROMPT' ? this.idea : undefined,
    };
    const snapshot = JSON.stringify(this.captureDraft());
    this.draftSaving = true;
    this.draftSaveMessage = '';
    this.error = '';
    this.http
      .post<any>('/api/v1/intelligence/workflow/idea-drafts', {
        draftId: id,
        expectedRevision: this.ideaDraftRevision,
        state,
      })
      .subscribe({
        next: (r) => this.finishIdeaDraft(r, continueAfter, epoch, id, snapshot),
        error: (e) => {
          this.draftSaving = false;
          this.fail(e, 'Draft could not be saved. Your text is retained.');
        },
      });
  }
  private finishIdeaDraft(
    r: any,
    continueAfter: boolean,
    epoch: number,
    id: string,
    snapshot: string,
  ) {
    if (epoch !== this.editorEpoch || id !== this.ideaDraftId) {
      this.draftSaving = false;
      return;
    }
    if (r?.state?.workspacePath) {
      this.workspacePath = String(r.state.workspacePath);
      this.persistLocal();
    }
    this.ideaDraftRevision = r.revision;
    this.savedIdeaDrafts = [r, ...this.savedIdeaDrafts.filter((row) => row.draftId !== id)];
    const baseline = JSON.parse(snapshot);
    if (r?.state?.workspacePath) baseline.workspacePath = String(r.state.workspacePath);
    this.draftBaseline = baseline;
    this.draftSaving = false;
    this.draftSaveMessage = this.draftDirty
      ? 'Draft saved. Newer changes still need saving.'
      : 'Draft saved without an AI call.';
    this.persistLocal();
    if (continueAfter && !this.draftDirty) this.continueIdeaDraft(r);
    this.changeDetector.markForCheck();
  }
  openIdeaDraft(draft: any) {
    if (this.draftSaving || this.busy) return;
    if (this.draftDirty) {
      this.askConfirmation(
        'Open this saved draft?',
        'Unsaved browser changes will be replaced.',
        () => this.openIdeaDraftNow(draft),
      );
      return;
    }
    this.openIdeaDraftNow(draft);
  }
  private openIdeaDraftNow(draft: any) {
    const epoch = ++this.editorEpoch;
    const snapshot = JSON.stringify(this.captureDraft());
    this.draftLoading = true;
    this.cancelStoryGeneration();
    this.http
      .get<any>(`/api/v1/intelligence/workflow/idea-drafts/${draft.draftId}`, {
        params: { workspacePath: draft.state.workspacePath },
      })
      .subscribe({
        next: (r) => {
          this.draftLoading = false;
          if (epoch !== this.editorEpoch || snapshot !== JSON.stringify(this.captureDraft()))
            return;
          this.clearSavedContext();
          Object.assign(this, { firstFrameDescription: '', ...r.state });
          this.explorationOpen = false;
          this.visualDirection = null;
          this.revisionParentId = String(r.state.revisionParentId || '');
          this.originIdeaDraftId = String(r.state.originIdeaDraftId || '');
          this.originIdeaRevision = Number(r.state.originIdeaRevision || 0);
          this.canonicalStoryResult = null;
          this.linkedIdeaStories = [];
          this.ideaDraftId = r.draftId;
          this.sessionId = r.draftId;
          this.ideaDraftRevision = r.revision;
          this.ideaBatchConsent = false;
          this.budget = 0;
          this.stage = 'IDEA';
          this.loadIdeaCandidates();
          this.sourceTexts = {
            IDEA: '',
            DETAILED_STORY: '',
            EXISTING_PROMPT: '',
            ...r.state.sourceTexts,
            [r.state.inputMode]: r.state.idea,
          };
          this.activeSourceMode = this.inputMode;
          this.activeJourney = 'NEW';
          this.newStoryOpen = true;
          this.draftBaseline = this.captureDraft();
          this.persistLocal();
          if (r.checkpoint !== 'IDEA') this.applyIdeaContinuation(r);
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.draftLoading = false;
          this.fail(e, 'Saved draft could not be reopened.');
        },
      });
  }
  private continueIdeaDraft(draft: any) {
    const epoch = this.editorEpoch;
    const snapshot = JSON.stringify(this.captureDraft());
    this.draftSaving = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/idea-drafts/${draft.draftId}/continue`, {
        expectedRevision: draft.revision,
        workspacePath: this.workspacePath,
      })
      .subscribe({
        next: (r) => {
          this.draftSaving = false;
          if (epoch !== this.editorEpoch || snapshot !== JSON.stringify(this.captureDraft()))
            return;
          this.savedIdeaDrafts = [
            r,
            ...this.savedIdeaDrafts.filter((row) => row.draftId !== r.draftId),
          ];
          this.applyIdeaContinuation(r);
          this.persistLocal();
          this.changeDetector.markForCheck();
        },
        error: (e) => {
          this.draftSaving = false;
          this.fail(e, 'Draft saved, but continuation could not be completed.');
        },
      });
  }
  private applyIdeaContinuation(r: any) {
    if (r.checkpoint === 'STORY' && r.storyRecordId) {
      this.storyRecordId = String(r.storyRecordId);
      this.approvalRecordId = '';
      this.candidates = (r.result?.alternatives || []).map((row: any) => ({ ...row }));
      this.selectedStory = this.candidates[0]?.text || '';
      this.selectedCandidateIdValue = this.candidates[0]?.candidateId || '';
      this.savedStories = [
        {
          recordId: this.storyRecordId,
          title: this.title,
          idea: this.idea,
          workspacePath: this.workspacePath,
          result: r.result,
          sourceType: 'OPERATOR',
          lifecycleStatus: 'DRAFT',
        },
        ...this.savedStories.filter((row) => row.recordId !== this.storyRecordId),
      ];
      this.activeJourney = 'SAVED';
      this.stage = 'STORY';
      this.reconcileStoryComparison();
    } else if (r.checkpoint === 'PRODUCTION_REVIEW' && r.contentId && r.promptVersionId) {
      this.storyRecordId = '';
      this.approvalRecordId = '';
      this.contentId = String(r.contentId);
      this.promptVersionId = String(r.promptVersionId);
      this.draftPrompt = String(r.rawText || this.idea);
      this.savedPromptBaseline = this.draftPrompt;
      this.savedPromptTargetSnapshot = this.currentPromptTarget();
      this.activeJourney = 'RESUME';
      this.stage = 'PRODUCTION_REVIEW';
      this.detailUrl = `/quality/detail?contentId=${this.contentId}&promptVersionId=${this.promptVersionId}&studio=1`;
      this.router.navigateByUrl(this.detailUrl);
    }
  }
  loadWorkspaces() {
    this.workspaceLoading = true;
    this.workspaceError = '';
    this.http.get<any[]>('/api/v1/videos/prompt-workspaces/destinations').subscribe({
      next: (rows) => {
        this.workspaces = rows.map((row) => ({
          folderPath: row.folderPath,
          creativeName: row.creativeName,
        }));
        this.workspaceLoading = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.workspaceLoading = false;
        this.workspaceError = 'Workspaces could not be loaded.';
        this.changeDetector.markForCheck();
      },
    });
  }
  createWorkspace() {
    this.workspaceName = '';
    this.workspaceNameError = '';
    this.workspaceDialogOpen = true;
    setTimeout(() => document.getElementById('workspace-name')?.focus(), 0);
  }
  closeWorkspaceDialog() {
    if (this.workspaceCreating) return;
    this.workspaceDialogOpen = false;
    this.workspaceName = '';
    this.workspaceNameError = '';
  }
  private askConfirmation(title: string, message: string, action: () => void) {
    this.confirmDialogTitle = title;
    this.confirmDialogMessage = message;
    this.pendingConfirmation = action;
    this.confirmDialogOpen = true;
  }
  resolveConfirmation(confirmed: boolean) {
    const action = this.pendingConfirmation;
    this.confirmDialogOpen = false;
    this.pendingConfirmation = null;
    if (confirmed) action?.();
  }
  submitWorkspace() {
    const name = this.workspaceName.trim();
    if (!name) {
      this.workspaceNameError = 'Enter a workspace name.';
      return;
    }
    if (!/^[\p{L}\p{N}][\p{L}\p{N} ._-]{0,99}$/u.test(name) || /[.]$|[ ]$/.test(name)) {
      this.workspaceNameError = 'Use letters, numbers, spaces, dot, underscore or hyphen.';
      return;
    }
    if (this.workspaces.some((row) => row.creativeName.toLowerCase() === name.toLowerCase())) {
      this.workspaceNameError = 'A workspace with this name already exists.';
      return;
    }
    this.workspaceCreating = true;
    this.http
      .post<any>('/api/v1/videos/prompt-workspaces/folders', {
        parentDirectory: 'library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026',
        folderName: name,
      })
      .subscribe({
        next: (r) => {
          this.workspacePath = String(r.folderPath || '');
          this.workspaceCreating = false;
          this.closeWorkspaceDialog();
          this.loadWorkspaces();
          this.persistLocal();
        },
        error: (e) => {
          this.workspaceCreating = false;
          this.workspaceNameError = e?.error?.detail || 'Workspace could not be created.';
          this.changeDetector.markForCheck();
        },
      });
  }
  @HostListener('window:beforeunload', ['$event']) protectUnsavedDraft(event: BeforeUnloadEvent) {
    if (this.newStoryOpen && this.draftDirty) {
      event.preventDefault();
      event.returnValue = '';
    }
  }
  private loadCatalogues() {
    this.http.get<any[]>('/api/v1/characters').subscribe({
      next: (rows) =>
        (this.characters = rows.map((row) => ({ id: String(row.id), name: row.name, raw: row }))),
      error: () => {
        this.characters = [];
        this.characterError = 'Character catalog could not be loaded.';
        this.changeDetector.markForCheck();
      },
    });
    this.loadWorkspaces();
  }
  private fail(response: any, fallback: string) {
    const raw = response?.error?.detail ?? response?.error?.message ?? '';
    const detail = Array.isArray(raw)
      ? raw
          .map((item: any) => String(item?.msg || item?.message || item?.detail || ''))
          .filter(Boolean)
          .join(' ')
      : typeof raw === 'object'
        ? String(raw.message || raw.detail || JSON.stringify(raw))
        : String(raw);
    this.technicalError = detail.trim();
    this.error = this.userMessage(this.technicalError, fallback);
    this.busy = false;
    this.changeDetector.markForCheck();
  }
  private userMessage(detail: string, fallback: string) {
    const value = detail.toLowerCase();
    if (!detail) return fallback;
    if (
      value.includes('maxcostusd') ||
      value.includes('input should be greater than 0') ||
      value.includes('approved cost ceiling') ||
      value.includes('request exceeds') ||
      value.includes('budget')
    )
      return 'Enter a prompt budget greater than $0 (for example 0.10), then try again.';
    if (
      value.includes('structured story_review') ||
      value.includes('candidate ids') ||
      value.includes('source request identity') ||
      value.includes('source fingerprint')
    )
      return 'OpenAI returned a review that did not match the story candidates. Review the same saved story again.';
    if (value.includes('creative roles are disabled'))
      return 'Story generation is disabled on the server. Enable the configured STORY role before continuing.';
    if (value.includes('server model configuration'))
      return 'No story model is configured on the server.';
    if (
      value.includes('empty json') ||
      value.includes('invalid json') ||
      value.includes('empty completion')
    )
      return 'The selected provider returned no usable story data. Check the configured model and API connection, then try again.';
    if (value.includes('price configuration'))
      return 'Story pricing is not configured on the server.';
    if (value.includes('unavailable') || value.includes('connection'))
      return 'The configured AI provider is not ready. Check the server connection.';
    return `${fallback} (${detail})`;
  }
  dismissError() {
    this.error = '';
    this.technicalError = '';
  }
  checkMismatch() {
    const title = this.title.toLowerCase();
    const text = this.idea.toLowerCase();
    const known = this.characters.map((item) => item.name.toLowerCase());
    const mentioned = known.filter((name) => title.includes(name));
    const inText = known.filter((name) => text.includes(name));
    if (mentioned.length && inText.length && !inText.some((name) => mentioned.includes(name))) {
      this.suggestedTitle = `${this.characters.find((item) => inText.includes(item.name.toLowerCase()))?.name || 'Story'}'s New Adventure`;
      this.mismatchMessage = `Your title mentions ${mentioned.join(', ')}, but the idea appears to focus on ${inText.join(', ')}. Would you like to update the title?`;
    } else {
      this.mismatchMessage = '';
    }
  }
  private persistLocal() {
    if (!this.sessionId) this.sessionId = crypto.randomUUID();
    const state = {
      originIdeaDraftId: this.originIdeaDraftId,
      originIdeaRevision: this.originIdeaRevision,
      visualDirection: this.visualDirection,
      revisionParentId: this.revisionParentId,
      canonicalStoryResult: this.canonicalStoryResult,
      canonicalStoryText: this.canonicalStoryText,
      firstFrameDescription: this.firstFrameDescription,
      sessionId: this.sessionId,
      activeJourney: this.activeJourney,
      newStoryOpen: this.newStoryOpen,
      newDraftSnapshot: this.newDraftSnapshot,
      ideaDraftId: this.ideaDraftId,
      ideaDraftRevision: this.ideaDraftRevision,
      sourceTexts: this.sourceTexts,
      savedContextSnapshot: this.savedContextSnapshot,
      inputMode: this.inputMode,
      mainCharacterId: this.mainCharacterId,
      workspacePath: this.workspacePath,
      durationPreset: this.durationPreset,
      candidateCount: this.candidateCount,
      storyProvider: this.storyProvider,
      preferences: this.preferences,
      storyMode: this.storyMode,
      storyModeTouched: this.storyModeTouched,
      lockedRequirements: this.lockedRequirements,
      idea: this.idea,
      title: this.title,
      profile: this.profile,
      duration: this.duration,
      aspectRatio: this.aspectRatio,
      constraints: this.constraints,
      stage: this.stage,
      candidates: this.candidates,
      selectedStory: this.selectedStory,
      storyRecordId: this.storyRecordId,
      storyQuality: this.storyQuality,
      storyReview: this.storyReview,
      storyReviewHistory: this.storyReviewHistory,
      storyReviewStatus: this.storyReviewStatus,
      selectedCandidateIdValue: this.selectedCandidateIdValue,
      reviewedStoryFingerprints: this.reviewedStoryFingerprints,
      approvalRecordId: this.approvalRecordId,
      builderRecordId: this.builderRecordId,
      builderResult: this.builderResult,
      builderMigration: this.builderMigration,
      buildAttemptState: this.buildAttemptState,
      buildAttemptDiagnostics: this.buildAttemptDiagnostics,
      targetGenerator: this.targetGenerator,
      draftPrompt: this.draftPrompt,
      savedPromptBaseline: this.savedPromptBaseline,
      savedPromptTargetSnapshot: this.savedPromptTargetSnapshot,
      contentId: this.contentId,
      promptVersionId: this.promptVersionId,
      detailUrl: this.detailUrl,
      promptBudget: this.promptBudget,
    };
    localStorage.setItem(this.storageKey, JSON.stringify(state));
    return state;
  }
  persist() {
    const state = this.persistLocal();
    if (this.stage === 'IDEA' || !this.storyRecordId) return;
    this.http
      .put(`/api/v1/intelligence/workflow/studio-sessions/${this.sessionId}`, state)
      .subscribe({ error: () => {} });
  }
  private restoreServer(value: any) {
    const localStoryId = String(this.storyRecordId || '');
    const serverStoryId = String(value?.storyRecordId || '');
    if (localStoryId && serverStoryId !== localStoryId) {
      this.sessionId = crypto.randomUUID();
      this.persistLocal();
      return;
    }
    const current = this.stage;
    Object.assign(this, value);
    this.newStoryOpen = Boolean(value.newStoryOpen);
    if (this.activeJourney === 'NEW' && this.stage === 'IDEA') this.clearSavedContext();
    this.activeSourceMode = this.inputMode;
    if (this.promptVersionId && this.stage === 'ANALYSIS') this.stage = 'PRODUCTION_REVIEW';
    this.draftBaseline = this.captureDraft();
    if (this.promptVersionId && !this.savedPromptTargetSnapshot)
      this.savedPromptTargetSnapshot = this.currentPromptTarget();
    if (this.storyReview) this.storyReview = this.normalizeStoryReview(this.storyReview);
    if (!value.stage) this.stage = current; // P0 fix: server session cannot fabricate successful generation without valid storyRecordId
    const isFixtureId = this.storyRecordId && this.storyRecordId.startsWith('LOCAL_MOCK_');
    if ((!this.storyRecordId || isFixtureId) && this.candidates?.length > 0) {
      this.candidates = [];
      this.selectedStory = '';
      this.selectedCandidateIdValue = '';
      this.storyQuality = null;
      this.storyReview = null;
      this.storyReviewHistory = [];
      this.storyReviewStatus = 'NOT_REVIEWED';
      this.stage = 'IDEA';
    } // Reconcile storyQuality after server restore to ensure persisted PARTIALLY_DISTINCT without evidence is corrected
    this.hydrateSavedStoryAssessment();
    if (this.candidates?.length > 0) this.reconcileStoryComparison();
    localStorage.setItem(
      this.storageKey,
      JSON.stringify({
        ...value,
        activeJourney: this.activeJourney,
        storyRecordId: this.storyRecordId,
        approvalRecordId: this.approvalRecordId,
        builderRecordId: this.builderRecordId,
        promptVersionId: this.promptVersionId,
        candidates: this.candidates,
        storyQuality: this.storyQuality,
      }),
    );
  }
  private restore() {
    try {
      const value = JSON.parse(localStorage.getItem(this.storageKey) || 'null');
      if (value) {
        Object.assign(this, value);
        this.newStoryOpen = Boolean(value.newStoryOpen);
        if (this.activeJourney === 'NEW' && this.stage === 'IDEA') this.clearSavedContext();
        this.activeSourceMode = this.inputMode;
        if (this.promptVersionId && this.stage === 'ANALYSIS') this.stage = 'PRODUCTION_REVIEW';
        this.draftBaseline = this.captureDraft();
        if (this.promptVersionId && !this.savedPromptTargetSnapshot)
          this.savedPromptTargetSnapshot = this.currentPromptTarget();
        if (this.storyReview) this.storyReview = this.normalizeStoryReview(this.storyReview); // P0 fix: localStorage cannot fabricate successful generation.
        // Candidates from localStorage are only valid if backed by a persisted backend record.
        // Fixture IDs (LOCAL_MOCK_*) and missing storyRecordId are both invalid.
        const isFixtureId = this.storyRecordId && this.storyRecordId.startsWith('LOCAL_MOCK_');
        if ((!this.storyRecordId || isFixtureId) && this.candidates?.length > 0) {
          this.candidates = [];
          this.selectedStory = '';
          this.selectedCandidateIdValue = '';
          this.storyQuality = null;
          this.storyReview = null;
          this.storyReviewHistory = [];
          this.storyReviewStatus = 'NOT_REVIEWED';
          this.stage = 'IDEA';
        }
        if (this.candidates?.length > 0) this.reconcileStoryComparison();
      }
    } catch {
      localStorage.removeItem(this.storageKey);
    }
  }
}
