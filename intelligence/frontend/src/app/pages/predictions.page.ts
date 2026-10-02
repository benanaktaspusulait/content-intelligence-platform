import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, PredictionRecord } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-predictions-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">PRE-REGISTRATION LEDGER</span><h1>Predictions</h1><p>Lock expectations before outcomes arrive. Uncertainty stays visible.</p></div><button class="button button--primary" type="button"><span aria-hidden="true">＋</span> New prediction</button></header>
    <div class="segmented-control" role="group" aria-label="Prediction state filter"><button type="button" [class.is-selected]="filter() === 'ALL'" (click)="filter.set('ALL')">All <span>{{ records().length }}</span></button><button type="button" [class.is-selected]="filter() === 'LOCKED'" (click)="filter.set('LOCKED')">Locked</button><button type="button" [class.is-selected]="filter() === 'DRAFT'" (click)="filter.set('DRAFT')">Draft</button></div>
    <section class="ledger-summary"><div><span>Total predictions</span><strong>{{ records().length }}</strong><small>Persisted records</small></div><div><span>Locked</span><strong>{{ lockedCount() }}</strong><small>Pre-registered</small></div><div><span>Small-sample flags</span><strong class="amber-text">{{ smallSampleCount() }}</strong><small>n &lt; 80 observations</small></div></section>
    <section class="table-shell">@if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading predictions</strong></div> } @else if (error()) { <div class="state-panel state-panel--error"><strong>Predictions unavailable</strong><p>{{ error() }}</p></div> } @else if (!visible().length) { <div class="state-panel"><strong>No predictions in this view</strong><p>No persisted records match the selected state.</p></div> } @else { <div class="data-table-scroll"><table class="data-table prediction-table"><thead><tr><th>Prediction</th><th>State</th><th>Platform</th><th class="numeric">Expected completion</th><th>80% interval</th><th class="numeric">Sample</th><th>Model</th><th>Locked</th><th></th></tr></thead><tbody>
      @for (item of visible(); track item.id) { <tr><td><strong>{{ item.video }}</strong><small>{{ item.id }}</small></td><td><span class="status-badge" [class.status-badge--green]="item.state === 'LOCKED'" [class.status-badge--amber]="item.state === 'DRAFT'">{{ item.state }}</span></td><td><span class="platform-cell"><i class="platform-dot" [class.instagram]="item.platform === 'Instagram'" [class.youtube]="item.platform === 'YouTube'" [class.tiktok]="item.platform === 'TikTok'"></i>{{ item.platform }}</span></td><td class="numeric forecast-value"><strong>{{ item.predicted === null ? '—' : item.predicted + '%' }}</strong></td><td><div class="interval-cell"><span>{{ item.range }}</span>@if (item.predicted !== null) { <i><b [style.left.%]="item.predicted"></b></i> }</div></td><td class="numeric tabular"><span [class.sample-warning]="item.sample < 80">{{ item.sample }}</span></td><td class="tabular">{{ item.model }}</td><td>{{ item.lockedAt }}</td><td><button class="icon-button table-action" type="button" title="Inspect prediction" aria-label="Inspect prediction">↗</button></td></tr> }
    </tbody></table></div> }</section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PredictionsPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly records = signal<PredictionRecord[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly filter = signal<'ALL' | 'LOCKED' | 'DRAFT'>('ALL');
  protected readonly visible = computed(() => this.filter() === 'ALL' ? this.records() : this.records().filter(item => item.state === this.filter()));
  protected readonly lockedCount = computed(() => this.records().filter(item => item.state === 'LOCKED').length);
  protected readonly smallSampleCount = computed(() => this.records().filter(item => item.sample < 80).length);
  constructor() { this.service.getPredictions().subscribe({ next: data => { this.records.set(data.records); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The evidence API did not respond.'); this.loading.set(false); } }); }
}
