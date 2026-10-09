import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MetaReadService } from '../core/meta-read.service';
import { MetaConnection, MetaPageContent, MetaPageInsights } from '../core/meta-read.models';

interface OAuthNotice {
  message: string;
  isError: boolean;
}

const OAUTH_NOTICES: Record<string, OAuthNotice> = {
  connected: { message: 'Meta authorization completed. The connection below reflects the newly authorized account.', isError: false },
  not_managed: { message: 'The authenticated user does not manage the configured Facebook Page.', isError: true },
  denied: { message: 'Meta authorization was not completed.', isError: true },
  invalid_state: { message: 'The authorization request could not be verified. Please try connecting again.', isError: true },
  missing_code: { message: 'Meta did not return an authorization code.', isError: true },
  failed: { message: 'The Meta authorization request could not be completed.', isError: true },
  not_configured: { message: 'Meta OAuth is not configured in this environment.', isError: true },
};

@Component({
  selector: 'app-meta-connection-page',
  imports: [RouterLink],
  template: `
    <header class="page-header">
      <div>
        <span class="eyebrow">META READ-ONLY</span>
        <h1>Meta Connection</h1>
        <p>Verifies read-only access to the configured Facebook Page and Instagram Professional Account. No publishing capability is requested or exposed.</p>
      </div>
      <div class="header-actions">
        <a class="button button--primary" href="/api/v1/meta/oauth/start">Connect Meta Account</a>
        <button class="button button--compact" type="button" [disabled]="loading()" (click)="reload()">
          {{ loading() ? 'Checking…' : 'Re-check' }}
        </button>
      </div>
    </header>

    @if (oauthNotice(); as notice) {
      <div class="context-banner" [class.state-panel--error]="notice.isError"><span>META OAUTH</span><strong>{{ notice.message }}</strong></div>
    }

    @if (loading()) {
      <section class="section-band" aria-live="polite"><span class="spinner"></span><strong>Validating Meta connection</strong></section>
    } @else if (error()) {
      <div class="state-panel state-panel--error"><strong>Connection check unavailable</strong><p>{{ error() }}</p></div>
    } @else if (connection(); as data) {
      <section class="section-band">
        <div>
          <span class="eyebrow">STATUS</span>
          <h2>
            <span class="status-badge" [class.status-badge--green]="data.connected" [class.status-badge--amber]="data.status === 'DEGRADED'">{{ statusLabel(data.status) }}</span>
          </h2>
          <p>{{ data.message }}</p>
          <small>API {{ data.apiVersion }} · {{ data.lastValidatedAt ? ('Validated ' + formatTime(data.lastValidatedAt)) : 'Not yet validated' }}</small>
        </div>
      </section>

      <section class="table-shell">
        <div class="data-table-scroll">
          <table class="data-table">
            <thead><tr><th>Account</th><th>Identifier</th><th>Detail</th></tr></thead>
            <tbody>
              <tr>
                <td><strong>Facebook Page</strong></td>
                <td class="tabular">{{ data.page?.id || '—' }}</td>
                <td>
                  {{ data.page ? (data.page.name + ' · ' + data.page.category) : 'Not available' }}
                  @if (data.pageManagementVerification === 'VERIFIED') {
                    <div><small>Management verification: <span class="status-badge status-badge--green">VERIFIED</span></small></div>
                  } @else if (data.pageManagementVerification === 'NOT_VERIFIED') {
                    <div><small>Management verification: <span class="status-badge status-badge--amber">NOT VERIFIED</span></small></div>
                  } @else {
                    <div><small>Management verification: <span class="status-badge">UNAVAILABLE</span></small></div>
                  }
                </td>
              </tr>
              <tr>
                <td><strong>Instagram Account</strong></td>
                <td class="tabular">{{ data.instagramAccount?.id || '—' }}</td>
                <td>{{ instagramDetail(data) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="table-shell">
        <div class="data-table-scroll">
          <table class="data-table">
            <thead><tr><th>Required permission</th><th>Status</th><th>Detail</th></tr></thead>
            <tbody>
              @for (permission of data.requiredPermissions; track permission.permission) {
                <tr>
                  <td class="source-path">{{ permission.permission }}</td>
                  <td><span class="status-badge" [class.status-badge--green]="permission.status === 'AVAILABLE'" [class.status-badge--amber]="permission.status === 'UNAVAILABLE'">{{ permission.status }}</span></td>
                  <td>{{ permission.message }}</td>
                </tr>
              }
              @for (permission of data.optionalPermissions; track permission.permission) {
                <tr>
                  <td class="source-path">{{ permission.permission }} <small>(optional)</small></td>
                  <td><span class="status-badge">{{ permission.status }}</span></td>
                  <td>{{ permission.message }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>

      @if (insightsGap()) {
        <div class="context-banner"><span>PERMISSION PENDING</span><strong>Insights metrics will appear once instagram_manage_insights is granted.</strong><p>Until then, reach and interaction values are shown as unavailable, never as zero.</p></div>
      }

      <section class="section-band">
        <div>
          <span class="eyebrow">pages_read_engagement</span>
          <h2>Recent Page Content</h2>
          <p>Read-only view of content published by the connected Facebook Page. This app reads Page content only; it never creates, edits, or deletes posts.</p>
        </div>
      </section>

      @if (pageContentLoading()) {
        <section class="section-band" aria-live="polite"><span class="spinner"></span><strong>Loading recent Page content</strong></section>
      } @else if (pageContentError()) {
        <div class="state-panel state-panel--error"><strong>Page content unavailable</strong><p>{{ pageContentError() }}</p><button class="button button--secondary" type="button" (click)="loadPageContent()">Retry Page content</button></div>
      } @else if (pageContent(); as content) {
        @if (content.availability === 'UNAVAILABLE') {
          <div class="state-panel"><strong>Page content unavailable</strong><p>{{ content.unavailableReason || 'Facebook Page content could not be read.' }}</p></div>
        } @else if (content.posts.length === 0) {
          <div class="state-panel"><strong>No recent posts</strong><p>The connected Page has no recent published content to display.</p></div>
        } @else {
          <section class="table-shell">
            <div class="data-table-scroll">
              <table class="data-table">
                <thead><tr><th>Post</th><th>Published</th><th><span class="sr-only">Link</span></th></tr></thead>
                <tbody>
                  @for (post of content.posts; track post.id) {
                    <tr>
                      <td><strong>{{ postText(post.message) }}</strong></td>
                      <td>{{ post.publishedAt ? formatTime(post.publishedAt) : '—' }}</td>
                      <td>@if (post.permalinkUrl) { <a [href]="post.permalinkUrl" target="_blank" rel="noopener noreferrer">View on Facebook ↗</a> }</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        }
      }

      @if (pageInsights(); as insights) {
        <section class="section-band">
          <div><span class="eyebrow">PAGE INSIGHTS · READ ONLY</span><h2>Facebook Page analytics</h2><p>Live values and durable snapshot count from the connected Page.</p></div>
          <div class="comparison-groups">
            @for (entry of insightEntries(insights.metrics); track entry[0]) { <div><span>{{ entry[0] }}</span><strong>{{ entry[1] }}</strong></div> }
            <div><span>Snapshots</span><strong>{{ insights.snapshots.length }}</strong></div>
          </div>
        </section>
      }

      <section class="section-band">
        <div>
          <span class="eyebrow">NEXT</span>
          <h2>Browse Reels</h2>
          <p>Open the read-only Instagram Reels list to review published content and capture analytics snapshots.</p>
        </div>
        <a class="button button--primary" routerLink="/meta/reels">Open Instagram Reels</a>
      </section>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MetaConnectionPage {
  private readonly service = inject(MetaReadService);
  private readonly route = inject(ActivatedRoute);
  protected readonly oauthNotice = signal<OAuthNotice | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly connection = signal<MetaConnection | null>(null);
  protected readonly pageContent = signal<MetaPageContent | null>(null);
  protected readonly pageContentLoading = signal(false);
  protected readonly pageContentError = signal('');
  protected readonly pageInsights = signal<MetaPageInsights | null>(null);
  protected readonly insightsGap = computed(() => {
    const data = this.connection();
    if (!data) return false;
    return data.requiredPermissions.some(
      permission => permission.permission === 'instagram_manage_insights' && permission.status !== 'AVAILABLE',
    );
  });

  constructor() {
    const status = this.route.snapshot.queryParamMap.get('meta_oauth');
    if (status && OAUTH_NOTICES[status]) {
      this.oauthNotice.set(OAUTH_NOTICES[status]);
    }
    this.reload();
  }

  protected reload(): void {
    this.loading.set(true);
    this.error.set('');
    this.service.getConnection().subscribe({
      next: data => {
        this.connection.set(data);
        this.loading.set(false);
        this.loadPageContent();
        // Keep the connection screen resilient when an older injected read client is present.
        const insightsReader = (this.service as Partial<MetaReadService>).getPageInsights;
        if (typeof insightsReader === 'function') {
          insightsReader.call(this.service, data.page?.id).subscribe({ next: insights => this.pageInsights.set(insights), error: () => this.pageInsights.set(null) });
        } else {
          this.pageInsights.set(null);
        }
      },
      error: response => {
        this.loading.set(false);
        this.error.set(response.error?.message || 'The Meta connection could not be validated.');
      },
    });
  }

  protected insightEntries(metrics: Record<string, number>): Array<[string, number]> {
    return Object.entries(metrics);
  }

  protected loadPageContent(): void {
    this.pageContentLoading.set(true); this.pageContentError.set('');
    this.service.getPageContent().subscribe({
      next: content => {
        this.pageContent.set(content);
        this.pageContentLoading.set(false);
      },
      error: response => {
        this.pageContent.set(null);
        this.pageContentError.set(response.error?.message || 'The configured Facebook Page content could not be read.');
        this.pageContentLoading.set(false);
      },
    });
  }

  protected postText(message: string | null): string {
    const text = message?.trim();
    if (!text) return 'Media post (no caption)';
    return text.length > 90 ? text.slice(0, 87) + '…' : text;
  }

  protected statusLabel(status: MetaConnection['status']): string {
    switch (status) {
      case 'CONNECTED': return 'Connected';
      case 'DEGRADED': return 'Partially available';
      case 'NOT_CONFIGURED': return 'Not configured';
      default: return 'Unavailable';
    }
  }

  protected instagramDetail(data: MetaConnection): string {
    const account = data.instagramAccount;
    if (!account) return 'Not available';
    const parts = [account.username ? '@' + account.username : null, account.accountType];
    if (account.mediaCount !== null) parts.push(account.mediaCount + ' media');
    return parts.filter(Boolean).join(' · ');
  }

  protected formatTime(value: string): string {
    return new Date(value).toLocaleString();
  }
}
