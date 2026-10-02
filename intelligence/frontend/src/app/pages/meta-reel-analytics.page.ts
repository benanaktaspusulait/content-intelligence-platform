import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MetaReadService } from '../core/meta-read.service';
import { MetaReelAnalytics } from '../core/meta-read.models';

@Component({
  selector: 'app-meta-reel-analytics-page',
  imports: [RouterLink],
  template: `
    <header class="page-header">
      <div>
        <span class="eyebrow">META READ-ONLY</span>
        <h1>Reel Analytics</h1>
        <p>Live read-only metrics plus the append-only history of captured snapshots. Metrics the platform does not report are shown as unavailable, never zero.</p>
      </div>
      <a class="button button--compact" routerLink="/meta/reels">Back to Reels</a>
    </header>

    @if (loading()) {
      <section class="section-band" aria-live="polite"><span class="spinner"></span><strong>Loading analytics</strong></section>
    } @else if (error()) {
      <div class="state-panel state-panel--error"><strong>Analytics unavailable</strong><p>{{ error() }}</p></div>
    } @else if (analytics(); as data) {
      <section class="section-band">
        <div>
          <span class="eyebrow">MEDIA</span>
          <h2>{{ caption(data) }}</h2>
          <p class="tabular">{{ data.mediaId }} · {{ data.mediaProductType || data.mediaType || 'media' }}</p>
          <small>
            {{ data.publishedAt ? ('Published ' + formatDate(data.publishedAt)) : 'Publish date unavailable' }} ·
            <span class="status-badge"
                  [class.status-badge--green]="data.localMatch.status === 'EXACT'"
                  [class.status-badge--amber]="data.localMatch.status === 'AMBIGUOUS' || data.localMatch.status === 'CONFLICT'">
              {{ matchLabel(data) }}
            </span>
          </small>
          @if (data.permalink) { <p><a [href]="data.permalink" target="_blank" rel="noopener noreferrer">View on Instagram ↗</a></p> }
        </div>
      </section>

      <section class="section-band">
        <div>
          <span class="eyebrow">LIVE METRICS</span>
          <h2><span class="status-badge" [class.status-badge--green]="data.availability === 'AVAILABLE'" [class.status-badge--amber]="data.availability === 'PARTIAL' || data.availability === 'UNAVAILABLE'">{{ data.availability }}</span></h2>
          @if (data.unavailableReason) { <p>{{ data.unavailableReason }}</p> }
        </div>
        <div class="metric-strip">
          <div class="metric"><span>Views</span><strong>{{ metric(data.live.views) }}</strong></div>
          <div class="metric"><span>Reach</span><strong>{{ metric(data.live.reach) }}</strong></div>
          <div class="metric"><span>Shares</span><strong>{{ metric(data.live.shares) }}</strong></div>
          <div class="metric"><span>Saved</span><strong>{{ metric(data.live.saved) }}</strong></div>
          <div class="metric"><span>Interactions</span><strong>{{ metric(data.live.totalInteractions) }}</strong></div>
        </div>
        <button class="button button--primary" type="button" [disabled]="capturing()" (click)="capture()">
          {{ capturing() ? 'Capturing…' : 'Capture snapshot' }}
        </button>
      </section>

      @if (notice()) { <div class="context-banner"><span>SNAPSHOT</span><strong>{{ notice() }}</strong></div> }

      <section class="table-shell">
        <div><span class="eyebrow">HISTORY</span><h2>Captured snapshots</h2></div>
        @if (data.history.length === 0) {
          <div class="state-panel"><strong>No snapshots yet</strong><p>Capture a snapshot to begin an append-only metrics history for this media.</p></div>
        } @else {
          <div class="data-table-scroll">
            <table class="data-table">
              <thead><tr><th>Captured</th><th>Availability</th><th>Views</th><th>Reach</th><th>Shares</th><th>Saved</th><th>Interactions</th></tr></thead>
              <tbody>
                @for (snapshot of data.history; track snapshot.observationId) {
                  <tr>
                    <td>{{ snapshot.measuredAt ? formatDate(snapshot.measuredAt) : '—' }}</td>
                    <td><span class="status-badge" [class.status-badge--green]="snapshot.availability === 'AVAILABLE'" [class.status-badge--amber]="snapshot.availability === 'PARTIAL' || snapshot.availability === 'UNAVAILABLE'">{{ snapshot.availability }}</span></td>
                    <td class="tabular">{{ metric(snapshot.metrics.views) }}</td>
                    <td class="tabular">{{ metric(snapshot.metrics.reach) }}</td>
                    <td class="tabular">{{ metric(snapshot.metrics.shares) }}</td>
                    <td class="tabular">{{ metric(snapshot.metrics.saved) }}</td>
                    <td class="tabular">{{ metric(snapshot.metrics.totalInteractions) }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </section>
    }
  `,
  styles: [`.metric-strip{display:flex;flex-wrap:wrap;gap:1rem;margin:1rem 0}.metric{min-width:7rem}.metric span{display:block;font-size:.75rem;text-transform:uppercase;opacity:.7}.metric strong{font-size:1.4rem}`],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MetaReelAnalyticsPage {
  private readonly service = inject(MetaReadService);
  private readonly route = inject(ActivatedRoute);
  protected readonly loading = signal(true);
  protected readonly capturing = signal(false);
  protected readonly error = signal('');
  protected readonly notice = signal('');
  protected readonly analytics = signal<MetaReelAnalytics | null>(null);
  private readonly mediaId = this.route.snapshot.paramMap.get('mediaId') ?? '';

  constructor() {
    this.reload();
  }

  protected capture(): void {
    if (!this.mediaId) return;
    this.capturing.set(true);
    this.notice.set('');
    this.error.set('');
    this.service.captureSnapshot(this.mediaId).subscribe({
      next: result => {
        this.capturing.set(false);
        this.notice.set(
          result.persisted
            ? `Snapshot captured (${result.availability}). History updated below.`
            : `Snapshot already recorded for this collection run (${result.availability}).`,
        );
        this.reload();
      },
      error: response => {
        this.capturing.set(false);
        this.error.set(response.error?.message || 'The snapshot could not be captured.');
      },
    });
  }

  private reload(): void {
    if (!this.mediaId) {
      this.loading.set(false);
      this.error.set('No media identifier was provided.');
      return;
    }
    this.loading.set(true);
    this.service.getAnalytics(this.mediaId).subscribe({
      next: data => {
        this.analytics.set(data);
        this.loading.set(false);
      },
      error: response => {
        this.loading.set(false);
        this.error.set(
          response.status === 503
            ? 'Meta read-only analytics is not configured in this environment.'
            : response.error?.message || 'Analytics could not be loaded.',
        );
      },
    });
  }

  protected metric(value: number | null): string {
    return value === null || value === undefined ? 'Unavailable' : new Intl.NumberFormat('en').format(value);
  }

  protected caption(data: MetaReelAnalytics): string {
    const text = data.caption?.trim();
    if (!text) return 'Untitled media';
    return text.length > 90 ? text.slice(0, 87) + '…' : text;
  }

  protected matchLabel(data: MetaReelAnalytics): string {
    switch (data.localMatch.status) {
      case 'EXACT': return 'Matched to local video';
      case 'AMBIGUOUS': return 'Ambiguous match';
      case 'CONFLICT': return 'Conflicting match';
      default: return 'Unmatched';
    }
  }

  protected formatDate(value: string): string {
    return new Date(value).toLocaleString();
  }
}
