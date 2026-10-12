import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CreativeIntelligenceService, OperationalGuardSnapshot, ReachFurtherResearch, AcknowledgementView } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-performance-page',
  imports: [FormsModule],
  template: `
    <header class="page-header"><div><span class="eyebrow">OBSERVED OUTCOMES</span><h1>Performance</h1><p>Canonical research profiles built from persisted observations.</p></div><label class="compact-control">Platform<select [value]="platform()" (change)="platform.set(selectValue($event)); load()"><option value="facebook">Facebook</option><option value="instagram">Instagram</option><option value="tiktok">TikTok</option></select></label></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading performance evidence</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Performance unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else if (data(); as result) {
      <section class="metric-strip"><div><span>Observed videos</span><strong>{{ result.observedVideos }}</strong><small>Persisted cases</small></div><div><span>Median first observation</span><strong>{{ number(result.medianViewsAtFirstObservation) }}</strong><small>Views</small></div><div><span>Median 24h</span><strong>{{ number(result.median24hViews) }}</strong><small>Views</small></div><div><span>Median 7d</span><strong>{{ number(result.median7dViews) }}</strong><small>Views</small></div></section>
      @if (guards(); as guardSet) {
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">OPERATIONAL SIGNALS</span><h2>Distribution and retention health</h2></div><span class="status-badge">Descriptive only</span></div>
          @if (!guardSet.enabled || !guardSet.decisions.length) { <p class="muted">Insufficient evidence or operational guards are disabled.</p> }
          @else {
            <div class="metric-strip">@for (guard of guardSet.decisions; track guard.guardType) { <div><span>{{ readable(guard.guardType) }}</span><strong>{{ readable(guard.state) }}</strong><small>{{ guard.evidenceCount }} mature observations · {{ guard.scopeType.toLowerCase() }} scope</small>@if (guard.acknowledged) { <span class="status-badge" style="margin-left:0.5rem">Acknowledged</span> } @else if (guard.state === 'PUBLICATION_REVIEW_REQUIRED') { <button class="button button--compact" style="margin-left:0.5rem" type="button" (click)="showAcknowledgeForm(guard)">Acknowledge review</button> }</div> }</div>
            @if (acknowledgeFormGuard()) {
              <div class="state-panel" style="margin-top:1rem">
                <h3>Acknowledge {{ readable(acknowledgeFormGuard()!.guardType) }} review</h3>
                <p class="muted">Record that you have reviewed this signal. This does not block rendering or publication.</p>
                <form (ngSubmit)="submitAcknowledgement()">
                  <label>Notes<textarea [(ngModel)]="acknowledgeNotes" name="notes" rows="3" placeholder="Optional notes about your review"></textarea></label>
                  <label>Actor<input [(ngModel)]="acknowledgeActor" name="actor" placeholder="Your name or identifier" /></label>
                  <div style="display:flex;gap:0.5rem;margin-top:0.5rem">
                    <button class="button" type="submit" [disabled]="acknowledging()">Submit acknowledgement</button>
                    <button class="button button--secondary" type="button" (click)="cancelAcknowledgement()">Cancel</button>
                  </div>
                </form>
              </div>
            }
          }
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
  protected readonly acknowledgeFormGuard = signal<OperationalGuardSnapshot['decisions'][number] | null>(null);
  protected readonly acknowledging = signal(false);
  protected acknowledgeNotes = '';
  protected acknowledgeActor = 'anonymous';

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
  protected showAcknowledgeForm(guard: OperationalGuardSnapshot['decisions'][number]): void {
    this.acknowledgeFormGuard.set(guard);
    this.acknowledgeNotes = '';
    this.acknowledgeActor = 'anonymous';
  }
  protected cancelAcknowledgement(): void {
    this.acknowledgeFormGuard.set(null);
  }
  protected submitAcknowledgement(): void {
    const guard = this.acknowledgeFormGuard();
    if (!guard) return;
    this.acknowledging.set(true);
    this.service.acknowledgeGuardDecision(
      this.platform(),
      guard.id,
      this.acknowledgeNotes || null,
      this.acknowledgeActor || 'anonymous'
    ).subscribe({
      next: () => {
        this.acknowledging.set(false);
        this.acknowledgeFormGuard.set(null);
        this.load();
      },
      error: response => {
        this.acknowledging.set(false);
        this.error.set(response.error?.message || 'Acknowledgement failed.');
      },
    });
  }
}
