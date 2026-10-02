import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MetaReadService } from '../core/meta-read.service';
import { MetaReelSummary } from '../core/meta-read.models';

@Component({
  selector: 'app-meta-reels-page',
  imports: [RouterLink],
  template: `
    <header class="page-header">
      <div>
        <span class="eyebrow">META READ-ONLY</span>
        <h1>Instagram Reels</h1>
        <p>Read-only list of published media on the connected Instagram account. Each entry shows whether it maps to a local video record.</p>
      </div>
      <a class="button button--compact" routerLink="/meta/connection">Connection</a>
    </header>

    @if (error()) {
      <div class="state-panel state-panel--error"><strong>Reels unavailable</strong><p>{{ error() }}</p></div>
    }

    <section class="table-shell">
      @if (loading() && reels().length === 0) {
        <div class="state-panel"><span class="spinner"></span><strong>Loading Instagram media</strong></div>
      } @else if (reels().length === 0) {
        <div class="state-panel"><strong>No media found</strong><p>The connected account returned no published media.</p></div>
      } @else {
        <div class="data-table-scroll">
          <table class="data-table">
            <thead><tr><th>Media</th><th>Type</th><th>Published</th><th>Local match</th><th><span class="sr-only">Actions</span></th></tr></thead>
            <tbody>
              @for (reel of reels(); track reel.mediaId) {
                <tr>
                  <td>
                    <strong>{{ caption(reel) }}</strong>
                    <small class="tabular">{{ reel.mediaId }}</small>
                  </td>
                  <td>{{ reel.mediaProductType || reel.mediaType || '—' }}</td>
                  <td>{{ reel.publishedAt ? formatDate(reel.publishedAt) : '—' }}</td>
                  <td>
                    <span class="status-badge"
                          [class.status-badge--green]="reel.localMatch.status === 'EXACT'"
                          [class.status-badge--amber]="reel.localMatch.status === 'AMBIGUOUS' || reel.localMatch.status === 'CONFLICT'">
                      {{ matchLabel(reel) }}
                    </span>
                  </td>
                  <td><a class="button button--compact" [routerLink]="['/meta/reels', reel.mediaId]">Analytics</a></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        @if (hasMore()) {
          <div class="load-more-row">
            <button class="button button--compact" type="button" [disabled]="loading()" (click)="loadMore()">
              {{ loading() ? 'Loading…' : 'Load more' }}
            </button>
          </div>
        }
      }
    </section>
  `,
  styles: [`.load-more-row{display:flex;justify-content:center;padding:1rem}`],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MetaReelsPage {
  private readonly service = inject(MetaReadService);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly reels = signal<MetaReelSummary[]>([]);
  protected readonly hasMore = signal(false);
  private cursor: string | null = null;

  constructor() {
    this.load(null);
  }

  protected loadMore(): void {
    this.load(this.cursor);
  }

  private load(after: string | null): void {
    this.loading.set(true);
    this.error.set('');
    this.service.listReels(after).subscribe({
      next: page => {
        this.reels.update(current => after ? [...current, ...page.reels] : page.reels);
        this.cursor = page.nextCursor;
        this.hasMore.set(page.hasMore);
        this.loading.set(false);
      },
      error: response => {
        this.loading.set(false);
        this.error.set(
          response.status === 503
            ? 'Meta read-only analytics is not configured in this environment.'
            : response.error?.message || 'Instagram media could not be loaded.',
        );
      },
    });
  }

  protected caption(reel: MetaReelSummary): string {
    const text = reel.caption?.trim();
    if (!text) return 'Untitled media';
    return text.length > 80 ? text.slice(0, 77) + '…' : text;
  }

  protected matchLabel(reel: MetaReelSummary): string {
    switch (reel.localMatch.status) {
      case 'EXACT': return 'Matched';
      case 'AMBIGUOUS': return 'Ambiguous';
      case 'CONFLICT': return 'Conflict';
      default: return 'Unmatched';
    }
  }

  protected formatDate(value: string): string {
    return new Date(value).toLocaleString();
  }
}
