import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, EventEmitter, Input, Output, OnChanges, OnDestroy, SimpleChanges, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { GeneralProducibilityComponent } from './general-producibility.component';

@Component({
  selector: 'app-post-family-workflow',
  standalone: true,
  imports: [CommonModule, FormsModule, GeneralProducibilityComponent],
  template: `
  <section *ngIf="activeStage === 4" class="workflow production-review" aria-label="Production review">
    <nav *ngIf="activeStage === 4" class="stage-subtabs" aria-label="Production Review sections" role="tablist">
      <button *ngFor="let tab of productionTabs" type="button" role="tab" [class.is-active]="activeProductionTab === tab.id" [attr.aria-selected]="activeProductionTab === tab.id" (click)="selectProductionTab(tab.id)">{{ tab.title }}<small>{{ tab.description }}</small></button>
    </nav>

    <section *ngIf="activeProductionTab === 'overview'" class="review-card overview-card">
      <header><div><span class="card-kicker">WORKFLOW OVERVIEW</span><h3>{{ contentTitle || 'Current saved prompt' }}</h3><p class="overview-subtitle">Prompt version {{ promptVersionId || 'UNKNOWN' }} · review the saved state before analysis.</p></div><span class="status-pill" [class.status-pill--ready]="analysisReady && !error">{{ error ? 'NEEDS ATTENTION' : (analysisReady ? 'READY' : 'INCOMPLETE') }}</span></header>
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
        <div><span class="check-icon" [class.check-icon--ok]="sourceEvents.length > 0">{{ sourceEvents.length > 0 ? '✓' : '!' }}</span><div><strong>Execution evidence</strong><small>{{ executionEvidenceStatus }}</small></div><button type="button" class="button button--secondary" (click)="selectProductionTab('execution')">Inspect</button></div>
        <div><span class="check-icon" [class.check-icon--ok]="references.length > 0">{{ references.length > 0 ? '✓' : '!' }}</span><div><strong>References</strong><small>{{ referenceStatus }}</small></div><button type="button" class="button button--secondary" (click)="selectProductionTab('references')">Manage</button></div>
      </div>
      <div class="overview-next"><div><span class="card-kicker">ANALYSIS ELIGIBILITY</span><strong>{{ analysisReady ? 'Eligible for preliminary quality analysis' : 'Complete the saved prompt requirements' }}</strong><p>{{ analysisReady ? 'This exact saved prompt version can be evaluated. Missing evidence remains explicitly UNKNOWN; this does not authorize rendering.' : 'A content ID, immutable prompt version and non-empty prompt are required.' }}</p></div></div>
      <p *ngIf="error" class="error">{{ error }}</p>
    </section>
    <section *ngIf="activeProductionTab === 'creative'" class="review-card intent-card"><header><div><span class="card-kicker">CREATIVE INTENT</span><h3>What must be preserved</h3></div><span class="source-badge">{{ intentConfirmed ? 'Confirmed source' : (protectedIntent ? 'Approved source' : 'Prompt-derived evidence') }}</span></header><div class="intent-grid"><div><span>Main character</span><strong>{{ characterLabel }}</strong><small>Catalog/source identity</small></div><div><span>Central object / situation</span><strong>{{ intentObject }}</strong><small>Source-backed extraction</small></div><div><span>Core mechanism</span><strong>{{ intentMechanism }}</strong><small>Prompt evidence; semantic approval pending</small></div><div><span>Essential progression</span><strong>{{ intentProgression }}</strong><small>Observable consequence</small></div><div><span>Essential ending</span><strong>{{ intentEnding }}</strong><small>Later source evidence</small></div><div><span>Needs clarification</span><strong>{{ intentAmbiguity }}</strong><small>Unresolved source relationship</small></div></div><div class="intent-actions"><button type="button" class="button button--primary" (click)="confirmIntent()" [disabled]="!intentAvailable">{{ intentConfirmed ? 'Intent confirmed' : 'Confirm supported intent' }}</button><button type="button" class="button button--secondary" (click)="intentEditing=!intentEditing">{{ intentEditing ? 'Hide intent editor' : 'Correct intent' }}</button><details><summary>View source evidence</summary><p>Source: approved story / saved prompt · version {{ promptVersionId || 'UNKNOWN' }}</p><p>{{ extractedIntent || 'No meaningful intent evidence found.' }}</p></details></div><textarea *ngIf="intentEditing" [(ngModel)]="protectedIntent" rows="4" placeholder="Add an operator correction; this will remain distinct from extracted evidence"></textarea></section>
    <section *ngIf="activeProductionTab === 'creative'" class="review-card"><header><div><span class="card-kicker">CREATIVE & SETTINGS</span><h3>Inherited workflow settings</h3></div><div class="intent-actions"><span class="status-pill" [class.status-pill--ready]="settingsStatus==='CONFIRMED'">{{ settingsStatus }}</span><button type="button" class="button button--secondary" (click)="settingsEditing=!settingsEditing">{{ settingsEditing ? 'Close settings' : 'Edit settings' }}</button></div></header><div class="settings-grid"><div><span>Main character</span><strong>{{ characterLabel || 'Unknown' }}</strong><small>{{ characterResolvedFromCatalog ? 'Catalog identity recognized from source prompt' : (characterLabel ? 'Saved source association' : 'Missing authoritative character record') }}</small></div><div><span>Content profile</span><strong>{{ contentProfileLabel }}</strong><small>{{ contentProfileHint }}</small></div><div><span>Target duration</span><strong>{{ desiredDuration ? desiredDuration + ' seconds' : 'Missing' }}</strong><small>{{ durationConflict ? 'Conflict: saved setting ' + savedDuration + 's · prompt text ' + promptDuration + 's' : (savedDuration ? 'Saved production setting' : (promptDuration ? 'Read from source prompt; confirm if authoritative' : 'Needs confirmation')) }}</small></div><div><span>Aspect ratio</span><strong>{{ aspectRatio || 'Missing' }}</strong><small>{{ aspectConflict ? 'Conflict: saved setting ' + savedAspectRatio + ' · prompt text ' + promptAspectRatio : (savedAspectRatio ? 'Saved production setting' : (promptAspectRatio ? 'Read from source prompt; confirm if authoritative' : 'Needs confirmation')) }}</small></div><div><span>Target generator</span><strong>{{ generatorLabel }}</strong><small>{{ generatorHint }}</small></div><div><span>Opening strategy</span><strong>{{ openingStrategyLabel }}</strong><small>{{ openingStrategyHint }}</small></div></div><div *ngIf="settingsEditing" class="settings-editor"><label>Content profile<select [(ngModel)]="contentProfile"><option value="AUTO">Source-based suggestion</option><option value="ABSURD_PHYSICS">Absurd Physics</option><option value="CURIOSITY_ADVENTURE">Curiosity / adventure</option><option value="EDUCATIONAL">Educational</option><option value="MIXED">Mixed</option></select></label><label>Target duration (seconds)<input type="number" min="1" [(ngModel)]="desiredDuration"></label><label>Aspect ratio<select [(ngModel)]="aspectRatio"><option value="">Needs confirmation</option><option>9:16</option><option>16:9</option><option>1:1</option></select></label><label>Target generator<select [(ngModel)]="generator"><option value="AUTO">System suggestion</option><option value="SEEDANCE_2_0_MINI">Seedance 2.0 Mini</option><option value="SEEDANCE_2_0">Seedance 2.0</option><option value="SEEDANCE_2_5">Seedance 2.5</option></select></label><button type="button" class="button button--primary settings-apply" (click)="applySettings()" [disabled]="busy || !contentId || !promptVersionId">{{ settingsSavedAt ? 'Apply changes' : 'Save settings' }}</button><small class="setting-note" *ngIf="settingsSavedAt">Saved {{ settingsSavedAt | date:'medium' }}</small></div></section>
    <section *ngIf="activeProductionTab === 'references'" class="review-card"><header><div><span class="card-kicker">VISUAL REFERENCES</span><h3>Character and first frame</h3></div><span class="status-pill">{{ firstFrameStatus }}</span></header><div class="reference-summary"><div><strong>{{ referenceCharacter || 'Character reference' }}</strong><span>{{ references.length ? references.length + ' validated reference(s)' : 'No Approved Character Reference' }}</span></div><div><strong>First frame</strong><span>{{ firstFrameStatus }}</span></div></div><button type="button" class="button button--secondary" (click)="referencesOpen=!referencesOpen">{{ referencesOpen ? 'Hide reference details' : 'Manage references' }}</button><p class="setting-note">The first frame defines the opening composition. Prepare, validate and accept it in Render after Quality Analysis; this screen never triggers image generation.</p><div *ngIf="referencesOpen" class="advanced-details"><p *ngFor="let ref of references">{{ ref.character || 'Character' }} · {{ ref.relativePath }}</p><p *ngIf="!references.length">No approved character asset is bound to this workflow.</p></div><details *ngIf="retrievedLessons.length" class="lesson-context"><summary>{{ retrievedLessons.length }} relevant lesson(s)</summary><p *ngFor="let lesson of retrievedLessons">{{ lesson.hypothesis }}</p></details></section>
    <section *ngIf="activeProductionTab === 'execution'" class="review-card execution-card"><header><div><span class="card-kicker">VISUAL EXECUTION PLAN</span><h3>Source-backed production beats</h3></div><span class="status-pill">{{ executionEvidenceStatus }} · {{ timedRanges.length }} timed ranges</span></header><div *ngIf="review?.productionEvidence?.videoPlanIR?.beats?.length; else sourceEventEvidence" class="beat-list"><article *ngFor="let beat of review.productionEvidence.videoPlanIR.beats"><strong>{{ beat.startTime != null ? beat.startTime + '–' + beat.endTime + ' s' : 'Sequence position' }}</strong><p>{{ cleanAnalysisText(beat.action) }}</p><small>{{ cleanAnalysisText(beat.sourceQuote || 'Source quote unavailable — source evidence could not be resolved.') }}</small></article></div><ng-template #sourceEventEvidence><div *ngIf="sourceEvents.length; else noBeatEvidence" class="beat-list"><article *ngFor="let event of sourceEvents"><strong>{{ event.start }}–{{ event.end }} s · {{ event.evidence }}</strong><p><b>{{ event.actor }}</b> · {{ event.object }}</p><p>{{ event.action }}</p><small>{{ event.consequence }} · Semantic significance: {{ event.semanticStatus }}</small><button type="button" class="source-quote-toggle" [attr.aria-expanded]="isSourceQuoteOpen(event.id)" (click)="toggleSourceQuote(event.id)">{{ isSourceQuoteOpen(event.id) ? 'Hide source quote' : 'Show source quote' }}</button><div *ngIf="isSourceQuoteOpen(event.id)" class="source-quote-panel"><span>Exact source · prompt version {{ promptVersionId || 'UNKNOWN' }}</span><p>{{ event.sourceQuote || 'Source quote unavailable — source evidence could not be resolved.' }}</p></div></article></div></ng-template><ng-template #noBeatEvidence><p class="missing-state">No source-backed timing or event evidence is available. Analysis may record UNKNOWN.</p></ng-template><details class="advanced-details"><summary>Advanced evidence details</summary><p>Source-bound extraction and raw structured data remain available for diagnostics; ordinary review does not require hand-written JSON.</p><dl class="diagnostic-list"><div><dt>Extraction</dt><dd>Deterministic timed-source extraction</dd></div><div><dt>Source version</dt><dd>{{ promptVersionId || 'UNKNOWN' }}</dd></div><div><dt>Evidence state</dt><dd>{{ semanticClassificationStatus }}</dd></div><div><dt>Event count</dt><dd>{{ sourceEvents.length }}</dd></div></dl><details class="developer-json"><summary>Developer-only raw JSON</summary><pre>{{ sourceEvents | json }}</pre></details></details></section>

    <details *ngIf="activeProductionTab === 'creative'" class="advanced-details technical-settings"><summary>Advanced details</summary><div class="advanced-groups"><section><h4>Configuration diagnostics</h4><p>Production settings are edited in the single canonical form above.</p><p><b>Selection provenance:</b> {{ settingsSavedAt ? 'Persisted workflow setting' : 'Not yet saved' }}</p><p><b>Opening strategy:</b> {{ openingStrategyLabel }} · {{ openingStrategyHint }}</p></section><section><h4>Creative context</h4><p><b>Protected intent provenance:</b> {{ protectedIntent ? 'Operator-confirmed source intent' : 'Prompt-derived; not yet confirmed' }}</p><p><b>Applicable lessons:</b> {{ retrievedLessons.length ? retrievedLessons.length + ' verified lesson(s)' : 'None found' }}</p><p><b>First-frame responsibility:</b> Render step owns visual preparation, generation, validation and acceptance.</p></section><section><h4>Visual reference diagnostics</h4><p><b>Character identity:</b> {{ characterLabel }} · {{ characterResolvedFromCatalog ? 'catalog recognized' : 'saved association or unresolved' }}</p><p><b>Character assets:</b> {{ references.length ? references.length + ' validated reference(s)' : 'Unavailable' }}</p><p><b>First frame:</b> {{ firstFrameStatus }} · no generation is triggered here.</p></section><section><h4>Developer diagnostics</h4><dl class="diagnostic-list"><div><dt>Workflow policy</dt><dd>{{ profile }}</dd></div><div><dt>Prompt version</dt><dd>{{ promptVersionId || 'UNKNOWN' }}</dd></div><div><dt>Content ID</dt><dd>{{ contentId || 'UNKNOWN' }}</dd></div><div><dt>Prompt hash</dt><dd>{{ review?.boundRequest?.promptSha256 || 'Available in saved prompt version endpoint' }}</dd></div><div><dt>Source reload</dt><dd><button type="button" (click)="loadSourceIntent()" [disabled]="busy || !contentId || !promptVersionId">Reload source evidence</button></dd></div></dl></section></div></details>
    <p class="error" *ngIf="error && !readinessCardShown">{{ error }}</p>
    <footer class="stage-action-bar" aria-label="Production Review actions"><button type="button" class="button button--secondary" (click)="selectStage(3)">← Back to Prompt</button><div><span class="card-kicker">NEXT ACTION</span><strong>{{ analysisReady ? 'Continue to Quality Analysis' : 'Complete the saved prompt requirements' }}</strong><small>{{ analysisReady ? 'Uses this saved content and prompt version; no render authorization is granted.' : 'Content ID, prompt version and prompt text are required.' }}</small></div><button type="button" class="button button--primary" (click)="runReview()" [disabled]="busy || !analysisReady || profile !== 'post-family-v1'">{{ busy ? 'Preparing evidence…' : 'Continue to Quality Analysis →' }}</button></footer>
  </section>
<ng-container *ngIf="review as r"><ng-container *ngIf="activeStage >= 5"><ng-container *ngIf="activeStage === 5">
        <nav class="stage-subtabs analysis-tabs" aria-label="Quality Analysis sections" role="tablist">
          <button *ngFor="let tab of analysisTabs" type="button" role="tab" [attr.aria-selected]="activeAnalysisTab === tab.id" [class.is-active]="activeAnalysisTab === tab.id" (click)="selectAnalysisTab(tab.id)">{{ tab.title }}<small>{{ tab.description }}</small></button>
        </nav>
        <div class="analysis-stage-toolbar"><span><b>Saved analysis</b><small>{{ r.recordId ? 'Current analysis run' : 'Analysis identity unavailable' }} · {{ r.promptVersionId || promptVersionId || 'UNKNOWN' }}</small></span><a class="button button--primary" [class.disabled-link]="!isCurrent()" [attr.aria-disabled]="!isCurrent()" [href]="isCurrent() ? '/api/v1/intelligence/workflow/records/' + (qa?.recordId || r.recordId) + '/pdf' : null" target="_blank" download>⇩ Export Analysis PDF</a></div>
        <ng-container *ngIf="activeAnalysisTab === 'summary'">
        <p class="error" *ngIf="!isCurrent()">
          Prompt, version, reference or setting changed. This review is stale; run it again.
        </p>
        <div class="facts" *ngIf="(qa || r).operatorReport as report">
          <p *ngFor="let row of report">
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
            <strong>Generator execution risk</strong>
            <p>{{ r.executionRisk?.status || 'UNKNOWN' }}</p>
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
        <section class="analysis-summary-decision" aria-label="Analysis decision summary"><div><span>Analysis status</span><strong>{{ r.reviewStatus || r.status || 'COMPLETED' }}</strong></div><div><span>Creative quality</span><strong>{{ r.family8?.creativeQuality?.creativeGrade || r.planQuality?.status || 'UNKNOWN' }}</strong></div><div><span>Render authorization</span><strong>{{ r.family8?.renderAuthorization?.status || 'UNKNOWN' }}</strong></div><div><span>Recommendation</span><strong>{{ r.planQuality?.recommendation || r.recommendation || 'No supported recommendation recorded' }}</strong></div></section>

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
              {{ reason.message }}
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
        <label *ngIf="activeAnalysisTab === 'evidence'"
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
        <footer class="analysis-stage-footer" aria-label="Quality Analysis navigation"><button type="button" class="button button--secondary" (click)="selectStage(4)">← Back to Production Review</button><button type="button" class="button button--primary" (click)="continueToRepair()">{{ nextAnalysisAction }} →</button></footer>
        </ng-container><ng-container *ngIf="activeStage === 6"><details><summary>Bounded repair session · at most two attempts</summary><label>Maximum total cost (USD)<input type="number" min="0" [(ngModel)]="repairBudget"></label><label><input type="checkbox" [(ngModel)]="repairConsent">I approve the configured repair provider within this session budget.</label><button type="button" (click)="startRepairSession()" [disabled]="busy || !isCurrent() || !repairConsent || repairBudget <= 0">Start bounded repair</button><label>Saved session ID<input [(ngModel)]="repairSessionId"></label><button type="button" (click)="reopenRepairSession(repairSessionId)">Reopen session</button><div *ngIf="repairSession"><p>{{ repairSession.sessionId }} · {{ repairSession.state }} · {{ repairSession.stopReason }} · attempts {{ repairSession.attempts }}/{{ repairSession.maxAttempts }} · reserved ceiling {{ repairSession.reservedCostUsd }} (actual spend may be unknown)</p><p>Best independently reviewed prompt version: {{ repairSession.bestPromptVersionId }}</p><section *ngIf="repairOriginalReview && repairBestReview" aria-label="Repair before and after findings"><h4>Original · prompt version {{ repairOriginalReview.promptVersionId }}</h4><pre>{{ repairOriginalReview.executionReview?.findings | json }}</pre><pre>{{ repairOriginalReview.planQuality | json }}</pre><h4>Best independently reviewed candidate · prompt version {{ repairBestReview.promptVersionId }}</h4><pre>{{ repairBestReview.executionReview?.findings | json }}</pre><pre>{{ repairBestReview.planQuality | json }}</pre></section><pre>{{ repairSession.history | json }}</pre><button type="button" (click)="nextRepairAttempt()" [disabled]="busy || repairSession.state !== 'READY'">Next bounded attempt</button><button type="button" (click)="decideRepair('ACCEPTED')" [disabled]="busy || repairSession.state === 'RUNNING'">Accept best candidate</button><button type="button" (click)="decideRepair('REJECTED')">Reject</button><button type="button" (click)="decideRepair('CANCELLED')">Cancel</button></div></details>
        <h3>Minimal repair</h3>
        <label>Source wording to replace<input [(ngModel)]="patchOriginal" /></label
        ><label>Replacement wording<input [(ngModel)]="patchReplacement" /></label>
        <button
          type="button"
          (click)="repair()"
          [disabled]="
            busy || !isCurrent() || !protectedIntent.trim() || !patchOriginal || r.repairPasses > 0
          "
        >
          One patch + final prompt validation
        </button>
        <pre *ngIf="r.diff">{{ r.diff }}</pre>
        <label>Final production prompt<textarea readonly [value]="r.finalPrompt"></textarea></label>
        <button type="button" (click)="copyPrompt()" [disabled]="!isCurrent()">Copy</button>
        <button type="button" (click)="saveFinal.emit(r.finalPrompt)" [disabled]="!isCurrent()">
          Transfer to editor and save version
        </button>
        <button type="button" (click)="exportHandoff()" [disabled]="!isCurrent()">
          Download manual render package
        </button>
        <p>
          The manual package does not authorize rendering or spending credits. The final video still follows the canonical
          acceptance flow.
        </p></ng-container>
        <section *ngIf="activeStage === 7" class="stage-empty-card render-stage-card">
          <span class="card-kicker">STEP 7 · RENDER</span>
          <h3>Render readiness</h3>
          <p>Prepare the first frame, verify provider capabilities and authorize generation from the canonical render queue.</p>
          <div class="render-readiness-summary"><strong>First frame</strong><span>{{ firstFrameStatus }}</span><strong>Authorization</strong><span>{{ review?.family8?.renderAuthorization?.status || 'Review required' }}</span></div>
          <p class="setting-note">Opening this stage does not generate an image or video and does not spend credits.</p>
          <a class="button button--primary" [href]="renderLink()" *ngIf="review?.contentId && review?.promptVersionId">Open render preparation →</a>
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
      .production-review{padding:24px;background:#f7f9fc}.stage-empty-card{display:grid;gap:12px;margin:14px 0;padding:22px;border:1px solid #cbded0;border-radius:12px;background:#f8fbf4}.stage-empty-card h3{margin:0;color:#263f56}.render-readiness-summary{display:grid;grid-template-columns:180px 1fr;gap:8px;padding:12px;border-radius:8px;background:#fff;border:1px solid #dfe7ee}.render-readiness-summary strong{color:#68747c}.render-readiness-summary span{color:#263f56;font-weight:700} .studio-stage-tabs{display:grid;grid-template-columns:repeat(8,minmax(90px,1fr));gap:7px;margin:0 0 14px;padding:6px;border:1px solid #d8e1ec;border-radius:12px;background:#fff;position:sticky;top:.75rem;z-index:10;box-shadow:0 5px 16px rgba(38,63,86,.08)}.studio-stage-tabs button,.stage-subtabs button{display:grid;gap:2px;padding:8px 9px;border:1px solid transparent;border-radius:8px;background:#fff;color:#52616b;text-align:left;font:inherit;cursor:pointer}.studio-stage-tabs button span{font-size:.65rem;color:#6a843e;font-weight:800}.studio-stage-tabs button strong{font-size:.73rem}.studio-stage-tabs button small,.stage-subtabs button small{font-size:.62rem;color:#7a858c}.studio-stage-tabs button.is-active{border-color:#8fbd36;background:#f5faed;box-shadow:0 0 0 2px #eaf3d7;color:#23452f}.studio-stage-tabs button:disabled{opacity:.45;cursor:not-allowed}.stage-subtabs{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:0 0 16px;padding:5px;border:1px solid #d8e1ec;border-radius:10px;background:#eef4f8}.stage-subtabs button{background:transparent}.stage-subtabs button.is-active{background:#fff;border-color:#8fbd36;color:#23452f}.stage-subtabs button.is-active small{color:#547b3c}.review-hero{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:20px}.review-hero h2{margin:4px 0;font-size:1.7rem;color:#263f56}.review-hero p{margin:0;color:#68747c;font-size:.95rem}.eyebrow,.card-kicker{color:#5f8435;font-size:.7rem;font-weight:800;letter-spacing:.08em}.review-card{display:grid;gap:14px;margin:14px 0;padding:20px;border:1px solid #d8e1ec;border-radius:12px;background:#fff;box-shadow:0 4px 16px rgba(38,63,86,.05)}.review-card header{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.review-card h3{margin:3px 0 0;color:#263f56;font-size:1.12rem}.status-pill,.source-badge{display:inline-flex;align-items:center;white-space:nowrap;padding:5px 9px;border-radius:999px;background:#fff5de;color:#855b15;font-size:.67rem;font-weight:800}.status-pill--ready{background:#e8f3dc;color:#31583b}.intent-summary{margin:0;padding:13px;border-left:4px solid #8fbd36;background:#f5faed;color:#40515a;line-height:1.55;white-space:pre-wrap}.intent-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.intent-grid>div{display:grid;gap:4px;padding:11px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.intent-grid span{color:#68747c;font-size:.7rem;font-weight:800;text-transform:uppercase}.intent-grid strong{color:#263f56;font-size:.9rem;line-height:1.4}.intent-grid small{color:#68747c;font-size:.72rem}.intent-actions{display:flex;flex-wrap:wrap;align-items:center;gap:8px}.intent-actions details{padding:0;margin-left:auto}.button{display:inline-flex;align-items:center;justify-content:center;padding:9px 13px;border:1px solid #cbd6ce;border-radius:7px;background:#fff;color:#31583b;font-weight:800;cursor:pointer}.button--primary{background:#31583b;color:#fff;border-color:#31583b}.button:disabled{opacity:.5;cursor:default}.settings-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.settings-grid>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.settings-grid span,.reference-summary span{color:#68747c;font-size:.7rem;font-weight:800;text-transform:uppercase}.settings-grid strong{font-size:.95rem;color:#263f56}.settings-grid small{color:#68747c;font-size:.72rem}.settings-editor{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;padding-top:8px;border-top:1px solid #e4e9e5}.advanced-groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.advanced-groups section{display:grid;gap:9px;padding:15px;border:1px solid #dfe7ee;border-radius:10px;background:#fbfcfd}.advanced-groups h4{margin:0;color:#263f56}.advanced-groups label{max-width:none}.setting-note{margin:0;color:#68747c;font-size:.78rem}.setting-note button{margin-left:6px;padding:4px 8px;border:1px solid #b8cdbf;border-radius:6px;background:#fff;color:#31583b;font-weight:700}.diagnostic-list{display:grid;gap:7px;margin:0}.diagnostic-list div{display:grid;grid-template-columns:130px 1fr;gap:8px}.diagnostic-list dt{font-weight:800;color:#68747c}.diagnostic-list dd{margin:0;color:#40515a;overflow-wrap:anywhere}.review-two-column{display:grid;grid-template-columns:1fr 1fr;gap:14px}.review-two-column .review-card{margin:0}.reference-summary{display:grid;grid-template-columns:1fr 1fr;gap:12px}.reference-summary>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px}.reference-summary strong{color:#263f56}.beat-list{display:grid;gap:9px}.beat-list article{display:grid;gap:4px;margin:0;padding:12px;border:1px solid #dfe7ee;border-radius:8px;background:#fbfcfd}.beat-list article strong{color:#31583b}.beat-list article p,.beat-list article small{margin:0;color:#40515a}.source-quote-toggle{justify-self:start;padding:5px 8px;border:1px solid #cbd6ce;border-radius:6px;background:#fff;color:#31583b;font-weight:800;cursor:pointer}.source-quote-panel{padding:10px;border-left:3px solid #8fbd36;background:#f3f7fb;color:#40515a}.source-quote-panel span{font-size:.72rem;font-weight:800;color:#68747c}.source-quote-panel p{margin:5px 0 0;white-space:pre-wrap}.success-note{margin:0;padding:10px 12px;background:#e8f3dc;border:1px solid #b9d7bd;border-radius:8px;color:#31583b;font-weight:700}.missing-state{margin:0;padding:14px;background:#fff9ed;border:1px solid #ecd2a2;border-radius:8px;color:#855b15}.advanced-details{color:#52616b}.advanced-details summary{cursor:pointer;font-weight:800}.readiness-card{border-color:#cbded0}.primary-action{justify-self:start}.restore-note{padding:10px 12px;border-radius:7px;background:#edf5fb;color:#40515a}.technical-settings{margin-top:16px;padding:12px 0}.technical-settings label{max-width:420px}.error{color:#983520}.overview-subtitle{margin:5px 0 0;color:#68747c;font-size:.82rem}.overview-facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.overview-facts>div{display:grid;gap:4px;padding:12px;border:1px solid #e1e8ee;border-radius:8px;background:#fbfcfd}.overview-facts span,.overview-checklist small{color:#68747c;font-size:.72rem}.overview-facts strong{color:#263f56;font-size:.92rem}.overview-checklist{display:grid;gap:8px}.overview-checklist>div{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:10px 12px;border:1px solid #e1e8ee;border-radius:8px;background:#fff}.overview-checklist div div{display:grid;gap:2px}.overview-checklist strong{color:#263f56}.check-icon{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:#fff2d5;color:#855b15;font-weight:900}.check-icon--ok{background:#e8f3dc;color:#31583b}.overview-next{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px;border:1px solid #cbded0;border-radius:10px;background:#f5faed}.overview-next div{display:grid;gap:4px}.overview-next strong{color:#263f56}.overview-next p{margin:0;color:#52616b;font-size:.82rem}@media(max-width:600px){.overview-facts{grid-template-columns:1fr}.overview-next{display:grid}.overview-checklist>div{grid-template-columns:auto 1fr}.overview-checklist button{grid-column:2;justify-self:start}}@media(max-width:900px){.studio-stage-tabs{grid-template-columns:repeat(4,minmax(120px,1fr));overflow-x:auto}.settings-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.settings-editor{grid-template-columns:repeat(2,minmax(0,1fr))}.advanced-groups{grid-template-columns:1fr}}@media(max-width:600px){.studio-stage-tabs{position:static;grid-template-columns:repeat(2,minmax(0,1fr))}.stage-subtabs{grid-template-columns:repeat(2,minmax(0,1fr))}.production-review{padding:14px}.review-hero{display:grid}.review-two-column,.settings-grid,.settings-editor,.reference-summary,.intent-grid{grid-template-columns:1fr}.review-card{padding:15px}.intent-actions details{margin-left:0}.primary-action{width:100%}.diagnostic-list div{grid-template-columns:1fr}}
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
      .facts {
        background: white;
        padding: 12px;
        margin: 12px 0;
      }
      .stage-action-bar,.analysis-stage-toolbar { display:flex; justify-content:space-between; gap:16px; align-items:center; margin:24px 0 4px; padding:16px; border:1px solid #cbded0; border-radius:10px; background:#f5faed; }
      .stage-action-bar > div,.analysis-stage-toolbar > span { display:grid; gap:4px; }
      .stage-action-bar small,.analysis-stage-toolbar small { color:#52616b; }
      .analysis-stage-toolbar { margin:0 0 16px; background:#fff; border-color:#d8e1ec; }
      .disabled-link { pointer-events:none; opacity:.5; }
      .analysis-stage-footer { display:flex; justify-content:space-between; gap:12px; align-items:center; margin:24px 0 4px; padding-top:16px; border-top:1px solid #d4dce8; }
      .analysis-stage-footer .button { margin:0; }
      .creative-quality-panel ul { margin:8px 0 0; padding-left:20px; }
      .source-details { margin:8px 0 14px; color:#526273; }
      .source-details summary { cursor:pointer; font-weight:600; }
      @media (max-width: 700px) { .analysis-stage-footer { flex-direction:column; align-items:stretch; } }
    `,
  ],
})
export class PostFamilyWorkflowComponent implements OnChanges, OnDestroy {
  private http = inject(HttpClient);
  private changeDetector = inject(ChangeDetectorRef);
  @Input() prompt = '';
  @Input() contentId = '';
  @Input() promptVersionId = '';
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
  selectStage(stage: number) {
    if (stage > 4 && !this.review) return;
    this.activeStage = stage;
    this.persistUiLocation();
    this.stageChanged.emit(stage);
    this.changeDetector.markForCheck();
  }
  get nextAnalysisAction(): string {
    const recommendation = String(this.review?.planQuality?.recommendation || this.review?.recommendation || '').toUpperCase();
    return recommendation.includes('REPAIR') ? 'Continue to Repair' : 'Review Required Findings';
  }
  continueToRepair(): void {
    if (!this.review || !this.isCurrent()) return;
    this.selectStage(6);
  }
  asList(value: unknown): string[] {
    if (Array.isArray(value)) return value.map(item => String(item)).filter(Boolean);
    const text = String(value ?? '').trim();
    return text ? [text] : ['UNKNOWN'];
  }
  selectAnalysisTab(tab: 'summary' | 'creative' | 'feasibility' | 'evidence') {
    this.activeAnalysisTab = tab;
    this.persistUiLocation();
  }
  selectProductionTab(tab: 'overview' | 'creative' | 'execution' | 'references') {
    this.activeProductionTab = tab;
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
      if (['overview', 'creative', 'execution', 'references'].includes(saved.tab)) this.activeProductionTab = saved.tab;
      if (['summary', 'creative', 'feasibility', 'evidence'].includes(saved.analysisTab)) this.activeAnalysisTab = saved.analysisTab;
    } catch { /* ignore corrupt UI-only state */ }
  }
  intentEditing = false; settingsEditing = false; referencesOpen = false; intentConfirmed = false; readinessCardShown = true;
  openSourceQuotes: Record<string, boolean> = {};
  profile = 'FROZEN';
  contentProfile = 'AUTO';
  get profileProposal(){const text=(this.prompt||'').toLowerCase();if(/sticky note|paper note|note .*stick|stick.*note|turns? in the air|flips? in the air|multiply|multipli/.test(text))return {value:'ABSURD_PHYSICS',reason:'Source describes an object behaving against its expected physical relationship.',status:'SUGGESTED'};if(/lesson|explain|teach|learn|how to|facts?/.test(text))return {value:'EDUCATIONAL',reason:'Source contains explicit teaching language.',status:'SUGGESTED'};if(/discover|mystery|wonder|explore|finds? out/.test(text))return {value:'CURIOSITY_ADVENTURE',reason:'Source contains a discovery-oriented promise.',status:'SUGGESTED'};return {value:'UNKNOWN',reason:'The source does not support a confident profile proposal.',status:'UNCERTAIN'};}
  get contentProfileLabel():string{if(this.contentProfile !== 'AUTO')return this.contentProfile.replaceAll('_',' ');return this.profileProposal.status==='SUGGESTED'?this.profileProposal.value.replaceAll('_',' '):'Profile uncertain';}
  get contentProfileHint():string{return this.contentProfile !== 'AUTO'?'Operator selection':this.profileProposal.status==='SUGGESTED'?'Suggested from approved source · confirmation required':'Review selection';}
  get generatorProposal(){const configured=this.generator !== 'AUTO'?this.generator:'SEEDANCE_2_0_MINI';return {value:configured,reason:this.generator !== 'AUTO'?'Operator selection':'Default production preference for a 15-second concept.',capability:this.generator !== 'AUTO'?'Verification pending':'Verification pending'};}
  get generatorLabel():string{return ({SEEDANCE_2_0_MINI:'Seedance 2.0 Mini',SEEDANCE_2_0:'Seedance 2.0',SEEDANCE_2_5:'Seedance 2.5'} as Record<string,string>)[this.generatorProposal.value] || this.generatorProposal.value.replaceAll('_',' ');}
  get generatorHint():string{return `${this.generatorProposal.reason} · Capability: ${this.generatorProposal.capability}`;}
  get openingProposal(){const first=this.timedRanges[0]?.quote.toLowerCase()||'';const second=this.timedRanges[1]?.quote.toLowerCase()||'';if(/already|clearly visible|visible from the first|holds? a sticky|stands? .* holding/.test(first)&&/turns?|flips?|sticks?|attaches?/.test(second))return {value:'INSTANT_IMPOSSIBLE',reason:'The opening establishes the ordinary setup, then exposes the unusual physical consequence immediately.',status:'SUGGESTED'};if(/problem|tries?|fails?|cannot|stuck/.test(first))return {value:'IMMEDIATE_PROBLEM',reason:'The first source event presents an active problem.',status:'SUGGESTED'};if(/discover|mystery|wonder|question/.test((this.prompt||'').slice(0,500).toLowerCase()))return {value:'CURIOSITY_DISCOVERY',reason:'The source opens with a discovery promise.',status:'SUGGESTED'};return {value:'UNKNOWN',reason:'Opening evidence is insufficient for a supported strategy proposal.',status:'UNCERTAIN'};}
  get openingStrategyLabel():string{return this.openingStrategy !== 'AUTO'?this.openingStrategy.replaceAll('_',' '):this.openingProposal.status==='SUGGESTED'?'Suggested: '+this.openingProposal.value.replaceAll('_',' '):'Opening strategy uncertain';}
  get openingStrategyHint():string{return this.openingStrategy !== 'AUTO'?'Operator confirmed · persisted workflow setting':this.openingProposal.status==='SUGGESTED'?'Needs confirmation · Accept or change':this.openingProposal.reason;}
  get characterLabel():string{return this.referenceCharacter || (this.references[0]?.character || 'Unknown');}
  get firstFrameStatus():string{return this.firstFramePath || this.firstFrameUrl ? 'Needs validation' : 'Not yet available';}
  get analysisReady(){return !!this.contentId && !!this.promptVersionId && !!this.prompt.trim();}
  get intentAvailable(){return !!(this.protectedIntent.trim() || this.extractedIntent.trim());}
  get evidenceIncomplete(){return !this.references.length || !this.review?.productionEvidence?.videoPlanIR?.beats?.length;}
  cleanAnalysisText(value: unknown): string { const text=String(value ?? 'UNKNOWN'); return text.replace(/\s*(?:AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\s*:?[\s\S]*$/i, '').replace(/Planlanan final\s*:/i, 'Planned ending:').trim() || 'UNKNOWN'; }
  get semanticClassificationStatus(): string { const evidence=this.review?.productionEvidence || {}; const metadata=evidence.videoPlanIR?.metadata || {}; return String(metadata.semanticClassificationStatus || evidence.semanticStatus || 'PENDING'); }
  get executionEvidenceStatus(): string { const beats=this.review?.productionEvidence?.videoPlanIR?.beats?.length || 0; const status=this.semanticClassificationStatus.toUpperCase(); return ['COMPLETED','CONFIRMED','OBSERVED'].includes(status) ? `${beats} semantically evaluated event(s)` : beats ? `${beats} parsed source event(s) · semantic classification pending` : this.sourceEvents.length ? `${this.sourceEvents.length} source event candidate(s) · classification pending` : 'No source event evidence yet'; }
  get referenceStatus(): string { return this.references.length ? `${this.references.length} validated reference(s)` : 'No approved character reference'; }

  get intentObject(){const text=(this.prompt||'').toLowerCase();if(/sticky note|sticky notes/.test(text))return 'Sticky notes around Mimi and the toy cabinet';if(/\b(note|cabinet|box|ball|door)\b/.test(text))return (text.match(/\b(note|cabinet|box|ball|door)\b/)||['Unresolved object'])[0];return 'Unresolved';}
  get intentMechanism(){const text=(this.prompt||'').toLowerCase();if(/sticky note|note/.test(text)&&/stick|attach|flip|turn/.test(text))return 'Notes change direction or attach to Mimi instead of the intended surface.';return 'No single source-backed mechanism is established.';}
  get intentProgression(){const text=(this.prompt||'').toLowerCase();if(/multiply|multipli/.test(text)&&/cover|covered/.test(text))return 'Attempts to remove or escape lead to further attachments and escalation.';if(this.sourceEvents.length>1)return 'The source describes successive observable actions across timed ranges.';return 'Progression remains unresolved.';}
  get intentEnding(){const text=(this.prompt||'').toLowerCase();if(/only (her|their) (wide )?eyes|covered .*notes|covered .*sticky/.test(text))return 'Mimi is covered by notes, leaving only her eyes visible.';return 'No explicit ending is available in the selected source.';}
  get intentAmbiguity(){const text=(this.prompt||'').toLowerCase();if(/multiply|multipli/.test(text))return 'Whether multiplication and pursuit are independent effects or one consequence.';return 'No unresolved mechanism was explicitly identified.';}
  settingsSavedAt: string | null = null;
  applySettings(){ if(!this.contentId || !this.promptVersionId) return; this.busy=true; this.error=''; this.http.post<any>('/api/v1/intelligence/workflow/production-settings',{contentId:this.contentId,promptVersionId:this.promptVersionId,contentProfile:this.contentProfile,openingStrategy:this.openingStrategy,generator:this.generator,desiredDuration:this.desiredDuration,aspectRatio:this.aspectRatio,qualityJustification:this.qualityJustification}).subscribe({next:r=>{this.settingsSavedAt=r.savedAt||new Date().toISOString();this.savedDuration=this.desiredDuration;this.savedAspectRatio=this.aspectRatio;this.settingsEditing=false;this.busy=false;this.changeDetector.markForCheck();},error:e=>this.fail(e)}); }
  private restorePersistedSettings(sequence:number){ if(!this.contentId||!this.promptVersionId)return; this.http.get<any>('/api/v1/intelligence/workflow/production-settings',{params:{contentId:this.contentId,promptVersionId:this.promptVersionId}}).subscribe({next:s=>{if(sequence!==this.restoreSequence)return; this.contentProfile=s.contentProfile??this.contentProfile;this.openingStrategy=s.openingStrategy??this.openingStrategy;this.generator=s.generator??this.generator;this.desiredDuration=s.desiredDuration??this.desiredDuration;this.aspectRatio=s.aspectRatio??this.aspectRatio;this.savedDuration=this.desiredDuration;this.savedAspectRatio=this.aspectRatio;this.settingsSavedAt=s.savedAt||null;this.changeDetector.markForCheck();},error:()=>{this.http.get<any>('/api/v1/intelligence/workflow/studio-sessions/by-prompt',{params:{contentId:this.contentId,promptVersionId:this.promptVersionId}}).subscribe({next:s=>{if(sequence!==this.restoreSequence)return; this.contentProfile=s.profile??this.contentProfile;this.generator=s.targetGenerator??this.generator;this.desiredDuration=s.duration??this.desiredDuration;this.aspectRatio=s.aspectRatio??this.aspectRatio;this.savedDuration=this.desiredDuration;this.savedAspectRatio=this.aspectRatio;this.savedAspectRatioProvenance = 'STUDIO_SESSION';this.settingsSavedAt=s.updatedAt||null;this.changeDetector.markForCheck();},error:()=>{}});}}); }
  get settingsStatus(){if(this.durationConflict||this.aspectConflict)return 'CONFLICT';if(!this.desiredDuration||!this.aspectRatio)return 'NEEDS CONFIRMATION';if(this.contentProfile==='AUTO'||this.generator==='AUTO'||this.openingStrategy==='AUTO')return 'PARTIALLY AVAILABLE';return 'CONFIRMED';}
  get sourceEvents(){return this.timedRanges.map((range,index)=>{const quote=range.quote.replace(/^\d{1,2}(?::\d{2})?\s*(?:-|–|—|to)\s*\d{1,2}(?::\d{2})?\s*(?:s|sec|secs|seconds)?\s*:?\s*/i,'').trim();const lower=quote.toLowerCase();const object=/sticky note|sticky notes|notes?|cabinet/.test(lower)?(lower.includes('cabinet')?'sticky note / cabinet':'sticky notes'):'Unresolved';const consequence=/cover|covered/.test(lower)?'Final state: Mimi is covered, with only her eyes visible.':/multiply|multipli/.test(lower)?'Apparent multiplication and return are explicit; causal relationship remains unresolved.':/stick|attach|flip|turn/.test(lower)?'Visible attachment or direction change is described in the source.':'Observable consequence requires semantic assessment.';return {id:`source-event-${index+1}`,start:range.start,end:range.end,actor:this.characterLabel==='Unknown'?'Unresolved':this.characterLabel,object,action:quote||'No action text extracted',consequence,sourceQuote:range.quote,evidence:'SOURCE_EVENT_CANDIDATE',semanticStatus:'PENDING'};});}
  isSourceQuoteOpen(id:string){return !!this.openSourceQuotes[id];}
  toggleSourceQuote(id:string){this.openSourceQuotes={...this.openSourceQuotes,[id]:!this.openSourceQuotes[id]};}
  acceptProfileSuggestion(){if(this.profileProposal.status==='SUGGESTED')this.contentProfile=this.profileProposal.value;}
  acceptOpeningSuggestion(){if(this.openingProposal.status==='SUGGESTED')this.openingStrategy=this.openingProposal.value;}
  acceptGeneratorSuggestion(){this.generator=this.generatorProposal.value;}
  get durationConflict(){return this.savedDuration != null && this.promptDuration != null && this.savedDuration !== this.promptDuration;}
  get aspectRatioProvenanceLabel(): string { return this.savedAspectRatioProvenance === 'OPERATOR_PRODUCTION_SETTINGS' ? 'Explicit operator setting' : this.savedAspectRatioProvenance === 'STUDIO_SESSION' ? 'Studio session setting' : this.savedAspectRatioProvenance === 'CANONICAL_REVIEW_BINDING' ? 'Recorded in review binding; override history unavailable' : 'Needs confirmation'; }
  get aspectConflict(){return !!this.savedAspectRatio && !!this.promptAspectRatio && this.savedAspectRatio !== this.promptAspectRatio;}
  get timedRanges():Array<{start:number;end:number;quote:string;quoteStart:number;quoteEnd:number}>{const text=this.prompt||'';const ranges:Array<{start:number;end:number;quote:string;quoteStart:number;quoteEnd:number}>=[];const add=(start:number,end:number,index:number,matchEnd:number)=>{if(end<=start)return;const rest=text.slice(matchEnd);const nextTimed=rest.search(/(?:\\n|\n)\s*(?:(?:\d{1,2}:\d{2})\s*(?:-|–|—|to)\s*(?:\d{1,2}:\d{2})|(?:\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(?:\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?\s*:)/i);const nextSection=rest.search(/(?:\\n|\n)\s*(?:AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT|REFERENCES|CHARACTER|VISUAL STYLE)\s*:?(?:\s*\n|\s*$)/i);const offsets=[text.length];if(nextTimed>=0)offsets.push(matchEnd+nextTimed);if(nextSection>=0)offsets.push(matchEnd+nextSection);const quoteEnd=Math.min(...offsets);if(!ranges.some(range=>range.start===start&&range.end===end))ranges.push({start,end,quote:text.slice(index,quoteEnd).trim(),quoteStart:index,quoteEnd});};let match:RegExpExecArray|null;const clock=/((?:\d{1,2}):(?:\d{2}))\s*(?:-|–|—|to)\s*((?:\d{1,2}):(?:\d{2}))\s*:?[ \t]*/gi;while((match=clock.exec(text))){const parse=(value:string)=>{const parts=value.split(':').map(Number);return parts[0]*60+parts[1];};add(parse(match[1]),parse(match[2]),match.index,clock.lastIndex);}const seconds=/(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?\s*:/gi;while((match=seconds.exec(text))){add(Number(match[1]),Number(match[2]),match.index,seconds.lastIndex);}return ranges.sort((a,b)=>a.start-b.start||a.end-b.end);}
  get extractedIntent():string{const text=this.prompt||'';const heading=/(TITLE\s*\/\s*FORMAT|VISUAL STYLE|CHARACTER\s*\/\s*CONTINUITY|TIMED SHOT PLAN|AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\s*:?[ \t]*/gi;const matches=Array.from(text.matchAll(heading));const useful:string[]=[];for(let index=0;index<matches.length;index++){const label=matches[index][1].toUpperCase();if(!/CHARACTER|TIMED SHOT PLAN/.test(label))continue;const start=(matches[index].index||0)+matches[index][0].length;const end=index+1<matches.length?(matches[index+1].index||text.length):text.length;const body=text.slice(start,end).trim();if(body)useful.push(body);}if(useful.length)return useful.join(' ').slice(0,520);return text.split(/\r?\n/).map(line=>line.trim()).filter(Boolean).filter(line=>!/(TITLE|FORMAT|VISUAL STYLE|AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT)\s*:?[ \t]*/i.test(line)).join(' ').slice(0,520);}
  confirmIntent(){if(!this.intentAvailable)return;this.intentConfirmed=true;const source=this.protectedIntent.trim()||this.extractedIntent;this.intentRequirementsText=JSON.stringify([{id:'character',level:'ESSENTIAL',value:this.characterLabel,sourceQuote:source,sourceVersion:this.promptVersionId},{id:'mechanism',level:'ESSENTIAL',value:this.intentMechanism,sourceQuote:source,sourceVersion:this.promptVersionId},{id:'ending',level:'ESSENTIAL',value:this.intentEnding,sourceQuote:source,sourceVersion:this.promptVersionId},{id:'ambiguity',level:'UNRESOLVED',value:this.intentAmbiguity,sourceQuote:source,sourceVersion:this.promptVersionId}]);this.changeDetector.markForCheck();}

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
  referencePath = '';
  references: Array<{ character: string; relativePath: string; kind: string }> = [];
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
    return '/render?' + new URLSearchParams({ contentId: String(this.regenerationHandoff.contentId), promptVersionId: String(this.regenerationHandoff.promptVersionId), workflowReviewId: this.regenerationHandoff.reviewId, regenerationHandoffId: this.regenerationHandoff.recordId }).toString();
  }
  repairBudget = 0;
  repairConsent = false;
  repairSession: any = null;
  repairOriginalReview: any = null;
  repairBestReview: any = null;
  private repairKey = '';
  private autoRepair = false;
  private repairOperation = 0;
  startRepairSession() {
    if (!this.isCurrent() || !this.repairConsent || this.repairBudget <= 0 || this.busy) return;
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
  ngOnDestroy(): void { this.autoRepair = false; this.repairOperation++; this.restoreSequence++; }
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
  private restoreSequence = 0;
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['workflowProfile']) this.profile = changes['workflowProfile'].currentValue || 'FROZEN';
    if (!changes['contentId'] && !changes['promptVersionId'] && !changes['workflowProfile']) return;
    this.review = null;
    this.qa = null;
    this.repairKey = '';
    this.autoRepair = false;
    this.repairOperation++;
    this.repairSession = null;
    this.repairOriginalReview = null;
    this.repairBestReview = null;
    this.busy = false;
    this.repairConsent = false;
    this.repairBudget = 0;
    this.reviewedInputs = '';
    this.restoredRecordId = '';
    this.activeStage = 4;
    this.activeProductionTab = 'overview';
    this.activeAnalysisTab = 'summary';
    this.savedDuration = null; this.savedAspectRatio = ''; this.savedAspectRatioProvenance = '';
    this.hydrateSettingsFromPrompt();
    this.resolveCharacterIdentity();
    const sequence = ++this.restoreSequence;
    if (!this.contentId || !this.promptVersionId) return;
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
        this.profile = 'post-family-v1';
        const bound = saved.boundRequest || {};
        this.canonicalValidationId = bound.canonicalValidationId || bound.authorizationEvidence?.validationRecordId || null;
        for (const key of ['contentProfile', 'openingStrategy', 'generator', 'desiredDuration', 'qualityJustification', 'viewerQuestion', 'plannedEditedDuration', 'intentChangeReason', 'lessonModelVersion'] as const) {
          if (bound[key] !== undefined) (this as any)[key] = bound[key];
        }
        this.savedDuration = bound.desiredDuration ?? bound.settings?.duration ?? null;
        this.intentRequirementsText = JSON.stringify(bound.intentRequirements || [], null, 2);
        this.creativeEvidenceText = JSON.stringify(bound.creativeEvidence || [], null, 2);
        this.protectedIntent = (bound.protectedIntent || []).join('\n');
        this.structuredPlanText = bound.structuredPlan ? JSON.stringify(bound.structuredPlan, null, 2) : '';
        this.references = (bound.references || []).filter((ref: any) => ref.kind !== 'FIRST_FRAME');
        const frame = (bound.references || []).find((ref: any) => ref.kind === 'FIRST_FRAME');
        this.firstFramePath = frame?.relativePath || '';
        this.firstFrameUrl = bound.settings?.startFrame?.url || '';
        this.savedAspectRatio = bound.settings?.aspectRatio || bound.aspectRatio || '';
        this.savedAspectRatioProvenance = this.savedAspectRatio ? 'CANONICAL_REVIEW_BINDING' : '';
        if (this.savedAspectRatio) this.aspectRatio = this.savedAspectRatio;
        else this.hydrateSettingsFromPrompt();
        if (!this.referenceCharacter && (bound.mainCharacter || bound.mainCharacterName)) this.referenceCharacter = String(bound.mainCharacter || bound.mainCharacterName);
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
        this.changeDetector.markForCheck();
      }, error: e => this.fail(e),
    });
  }

  private resolveCharacterIdentity(){if(this.referenceCharacter||!this.prompt.trim())return;this.http.get<any[]>('/api/v1/characters').subscribe({next:rows=>{const text=this.prompt.toLowerCase();const match=(rows||[]).find(row=>{const names=[row.name,row.displayName,row.characterName,...(Array.isArray(row.aliases)?row.aliases:[])].filter(Boolean).map(String);return names.some(name=>new RegExp('\\b'+name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\b','i').test(text));});if(match){this.referenceCharacter=String(match.name||match.displayName||match.characterName);this.characterResolvedFromCatalog=true;}this.changeDetector.markForCheck();},error:()=>{}});}
  private hydrateSettingsFromPrompt(){const text=this.prompt||'';const labelled=text.match(/(?:duration|target duration|length)\s*[:=]?\s*(\d{1,2})\s*(?:s|sec|seconds)?/i);const candidates=Array.from(text.matchAll(/\b(5|8|10|12|15|20|25|30)\s*(?:s|sec|seconds)\b/gi)).map(match=>Number(match[1]));const durationValue=labelled?Number(labelled[1]):(candidates.length?Math.max(...candidates):null);this.promptDuration=durationValue;if(!this.desiredDuration&&durationValue)this.desiredDuration=durationValue;const ratio=text.match(/\b(9:16|16:9|1:1)\b/);this.promptAspectRatio=ratio?ratio[1]:'';if(!this.aspectRatio&&ratio)this.aspectRatio=ratio[1];}
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
      structuredPlan: this.parsedPlan() || { events: this.sourceEvents, evidenceStatus: 'DETERMINISTIC_SOURCE_EVENTS_ONLY', sourceVersion: this.promptVersionId },
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
          this.busy = false;
          this.changeDetector.markForCheck();
        },
        error: (e) => this.fail(e),
      });
  }
  async copyPrompt() {
    await navigator.clipboard.writeText(this.review.finalPrompt);
  }
  exportHandoff() {
    const blob = new Blob([JSON.stringify(this.review, null, 2)], { type: 'application/json' });
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
      '/render?' +
      new URLSearchParams({
        contentId: String(this.review?.contentId || ''),
        promptVersionId: String(this.review?.promptVersionId || ''),
        workflowReviewId: this.review?.recordId || '',
      }).toString()
    );
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
