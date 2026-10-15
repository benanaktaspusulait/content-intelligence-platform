import { CommonModule } from '@angular/common';
import { afterNextRender, ChangeDetectorRef, Component, ElementRef, EventEmitter, Injector, Input, Output, OnChanges, OnDestroy, QueryList, SimpleChanges, ViewChild, ViewChildren, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterModule } from '@angular/router';
import { Step6GovernanceComponent } from './step6-governance.component';
import { GeneralProducibilityComponent } from './general-producibility.component';

@Component({
  selector: 'app-post-family-workflow',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, GeneralProducibilityComponent, Step6GovernanceComponent],
  template: `
  <p *ngIf="settingsSavedAt && contentProfile !== evaluationProfile" class="missing-state">Existing analysis remains linked to its recorded profile ({{ evaluationProfile }}). Selected profile {{ contentProfile }} has not been evaluated by that historical score; a new evaluation is required before dependent evidence can be reused.</p>
  <section *ngIf="activeStage === 4" class="workflow production-review" aria-label="Production review">
    <div *ngIf="creativeProvenance?.productionSpecificationStatus === 'STALE'" class="missing-state" role="alert"><strong>Production Specification is STALE</strong><p>The original provider plan predates this edited prompt. Its beats and source traceability are not current verified evidence for prompt version {{ promptVersionId }}. This legacy status does not invalidate a separately saved evaluation of the current prompt.</p></div>
    <details *ngIf="creativeProvenance?.approvedStoryText" class="advanced-details"><summary>Approved story · {{ creativeProvenance.storyRevisionId }}</summary><p>{{ creativeProvenance.approvedStoryText }}</p><small>Story {{ creativeProvenance.sourceStoryRecordId }} · {{ creativeProvenance.candidateId }} · approval {{ creativeProvenance.approvalRecordId }}</small></details>
    <nav *ngIf="activeStage === 4" class="stage-subtabs" aria-label="Production Review sections" role="tablist">
      <button *ngFor="let tab of productionTabs" type="button" role="tab" [class.is-active]="activeProductionTab === tab.id" [attr.aria-selected]="activeProductionTab === tab.id" (click)="selectProductionTab(tab.id)">{{ tab.title }}<small>{{ tab.description }}</small></button>
    </nav>

    <section *ngIf="activeProductionTab === 'overview'" class="review-card overview-card">
      <header><div><span class="card-kicker">WORKFLOW OVERVIEW</span><h3>{{ contentTitle || 'Current saved prompt' }}</h3><p class="overview-subtitle">Prompt v{{ promptVersionNumber ?? 'UNKNOWN' }} · ID {{ promptVersionId || 'UNKNOWN' }} · review the saved state before analysis.</p></div><span class="status-pill" [class.status-pill--ready]="analysisReady && !error">{{ error ? 'NEEDS ATTENTION' : (analysisReady ? 'ELIGIBLE FOR PRELIMINARY ANALYSIS' : 'INCOMPLETE') }}</span></header>
      <div class="overview-facts">
        <div><span>Character</span><strong>{{ characterLabel }}</strong></div>
        <div><span>Profile</span><strong>{{ contentProfileLabel }}</strong><small>{{ contentProfileHint }}</small></div>
        <div><span>Duration</span><strong>{{ desiredDuration ? desiredDuration + 's' : 'Not set' }}</strong><small>{{ savedDuration ? 'Saved setting' : 'Needs confirmation' }}</small></div>
        <div><span>Aspect ratio</span><strong>{{ aspectRatio || 'Not set' }}</strong><small>{{ aspectConflict ? 'Saved and prompt values differ' : (savedAspectRatio ? 'Saved setting' : 'Needs confirmation') }}</small></div>
        <div><span>Opening</span><strong>{{ openingStrategyLabel }}</strong><small>{{ openingStrategyHint }}</small></div>
        <div><span>Generator</span><strong>{{ generatorLabel }}</strong><small>{{ generatorHint }}</small></div>
      </div>
      <div class="overview-checklist" aria-label="Production review checklist">
        <div><span class="check-icon" [class.check-icon--ok]="intentConfirmed">{{ intentConfirmed ? '✓' : '!' }}</span><div><strong>Creative intent</strong><small>{{ intentConfirmed ? 'Confirmed for analysis' : 'Review and confirm the source-backed intent' }}</small></div><button type="button" class="button button--secondary" (click)="selectProductionTab('creative')">Review</button></div>
        <div><span class="check-icon" [class.check-icon--ok]="settingsStatus === 'CONFIRMED'">{{ settingsStatus === 'CONFIRMED' ? '✓' : '!' }}</span><div><strong>Production settings</strong><small>{{ settingsStatus === 'CONFIRMED' ? 'Saved settings are confirmed' : settingsStatus }}</small></div><button type="button" class="button button--secondary" (click)="selectProductionTab('creative')">Inspect</button></div>
        <div><span class="check-icon" [class.check-icon--ok]="semanticEvidenceReady">{{ semanticEvidenceReady ? '✓' : '!' }}</span><div><strong>Execution evidence</strong><small>{{ executionEvidenceStatus }}</small></div><button type="button" class="button button--secondary" (click)="selectProductionTab('execution')">Inspect</button></div>
        <div><span class="check-icon" [class.check-icon--ok]="approvedCharacterReference">{{ approvedCharacterReference ? '✓' : '!' }}</span><div><strong>References</strong><small>{{ referenceStatus }} · deferred to Step 7; advisory for text analysis</small></div><button type="button" class="button button--secondary" (click)="selectProductionTab('references')">Manage</button></div>
      </div>
      <div class="overview-next"><div><span class="card-kicker">ANALYSIS ELIGIBILITY</span><strong>{{ analysisReady ? 'READY FOR PRELIMINARY ANALYSIS' : 'Incomplete saved prompt' }}</strong><p>{{ analysisReady ? 'This exact saved prompt version can be evaluated. Analysis eligibility does not mean READY FOR RENDER and grants no render authorization.' : 'A content ID, immutable prompt version and non-empty prompt are required.' }}</p></div></div>
      <div class="review-card readiness-card"><header><div><span class="card-kicker">REQUIREMENTS AND EVIDENCE</span><h3>What is confirmed and what is still missing</h3></div><strong>RENDER NOT READY</strong></header><div class="overview-checklist"><div><span class="check-icon" [class.check-icon--ok]="characterResolvedFromCatalog">{{ characterResolvedFromCatalog ? '✓' : '!' }}</span><div><strong>Character identity</strong><small>{{ characterResolvedFromCatalog ? 'Catalog recognized: ' + characterLabel : 'Not confirmed against character catalog' }}</small></div></div><div><span class="check-icon" [class.check-icon--ok]="settingsStatus === 'CONFIRMED' && contentProfile !== 'AUTO'">{{ contentProfile !== 'AUTO' ? '✓' : '!' }}</span><div><strong>Content profile</strong><small>{{ contentProfileLabel }} · {{ settingsStatus === 'CONFIRMED' && contentProfile !== 'AUTO' ? 'confirmed and saved' : (contentProfile !== 'AUTO' ? 'selection needs saving' : 'suggestion only') }}</small></div></div><div><span class="check-icon" [class.check-icon--ok]="!!desiredDuration">{{ desiredDuration ? '✓' : '!' }}</span><div><strong>Duration / aspect ratio</strong><small>{{ desiredDuration || 'Missing' }}s · {{ aspectRatio || 'Missing' }} · saved values remain separate from prompt text</small></div></div><div><span class="check-icon" [class.check-icon--ok]="capabilityStatus.startsWith('Supported')">{{ capabilityStatus.startsWith('Supported') ? '✓' : '?' }}</span><div><strong>Generator capability</strong><small>{{ generatorLabel }} · {{ capabilityStatus }}</small></div></div><div><span class="check-icon" [class.check-icon--ok]="openingStrategy !== 'AUTO'">{{ openingStrategy !== 'AUTO' ? '✓' : '?' }}</span><div><strong>Opening strategy</strong><small>{{ openingStrategyLabel }} · {{ openingStrategy !== 'AUTO' ? 'operator confirmed' : 'unknown or unconfirmed hypothesis' }}</small></div></div><div><span class="check-icon">!</span><div><strong>Character image reference</strong><small>{{ references.length ? 'Candidate exists; approval and stable version must be verified' : 'Missing approved canonical reference' }}</small></div></div><div><span class="check-icon">!</span><div><strong>First-frame image</strong><small>Not generated · scheduled for Render Preparation after Quality Analysis</small></div></div></div></div>
    </section>
    <section *ngIf="activeProductionTab === 'creative'" class="review-card intent-card"><header><div><span class="card-kicker">CREATIVE INTENT</span><h3>What must be preserved</h3></div><span class="source-badge">{{ intentConfirmed ? 'Confirmed source' : (creativeProvenance?.approvedStoryText ? 'Approved story / saved prompt · review pending' : 'Prompt-derived evidence · review pending') }}</span></header><p class="setting-note"><b>Creative objective: {{ intentConfirmed ? 'Operator-reviewed; outcome evidence UNKNOWN' : 'NEEDS_CONFIRMATION' }}.</b> The saved prompt supplies actions and a playful presentation; adult-first discovery, retention, completion and intentional rewatch are not independently established objectives. Review the approved story and preserve its visual curiosity and repeated causal escalation. Comedy is optional.</p><p *ngIf="protectedIntent" class="intent-summary">Protected intent / operator draft: {{ protectedIntent }}</p><div class="intent-grid"><div><span>Main character</span><strong>{{ characterLabel }}</strong><small>Catalog/source identity</small></div><div><span>Central object / situation</span><strong>{{ intentObject }}</strong><small>Source-backed extraction</small></div><div><span>Core mechanism</span><strong>{{ intentMechanism }}</strong><small>Source evidence and semantic interpretation are kept separate.</small></div><div><span>Essential progression</span><strong>{{ intentProgression }}</strong><small>Observable consequence</small></div><div><span>Essential ending</span><strong>{{ intentEnding }}</strong><small>{{ sourceEvents.length ? 'Final visual event present; semantic payoff pending' : 'Source ending evidence unavailable' }}</small></div><div><span>Needs clarification</span><strong>{{ intentAmbiguity }}</strong><small>Unresolved source relationship</small></div></div><div class="intent-actions"><button type="button" class="button button--primary" (click)="confirmIntent()" [disabled]="busy || !intentAvailable || !contentId || !promptVersionId">{{ intentConfirmed ? 'Intent confirmed' : 'Confirm supported intent' }}</button><button type="button" class="button button--secondary" (click)="intentEditing=!intentEditing">{{ intentEditing ? 'Hide intent editor' : 'Correct intent' }}</button><details><summary>View source evidence</summary><p>Source: approved story / saved prompt · version {{ promptVersionId || 'UNKNOWN' }}</p><p>{{ extractedIntent || 'No meaningful intent evidence found.' }}</p></details></div><textarea *ngIf="intentEditing" [(ngModel)]="protectedIntent" (ngModelChange)="intentConfirmed=false" rows="4" placeholder="Add an operator correction; this will remain distinct from extracted evidence"></textarea></section>
    <section *ngIf="activeProductionTab === 'creative'" class="review-card"><header><div><span class="card-kicker">CREATIVE & SETTINGS</span><h3>Inherited workflow settings</h3></div><div class="intent-actions"><span class="status-pill" [class.status-pill--ready]="settingsStatus==='CONFIRMED'">{{ settingsStatus }}</span><button type="button" class="button button--secondary" (click)="settingsEditing=!settingsEditing">{{ settingsEditing ? 'Close settings' : 'Edit settings' }}</button></div></header><p *ngIf="profileMismatch" class="missing-state"><strong>Content Profile Review Recommended.</strong> The source appears discovery-oriented while the selected profile is Absurd Physics. Keep the current profile or choose another supported profile; no automatic override was made.</p><div class="settings-grid"><div><span>Main character</span><strong>{{ characterLabel || 'Unknown' }}</strong><small>{{ characterResolvedFromCatalog ? 'Catalog identity recognized from source prompt' : (characterLabel ? 'Saved source association' : 'Missing authoritative character record') }}</small></div><div><span>Content profile</span><strong>{{ contentProfileLabel }}</strong><small>{{ contentProfileHint }}</small></div><div><span>Target duration</span><strong>{{ desiredDuration ? desiredDuration + ' seconds' : 'Missing' }}</strong><small>{{ durationConflict ? 'Conflict: saved setting ' + savedDuration + 's · prompt text ' + promptDuration + 's' : (savedDuration ? 'Saved production setting' : (promptDuration ? 'Read from source prompt; confirm if authoritative' : 'Needs confirmation')) }}</small></div><div><span>Aspect ratio</span><strong>{{ aspectRatio || 'Missing' }}</strong><small>{{ aspectConflict ? 'Conflict: saved setting ' + savedAspectRatio + ' · prompt text ' + promptAspectRatio : (savedAspectRatio ? 'Saved production setting' : (promptAspectRatio ? 'Read from source prompt; confirm if authoritative' : 'Needs confirmation')) }}</small></div><div><span>Target generator</span><strong>{{ generatorLabel }}</strong><small>{{ generatorHint }}</small></div><div><span>Opening strategy</span><strong>{{ openingStrategyLabel }}</strong><small>{{ openingStrategyHint }}</small></div></div><div *ngIf="settingsEditing" class="settings-editor"><label>Content profile<select [(ngModel)]="contentProfile"><option value="AUTO">Source-based suggestion</option><option value="ABSURD_PHYSICS">Absurd Physics</option><option value="CURIOSITY_ADVENTURE">Curiosity / adventure</option><option value="EDUCATIONAL">Educational</option><option value="MIXED">Mixed</option></select></label><label>Target duration (seconds)<input type="number" min="1" [(ngModel)]="desiredDuration"></label><label>Aspect ratio<select [(ngModel)]="aspectRatio"><option value="">Needs confirmation</option><option>9:16</option><option>16:9</option><option>1:1</option></select></label><label>Target generator<select [(ngModel)]="generator"><option value="AUTO">System suggestion</option><option value="SEEDANCE_2_0_MINI">Seedance 2.0 Mini</option><option value="SEEDANCE_2_5">Seedance 2.5</option></select></label><label>Opening strategy<select [(ngModel)]="openingStrategy"><option value="AUTO">Unknown / not confirmed</option><option value="INSTANT_IMPOSSIBLE">Instant impossible event</option><option value="IMMEDIATE_PROBLEM">Immediate problem</option><option value="CURIOSITY_DISCOVERY">Curiosity / discovery</option><option value="SUGGESTION">Suggestion</option></select><small>{{ openingStrategy === 'AUTO' ? openingProposal.reason : 'Previously saved operator selection is preserved unless changed here.' }}</small></label><button type="button" class="button button--primary settings-apply" (click)="applySettings()" [disabled]="busy || !contentId || !promptVersionId">{{ settingsSavedAt ? 'Apply changes' : 'Save settings' }}</button><small class="setting-note" *ngIf="settingsSavedAt">Saved {{ settingsSavedAt | date:'medium' }}</small></div></section>
    <section *ngIf="activeProductionTab === 'references'" class="review-card"><header><div><span class="card-kicker">VISUAL REFERENCES</span><h3>Character and first frame</h3></div><span class="status-pill">{{ firstFrameStatus }}</span></header><div class="reference-summary"><div><strong>{{ referenceCharacter || characterLabel || 'Character identity' }}</strong><span>{{ referenceStatus }}</span></div><div *ngIf="activeStage !== 4 && approvedCharacterReferences.length" class="reference-binding-control"><label>Select approved character reference<select [(ngModel)]="selectedReferenceId"><option value="">Choose approved reference</option><option *ngFor="let ref of approvedCharacterReferences" [value]="ref.id">Version {{ ref.version }} · {{ ref.sha256.slice(0,12) }} · {{ ref.relativePath }}</option></select></label><button type="button" class="button button--primary" (click)="bindCharacterReference()" [disabled]="busy || !selectedReferenceId">Bind selected reference</button></div><div *ngIf="selectedReferencePreview" class="selected-reference-preview"><img [src]="selectedReferencePreview.previewUrl" [alt]="characterLabel + ' approved visual reference'" /><span>Version {{ selectedReferencePreview.version }} · SHA-256 {{ selectedReferencePreview.sha256 }}</span></div><div><strong>First frame</strong><span>{{ firstFrameStatus }} · generated only in Render Preparation after Quality Analysis</span></div><div><strong>Opening visual assessment</strong><span>Planned source assessment: {{ plannedOpeningAssessment }}</span><small>Actual first-two-seconds assessment: pending Video QA</small></div></div><div *ngIf="references.length" class="reference-candidate-list"><article *ngFor="let ref of references"><strong>{{ ref.character || characterLabel }} · {{ ref.kind }}</strong><span>{{ ref.relativePath }}</span><small>{{ ref.status === 'APPROVED' && ref.sha256 ? 'Approved asset identity is recorded; final binding belongs to Step 7.' : 'Unverified candidate from saved evidence.' }}</small></article></div><p *ngIf="!references.length" class="missing-state"><strong>Character identity is {{ characterResolvedFromCatalog ? 'catalog-confirmed' : 'source-derived' }}; visual identity is not verified.</strong> MISSING_VERIFIED_REFERENCE for content {{ contentId }} / prompt {{ promptVersionId }}. No approved reference asset is bound. Open Characters to upload a reference, inspect its image and explicitly approve it. Step 7 owns final reference binding and start-frame preparation. Missing images do not invalidate this saved text prompt or block preliminary analysis. No image will be generated from this screen.</p><div class="intent-actions"><a class="button button--secondary" routerLink="/characters">Open Characters</a><a class="button button--secondary" [href]="renderPreparationLink()">Open Render Preparation</a></div><p class="setting-note">The first frame defines the opening composition. Prepare, validate and accept it in Render after Quality Analysis; Step 4 never triggers image generation.</p><details *ngIf="retrievedLessons.length" class="lesson-context"><summary>{{ retrievedLessons.length }} relevant lesson(s)</summary><p *ngFor="let lesson of retrievedLessons">{{ lesson.hypothesis }}</p></details></section>
    <section *ngIf="activeProductionTab === 'execution'" class="review-card execution-card"><header><div><span class="card-kicker">VISUAL EXECUTION PLAN</span><h3>Source-backed production events</h3></div><span class="status-pill">{{ executionEvidenceStatus }} · {{ sourceEvents.length }} candidates</span></header><p class="setting-note"><b>Current source:</b> saved prompt version {{ promptVersionId }}. Action text and arrow consequences below are textual evidence; role suggestions are local interpretations.</p><p class="setting-note"><b>Narrative fidelity:</b> compare these intervals with the approved story above. A matching story fingerprint establishes ancestry only. Independent semantic fidelity is UNKNOWN; rendered visual fidelity awaits Video QA. One beat per story sentence is not required.</p><p *ngIf="creativeProvenance?.productionSpecificationStatus === 'STALE'" class="setting-note"><b>Legacy provider evidence: STALE.</b> Missing sourceEvidence in the original response leaves provider traceability UNKNOWN (the legacy 0/9 does not assess this edited prompt).</p><details *ngIf="creativeProvenance?.creativeRoleRecordId" class="advanced-details"><summary>Original provider specification · {{ creativeProvenance.productionSpecificationStatus || 'UNKNOWN' }}</summary><p>Provider-derived historical data; never treated as the current prompt plan or independent semantic verification.</p><button type="button" class="button button--secondary" (click)="loadLegacySpecification()">Inspect legacy provider evidence</button><div *ngIf="legacyProductionPlan"><p><b>Original creative objective (AI-derived):</b> {{ legacyProductionPlan.creativeObjective || 'UNKNOWN' }}</p><p><b>Original traceability:</b> {{ legacyProductionPlan.storyPromptFidelity?.traceableSentenceCount ?? 'UNKNOWN' }}/{{ legacyProductionPlan.storyPromptFidelity?.sourceSentenceCount ?? 'UNKNOWN' }} · {{ legacyProductionPlan.storyPromptFidelity?.status || 'UNKNOWN' }}. This concerns provenance of the original response.</p><pre>{{ legacyProductionPlan.visualExecution?.beats | json }}</pre></div><p *ngIf="legacyEvidenceError" class="error">{{ legacyEvidenceError }}</p></details><p class="setting-note">A timed range is a source event candidate, not automatically a major narrative beat. Proposed roles are deterministic suggestions; operator decisions are saved with provenance.</p><div *ngIf="timedRangeIssues.length" class="missing-state"><strong>Source extraction needs review.</strong> {{ timedRangeIssues.join(' ') }} These ranges remain UNKNOWN until reviewed.</div><div *ngIf="sourceEvents.length; else noBeatEvidence" class="beat-list"><article *ngFor="let event of sourceEvents; trackBy: trackSourceEvent"><strong>{{ event.start }}–{{ event.end }} s · {{ event.savedRole || event.proposedRole }} <small>({{ event.savedRole ? 'operator-confirmed' : event.roleEvidence }})</small></strong><p><b>Actor:</b> {{ eventDrafts[event.id]?.actor || event.actor }} · <b>Primary object:</b> {{ eventDrafts[event.id]?.primaryObject || event.primaryObject }}</p><p><b>Environment / target:</b> {{ eventDrafts[event.id]?.environment || event.environment }} · <b>Obstacle:</b> {{ event.obstacle }}</p><p><b>Action:</b> {{ eventDrafts[event.id]?.action || event.action }}</p><p><b>Planned consequence:</b> {{ eventDrafts[event.id]?.consequence || event.consequence }}</p><details class="advanced-details"><summary>Review or correct this interpretation</summary><label>Semantic role<select [ngModel]="eventDrafts[event.id]?.role || event.savedRole || event.proposedRole" (ngModelChange)="setEventDraft(event.id,'role',$event)"><option value="">Keep pending</option><option *ngFor="let role of semanticRoles" [value]="role">{{ role }}</option></select></label><label>Correct actor<input [ngModel]="eventDrafts[event.id]?.actor || event.actor" (ngModelChange)="setEventDraft(event.id,'actor',$event)" /></label><label>Correct primary object<input [ngModel]="eventDrafts[event.id]?.primaryObject || event.primaryObject" (ngModelChange)="setEventDraft(event.id,'primaryObject',$event)" /></label><label>Correct environment / target<input [ngModel]="eventDrafts[event.id]?.environment || event.environment" (ngModelChange)="setEventDraft(event.id,'environment',$event)" /></label><label>Correct action<textarea [ngModel]="eventDrafts[event.id]?.action || event.action" (ngModelChange)="setEventDraft(event.id,'action',$event)" rows="2"></textarea></label><label>Correct planned consequence<textarea [ngModel]="eventDrafts[event.id]?.consequence || event.consequence" (ngModelChange)="setEventDraft(event.id,'consequence',$event)" rows="2"></textarea></label><label>Operator clarification (optional)<input [ngModel]="eventDrafts[event.id]?.note || ''" (ngModelChange)="setEventDraft(event.id,'note',$event)" placeholder="Clarify causal relationship or evidence limitation" /></label><button type="button" class="button button--secondary" (click)="saveEventClassification(event)" [disabled]="busy || !eventDrafts[event.id]?.role">Save operator interpretation</button></details><small>Classification: {{ event.savedRole ? 'OPERATOR_CONFIRMED' : (eventDrafts[event.id]?.role ? 'UNSAVED DRAFT' : event.semanticStatus) }} · source evidence {{ event.evidence }}</small><button type="button" class="source-quote-toggle" [attr.aria-expanded]="isSourceQuoteOpen(event.id)" (click)="toggleSourceQuote(event.id)">{{ isSourceQuoteOpen(event.id) ? 'Hide source quote' : 'Show source quote' }}</button><div *ngIf="isSourceQuoteOpen(event.id)" class="source-quote-panel"><span>Exact source · prompt version {{ promptVersionId || 'UNKNOWN' }}</span><p>{{ event.sourceQuote }}</p></div></article></div><ng-template #noBeatEvidence><p class="missing-state">No source-backed timing or event evidence is available. Analysis may record UNKNOWN.</p></ng-template><section class="conflict-review" *ngIf="creativeConflicts.length"><header><div><span class="card-kicker">CREATIVE MECHANISM REVIEW</span><h3>Clarify possible causal conflicts</h3></div></header><article *ngFor="let issue of creativeConflicts"><strong>{{ issue.title }} · {{ issue.status }}</strong><p>{{ issue.explanation }}</p><blockquote>{{ issue.sourceEvidence }}</blockquote><p><b>Minimal optional repair:</b> {{ issue.suggestion }}</p><label>Decision<select [ngModel]="conflictDrafts[issue.id]?.decision || issue.savedDecision" (ngModelChange)="setConflictDraft(issue.id,'decision',$event)"><option value="">No decision yet</option><option value="ACCEPT">Accept suggestion</option><option value="MODIFY">Modify suggestion</option><option value="REJECT">Reject suggestion</option></select></label><textarea *ngIf="conflictDrafts[issue.id]?.decision==='MODIFY' || issue.savedDecision==='MODIFY'" [ngModel]="conflictDrafts[issue.id]?.modifiedSuggestion || issue.savedSuggestion || ''" (ngModelChange)="setConflictDraft(issue.id,'modifiedSuggestion',$event)" rows="2" placeholder="Write the modified suggestion; approved story stays unchanged"></textarea><button type="button" class="button button--secondary" (click)="saveConflictDecision(issue)" [disabled]="busy || !conflictDrafts[issue.id]?.decision">Save decision</button><small>Saving a decision records provenance; it never edits the approved story or saved prompt.</small></article></section><details class="advanced-details"><summary>Advanced evidence details</summary><dl class="diagnostic-list"><div><dt>Extraction</dt><dd>Deterministic source/timeline parsing</dd></div><div><dt>Source version</dt><dd>{{ promptVersionId || 'UNKNOWN' }}</dd></div><div><dt>Classification</dt><dd>{{ semanticClassificationStatus }} · PENDING is preserved until operator confirmation or supported evidence</dd></div><div><dt>Event count</dt><dd>{{ sourceEvents.length }}</dd></div></dl><details class="developer-json"><summary>Developer-only raw JSON</summary><pre>{{ sourceEvents | json }}</pre></details></details></section>

    <details *ngIf="activeProductionTab === 'creative'" class="advanced-details technical-settings"><summary>Advanced details</summary><div class="advanced-groups"><section><h4>Configuration diagnostics</h4><p>Production settings are edited in the single canonical form above.</p><p><b>Selection provenance:</b> {{ settingsSavedAt ? 'Persisted workflow setting' : 'Not yet saved' }}</p><p><b>Opening strategy:</b> {{ openingStrategyLabel }} · {{ openingStrategyHint }}</p></section><section><h4>Creative context</h4><p><b>Protected intent provenance:</b> {{ intentConfirmed ? 'Explicit Step 4 reviewer decision' : 'Unconfirmed source or operator draft' }}</p><p><b>Applicable lessons:</b> {{ retrievedLessons.length ? retrievedLessons.length + ' verified lesson(s)' : 'None found' }}</p><p><b>First-frame responsibility:</b> Render step owns visual preparation, generation, validation and acceptance.</p></section><section><h4>Visual reference diagnostics</h4><p><b>Character identity:</b> {{ characterLabel }} · {{ characterResolvedFromCatalog ? 'catalog recognized' : 'saved association or unresolved' }}</p><p><b>Character assets:</b> {{ referenceStatus }}</p><p><b>First frame:</b> {{ firstFrameStatus }} · no generation is triggered here.</p></section><section><h4>Developer diagnostics</h4><dl class="diagnostic-list"><div><dt>Workflow policy</dt><dd>{{ profile }}</dd></div><div><dt>Prompt version</dt><dd>{{ promptVersionId || 'UNKNOWN' }}</dd></div><div><dt>Content ID</dt><dd>{{ contentId || 'UNKNOWN' }}</dd></div><div><dt>Prompt hash</dt><dd>{{ review?.boundRequest?.promptSha256 || 'Available in saved prompt version endpoint' }}</dd></div><div><dt>Source reload</dt><dd><button type="button" (click)="loadSourceIntent()" [disabled]="busy || !contentId || !promptVersionId">Reload source evidence</button></dd></div></dl></section></div></details>
    <p class="error" role="alert" *ngIf="error">{{ error }}</p>
        <footer class="stage-action-bar" aria-label="Production Review actions"><button type="button" class="button button--secondary" (click)="selectStage(3)">← Back to Prompt</button><div><span class="card-kicker">NEXT ACTION</span><strong>{{ analysisReady ? 'Continue to Quality Analysis' : 'Complete the saved prompt requirements' }}</strong><small>{{ analysisReady ? (isCurrent() ? 'Reuses this exact saved review without another evaluation call; render authorization remains separate.' : 'Evaluates this saved content and prompt version; no render authorization is granted.') : 'Content ID, prompt version and prompt text are required.' }}</small></div><button type="button" class="button button--primary" (click)="continueToQualityAnalysis()" [disabled]="busy || !analysisReady || profile !== 'post-family-v1'">{{ busy ? 'Preparing evidence…' : 'Continue to Quality Analysis →' }}</button></footer>
  </section>
<ng-container *ngIf="review as r"><ng-container *ngIf="activeStage >= 5"><ng-container *ngIf="activeStage === 5">
        <nav class="stage-subtabs analysis-tabs" aria-label="Quality Analysis sections" role="tablist">
          <button *ngFor="let tab of analysisTabs" type="button" role="tab" [attr.aria-selected]="activeAnalysisTab === tab.id" [class.is-active]="activeAnalysisTab === tab.id" (click)="selectAnalysisTab(tab.id)">{{ tab.title }}<small>{{ tab.description }}</small></button>
        </nav>
        <div class="analysis-stage-toolbar"><span><b>Saved analysis</b><small>{{ r.recordId ? 'Run ' + r.recordId.slice(0, 8) : 'Analysis identity unavailable' }} · {{ r.promptVersionId || promptVersionId || 'UNKNOWN' }} · {{ analysisExportState }}</small></span><span class="toolbar-action"><a class="button button--primary" [class.disabled-link]="analysisExportState !== 'ANALYSIS_AVAILABLE'" [attr.aria-disabled]="analysisExportState !== 'ANALYSIS_AVAILABLE'" [href]="analysisExportState === 'ANALYSIS_AVAILABLE' ? '/api/v1/intelligence/workflow/records/' + r.recordId + '/pdf' : null" target="_blank" download>⇩ Export Analysis PDF</a><small>{{ analysisExportMessage }}</small></span></div>
        <ng-container *ngIf="activeAnalysisTab === 'summary'">
        <p class="error" *ngIf="!isCurrent()">
          Prompt, version, reference or setting changed. This review is stale; run it again.
        </p>
        <div class="facts" *ngIf="(qa || r).operatorReport as report">
          <p *ngFor="let row of analysisReportRows(report)">
            <strong>{{ row.label }}</strong
            ><br />{{ cleanAnalysisText(row.text) }}
          </p>
        </div>
        <div class="inputs">
          <article>
            <strong>Prompt / plan quality</strong>
            <p>{{ r.planQuality?.status || 'UNKNOWN' }} · {{ r.planQuality?.recommendation }}</p>
          </article>
          <article>
            <strong>Local execution check</strong>
            <p>{{ r.executionRisk?.status || 'UNKNOWN' }} · {{ r.executionRisk?.findings?.length || 0 }} local findings</p><small>Local text critic only. PASS means no local findings were recorded; actual generator success remains UNKNOWN.</small>
          </article>
          <article><strong>Generator capability</strong><p>{{ r.generation?.capabilityStatus || 'UNKNOWN' }} · {{ r.generation?.desiredDuration ?? 'UNKNOWN' }}s · {{ r.generation?.settings?.aspectRatio || 'UNKNOWN' }}</p><small>Recorded schema support; required inputs and creative producibility are separate.</small></article><article *ngIf="r.generalProducibility">
            <strong>Production complexity</strong>
            <p>{{ r.generalProducibility?.status || r.generalProducibility?.overallStatus || 'UNKNOWN' }}</p><small>Text-based producibility assessment from LocalExecutionCritic; actual render success remains UNKNOWN.</small>
          </article>
          <article>
            <strong>Actual render quality</strong>
            <p>
              Plan fidelity: {{ qa?.planFidelity || 'UNKNOWN' }} · Usability:
              {{ qa?.viewerFacingUsability || 'UNKNOWN' }}
            </p>
          </article>
          <article>
            <strong>Audience / distribution outcome</strong>
            <p>{{ measurement ? 'Measurement is stored separately' : 'Not associated yet' }}</p>
          </article>
        </div>
        <section class="analysis-summary-decision" aria-label="Analysis decision summary"><div><span>Analysis status</span><strong>{{ r.reviewStatus || r.status || 'COMPLETED' }}</strong></div><div><span>Creative quality</span><strong>{{ r.family8?.creativeQuality?.creativeGrade || r.planQuality?.status || 'UNKNOWN' }}</strong></div><div><span>Render authorization</span><strong>{{ authorizationLabel(r.family8?.renderAuthorization?.status) }}</strong><small>{{ r.family8?.renderAuthorization?.status || 'UNKNOWN' }}</small></div><div><span>Recommendation</span><strong>{{ r.planQuality?.recommendation || r.recommendation || 'No supported recommendation recorded' }}</strong></div></section>
        <section id="findings-resolution" class="findings-resolution" aria-label="Findings resolution" *ngIf="resolutionItems().length"><header><div><span class="card-kicker">FINDINGS RESOLUTION</span><h3>What needs to happen next</h3><p>Each item is derived from this saved analysis run and canonical authorization result. These actions do not call a provider.</p></div></header><div class="resolution-list"><article *ngFor="let item of resolutionItems()" class="resolution-item" [class.resolution-item--blocking]="item.blocking"><div class="resolution-item__title"><span class="resolution-category">{{ item.category.replaceAll('_', ' ') }}</span><strong>{{ item.finding }}</strong></div><p>{{ item.why }}</p><small><b>Finding ID:</b> {{ item.id || item.category }} · <b>Status:</b> {{ item.status || 'NEEDS_ACTION' }} · <b>Impact:</b> {{ item.severity || (item.blocking ? 'BLOCKING' : 'REVIEW') }}</small><small><b>Evidence:</b> {{ item.evidence || item.why }}</small><small><b>Required action:</b> {{ item.action }} · <b>Owner:</b> {{ item.owner }} · <b>Revalidate:</b> {{ item.revalidationRequired === false ? 'No' : 'Yes' }} · <b>Prompt revision:</b> {{ item.promptRevisionRequired ? 'Required' : 'Not currently required' }}</small><details *ngIf="item.relatedReasons?.length"><summary>Recorded authorization evidence ({{ item.relatedReasons.length }})</summary><p *ngFor="let reason of item.relatedReasons">{{ reason.code }} · {{ reason.source }} · {{ reason.message }} · references {{ reason.references?.join(', ') || 'UNKNOWN' }}</p></details><a *ngIf="item.target === 7" class="button button--secondary" [href]="renderPreparationLink(item)">{{ item.button }}</a><button *ngIf="item.target !== 7" type="button" class="button button--secondary" (click)="resolveFinding(item)">{{ item.button }}</button></article></div></section>

        <section class="canonical-rule-evaluation" aria-label="Canonical Rule Evaluation" *ngIf="r.canonicalRuleEvaluation as canonical">
          <header>
            <span class="card-kicker">CANONICAL RULE EVALUATION</span>
            <h3>Deterministic rule-based quality assessment</h3>
            <p>This section uses the existing canonical Rule Engine (F1–F10 families). It is separate from the Local Execution Review above and does not call a paid provider.</p>
          </header>
          <div class="canonical-summary-grid" *ngIf="canonical.status === 'EVALUATED'">
            <div><span>Ruleset version</span><strong>{{ canonical.rulesetVersion || 'UNKNOWN' }}</strong></div>
            <div><span>Overall score</span><strong>{{ canonical.score | number:'1.1-1' }} / 100</strong><small>Provisional text-based assessment; not proven video quality.</small></div>
            <div><span>Grade</span><strong>{{ canonical.grade || 'UNKNOWN' }}</strong></div>
            <div><span>Status</span><strong>{{ canonical.status }}</strong></div>
            <div><span>Rules evaluated</span><strong>{{ canonical.rulesEvaluated || 0 }}</strong></div>
            <div><span>PASS</span><strong class="outcome-pass">{{ (canonical.passedRules || []).length }}</strong></div>
            <div><span>FAIL</span><strong class="outcome-fail">{{ (canonical.failedRules || []).length }}</strong></div>
            <div><span>UNKNOWN</span><strong class="outcome-unknown">{{ (canonical.unknownRules || []).length }}</strong></div>
            <div><span>NOT APPLICABLE</span><strong class="outcome-na">{{ (canonical.notApplicableRules || []).length }}</strong></div>
          </div>
          <div class="canonical-summary-grid" *ngIf="canonical.status === 'ERROR'">
            <div><span>Status</span><strong class="outcome-error">ERROR</strong></div>
            <div><span>Reason</span><strong>{{ canonical.reason || 'Unknown error' }}</strong></div>
          </div>
          <div class="canonical-summary-grid" *ngIf="canonical.status === 'NOT_EVALUATED'">
            <div><span>Status</span><strong>NOT_EVALUATED</strong></div>
            <div><span>Reason</span><strong>{{ canonical.reason || 'Canonical evaluation not available' }}</strong></div>
          </div>
          <div class="canonical-video-plan" *ngIf="canonical.videoPlanIR">
            <h4>Extracted Video Plan IR</h4>
            <p><b>Beats:</b> {{ canonical.videoPlanIR.beats?.length || 0 }}</p>
            <p><b>Core mechanic:</b> {{ readableCoreMechanic(canonical.videoPlanIR.coreMechanic) }}</p>
            <p><b>Goal evidence:</b> {{ readableGoalEvidence(canonical.videoPlanIR.goalEvidence) }}</p>
            <p><b>Recurrence:</b> {{ canonical.videoPlanIR.recurrence !== undefined ? canonical.videoPlanIR.recurrence : 'UNKNOWN' }}</p>
          </div>
          <section *ngIf="sourcePlanEvidence as extraction" class="read-only-source-plan"><h4>Read-only source extraction · not revalidation</h4><p>{{ extraction.resultId }} · parent run {{ extraction.historicalRunId }}</p><p>Historical canonical fields and 85/B are preserved. These current parser fields establish textual correspondence only; semantic fidelity and render authorization are not evaluated.</p><p><b>Source character:</b> {{ extraction.videoPlanIR?.mainCharacter || 'UNKNOWN' }} · {{ extraction.videoPlanIR?.entityEvidence?.mainCharacter?.state || 'UNKNOWN' }}</p><p><b>Source principal object:</b> {{ extraction.videoPlanIR?.principalObject || 'UNKNOWN' }} · {{ extraction.videoPlanIR?.entityEvidence?.principalObject?.state || 'UNKNOWN' }}</p><article *ngFor="let beat of extraction.videoPlanIR?.beats"><strong>{{ beat.startTime }}–{{ beat.endTime }}s</strong><p>Actor: {{ beat.actor || 'UNKNOWN' }} · {{ beat.fieldEvidence?.actor?.state || 'UNKNOWN' }}; object: {{ beat.primaryObject || 'UNKNOWN' }} · {{ beat.fieldEvidence?.primaryObject?.state || 'UNKNOWN' }}</p><p>Action: {{ beat.sourceAction || 'UNKNOWN' }}</p><p>Consequence: {{ cleanAnalysisText(beat.consequence) }}</p><small>Source span {{ beat.sourceSpan?.join('–') || 'UNKNOWN' }} · {{ beat.sourceSpanStatus || 'UNKNOWN' }} · independent semantic verification NOT_PERFORMED</small></article></section><p *ngIf="sourcePlanStatus==='UNKNOWN'" class="missing-state">Current parser extraction is unavailable (UNKNOWN). Historical analysis and authorization remain unchanged.</p>
          <div class="canonical-rules-list" *ngIf="canonical.status === 'EVALUATED'">
            <h4>Individual Rule Outcomes</h4>
            <article *ngFor="let rule of canonical.passedRules" class="canonical-rule-item rule-pass">
              <span class="rule-outcome-badge pass">PASS</span>
              <strong>{{ rule.ruleId }}</strong>
              <span class="rule-family">{{ rule.family }}</span>
              <p>{{ rule.message }}</p>
            </article>
            <article *ngFor="let rule of canonical.failedRules" class="canonical-rule-item rule-fail">
              <span class="rule-outcome-badge fail">{{ rule.severity || 'FAIL' }}</span>
              <strong>{{ rule.ruleId }}</strong>
              <span class="rule-family">{{ rule.family }}</span>
              <p>{{ rule.message }}</p>
              <small *ngIf="rule.details?.missing">Missing: {{ rule.details.missing.join(', ') }}</small>
            </article>
            <article *ngFor="let rule of canonical.unknownRules" class="canonical-rule-item rule-unknown">
              <span class="rule-outcome-badge unknown">UNKNOWN</span>
              <strong>{{ rule.ruleId }}</strong>
              <span class="rule-family">{{ rule.family }}</span>
              <p>{{ rule.message }}</p>
            </article>
            <article *ngFor="let rule of canonical.notApplicableRules" class="canonical-rule-item rule-na">
              <span class="rule-outcome-badge na">NOT_APPLICABLE</span>
              <strong>{{ rule.ruleId }}</strong>
              <span class="rule-family">{{ rule.family }}</span>
              <p>{{ rule.message }}</p>
            </article>
          </div>
        </section>

        </ng-container>
        <details *ngIf="activeAnalysisTab === 'feasibility'">
          <summary>Raw plan, generator and authorization evidence</summary>
          <div class="facts">
            <p>
              Content: <strong>{{ r.routing?.contentProfile }}</strong> · {{ r.routing?.basis }}
            </p>
            <p>
              Opening: <strong>{{ r.opening?.strategy }}</strong> · Text plan
              {{ r.opening?.plannedOpening?.status || 'UNKNOWN' }}
            </p>
            <p>
              Suggested / selected generator: {{ r.generation?.recommendedGenerator }} /
              {{ r.generation?.selectedGenerator }}
            </p>
            <p>
              Requested / supported render / edit duration:
              {{ r.generation?.desiredDuration ?? 'UNKNOWN' }} /
              {{ r.generation?.supportedRenderDuration ?? 'UNKNOWN' }} /
              {{ r.generation?.plannedEditedDuration ?? 'UNKNOWN' }} s
            </p>
            <p>
              Provider contract: {{ r.generation?.capabilityStatus }} ·
              {{ r.generation?.apiModelId || 'UNKNOWN' }}
            </p>
            <p>
              Creative Quality: {{ r.family8?.creativeQuality?.creativeGrade ?? 'UNKNOWN' }} ·
              Evidence: {{ r.family8?.evidenceCompleteness?.status ?? 'UNKNOWN' }}
            </p>
            <p>
              Render Authorization: <strong>{{ r.family8?.renderAuthorization?.status }}</strong>
            </p>
            <p *ngFor="let reason of r.family8?.renderAuthorization?.reasons">
              {{ reason.code }} · {{ reason.source }}: {{ authorizationReasonText(reason) }}
            </p>
          </div>
          <app-general-producibility
            *ngIf="r.generalProducibility?.dimensions"
            [assessment]="r.generalProducibility"
          ></app-general-producibility>
          <h3>Attention → progression → rewatch hypothesis</h3>
          <p>{{ r.engagement?.attentionPromise }}</p>
          <p>Ending: {{ cleanAnalysisText(r.engagement?.endingDelivery) }} · {{ r.engagement?.rewatchMechanism }}</p>
          <p>
            First frame / actual opening / cover evidence: {{ r.opening?.actualFirstFrame?.status }} /
            {{ r.opening?.actualOpeningVideo?.status }} / {{ r.opening?.cover?.status }}
          </p>
          <p *ngFor="let alternative of r.opening?.alternatives">{{ alternative }}</p>
          <h3>Generator execution review · {{ r.executionReview?.status }}</h3>
          <article *ngFor="let finding of r.executionReview?.findings?.slice(0, 5)">
            <strong
              >{{ finding.riskCategory }} · {{ finding.evidenceBasis }} ·
              {{ finding.confidence }}</strong
            >
            <blockquote>{{ finding.sourceQuote }}</blockquote>
            <p>{{ finding.plausibleFailure }} {{ finding.smallestChange }}</p>
          </article>
          <p>
            The local text critic does not inspect visuals or clips. DeepSeek second opinion
            can be configured on the server; paid calls are disabled by default.
          </p>
        </details>
        <section *ngIf="activeAnalysisTab === 'evidence' && r.family8?.renderAuthorization?.status === 'BLOCKED_TECHNICAL_FAILURE'" class="missing-state"><h3>Saved technical validation diagnostic</h3><p>{{ technicalDiagnostic() }}</p><p>Status remains BLOCKED_TECHNICAL_FAILURE. This screen does not rerun the assessment or authorize render.</p></section><label *ngIf="activeAnalysisTab === 'evidence'"
          >Second-opinion provider<select [(ngModel)]="criticProvider">
            <option value="deepseek">DeepSeek · text provider</option>
            <option value="openai">OpenAI</option>
            <option value="claude">Claude</option>
            <option value="gemini">Gemini</option>
          </select></label
        ><label *ngIf="activeAnalysisTab === 'evidence'">Structured critic model<input [(ngModel)]="criticModel" /></label
        ><button *ngIf="activeAnalysisTab === 'evidence'"
          type="button"
          (click)="secondOpinion()"
          [disabled]="busy || !isCurrent() || !criticModel"
        >
          Run second opinion
        </button>
        <p *ngIf="opinion && activeAnalysisTab === 'evidence'">
          Second opinion: {{ opinion.secondOpinion?.status }} · does not change canonical authorization.
        </p>
        <a [href]="renderLink()" *ngIf="activeAnalysisTab === 'feasibility' && r.contentId && r.promptVersionId"
          >Open the current render queue for this review</a
        >
        <details *ngIf="activeAnalysisTab === 'evidence'">
          <summary>Evidence and uncertainty</summary>
          <p>Extraction: {{ r.productionEvidence?.videoPlanIR?.metadata?.generalProducibilityEvidence?.extractionVersion || 'UNKNOWN' }} · Source quote coverage: {{ evidenceCoverage(r.productionEvidence) }}. Quote coverage does not establish complete entity or effect tracking.</p>
          <article *ngFor="let claim of r.productionEvidence?.claims">
            <strong>{{ claim.field }} · {{ claim.state }}</strong>
            <blockquote *ngIf="claim.quote">{{ claim.quote }}</blockquote>
            <p>{{ claim.reason }}</p>
            <small>Source {{ claim.sourceId || r.source?.artifact || 'UNKNOWN' }} · version {{ claim.sourceVersion || r.source?.version || 'UNKNOWN' }} · span {{ claim.span?.join('–') || 'UNKNOWN' }} · method {{ claim.methodVersion || 'UNKNOWN' }} · confidence {{ claim.confidence || 'UNKNOWN' }}</small>
          </article>
          <p>Unresolved requirements: {{ r.productionEvidence?.remainingUncertainty?.join(', ') || 'No missing extracted dependency; other unsupported effects may remain UNKNOWN.' }}</p>
          <small>{{ r.source?.sha256 }} · version {{ r.source?.version }}</small>
        </details>
        <ng-container *ngIf="activeAnalysisTab === 'evidence'">
        <h3>Core intent before render</h3>
        <p>
          Importance is bound to this source version. Re-review when it changes; it is not changed retroactively
          based on the video result.
        </p>
        <article *ngFor="let beat of r.productionEvidence?.videoPlanIR?.beats">
          <p>{{ beat.startTime }}–{{ beat.endTime }} s · {{ cleanAnalysisText(beat.action) }}</p>
          <button type="button" (click)="setIntentLevel(beat, 'ESSENTIAL')">Core event</button>
          <button type="button" (click)="setIntentLevel(beat, 'FLEXIBLE')">Flexible preference</button>
          <button type="button" (click)="setIntentLevel(beat, 'POLISH')">Visual polish</button>
        </article>
        <details>
          <summary>Source-bound intent and creative interpretation details</summary>
          <label
            >Intent requirements<textarea [(ngModel)]="intentRequirementsText"></textarea>
          </label>
          <label
            >Plan notes (source range and rationale)<textarea
              [(ngModel)]="creativeEvidenceText"
            ></textarea>
          </label>
          <p>
            Progression may develop through information, relationships, emotion, physics or rhythm. The ending may serve
            more than one function. Unsupported interpretation remains UNKNOWN.
          </p>
        </details>
        </ng-container>
        <section *ngIf="activeAnalysisTab === 'creative'" class="analysis-tab-panel creative-quality-panel"><h3>Creative Quality</h3><div class="analysis-summary-grid"><article><span>Opening promise</span><strong>{{ r.engagement?.attentionPromise || r.opening?.strategy || 'UNKNOWN' }}</strong><small>Planned source interpretation; actual opening remains a Video QA observation.</small></article><article><span>Progression</span><ul><li *ngFor="let item of asList(r.engagement?.progression)">{{ cleanAnalysisText(item) }}</li></ul><small>Each item is kept as a separate evidence-led statement.</small></article><article><span>Ending delivery</span><strong>{{ cleanAnalysisText(r.engagement?.endingDelivery || r.opening?.plannedEnding?.status || 'UNKNOWN') }}</strong></article><article><span>Rewatch rationale</span><strong>{{ r.engagement?.rewatchMechanism || 'UNKNOWN' }}</strong></article></div><p class="missing-state">Actual first-frame and video observations are owned by Video QA and are not asserted here.</p></section>
        <section *ngIf="activeAnalysisTab === 'feasibility'" class="analysis-tab-panel feasibility-summary"><h3>Production Feasibility</h3><p>Canonical render authorization: <strong>{{ r.family8?.renderAuthorization?.status || 'UNKNOWN' }}</strong></p><p>Generator execution risk: <strong>{{ r.executionRisk?.status || 'UNKNOWN' }}</strong></p><p>Evidence coverage: <strong>{{ evidenceCoverage(r.productionEvidence) }}</strong></p></section>
        <footer class="analysis-stage-footer" aria-label="Quality Analysis navigation"><button type="button" class="button button--secondary" (click)="selectStage(4)">← Back to Production Review</button><button type="button" class="button button--primary" (click)="continueFromAnalysis()">{{ nextAnalysisAction }} →</button></footer>
        </ng-container><ng-container *ngIf="activeStage === 6">
        <section class="repair-triage" aria-label="Repair decision">
          <header><span class="card-kicker">STEP 6 · GOVERNED REVIEW</span><h3>Current canonical evidence</h3></header>
          <p>{{ canonicalScoreLabel }} · Grade {{ canonicalGrade }} · {{ canonicalFailCount }} canonical failures retained.</p>
          <app-step6-governance [analysisId]="review?.recordId || ''" [preparationLink]="renderPreparationLink()"></app-step6-governance>
        </section>
        <details class="creative-optimization-details">
          <summary>Creative Optimization (optional)</summary>
          <div class="creative-optimization-body">
            <p class="setting-note">Diagnose and reconstruct up to two defensible production candidates after explicit paid consent and a valid budget. One candidate or Keep Original may be the correct result. Canonical compliance and creative improvement are assessed separately; neither authorizes rendering.</p>
            <button type="button" class="button button--secondary button--compact" (click)="loadLatestCreativeOptimization()" [disabled]="creativeOptimizationBusy || !review?.recordId">Load saved comparison / attempt</button>
            <div class="repair-fields">
              <label class="repair-field" for="creative-optimization-budget">
                <span>Maximum total cost (USD)</span>
                <input #creativeOptimizationBudgetInput id="creative-optimization-budget" type="number" min="0.01" max="20" step="0.01" [disabled]="creativeOptimizationBusy" (input)="creativeOptimizationBudget = +($any($event.target).value || 0)">
              </label>
            </div>
            <label class="repair-consent-row" for="creative-optimization-consent">
              <input #creativeOptimizationConsentInput id="creative-optimization-consent" type="checkbox" [disabled]="creativeOptimizationBusy" (change)="creativeOptimizationConsent = $any($event.target).checked">
              <span>I explicitly authorize one creative optimization call within the configured budget.</span>
            </label>
            <p>V2 uses source-bound creative diagnosis, production reconstruction and critique. Existing saved drafts retain their current comparison decision.</p>
            <label class="repair-consent-row"><input type="checkbox" (change)="creativeOptimizationPlanFirstNewAttempt = $any($event.target).checked" [disabled]="creativeOptimizationBusy">Explicitly request a new reconstruction attempt (separate paid consent and budget required).</label>
            <div class="repair-button-row">
              <button #creativeOptimizationGenerateButton type="button" class="button button--primary button--compact" (click)="generateCreativeOptimizationCandidates()" [disabled]="creativeOptimizationBusy || !creativeOptimizationConsent || !validCreativeOptimizationBudget || !review?.recordId">Diagnose and reconstruct</button>
            </div>
            <p *ngIf="creativeOptimizationError" class="error" role="alert">{{ creativeOptimizationError }}</p>
            <section *ngIf="creativeOptimizationComparison" class="optimization-conclusion" aria-label="Optimization comparison conclusion">
              <strong>{{ creativeOptimizationComparison.comparisonAssessment?.recommendation || 'CURRENT VALIDATION REQUIRED' }}</strong>
              <p>{{ creativeOptimizationComparison.comparisonAssessment?.conclusion || 'This historical comparison must be revalidated before approval.' }}</p>
              <p *ngFor="let candidate of creativeOptimizationComparison.candidates; let idx = index"><strong>Candidate {{ candidate.candidateId === 'candidate-b' ? 'B' : 'A' }}:</strong> {{ candidate.currentAssessment?.conclusion || 'Current assessment unavailable.' }}</p>
              <p *ngIf="creativeOptimizationComparison.candidates?.length !== 2" role="alert">Incomplete comparison: {{ creativeOptimizationComparison.candidates?.length || 0 }} actual candidate(s). No placeholder candidate is accepted.</p>
            </section>
            <p *ngIf="creativeOptimizationComparison?.creativeEvidence?.outcome === 'NO_JUSTIFIED_IMPROVEMENT'">No justified improvement. Keep Original. {{ creativeOptimizationComparison?.creativeEvidence?.noImprovementReason }}</p>
            <details *ngIf="creativeOptimizationComparison?.creativeEvidence?.creativeDiagnosis as diagnosis" class="optimization-panel">
              <summary>Creative diagnosis · {{ diagnosis.qualityModelVersion }}</summary>
              <article *ngFor="let opportunity of diagnosis.opportunities"><strong>{{ opportunity.beatId }} · {{ opportunity.classification }}</strong><p>{{ opportunity.weaknessOrUncertainty }}</p><p>{{ opportunity.proposedImprovement }}</p></article>
            </details>
            <div *ngIf="creativeOptimizationComparison?.candidates?.length" class="creative-optimization-grid">
              <article class="creative-optimization-card optimization-original">
                <header><div><span class="card-kicker">Original · v{{ promptVersionNumber ?? 'UNKNOWN' }}</span><h4>Saved production prompt</h4></div><span class="status-pill">Baseline</span></header>
                <p class="optimization-score">{{ review?.canonicalRuleEvaluation?.score != null ? (review?.canonicalRuleEvaluation?.score | number:'1.0-2') : 'UNKNOWN' }}<small>/100 · {{ review?.canonicalRuleEvaluation?.grade ?? 'UNKNOWN' }}</small></p>
                <p><strong>Canonical result:</strong> {{ review?.canonicalRuleEvaluation?.rulesetVersion || creativeOptimizationComparison.rulesetVersion || 'UNKNOWN' }} · {{ canonicalOutcomeSummary }}</p>
                <p><strong>Recommendation:</strong> {{ creativeOptimizationComparison.comparisonAssessment?.recommendation || 'CURRENT VALIDATION REQUIRED' }}</p>
                <a class="optimization-detail-link" href="#optimization-original-prompt" (click)="openOptimizationPanel('optimization-original-prompt', $event)">View Original Prompt</a>
              </article>
              <article *ngFor="let candidate of creativeOptimizationComparison.candidates; let idx = index" class="creative-optimization-card" [class.is-selected]="creativeOptimizationSelectedCandidateId === candidate.candidateId">
                <header><div><span class="card-kicker">Candidate {{ candidate.candidateId === 'candidate-b' ? 'B' : 'A' }}</span><h4>{{ candidate.title || 'Untitled draft' }}</h4></div><span class="status-pill">{{ creativeOptimizationSelectedCandidateId === candidate.candidateId ? 'Selected' : 'Draft' }}</span></header>
                <p *ngIf="candidate.creativeContractVersion" class="setting-note">Canonical compliance score · creative evidence is assessed separately below.</p>
                <p class="optimization-score">{{ candidate.review?.canonicalRuleEvaluation?.score != null ? (candidate.review?.canonicalRuleEvaluation?.score | number:'1.0-2') : 'UNKNOWN' }}<small>/100 · {{ candidate.review?.canonicalRuleEvaluation?.grade ?? 'UNKNOWN' }} · Δ {{ optimizationScoreDelta(candidate) }}</small></p>
                <p class="optimization-classification">{{ candidate.currentAssessment?.classification || 'NOT_REVALIDATED' }}</p>
                <p><strong>Similarity:</strong> {{ optimizationSimilarity(candidate) }} · textual heuristic</p>
                <p><strong>Hypothesis:</strong> {{ candidate.hypothesis || 'No hypothesis recorded.' }}</p>
                <p><strong>Observed changes:</strong> {{ candidate.currentAssessment?.actualChanges?.join('; ') || 'No current change evidence.' }}</p>
                <p><strong>Production risk:</strong> {{ candidate.currentAssessment?.productionRiskChange || 'UNKNOWN' }}</p>
                <p class="optimization-eligibility"><strong>Approval:</strong> {{ candidate.currentAssessment?.approvalEligible === true ? 'Eligible for explicit review' : 'Blocked' }}</p>
                <div class="creative-optimization-actions">
                  <button type="button" class="button button--secondary button--compact" (click)="reviewCreativeOptimizationCandidate(candidate.candidateId)" [disabled]="creativeOptimizationBusy">Review Candidate {{ candidate.candidateId === 'candidate-b' ? 'B' : 'A' }}</button>
                  <button type="button" class="button button--compact" [class.button--primary]="candidate.currentAssessment?.approvalEligible === true" [class.button--secondary]="candidate.currentAssessment?.approvalEligible !== true" (click)="selectCreativeOptimizationCandidate(candidate.candidateId)" [disabled]="creativeOptimizationBusy || !canSelectOptimizationCandidate(candidate)">{{ candidate.currentAssessment?.approvalEligible === true ? 'Select candidate' : 'Select for review' }}</button>
                </div>
              </article>
            </div>
            <div *ngIf="creativeOptimizationComparison?.candidates?.length" class="creative-optimization-approval">
              <div class="repair-button-row">
                <button type="button" class="button button--secondary button--compact" (click)="selectCreativeOptimizationCandidate('ORIGINAL')" [disabled]="creativeOptimizationBusy">Keep Original</button>
                <button type="button" class="button button--primary button--compact" (click)="approveSelectedCreativeOptimizationCandidate()" [disabled]="creativeOptimizationBusy || !creativeOptimizationApprovalEnabled">Approve Selected Revision</button>
              </div>
              <p class="setting-note">{{ creativeOptimizationSelectedCandidateId === 'ORIGINAL' ? 'Original retained. No revision is selected.' : 'Review and select an eligible candidate before explicit approval.' }} Scores do not auto-select or grant render authorization.</p>
            </div>
            <details *ngIf="creativeOptimizationComparison" id="optimization-original-prompt" class="optimization-panel optimization-prompt-panel">
              <summary>View Original Prompt</summary>
              <button type="button" class="button button--secondary button--compact" (click)="copySavedPrompt()" [disabled]="!isCurrent() || !prompt">Copy original prompt</button>
              <pre class="creative-optimization-diff">{{ prompt }}</pre>
            </details>
            <section #optimizationReviewSection *ngFor="let candidate of creativeOptimizationComparison?.candidates; let idx = index" class="optimization-candidate-details" [attr.data-candidate-id]="candidate.candidateId" [attr.aria-label]="'Candidate ' + (candidate.candidateId === 'candidate-b' ? 'B' : 'A') + ' details'">
              <h4 #optimizationReviewHeading tabindex="-1" [attr.data-candidate-id]="candidate.candidateId" class="optimization-review-heading">Candidate {{ candidate.candidateId === 'candidate-b' ? 'B' : 'A' }} · Review details</h4>
              <details open class="optimization-panel optimization-actual-changes">
                <summary>Actual Changes</summary>
                <ul><li *ngFor="let change of candidate.currentAssessment?.actualChanges">{{ change }}</li></ul>
                <p>{{ candidate.currentAssessment?.conclusion || 'No current value assessment is available.' }}</p>
              </details>
              <details *ngIf="candidate.currentAssessment?.creativeAssessment as creative" open class="optimization-panel optimization-creative-proof">
                <summary>Creative improvement evidence · {{ creative.classification }}</summary>
                <p>Text-grounded execution change. Visual benefit, generator adherence and audience response remain unverified.</p>
                <article *ngFor="let change of creative.changeContract">
                  <h5>{{ change.beatId }} · {{ change.opportunityId }}</h5>
                  <strong>Original execution</strong><pre class="creative-optimization-diff">{{ change.originalExecution }}</pre>
                  <strong>New execution</strong><pre class="creative-optimization-diff">{{ change.newExecution }}</pre>
                  <p><strong>Observable difference:</strong> {{ change.observableDifference }}</p>
                  <p *ngIf="change.authorship"><strong>Instruction author:</strong> {{ change.authorship }} · Source references are substituted exactly; visual benefit remains unverified.</p>
                  <p><strong>Creative rationale:</strong> {{ change.creativeRationale }}</p>
                  <p><strong>Source fidelity:</strong> Protected source event retained · semantic fidelity {{ change.sourceFidelity?.semanticFidelity }}</p>
                  <p><strong>Production risk:</strong> {{ change.productionRisk?.change }} · {{ change.productionRisk?.evidence }}</p>
                  <p>{{ change.evidenceLimitation }}</p>
                </article>
              </details>
              <details open class="optimization-panel optimization-quality-panel">
                <summary>Quality and Production Assessment</summary>
                <p><strong>Validation:</strong> {{ candidate.currentAssessment?.validationStatus || 'UNKNOWN' }} · <strong>Risk:</strong> {{ candidate.currentAssessment?.productionRiskChange || 'UNKNOWN' }}</p>
                <p><strong>Story and ending:</strong> {{ candidate.currentAssessment?.storyCoverage || 'UNKNOWN' }} · {{ candidate.currentAssessment?.endingPreservation || 'UNKNOWN' }}</p>
                <p>First-frame clarity, hook effectiveness and Seedance feasibility require visual evidence. Viewer response is unmeasured.</p>
                <p *ngIf="candidate.currentAssessment?.approvalBlockReason" class="setting-note">Approval blocked: {{ candidate.currentAssessment.approvalBlockReason }}</p>
              </details>
                <details *ngIf="candidate.executionPlan" class="optimization-panel"><summary>Validated improvement plan · hypothesis only</summary>
                  <p><strong>Baseline opportunity:</strong> {{ candidate.executionPlan.baselineOpportunity }}</p>
                  <p><strong>Proposed visual consequence:</strong> {{ candidate.executionPlan.proposedVisualConsequence }}</p>
                  <p><strong>Material difference:</strong> {{ candidate.executionPlan.materialDifference }}</p>
                  <p><strong>Plan validation:</strong> {{ candidate.planValidation?.status || 'UNKNOWN' }}</p>
                  <strong>Risk reduction hypotheses</strong><ul><li *ngFor="let risk of candidate.executionPlan.risksReducedHypotheses">{{ risk }}</li></ul>
                  <strong>Introduced risks</strong><ul><li *ngFor="let risk of candidate.executionPlan.risksIntroduced">{{ risk }}</li></ul>
                  <strong>Visual evidence required</strong><ul><li *ngFor="let unknown of candidate.executionPlan.unknowns">{{ unknown }}</li></ul>
                </details>

              <details class="optimization-panel optimization-prompt-panel">
                <summary>Full Candidate Prompt</summary>
                <button type="button" class="button button--secondary button--compact" (click)="copyOptimizationPrompt(candidate.prompt)">Copy full candidate prompt</button>
                <pre class="creative-optimization-diff">{{ candidate.prompt }}</pre>
              </details>
              <details class="optimization-panel optimization-technical-panel"><summary>Technical Evidence</summary><pre class="creative-optimization-diff">{{ candidate | json }}</pre></details>
            </section>
            <details *ngIf="creativeOptimizationComparison?.candidates?.length" class="optimization-panel optimization-side-diff">
              <summary>Compare Full Prompt Changes</summary>
              <div class="optimization-diff-controls">
                <label>Compare candidate <select aria-label="Compare candidate" [ngModel]="optimizationDiffCandidate.candidateId" (ngModelChange)="optimizationDiffCandidateId = $event"><option *ngFor="let candidate of creativeOptimizationComparison.candidates; let idx = index" [value]="candidate.candidateId">Candidate {{ candidate.candidateId === 'candidate-b' ? 'B' : 'A' }} · {{ candidate.title }}</option></select></label>
                <label><input type="checkbox" [checked]="optimizationShowUnchanged" (change)="optimizationShowUnchanged = $any($event.target).checked"> Show Unchanged Context</label>
              </div>
              <p>Alternative versions of the same source events. Removed and added text are not sequential story beats.</p>
              <table><thead><tr><th scope="col">Original · removed text (−)</th><th scope="col">{{ optimizationDiffCandidate.candidateId }} · added text (+)</th></tr></thead>
                <tbody><tr *ngFor="let row of optimizationVisibleDiffRows" [class.diff-change]="row.changed"><td><span *ngFor="let token of optimizationInlineDiff(row).before" [class.diff-removed]="token.changed">{{ token.text }}</span></td><td><span *ngFor="let token of optimizationInlineDiff(row).after" [class.diff-added]="token.changed">{{ token.text }}</span></td></tr></tbody>
              </table>
              <p *ngIf="!optimizationVisibleDiffRows.length">No changed text in the saved diff.</p>
            </details>
            <details *ngIf="creativeOptimizationComparison" class="optimization-panel optimization-technical-panel"><summary>Comparison provenance and technical evidence</summary><pre class="creative-optimization-diff">{{ creativeOptimizationComparison | json }}</pre></details>
            <p *ngIf="optimizationCopyStatus" role="status">{{ optimizationCopyStatus }}</p>
          </div>
        </details>
        <details class="repair-secondary-details">
          <summary>Analysis details and provenance</summary>
          <div class="repair-secondary-grid">
            <div><span>Analysis run</span><strong>{{ review?.recordId || 'Unavailable' }}</strong></div>
            <div><span>Prompt version</span><strong>v{{ promptVersionNumber ?? 'UNKNOWN' }} · ID {{ review?.promptVersionId || promptVersionId }}</strong></div>
            <div><span>Rule outcomes</span><strong>{{ canonicalOutcomeSummary }}</strong></div>
            <div><span>Saved findings · resolution requires the exit policy above</span><strong>{{ actionableTextDefects.length ? actionableTextDefects.join('; ') : 'None identified' }}</strong></div>
            <div><span>Optional improvements</span><strong>{{ optionalCreativeImprovements.length ? optionalCreativeImprovements.join('; ') : 'None recorded' }}</strong></div>
            <div><span>Outstanding requirements</span><strong>{{ outstandingEvidence.length ? outstandingEvidence.join('; ') : 'None recorded' }}</strong></div>
          </div>
          <details><summary>Step 5 production and technical classifications</summary>
            <div class="repair-secondary-grid">
              <div><span>Local execution critic</span><strong>{{ localExecutionStatus }}</strong></div>
              <div><span>Generator capability</span><strong>{{ generatorCapabilityStatus }}</strong></div>
              <div><span>Production complexity</span><strong>{{ productionComplexityStatus }}</strong></div>
              <div><span>Technical evaluation</span><strong>{{ technicalEvaluationStatus }}</strong></div>
              <div><span>UNKNOWN canonical rules</span><strong>{{ unknownCanonicalRules.length ? unknownCanonicalRules.join(', ') : 'None' }}</strong></div>
            </div>
          </details>
          <details *ngIf="promptDeclaredProfile !== 'NOT DECLARED' && promptDeclaredProfile !== contentProfile">
            <summary>Historical profile mismatch</summary>
            <p>Immutable prompt text declares {{ promptDeclaredProfile }}. The saved production profile and analysis use {{ contentProfile }}. The prompt remains unchanged; use the versioned editor only after an explicit operator edit.</p>
          </details>
          <details><summary>Operator provenance</summary>
            <p>Content {{ contentId }} · prompt version {{ promptVersionId }} · current saved settings {{ contentProfile }} / {{ generator }} / {{ desiredDuration }}s / {{ aspectRatio }}.</p>
            <p>Analysis binding {{ review?.bindingHash || 'UNKNOWN' }} · source hash {{ review?.source?.sha256 || 'UNKNOWN' }}.</p>
          </details>
        </details>
        <details class="current-prompt-card">
          <summary>Current prompt · Prompt v{{ promptVersionNumber ?? 'UNKNOWN' }} / ID {{ review?.promptVersionId || promptVersionId }}</summary>
          <div class="prompt-preview-toolbar">
            <span>Immutable saved prompt text · read-only</span>
            <button type="button" class="button button--secondary button--compact" (click)="copySavedPrompt()" [disabled]="!isCurrent() || !prompt">Copy saved prompt</button>
          </div>
          <div #promptPreviewEditor class="prompt-monaco" aria-label="Immutable prompt preview"></div>
          <label *ngIf="!promptPreviewEditorReady" class="prompt-fallback-label">Read-only prompt preview<textarea readonly [value]="prompt" aria-label="Current prompt text"></textarea></label>
          <p *ngIf="promptPreviewLoadError" class="setting-note">{{ promptPreviewLoadError }}</p>
          <p *ngIf="copyStatus" role="status">{{ copyStatus }}</p>
        </details>
        <details class="repair-tools-details"><summary>Optional Repair Tools</summary>
          <div class="repair-tools-group">
            <h3>Bounded AI Repair</h3>
            <p>A provider call happens only after you explicitly approve the budget and start this session.</p>
            <div class="repair-fields">
              <label class="repair-field">
                <span>Maximum total cost (USD)</span>
                <input class="repair-budget" type="number" min="0.01" max="20" step="0.01" [(ngModel)]="repairBudget">
              </label>
              <small>Choose a total ceiling between $0.01 and $20.00 USD. Zero is not authorization.</small>
            </div>
            <label class="repair-consent-row" for="repair-consent">
              <input id="repair-consent" type="checkbox" [(ngModel)]="repairConsent">
              <span>I approve the configured repair provider within this session budget.</span>
            </label>
            <div class="repair-button-row">
              <button type="button" class="button button--primary button--compact" (click)="startRepairSession()" [disabled]="busy || !isCurrent() || !repairConsent || !validRepairBudget">Start bounded repair</button>
            </div>
            <small *ngIf="!validRepairBudget">Enter a budget greater than zero and no more than $20.00.</small>
            <small *ngIf="!repairConsent">Provider authorization is required before a repair session can start.</small>
            <label class="repair-field">
              <span>Saved session ID</span>
              <input [(ngModel)]="repairSessionId" placeholder="Session UUID">
            </label>
            <div class="repair-button-row">
              <button type="button" class="button button--secondary button--compact" (click)="reopenRepairSession(repairSessionId)" [disabled]="!validRepairSessionId">Reopen session</button>
            </div>
            <small *ngIf="!validRepairSessionId">Enter a valid saved session ID to reopen a session.</small>
            <div *ngIf="repairSession">
              <p>{{ repairSession.sessionId }} · {{ repairSession.state }} · {{ repairSession.stopReason }} · attempts {{ repairSession.attempts }}/{{ repairSession.maxAttempts }} · reserved ceiling {{ repairSession.reservedCostUsd }} (actual spend may be unknown)</p>
              <p>Best independently reviewed prompt version: {{ repairSession.bestPromptVersionId }}</p>
              <section *ngIf="repairOriginalReview && repairBestReview" aria-label="Repair before and after findings">
                <h4>Original · prompt version {{ repairOriginalReview.promptVersionId }}</h4><pre>{{ repairOriginalReview.executionReview?.findings | json }}</pre><pre>{{ repairOriginalReview.planQuality | json }}</pre>
                <h4>Best independently reviewed candidate · prompt version {{ repairBestReview.promptVersionId }}</h4><pre>{{ repairBestReview.executionReview?.findings | json }}</pre><pre>{{ repairBestReview.planQuality | json }}</pre>
              </section>
              <pre>{{ repairSession.history | json }}</pre>
              <div class="repair-button-row">
                <button type="button" class="button button--secondary button--compact" (click)="nextRepairAttempt()" [disabled]="busy || repairSession.state !== 'READY'">Next bounded attempt</button>
                <button type="button" class="button button--primary button--compact" (click)="decideRepair('ACCEPTED')" [disabled]="busy || repairSession.state === 'RUNNING'">Accept best candidate</button>
                <button type="button" class="button button--secondary button--compact" (click)="decideRepair('REJECTED')" [disabled]="busy || repairSession.state === 'RUNNING'">Reject</button>
                <button type="button" class="button button--secondary button--compact" (click)="decideRepair('CANCELLED')" [disabled]="busy || repairSession.state === 'RUNNING'">Cancel</button>
              </div>
            </div>
          </div>
          <div class="repair-tools-group">
            <h3>Minimal Manual Repair</h3>
            <p *ngIf="intentConfirmed && !protectedIntent.trim()" class="setting-note">
              Step 4 Creative Intent is already confirmed for this prompt. Its saved decision contains no protected-intent text; this is a separate patch-safety requirement, not a request to confirm intent again.
            </p>
            <p *ngIf="!intentConfirmed" class="missing-state">
              No current Step 4 Creative Intent confirmation is available for this prompt. Confirm supported intent in Production Review before preparing a patch.
            </p>
            <label class="repair-field">
              <span>Protected intent that must remain unchanged</span>
              <textarea [(ngModel)]="protectedIntent" [disabled]="!intentConfirmed" rows="2" class="repair-field__text"></textarea>
            </label>
            <div class="repair-fields repair-fields--patch">
              <label class="repair-field repair-field--inline">
                <span>Exact source wording to replace</span>
                <input [(ngModel)]="patchOriginal" class="repair-field__input">
              </label>
              <label class="repair-field repair-field--inline">
                <span>Replacement wording</span>
                <input [(ngModel)]="patchReplacement" class="repair-field__input">
              </label>
            </div>
            <p class="repair-help">Only the exact selected wording is changed in a candidate. Protected intent remains unchanged; saving a candidate requires an explicit transfer to the versioned editor.</p>
            <small *ngIf="manualPatchMessage" class="repair-field-help" role="status">{{ manualPatchMessage }}</small>
            <pre *ngIf="manualPatchPreview" aria-label="Manual patch preview">{{ manualPatchPreview }}</pre>
            <div class="repair-button-row">
              <button type="button" class="button button--secondary button--compact" (click)="repair()" [disabled]="busy || !isCurrent() || !intentConfirmed || !protectedIntent.trim() || !manualPatchValid || review?.repairPasses > 0">Preview and validate exact patch</button>
            </div>
            <p *ngIf="error" class="error" role="alert">{{ error }}</p>
            <pre *ngIf="review?.diff">{{ review.diff }}</pre>
          </div>
          <div class="repair-tools-group">
            <h3>Export and Advanced Actions</h3>
            <div class="repair-tool-actions">
              <button type="button" class="button button--secondary button--compact" (click)="exportHandoff()" [disabled]="!isCurrent()">Download manual render package</button>
            </div>
            <p *ngIf="copyStatus" role="status">{{ copyStatus }}</p>
            <p class="repair-help">Preview, copy and export do not change prompt, story or analysis data. “Transfer to editor and save version” is an explicit action that creates a new immutable prompt version. The manual package is an evidence snapshot only; it does not authorize rendering or spend credits.</p>
            <details *ngIf="review?.finalPrompt && review?.finalPrompt !== prompt" class="repair-candidate-details">
              <summary>Unsaved repair candidate · not the immutable saved prompt</summary>
              <textarea readonly [value]="review.finalPrompt" aria-label="Unsaved repair candidate"></textarea>
              <div class="repair-button-row">
                <button type="button" class="button button--secondary button--compact" (click)="saveFinal.emit(review.finalPrompt)" [disabled]="!isCurrent()">Transfer candidate to versioned editor</button>
              </div>
            </details>
          </div>
        </details>
        </ng-container>
        <section *ngIf="activeStage === 7" class="stage-empty-card render-stage-card">
          <span class="card-kicker">STEP 7 · RENDER</span>
          <h3>Render preparation</h3>
          <p>This stage is bound to the saved content, prompt revision and analysis. Prepare inputs here, then queue only after canonical authorization passes.</p>
          <div class="render-context-grid"><div><span>Content</span><strong>{{ review?.contentId || contentId }}</strong></div><div><span>Prompt version · database ID</span><strong>v{{ promptVersionNumber ?? 'UNKNOWN' }} · ID {{ review?.promptVersionId || promptVersionId }}</strong></div><div><span>Analysis run</span><strong>{{ review?.recordId || 'Unavailable' }}</strong></div><div><span>Generator</span><strong>{{ generatorLabel }}</strong></div><div><span>Duration / ratio</span><strong>{{ desiredDuration || 'Unknown' }}s · {{ aspectRatio || 'Unknown' }}</strong></div><div><span>References</span><strong>{{ approvedCharacterReference ? 'Approved reference bound' : 'Missing or unverified' }}</strong></div></div><div class="render-preflight"><div><span>Prompt snapshot</span><strong>Present · prompt v{{ promptVersionNumber ?? 'UNKNOWN' }} · database ID {{ review?.promptVersionId || promptVersionId }}</strong><small>{{ isCurrent() ? 'Matches the immutable version reviewed above.' : 'Current inputs differ; revalidation is required.' }}</small></div><div><span>Creative review</span><strong>{{ r.family8?.creativeQuality?.creativeGrade || r.planQuality?.status || 'UNKNOWN' }}</strong><small>Separate from render admission.</small></div><div><span>First frame</span><strong>{{ firstFrameStatus }}</strong></div><div><span>Provider capability</span><strong>{{ r.generation?.capabilityStatus || 'UNVERIFIED' }}</strong><small>Contract status does not imply a live provider check.</small></div><div><span>Render authorization</span><strong>{{ authorizationLabel(r.family8?.renderAuthorization?.status) }}</strong><small>{{ renderAuthorizationReason }}</small><details><summary>Technical status</summary><code>{{ r.family8?.renderAuthorization?.status || 'UNKNOWN' }}</code></details></div></div>
          <p class="setting-note">Opening this stage does not generate an image or video and does not spend credits.</p>
          <a class="button button--primary" [href]="renderPreparationLink()" *ngIf="contentId && promptVersionId">Open Render Preparation →</a>
          <p class="missing-state" *ngIf="!review?.contentId || !review?.promptVersionId">Render context is unavailable because this analysis is not bound to a saved content and prompt revision.</p>
        </section>
        <ng-container *ngIf="activeStage === 8"><h3>Actual render QA</h3>
        <label
          >Returned video local media path<input
            [(ngModel)]="qaPath"
            placeholder="library/.../video.mp4"
        /></label>
        <p>
          Open the actual clip and inspect every planned time range. Sparse frames are not evidence of motion/contact/loop.
        </p>
        <a *ngIf="qaPath" [href]="'/api/v1/videos/content?path=' + encode(qaPath)" target="_blank"
          >Open actual video</a
        >
        <article *ngFor="let beat of r.productionEvidence?.videoPlanIR?.beats">
          <strong>{{ beat.startTime }}–{{ beat.endTime }} s</strong>
          <p>{{ cleanAnalysisText(beat.action) }}</p>
          <label
            >Observed start (s)<input type="number" [(ngModel)]="qaStarts[beat.id]"
          /></label>
          <label
            >Observed end (s)<input type="number" [(ngModel)]="qaEnds[beat.id]"
          /></label>
          <select [(ngModel)]="qaStates[beat.id]">
            <option value="UNKNOWN">Insufficient evidence</option>
            <option value="PRESENT">Observed</option>
            <option value="ABSENT">Missing / failed</option>
          </select>
        </article>
        <label>Reviewed range start (s)<input type="number" [(ngModel)]="qaStart" /></label>
        <label>Reviewed range end (s)<input type="number" [(ngModel)]="qaEnd" /></label>
        <article *ngFor="let aspect of qaAspects">
          <strong>{{ aspect.label }}</strong>
          <select [(ngModel)]="qaExperience[aspect.key]">
            <option value="UNKNOWN">Insufficient evidence</option>
            <option *ngFor="let value of aspect.values" [value]="value">{{ value }}</option>
          </select>
          <label
            >What was actually observed in this range<input [(ngModel)]="qaDescriptions[aspect.key]"
          /></label>
        </article>
        <details>
          <summary>Range-specific defect and intervention evidence</summary>
          <label>Defects<textarea [(ngModel)]="qaDefectsText"></textarea></label>
          <label>Justified rerender recommendation<textarea [(ngModel)]="qaRepairText"></textarea></label>
          <p>
            Each defect needs a type, time, observation, inference/uncertainty, affected event/intent and audience
            impact. A technical type alone does not determine importance.
          </p>
        </details>
        <label
          ><input type="checkbox" [(ngModel)]="clipReviewed" />I inspected these ranges in the actual clip and confirm the observations</label
        >
        <label
          ><input type="checkbox" [(ngModel)]="stillsReviewed" />I inspected stills extracted from this video; they are evidence only for static appearance/pose findings</label
        >
        <button type="button" (click)="runQa()" [disabled]="busy || !isCurrent() || !qaPath">
          Deterministic analysis + plan comparison
        </button>
        <p *ngIf="qa">ACTUAL_RENDER_QA: {{ qa.status }} · Video {{ qa.videoId }}</p>
        <p *ngFor="let finding of qa?.findings">
          {{ finding.start }}–{{ finding.end }} s · {{ finding.reason }} {{ finding.action }}
        </p>
        <details><summary>Justified full-video regeneration handoff</summary><p>Requires a verified actual review with material full-rerender justification and exact prompt ancestry. Queue authorization and budget controls still apply.</p><label>Parent actual QA record<input [(ngModel)]="regenerationQaId" [placeholder]="qa?.recordId || ''"></label><label>Parent video ID<input [(ngModel)]="regenerationParentVideoId" [placeholder]="qa?.videoId || ''"></label><label>Parent variant ID (optional)<input [(ngModel)]="regenerationParentVariantId"></label><label>Why this new full-video attempt is justified<input [(ngModel)]="regenerationReason"></label><button type="button" (click)="createRegenerationHandoff()" [disabled]="!isCurrent() || !regenerationReason.trim()">Create immutable handoff</button><p *ngIf="regenerationHandoff">{{ regenerationHandoff.status }} · {{ regenerationHandoff.executionScope }}</p><a *ngIf="regenerationHandoff" [href]="regenerationLink()">Review authorized queue settings</a></details>
        <h3>Publication and measurement association</h3>
        <p>
          Prompt → references → render settings → actual video → edited variant → publication ID →
          immutable measurement are kept separate.
        </p>
        <div class="inputs">
          <label
            >Platform<select [(ngModel)]="platform">
              <option>INSTAGRAM</option>
              <option>FACEBOOK</option>
              <option>YOUTUBE</option>
            </select></label
          ><label>Publication ID (text)<input type="text" [(ngModel)]="platformContentId" /></label
          ><label>Edit varyant ID (varsa)<input [(ngModel)]="variantId" /></label
          ><label
            >Association evidence<input
              [(ngModel)]="associationReason"
              placeholder="Verified permalink / manual review reason"
          /></label>
        </div>
        <button
          type="button"
          (click)="associate()"
          [disabled]="busy || !qa?.videoId || !platformContentId || !associationReason"
        >
          Save manual association
        </button>
        <p *ngIf="association">
          Association: {{ association.status }} · {{ association.platformContentId }}
        </p>
        <a href="/import">Review and map the CSV/XLSX file in the import screen</a>
        <details>
          <summary>Source-backed measurement record and comparison</summary>
          <div class="inputs">
            <label>Measurement source / import row<input [(ngModel)]="measurementSource" /></label
            ><label
              >Observation window<select [(ngModel)]="horizon">
                <option>UNKNOWN</option>
                <option>LIFETIME</option>
                <option>1H</option>
                <option>3H</option>
                <option>24H</option>
                <option>72H</option>
              </select></label
            ><label>Measurement time<input type="datetime-local" [(ngModel)]="measuredAt" /></label
            ><label
              >Actual video duration (s)<input type="number" [(ngModel)]="videoDuration" /></label
            ><label>Reach<input type="number" [(ngModel)]="reach" /></label
            ><label>Views / plays<input type="number" [(ngModel)]="views" /></label
            ><label>Ortalama izleme (s)<input type="number" [(ngModel)]="watchSeconds" /></label
            ><label>Paid Reach<input type="number" [(ngModel)]="paidReach" /></label
            ><label
              >Paid watch-time share (0–1)<input type="number" [(ngModel)]="paidWatchShare"
            /></label>
          </div>
          <button
            type="button"
            (click)="saveMeasurement()"
            [disabled]="busy || !association || !measurementSource || !measuredAt"
          >
            Save measurement as a separate snapshot
          </button>
          <ng-container *ngIf="measurement"
            ><p>
              Reach {{ measurement.outcome?.reach?.value ?? 'UNKNOWN' }} · Views
              {{ measurement.outcome?.views?.value ?? 'UNKNOWN' }}
            </p>
            <p>
              Average watch / actual duration ratio:
              {{ measurement.audience?.averageWatchDurationRatio?.value ?? 'UNKNOWN' }} ·
              This is not an intentional replay rate.
            </p>
            <p>
              Distribution: {{ measurement.distribution?.cohort }} · Paid Reach share
              {{ measurement.distribution?.paidReachShare?.value ?? 'UNKNOWN' }} · paid watch-time
              share is separate.
            </p></ng-container
          >
          <label
            >Near-organic Paid Reach threshold (0–1)<input
              type="number"
              min="0"
              max="1"
              step="0.01"
              [(ngModel)]="nearOrganicThreshold" /></label
          ><button
            type="button"
            (click)="compare()"
            [disabled]="busy || !['1H', '3H', '24H', '72H'].includes(horizon)"
          >
            Compare cohorts in the same time window
          </button>
          <p *ngIf="cohort">
            Included {{ cohort.included }} · excluded {{ cohort.excluded }} · no causal conclusion is drawn.
          </p>
        </details>
        <button type="button" (click)="validateCanonicalProfile()" [disabled]="busy || !isCurrent()">Save canonical profile validation</button><p *ngIf="canonicalValidationId">{{ canonicalMessage }}</p><details>
          <summary>Human-reviewed lesson / experiment record</summary>
          <label>Lesson scope<select [(ngModel)]="lessonScope"><option value="ACTUAL_EXECUTION">Verified actual video</option><option value="PROMPT_FIX">Accepted prompt repair</option></select></label><label>Hypothesis<textarea [(ngModel)]="lessonHypothesis"></textarea></label
          ><label>Counterexamples<input [(ngModel)]="counterexamples" /></label
          ><button
            type="button"
            (click)="saveLesson('LESSON')"
            [disabled]="!lessonHypothesis || (lessonScope === 'PROMPT_FIX' ? repairSession?.state !== 'ACCEPTED' : !qa)"
          >
            Save lesson candidate</button
          ><button
            type="button"
            (click)="saveLesson('EXPERIMENT')"
            [disabled]="!lessonHypothesis || (lessonScope === 'PROMPT_FIX' ? repairSession?.state !== 'ACCEPTED' : !qa)"
          >
            Save experiment result
          </button>
          <p *ngIf="lesson">{{ lesson.reviewStatus }} · not automatically applied to frozen rules.</p>
          <ng-container *ngIf="lesson?.reviewStatus === 'PENDING_HUMAN_REVIEW'"
            ><label>Human review reason<input [(ngModel)]="learningReason" /></label
            ><button type="button" (click)="reviewLesson('APPROVED')" [disabled]="!learningReason">
              Approve lesson / experiment</button
            ><button type="button" (click)="reviewLesson('REJECTED')" [disabled]="!learningReason">
              Reject
            </button></ng-container
          >
          <div *ngIf="lesson?.reviewStatus === 'APPROVED'"><label>Revocation reason<input [(ngModel)]="learningReason"></label><button type="button" (click)="reviewLesson('REVOKED')" [disabled]="!learningReason.trim()">Revoke approved lesson</button></div>
        </details>
            </ng-container>
  </ng-container>
  </ng-container>
`,
  styles: [
    `
      .production-review{padding:24px;background:#f7f9fc}.stage-empty-card{display:grid;gap:12px;margin:14px 0;padding:22px;border:1px solid #cbded0;border-radius:12px;background:#f8fbf4}.stage-empty-card h3{margin:0;color:#263f56}.render-readiness-summary{display:grid;grid-template-columns:180px 1fr;gap:8px;padding:12px;border-radius:8px;background:#fff;border:1px solid #dfe7ee}.render-readiness-summary strong{color:#68747c}.render-readiness-summary span{color:#263f56;font-weight:700} .studio-stage-tabs{display:grid;grid-template-columns:repeat(8,minmax(90px,1fr));gap:7px;margin:0 0 14px;padding:6px;border:1px solid #d8e1ec;border-radius:12px;background:#fff;position:sticky;top:.75rem;z-index:10;box-shadow:0 5px 16px rgba(38,63,86,.08)}.studio-stage-tabs button,.stage-subtabs button{display:grid;gap:2px;padding:8px 9px;border:1px solid transparent;border-radius:8px;background:#fff;color:#52616b;text-align:left;font:inherit;cursor:pointer}.studio-stage-tabs button span{font-size:.65rem;color:#6a843e;font-weight:800}.studio-stage-tabs button strong{font-size:.73rem}.studio-stage-tabs button small,.stage-subtabs button small{font-size:.62rem;color:#7a858c}.studio-stage-tabs button.is-active{border-color:#8fbd36;background:#f5faed;box-shadow:0 0 0 2px #eaf3d7;color:#23452f}.studio-stage-tabs button:disabled{opacity:.45;cursor:not-allowed}.stage-subtabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:0 0 16px;padding:5px;border:1px solid #d8e1ec;border-radius:10px;background:#eef4f8}.stage-subtabs button{background:transparent}.stage-subtabs button.is-active{background:#fff;border-color:#8fbd36;color:#23452f}.stage-subtabs button.is-active small{color:#547b3c}.review-hero{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:20px}.review-hero h2{margin:4px 0;font-size:1.7rem;color:#263f56}.review-hero p{margin:0;color:#68747c;font-size:.95rem}.eyebrow,.card-kicker{color:#5f8435;font-size:.7rem;font-weight:800;letter-spacing:.08em}.review-card{display:grid;gap:14px;margin:14px 0;padding:20px;border:1px solid #d8e1ec;border-radius:12px;background:#fff;box-shadow:0 4px 16px rgba(38,63,86,.05)}.review-card header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.review-card h3{margin:3px 0 0;color:#263f56;font-size:1.12rem}.status-pill,.source-badge{display:inline-flex;align-items:center;white-space:nowrap;padding:5px 9px;border-radius:999px;background:#fff5de;color:#855b15;font-size:.67rem;font-weight:800}.status-pill--ready{background:#e8f3dc;color:#31583b}.intent-summary{margin:0;padding:13px;border-left:4px solid #8fbd36;background:#f5faed;color:#40515a;line-height:1.55;white-space:pre-wrap}.intent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.intent-grid>div{display:grid;gap:4px;padding:11px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.intent-grid span{color:#68747c;font-size:.7rem;font-weight:800;text-transform:uppercase}.intent-grid strong{color:#263f56;font-size:.9rem;line-height:1.4}.intent-grid small{color:#68747c;font-size:.72rem}.intent-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.intent-actions details{padding:0;margin-left:auto}.button{display:inline-flex;align-items:center;justify-content:center;padding:9px 13px;border:1px solid #cbd6ce;border-radius:7px;background:#fff;color:#31583b;font-weight:800;cursor:pointer}.button--primary{background:#31583b;color:#fff;border-color:#31583b}.button:disabled{opacity:.5;cursor:default}.settings-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.settings-grid>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.settings-grid span,.reference-summary span{color:#68747c;font-size:.7rem;font-weight:800;text-transform:uppercase}.settings-grid strong{font-size:.95rem;color:#263f56}.settings-grid small{color:#68747c;font-size:.72rem}.settings-editor{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding-top:8px;border-top:1px solid #e4e9e5}.settings-apply{align-self:end;justify-self:end;min-width:140px;max-width:160px;height:40px;margin:0}.advanced-groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.advanced-groups section{display:grid;gap:9px;padding:15px;border:1px solid #dfe7ee;border-radius:10px;background:#fbfcfd}.advanced-groups h4{margin:0;color:#263f56}.advanced-groups label{max-width:none}.setting-note{margin:0;color:#68747c;font-size:.78rem}.setting-note button{margin-left:6px;padding:4px 8px;border:1px solid #b8cdbf;border-radius:6px;background:#fff;color:#31583b;font-weight:700}.diagnostic-list{display:grid;gap:7px;margin:0}.diagnostic-list div{display:grid;grid-template-columns:130px 1fr;gap:8px}.diagnostic-list dt{font-weight:800;color:#68747c}.diagnostic-list dd{margin:0;color:#40515a;overflow-wrap:anywhere}.review-two-column{display:grid;grid-template-columns:1fr 1fr;gap:14px}.review-two-column .review-card{margin:0}.reference-summary{display:grid;grid-template-columns:1fr 1fr;gap:12px}.reference-summary>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px}.reference-summary strong{color:#263f56}.beat-list{display:grid;gap:9px}.beat-list article{display:grid;gap:4px;margin:0;padding:12px;border:1px solid #dfe7ee;border-radius:8px;background:#fbfcfd}.beat-list article strong{color:#31583b}.beat-list article p,.beat-list article small{margin:0;color:#40515a}.source-quote-toggle{justify-self:start;padding:5px 8px;border:1px solid #cbd6ce;border-radius:6px;background:#fff;color:#31583b;font-weight:800;cursor:pointer}.source-quote-panel{padding:10px;border-left:3px solid #8fbd36;background:#f3f7fb;color:#40515a}.source-quote-panel span{font-size:.72rem;font-weight:800;color:#68747c}.source-quote-panel p{margin:5px 0 0;white-space:pre-wrap}.success-note{margin:0;padding:10px 12px;background:#e8f3dc;border:1px solid #b9d7bd;border-radius:8px;color:#31583b;font-weight:700}.missing-state{margin:0;padding:14px;background:#fff9ed;border:1px solid #ecd2a2;border-radius:8px;color:#855b15}.advanced-details{color:#52616b}.advanced-details summary{cursor:pointer;font-weight:800}.readiness-card{border-color:#cbded0}.primary-action{justify-self:start}.restore-note{padding:10px 12px;border-radius:7px;background:#edf5fb;color:#40515a}.technical-settings{margin-top:16px;padding:12px 0}.technical-settings label{max-width:420px}.error{color:#983520}.overview-subtitle{margin:5px 0 0;color:#68747c;font-size:.82rem}.overview-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.overview-facts>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.overview-facts span,.overview-checklist small{color:#68747c;font-size:.72rem}.overview-facts strong{color:#263f56;font-size:.92rem}.overview-checklist{display:grid;gap:8px}.overview-checklist>div{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:10px 12px;border:1px solid #e1e8ee;border-radius:8px;background:#fff}.overview-checklist div div{display:grid;gap:2px}.overview-checklist strong{color:#263f56}.check-icon{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#fff2d5;color:#855b15;font-weight:900}.check-icon--ok{background:#e8f3dc;color:#31583b}.overview-next{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px;border:1px solid #cbded0;border-radius:10px;background:#f5faed}.overview-next div{display:grid;gap:4px}.overview-next strong{color:#263f56}.overview-next p{margin:0;color:#52616b;font-size:.82rem}@media(max-width:600px){.overview-facts{grid-template-columns:1fr}.overview-next{display:grid}.overview-checklist>div{grid-template-columns:auto 1fr}.overview-checklist button{grid-column:2;justify-self:start}}@media(max-width:900px){.studio-stage-tabs{grid-template-columns:repeat(4,minmax(120px,1fr));overflow-x:auto}.settings-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.settings-editor{grid-template-columns:repeat(2,minmax(0,1fr))}.advanced-groups{grid-template-columns:1fr}.render-context-grid,.render-preflight{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.studio-stage-tabs{position:static;grid-template-columns:repeat(2,minmax(0,1fr))}.stage-subtabs{grid-template-columns:repeat(2,minmax(0,1fr))}.production-review{padding:14px}.review-hero{display:grid}.review-two-column,.settings-grid,.settings-editor,.reference-summary,.intent-grid{grid-template-columns:1fr}.review-card{padding:15px}.intent-actions details{margin-left:0}.settings-apply{min-width:0;max-width:none;width:100%}.primary-action{width:100%}.diagnostic-list div{grid-template-columns:1fr}}
      .workflow {
        border: 1px solid #ccd7e4;
        border-radius: 12px;
        padding: 20px;
        margin: 20px 0;
        background: #f7f9fc;
        color: #20334a;
      }
      .inputs {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
      }
      label {
        display: block;
        margin: 10px 0;
      }
      input,
      select,
      textarea {
        display: block;
        max-width: 100%;
        width: 100%;
        padding: 8px;
        border: 1px solid #b8c5d5;
        border-radius: 6px;
      }
      input[type='checkbox'] {
        display: inline;
        width: auto;
      }
      textarea {
        min-height: 85px;
      }
      button {
        margin: 8px 8px 8px 0;
        padding: 8px 12px;
        cursor: pointer;
      }
      button:disabled {
        opacity: 0.5;
        cursor: default;
      }
      article {
        border-top: 1px solid #d4dce8;
        padding: 10px 0;
      }
      details {
        padding: 12px 0;
      }
      .error {
        color: #983520;
      }
      pre,
      small {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
      }
      .analysis-summary-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.analysis-summary-grid article{display:grid;gap:6px;min-width:0}.analysis-summary-grid span,.analysis-summary-grid small{display:block}.analysis-summary-grid strong{overflow-wrap:anywhere}@media(max-width:600px){.analysis-summary-grid{grid-template-columns:1fr}}
      .analysis-summary-decision {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0;padding:16px;border:1px solid #d8e1ec;border-radius:10px;background:#fff}.analysis-summary-decision>div{display:grid;gap:5px;min-width:0}.analysis-summary-decision span{color:#68747c;font-size:.75rem}.analysis-summary-decision strong{overflow-wrap:anywhere}.analysis-summary-decision small{display:block}.inputs article{min-width:0}.inputs p{overflow-wrap:anywhere}@media(max-width:600px){.analysis-summary-decision{grid-template-columns:1fr}}
      .facts {
        background: white;
        padding: 12px;
        margin: 12px 0;
      }
      .stage-action-bar,.analysis-stage-toolbar { display:flex; justify-content:space-between; gap:16px; align-items:center; margin:24px 0 4px; padding:16px; border:1px solid #cbded0; border-radius:10px; background:#f5faed; }
      .stage-action-bar > div,.analysis-stage-toolbar > span { display:grid; gap:4px; }
      .stage-action-bar small,.analysis-stage-toolbar small { color:#52616b; }
      .analysis-stage-toolbar { margin:0 0 16px; background:#fff; border-color:#d8e1ec; }
      .repair-triage,.current-prompt-card,.repair-secondary-details,.repair-candidate-details,.repair-tools-details{margin:0 0 14px;padding:16px;border:1px solid #d8e1ec;border-radius:12px;background:#f8fbfd}
      .repair-triage{display:grid;gap:13px}.repair-triage header h3{margin:3px 0;color:#263f56}.repair-triage header p{margin:4px 0;color:#52616b;line-height:1.5}
      .repair-primary-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.repair-primary-grid article{display:grid;align-content:start;gap:6px;min-width:0;min-height:88px;padding:12px;border:1px solid #dfe7ee;border-radius:9px;background:#fff}.repair-primary-grid span,.repair-secondary-grid span{font-size:.76rem;color:#68747c;font-weight:800;text-transform:uppercase;letter-spacing:.03em}.repair-primary-grid strong,.repair-secondary-grid strong{font-size:.98rem;color:#263f56;overflow-wrap:anywhere;line-height:1.4}
      .no-repair-confirm,.no-repair-saved{display:grid;gap:10px;padding:13px;border:1px solid #d2dfc4;border-radius:9px;background:#fff}.no-repair-confirm label{display:flex;align-items:flex-start;gap:9px;line-height:1.5}.no-repair-confirm input[type=checkbox]{margin-top:3px;flex:0 0 auto}.no-repair-saved{border-color:#9dbd83;background:#f5faed}.no-repair-saved span{overflow-wrap:anywhere;color:#40515a}.no-repair-confirm small{color:#855b15}.no-repair-saved .button{justify-self:start}
      .repair-secondary-details>summary,.repair-tools-details>summary,.current-prompt-card>summary,.repair-candidate-details>summary{cursor:pointer;font-weight:800;color:#263f56}.repair-secondary-details>summary,.repair-tools-details>summary,.current-prompt-card>summary{font-size:.96rem}.repair-secondary-details[open],.repair-tools-details[open],.current-prompt-card[open],.repair-candidate-details[open]{display:grid;gap:12px}.repair-secondary-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.repair-secondary-grid>div{display:grid;align-content:start;gap:5px;min-width:0;padding:11px;border:1px solid #dfe7ee;border-radius:8px;background:#fff}.repair-secondary-details details{padding:10px;border:1px solid #dfe7ee;border-radius:8px;background:#fff}.repair-secondary-details details>summary{cursor:pointer;font-weight:750;color:#263f56}
      .current-prompt-card{background:#fff}.prompt-preview-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;color:#52616b;font-size:.88rem}.prompt-monaco{width:100%;height:340px;min-height:260px;border:1px solid #cbd6ce;border-radius:8px;overflow:hidden}.prompt-fallback-label{display:grid;gap:6px}.prompt-fallback-label textarea,.repair-candidate-details textarea{width:100%;height:340px;min-height:260px;white-space:pre;overflow:auto;resize:vertical;font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}.repair-candidate-details{background:#fff}.repair-candidate-details textarea{height:220px}
      .creative-optimization-details{margin:0 0 14px;padding:16px;border:1px solid #d8e1ec;border-radius:12px;background:#f8fbfd}.creative-optimization-details summary{cursor:pointer;font-weight:800;color:#263f56}.creative-optimization-body{display:grid;gap:12px}.creative-optimization-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;align-items:start}.creative-optimization-card{min-width:0;overflow-wrap:anywhere}.optimization-conclusion{scroll-margin-top:130px;padding:14px;border-left:4px solid #617b36;background:#f1f5eb}.optimization-side-diff table{width:100%;table-layout:fixed;border-collapse:collapse}.optimization-side-diff td,.optimization-side-diff th{width:50%;vertical-align:top;padding:10px;border:1px solid #dfe7ee;white-space:pre-wrap;overflow-wrap:anywhere}.diff-removed{background:#ffe0da;color:#842a1d;text-decoration:line-through;text-decoration-thickness:1px}.diff-added{background:#dcefd5;color:#244c27;font-weight:700}.optimization-side-diff summary{cursor:pointer;font-weight:700}.creative-optimization-card{display:grid;gap:10px;padding:12px;border:1px solid #dfe7ee;border-radius:10px;background:#fff}.creative-optimization-card.is-selected{border-color:#8fbd36;background:#f5faed}.creative-optimization-card header{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}.creative-optimization-card h4{margin:3px 0 0;color:#263f56}.creative-optimization-card p{margin:0;color:#40515a;line-height:1.45}.creative-optimization-actions{display:flex;flex-wrap:wrap;gap:8px}.creative-optimization-diff{margin:0;padding:10px;border:1px solid #dfe7ee;border-radius:8px;background:#fbfcfd;color:#263f56;white-space:pre-wrap;overflow-wrap:anywhere}.creative-optimization-approval{display:grid;gap:8px;padding-top:4px;border-top:1px solid #dfe7ee}.repair-tools-details,.repair-tools-group{background:#fff}.repair-tools-details>summary{padding:2px}.repair-tools-group{display:grid;gap:10px;padding:14px;border:1px solid #dfe7ee;border-radius:10px}.repair-tools-group + .repair-tools-group{margin-top:12px}.repair-tools-group h3{margin:0;color:#263f56}.repair-fields{display:grid;gap:8px}.repair-fields--patch{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}.repair-field{display:grid;gap:5px;min-width:0}.repair-field span{font-weight:650;color:#35464f;line-height:1.4}.repair-field input,.repair-field textarea{max-width:100%;min-width:0;width:100%;height:40px;border:1px solid #cbd6ce;border-radius:8px;padding:8px 10px;box-sizing:border-box;background:#fff;color:#1e2b36}.repair-field textarea{min-height:84px;resize:vertical}.repair-field__text{min-height:84px}.repair-field__input{height:40px}.repair-field--inline{max-width:100%}.repair-consent-row{display:flex;align-items:flex-start;gap:10px;cursor:pointer;font-weight:650;color:#35464f;line-height:1.5}.repair-consent-row input[type=checkbox]{margin-top:2px;flex:0 0 auto}.repair-help,.repair-field-help,.repair-tools-group small{margin:0;color:#52616b;line-height:1.45}.repair-button-row,.repair-tool-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.repair-button-row > .button,.repair-tool-actions > .button{width:auto;margin:0}.button.button--compact,.repair-triage .button{min-width:0;min-height:40px;height:40px;padding:0 14px;border-radius:8px;font-size:13px;line-height:1}.repair-triage .button{justify-self:start}.repair-triage button:disabled,.repair-tools-details button:disabled,.repair-button-row button:disabled,.repair-tool-actions button:disabled{opacity:.58;cursor:not-allowed}.repair-triage button:focus-visible,.repair-tools-details button:focus-visible,.current-prompt-card button:focus-visible,.repair-tools-details input:focus-visible,.repair-tools-details textarea:focus-visible{outline:3px solid #345f9a;outline-offset:2px}.repair-tools-details .error{color:#983520}

      .optimization-score{font-size:28px;font-weight:800;color:#263f56!important}.optimization-score small{font-size:13px;font-weight:600;margin-left:6px}.optimization-classification{font-size:12px;font-weight:800;letter-spacing:.02em}.optimization-detail-link{color:#345f9a;font-weight:700}.optimization-panel{min-width:0;border-top:1px solid #dfe7ee;padding:10px 0}.optimization-panel>summary{padding:4px 0;cursor:pointer;color:#263f56;font-weight:750}.optimization-panel p{margin:8px 0;line-height:1.5;color:#40515a}.optimization-panel ul{margin:8px 0;padding-left:22px;line-height:1.5}.optimization-candidate-details{min-width:0}.optimization-candidate-details>h4{margin:8px 0;color:#263f56}.optimization-prompt-panel .button{margin:8px 0}.creative-optimization-diff{max-height:400px;overflow:auto;min-width:0;max-width:100%;box-sizing:border-box;word-break:break-word}.optimization-diff-controls{display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin:12px 0}.optimization-diff-controls label{display:flex;gap:8px;align-items:center;flex-wrap:wrap;min-width:0}.optimization-diff-controls select{max-width:100%;min-width:0;padding:8px;border:1px solid #cbd6ce;border-radius:6px;background:#fff;color:#263f56}.optimization-panel summary:focus-visible,.creative-optimization-body button:focus-visible,.creative-optimization-body a:focus-visible,.optimization-diff-controls input:focus-visible,.optimization-diff-controls select:focus-visible{outline:3px solid #345f9a;outline-offset:3px}.optimization-side-diff{overflow:hidden}.optimization-side-diff table{font-size:13px}.creative-optimization-body{min-width:0}.optimization-conclusion p{margin:8px 0;line-height:1.5}.creative-optimization-approval{padding:12px 0}.creative-optimization-card .creative-optimization-actions{padding-top:4px}.optimization-eligibility{border-top:1px solid #dfe7ee;padding-top:8px}
      .optimization-review-heading{scroll-margin-top:calc(var(--review-navigation-inset,0px) + 1rem)}.optimization-review-heading:focus{outline:3px solid #345f9a;outline-offset:3px}
      @media(max-width:600px){.creative-optimization-grid{grid-template-columns:1fr}.creative-optimization-details{padding:12px}.optimization-side-diff td,.optimization-side-diff th{padding:6px}.optimization-diff-controls{display:grid;gap:10px}.optimization-score{font-size:25px}}
      @media(max-width:900px){.repair-primary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.repair-secondary-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @media(max-width:1100px){.creative-optimization-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @media(max-width:600px){.creative-optimization-grid{grid-template-columns:1fr}}
      @media(max-width:600px){.repair-triage,.current-prompt-card,.repair-secondary-details,.repair-candidate-details,.repair-tools-details{padding:13px}.repair-primary-grid,.repair-secondary-grid,.repair-fields--patch{grid-template-columns:1fr}.repair-primary-grid article{min-height:0}.prompt-preview-toolbar{align-items:flex-start}.prompt-monaco,.prompt-fallback-label textarea{height:320px;min-height:280px}.repair-triage .button{width:auto;max-width:100%}.repair-button-row,.repair-tool-actions{display:grid;grid-template-columns:1fr}.repair-tool-actions .button,.repair-button-row .button{width:100%}.repair-field input,.repair-field textarea{font-size:16px}}
      .findings-resolution{display:grid;gap:12px;margin:16px 0;padding:16px;border:1px solid #d8e1ec;border-radius:12px;background:#f8fbfd}.findings-resolution header h3{margin:3px 0;color:#263f56}.findings-resolution header p{margin:4px 0;color:#68747c;font-size:.82rem}.resolution-list{display:grid;gap:9px}.resolution-item{display:grid;gap:6px;padding:12px;border:1px solid #dfe7ee;border-radius:9px;background:#fff}.resolution-item--blocking{border-left:4px solid #b9503e}.resolution-item__title{display:flex;gap:9px;align-items:center;flex-wrap:wrap}.resolution-item__title strong{color:#263f56}.resolution-category{font-size:.64rem;font-weight:800;color:#5f8435;letter-spacing:.06em}.resolution-item p{margin:0;color:#40515a}.resolution-item small{color:#68747c}.resolution-item .button{justify-self:start;margin:3px 0 0}.render-context-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.render-context-grid>div,.render-preflight>div{display:grid;gap:4px;padding:10px;border:1px solid #dfe7ee;border-radius:8px;background:#fff}.render-context-grid span,.render-preflight span{font-size:.68rem;color:#68747c;font-weight:800;text-transform:uppercase}.render-context-grid strong,.render-preflight strong{color:#263f56;font-size:.86rem;overflow-wrap:anywhere}.render-preflight{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.render-preflight small{color:#855b15;font-size:.7rem}.render-stage-card{display:grid;gap:14px}
      .disabled-link { pointer-events:none; opacity:.5; }
      .analysis-stage-footer { display:flex; justify-content:space-between; gap:12px; align-items:center; margin:24px 0 4px; padding-top:16px; border-top:1px solid #d4dce8; }
      .analysis-stage-footer .button { margin:0; }
      .creative-quality-panel ul { margin:8px 0 0; padding-left:20px; }
      .source-details { margin:8px 0 14px; color:#526273; }
      .source-details summary { cursor:pointer; font-weight:600; }
      @media (max-width: 700px) { .analysis-stage-footer { flex-direction:column; align-items:stretch; } }
      .canonical-rule-evaluation { display:grid; gap:14px; margin:20px 0; padding:18px; border:1px solid #d8e1ec; border-radius:12px; background:#f8fbfd; }
      .canonical-rule-evaluation header h3 { margin:3px 0; color:#263f56; }
      .canonical-rule-evaluation header p { margin:4px 0; color:#68747c; font-size:.82rem; }
      .canonical-summary-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:10px; }
      .canonical-summary-grid > div { display:grid; gap:3px; padding:10px; border:1px solid #dfe7ee; border-radius:8px; background:#fff; }
      .canonical-summary-grid span { font-size:.68rem; color:#68747c; font-weight:800; text-transform:uppercase; }
      .canonical-summary-grid strong { color:#263f56; font-size:.9rem; }
      .canonical-video-plan { padding:12px; border:1px solid #dfe7ee; border-radius:8px; background:#fff; }
      .canonical-video-plan h4 { margin:0 0 8px; color:#263f56; }
      .canonical-rules-list { display:grid; gap:8px; }
      .canonical-rules-list h4 { margin:0; color:#263f56; }
      .canonical-rule-item { display:grid; gap:4px; padding:10px; border-radius:8px; border-left:4px solid #d4dce8; background:#fff; }
      .canonical-rule-item.rule-pass { border-left-color:#5f8435; }
      .canonical-rule-item.rule-fail { border-left-color:#b9503e; }
      .canonical-rule-item.rule-unknown { border-left-color:#855b15; }
      .canonical-rule-item.rule-na { border-left-color:#b8c5d5; }
      .rule-outcome-badge { display:inline-block; font-size:.64rem; font-weight:800; padding:2px 6px; border-radius:4px; letter-spacing:.04em; }
      .rule-outcome-badge.pass { background:#e8f5e0; color:#5f8435; }
      .rule-outcome-badge.fail { background:#fde8e4; color:#b9503e; }
      .rule-outcome-badge.unknown { background:#fdf3e0; color:#855b15; }
      .rule-outcome-badge.na { background:#e8edf3; color:#52616b; }
      .rule-outcome-badge.error { background:#fde8e4; color:#b9503e; }
      .rule-family { font-size:.68rem; color:#68747c; text-transform:uppercase; }
      .canonical-rule-item strong { color:#263f56; }
      .canonical-rule-item p { margin:0; color:#40515a; font-size:.86rem; }
      .canonical-rule-item small { color:#68747c; font-size:.78rem; }
      .outcome-pass { color:#5f8435 !important; }
      .outcome-fail { color:#b9503e !important; }
      .outcome-unknown { color:#855b15 !important; }
      .outcome-na { color:#52616b !important; }
      .outcome-error { color:#b9503e !important; }
    `,
  ],
})
export class PostFamilyWorkflowComponent implements OnChanges, OnDestroy {
  private promptPreviewHost?: ElementRef<HTMLDivElement>;
  private promptPreviewEditor: {
    dispose(): void;
    getValue(): string;
    setValue(value: string): void;
    setScrollTop(value: number): void;
    layout(): void;
  } | null = null;
  private promptPreviewLoadSequence = 0;
  promptPreviewEditorReady = false;
  promptPreviewLoadError = '';
  @ViewChild('promptPreviewEditor')
  set promptPreviewElement(host: ElementRef<HTMLDivElement> | undefined) {
    this.promptPreviewHost = host;
    if (host) this.initializePromptPreview();
    else this.disposePromptPreview();
  }
  private initializePromptPreview(): void {
    const host = this.promptPreviewHost;
    if (!host || this.promptPreviewEditor) return;
    const sequence = ++this.promptPreviewLoadSequence;
    import('monaco-editor/esm/vs/editor/editor.api').then(monaco => {
      if (sequence !== this.promptPreviewLoadSequence || !this.promptPreviewHost) return;
      this.promptPreviewEditor = monaco.editor.create(this.promptPreviewHost.nativeElement, {
        value: this.prompt,
        language: 'markdown',
        automaticLayout: true,
        minimap: { enabled: false },
        wordWrap: 'on',
        lineNumbers: 'on',
        readOnly: true,
        fontSize: 13,
        scrollBeyondLastLine: false,
        padding: { top: 12, bottom: 12 },
      });
      this.promptPreviewEditor.setScrollTop(0);
      this.promptPreviewEditorReady = true;
      this.promptPreviewLoadError = '';
      window.setTimeout(() => this.promptPreviewEditor?.layout(), 0);
      this.changeDetector.markForCheck();
    }).catch(() => {
      if (sequence !== this.promptPreviewLoadSequence) return;
      this.promptPreviewLoadError = 'The editor preview could not be loaded; the read-only text fallback is available.';
      this.changeDetector.markForCheck();
    });
  }
  private disposePromptPreview(): void {
    this.promptPreviewLoadSequence++;
    this.promptPreviewEditor?.dispose();
    this.promptPreviewEditor = null;
    this.promptPreviewEditorReady = false;
  }
  private http = inject(HttpClient);
  private changeDetector = inject(ChangeDetectorRef);
  private readonly reviewNavigationInjector = inject(Injector);
  private reviewNavigationSequence = 0;
  private readonly optimizationReviewedSnapshots = new Map<string, string>();
  @ViewChildren('optimizationReviewSection', {read:ElementRef}) private optimizationReviewSections!: QueryList<ElementRef<HTMLElement>>;
  @ViewChildren('optimizationReviewHeading', {read:ElementRef}) private optimizationReviewHeadings!: QueryList<ElementRef<HTMLElement>>;
  @Input() prompt = '';
  @Input() contentId = '';
  @Input() promptVersionId = '';
  @Input() promptVersionNumber: number | null = null;
  @Input() creativeProvenance: any = null;
  @Input() contentTitle = '';
  @Input() sourcePath = '';
  @Input() videoPath = '';
  @Input() workflowProfile = 'FROZEN';
  @Output() saveFinal = new EventEmitter<string>();
  @Output() acceptedVersion = new EventEmitter<{contentId: number; promptVersionId: number; rawText: string; repairSessionId: string}>();
  @Output() stageChanged = new EventEmitter<number>();
  activeStage = 4;
  activeProductionTab: 'overview' | 'creative' | 'execution' | 'references' = 'overview';
  activeAnalysisTab: 'summary' | 'creative' | 'feasibility' | 'evidence' = 'summary';
  readonly studioStages = [
    { id: 1, title: 'Idea', status: 'Brief' },
    { id: 2, title: 'Story', status: 'Approved story' },
    { id: 3, title: 'Prompt', status: 'Saved prompt' },
    { id: 4, title: 'Production Review', status: 'Current' },
    { id: 5, title: 'Quality Analysis', status: 'Evidence' },
    { id: 6, title: 'Repair', status: 'Optional' },
    { id: 7, title: 'Render', status: 'Authorization' },
    { id: 8, title: 'Video QA', status: 'Actual video' },
  ];
  readonly analysisTabs = [
    { id: 'summary' as const, title: 'Summary', description: 'Decision and next action' },
    { id: 'creative' as const, title: 'Creative Quality', description: 'Opening, progression and ending' },
    { id: 'feasibility' as const, title: 'Production Feasibility', description: 'Risks and authorization' },
    { id: 'evidence' as const, title: 'Evidence & Diagnostics', description: 'Source spans and developer evidence' },
  ];
  readonly productionTabs = [
    { id: 'overview' as const, title: 'Overview', description: 'Summary and next action' },
    { id: 'creative' as const, title: 'Creative & Settings', description: 'Intent and saved settings' },
    { id: 'execution' as const, title: 'Execution Plan', description: 'Source-backed events' },
    { id: 'references' as const, title: 'References', description: 'Character and first frame' },
  ];
  private readonly preparationRouter = inject(Router, {optional:true});
  selectStage(stage: number) {
    if (stage === 7 && this.review) { void this.preparationRouter?.navigateByUrl(this.renderPreparationLink()); return; }
    if (stage > 4 && !this.review) return;
    this.activeStage = stage;
    if(stage===5)this.loadSourcePlan();
    this.persistUiLocation();
    this.stageChanged.emit(stage);
    this.changeDetector.markForCheck();
  }
  get analysisExportState(): 'ANALYSIS_AVAILABLE' | 'ANALYSIS_RUNNING' | 'NO_ANALYSIS' | 'ANALYSIS_FAILED' | 'ANALYSIS_STALE' {
    if (!this.review) return 'NO_ANALYSIS';
    const status = String(this.review.reviewStatus || this.review.status || '').toUpperCase();
    if (['RUNNING', 'PENDING', 'IN_PROGRESS'].includes(status)) return 'ANALYSIS_RUNNING';
    if (['FAILED', 'SERVICE_ERROR', 'ERROR'].includes(status)) return 'ANALYSIS_FAILED';
    if (!this.isCurrent()) return 'ANALYSIS_STALE';
    return 'ANALYSIS_AVAILABLE';
  }
  get analysisExportMessage(): string {
    return ({ ANALYSIS_AVAILABLE: 'Download the saved report for this exact analysis run.', ANALYSIS_RUNNING: 'The analysis is still running.', NO_ANALYSIS: 'Run Quality Analysis before exporting.', ANALYSIS_FAILED: 'A failed analysis cannot be exported as a successful report.', ANALYSIS_STALE: 'This report is stale for the current prompt or settings.' } as Record<string, string>)[this.analysisExportState];
  }
  get nextAnalysisAction(): string {
    const recommendation = String(this.review?.planQuality?.recommendation || this.review?.recommendation || '').toUpperCase();
    if (recommendation.includes('REPAIR') || String(this.review?.planQuality?.status || '').toUpperCase().includes('FAIL')) return 'Review Prompt Repair';
    if (this.resolutionItems().length) return 'Resolve Outstanding Findings';
    return 'Open Render Preparation';
  }
  get renderAuthorizationReason(): string {
    const reasons = this.review?.family8?.renderAuthorization?.reasons;
    if (Array.isArray(reasons) && reasons.length) return reasons.map((reason: any) => String(reason.message || reason.code || reason)).join(' · ');
    return this.review?.family8?.renderAuthorization?.reason || 'No canonical blocker explanation recorded.';
  }
  resolutionItems(): Array<any> {
    const r = this.review;
    if (!r) return [];
    const items: Array<any> = [];
    const auth = String(r.family8?.renderAuthorization?.status || '').toUpperCase();
    const uncertainty = (r.productionEvidence?.remainingUncertainty || []).map((value: unknown) => String(value));
    const unknownKeys = Array.isArray(r.generalProducibility?.unknownDimensions) ? r.generalProducibility.unknownDimensions : [];
    const unknownDimensions = unknownKeys.map((key: string) => ({ key, reason: r.generalProducibility?.dimensions?.[key]?.reason || '' }));
    const unresolvedText = [...uncertainty, ...unknownDimensions.map((d: any) => `${d.key || d.dimension || ''} ${d.reason || ''}`)].join(' ').toLowerCase();
    if (!this.intentConfirmed || /mechanism|intent|story|source/.test(unresolvedText)) items.push({category:'OPERATOR_CLARIFICATION', finding:'Source intent or story mechanism needs confirmation', why:'The analysis cannot distinguish an extracted source fact from an operator decision.', action:'Confirm supported intent or correct the source-bound intent.', owner:'Creative / Analysis', button:'Review creative intent', blocking:false, target:4});
    if (!this.references.length || /reference|character asset/.test(unresolvedText)) items.push({category:'REFERENCE_REQUIRED', finding:'Character reference is missing or unverified', why:'Identity continuity cannot be checked from an authoritative visual asset.', action:'Select or verify a character reference in Render preparation.', owner:'References / Render', button:'Prepare visual references', blocking:false, target:7});
    if (!this.firstFramePath && !this.firstFrameUrl || /start.?frame|first.?frame/.test(unresolvedText)) items.push({category:'PROVIDER_INPUT_REQUIRED', finding:'Accepted first frame is missing', why:'The selected image-to-video workflow has no bound opening frame.', action:'Attach or prepare a first frame; generation remains explicitly opt-in.', owner:'Render', button:'Open render preparation', blocking:auth.includes('BLOCKED'), target:7});
    if (!this.sourceEvents.length && !r.productionEvidence?.videoPlanIR?.beats?.length) items.push({category:'SOURCE_RECOVERABLE', finding:'Source events were not extracted', why:'The saved prompt contains no mapped execution beats for the evaluator.', action:'Reload deterministic source evidence and validate the saved version.', owner:'Analysis', button:'Resolve source evidence', blocking:false, target:4});
    if (/actual|video|render|opening/.test(unresolvedText) && !this.qa) items.push({category:'POST_RENDER_EVIDENCE', finding:'Actual video evidence is unavailable', why:'Output quality can only be established after a completed clip is inspected.', action:'Run Video QA after an authorized render; this is not a preliminary render prerequisite.', owner:'Video QA', button:'Open Video QA', blocking:false, target:8});
    if (String(r.planQuality?.recommendation || r.recommendation || '').toUpperCase().includes('REPAIR') || String(r.planQuality?.status || '').toUpperCase().includes('FAIL')) items.push({category:'UNRESOLVED_OR_UNSUPPORTED', finding:'The saved prompt has a confirmed quality defect', why:'The canonical review recommends a bounded correction before render.', action:'Open the existing bounded Repair stage and review the selected finding.', owner:'Repair', button:'Open repair plan', blocking:true, target:6});
    const canonicalReasons = Array.isArray(r.family8?.renderAuthorization?.reasons) ? r.family8.renderAuthorization.reasons : [];
    const groups = new Map<string, any>();
    for (const reason of canonicalReasons) {
      const code=String(reason?.code || 'UNKNOWN_AUTHORIZATION_REASON');
      const source=String(reason?.source || 'UNKNOWN');
      const normalized=`${code} ${source} ${reason?.message || ''}`.toLowerCase();
      const technical=/technical_failure|parser_timeout|required_service_failure/.test(code.toLowerCase());
      const referenceIssue=!technical && /reference|character asset/.test(normalized);
      const frameIssue=!technical && /first.?frame|start.?frame|execution_inputs/.test(normalized);
      const sourceIssue=!technical && /contradict/.test(normalized) && (reason?.references || []).length >= 2;
      const providerIssue=!technical && /provider|generator|capability|duration|aspect.?ratio|settings/.test(normalized);
      const key=referenceIssue?'reference':frameIssue?'first-frame':`${code}:${source}`;
      const existing=groups.get(key);
      if(existing){existing.relatedReasons.push(reason);continue;}
      // One action per missing input, retaining every distinct canonical reason.
      if(referenceIssue || frameIssue){for(let i=items.length-1;i>=0;i--)if(items[i].category===(referenceIssue?'REFERENCE_REQUIRED':'PROVIDER_INPUT_REQUIRED'))items.splice(i,1);}
      const item={id:`AUTHORIZATION:${code}:${source}`,category:technical?'TECHNICAL_ASSESSMENT_REQUIRED':sourceIssue?'SOURCE_EVIDENCE_CONTRADICTION':referenceIssue||frameIssue?'RENDER_INPUT_REQUIRED':providerIssue?'PROVIDER_SETTINGS':'CANONICAL_AUTHORIZATION_BLOCKER',
        finding:this.authorizationReasonText(reason),why:technical?'This saved technical validation failed; render authorization remains blocked. This is not verified evidence of a story contradiction.':'This requirement contributes to the saved Family 8 render decision.',
        action:technical?'Inspect the saved validation diagnostic and input contract. No prompt change is justified by this failure alone.':sourceIssue?'Inspect the conflicting source references and resolve with grounded evidence.':referenceIssue?'Select and bind a verified character asset.':frameIssue?'Select or upload a first frame; image generation remains separately opt-in.':providerIssue?'Review the selected generator and saved execution settings.':'Inspect the saved diagnostic; supporting evidence remains UNKNOWN.',
        owner:technical?'Technical review':sourceIssue?'Source review':referenceIssue||frameIssue||providerIssue?'Render Preparation':'Technical review',
        button:technical?'Open diagnostics':sourceIssue?'Review source evidence':referenceIssue||frameIssue||providerIssue?'Open render preparation':'Open diagnostics',
        blocking:true,target:technical?5:sourceIssue?4:referenceIssue||frameIssue||providerIssue?7:5,severity:'BLOCKING',status:'UNVERIFIED',evidence:technical?this.technicalDiagnostic():`${source} · ${(reason?.references||[]).join(', ') || 'Supporting source references UNKNOWN'}`,relatedReasons:[reason],revalidationRequired:true,promptRevisionRequired:false};
      groups.set(key,item);items.push(item);
    }
    return items;
  }
  resolveFinding(item: {target: number; category: string}): void {
    this.selectStage(item.target);
    if(item.target===5)this.selectAnalysisTab('evidence');
    if (item.target === 4) this.selectProductionTab(['SOURCE_RECOVERABLE', 'SOURCE_EVIDENCE_CONTRADICTION'].includes(item.category) ? 'execution' : 'creative');
  }
  continueToRepair(): void {
    if (!this.review || !this.isCurrent()) return;
    this.selectStage(6);
  }
  creativeOptimizationPlanFirstNewAttempt = false;
  get validCreativeOptimizationBudget(): boolean {
    const value = Number(this.creativeOptimizationBudget);
    return Number.isFinite(value) && value > 0 && value <= 20;
  }
  canSelectOptimizationCandidate(candidate: any): boolean {
    const assessment = this.creativeOptimizationComparison?.comparisonAssessment;
    const count = this.creativeOptimizationComparison?.candidates?.length;
    const complete = assessment?.contractVersion === 'creative-reconstruction-v2'
      ? count >= 1 && count <= 2 && assessment?.actualCandidateCount === count && assessment?.integrityStatus === 'COMPLETE_CANDIDATE_SET'
      : count === 2 && assessment?.actualCandidateCount === 2 && assessment?.integrityStatus === 'COMPLETE_TWO_CANDIDATES';
    return complete && assessment?.lineageVerified === true && String(assessment.lineage?.analysisRunId) === String(this.review?.recordId)
      && String(assessment.lineage?.promptVersionId) === String(this.promptVersionId)
      && String(assessment.lineage?.contentId) === String(this.contentId)
      && ['VALID_MINOR_VARIATION', 'VALID_MATERIAL_VARIATION', 'VALID_WITH_UNPROVEN_BENEFIT', 'PLAUSIBLE_IMPROVEMENT_UNVERIFIED', 'MATERIAL_IMPROVEMENT_SUPPORTED'].includes(candidate.currentAssessment?.classification);
  }
  optimizationScoreDelta(candidate: any): string {
    const value = Number(candidate.review?.canonicalRuleEvaluation?.score) - Number(this.review?.canonicalRuleEvaluation?.score);
    const displayed = Number(value.toFixed(2));
    return Number.isFinite(value) ? `${displayed > 0 ? '+' : ''}${displayed}` : 'UNKNOWN';
  }
  optimizationDiffCandidateId: string | null = null;
  optimizationShowUnchanged = false;
  optimizationCopyStatus = '';
  get optimizationDiffCandidate(): any {
    const candidates = this.creativeOptimizationComparison?.candidates || [];
    return candidates.find((candidate: any) => candidate.candidateId === this.optimizationDiffCandidateId) || candidates[0] || {};
  }
  get optimizationVisibleDiffRows(): {before: string; after: string; changed: boolean}[] {
    return this.optimizationDiffRows(this.optimizationDiffCandidate).filter(row => this.optimizationShowUnchanged || row.changed);
  }
  private optimizationTokenDiffCache = new Map<string, {before: {text: string; changed: boolean}[]; after: {text: string; changed: boolean}[]}>();
  optimizationInlineDiff(row: {before: string; after: string}): {before: {text: string; changed: boolean}[]; after: {text: string; changed: boolean}[]} {
    const key = JSON.stringify([row.before, row.after]);
    const cached = this.optimizationTokenDiffCache.get(key);
    if (cached) return cached;
    // Compare only saved alternative text. Token boundaries preserve original whitespace exactly.
    const tokenize = (text: string) => text.match(/\s+|[\p{L}\p{N}_]+|[^\s\p{L}\p{N}_]/gu) || [];
    const before = tokenize(row.before), after = tokenize(row.after);
    const result = {before: before.map(text => ({text, changed: true})), after: after.map(text => ({text, changed: true}))};
    const widths = after.length + 1;
    // Prompt rows are normally short; bound the table for unexpectedly large saved text.
    if (before.length * after.length <= 1000000) {
      const lengths = Array.from({length: before.length + 1}, () => new Uint32Array(widths));
      for (let i = before.length - 1; i >= 0; i--) for (let j = after.length - 1; j >= 0; j--)
        lengths[i][j] = before[i] === after[j] ? lengths[i + 1][j + 1] + 1 : Math.max(lengths[i + 1][j], lengths[i][j + 1]);
      let i = 0, j = 0;
      while (i < before.length && j < after.length) {
        if (before[i] === after[j]) {result.before[i++].changed = false; result.after[j++].changed = false;}
        else if (lengths[i + 1][j] >= lengths[i][j + 1]) i++; else j++;
      }
    } else {
      let i = 0;
      while (i < before.length && i < after.length && before[i] === after[i]) {result.before[i].changed = false; result.after[i++].changed = false;}
      let left = before.length - 1, right = after.length - 1;
      while (left >= i && right >= i && before[left] === after[right]) {result.before[left--].changed = false; result.after[right--].changed = false;}
    }
    if (this.optimizationTokenDiffCache.size >= 64) this.optimizationTokenDiffCache.clear();
    this.optimizationTokenDiffCache.set(key, result);
    return result;
  }
  optimizationSimilarity(candidate: any): string {
    const value = candidate.currentAssessment?.textSimilarity;
    return typeof value === 'number' && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'UNKNOWN';
  }
  openOptimizationPanel(id: string, event: Event): void {
    event.preventDefault();
    const panel = document.getElementById(id) as HTMLDetailsElement | null;
    if (panel) { panel.open = true; panel.querySelector('summary')?.focus(); panel.scrollIntoView?.({block: 'nearest'}); }
  }
  async copyOptimizationPrompt(value: string): Promise<void> {
    try { await navigator.clipboard.writeText(value); this.optimizationCopyStatus = 'Candidate prompt copied.'; }
    catch { this.optimizationCopyStatus = 'Copy unavailable. Select the full prompt text to copy it.'; }
    this.changeDetector.markForCheck();
  }
  optimizationDiffRows(candidate: any): {before: string; after: string; changed: boolean}[] {
    const rows: {before: string; after: string; changed: boolean}[] = [];
    let removed: string[] = [], added: string[] = [];
    const flush = () => { for (let i=0;i<Math.max(removed.length,added.length);i++) rows.push({before:removed[i]||'',after:added[i]||'',changed:true});removed=[];added=[]; };
    for (const line of String(candidate.diff || '').split('\n')) {
      if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@')) continue;
      if (line.startsWith('-')) removed.push(line.slice(1));
      else if (line.startsWith('+')) added.push(line.slice(1));
      else {flush();const text=line.startsWith(' ')?line.slice(1):line;rows.push({before:text,after:text,changed:false});}
    }
    flush();return rows;
  }
  get creativeOptimizationApprovalEnabled(): boolean {
    if (!this.creativeOptimizationComparison || !this.creativeOptimizationSelectedCandidateId) return false;
    const candidate = this.creativeOptimizationSelectedCandidate;
    if (!candidate || !this.canSelectOptimizationCandidate(candidate) || candidate.currentAssessment?.approvalEligible !== true) return false;
    const reviewed = this.optimizationReviewedSnapshots.get(candidate.candidateId) === this.optimizationReviewSignature(candidate);
    if (!reviewed) return false;
    const fidelity = candidate.fidelity ?? {};
    const essential = candidate.essentialEventsPreserved ?? fidelity.essentialEventsPreserved ?? true;
    const coverage = candidate.approvedStoryCoverage ?? fidelity.approvedStoryCoverage ?? fidelity.storyCoverage ?? null;
    return Boolean(essential) && !!coverage;
  }
  get creativeOptimizationSelectedCandidate(): any {
    if (!this.creativeOptimizationComparison) return null;
    if (!this.creativeOptimizationSelectedCandidateId) return null;
    return this.creativeOptimizationComparison.candidates.find((candidate: any) => candidate.candidateId === this.creativeOptimizationSelectedCandidateId) || null;
  }
  selectCreativeOptimizationCandidate(candidateId: string | null): void {
    this.creativeOptimizationSelectedCandidateId = candidateId;
    if (!candidateId) {
      this.creativeOptimizationReviewedCandidateId = null;
      this.creativeOptimizationError = '';
      this.changeDetector.markForCheck();
      return;
    }
    if (candidateId !== 'ORIGINAL' && !this.canSelectOptimizationCandidate(this.creativeOptimizationComparison?.candidates?.find((c: any) => c.candidateId === candidateId))) { this.creativeOptimizationError = 'Candidate is invalid, stale or not currently validated.'; return; }
    if (this.creativeOptimizationReviewedCandidateId !== candidateId) {
      this.creativeOptimizationReviewedCandidateId = null;
    }
    this.creativeOptimizationError = '';
    this.changeDetector.markForCheck();
  }
  reviewCreativeOptimizationCandidate(candidateId: string): void {
    if (!this.creativeOptimizationComparison) return;
    const candidate = this.creativeOptimizationComparison.candidates.find((item: any) => item.candidateId === candidateId);
    if (!candidate || this.creativeOptimizationBusy) return;
    this.creativeOptimizationReviewedCandidateId = candidateId;
    this.optimizationReviewedSnapshots.set(candidateId, this.optimizationReviewSignature(candidate));
    this.creativeOptimizationError = '';
    const comparison = this.creativeOptimizationComparison;
    const navigation = ++this.reviewNavigationSequence;
    this.changeDetector.markForCheck();
    afterNextRender(() => {
      // Resolve the current view after rendering; superseded clicks/reloads must not jump.
      if (navigation !== this.reviewNavigationSequence || comparison !== this.creativeOptimizationComparison) return;
      const section = this.optimizationReviewSections?.find(ref => ref.nativeElement.dataset['candidateId'] === candidateId)?.nativeElement;
      const heading = this.optimizationReviewHeadings?.find(ref => ref.nativeElement.dataset['candidateId'] === candidateId)?.nativeElement;
      if (!section || !heading) return;
      section.querySelectorAll<HTMLDetailsElement>('.optimization-actual-changes,.optimization-quality-panel').forEach(panel => panel.open = true);
      const target = heading.getBoundingClientRect();
      let inset = 0;
      document.querySelectorAll<HTMLElement>('nav,header').forEach(element => {
        const style = getComputedStyle(element), rect = element.getBoundingClientRect(), top = Number.parseFloat(style.top);
        if (['sticky','fixed'].includes(style.position) && Number.isFinite(top) && rect.height > 0 && rect.left < target.right && rect.right > target.left)
          inset = Math.max(inset, top + rect.height);
      });
      heading.style.setProperty('--review-navigation-inset', `${inset}px`);
      heading.focus({preventScroll:true});
      heading.scrollIntoView?.({block:'start', behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    }, {injector:this.reviewNavigationInjector});
  }
  private optimizationReviewSignature(candidate: any): string {
    return JSON.stringify([this.creativeOptimizationComparison?.recordId, this.creativeOptimizationComparison?.comparisonAssessment?.lineage, candidate]);
  }
  loadLatestCreativeOptimization(): void {
    if (!this.contentId || !this.promptVersionId || !this.review?.recordId) return;
    this.creativeOptimizationError = '';
    const latestPath = `/api/v1/intelligence/workflow/records/${encodeURIComponent(String(this.review.recordId))}/creative-optimization/latest`;
    this.http.get<any>(latestPath).subscribe({
      next: (payload) => {
        const previous = this.creativeOptimizationComparison;
        const selected = this.creativeOptimizationSelectedCandidateId;
        const reviewed = this.creativeOptimizationReviewedCandidateId;
        this.creativeOptimizationComparison = payload?.comparison ?? null;
        if(payload?.attempt?.optimizationFailed) this.creativeOptimizationError=this.creativeOptimizationFailureMessage({error:payload.attempt});
        const sameSavedRecord = !!previous?.recordId && previous.recordId === this.creativeOptimizationComparison?.recordId;
        const candidate = this.creativeOptimizationComparison?.candidates?.find((item: any) => item.candidateId === selected);
        const preserve = sameSavedRecord && (selected === 'ORIGINAL' || (candidate && this.canSelectOptimizationCandidate(candidate)));
        this.creativeOptimizationSelectedCandidateId = preserve ? selected : null;
        const reviewedCandidate = this.creativeOptimizationComparison?.candidates?.find((item: any) => item.candidateId === reviewed);
        this.creativeOptimizationReviewedCandidateId = sameSavedRecord && !!reviewedCandidate && JSON.stringify(previous?.candidates?.find((item: any) => item.candidateId === reviewed)) === JSON.stringify(reviewedCandidate) ? reviewed : null;
        this.creativeOptimizationConsent = false;
        this.creativeOptimizationBusy = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.creativeOptimizationComparison = null;
        this.creativeOptimizationSelectedCandidateId = null;
        this.creativeOptimizationReviewedCandidateId = null;
        this.creativeOptimizationError = 'Creative optimization status is unavailable. No automatic candidate was approved.';
        this.changeDetector.markForCheck();
      },
    });
  }
  generateCreativeOptimizationCandidates(): void {
    if (this.creativeOptimizationBusy) return;
    if (!this.review?.recordId || !this.contentId || !this.promptVersionId) {
      this.creativeOptimizationError = 'Current analysis and saved prompt version are required to generate creative candidates.';
      return;
    }
    if (!this.creativeOptimizationConsent || !this.validCreativeOptimizationBudget) {
      this.creativeOptimizationError = 'Explicit paid-call consent and a valid budget up to $20 are required before generation.';
      return;
    }
    this.creativeOptimizationBusy = true;
    this.creativeOptimizationError = '';
    const generationPath = `/api/v1/intelligence/workflow/records/${encodeURIComponent(String(this.review.recordId))}/creative-optimization`;
    this.http.post<any>(generationPath, {
      contentId: Number(this.contentId),
      promptVersionId: Number(this.promptVersionId),
      startNewPlanFirstAttempt: this.creativeOptimizationPlanFirstNewAttempt,
      operatorAuthorized: true,
      maxCostUsd: Number(this.creativeOptimizationBudget),
    }).subscribe({
      next: (payload) => {
        if(payload?.optimizationFailed){this.creativeOptimizationComparison=null;this.creativeOptimizationError=this.creativeOptimizationFailureMessage({error:payload});}
        else this.creativeOptimizationComparison = payload?.comparison ?? payload ?? null;
        this.creativeOptimizationSelectedCandidateId = null;
        this.creativeOptimizationReviewedCandidateId = null;
        this.creativeOptimizationConsent = false;
        this.creativeOptimizationBusy = false;
        this.changeDetector.markForCheck();
      },
      error: (response) => {
        this.creativeOptimizationBusy = false;
        this.creativeOptimizationComparison = null;
        this.creativeOptimizationSelectedCandidateId = null;
        this.creativeOptimizationReviewedCandidateId = null;
        this.creativeOptimizationConsent = false;
        this.creativeOptimizationError = this.creativeOptimizationFailureMessage(response);
        this.changeDetector.markForCheck();
      },
    });
  }
  creativeOptimizationFailureMessage(response: any): string {
    const failure=response?.error;
    if(failure?.category){
      const dispatched=failure.providerDispatched===true?'Provider dispatch: yes.':'Provider dispatch: no.';
      const returned=failure.providerResponseReturned===true?'Response received.':'Response not confirmed.';
      const retry=failure.retrySafe===true?'Explicit operator action required before retry/recovery.':'Retry blocked; review the saved attempt. No automatic retry.';
      return `${failure.category}: ${failure.detail || 'Optimization outcome requires review.'} ${dispatched} ${returned} Candidates saved: ${failure.candidatesSaved===true?'yes':'no'}. ${retry} Attempt: ${failure.attemptId || failure.roleRecordId || 'unavailable'}.`;
    }
    const detail = String(response?.error?.detail ?? response?.error?.message ?? '').trim();
    const normalized = detail.toLowerCase();
    if (normalized.includes('explicit server model configuration required')) {
      return 'Creative Optimization is unavailable because its server-side AI model is not configured. No candidates were generated. Configure the optimization role before retrying.';
    }
    if (normalized.includes('verified server price configuration')) {
      return 'Creative Optimization pricing is not configured on the server. No candidates were generated; ask an administrator to configure role pricing.';
    }
    if (normalized.includes('request exceeds approved cost ceiling')
        || normalized.includes('positive authorized cost ceiling')
        || normalized.includes('positive budget no greater than')) {
      return 'The request exceeds the configured cost ceiling. No candidates were generated; lower the scope or confirm an allowed budget.';
    }
    if (normalized.includes('actual provider cost')
        || normalized.includes('actual cost cannot be checked')) {
      return 'The provider response did not include verifiable usage within the authorized cost ceiling. No candidates were accepted; review the saved provider attempt before retrying.';
    }
    if (normalized.includes('prior optimization provider outcome is unresolved')
        || normalized.includes('optimization outcome is unresolved')) {
      return 'A previous provider outcome is unresolved. No automatic retry was made; review the saved attempt before requesting another generation.';
    }
    if (normalized.includes('invalid json')
        || normalized.includes('candidate')
        || normalized.includes('response must')
        || normalized.includes('essential event')) {
      return 'The provider response did not satisfy the candidate contract. No candidate was accepted and no prompt version was created; review the saved attempt before retrying.';
    }
    if (response?.status === 502
        || normalized.includes('workflow service unavailable')
        || normalized.includes('connection')
        || normalized.includes('timeout')) {
      return 'The configured AI provider could not be reached or its outcome is uncertain. No automatic retry was made; check provider connectivity and the saved attempt.';
    }
    if (normalized.includes('creative roles are disabled')) {
      return 'Creative Optimization is disabled on the server. No candidates were generated; enable the explicitly configured role before retrying.';
    }
    return detail
      ? `Creative Optimization failed. No candidates were generated. ${detail}`
      : 'Creative Optimization could not complete. No candidates were generated and no prompt version was created.';
  }
  approveSelectedCreativeOptimizationCandidate(): void {
    const candidate = this.creativeOptimizationSelectedCandidate;
    if (!candidate || !this.creativeOptimizationComparison || !this.creativeOptimizationApprovalEnabled) {
      this.creativeOptimizationError = 'Review a candidate and confirm its fidelity before approving a revision.';
      return;
    }
    this.creativeOptimizationBusy = true;
    this.creativeOptimizationError = '';
    const request = {
      rawText: String(candidate.prompt || ''),
      parentPromptVersionId: this.promptVersionId ? Number(this.promptVersionId) : null,
      creativeRoleRecordId: this.creativeOptimizationComparison.roleRecordId || null,
      candidateId: candidate.candidateId,
      optimizationComparisonId: this.creativeOptimizationComparison.recordId || null,
      operatorApproved: true,
    };
    this.http.post<any>(`/api/v1/intelligence/contents/${encodeURIComponent(String(this.contentId))}/prompt-versions`, request).subscribe({
      next: (response) => {
        const nextVersionId = response?.promptVersionId ?? response?.id ?? this.promptVersionId;
        this.creativeOptimizationBusy = false;
        this.creativeOptimizationSelectedCandidateId = null;
        this.creativeOptimizationReviewedCandidateId = null;
        this.creativeOptimizationComparison = null;
        this.creativeOptimizationConsent = false;
        this.changeDetector.markForCheck();
        if (this.preparationRouter) {
          void this.preparationRouter.navigate(['/quality/detail'], { queryParams: { contentId: this.contentId, promptVersionId: nextVersionId }, replaceUrl: true }).catch(() => undefined);
        }
      },
      error: (response) => {
        this.creativeOptimizationBusy = false;
        this.creativeOptimizationError = response?.error?.detail || 'The selected revision could not be approved. No prompt version was created.';
        this.changeDetector.markForCheck();
      },
    });
  }
  continueToQualityAnalysis(): void {
    if (this.review && this.isCurrent()) {
      this.selectStage(5);
      return;
    }
    this.runReview();
  }
  continueFromAnalysis(): void {
    if (!this.review || !this.isCurrent()) return;
    const recommendation = String(this.review?.planQuality?.recommendation || this.review?.recommendation || '').toUpperCase();
    const repairRequired = recommendation.includes('REPAIR') || String(this.review?.planQuality?.status || '').toUpperCase().includes('FAIL');
    if (repairRequired) { this.selectStage(6); return; }
    const firstFinding = this.resolutionItems()[0];
    if (firstFinding) { this.resolveFinding(firstFinding); return; }
    this.selectStage(7);
  }
  asList(value: unknown): string[] {
    if (Array.isArray(value)) return value.map(item => String(item)).filter(Boolean);
    const text = String(value ?? '').trim();
    return text ? [text] : ['UNKNOWN'];
  }
  sourcePlanEvidence: any = null;
  sourcePlanStatus = 'NOT_LOADED';
  private sourcePlanRun = '';
  private loadSourcePlan(){
    const id=this.review?.recordId;const sequence=this.restoreSequence;if(!id || this.sourcePlanRun===id)return;this.sourcePlanRun=id;this.sourcePlanStatus='LOADING';
    this.http.get<any>(`/api/v1/intelligence/workflow/records/${encodeURIComponent(id)}/source-plan`).subscribe({next:projection=>{if(sequence!==this.restoreSequence || this.review?.recordId!==id)return;
      const matched=projection?.historicalRunId===id && projection?.source?.sha256===this.review?.source?.sha256;this.sourcePlanEvidence=matched?projection:null;this.sourcePlanStatus=matched?'AVAILABLE':'UNKNOWN';this.changeDetector.markForCheck();},error:()=>{if(sequence===this.restoreSequence){this.sourcePlanStatus='UNKNOWN';this.changeDetector.markForCheck();}}});
  }
  selectAnalysisTab(tab: 'summary' | 'creative' | 'feasibility' | 'evidence') {
    this.activeAnalysisTab = tab;
    this.loadSourcePlan();
    this.persistUiLocation();
  }
  selectProductionTab(tab: 'overview' | 'creative' | 'execution' | 'references') {
    this.activeProductionTab = tab;
    if (tab === 'execution' || tab === 'creative') this.restoreProductionReviewDecisions();
    this.changeDetector.markForCheck();
    if (tab === 'references') this.loadCharacterReferenceOptions();
    this.persistUiLocation();
  }
  private persistUiLocation() {
    if (typeof localStorage === 'undefined' || !this.contentId || !this.promptVersionId) return;
    localStorage.setItem(`pompom-studio-location:${this.contentId}:${this.promptVersionId}`, JSON.stringify({ stage: this.activeStage, tab: this.activeProductionTab, analysisTab: this.activeAnalysisTab }));
  }
  private restoreUiLocation() {
    if (typeof localStorage === 'undefined' || !this.contentId || !this.promptVersionId) return;
    try {
      const saved = JSON.parse(localStorage.getItem(`pompom-studio-location:${this.contentId}:${this.promptVersionId}`) || '{}');
      if (Number.isInteger(saved.stage) && saved.stage >= 4 && saved.stage <= 8 && (saved.stage === 4 || this.review)) this.activeStage = saved.stage;
      const requestedStage = Number(new URL(window.location.href).searchParams.get('stage'));
      if (Number.isInteger(requestedStage) && requestedStage >= 4 && requestedStage <= 8 && (requestedStage === 4 || this.review)) this.activeStage = requestedStage;
      if (['overview', 'creative', 'execution', 'references'].includes(saved.tab)) this.activeProductionTab = saved.tab;
      if (['summary', 'creative', 'feasibility', 'evidence'].includes(saved.analysisTab)) this.activeAnalysisTab = saved.analysisTab;
      const requestedAnalysisTab=new URL(window.location.href).searchParams.get('analysisTab');
      if(requestedAnalysisTab&&['summary','creative','feasibility','evidence'].includes(requestedAnalysisTab))this.activeAnalysisTab=requestedAnalysisTab as typeof this.activeAnalysisTab;
      if(this.activeStage===7&&this.review)void this.preparationRouter?.navigateByUrl(this.renderPreparationLink());
      if(window.location.hash==='#findings-resolution')setTimeout(()=>document.getElementById('findings-resolution')?.scrollIntoView({block:'start'}),50);
    } catch { /* ignore corrupt UI-only state */ }
  }
  intentEditing = false; settingsEditing = false; referencesOpen = false; intentConfirmed = false; readinessCardShown = true;
  openSourceQuotes: Record<string, boolean> = {};
  readonly semanticRoles = ['SETUP', 'TRIGGER', 'CONSEQUENCE', 'ESCALATION', 'TRANSFORMATION', 'PAYOFF', 'OTHER'];
  eventDrafts: Record<string, { role?: string; note?: string; actor?: string; primaryObject?: string; environment?: string; action?: string; consequence?: string }> = {};
  conflictDrafts: Record<string, { decision?: string; modifiedSuggestion?: string }> = {};
  reviewDecisions: any[] = [];
  private decisionsLoadedFor = '';
  profile = 'FROZEN';
  contentProfile = 'AUTO';
  get profileProposal(){const text=(this.prompt||'').toLowerCase();if(/sticky note|paper note|note .*stick|stick.*note|turns? in the air|flips? in the air|multiply|multipli/.test(text))return {value:'ABSURD_PHYSICS',reason:'Source describes an object behaving against its expected physical relationship.',status:'SUGGESTED'};if(/lesson|explain|teach|learn|how to|facts?/.test(text))return {value:'EDUCATIONAL',reason:'Source contains explicit teaching language.',status:'SUGGESTED'};if(/discover|mystery|wonder|explore|finds? out/.test(text))return {value:'CURIOSITY_ADVENTURE',reason:'Source contains a discovery-oriented promise.',status:'SUGGESTED'};return {value:'UNKNOWN',reason:'The source does not support a confident profile proposal.',status:'UNCERTAIN'};}
  get evaluationProfile():string{return this.review?.boundRequest?.contentProfile || (this.prompt.match(/Content profile:\s*([A-Z_]+)/)?.[1]) || 'UNKNOWN';}
  get contentProfileLabel():string{if(this.contentProfile !== 'AUTO')return this.contentProfile.replaceAll('_',' ');return this.profileProposal.status==='SUGGESTED'?this.profileProposal.value.replaceAll('_',' '):'Profile uncertain';}
  get contentProfileHint():string{return this.contentProfile !== 'AUTO'?(this.confirmedSettingsSnapshot===this.settingsSnapshot()?'Explicit saved operator selection':'Unsaved selection · save settings to confirm'):this.profileProposal.status==='SUGGESTED'?'Suggested from approved source · confirmation required':'Review selection';}
  get profileMismatch(): boolean { const text=(this.prompt||'').toLowerCase(); return this.contentProfile === 'ABSURD_PHYSICS' && /discover|shiny box|ribbon|rainbow|finds?/.test(text) && !/impossible|defies|multipl|turns? in the air|physics/.test(text); }
  get generatorProposal(){const configured=this.generator !== 'AUTO'?this.generator:'SEEDANCE_2_0_MINI';return {value:configured,reason:this.generator !== 'AUTO'?'Saved or selected production choice':'Default production preference for a 15-second concept.',capability:this.capabilityStatus};}
  get generatorLabel():string{return ({SEEDANCE_2_0_MINI:'Seedance 2.0 Mini',SEEDANCE_2_0:'Seedance 2.0',SEEDANCE_2_5:'Seedance 2.5'} as Record<string,string>)[this.generatorProposal.value] || this.generatorProposal.value.replaceAll('_',' ');}
  get generatorHint():string{return `${this.generatorProposal.reason} · Capability: ${this.generatorProposal.capability}`;}
  get openingProposal(){const first=this.timedRanges[0]?.quote.toLowerCase()||'';const second=this.timedRanges[1]?.quote.toLowerCase()||'';if(/already|clearly visible|visible from the first|holds? a sticky|stands? .* holding/.test(first)&&/turns?|flips?|sticks?|attaches?/.test(second))return {value:'INSTANT_IMPOSSIBLE',reason:'The opening establishes the ordinary setup, then exposes the unusual physical consequence immediately.',status:'SUGGESTED'};if(/problem|tries?|fails?|cannot|stuck/.test(first))return {value:'IMMEDIATE_PROBLEM',reason:'The first source event presents an active problem.',status:'SUGGESTED'};if(/discover|mystery|wonder|question/.test((this.prompt||'').slice(0,500).toLowerCase()))return {value:'CURIOSITY_DISCOVERY',reason:'The source opens with a discovery promise.',status:'SUGGESTED'};return {value:'UNKNOWN',reason:'Opening evidence is insufficient for a supported strategy proposal.',status:'UNCERTAIN'};}
  get openingStrategyLabel():string{return this.openingStrategy !== 'AUTO'?this.openingStrategy.replaceAll('_',' '):this.openingProposal.status==='SUGGESTED'?'Suggested: '+this.openingProposal.value.replaceAll('_',' '):'Opening strategy uncertain';}
  get openingStrategyHint():string{return this.openingStrategy !== 'AUTO'?'Selected strategy · confirm by saving settings':this.openingProposal.status==='SUGGESTED'?'Needs confirmation · Accept or change':this.openingProposal.reason;}
  get characterLabel():string{return this.referenceCharacter || (this.references[0]?.character || 'Unknown');}
  get approvedCharacterReference():boolean{return this.references.some(ref=>ref.kind!=='FIRST_FRAME'&&ref.status==='APPROVED'&&!!ref.sha256&&!!(ref.id||ref.assetId));}
  get firstFrameStatus():string{return this.firstFramePath || this.firstFrameUrl ? 'Needs validation' : 'Not yet available';}
  get plannedOpeningAssessment():string { const opening=this.timedRanges[0]?.quote || ''; if(!opening)return 'UNKNOWN — no timed opening source'; if(/already stuck|already attached|visible from the first frame/i.test(opening))return 'Source describes a note on Mimi from the opening; the impossible relationship is not visually verified.'; return 'Source-based plan only; no generated frame has been inspected.'; }
  get analysisReady(){return !!this.contentId && !!this.promptVersionId && !!this.prompt.trim();}
  get intentAvailable(){return !!(this.protectedIntent.trim() || this.extractedIntent.trim());}
  get evidenceIncomplete(){return !this.approvedCharacterReference || !this.review?.productionEvidence?.videoPlanIR?.beats?.length;}
  analysisReportRows(report: any[]): any[] {
    const rows = (report || []).map(row => ({ ...row, text: this.cleanAnalysisText(row?.text) }));
    const label = (row: any) => String(row?.label || '').toLowerCase().replace(/[^a-z]/g, '');
    const mechanism = rows.find(row => label(row).includes('viewingmechanism'));
    const opening = rows.find(row => label(row) === 'opening');
    if (mechanism && opening && mechanism.text !== 'UNKNOWN' && mechanism.text === opening.text) {
      opening.text = 'Same source observation as the viewing mechanism; no separate opening assessment was recorded.';
    }
    for (const row of rows) {
      if (label(row).includes('progression') && /insufficient evidence/i.test(row.text) && this.timedRanges.length) {
        row.text = `${row.text}. ${this.timedRanges.length} timed source range(s) were extracted, but semantic progression remains unconfirmed.`;
      }
    }
    return rows;
  }
  cleanAnalysisText(value: unknown): string { const text=String(value ?? 'UNKNOWN'); return text.replace(/\s*(?:AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\s*:?[\s\S]*$/i, '').replace(/Planlanan final\s*:/i, 'Planned ending:').replace(/:\s*:/g, ':').replace(/^\s*:\s*/, '').trim() || 'UNKNOWN'; }
  private readableEvidenceValue(value:any):string {
    if(value==null)return 'UNKNOWN';
    if(Array.isArray(value))return value.map(v=>this.readableEvidenceValue(v)).join(', ');
    if(typeof value==='object')return Object.entries(value).map(([key,v])=>`${key}: ${this.readableEvidenceValue(v)}`).join('; ');
    return String(value).replaceAll('_',' ');
  }
  readableCoreMechanic(value:any):string {
    if(!value || typeof value!=='object')return this.readableEvidenceValue(value);
    return ['physicalRule','abnormalProperty','trigger','primaryObject','persistence','releaseCondition','causeEffect','recurrence'].filter(key=>value[key]!=null).map(key=>`${key}: ${this.readableEvidenceValue(value[key])}`).join('; ') || 'UNKNOWN — no mechanic fields recorded';
  }
  readableGoalEvidence(value:any):string {
    if(!value || typeof value!=='object')return this.readableEvidenceValue(value);
    return ['description','goalType','source','goalExplicitness','obstruction','targetObject','intendedEffect'].filter(key=>value[key]!=null).map(key=>`${key}: ${this.readableEvidenceValue(value[key])}`).join('; ') || 'UNKNOWN — no goal fields recorded';
  }
  technicalDiagnostic():string {
    const claims=(this.review?.productionEvidence?.claims || []).filter((c:any)=>c.state==='CONTRADICTORY'||c.state==='INVALID');
    const plan=this.review?.boundRequest?.structuredPlan;
    const envelope=plan?.events && !plan?.beats ? 'Saved request supplied deterministic events, while the source-bound tracked-plan validator expected beats. This is an input-contract mismatch.' : '';
    return [envelope,...claims.map((c:any)=>`${c.field}: ${c.reason || 'cause not recorded'}`),'No runtime exception or conflicting source spans were saved; independent contradiction evidence is UNKNOWN.'].filter(Boolean).join(' ');
  }
  authorizationReasonText(reason:any):string {
    return /technical_failure|parser_timeout|required_service_failure/i.test(reason?.code || '') ? 'Saved assessment technical failure — '+this.technicalDiagnostic() : String(reason?.message || reason?.code || 'UNKNOWN');
  }
  get semanticClassificationStatus(): string { const evidence=this.review?.productionEvidence || {}; const metadata=evidence.videoPlanIR?.metadata || {}; return String(metadata.semanticClassificationStatus || evidence.semanticStatus || 'PENDING'); }
  get semanticEvidenceReady(): boolean { const status=this.semanticClassificationStatus.toUpperCase(); return ['COMPLETED','CONFIRMED','OBSERVED'].includes(status) && !this.timedRangeIssues.length; }
  get executionEvidenceStatus(): string { const reviewed=this.sourceEvents.filter(event=>event.savedRole).length;return `${this.sourceEvents.length} current source interval(s) · ${reviewed} operator-reviewed · independent semantic fidelity UNKNOWN`; }
  get referenceStatus(): string { return this.approvedCharacterReference ? 'Approved character image bound with stable identity and hash' : this.references.length ? 'Reference candidate exists, but approval/version/hash is not verified' : 'Missing approved character reference'; }
  loadCharacterReferenceOptions(){const sequence=this.restoreSequence;if(!this.characterId)return;this.http.get<any[]>(`/api/v1/characters/${this.characterId}/references`).subscribe({next:rows=>{if(sequence!==this.restoreSequence)return;this.approvedCharacterReferences=(rows||[]).filter(row=>row.status==='APPROVED'&&row.sha256&&row.id);this.http.get<any>('/api/v1/intelligence/workflow/production-review/reference-binding',{params:{contentId:this.contentId,promptVersionId:this.promptVersionId}}).subscribe({next:binding=>{if(sequence!==this.restoreSequence)return;const found=this.approvedCharacterReferences.find(row=>row.id===binding.referenceId&&row.sha256===binding.sha256);if(found){this.selectedReferenceId=found.id;this.selectedReferencePreview=found;this.references=[{character:this.referenceCharacter,kind:'CHARACTER_REFERENCE',relativePath:found.relativePath,status:'APPROVED',sha256:found.sha256,id:found.id,assetId:found.id,version:found.version}];}else if(binding.referenceId){this.references=[];this.selectedReferencePreview=null;}this.changeDetector.markForCheck();},error:()=>{}});this.changeDetector.markForCheck();},error:()=>{this.approvedCharacterReferences=[];}});}
  bindCharacterReference(){const ref=this.approvedCharacterReferences.find(row=>row.id===this.selectedReferenceId);if(!ref||!this.characterId)return;this.busy=true;this.http.post<any>('/api/v1/intelligence/workflow/production-review/reference-binding',{contentId:this.contentId,promptVersionId:this.promptVersionId,characterId:this.characterId,referenceId:ref.id}).subscribe({next:binding=>{this.references=[{character:this.referenceCharacter,kind:'CHARACTER_REFERENCE',relativePath:binding.relativePath,status:'APPROVED',sha256:binding.sha256,id:binding.referenceId,assetId:binding.referenceId,version:binding.version}];this.selectedReferencePreview=ref;this.busy=false;this.changeDetector.markForCheck();},error:e=>this.fail(e)});}

  get intentObject(){const text=(this.prompt||'').toLowerCase();if(/sticky note|sticky notes/.test(text))return /toy cabinet/.test(text)?'Sticky notes and the toy cabinet (saved prompt)':'Sticky notes (saved prompt)';if(/\b(note|cabinet|box|ball|door)\b/.test(text))return (text.match(/\b(note|cabinet|box|ball|door)\b/)||['Unresolved object'])[0];return 'Unresolved';}
  get intentMechanism(){const doubling=this.sourceEvents.find(event=>/each pull doubles|every.*pull.*doubl/i.test(event.action));return doubling ? doubling.action : 'UNKNOWN — inspect the saved source events; no independent mechanism interpretation is confirmed.';}
  get intentProgression(){const event=this.sourceEvents.find(event=>/doubl|multiply|multipli/i.test(event.action));return event ? event.action : 'UNKNOWN — inspect the timed source actions.';}
  get intentEnding(){const event=this.sourceEvents.at(-1);return event ? event.action : 'UNKNOWN — no final timed source event is available.';}
  get intentAmbiguity(){return this.creativeConflicts.length ? this.creativeConflicts[0].explanation : 'No causal conflict identified by local extraction; independent semantic verification remains UNKNOWN.';}
  legacyProductionPlan: any = null;
  legacyEvidenceError = '';
  loadLegacySpecification(){
    const id=this.creativeProvenance?.creativeRoleRecordId;const sequence=this.restoreSequence;if(!id)return;
    this.http.get<any>(`/api/v1/intelligence/workflow/records/${encodeURIComponent(id)}`).subscribe({next:record=>{if(sequence!==this.restoreSequence||id!==this.creativeProvenance?.creativeRoleRecordId)return;this.legacyProductionPlan=record.result?.productionPlan||null;this.legacyEvidenceError=this.legacyProductionPlan?'':'Original structured specification is unavailable (UNKNOWN).';this.changeDetector.markForCheck();},error:()=>{this.legacyEvidenceError='Original structured specification could not be read (UNKNOWN).';this.changeDetector.markForCheck();}});
  }
  providerCapabilities: any = null;
  get capabilityStatus(): string {
    const model=this.providerCapabilities?.models?.[this.generator];
    const props=model?.modes?.image2video?.properties;
    if(!props || !model?.provenance?.schemaSha256)return 'UNKNOWN — local capability evidence unavailable';
    const duration=this.desiredDuration;
    const supported=!!duration && duration >= props.duration?.minimum && duration <= props.duration?.maximum && props.aspectRatio?.enum?.includes(this.aspectRatio);
    return `${supported ? 'Supported by local schema snapshot' : 'UNKNOWN or unsupported settings'} · ${model.version} · image2video; start frame required in Step 7. Technical support does not verify creative producibility or successful generation.`;
  }
  private loadProviderCapabilities(){this.http.get<any>('/api/v1/intelligence/workflow/provider-capabilities').subscribe({next:value=>{this.providerCapabilities=value;this.changeDetector.markForCheck();},error:()=>{this.providerCapabilities=null;}});}
  private confirmedSettingsSnapshot = '';
  private settingsSnapshot(){return JSON.stringify({contentProfile:this.contentProfile,openingStrategy:this.openingStrategy,generator:this.generator,desiredDuration:this.desiredDuration,aspectRatio:this.aspectRatio,qualityJustification:this.qualityJustification});}
  settingsSavedAt: string | null = null;
  applySettings(){ const sequence=this.restoreSequence;if(!this.contentId || !this.promptVersionId) return; this.busy=true; this.error=''; this.http.post<any>('/api/v1/intelligence/workflow/production-settings',{contentId:this.contentId,promptVersionId:this.promptVersionId,contentProfile:this.contentProfile,openingStrategy:this.openingStrategy,generator:this.generator,desiredDuration:this.desiredDuration,aspectRatio:this.aspectRatio,qualityJustification:this.qualityJustification}).subscribe({next:r=>{if(sequence!==this.restoreSequence)return;this.settingsSavedAt=r.savedAt||new Date().toISOString();this.savedDuration=this.desiredDuration;this.savedAspectRatio=this.aspectRatio;this.confirmedSettingsSnapshot=this.settingsSnapshot();this.settingsEditing=false;this.busy=false;this.changeDetector.markForCheck();},error:e=>this.fail(e)}); }
  private restorePersistedSettings(sequence:number){ if(!this.contentId||!this.promptVersionId)return; this.http.get<any>('/api/v1/intelligence/workflow/production-settings',{params:{contentId:this.contentId,promptVersionId:this.promptVersionId}}).subscribe({next:s=>{if(sequence!==this.restoreSequence)return; this.contentProfile=s.contentProfile??this.contentProfile;this.openingStrategy=s.openingStrategy??this.openingStrategy;this.generator=s.generator??this.generator;this.desiredDuration=s.desiredDuration??this.desiredDuration;this.aspectRatio=s.aspectRatio??this.aspectRatio;this.savedDuration=this.desiredDuration;this.savedAspectRatio=this.aspectRatio;this.settingsSavedAt=s.savedAt||null;this.confirmedSettingsSnapshot=s.savedAt?this.settingsSnapshot():'';if(s.startFrame?.id){this.firstFramePath=s.startFrame.id;this.firstFrameUrl=s.startFrame.url||'';}this.changeDetector.markForCheck();},error:()=>{this.http.get<any>('/api/v1/intelligence/workflow/studio-sessions/by-prompt',{params:{contentId:this.contentId,promptVersionId:this.promptVersionId}}).subscribe({next:s=>{if(sequence!==this.restoreSequence)return; this.contentProfile=s.profile??this.contentProfile;this.generator=s.targetGenerator??this.generator;this.desiredDuration=s.duration??this.desiredDuration;this.aspectRatio=s.aspectRatio??this.aspectRatio;this.savedDuration=this.desiredDuration;this.savedAspectRatio=this.aspectRatio;this.savedAspectRatioProvenance = 'STUDIO_SESSION';this.settingsSavedAt=s.updatedAt||null;this.changeDetector.markForCheck();},error:()=>{}});}}); }
  get settingsStatus(){if(this.durationConflict||this.aspectConflict)return 'CONFLICT — saved and prompt values differ';const missing:string[]=[];if(!this.desiredDuration)missing.push('duration');if(!this.aspectRatio)missing.push('aspect ratio');if(this.contentProfile==='AUTO')missing.push('content profile');if(this.generator==='AUTO')missing.push('generator');return missing.length?`Needs confirmation: ${missing.join(', ')}`:this.confirmedSettingsSnapshot===this.settingsSnapshot()?'CONFIRMED':'Needs confirmation: save the selected settings';}
  get sourceEvents(){return this.timedRanges.map((range,index)=>{const quote=range.quote.replace(/^\d{1,2}(?::\d{2})?\s*(?:-|–|—|to)\s*\d{1,2}(?::\d{2})?\s*(?:s|sec|secs|seconds)?\s*:?\s*/i,'').trim();const lower=quote.toLowerCase();const id=`source-event-${index+1}`;const hasNotes=/sticky notes?|notes?/.test(lower);const centralNotes=/\bsticky notes?\b/i.test(this.prompt);const actorMatch=quote.match(/\b(Mimi|Kiko|Luca)\b/i);const action=quote.replace(/^(?:[A-Z][^.!?]{0,30}:\s*)/,'').trim();let proposedRole='PENDING',roleEvidence='insufficient source evidence';if(index===0&&/stand|hold|already|opening/.test(lower)){proposedRole='SETUP';roleEvidence='opening context explicitly described';}if(/instead|unexpected|turns? in the air|flips? in the air/.test(lower)){proposedRole='TRIGGER';roleEvidence='unexpected event is stated in source';}if(/double|doubl|multiply|multipli|again|another/.test(lower)){proposedRole='ESCALATION';roleEvidence='repetition or increase is explicitly stated';}if(index===this.timedRanges.length-1 && /completely cover|covers? .*only .*eyes|leaving only .*eyes/.test(lower)){proposedRole='PAYOFF';roleEvidence='explicit final visual state; narrative value remains an interpretation';}const consequence=action.includes('->')?action.split('->').slice(1).join('->').trim():'UNKNOWN — no explicit arrow consequence in this source interval; inspect the action text.';const saved=this.eventDecision(id);return {id,start:range.start,end:range.end,actor:actorMatch?.[1]||`${this.characterLabel} (source-associated; action attribution uncertain)`,object:(lower.match(/\b(shiny box|box|ribbons?|rainbow arch|sticky notes?|notes?|cabinet)\b/)||[])[0]||'Unresolved',primaryObject:centralNotes?'Sticky notes':(hasNotes?'Notes':'Unresolved'),secondaryObjects:(lower.match(/\b(paw|paws|ear|ears|face|arms?|body|eyes?)\b/g)||[]).join(', ')||'None stated',environment:/toy cabinet/.test(lower)?'Toy cabinet (stated in source)':/cabinet|cupboard/.test(lower)?'Cabinet / cupboard (stated in source)':/mirror/.test(lower)?'Mirror (stated in source)':'Not stated in this range',obstacle:/doubl|multiply|multipli/.test(lower)?'Repeated increase in notes (source interpretation)':/instead/.test(lower)?'Attachment differs from the intended target (source interpretation)':/follow/.test(lower)?'Pursuit stated in this source interval':'Not explicit',action:action||'No action text extracted',consequence,sourceQuote:range.quote,evidence:'SOURCE_EVENT_CANDIDATE',semanticStatus:'PENDING',proposedRole:proposedRole,roleEvidence:roleEvidence,savedRole:saved?.decision||'',savedNote:saved?.note||'',operatorInterpretation:saved?{semanticRole:saved.decision,actor:saved.actor,primaryObject:saved.primaryObject,environment:saved.environment,action:saved.action,consequence:saved.consequence,note:saved.note,provenance:saved.provenance,sourceFingerprint:saved.sourceFingerprint}:null};});}
  get creativeConflicts(){if(!/multiply|multipli/i.test(this.prompt)||!/(follow|follows|chase|fly back)/i.test(this.prompt))return [];const sentences=(this.prompt||'').split(/(?<=[.!?])\s+/).filter(sentence=>/multiply|multipli|fly back|follow|follows|cover|covered/i.test(sentence));const id='notes-multiplication-and-pursuit';const saved=this.eventDecision(id,'CREATIVE_CONFLICT');return [{id,title:'Multiplication and pursuit relationship',status:'UNRESOLVED CAUSAL RELATIONSHIP — not a confirmed contradiction',explanation:'The source states both that notes multiply/return and that they follow Mimi. It does not say whether pursuit is caused by the multiplying notes or is a separate effect; both readings may be intentional.',sourceEvidence:sentences.join('\n'),suggestion:'Optional minimal clarification: state whether the notes that multiply are the same notes that follow and reattach to Mimi. This preserves the approved events without imposing a single-rule requirement.',savedDecision:saved?.decision||'',savedSuggestion:saved?.modifiedSuggestion||''}];}
  private eventDecision(id:string,type='EVENT_CLASSIFICATION'){return [...this.reviewDecisions].reverse().find((row:any)=>row.decisionType===type&&row.decisionId===id);}
  private restoreProductionReviewDecisions() {
    const sequence = this.restoreSequence;
    const key = `${this.contentId}/${this.promptVersionId}`;
    if (!this.contentId || !this.promptVersionId || this.decisionsLoadedFor === key) return;
    this.decisionsLoadedFor = key;
    this.decisionReadError = '';
    this.http.get<any>('/api/v1/intelligence/workflow/production-review/decisions', {
      params: { contentId: this.contentId, promptVersionId: this.promptVersionId },
    }).subscribe({
      next: response => {
        if (sequence !== this.restoreSequence) return;
        this.reviewDecisions = response.decisions || [];
        const intent = this.eventDecision('creative-intent', 'CREATIVE_INTENT');
        this.intentConfirmed = !!intent
          && (!this.creativeProvenance || intent.storyRevisionId === (this.creativeProvenance?.storyRevisionId || null));
        if (intent) this.protectedIntent = intent.protectedIntent || '';
        for (const row of this.reviewDecisions) {
          if (row.decisionType === 'EVENT_CLASSIFICATION') this.eventDrafts[row.decisionId] = {
            role: row.decision, note: row.note || '', actor: row.actor || '',
            primaryObject: row.primaryObject || '', environment: row.environment || '',
            action: row.action || '', consequence: row.consequence || '',
          };
          if (row.decisionType === 'CREATIVE_CONFLICT') this.conflictDrafts[row.decisionId] = {
            decision: row.decision, modifiedSuggestion: row.modifiedSuggestion || '',
          };
        }
        this.changeDetector.markForCheck();
      },
      error: () => {
        if (sequence !== this.restoreSequence) return;
        this.decisionsLoadedFor = '';
        this.decisionReadError = 'Saved Step 4/6 operator decisions could not be read. Refresh before relying on a saved confirmation.';
        this.changeDetector.markForCheck();
      },
    });
  }
  setEventDraft(id:string,field:'role'|'note'|'actor'|'primaryObject'|'environment'|'action'|'consequence',value:string){this.eventDrafts={...this.eventDrafts,[id]:{...this.eventDrafts[id],[field]:value}};this.changeDetector.markForCheck();}
  setConflictDraft(id:string,field:'decision'|'modifiedSuggestion',value:string){this.conflictDrafts={...this.conflictDrafts,[id]:{...this.conflictDrafts[id],[field]:value}};}
  private saveDecision(payload:any){const sequence=this.restoreSequence;this.busy=true;this.error='';this.http.post<any>('/api/v1/intelligence/workflow/production-review/decisions',{contentId:this.contentId,promptVersionId:this.promptVersionId,...payload}).subscribe({next:r=>{if(sequence!==this.restoreSequence)return;this.reviewDecisions=[...this.reviewDecisions.filter(row=>row.decisionType!==r.decisionType||row.decisionId!==r.decisionId),r];if(r.decisionType==='CREATIVE_INTENT')this.intentConfirmed=true;this.busy=false;this.changeDetector.markForCheck();},error:e=>this.fail(e)});}
  saveEventClassification(event:any){const draft=this.eventDrafts[event.id];if(!draft?.role)return;this.saveDecision({decisionType:'EVENT_CLASSIFICATION',decisionId:event.id,decision:draft.role,note:draft.note||'',actor:draft.actor||event.actor,primaryObject:draft.primaryObject||event.primaryObject,environment:draft.environment||event.environment,action:draft.action||event.action,consequence:draft.consequence||event.consequence,sourceQuote:event.sourceQuote,sourceFingerprint:this.review?.boundRequest?.promptSha256||this.review?.bindingHash||this.promptFingerprint()});}
  saveConflictDecision(issue:any){const draft=this.conflictDrafts[issue.id];if(!draft?.decision)return;this.saveDecision({decisionType:'CREATIVE_CONFLICT',decisionId:issue.id,decision:draft.decision,modifiedSuggestion:draft.modifiedSuggestion||'',sourceEvidence:issue.sourceEvidence,suggestion:issue.suggestion,sourceFingerprint:this.review?.boundRequest?.promptSha256||this.review?.bindingHash||this.promptFingerprint()});}
  private promptFingerprint(){let hash=2166136261;for(const char of this.prompt)hash=Math.imul(hash^char.charCodeAt(0),16777619);return (hash>>>0).toString(16).padStart(8,'0');}

  isSourceQuoteOpen(id:string){return !!this.openSourceQuotes[id];}
  toggleSourceQuote(id:string){this.openSourceQuotes={...this.openSourceQuotes,[id]:!this.openSourceQuotes[id]};}
  acceptProfileSuggestion(){if(this.profileProposal.status==='SUGGESTED')this.contentProfile=this.profileProposal.value;}
  acceptOpeningSuggestion(){if(this.openingProposal.status==='SUGGESTED'){this.openingStrategy=this.openingProposal.value;if(this.contentId&&this.promptVersionId)this.applySettings();}}
  acceptGeneratorSuggestion(){this.generator=this.generatorProposal.value;}
  get durationConflict(){return this.savedDuration != null && this.promptDuration != null && this.savedDuration !== this.promptDuration;}
  get aspectRatioProvenanceLabel(): string { return this.savedAspectRatioProvenance === 'OPERATOR_PRODUCTION_SETTINGS' ? 'Explicit operator setting' : this.savedAspectRatioProvenance === 'STUDIO_SESSION' ? 'Studio session setting' : this.savedAspectRatioProvenance === 'CANONICAL_REVIEW_BINDING' ? 'Recorded in review binding; override history unavailable' : 'Needs confirmation'; }
  get aspectConflict(){return !!this.savedAspectRatio && !!this.promptAspectRatio && this.savedAspectRatio !== this.promptAspectRatio;}
  get timedRangeIssues(): string[] { const issues:string[]=[]; const max=this.promptDuration; const ranges=this.timedRangesRaw; for(const range of ranges){ if(max!=null&&range.end>max) issues.push(`${range.start}–${range.end}s exceeds the declared ${max}s duration.`); } for(let i=1;i<ranges.length;i++){ if(ranges[i].start<ranges[i-1].end) issues.push(`${ranges[i].start}–${ranges[i].end}s overlaps ${ranges[i-1].start}–${ranges[i-1].end}s.`); } return Array.from(new Set(issues)); }
  private get timedRangesRaw():Array<{start:number;end:number;quote:string;quoteStart:number;quoteEnd:number}>{const text=this.prompt||'';const ranges:Array<{start:number;end:number;quote:string;quoteStart:number;quoteEnd:number}>=[];const add=(start:number,end:number,index:number,matchEnd:number)=>{if(end<=start)return;const rest=text.slice(matchEnd);const nextTimed=rest.search(/(?:\\n|\n)\s*(?:(?:\d{1,2}:\d{2})\s*(?:-|–|—|to)\s*(?:\d{1,2}:\d{2})|(?:\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(?:\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?\s*:)/i);const nextSection=rest.search(/(?:\\n|\n)\s*(?:AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT|REFERENCES|CHARACTER|VISUAL STYLE)\s*:?(?:\s*\n|\s*$)/i);const offsets=[text.length];if(nextTimed>=0)offsets.push(matchEnd+nextTimed);if(nextSection>=0)offsets.push(matchEnd+nextSection);const quoteEnd=Math.min(...offsets);if(!ranges.some(range=>range.start===start&&range.end===end))ranges.push({start,end,quote:text.slice(index,quoteEnd).trim(),quoteStart:index,quoteEnd});};let match:RegExpExecArray|null;const clock=/((?:\d{1,2}):(?:\d{2}))\s*(?:-|–|—|to)\s*((?:\d{1,2}):(?:\d{2}))\s*:?[ \t]*/gi;while((match=clock.exec(text))){const parse=(value:string)=>{const parts=value.split(':').map(Number);return parts[0]*60+parts[1];};add(parse(match[1]),parse(match[2]),match.index,clock.lastIndex);}const seconds=/(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?\s*:/gi;while((match=seconds.exec(text))){add(Number(match[1]),Number(match[2]),match.index,seconds.lastIndex);}return ranges.sort((a,b)=>a.start-b.start||a.end-b.end);}
  get timedRanges(){ let previousEnd=-Infinity; return this.timedRangesRaw.filter(range=>{ const withinDuration=this.promptDuration == null || range.end <= this.promptDuration; const chronological=range.start >= previousEnd; if(withinDuration && chronological) previousEnd=range.end; return withinDuration && chronological; }); }
  get extractedIntent():string{const text=this.prompt||'';const heading=/(TITLE\s*\/\s*FORMAT|VISUAL STYLE|CHARACTER\s*\/\s*CONTINUITY|TIMED SHOT PLAN|AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\s*:?[ \t]*/gi;const matches=Array.from(text.matchAll(heading));const useful:string[]=[];for(let index=0;index<matches.length;index++){const label=matches[index][1].toUpperCase();if(!/CHARACTER|TIMED SHOT PLAN/.test(label))continue;const start=(matches[index].index||0)+matches[index][0].length;const end=index+1<matches.length?(matches[index+1].index||text.length):text.length;const body=text.slice(start,end).trim();if(body)useful.push(body);}if(useful.length)return useful.join(' ').slice(0,520);return text.split(/\r?\n/).map(line=>line.trim()).filter(Boolean).filter(line=>!/(TITLE|FORMAT|VISUAL STYLE|AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\s*:?[ \t]*/i.test(line)).join(' ').slice(0,520);}
  confirmIntent(){if(!this.intentAvailable||this.busy||!this.contentId||!this.promptVersionId)return;this.saveDecision({decisionType:'CREATIVE_INTENT',decisionId:'creative-intent',decision:'CONFIRMED',sourceQuote:this.prompt,protectedIntent:this.protectedIntent.trim(),reviewedMechanism:this.intentMechanism,reviewedEnding:this.intentEnding,storyRevisionId:this.creativeProvenance?.storyRevisionId||null});}
  trackSourceEvent(_index:number,event:any){return event.id;}


  openingStrategy = 'AUTO';
  generator = 'AUTO';
  desiredDuration: number | null = null;
  savedDuration: number | null = null;
  promptDuration: number | null = null;
  qualityJustification = '';
  aspectRatio = '';
  savedAspectRatio = '';
  savedAspectRatioProvenance = '';
  promptAspectRatio = '';
  structuredPlanText = '';
  intentRequirementsText = '[]';
  creativeEvidenceText = '[]';
  intentChangeReason = '';
  qaDefectsText = '[]';
  qaRepairText = '{}';
  qaStart = 0;
  qaEnd: number | null = null;
  qaExperience: Record<string, string> = {};
  qaDescriptions: Record<string, string> = {};
  qaAspects = [
    {
      key: 'coreEventReadability',
      label: 'Core event readability',
      values: ['ADEQUATE', 'UNREADABLE'],
    },
    { key: 'identity', label: 'Identity', values: ['RECOGNIZABLE', 'UNRECOGNIZABLE'] },
    {
      key: 'safety',
      label: 'Content safety for children',
      values: ['APPROPRIATE', 'UNSAFE'],
    },
    { key: 'coherence', label: 'Overall comprehensibility', values: ['ADEQUATE', 'DESTROYED'] },
    {
      key: 'progression',
      label: 'Viewing experience progression',
      values: ['DEVELOPING', 'PURPOSEFUL_REPETITION', 'WEAK'],
    },
    {
      key: 'opening',
      label: 'Actual opening',
      values: [
        'READABLE_EARLY_DEVELOPMENT',
        'READABLE_PROMISE',
        'UNREADABLE',
        'EXCESSIVELY_DELAYED',
      ],
    },
    {
      key: 'ending',
      label: 'Actual ending',
      values: ['DELIVERS_PROMISE', 'PURPOSEFUL_UNRESOLVED', 'ARBITRARY_TRUNCATION', 'WEAK'],
    },
  ];
  plannedEditedDuration: number | null = null;
  viewerQuestion = '';
  evidenceCoverage(evidence: any): string {
    const total = Array.from(this.prompt).length;
    if (!total) return 'UNKNOWN';
    const intervals: number[][] = (evidence?.claims || []).map((claim: any) => claim.span)
      .filter((span: any) => Array.isArray(span) && span.length === 2 && Number.isInteger(span[0]) && Number.isInteger(span[1]) && span[0] >= 0 && span[1] > span[0] && span[1] <= total)
      .sort((a: number[], b: number[]) => a[0] - b[0]);
    let count = 0, end = 0;
    for (const span of intervals) { count += Math.max(0, span[1] - Math.max(end, span[0])); end = Math.max(end, span[1]); }
    return `${count}/${total} Unicode characters (${Math.round(100 * count / total)}%)`;
  }

  protectedIntent = '';
  firstFramePath = '';
  firstFrameUrl = '';
  referenceCharacter = '';
  characterResolvedFromCatalog = false;
  characterId = '';
  approvedCharacterReferences: any[] = [];
  selectedReferenceId = '';
  selectedReferencePreview: any = null;
  referencePath = '';
  references: Array<{ character: string; relativePath: string; kind: string; status?: string; sha256?: string; id?: string; assetId?: string; version?: string }> = [];
  review: any = null;
  busy = false;
  analysisJustCompleted = false;
  error = '';
  private reviewedInputs = '';
  patchOriginal = '';
  patchReplacement = '';
  qaPath = '';
  qaStates: Record<string, string> = {};
  qaStarts: Record<string, number> = {};
  qaEnds: Record<string, number> = {};
  clipReviewed = false;
  stillsReviewed = false;
  qa: any = null;
  platform = 'INSTAGRAM';
  platformContentId = '';
  variantId = '';
  associationReason = '';
  association: any = null;
  measurementSource = '';
  horizon = 'UNKNOWN';
  measuredAt = '';
  videoDuration: number | null = null;
  reach: number | null = null;
  views: number | null = null;
  watchSeconds: number | null = null;
  paidReach: number | null = null;
  paidWatchShare: number | null = null;
  measurement: any = null;
  cohort: any = null;
  criticProvider = 'deepseek';
  criticModel = '';
  opinion: any = null;
  nearOrganicThreshold = 0.05;
  learningReason = '';
  lessonModelVersion = '';
  retrievedLessons: any[] = [];
  retrieveLessons() {
    this.http.get<any[]>('/api/v1/intelligence/workflow/learning/retrieve', { params: { contentProfile: this.contentProfile, modelVersion: this.lessonModelVersion, duration: this.desiredDuration || 0, generator:this.generator, settings:JSON.stringify(this.options().settings) } }).subscribe({ next: lessons => { this.retrievedLessons = lessons; this.changeDetector.markForCheck(); }, error: e => this.fail(e) });
  }
  lessonHypothesis = '';
  lessonScope = 'ACTUAL_EXECUTION';
  counterexamples = '';
  lesson: any = null;
  encode = encodeURIComponent;
  regenerationQaId = '';
  regenerationParentVideoId = '';
  regenerationParentVariantId = '';
  regenerationReason = '';
  regenerationHandoff: any = null;
  createRegenerationHandoff() {
    if (!this.isCurrent() || !this.regenerationReason.trim()) return;
    this.http.post<any>('/api/v1/intelligence/workflow/regeneration-handoff', { qaRecordId: this.regenerationQaId || this.qa?.recordId, reviewId: this.review.recordId, parentVideoId: this.regenerationParentVideoId || this.qa?.videoId, parentVariantId: this.regenerationParentVariantId || null, reason: this.regenerationReason.trim() }).subscribe({ next: handoff => { this.regenerationHandoff = handoff; this.changeDetector.markForCheck(); }, error: e => this.fail(e) });
  }
  regenerationLink() {
    return '/render-preparation?' + new URLSearchParams({ contentId: String(this.regenerationHandoff.contentId), promptVersionId: String(this.regenerationHandoff.promptVersionId), workflowReviewId: this.regenerationHandoff.reviewId, regenerationHandoffId: this.regenerationHandoff.recordId }).toString();
  }
  repairBudget = 0;
  repairConsent = false;
  repairSession: any = null;
  repairOriginalReview: any = null;
  repairBestReview: any = null;
  copyStatus = '';
  noRepairConfirmed = false;
  noRepairDecisionError = '';
  decisionReadError = '';
  get validRepairBudget(): boolean { return Number.isFinite(Number(this.repairBudget)) && Number(this.repairBudget) > 0 && Number(this.repairBudget) <= 20; }
  get validRepairSessionId(): boolean { return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(this.repairSessionId.trim()); }
  get manualPatchMessage(): string {
    if (!this.intentConfirmed) return 'No current Step 4 Creative Intent confirmation is available; confirm supported intent in Production Review first.';
    if (!this.protectedIntent.trim()) return 'Step 4 Creative Intent is already confirmed, but the saved decision has no protected-intent text. Enter the wording that must remain unchanged; do not repeat the intent confirmation.';
    if (!this.patchOriginal) return 'Select the exact source wording to replace.';
    const first = this.prompt.indexOf(this.patchOriginal);
    if (first < 0) return 'The selected wording does not occur in the saved prompt.';
    if (this.prompt.indexOf(this.patchOriginal, first + 1) >= 0) return 'The selected wording occurs more than once; narrow the exact match.';
    if (!this.patchReplacement.trim()) return 'Enter replacement wording to preview the patch.';
    return 'Exact match found once. Validation creates a candidate only; the saved prompt remains unchanged.';
  }
  get manualPatchValid(): boolean {
    return !!this.patchOriginal && !!this.patchReplacement.trim() && this.prompt.indexOf(this.patchOriginal) >= 0
      && this.prompt.indexOf(this.patchOriginal, this.prompt.indexOf(this.patchOriginal) + 1) < 0;
  }
  get manualPatchPreview(): string {
    if (!this.manualPatchValid) return '';
    return this.prompt.replace(this.patchOriginal, this.patchReplacement);
  }
  get canonicalEvaluation(): any { return this.review?.canonicalRuleEvaluation || {}; }
  get canonicalScoreLabel(): string {
    const score = this.canonicalEvaluation.score;
    return Number.isFinite(Number(score)) ? `${Number(score).toFixed(0)} / 100` : 'UNKNOWN score';
  }
  get canonicalGrade(): string { return String(this.canonicalEvaluation.grade || 'UNKNOWN'); }
  get canonicalFailCount(): number { return Array.isArray(this.canonicalEvaluation.failedRules) ? this.canonicalEvaluation.failedRules.length : 0; }
  get canonicalOutcomeSummary(): string {
    const canonical = this.canonicalEvaluation;
    return `PASS ${canonical.passedRules?.length || 0} · FAIL ${canonical.failedRules?.length || 0} · UNKNOWN ${canonical.unknownRules?.length || 0} · NOT_APPLICABLE ${canonical.notApplicableRules?.length || 0}`;
  }
  get actionableTextDefects(): string[] {
    const canonicalFailures = (Array.isArray(this.canonicalEvaluation.failedRules) ? this.canonicalEvaluation.failedRules : [])
      .map((rule: any) => `${rule.ruleId || 'Unnamed canonical rule'} · ${rule.severity || 'severity UNKNOWN'} · applicable canonical FAIL`);
    const explicitTextFindings = (Array.isArray(this.review?.planQuality?.findings) ? this.review.planQuality.findings : [])
      .filter((finding: any) => {
        const scope = String(finding?.scope || finding?.category || finding?.type || finding?.domain || '').toUpperCase();
        const applicability = String(finding?.applicability || '').toUpperCase();
        const repairability = String(finding?.repairability || '').toUpperCase();
        return /PROMPT|TEXT/.test(scope)
          && finding?.repairable === true
          && !['NOT_APPLICABLE', 'UNKNOWN'].includes(applicability)
          && !['OPTIONAL', 'NOT_REPAIRABLE'].includes(repairability);
      })
      .map((finding: any) => `${finding.id || finding.ruleId || finding.code || 'Text finding'} · ${finding.severity || 'severity UNKNOWN'} · explicitly repairable`);
    return [...canonicalFailures, ...explicitTextFindings];
  }
  get requiredTextRepair(): boolean {
    return this.canonicalFailCount > 0
      || String(this.review?.planQuality?.status || '').toUpperCase() === 'FAIL'
      || (Array.isArray(this.review?.planQuality?.findings) && this.review.planQuality.findings.some((finding: any) =>
        finding?.repairable === true
        && !['OPTIONAL', 'NOT_REPAIRABLE'].includes(String(finding?.repairability || '').toUpperCase())
        && !['UNKNOWN', 'NOT_APPLICABLE'].includes(String(finding?.applicability || '').toUpperCase())
        && /PROMPT|TEXT/i.test(String(finding?.scope || finding?.category || finding?.type || finding?.domain || ''))));
  }
  get recommendedTextRepair(): boolean {
    return !this.requiredTextRepair && (
      this.optionalCreativeImprovements.length > 0
      || String(this.review?.planQuality?.recommendation || this.review?.recommendation || '').toUpperCase().includes('REPAIR')
    );
  }
  get repairRecommendationLabel(): string {
    if (!this.review || !this.isCurrent()) return 'Evidence missing or stale';
    if (this.technicalEvaluationStatus.startsWith('Technical failure')) return 'Revalidation required';
    if (this.requiredTextRepair) return 'Required';
    if (this.recommendedTextRepair) return 'Optional recommendation';
    return 'No repair justified';
  }
  get repairPolicyMessage(): string {
    if (!this.review || !this.isCurrent()) return 'The saved evaluation is missing or stale. Revalidate in Step 5 before recording a Step 6 decision.';
    if (this.technicalEvaluationStatus.startsWith('Technical failure')) return 'Technical assessment is unavailable; resolve and revalidate it before making a no-repair decision.';
    if (this.requiredTextRepair) return 'The saved evidence indicates a text repair requirement. Review the supported finding before continuing.';
    if (this.recommendedTextRepair) return 'A text improvement is recommended but not required. You may approve a reasoned no-repair decision and continue without marking the suggestion resolved.';
    return 'No applicable canonical prompt-text failure or required text repair was identified.';
  }
  get noRepairDecisionBlockReason(): string {
    if (!this.review || !this.isCurrent()) return 'Current saved analysis evidence is required.';
    if (this.technicalEvaluationStatus.startsWith('Technical failure')) return 'Revalidate the technical evaluation before deciding.';
    if (this.requiredTextRepair) return 'A required text repair must be reviewed; no-repair approval is not available.';
    if (this.decisionReadError) return 'Saved operator decisions could not be verified; retry the read before submitting.';
    return 'No-repair approval is not available for this evidence state.';
  }
  get noRepairDecisionEligible(): boolean {
    return !!this.review && this.isCurrent()
      && this.canonicalEvaluation.status === 'EVALUATED'
      && !this.technicalEvaluationStatus.startsWith('Technical failure')
      && !this.requiredTextRepair
      && !this.decisionReadError;
  }
  get activeNoRepairDecision(): any | null {
    const decision = this.eventDecision('step6-no-text-repair', 'NO_TEXT_REPAIR_JUSTIFIED');
    return decision
      && !decision.stale
      && String(decision.analysisRunId) === String(this.review?.recordId)
      && String(decision.analysisBindingHash) === String(this.review?.bindingHash)
      ? decision
      : null;
  }
  get staleNoRepairDecision(): any | null {
    const decision = this.eventDecision('step6-no-text-repair', 'NO_TEXT_REPAIR_JUSTIFIED');
    return decision && !this.activeNoRepairDecision ? decision : null;
  }
  get optionalCreativeImprovements(): string[] {
    const findings = this.review?.planQuality?.optionalImprovements || this.review?.optionalCreativeImprovements || [];
    return (Array.isArray(findings) ? findings : []).map((item: any) =>
      typeof item === 'string' ? item : String(item?.message || item?.description || item?.ruleId || 'Optional improvement'));
  }
  get outstandingEvidence(): string[] {
    const reasons = this.review?.family8?.renderAuthorization?.reasons;
    if (!Array.isArray(reasons)) return [];
    return reasons.filter((reason: any) => /MISSING|PENDING|REQUIRED/.test(String(reason.code || '').toUpperCase()))
      .map((reason: any) => `${reason.source || 'Evidence'}: ${reason.message || reason.code || 'Requirement unresolved'}`);
  }
  get unknownCanonicalRules(): string[] {
    return (Array.isArray(this.canonicalEvaluation.unknownRules) ? this.canonicalEvaluation.unknownRules : [])
      .map((rule: any) => String(rule.ruleId || 'Unnamed rule'));
  }
  get localExecutionStatus(): string {
    return String(this.review?.executionReview?.status || this.review?.executionRisk?.status || 'UNKNOWN');
  }
  get generatorCapabilityStatus(): string {
    return String(this.review?.generation?.capabilityStatus || 'UNKNOWN');
  }
  get productionComplexityStatus(): string {
    return String(this.review?.generalProducibility?.status || 'UNKNOWN');
  }
  get technicalEvaluationStatus(): string {
    const status = String(this.canonicalEvaluation.status || this.review?.reviewStatus || this.review?.status || '').toUpperCase();
    const reviewStatus = String(this.review?.reviewStatus || this.review?.status || '').toUpperCase();
    const reasons = this.review?.family8?.renderAuthorization?.reasons || [];
    const authorizationStatus = String(this.review?.family8?.renderAuthorization?.status || '').toUpperCase();
    const failed = status.includes('FAILED') || status.includes('TECHNICAL_FAILURE')
      || reviewStatus.includes('TECHNICAL_FAILURE')
      || authorizationStatus.includes('TECHNICAL_FAILURE')
      || reasons.some((reason: any) => /TECHNICAL_FAILURE/.test(String(reason.code || '').toUpperCase()));
    return failed ? 'Technical failure recorded; revalidation required' : 'No technical evaluation failure recorded';
  }
  get recommendedRepairAction(): string {
    if (!this.review || !this.isCurrent()) return 'Load or revalidate the exact saved analysis.';
    if (this.technicalEvaluationStatus.startsWith('Technical failure')) return 'Resolve the technical evaluation failure before proceeding.';
    if (this.repairRecommended) return 'Review the supported text finding; no automatic repair is applied.';
    if (this.outstandingEvidence.length) return 'Continue to Render Preparation to resolve visual inputs; keep UNKNOWN evidence unchanged.';
    if (this.unknownCanonicalRules.length) return 'Review UNKNOWN canonical evidence before relying on this assessment.';
    return 'Continue to Render Preparation.';
  }
  get promptDeclaredProfile(): string {
    return String(this.prompt.match(/Content profile:\s*([A-Z_]+)/i)?.[1] || 'NOT DECLARED').toUpperCase();
  }
  get repairRecommended(): boolean {
    const recommendation = String(this.review?.planQuality?.recommendation || this.review?.recommendation || '').toUpperCase();
    return this.actionableTextDefects.length > 0 || recommendation.includes('REPAIR') || String(this.review?.planQuality?.status || '').toUpperCase().includes('FAIL');
  }
  get repairTriageTitle(): string {
    if (!this.review || !this.isCurrent()) return 'Confirm this exact saved analysis before deciding';
    if (this.technicalEvaluationStatus.startsWith('Technical failure')) return 'Evaluation unavailable for repair triage';
    if (this.requiredTextRepair) return 'Text repair required';
    if (this.recommendedTextRepair) return 'Optional text repair is recommended';
    return 'No actionable prompt-text repair identified';
  }
  get repairTriageSummary(): string {
    if (!this.review || !this.isCurrent()) return 'This analysis is missing or stale for the selected prompt/settings. Revalidate the exact saved version before continuing.';
    if (this.technicalEvaluationStatus.startsWith('Technical failure')) return 'This saved evaluation has a technical failure and cannot support repair triage. Revalidate through the official analysis workflow.';
    const summary = `Saved canonical result: ${this.canonicalScoreLabel}, grade ${this.canonicalGrade}; ${this.canonicalOutcomeSummary}.`;
    if (this.requiredTextRepair) return `${summary} ${this.actionableTextDefects.join('; ') || this.review?.planQuality?.recommendation || 'The saved evidence requires text repair.'}`;
    if (this.recommendedTextRepair) return `${summary} ${this.optionalCreativeImprovements.join('; ') || this.review?.planQuality?.recommendation || 'A non-blocking text improvement is recommended.'}`;
    const evidence = this.outstandingEvidence.length
      ? ` Outstanding evidence remains: ${this.outstandingEvidence.join('; ')}.`
      : '';
    const unknown = this.unknownCanonicalRules.length
      ? ` UNKNOWN rules remain unverified: ${this.unknownCanonicalRules.join(', ')}.`
      : '';
    return `${summary} No actionable canonical prompt-text failure is recorded.${evidence}${unknown} Production critic, provider capability and complexity classifications are distinct and shown separately. Missing verified character reference and accepted start frame are Step 7 responsibilities, not text-repair tasks.`;
  }
  selectRepairForReview(): void {
    if (!this.review || !this.isCurrent() || !this.repairRecommended) return;
    this.persistUiLocation();
  }
  approveNoTextRepairAndContinue(): void {
    if (!this.noRepairDecisionEligible || !this.noRepairConfirmed || this.busy || !this.review) return;
    const sequence = this.restoreSequence;
    const analysisRunId = String(this.review.recordId);
    this.busy = true;
    this.noRepairDecisionError = '';
    this.http.post<any>('/api/v1/intelligence/workflow/production-review/decisions', {
      contentId: this.contentId,
      promptVersionId: this.promptVersionId,
      decisionType: 'NO_TEXT_REPAIR_JUSTIFIED',
      decisionId: 'step6-no-text-repair',
      decision: 'NO_TEXT_REPAIR_JUSTIFIED',
      operatorConfirmed: true,
      analysisRunId,
      analysisBindingHash: this.review.bindingHash,
    }).subscribe({
      next: decision => {
        if (sequence !== this.restoreSequence) return;
        if (decision?.decisionType !== 'NO_TEXT_REPAIR_JUSTIFIED'
            || decision?.decision !== 'NO_TEXT_REPAIR_JUSTIFIED'
            || String(decision?.analysisRunId) !== analysisRunId
            || String(decision?.analysisBindingHash) !== String(this.review?.bindingHash)
            || decision?.stale === true
            || !decision?.recordId
            || !decision?.savedAt) {
          this.busy = false;
          this.noRepairDecisionError = 'The server did not confirm a current saved decision. Step 7 was not opened.';
          this.changeDetector.markForCheck();
          return;
        }
        this.reviewDecisions = [
          ...this.reviewDecisions.filter((row: any) =>
            !(row.decisionType === decision.decisionType && row.decisionId === decision.decisionId)),
          decision,
        ];
        this.noRepairConfirmed = false;
        this.busy = false;
        this.changeDetector.markForCheck();
        this.selectStage(7);
      },
      error: error => {
        if (sequence !== this.restoreSequence) return;
        this.busy = false;
        this.noRepairDecisionError = error?.error?.detail || error?.error?.message
          || 'The no-repair decision could not be saved. Step 7 was not opened.';
        this.changeDetector.markForCheck();
      },
    });
  }
  private repairKey = '';
  private autoRepair = false;
  private repairOperation = 0;
  startRepairSession() {
    if (!this.isCurrent() || !this.repairConsent || !this.validRepairBudget || this.busy || !this.review?.recordId) return;
    this.busy = true;
    this.autoRepair = true;
    this.repairOriginalReview = null; this.repairBestReview = null;
    const sequence = this.restoreSequence;
    const operation = ++this.repairOperation;
    this.repairKey ||= crypto.randomUUID();
    this.http.post<any>('/api/v1/intelligence/workflow/repair-sessions', { reviewId: this.review.recordId, idempotencyKey: this.repairKey, maxAttempts: 2, maxCostUsd: this.repairBudget }).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation) return;
      this.repairSession = session; this.repairSessionId = session.sessionId; this.busy = false;
      const url = new URL(window.location.href); url.searchParams.set('repairSessionId', session.sessionId); window.history.replaceState(window.history.state, '', url.toString());
      this.nextRepairAttempt(true); }, error: e => { if (sequence === this.restoreSequence && operation === this.repairOperation) { this.autoRepair = false; this.fail(e); } } });
  }
  nextRepairAttempt(continueAutomatically = false) {
    if (this.repairSession?.state !== 'READY' || this.busy) return;
    if (this.repairSession.attempts >= Math.min(this.repairSession.maxAttempts, 2)) return;
    const sequence = this.restoreSequence;
    const operation = this.repairOperation;
    const sessionId = this.repairSession.sessionId;
    const previousAttempts = this.repairSession.attempts;
    this.busy = true;
    this.http.post<any>(`/api/v1/intelligence/workflow/repair-sessions/${sessionId}/step`, {}).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation || this.repairSession?.sessionId !== sessionId) return;
      this.repairSession = session; this.busy = false; this.changeDetector.markForCheck();
      if (continueAutomatically && this.autoRepair && session.state === 'READY'
          && session.stopReason === 'NEXT_ATTEMPT_AVAILABLE' && session.attempts > previousAttempts
          && session.history?.at(-1)?.stage === 'INDEPENDENTLY_REVIEWED') this.nextRepairAttempt(true);
      else { this.autoRepair = false; this.loadRepairComparison(session); }
    }, error: e => { if (sequence === this.restoreSequence && operation === this.repairOperation && this.repairSession?.sessionId === sessionId) { this.autoRepair = false; this.fail(e); } } });
  }
  decideRepair(decision: string) {
    if (!this.repairSession) return;
    this.autoRepair = false;
    const sequence = this.restoreSequence;
    const operation = ++this.repairOperation;
    const sessionId = this.repairSession.sessionId;
    this.http.post<any>(`/api/v1/intelligence/workflow/repair-sessions/${this.repairSession.sessionId}/decision`, { decision }).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation || this.repairSession?.sessionId !== sessionId) return;
      this.repairSession = session;
      this.busy = false;
      if (session.state === 'ACCEPTED') this.http.get<any>(`/api/v1/intelligence/workflow/records/${session.bestReviewId}`).subscribe({ next: review => { if (sequence === this.restoreSequence && this.repairSession?.sessionId === sessionId) this.acceptedVersion.emit({ contentId: session.contentId, promptVersionId: session.bestPromptVersionId, rawText: review.originalPrompt, repairSessionId: session.sessionId }); }, error: e => { if (sequence === this.restoreSequence) this.fail(e); } });
      this.changeDetector.markForCheck();
    }, error: e => this.fail(e) });
  }
  reopenRepairSession(id: string) {
    if (!id.trim()) return;
    this.autoRepair = false;
    const sequence = this.restoreSequence;
    const operation = ++this.repairOperation;
    this.http.get<any>(`/api/v1/intelligence/workflow/repair-sessions/${encodeURIComponent(id.trim())}`).subscribe({ next: session => {
      if (sequence !== this.restoreSequence || operation !== this.repairOperation) return;
      if (String(session.contentId) !== this.contentId || ![String(session.originalPromptVersionId), String(session.bestPromptVersionId)].includes(this.promptVersionId)) { this.error = 'Repair session belongs to another source version.'; return; }
      this.repairSession = session; this.repairSessionId = session.sessionId; this.loadRepairComparison(session); this.changeDetector.markForCheck();
    }, error: e => this.fail(e) });
  }
  ngOnDestroy(): void { this.reviewNavigationSequence++; this.autoRepair = false; this.repairOperation++; this.restoreSequence++; this.disposePromptPreview(); }
  private loadRepairComparison(session: any): void {
    if (!session.originalReviewId || !session.bestReviewId) return;
    const sequence = this.restoreSequence, operation = this.repairOperation;
    for (const [field, id] of [['repairOriginalReview', session.originalReviewId], ['repairBestReview', session.bestReviewId]] as const) {
      this.http.get<any>(`/api/v1/intelligence/workflow/records/${id}`).subscribe({ next: review => {
        if (sequence !== this.restoreSequence || operation !== this.repairOperation || this.repairSession?.sessionId !== session.sessionId) return;
        this[field] = review; this.changeDetector.markForCheck();
      }, error: e => { if (sequence === this.restoreSequence && operation === this.repairOperation) this.fail(e); } });
    }
  }
  repairSessionId = '';
  restoredRecordId = '';
  creativeOptimizationOpen = false;
  creativeOptimizationComparison: any = null;
  creativeOptimizationError = '';
  creativeOptimizationBusy = false;
  creativeOptimizationConsent = false;
  creativeOptimizationBudget = 0;
  creativeOptimizationSelectedCandidateId: string | null = null;
  creativeOptimizationReviewedCandidateId: string | null = null;
  private restoreSequence = 0;
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['prompt'] && this.promptPreviewEditor && this.promptPreviewEditor.getValue() !== this.prompt) {
      this.promptPreviewEditor.setValue(this.prompt);
      this.promptPreviewEditor.setScrollTop(0);
    }
    if(changes['prompt'] && this.eventDecision('creative-intent','CREATIVE_INTENT')?.sourceQuote !== this.prompt)this.intentConfirmed=false;
    if(changes['creativeProvenance']) { const decision=this.eventDecision('creative-intent','CREATIVE_INTENT'); if(decision && decision.storyRevisionId !== (this.creativeProvenance?.storyRevisionId||null))this.intentConfirmed=false; }
    if (changes['workflowProfile']) this.profile = changes['workflowProfile'].currentValue || 'FROZEN';
    if (!changes['contentId'] && !changes['promptVersionId'] && !changes['workflowProfile']) return;
    this.review = null;
    this.sourcePlanEvidence=null;this.sourcePlanStatus='NOT_LOADED';this.sourcePlanRun='';
    this.qa = null;
    this.creativeOptimizationOpen = false;
    this.creativeOptimizationComparison = null;
    this.creativeOptimizationError = '';
    this.creativeOptimizationBusy = false;
    this.creativeOptimizationConsent = false;
    this.creativeOptimizationBudget = 0;
    this.creativeOptimizationSelectedCandidateId = null;
    this.creativeOptimizationReviewedCandidateId = null;
    this.repairKey = '';
    this.autoRepair = false;
    this.repairOperation++;
    this.repairSession = null;
    this.repairOriginalReview = null;
    this.repairBestReview = null;
    this.busy = false;
    this.repairConsent = false;
    this.repairBudget = 0;
    this.noRepairConfirmed = false;
    this.noRepairDecisionError = '';
    this.decisionReadError = '';
    this.copyStatus = '';
    this.reviewedInputs = '';
    this.restoredRecordId = '';
    this.activeStage = 4;
    this.activeProductionTab = 'overview';
    this.activeAnalysisTab = 'summary';
    this.savedDuration = null; this.savedAspectRatio = ''; this.savedAspectRatioProvenance = '';
    this.legacyProductionPlan=null;this.legacyEvidenceError='';this.contentProfile='AUTO';this.openingStrategy='AUTO';this.generator='AUTO';this.desiredDuration=null;this.aspectRatio='';this.intentConfirmed=false;this.protectedIntent='';this.intentRequirementsText='[]';this.reviewDecisions=[];this.eventDrafts={};this.conflictDrafts={};this.decisionsLoadedFor='';this.confirmedSettingsSnapshot='';this.settingsSavedAt=null;this.references=[];this.referenceCharacter='';this.characterId='';this.characterResolvedFromCatalog=false;this.approvedCharacterReferences=[];this.selectedReferencePreview=null;this.firstFramePath='';this.firstFrameUrl='';
    this.hydrateSettingsFromPrompt();
    this.resolveCharacterIdentity();
    const sequence = ++this.restoreSequence;
    if (!this.contentId || !this.promptVersionId) return;
    this.restoreProductionReviewDecisions();this.loadProviderCapabilities();
    const savedSessionId = new URL(window.location.href).searchParams.get('repairSessionId');
    if (savedSessionId) this.reopenRepairSession(savedSessionId);
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=REVIEW', { params: { contentId: this.contentId, promptVersionId: this.promptVersionId } }).subscribe({
      next: rows => {
        if (sequence !== this.restoreSequence) return;
        const saved = rows.find(row => String(row.contentId) === this.contentId && String(row.promptVersionId) === this.promptVersionId);
        if (!saved) { this.restorePersistedSettings(sequence); return; }
        this.review = saved;
        this.restoreUiLocation();
        this.restoredRecordId = saved.recordId;
        if(this.activeStage===5)this.loadSourcePlan();
        this.profile = 'post-family-v1';
        const bound = saved.boundRequest || {};
        this.canonicalValidationId = bound.canonicalValidationId || bound.authorizationEvidence?.validationRecordId || null;
        for (const key of ['contentProfile', 'openingStrategy', 'generator', 'desiredDuration', 'qualityJustification', 'viewerQuestion', 'plannedEditedDuration', 'intentChangeReason', 'lessonModelVersion'] as const) {
          if (bound[key] !== undefined) (this as any)[key] = bound[key];
        }
        this.savedDuration = bound.desiredDuration ?? bound.settings?.duration ?? null;
        this.intentRequirementsText = JSON.stringify(bound.intentRequirements || [], null, 2);
        // Analysis intent requirements are evidence, not a Step 4 reviewer approval.
        this.creativeEvidenceText = JSON.stringify(bound.creativeEvidence || [], null, 2);
        if(!this.intentConfirmed)this.protectedIntent = (bound.protectedIntent || []).join('\n');
        this.structuredPlanText = bound.structuredPlan ? JSON.stringify(bound.structuredPlan, null, 2) : '';
        this.references = (bound.references || []).filter((ref: any) => ref.kind !== 'FIRST_FRAME');
        const frame = (bound.references || []).find((ref: any) => ref.kind === 'FIRST_FRAME');
        this.firstFramePath = frame?.relativePath || '';
        this.firstFrameUrl = bound.settings?.startFrame?.url || '';
        this.savedAspectRatio = bound.settings?.aspectRatio || bound.aspectRatio || '';
        this.savedAspectRatioProvenance = this.savedAspectRatio ? 'CANONICAL_REVIEW_BINDING' : '';
        this.settingsSavedAt = saved.createdAt || saved.updatedAt || null;
        if (this.savedAspectRatio) this.aspectRatio = this.savedAspectRatio;
        else this.hydrateSettingsFromPrompt();
        if (!this.referenceCharacter && (bound.mainCharacter || bound.mainCharacterName)) this.referenceCharacter = String(bound.mainCharacter || bound.mainCharacterName);
        // Restore a prior server-side reference binding as soon as the saved review
        // and canonical character identity are available, without requiring a tab click.
        if (this.characterId) this.loadCharacterReferenceOptions();
        this.qaPath = this.videoPath;
        if (saved.decisionPolicyVersion === 'impact-review-v1' && bound.prompt === this.prompt) {
          this.reviewedInputs = this.inputSnapshot();
        } else this.error = 'Historical review: source or decision policy changed; a new evaluation is required.';
        this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=ACTUAL_RENDER_QA', { params: { bindingHash: saved.bindingHash } }).subscribe({
          next: records => {
            if (sequence !== this.restoreSequence) return;
            this.qa = records.find(row => row.bindingHash === saved.bindingHash) || null;
            this.changeDetector.markForCheck();
          }, error: e => this.fail(e),
        });
        this.restorePersistedSettings(sequence);
        this.changeDetector.markForCheck();
      }, error: e => this.fail(e),
    });
  }

  private resolveCharacterIdentity(){const sequence=this.restoreSequence+1;if(this.referenceCharacter||!this.prompt.trim())return;this.http.get<any[]>('/api/v1/characters').subscribe({next:rows=>{if(sequence!==this.restoreSequence)return;const text=this.prompt.toLowerCase();const match=(rows||[]).find(row=>{const names=[row.name,row.displayName,row.characterName,...(Array.isArray(row.aliases)?row.aliases:[])].filter(Boolean).map(String);return names.some(name=>new RegExp('\\b'+name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\b','i').test(text));});if(match){this.referenceCharacter=String(match.name||match.displayName||match.characterName);this.characterId=String(match.id||'');this.characterResolvedFromCatalog=true;if(this.review)this.loadCharacterReferenceOptions();}this.changeDetector.markForCheck();},error:()=>{}});}
  private hydrateSettingsFromPrompt(){const text=this.prompt||'';const labelled=text.match(/(?:duration|target duration|length)\s*[:=]?\s*(\d{1,2})\s*(?:s|sec|seconds)?/i);const candidates=Array.from(text.matchAll(/\b(5|8|10|12|15|20|25|30)\s*(?:s|sec|seconds)\b/gi)).map(match=>Number(match[1]));const durationValue=labelled?Number(labelled[1]):(candidates.length?Math.max(...candidates):null);this.promptDuration=durationValue;if(!this.desiredDuration&&durationValue)this.desiredDuration=durationValue;const ratio=text.match(/\b(9:16|16:9|1:1)\b/);this.promptAspectRatio=ratio?ratio[1]:'';if(!this.aspectRatio&&ratio)this.aspectRatio=ratio[1];}
  private sourceBoundPlan(){
    const saved=this.parsedPlan();
    if(saved && !(saved.evidenceStatus==='DETERMINISTIC_SOURCE_EVENTS_ONLY' && saved.events && !saved.beats))return saved;
    return {schemaVersion:'source-bound-beats-v1',evidenceStatus:'DETERMINISTIC_SOURCE_EVENTS_ONLY',sourceVersion:this.promptVersionId,
      beats:this.timedRanges.map((range,index)=>{const start=this.prompt.indexOf(range.quote,range.quoteStart);const event=this.sourceEvents[index];
        return {id:event.id,startTime:range.start,endTime:range.end,action:event.action,sourceQuote:range.quote,
          sourceSpan:start<0?null:[Array.from(this.prompt.slice(0,start)).length,Array.from(this.prompt.slice(0,start+range.quote.length)).length],semanticStatus:'PENDING'};})};
  }
  private options() {
    return {
      profile: this.profile,
      canonicalValidationId: this.canonicalValidationId,
      lessonModelVersion: this.lessonModelVersion,
      contentProfile: this.contentProfile,
      contentProfileRecommendation: { ...this.profileProposal, sourceVersion: this.promptVersionId },
      openingStrategy: this.openingStrategy,
      openingStrategyRecommendation: { ...this.openingProposal, sourceVersion: this.promptVersionId },
      generator: this.generator,
      generatorRecommendation: { ...this.generatorProposal, sourceVersion: this.promptVersionId },
      desiredDuration: this.desiredDuration,
      qualityJustification: this.qualityJustification,
      viewerQuestion: this.viewerQuestion,
      plannedEditedDuration: this.plannedEditedDuration,
      structuredPlan: this.sourceBoundPlan(),
      intentRequirements: this.parseList(this.intentRequirementsText),
      creativeEvidence: this.parseList(this.creativeEvidenceText),
      intentChangeReason: this.intentChangeReason,
      protectedIntent: this.protectedIntent
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean),
      references: this.firstFramePath
        ? [
            ...this.references,
            { character: '', kind: 'FIRST_FRAME', relativePath: this.firstFramePath },
          ]
        : this.references,
      settings: {
        mode: 'image2video',
        aspectRatio: this.aspectRatio,
        resolution: '480p',
        ...(this.firstFramePath
          ? {
              startFrame: {
                type: 'image',
                id: this.firstFramePath,
                url: this.firstFrameUrl,
                label: 'Reviewed first frame',
              },
            }
          : {}),
      },
      segments: [],
    };
  }
  loadSourceIntent() {
    this.busy = true;
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=REVIEW', { params: { contentId: this.contentId, promptVersionId: this.promptVersionId } }).subscribe({
      next: (rows) => {
        const source = rows.find(
          (r) =>
            String(r.contentId) === this.contentId &&
            String(r.promptVersionId) === this.promptVersionId &&
            r.decisionPolicyVersion === 'impact-review-v1',
        );
        if (source) {
          this.intentRequirementsText = JSON.stringify(
            source.boundRequest?.intentRequirements || [],
            null,
            2,
          );
          this.creativeEvidenceText = JSON.stringify(
            source.boundRequest?.creativeEvidence || [],
            null,
            2,
          );
          this.protectedIntent = (source.boundRequest?.protectedIntent || []).join('\n');
          this.error = '';
        } else this.error = 'No impact review found for this source version.';
        this.busy = false;
        this.changeDetector.markForCheck();
      },
      error: (e) => this.fail(e),
    });
  }
  private parseList(text: string) {
    try {
      const value = JSON.parse(text);
      return Array.isArray(value) ? value : null;
    } catch {
      return null;
    }
  }
  setIntentLevel(beat: any, level: string) {
    const items = this.parseList(this.intentRequirementsText) || [];
    const quote = Array.from(this.prompt).slice(beat.sourceSpan[0], beat.sourceSpan[1]).join('');
    this.intentRequirementsText = JSON.stringify(
      [
        ...items.filter((i: any) => i.id !== beat.id),
        {
          id: beat.id,
          level,
          sourceSpan: beat.sourceSpan,
          sourceQuote: quote,
          eventIds: [beat.id],
          rationale: 'Operator source-event preference before render',
        },
      ],
      null,
      2,
    );
  }
  private parsedPlan() {
    try {
      return this.structuredPlanText.trim() ? JSON.parse(this.structuredPlanText) : null;
    } catch {
      return null;
    }
  }
  private inputSnapshot() {
    return JSON.stringify({
      creativeSource: this.creativeProvenance ? {recordId:this.creativeProvenance.creativeRoleRecordId,revision:this.creativeProvenance.storyRevisionId,specificationStatus:this.creativeProvenance.productionSpecificationStatus} : null,
      structuredPlanText: this.structuredPlanText,
      prompt: this.prompt,
      contentId: this.contentId,
      promptVersionId: this.promptVersionId,
      options: this.options(),
    });
  }
  isCurrent() {
    return !!this.review && this.inputSnapshot() === this.reviewedInputs;
  }
  addReference() {
    this.references = [
      ...this.references,
      {
        character: this.referenceCharacter,
        relativePath: this.referencePath,
        kind: 'CHARACTER_REFERENCE',
      },
    ];
    this.referencePath = '';
  }
  runReview() {
    if (this.profile !== 'post-family-v1') {
      this.error = 'Select the approved Production Review workflow before continuing.';
      return;
    }
    if (!this.analysisReady) {
      this.error = 'The saved content ID, prompt version and source prompt are required before analysis.';
      return;
    }
    if (this.structuredPlanText.trim() && !this.parsedPlan()) {
      this.error = 'The source-bound plan could not be read as JSON; source evidence was not updated.';
      return;
    }
    if (
      !this.parseList(this.intentRequirementsText) ||
      !this.parseList(this.creativeEvidenceText)
    ) {
      this.error = 'Intent/comment declarations could not be read; source review was not run.';
      return;
    }
    this.busy = true;
    this.analysisJustCompleted = false;
    this.error = '';
    const snapshot = this.inputSnapshot();
    this.http
      .post<any>('/api/v1/intelligence/workflow/review', {
        contentId: Number(this.contentId) || null,
        promptVersionId: Number(this.promptVersionId) || null,
        prompt: this.prompt,
        sourcePath: this.sourcePath,
        options: this.options(),
      })
      .subscribe({
        next: (r) => {
          this.review = r;
          this.reviewedInputs = r.originalPrompt !== undefined && r.originalPrompt !== this.prompt ? '' : snapshot;
          if (!this.reviewedInputs) this.error = 'Save the edited text as a new immutable version; the server reviewed the saved source version.';
          this.busy = false;
          this.analysisJustCompleted = true;
          this.activeStage = 5;
          this.persistUiLocation();
          this.changeDetector.markForCheck();
          setTimeout(() => document.getElementById('analysis-report')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
          this.qaPath = this.videoPath;
          this.qaStates = {};
          this.qaStarts = {};
          this.qaEnds = {};
          this.qaExperience = {};
          this.qaDescriptions = {};
          this.qaEnd = null;
          this.clipReviewed = false;
          this.stillsReviewed = false;
          this.qa = null;
          this.association = null;
        },
        error: (e) => this.fail(e),
      });
  }
  repair() {
    if (!this.review?.recordId || !this.isCurrent()) {
      this.error = 'A current saved analysis is required before applying a prompt patch.';
      return;
    }
    if (!this.intentConfirmed || !this.protectedIntent.trim()) {
      this.error = this.manualPatchMessage;
      return;
    }
    const start = this.prompt.indexOf(this.patchOriginal);
    if (start < 0 || this.prompt.indexOf(this.patchOriginal, start + 1) >= 0) {
      this.error = 'The patch text must occur exactly once in the source.';
      return;
    }
    this.busy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/repair`, {
        patches: [
          {
            start: Array.from(this.prompt.slice(0, start)).length,
            end: Array.from(this.prompt.slice(0, start + this.patchOriginal.length)).length,
            sourceQuote: this.patchOriginal,
            replacement: this.patchReplacement,
          },
        ],
      })
      .subscribe({
        next: (r) => {
          this.review = r;
          this.error = '';
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  async copyPrompt() {
    const value = this.review?.finalPrompt || this.prompt;
    if (!value || !this.isCurrent()) return;
    try {
      await navigator.clipboard.writeText(value);
      this.copyStatus = 'Prompt preview copied.';
    } catch {
      this.copyStatus = 'Clipboard access is unavailable. Select and copy the preview manually.';
    }
    this.changeDetector.markForCheck();
  }
  async copySavedPrompt() {
    if (!this.prompt || !this.isCurrent()) return;
    try {
      await navigator.clipboard.writeText(this.prompt);
      this.copyStatus = 'Saved prompt copied.';
    } catch {
      this.copyStatus = 'Clipboard access is unavailable. Select and copy the saved prompt manually.';
    }
    this.changeDetector.markForCheck();
  }
  manualHandoffSnapshot(exportedAt: Date = new Date()) {
    if (!this.review) return null;
    return {
      ...this.review,
      manualHandoff: {
        schemaVersion: 'manual-render-package-v1',
        exportedAt: exportedAt.toISOString(),
        contentId: String(this.review.contentId || this.contentId),
        promptVersionId: String(this.review.promptVersionId || this.promptVersionId),
        promptVersionNumber: this.promptVersionNumber,
        analysisId: this.review.recordId,
        bindingHash: this.review.bindingHash || null,
        promptSha256: this.review.source?.sha256 || null,
        promptDeclaredProfile: this.promptDeclaredProfile,
        profileUsedByAnalysis: this.evaluationProfile,
        effectiveSavedProfile: this.contentProfile,
        effectiveSettings: {
          contentProfile: this.contentProfile,
          generator: this.generator,
          durationSeconds: this.desiredDuration,
          aspectRatio: this.aspectRatio,
          status: this.settingsStatus,
        },
        renderAuthorizationStatus: this.review.family8?.renderAuthorization?.status || 'UNKNOWN',
        authorizationGrantedByExport: false,
        providerCalledByExport: false,
      },
    };
  }
  exportHandoff() {
    if (!this.review || !this.isCurrent()) return;
    const handoff = this.manualHandoffSnapshot();
    if (!handoff) return;
    const blob = new Blob([JSON.stringify(handoff, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'pompom-manual-render-review.json';
    a.click();
    URL.revokeObjectURL(url);
  }
  runQa() {
    const defects = this.parseList(this.qaDefectsText);
    let repairProposal: any;
    try {
      repairProposal = JSON.parse(this.qaRepairText);
    } catch {
      this.error = 'Intervention evidence could not be read';
      return;
    }
    if (!defects || !repairProposal || Array.isArray(repairProposal)) {
      this.error = 'Defect/intervention evidence could not be read';
      return;
    }
    this.busy = true;
    const beats = this.review.productionEvidence.videoPlanIR.beats;
    const duration = Math.max(...beats.map((b: any) => b.endTime), 0);
    const end = this.qaEnd ?? this.videoDuration ?? duration;
    const events = beats.map((b: any) => ({
      id: b.id,
      start: this.qaStarts[b.id] ?? (this.qaStates[b.id] === 'ABSENT' ? this.qaStart : b.startTime),
      end: this.qaEnds[b.id] ?? (this.qaStates[b.id] === 'ABSENT' ? end : b.endTime),
      state: this.qaStates[b.id] || 'UNKNOWN',
      evidenceBasis: this.clipReviewed ? 'HUMAN_REVIEWED_CLIP' : 'SAMPLED_STILLS',
      reference: `${this.qaPath}#t=${this.qaStarts[b.id] ?? b.startTime},${this.qaEnds[b.id] ?? b.endTime}`,
      observed:
        this.qaStates[b.id] === 'PRESENT'
          ? 'The operator observed this planned event in the actual clip range.'
          : this.qaStates[b.id] === 'ABSENT'
            ? 'The operator observed that this planned event was absent from the actual clip range.'
            : '',
      inferred: '',
      uncertainty: 'Operator observation; no automatic semantic validation was performed',
      confidence: this.clipReviewed ? 'MEDIUM' : 'UNKNOWN',
    }));
    const experience = Object.fromEntries(
      this.qaAspects.map((a) => [
        a.key,
        {
          value: this.qaExperience[a.key] || 'UNKNOWN',
          start: this.qaStart,
          end,
          observed: this.qaDescriptions[a.key] || '',
          inferred: '',
          uncertainty: 'Operator observation; no audio/transcript evidence',
          confidence: this.clipReviewed ? 'MEDIUM' : 'UNKNOWN',
          evidenceBasis: this.clipReviewed ? 'HUMAN_REVIEWED_CLIP' : 'SAMPLED_STILLS',
          reference: `${this.qaPath}#t=${this.qaStart},${end}`,
        },
      ]),
    );
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/qa`, {
        relativePath: this.qaPath,
        humanReviewed: this.clipReviewed,
        stillsReviewed: this.stillsReviewed,
        observation: { coverage: [this.qaStart, end], events, experience, defects, repairProposal },
      })
      .subscribe({
        next: (r) => {
          this.qa = r;
          this.busy = false;
          this.changeDetector.markForCheck();
          this.videoDuration = r.technicalAnalysis?.metadata?.durationMs / 1000 || null;
        },
        error: (e) => this.fail(e),
      });
  }
  associate() {
    this.busy = true;
    this.http
      .post<any>('/api/v1/intelligence/workflow/feedback/ASSOCIATION', {
        platform: this.platform,
        platformContentId: this.platformContentId,
        videoId: this.qa.videoId,
        variantId: this.variantId || null,
        reviewId: this.review.recordId,
        qaRecordId: this.qa.recordId,
        renderAttemptId: null,
        reviewReason: this.associationReason,
      })
      .subscribe({
        next: (r) => {
          this.association = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  saveMeasurement() {
    this.busy = true;
    this.http
      .post<any>('/api/v1/intelligence/workflow/feedback/MEASUREMENT', {
        observation: {
          associationRecordId: this.association.recordId,
          platform: this.platform,
          platformContentId: this.platformContentId,
          sourceId: this.measurementSource,
          window: this.horizon,
          observedAt: new Date(this.measuredAt).toISOString(),
          durationSeconds: this.videoDuration,
          reach: this.reach,
          views: this.views,
          averageWatchSeconds: this.watchSeconds,
          paidReach: this.paidReach,
          paidWatchTimeShare: this.paidWatchShare,
        },
      })
      .subscribe({
        next: (r) => {
          this.measurement = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  compare() {
    this.busy = true;
    this.http.get<any[]>('/api/v1/intelligence/workflow/records?kind=MEASUREMENT').subscribe({
      next: (records) =>
        this.http
          .post<any>('/api/v1/intelligence/workflow/feedback/COHORT', {
            records: records.map((r) => r.raw),
            horizon: this.horizon,
            nearOrganicThreshold: this.nearOrganicThreshold,
          })
          .subscribe({
            next: (r) => {
              this.cohort = r;
              this.busy = false;
              this.changeDetector.markForCheck();
            },
            error: (e) => this.fail(e),
          }),
      error: (e) => this.fail(e),
    });
  }
  canonicalValidationId: number | null = null;
  canonicalMessage = ''; 
  validateCanonicalProfile() {
    if(!this.review?.recordId || !this.isCurrent()) return;
    this.busy=true;
    this.http.post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/canonical-validation`,{}).subscribe({
      next: value => {this.canonicalValidationId=value.validationRecordId; this.busy=false; this.canonicalMessage=`Canonical profile validation #${this.canonicalValidationId}: ${value.report?.status || 'recorded'}. Visual gates and independent revalidation remain required. Review again to bind the new canonical evidence.`;this.changeDetector.markForCheck();},
      error: response => {this.busy=false;this.error=response.error?.message || 'Canonical profile validation failed';this.changeDetector.markForCheck();}
    });
  }

  saveLesson(kind: string) {
    this.http
      .post<any>(`/api/v1/intelligence/workflow/learning/${kind}`, {
        hypothesis: this.lessonHypothesis,
        lessonScope: this.lessonScope,
        evidenceBasis: this.lessonScope === 'PROMPT_FIX' ? [this.repairSession?.history?.find((attempt: any) => attempt.reviewId === this.repairSession.bestReviewId)?.repairRecordId].filter(Boolean) : [this.qa?.recordId].filter(Boolean),
        sampleSize: 1,
        targetModelVersion: this.review.generation.profileVersion,
        settings: this.review.generation.settings,
        contentProfile: this.review.routing.contentProfile,
        durationRange: [this.lessonScope === 'PROMPT_FIX' ? this.desiredDuration : this.videoDuration, this.lessonScope === 'PROMPT_FIX' ? this.desiredDuration : this.videoDuration],
        observedResult: this.lessonScope === 'PROMPT_FIX' ? this.review?.executionReview?.status || 'UNKNOWN' : this.qa?.viewerFacingUsability || 'UNKNOWN',
        counterexamples: this.counterexamples,
      })
      .subscribe({
        next: (r) => {
          this.lesson = r;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  secondOpinion() {
    this.busy = true;
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.review.recordId}/critic`, {
        provider: this.criticProvider,
        model: this.criticModel,
      })
      .subscribe({
        next: (r) => {
          this.opinion = r;
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  renderLink() {
    return (
      '/render-preparation?' +
      new URLSearchParams({
        contentId: String(this.review?.contentId || ''),
        promptVersionId: String(this.review?.promptVersionId || ''),
        promptVersionNumber: String(this.promptVersionNumber ?? ''),
        ...(this.canonicalValidationId ? { validationRecordId: String(this.canonicalValidationId) } : {}),
        analysisId: String(this.review?.recordId || ''),
        workflowReviewId: this.review?.recordId || '',
      }).toString()
    );
  }
  renderPreparationLink(item?: {category:string; finding?:string}) {
    const text = `${item?.category || ''} ${item?.finding || ''}`.toLowerCase();
    const tab = /first.?frame|provider_input/.test(text) ? 'first-frame' : /reference|character/.test(text) ? 'characters' : /provider|setting|generator/.test(text) ? 'settings' : 'overview';
    const reviewId = this.review?.recordId || this.restoredRecordId || '';
    return '/render-preparation?' + new URLSearchParams({
      contentId: String(this.review?.contentId || this.contentId || ''),
      promptVersionId: String(this.review?.promptVersionId || this.promptVersionId || ''),
      promptVersionNumber: String(this.promptVersionNumber ?? ''),
      ...(this.canonicalValidationId ? { validationRecordId: String(this.canonicalValidationId) } : {}),
      ...(this.review?.recordId ? { analysisId: String(this.review.recordId) } : {}),
      ...(reviewId ? { workflowReviewId: reviewId } : {}), tab,
    }).toString();
  }
  authorizationLabel(status: unknown): string {
    const value = String(status || 'UNKNOWN').toUpperCase();
    if (value === 'AUTHORIZED') return 'Authorized for this exact saved request';
    if (value === 'BLOCKED_TECHNICAL_FAILURE') return 'Rendering blocked: saved assessment technical failure; inspect diagnostics';
    if (value.startsWith('BLOCKED')) return 'Rendering blocked: required production inputs or checks are missing';
    return 'Authorization unknown · rendering remains blocked';
  }
  reviewLesson(decision: string) {
    this.http
      .post<any>(`/api/v1/intelligence/workflow/records/${this.lesson.recordId}/learning-review`, {
        decision,
        reason: this.learningReason,
      })
      .subscribe({
        next: (r) => {
          this.lesson = r;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  private fail(error: any) {
    this.busy = false;
    this.changeDetector.markForCheck();
    this.error =
      error.error?.detail ||
      error.error?.message ||
      'The operation could not be completed; evidence remains UNKNOWN.';
  }
}
