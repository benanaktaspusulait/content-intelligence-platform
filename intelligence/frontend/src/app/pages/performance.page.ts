import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, OperationalGuardSnapshot, ReachFurtherResearch } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-performance-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">OBSERVED OUTCOMES</span><h1>Performance</h1><p>Canonical research profiles built from persisted observations.</p></div><label class="compact-control">Platform<select [value]="platform()" (change)="platform.set(selectValue($event)); load()"><option value="facebook">Facebook</option><option value="instagram">Instagram</option><option value="tiktok">TikTok</option></select></label></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading performance evidence</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Performance unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else if (data(); as result) {
      <section class="metric-strip"><div><span>Observed videos</span><strong>{{ result.observedVideos }}</strong><small>Persisted cases</small></div><div><span>Median first observation</span><strong>{{ number(result.medianViewsAtFirstObservation) }}</strong><small>Views</small></div><div><span>Median 24h</span><strong>{{ number(result.median24hViews) }}</strong><small>Views</small></div><div><span>Median 7d</span><strong>{{ number(result.median7dViews) }}</strong><small>Views</small></div></section>
      @if (guards(); as guardSet) {
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">OPERATIONAL SIGNALS</span><h2>Distribution and retention health</h2></div><span class="status-badge">Descriptive only</span></div>
          @if (!guardSet.enabled || !guardSet.decisions.length) { <p class="muted">Insufficient evidence or operational guards are disabled.</p> }
          @else { <div class="metric-strip">@for (guard of guardSet.decisions; track guard.guardType) { <div><span>{{ readable(guard.guardType) }}</span><strong>{{ readable(guard.state) }}</strong><small>{{ guard.evidenceCount }} mature observations · {{ guard.scopeType.toLowerCase() }} scope</small></div> }</div> }
          <p class="muted">These signals support review and do not block rendering, quarantine assets, or make causal claims.</p>
        </section>
      }
      <section class="section-band"><div class="section-heading"><div><span class="eyebrow">OBSERVATION PROFILES</span><h2>Video cases</h2></div><span class="status-badge">{{ platform() }}</span></div>@if (!result.cases.length) { <div class="state-panel compact-state"><strong>No performance evidence</strong><p>The API returned no persisted cases for this platform.</p></div> } @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Video</th><th>First observed</th><th>Latest views</th><th>Trajectory</th><th>Band</th><th>Source state</th></tr></thead><tbody>@for (item of result.cases; track item.videoId) { <tr><td><strong>{{ item.video }}</strong><small>{{ item.videoId }}</small></td><td>{{ date(item.firstObservedAt) }}</td><td class="numeric">{{ number(item.current?.views) }}</td><td>{{ readable(item.trajectoryType) }}</td><td><span class="status-badge">{{ readable(item.performanceBand) }}</span></td><td>{{ item.observations.length }} observations</td></tr> }</tbody></table></div> }</section>
      <p class="muted">{{ result.disclaimer }}</p>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PerformancePage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly platform = signal('facebook');
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly data = signal<ReachFurtherResearch | null>(null);
  protected readonly guards = signal<OperationalGuardSnapshot | null>(null);
  constructor() { this.load(); }
  protected load(): void {
    this.loading.set(true); this.error.set('');
    this.service.getPerformanceResearch(this.platform()).subscribe({ next: value => { this.data.set(value); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The performance API did not respond.'); this.loading.set(false); } });
    this.service.getOperationalGuards(this.platform()).subscribe({ next: value => this.guards.set(value), error: () => this.guards.set(null) });
  }
  protected selectValue(event: Event): string { return (event.target as HTMLSelectElement).value; }
  protected number(value: number | null | undefined): string { return value === null || value === undefined ? '—' : new Intl.NumberFormat('en').format(value); }
  protected date(value: string | null): string { return value ? new Date(value).toLocaleDateString() : '—'; }
  protected readable(value: string): string { return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()); }
}
