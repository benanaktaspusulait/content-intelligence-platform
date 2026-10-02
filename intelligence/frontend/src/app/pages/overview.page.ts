import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CreativeIntelligenceService, OverviewData } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-overview-page',
  imports: [RouterLink],
  template: `
    <header class="page-header"><div><span class="eyebrow">EVIDENCE WORKSPACE</span><h1>Overview</h1><p>Only persisted videos, predictions, and imported outcomes are shown.</p></div><a class="button button--primary" routerLink="/import"><span aria-hidden="true">＋</span> Import data</a></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading evidence</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Evidence unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else if (data(); as overview) {
      <section class="metric-strip" aria-label="Persisted record counts">
        <div><span>Videos</span><strong>{{ overview.videos.length }}</strong><small>Persisted records</small></div>
        <div><span>Predictions</span><strong>{{ overview.predictions.length }}</strong><small>All states</small></div>
        <div><span>Locked predictions</span><strong>{{ locked() }}</strong><small>Pre-registered</small></div>
        <div><span>Evaluated predictions</span><strong>{{ evaluated() }}</strong><small>Observed outcome attached</small></div>
      </section>

      <div class="dashboard-grid">
        <section class="section-band queue-panel"><div class="section-heading"><div><span class="eyebrow">VIDEO RECORDS</span><h2>Recently ingested</h2></div><a class="text-link" routerLink="/videos">Open library →</a></div>
          @if (!overview.videos.length) { <div class="state-panel compact-state"><strong>No videos ingested</strong><p>Add a video or ingest a directory to begin.</p></div> }
          @else { <div class="queue-list">@for (video of overview.videos.slice(0, 5); track video.id; let index = $index) { <div><span class="queue-index">{{ index + 1 }}</span><div><strong>{{ video.title }}</strong><small>{{ video.state }} · ingested {{ video.published }}</small></div></div> }</div> }
        </section>
        <section class="section-band reliability-panel"><div class="section-heading"><div><span class="eyebrow">PREDICTION LEDGER</span><h2>Current state</h2></div><a class="text-link" routerLink="/predictions">Open ledger →</a></div>
          @if (!overview.predictions.length) { <div class="state-panel compact-state"><strong>No predictions recorded</strong><p>Generate and lock a prediction before publishing.</p></div> }
          @else { <dl class="compact-facts"><div><dt>Draft</dt><dd>{{ drafts() }}</dd></div><div><dt>Locked</dt><dd>{{ locked() }}</dd></div><div><dt>Evaluated</dt><dd>{{ evaluated() }}</dd></div></dl> }
        </section>
      </div>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OverviewPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly data = signal<OverviewData | null>(null);
  protected readonly locked = computed(() => this.data()?.predictions.filter(item => item.state === 'LOCKED').length || 0);
  protected readonly drafts = computed(() => this.data()?.predictions.filter(item => item.state === 'DRAFT').length || 0);
  protected readonly evaluated = computed(() => this.data()?.predictions.filter(item => item.state === 'EVALUATED').length || 0);

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true); this.error.set('');
    this.service.getOverview().subscribe({
      next: data => { this.data.set(data); this.loading.set(false); },
      error: response => { this.error.set(response.error?.message || 'The evidence API did not respond.'); this.loading.set(false); },
    });
  }
}
