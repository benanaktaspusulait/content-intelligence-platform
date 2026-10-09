import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { forkJoin } from 'rxjs';

interface PublicationJob { id: string; platform: string; status: string; title?: string; queuedAt?: string; completedAt?: string; startedAt?: string; errorMessage?: string; platformPostId?: string; postUrl?: string; }
interface ScheduledPublication { id: string; platform: string; status: string; title?: string; scheduledAt?: string; cancellationRequestedAt?: string; }
export const enabledPublicationPlatforms = ['TIKTOK', 'YOUTUBE'] as const;
export function isPublicationPlatformEnabled(platform: string): boolean {
  return (enabledPublicationPlatforms as readonly string[]).includes(platform);
}
interface QaReview { id: string; decision?: string; decisionReason?: string; requiresHumanReview?: boolean; createdAt?: string; }
interface BudgetStatus { budgetLimit?: number; usedCredits?: number; remainingCredits?: number; level?: string; totalJobs?: number; }
interface NotificationRecord { id: string; title: string; message?: string; priority: string; isRead: boolean; createdAt: string; }
interface OperationalStatus { status: string; observedAt: string; renderJobs: Record<string, number>; publicationStatus?: string; }
interface ServiceHealth { status: string; message?: string; }

@Component({
  selector: 'app-operations-page',
  imports: [FormsModule],
  template: `
    <header class="page-header"><div><span class="eyebrow">RENDER SERVICE OPERATIONS</span><h1>Operations</h1><p>Read persisted publication, scheduling, QA and credit state. No action is implied by these records.</p></div></header>
    <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PUBLICATION ACTIONS</span><h2>Queue or schedule an approved asset</h2></div><span class="data-freshness">Existing publication API</span></div><div class="dashboard-grid"><form class="compact-form" (submit)="queuePublication($event)"><label>Render asset ID<input name="queueAssetId" [(ngModel)]="queueForm.renderAssetId" required placeholder="UUID" /></label><label>Platform<select name="queuePlatform" [(ngModel)]="queueForm.platform"><option value="TIKTOK">TikTok</option><option value="YOUTUBE">YouTube</option></select></label><label>Platform account ID<input name="queueAccount" [(ngModel)]="queueForm.platformAccountId" placeholder="Configured account ID" /></label><label>Title<input name="queueTitle" [(ngModel)]="queueForm.title" /></label><label>Caption<textarea name="queueCaption" [(ngModel)]="queueForm.caption" rows="3"></textarea></label><label>Hashtags<input name="queueHashtags" [(ngModel)]="queueForm.hashtags" placeholder="#PompomHills" /></label><button class="button button--primary" type="submit" [disabled]="actionId() === 'queue'">{{ actionId() === 'queue' ? 'Queueing…' : 'Queue publication' }}</button></form><form class="compact-form" (submit)="schedulePublication($event)"><label>Render asset ID<input name="scheduleAssetId" [(ngModel)]="scheduleForm.renderAssetId" required placeholder="UUID" /></label><label>Platform<select name="schedulePlatform" [(ngModel)]="scheduleForm.platform"><option value="TIKTOK">TikTok</option><option value="YOUTUBE">YouTube</option></select></label><label>Platform account ID<input name="scheduleAccount" [(ngModel)]="scheduleForm.platformAccountId" placeholder="Configured account ID" /></label><label>Schedule time<input name="scheduledAt" type="datetime-local" [(ngModel)]="scheduleForm.scheduledAt" required /></label><label>Timezone<input name="timezone" [(ngModel)]="scheduleForm.timezone" required /></label><label>Title<input name="scheduleTitle" [(ngModel)]="scheduleForm.title" /></label><label>Caption<textarea name="scheduleCaption" [(ngModel)]="scheduleForm.caption" rows="3"></textarea></label><button class="button button--secondary" type="submit" [disabled]="actionId() === 'schedule'">{{ actionId() === 'schedule' ? 'Scheduling…' : 'Schedule publication' }}</button></form></div></section>
    @if (loading()) { <section class="state-panel section-band"><span class="spinner"></span><strong>Loading operational state</strong></section> }
    @else if (error()) { <section class="state-panel state-panel--error section-band"><strong>Operational state unavailable</strong><p>{{ error() }}</p><button class="button button--secondary" type="button" (click)="load()">Retry</button></section> }
    @else {
      <section class="metric-strip" aria-label="Operational counts"><div><span>Render health</span><strong>{{ operational()?.status || '—' }}</strong><small>{{ operational()?.observedAt ? date(operational()!.observedAt) : 'No status snapshot' }}</small></div><div><span>Publication safety</span><strong>{{ operational()?.publicationStatus || '—' }}</strong><small>Meta publishing remains fail-closed by default</small></div><div><span>Publications</span><strong>{{ publications().length }}</strong><small>Persisted publication jobs</small></div><div><span>Scheduled</span><strong>{{ scheduled().length }}</strong><small>Persisted schedules</small></div><div><span>QA review</span><strong>{{ reviews().length }}</strong><small>Pending review records</small></div><div><span>Credits</span><strong>{{ credits() }}</strong><small>{{ budget()?.level || 'Reported budget state' }}</small></div></section>
      <section class="section-band"><div class="section-heading"><div><span class="eyebrow">SERVICE HEALTH</span><h2>Workflow dependencies</h2></div><span class="data-freshness">Read-only health checks</span></div><div class="compact-facts"><div><strong>Render service</strong><span>{{ operational()?.status || 'UNKNOWN' }}</span></div><div><strong>ML quality service</strong><span>{{ qualityHealth()?.status || 'UNKNOWN' }}</span></div></div>@if (qualityHealth()?.message) { <p class="muted">{{ qualityHealth()?.message }}</p> }</section>
      <div class="dashboard-grid">
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PUBLICATION QUEUE</span><h2>Recent publication jobs</h2></div><span class="data-freshness">Persisted API records</span></div>@if (!publications().length) { <div class="state-panel compact-state"><strong>No publication jobs</strong><p>The render service has not recorded a publication job.</p></div> } @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Platform</th><th>Title</th><th>Status</th><th>Queued</th><th>Result</th><th></th></tr></thead><tbody>@for (job of publications(); track job.id) {<tr><td>{{ job.platform }}</td><td><strong>{{ job.title || 'Untitled publication' }}</strong><small>{{ job.id }}</small></td><td><span class="status-badge">{{ job.status }}</span>@if (job.errorMessage) {<small class="error-text">{{ job.errorMessage }}</small>}</td><td>{{ date(job.queuedAt) }}</td><td>@if (job.postUrl) { <a [href]="job.postUrl" target="_blank" rel="noreferrer">Open post</a> } @else { {{ job.platformPostId || '—' }} }</td><td>@if (canCancelPublication(job)) { <button class="button button--compact" type="button" [disabled]="actionId() === job.id" (click)="cancelPublication(job)">{{ actionId() === job.id ? 'Cancelling…' : 'Cancel' }}</button> }</td></tr>}</tbody></table></div> }</section>
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">SCHEDULE</span><h2>Scheduled publications</h2></div><span class="data-freshness">Persisted API records</span></div>@if (!scheduled().length) { <div class="state-panel compact-state"><strong>No scheduled publications</strong><p>No schedule is currently recorded.</p></div> } @else { <table class="data-table"><thead><tr><th>Platform</th><th>Title</th><th>Status</th><th>Scheduled</th><th></th></tr></thead><tbody>@for (item of scheduled(); track item.id) {<tr><td>{{ item.platform }}</td><td>{{ item.title || 'Untitled publication' }}</td><td>{{ item.status }}</td><td>{{ date(item.scheduledAt) }}</td><td>@if (canCancelSchedule(item)) { <button class="button button--compact" type="button" [disabled]="actionId() === item.id" (click)="cancelSchedule(item)">{{ actionId() === item.id ? 'Cancelling…' : 'Cancel' }}</button> }</td></tr>}</tbody></table> }</section>
      </div>
      <section class="section-band"><div class="section-heading"><div><span class="eyebrow">NOTIFICATIONS</span><h2>In-app notifications</h2></div><button class="button button--compact" type="button" [disabled]="!unreadCount()" (click)="markAllRead()">{{ unreadCount() ? 'Mark all read' : 'All read' }}</button></div>@if (!notifications().length) { <div class="state-panel compact-state"><strong>No notifications</strong><p>The render service has not persisted any notification records.</p></div> } @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Priority</th><th>Notification</th><th>Created</th><th></th></tr></thead><tbody>@for (item of notifications(); track item.id) {<tr><td>{{ item.priority }}</td><td><strong>{{ item.title }}</strong><small>{{ item.message || '—' }}</small></td><td>{{ date(item.createdAt) }}</td><td>@if (!item.isRead) { <button class="button button--compact" type="button" (click)="markRead(item)">Mark read</button> } @else { <span class="muted">Read</span> }</td></tr>}</tbody></table></div> }</section>
      <div class="dashboard-grid">
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">HUMAN QA</span><h2>Pending review</h2></div><span class="data-freshness">Decision endpoint remains protected</span></div>@if (!reviews().length) { <div class="state-panel compact-state"><strong>No pending review records</strong><p>Nothing is waiting for human QA.</p></div> } @else { <table class="data-table"><thead><tr><th>Review ID</th><th>Decision</th><th>Reason</th><th>Created</th></tr></thead><tbody>@for (item of reviews(); track item.id) {<tr><td><code>{{ item.id }}</code></td><td>{{ item.decision || 'PENDING' }}</td><td>{{ item.decisionReason || 'No decision recorded' }}</td><td>{{ date(item.createdAt) }}</td></tr>}</tbody></table> }</section>
      <section class="section-band"><div class="section-heading"><div><span class="eyebrow">CREDITS</span><h2>Budget status</h2></div><span class="data-freshness">Reported by render service</span></div><dl class="compact-facts"><div><dt>Budget limit</dt><dd>{{ number(budget()?.budgetLimit) }}</dd></div><div><dt>Used credits</dt><dd>{{ number(budget()?.usedCredits) }}</dd></div><div><dt>Remaining credits</dt><dd>{{ number(budget()?.remainingCredits) }}</dd></div><div><dt>Level</dt><dd>{{ budget()?.level || '—' }}</dd></div><div><dt>Total jobs</dt><dd>{{ number(budget()?.totalJobs) }}</dd></div></dl></section>
      </div>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OperationsPage {
  private readonly http = inject(HttpClient);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly publications = signal<PublicationJob[]>([]);
  protected readonly scheduled = signal<ScheduledPublication[]>([]);
  protected readonly reviews = signal<QaReview[]>([]);
  protected readonly budget = signal<BudgetStatus | null>(null);
  protected readonly operational = signal<OperationalStatus | null>(null);
  protected readonly qualityHealth = signal<ServiceHealth | null>(null);
  protected readonly notifications = signal<NotificationRecord[]>([]);
  protected readonly unreadCount = signal(0);
  protected readonly actionId = signal<string | null>(null);
  protected queueForm = { renderAssetId: '', platform: 'TIKTOK', platformAccountId: '', title: '', caption: '', hashtags: '' };
  protected scheduleForm = { renderAssetId: '', platform: 'TIKTOK', platformAccountId: '', scheduledAt: '', timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', title: '', caption: '' };
  protected readonly credits = () => this.budget()?.remainingCredits ?? '—';

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true); this.error.set('');
    forkJoin({
      publications: this.http.get<PublicationJob[]>('/api/v1/publications'),
      scheduled: this.http.get<ScheduledPublication[]>('/api/v1/scheduled'),
      reviews: this.http.get<QaReview[]>('/api/v1/qa/reviews/pending'),
      budget: this.http.get<BudgetStatus>('/api/v1/budget/status'),
      notifications: this.http.get<NotificationRecord[]>('/api/v1/notifications'),
      operational: this.http.get<OperationalStatus>('/api/v1/operational/status'),
      qualityHealth: this.http.get<ServiceHealth>('/api/quality/health'),
    }).subscribe({
      next: data => { this.publications.set(data.publications); this.scheduled.set(data.scheduled); this.reviews.set(data.reviews); this.budget.set(data.budget); this.notifications.set(data.notifications); this.unreadCount.set(data.notifications.filter(item => !item.isRead).length); this.operational.set(data.operational); this.qualityHealth.set(data.qualityHealth); this.loading.set(false); },
      error: response => { this.error.set(response.error?.detail || response.error?.message || 'The render service did not respond.'); this.loading.set(false); },
    });
  }

  protected number(value: number | undefined): string { return value === undefined ? '—' : new Intl.NumberFormat('en').format(value); }
  protected date(value: string | undefined): string { return value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'; }
  protected canCancelPublication(job: PublicationJob): boolean { return ['QUEUED', 'UPLOADING', 'PROCESSING'].includes(job.status); }
  protected canCancelSchedule(item: ScheduledPublication): boolean { return !['COMPLETED', 'CANCELLED', 'FAILED'].includes(item.status); }
  protected cancelPublication(job: PublicationJob): void {
    this.actionId.set(job.id);
    this.http.post(`/api/v1/publications/${job.id}/cancel`, {}).subscribe({ next: () => { this.actionId.set(null); this.load(); }, error: response => { this.actionId.set(null); this.error.set(response.error?.message || 'Publication could not be cancelled.'); } });
  }
  protected cancelSchedule(item: ScheduledPublication): void {
    this.actionId.set(item.id);
    this.http.delete(`/api/v1/scheduled/${item.id}`).subscribe({ next: () => { this.actionId.set(null); this.load(); }, error: response => { this.actionId.set(null); this.error.set(response.error?.message || 'Schedule could not be cancelled.'); } });
  }
  protected queuePublication(event: Event): void { event.preventDefault(); if (!isPublicationPlatformEnabled(this.queueForm.platform)) { this.error.set('This platform is disabled for publication.'); return; } this.actionId.set('queue'); this.http.post('/api/v1/publications/queue', { ...this.queueForm, isPrivate: false }).subscribe({ next: () => { this.actionId.set(null); this.queueForm = { ...this.queueForm, renderAssetId: '', title: '', caption: '', hashtags: '' }; this.load(); }, error: response => { this.actionId.set(null); this.error.set(response.error?.message || 'Publication could not be queued.'); } }); }
  protected schedulePublication(event: Event): void { event.preventDefault(); if (!isPublicationPlatformEnabled(this.scheduleForm.platform)) { this.error.set('This platform is disabled for publication.'); return; } this.actionId.set('schedule'); const scheduledAt = new Date(this.scheduleForm.scheduledAt).toISOString(); this.http.post('/api/v1/scheduled', { ...this.scheduleForm, scheduledAt, isPrivate: false }).subscribe({ next: () => { this.actionId.set(null); this.scheduleForm = { ...this.scheduleForm, renderAssetId: '', scheduledAt: '', title: '', caption: '' }; this.load(); }, error: response => { this.actionId.set(null); this.error.set(response.error?.message || 'Schedule could not be created.'); } }); }
  protected markRead(item: NotificationRecord): void { this.http.post(`/api/v1/notifications/${item.id}/read`, {}).subscribe({ next: () => { this.notifications.update(items => items.map(value => value.id === item.id ? { ...value, isRead: true } : value)); this.unreadCount.update(value => Math.max(0, value - 1)); }, error: response => this.error.set(response.error?.message || 'Notification could not be marked read.') }); }
  protected markAllRead(): void { this.http.post('/api/v1/notifications/read-all', {}).subscribe({ next: () => { this.notifications.update(items => items.map(item => ({ ...item, isRead: true }))); this.unreadCount.set(0); }, error: response => this.error.set(response.error?.message || 'Notifications could not be marked read.') }); }
}
