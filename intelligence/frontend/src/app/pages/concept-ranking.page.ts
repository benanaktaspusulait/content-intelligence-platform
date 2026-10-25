import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { StructuredSfeAuditComponent } from './structured-sfe-audit.component';

@Component({
  selector: 'app-concept-ranking', standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, StructuredSfeAuditComponent],
  template: `
    <main class="quality-validator-container">
      <header class="header"><h1>Concept Ranking</h1><p>Compare supplied concepts for approximately 15-second production before writing prompts.</p><a routerLink="/quality">Back to Prompt Quality</a></header>
      <section class="card card-body">
        <label for="concept-batch">Supplied concepts</label>
        <p>Paste a JSON array, one concept object, or labeled text concepts separated by a line containing ---.
          Include title, protagonist, goal, object/interaction, rule, frame zero, timed escalation plan, payoff and intended duration. Missing details stay missing.</p>
        <textarea id="concept-batch" rows="12" [ngModel]="batchText" (ngModelChange)="sourceChanged($event)" spellcheck="false"></textarea>
        <button type="button" class="btn btn-primary" [disabled]="busy || !batchText.trim()" (click)="rank()">{{ busy ? 'Ranking…' : 'Rank supplied concepts' }}</button>
        <p>Supplied-concept ranking uses the existing validators. Recommendations require subsequent prompt and render admission checks.</p>
        <p *ngIf="error" role="alert">{{ error }}</p>
      </section>
      <section class="card card-body" aria-label="Stored semantic evidence diagnostics">
        <h2>Stored semantic evidence diagnostics</h2>
        <p>Reanalyze the saved seed-42 live response. No new concepts, provider calls or renders.</p>
        <button type="button" class="btn" [disabled]="evidenceBusy" (click)="replayEvidence()">{{ evidenceBusy ? 'Reanalyzing…' : 'Reanalyze stored evidence — adapter V1' }}</button>
        <p *ngIf="evidenceError" role="alert">{{ evidenceError }}</p>
        <div *ngIf="evidenceReplay as replay">
          <p>Provider calls: {{ replay.providerCalls }} · Baseline exact: {{ replay.baselineExact }}. Presence does not establish creative quality.</p>
          <pre>{{ replay.payoffBreakdown | json }}</pre>
          <article *ngFor="let candidate of replay.candidates">
            <details><summary>{{ candidate.ideaId }} · {{ candidate.title }} · {{ candidate.projectedCanonicalEvidence.payoffStatus }}</summary>
              <details><summary>Raw</summary><pre>{{ candidate.rawProviderIdea | json }}</pre></details>
              <details><summary>Normalized</summary><pre>{{ candidate.normalizedSemanticStructure | json }}</pre></details>
              <details><summary>Projected Evidence</summary><pre>{{ candidate.projectedCanonicalEvidence | json }}</pre></details>
              <details><summary>Validator Recognition</summary><pre>{{ candidate.afterRecognition | json }}</pre></details>
              <p *ngFor="let field of candidate.fieldLossAudit" [class.evidence-loss]="field.status !== 'PRESERVED'">{{ field.sourceField }} · {{ field.status }} · {{ field.validatorRecognition }}</p>
            </details>
          </article>
        </div>
      </section>
      <app-structured-sfe-audit />
      <section class="card card-body" aria-label="Local concept generation">
        <h2>Generate local short-form concepts</h2>
        <p>Choose authored V1 recipes or a V2 compatible causal grammar with planned staging diversity and additive production selection. These are pre-render hypotheses, not measured retention.</p>
        <label>Generator Mode <select aria-label="Generator mode" [ngModel]="generatorMode" (ngModelChange)="modeChanged($event)"><option value="deterministic">Deterministic</option><option value="semantic">Semantic — configured provider required</option><option value="hybrid">Hybrid — configured provider required</option></select></label>
        <div *ngIf="generatorMode !== 'deterministic'"><p>Configured semantic provider required. Live execution is disabled in V1; no external spend is enabled here.</p><label><input type="checkbox" aria-label="Use mock semantic corpus" [ngModel]="useMockSemantic" (ngModelChange)="mockChanged($event)"> Use bundled mock corpus — no external calls</label></div>
        <label>Generator <select aria-label="Generator version" [ngModel]="generatorVersion" (ngModelChange)="versionChanged($event)"><option value="v1">V1 — authored baseline</option><option value="v2">V2 — causal grammar</option></select></label>
        <label *ngIf="generatorVersion === 'v2'">Beat Grammar <select aria-label="Beat Grammar version" [ngModel]="beatGrammarVersion" (ngModelChange)="beatVersionChanged($event)"><option value="">Off — accepted V2 baseline</option><option value="v2">V2 — strategy and consequence plan</option></select></label>
        <label *ngIf="generatorVersion === 'v2' && beatGrammarVersion === 'v2'">Premise Naturalness <select aria-label="Premise naturalness gate" [ngModel]="premiseGateVersion" (ngModelChange)="premiseGateChanged($event)"><option value="">Off — accepted baseline</option><option value="v1">V1 — affordance contradiction</option></select></label>
        <label *ngIf="generatorVersion === 'v2' && beatGrammarVersion === 'v2' && premiseGateVersion === 'v1'">Creative Shape <select aria-label="Creative Shape version" [ngModel]="creativeShapeVersion" (ngModelChange)="shapeVersionChanged($event)"><option value="">Off — accepted baseline</option><option value="v1">V1 — story shape curation</option></select></label>
        <label>Candidate count <input aria-label="Candidate count" type="number" min="10" max="100" [ngModel]="candidateCount" (ngModelChange)="generationChanged('count', $event)"></label>
        <label>Seed <input aria-label="Generation seed" type="number" min="0" [ngModel]="generationSeed" (ngModelChange)="generationChanged('seed', $event)"></label>
        <button type="button" class="btn btn-primary" [disabled]="busy" (click)="generate()">{{ busy ? 'Working…' : 'Generate and rank locally' }}</button>
        <p *ngIf="error" role="alert">{{ error }}</p>
        <div *ngIf="generationResult as run">
          <h3>Generation stats</h3><pre>{{ run.generationSummary | json }}</pre>
          <p *ngIf="run.generationSummary.catalogExhausted">The finite recipe catalog was exhausted. Repeated engines remain visible as rejected duplicates.</p>
          <h3>Engine distribution</h3><p *ngFor="let family of run.engineDistribution | keyvalue">{{ family.key }}: {{ family.value }}</p>
          <p *ngIf="run.dominantEngineWarning">{{ run.dominantEngineWarning.reason }}</p>
          <p>Diversity {{ run.diversityScore }} · Seed {{ run.seed }} · {{ run.generatorVersion }}</p>
          <div *ngIf="run.generatorVersion === 'short-concept-generator-v2'">
            <h3>Batch diversity summary</h3><pre>{{ run.generationEvidence | json }}</pre>
            <h3>Object distribution</h3><pre>{{ run.objectCategoryDistribution | json }}</pre>
            <h3>Payoff distribution</h3><pre>{{ run.payoffDistribution | json }}</pre>
            <p *ngFor="let warning of run.concentrationWarnings">{{ warning.code }} · {{ warning.reason }}</p>
            <h3>Top 3 production slate</h3>
            <article *ngFor="let chosen of run.top3ProductionCandidates"><h4>{{ chosen.title }}</h4>
              <p>Raw rank {{ chosen.rawRank }} · Production slate rank {{ chosen.productionSlateRank }}</p>
              <p>{{ chosen.diversityAdjustmentReason }}</p>
            </article>
            <pre *ngFor="let idea of run.humanReadableTop3">{{ idea }}</pre>
            <p>V2 production selection uses creative tie signals and planned distance; the table below preserves raw accepted ranking.</p>
          </div>
          <details><summary>Generator diagnostics</summary><pre>{{ run.generatorMetrics | json }}</pre></details>
          <details><summary>Every attempt and its failure reasons</summary>
            <article *ngFor="let attempt of run.candidates"><strong>{{ attempt.candidate.title || attempt.candidateId }} · {{ attempt.disposition }}</strong><p>Generation Source {{ attempt.generationSource || attempt.candidate.generationSource || (run.generatorVersion === 'short-concept-generator-v1' ? 'DETERMINISTIC_V1' : 'DETERMINISTIC_V2') }}</p>
              <p *ngFor="let finding of attempt.failureReasons">{{ finding.code }} · {{ finding.reason }}</p>
              <p *ngIf="attempt.creativeDistanceSummary">Creative distance {{ attempt.creativeDistanceSummary.minimum }} · Engine similarity {{ attempt.creativeDistanceSummary.engineSimilarity }} · Visual silhouette similarity {{ attempt.creativeDistanceSummary.visualSilhouetteSimilarity }} · Raw rank {{ attempt.rawRank }} · Production slate rank {{ attempt.productionSlateRank }}</p>
              <div *ngIf="attempt.premiseNaturalness as premise">
                <p>Premise Naturalness {{ premise.premiseNaturalness }} · Goal Interference {{ premise.goalInterferenceType }} · Object Specificity {{ premise.objectSpecificityScore }} · Functional Irony {{ premise.functionalIrony }} · Physical Payoff Potential {{ premise.physicalPayoffPotential }} · Static-Frame Legibility {{ premise.staticFrameLegibility }}</p>
                <p>Expected: {{ premise.primaryExpectedBehaviors.join('; ') }}</p><p>{{ premise.whyThisObject }}</p><pre>{{ premise.flags | json }}</pre>
              </div>
              <div *ngIf="attempt.creativeShape as shape">
                <p>Story Shape {{ shape.shapeHash }} · Payoff Family {{ shape.payoffFamily }} · Final Relationship {{ shape.finalRelationship }}</p>
                <p>Template Shape Risk {{ attempt.templateShapeRisk?.risk }} · Historical Creative Territory Risk {{ attempt.historicalCreativeTerritory?.historicalCreativeTerritoryRisk }} · Shape Distance {{ attempt.closestBatchShape?.distance }}</p>
                <details><summary>Expand story shape evidence</summary><pre>{{ shape.dimensions | json }}</pre><pre>{{ attempt.historicalCreativeTerritory | json }}</pre></details>
              </div>
              <div *ngIf="attempt.beatGrammar as bg">
                <p>Strategy Diversity {{ bg.strategyDiversityScore }} · Consequence Diversity {{ bg.consequenceDiversityScore }} · Body Progression {{ bg.bodyStateProgressionScore }} · Payoff Distance {{ bg.payoffDistance }} · Beat Grammar Quality {{ bg.beatGrammarQuality }}</p>
                <details><summary>Expand structured beats</summary><article *ngFor="let beat of attempt.structuredBeatPlan">
                  <strong>Beat {{ beat.beatNumber }} · {{ beat.beatRole }}</strong><p>Strategy: {{ beat.characterStrategy }}</p><p>Consequence: {{ beat.characterConsequence }}</p><p>New information: {{ beat.newInformation.join(', ') }}</p>
                </article></details><pre>{{ bg.flags | json }}</pre>
              </div>
              <pre>{{ attempt.structuralFingerprint | json }}</pre>
            </article>
          </details>
          <details><summary>What should we make today?</summary><pre>{{ run.reportLines.join('\n') }}</pre></details>
        </div>
      </section>
      <section *ngIf="result as report" aria-label="Concept ranking results" class="card card-body">
        <h2>Produce first: {{ (generationResult?.generatorVersion === 'short-concept-generator-v2' ? generationResult.firstRenderCandidate : report.firstRenderCandidate) || 'None — revise supplied concepts' }}</h2>
        <p>Production slate: {{ (generationResult?.generatorVersion === 'short-concept-generator-v2' ? generationSlateNames() : slateNames(report)) || 'No eligible concepts' }}. Canonical and validator scores are preserved.</p>
        <p>Creative ranking score includes named penalties. Production efficiency breaks ties within anchored three-point bands; a lower score can therefore rank first.</p>
        <div class="table-responsive"><table class="table">
          <caption>Eligible concepts only · expand a row for source-backed ranking rationale</caption>
          <thead><tr><th>Rank</th><th>Concept</th><th>Score</th><th>Hook</th><th>Progress</th><th>Payoff</th><th>Duplicate Risk</th><th>Production Risk</th><th>Result</th></tr></thead>
          <tbody><ng-container *ngFor="let row of report.rankedEligibleCandidates">
            <tr><td>{{ row.rank }}</td><td>{{ row.title }} <small>{{ row.candidateId }}</small></td><td>{{ row.rankingScore }}<small>Short form {{ row.shortFormScore }}</small></td><td>{{ row.shortFormEngine.hookScore }}</td><td>{{ row.shortFormEngine.progressDensityScore }}</td><td>{{ row.shortFormEngine.payoffScore }}</td><td>{{ row.duplicateRisk }}</td><td>{{ row.productionRisk.flags.join(', ') || 'No screened flags' }}<small>Efficiency {{ row.productionEfficiency.score }}</small></td><td>{{ row.eligibility }}</td></tr>
            <tr><td colspan="9"><details><summary>Why rank {{ row.rank }} · {{ row.candidateId }}</summary>
              <p>{{ row.whyRankedHere.text }}</p>
              <ul><li *ngFor="let dimension of row.rankingDimensions">{{ dimension.dimension }}: {{ dimension.score }} · weight {{ dimension.weightPercent }}% · {{ dimension.source }}</li></ul>
              <p *ngFor="let penalty of row.penalties">{{ penalty.code }}: {{ penalty.points }} quality points · {{ penalty.scope }}</p>
              <p>Closest historical engine: {{ row.historicalComparison.closestHistoricalEngine || 'No supported match' }}. {{ row.historicalComparison.limitation }}</p>
              <pre>{{ row.historicalComparison | json }}</pre>
              <p>CPQ: {{ row.cpqPreview?.gradingStatus }}. No calibrated CPQ score is inferred.</p>
              <details><summary>Existing CPQ creative signals</summary><pre>{{ row.cpqPreview | json }}</pre></details>
              <pre>{{ row.normalizedConcept | json }}</pre>
            </details></td></tr>
          </ng-container></tbody>
        </table></div>
        <h3>Revision / excluded concepts</h3>
        <article *ngFor="let row of report.revisionCandidates"><strong>{{ row.candidateId }} · {{ row.title || 'Untitled' }} · INELIGIBLE</strong><ul><li *ngFor="let reason of row.eligibilityReasons">{{ reason.code }} · {{ reason.reason }}</li></ul></article>
        <h3>Diversity adjustments</h3><pre>{{ report.diversityAdjustments | json }}</pre>
        <details><summary>Production decision report</summary><pre>{{ report.reportLines.join('\n') }}</pre></details>
        <p *ngFor="let limitation of report.limitations">{{ limitation }}</p>
      </section>
    </main>`,
  styles: [`main{padding:1.5rem;max-width:1400px;margin:auto}.card{margin:1rem 0;padding:1rem}textarea{display:block;width:100%;font-family:monospace;margin:.7rem 0}small{display:block}table{width:100%;text-align:left}th,td{padding:.5rem;vertical-align:top} .evidence-loss{border-left:3px solid #b45f06;padding-left:.5rem}pre{white-space:pre-wrap;overflow-wrap:anywhere}.table-responsive{overflow:auto}`],
})
export class ConceptRankingPage implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly changes = inject(ChangeDetectorRef);
  private pending?: Subscription;
  batchText = '';
  busy = false;
  error = '';
  result: any = null;
  generationResult: any = null;
  evidenceReplay: any = null;
  evidenceBusy = false;
  evidenceError = '';
  private evidencePending?: Subscription;
  replayEvidence(): void {
    if (this.evidenceBusy) return;
    this.evidenceBusy = true; this.evidenceReplay = null; this.evidenceError = '';
    this.evidencePending = this.http.post<any>('/api/v1/intelligence/workflow/concepts/semantic/replay', {
      experimentId: 'semantic-live-v1-seed-42-count-40', semanticEvidenceAdapterVersion: 'v1', allowExternalGeneration: false,
    }).subscribe({
      next: report => {
        this.evidenceBusy = false;
        if (report?.workflow !== 'SEMANTIC_EVIDENCE_REPLAY') this.evidenceError = 'No usable stored evidence report returned.';
        else this.evidenceReplay = report;
        this.changes.markForCheck();
      },
      error: () => { this.evidenceBusy = false; this.evidenceError = 'Stored evidence reanalysis failed.'; this.changes.markForCheck(); },
    });
  }
  candidateCount = 20;
  generationSeed = 42;
  generatorVersion: 'v1' | 'v2' = 'v2';
  beatGrammarVersion: '' | 'v2' = '';
  generatorMode: 'deterministic' | 'semantic' | 'hybrid' = 'deterministic';
  useMockSemantic = false;
  modeChanged(value: 'deterministic' | 'semantic' | 'hybrid'): void { this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.generatorMode = value; if (value !== 'deterministic') this.generatorVersion = 'v2'; this.changes.markForCheck(); }
  mockChanged(value: boolean): void { this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.useMockSemantic = value; this.changes.markForCheck(); }
  creativeShapeVersion: '' | 'v1' = '';
  shapeVersionChanged(value: '' | 'v1'): void { this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.creativeShapeVersion = value; this.changes.markForCheck(); }
  premiseGateVersion: '' | 'v1' = '';
  premiseGateChanged(value: '' | 'v1'): void { this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.premiseGateVersion = value; if (!value) this.creativeShapeVersion = ''; this.changes.markForCheck(); }
  beatVersionChanged(value: '' | 'v2'): void { this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.beatGrammarVersion = value; if (!value) { this.premiseGateVersion = ''; this.creativeShapeVersion = ''; } this.changes.markForCheck(); }

  versionChanged(value: 'v1' | 'v2'): void {
    this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.generatorVersion = value; if (value === 'v1') { this.beatGrammarVersion = ''; this.premiseGateVersion = ''; this.creativeShapeVersion = ''; } this.changes.markForCheck();
  }

  sourceChanged(text: string): void {
    this.pending?.unsubscribe(); this.batchText = text; this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.changes.markForCheck();
  }
  generationChanged(field: 'count' | 'seed', value: number): void {
    this.pending?.unsubscribe(); this.busy = false; this.error = ''; this.result = null; this.generationResult = null; this.changes.markForCheck();
    if (field === 'count') this.candidateCount = value; else this.generationSeed = value;
  }
  generate(): void {
    if (this.busy) return;
    if (!Number.isInteger(this.candidateCount) || this.candidateCount < 10 || this.candidateCount > 100 || !Number.isInteger(this.generationSeed) || this.generationSeed < 0 || this.generationSeed > 2147483647) {
      this.error = 'Use 10–100 candidates and an integer seed from 0 to 2147483647.'; return;
    }
    this.busy = true; this.error = ''; this.result = null; this.generationResult = null; this.changes.markForCheck();
    this.pending = this.http.post<any>('/api/v1/intelligence/workflow/concepts/generate', { count: this.candidateCount, seed: this.generationSeed, duration: 15, rank: true, generatorVersion: this.generatorVersion, ...(this.beatGrammarVersion ? { beatGrammarVersion: this.beatGrammarVersion } : {}), ...(this.premiseGateVersion ? { premiseNaturalnessGateVersion: this.premiseGateVersion } : {}), ...(this.creativeShapeVersion ? { creativeShapeVersion: this.creativeShapeVersion } : {}), ...(this.generatorMode !== 'deterministic' ? { generatorMode: this.generatorMode, allowExternalGeneration: false, ...(this.useMockSemantic ? { semanticProvider: { provider: 'mock', model: 'fixture-v1' } } : {}) } : {}) }).subscribe({
      next: report => {
        this.busy = false;
        if (report?.workflow !== 'GENERATE_AND_RANK_SHORT_CONCEPTS') this.error = 'No usable local generation report returned.';
        else { this.generationResult = report; this.result = report.rankingResult; }
        this.changes.markForCheck();
      },
      error: () => { this.busy = false; this.error = 'Local generation failed. Check the configuration and canonical cast.'; this.changes.markForCheck(); },
    });
  }
  ngOnDestroy(): void { this.pending?.unsubscribe(); this.evidencePending?.unsubscribe(); }
  generationSlateNames(): string { return (this.generationResult?.top3ProductionCandidates ?? []).map((row: any) => row.candidateId).join(', '); }
  slateNames(report: any): string { return report.productionSlate.map((row: any) => row.candidateId).join(', '); }
  rank(): void {
    if (this.busy || !this.batchText.trim()) return;
    let candidates: any[];
    try {
      const source = this.batchText.trim();
      if (source.startsWith('{') || source.startsWith('[')) {
        const parsed = JSON.parse(source);
        candidates = Array.isArray(parsed) ? parsed : parsed.candidates ?? [parsed];
        if (parsed.candidates && Object.keys(parsed).some(key => key !== 'candidates')) throw new Error('Batch accepts only candidates.');
      } else candidates = source.split(/\n\s*---\s*\n/).filter(text => text.trim());
      if (!Array.isArray(candidates) || candidates.length < 1 || candidates.length > 30) throw new Error('Provide 1–30 supplied concepts.');
    } catch (error: any) { this.error = error.message || 'Invalid concept input.'; return; }
    this.busy = true; this.error = ''; this.result = null; this.generationResult = null; this.changes.markForCheck();
    this.pending = this.http.post<any>('/api/v1/intelligence/workflow/concepts/rank', { candidates }).subscribe({
      next: report => {
        this.busy = false;
        if (report?.workflow !== 'CONCEPT_CANDIDATE_RANKING') this.error = 'No usable concept ranking returned.';
        else this.result = report;
        this.changes.markForCheck();
      },
      error: response => {
        this.busy = false; this.error = typeof response.error?.detail === 'string' ? response.error.detail : 'Concept ranking failed. Check the input and validation service.';
        this.changes.markForCheck();
      },
    });
  }
}
