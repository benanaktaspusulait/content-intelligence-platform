import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

type ProductionRun = {
  runId: string;
  status: string;
  selectedCandidateId: string | null;
  candidateEvaluations: any[];
  characterReference: Record<string, any>;
  firstFrame: Record<string, any>;
  productionPrompt: Record<string, any>;
  modelConfiguration: Record<string, any>;
  validationEvidence: Record<string, any>;
  blockers: Array<{ code: string; detail: string }>;
  providerRequests: number;
  nextApplicationAction: string;
};

@Component({
  selector: 'app-autonomous-production',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="autonomous-page">
      <header>
        <p class="eyebrow">POMPOM HILLS · PRODUCTION</p>
        <h1>Generate a new video</h1>
        <p>Start one durable run. It selects an existing eligible story first, rechecks the existing creative gates, and prepares the next application stage.</p>
      </header>
      <section class="start-card">
        <div><strong>Bounded run defaults</strong><p>Existing candidates first · up to 1 first-frame generation · up to 1 video render · 0 automatic paid retries · Seedance 2.0 Mini · 9:16 · 14 seconds, 15 seconds maximum.</p></div>
        <button type="button" (click)="start()" [disabled]="busy()">{{ busy() ? 'Starting…' : run() ? 'Start another run' : 'Generate a new video' }}</button>
      </section>
      @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
      @if (run(); as current) {
        <section class="run-card" aria-live="polite">
          <div class="run-heading"><div><p class="eyebrow">RUN {{ current.runId }}</p><h2>{{ current.status.replaceAll('_', ' ') }}</h2></div><button type="button" class="secondary" (click)="refresh()" [disabled]="busy()">Refresh</button></div>
          @if (selected(); as item) {
            <h3>{{ item.candidate.title }}</h3>
            <p><strong>{{ item.candidate.protagonist }}</strong> wants to {{ item.candidate.everydayGoal }}. {{ item.candidate.impossibleRule }}</p>
            <p><strong>Frame zero:</strong> {{ item.candidate.frameZeroDescription }}</p>
            <h4>Stored timed beats</h4>
            <ol>@for (beat of item.candidate.beats; track beat.startSeconds) { <li><strong>{{ beat.startSeconds }}–{{ beat.endSeconds }}s</strong> {{ beat.description }}</li> }</ol>
            <div class="gate-summary">
              <p>Short Form {{ item.ranking.shortFormScore }} · Ranking {{ item.ranking.rankingScore }} · Beat Grammar {{ item.beatGrammar.beatGrammarQuality }} · Premise Naturalness {{ item.premiseNaturalness.premiseNaturalness }} · Creative Shape {{ item.creativeShape.payoffFamily }}</p>
              <p>Historical Territory {{ item.historicalTerritory.historicalCreativeTerritoryRisk }}; evidence scope is the current frozen comparison set.</p>
            </div>
          } @else { <p>No candidate passed the current selection policy.</p> }
          <h4>Run gates</h4>
          <ul>@for (blocker of current.blockers; track blocker.code) { <li><strong>{{ blocker.code }}</strong> — {{ blocker.detail }}</li> }</ul>
          <p><strong>Character reference:</strong> {{ current.characterReference['status'] }} @if (current.characterReference['path']) { · {{ current.characterReference['path'] }} · SHA-256 {{ current.characterReference['sha256'] }} }</p>
          <p><strong>First frame:</strong> {{ current.firstFrame['status'] }} · <strong>Production prompt:</strong> {{ current.productionPrompt['status'] }}</p>
          <p><strong>Provider requests:</strong> {{ current.providerRequests }}. This start action never makes a provider call.</p>
          <p class="next-action">{{ current.nextApplicationAction }}</p>
        </section>
      }
    </main>
  `,
  styles: [`
    :host{display:block}.autonomous-page{max-width:1000px;margin:0 auto;padding:2rem;color:#18241c}header{margin-bottom:1.5rem}.eyebrow{font-size:.7rem;letter-spacing:.12em;font-weight:800;color:#57755b;margin:.2rem 0}.autonomous-page h1{font-size:2rem;margin:.35rem 0}.autonomous-page h2{font-size:1.3rem;margin:.3rem 0}.autonomous-page h3{margin:1rem 0 .5rem}.autonomous-page p{line-height:1.55}.start-card,.run-card{border:1px solid #d9e1d6;border-radius:12px;background:#fff;padding:1.2rem;margin:1rem 0}.start-card{display:flex;align-items:center;justify-content:space-between;gap:1rem;background:#f6f8f4}.start-card p{margin:.4rem 0 0;color:#526356}.autonomous-page button{border:0;border-radius:8px;background:#315b3a;color:white;font-weight:750;padding:.75rem 1rem;cursor:pointer;white-space:nowrap}.autonomous-page button:disabled{opacity:.55;cursor:wait}.autonomous-page button.secondary{background:#e8eee6;color:#29482f}.run-heading{display:flex;justify-content:space-between;align-items:center;gap:1rem}.run-card ol{padding-left:1.4rem}.run-card li{padding:.35rem 0;line-height:1.5}.gate-summary{padding:.6rem .8rem;background:#f6f8f4;border-radius:8px}.run-card ul{padding-left:1.25rem}.run-card li{margin:.45rem 0;line-height:1.45}.next-action{padding:.75rem;background:#fff7df;border-left:4px solid #d4a335}.error{color:#9c2727;background:#fff0ef;padding:.8rem;border-radius:8px}@media(max-width:650px){.start-card{align-items:stretch;flex-direction:column}.autonomous-page{padding:1rem}}
  `],
})
export class AutonomousProductionPage {
  private readonly http = inject(HttpClient);
  readonly run = signal<ProductionRun | null>(null);
  readonly busy = signal(false);
  readonly error = signal('');

  selected(): any | null {
    const current = this.run();
    return current?.candidateEvaluations?.find(row => row.candidateId === current.selectedCandidateId) ?? null;
  }

  start(): void {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    const idempotencyKey = globalThis.crypto?.randomUUID?.() ?? `production-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    this.http.post<ProductionRun>('/api/v1/intelligence/autonomous-production/runs', {}, {
      headers: new HttpHeaders({ 'Idempotency-Key': idempotencyKey }),
    }).subscribe({
      next: value => { this.run.set(value); this.busy.set(false); },
      error: error => { this.error.set(error?.error?.detail ?? error?.message ?? 'Production run could not start.'); this.busy.set(false); },
    });
  }

  refresh(): void {
    const current = this.run();
    if (!current || this.busy()) return;
    this.busy.set(true); this.error.set('');
    this.http.get<ProductionRun>(`/api/v1/intelligence/autonomous-production/runs/${current.runId}`).subscribe({
      next: value => { this.run.set(value); this.busy.set(false); },
      error: error => { this.error.set(error?.error?.detail ?? error?.message ?? 'Production run could not refresh.'); this.busy.set(false); },
    });
  }
}
