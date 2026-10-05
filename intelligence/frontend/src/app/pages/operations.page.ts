import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin } from 'rxjs';

interface PublicationJob { id: string; platform: string; status: string; title?: string; queuedAt?: string; completedAt?: string; }
interface ScheduledPublication { id: string; platform: string; status: string; title?: string; scheduledAt?: string; }
interface QaReview { id: string; decision?: string; decisionReason?: string; requiresHumanReview?: boolean; createdAt?: string; }
interface BudgetStatus { budgetLimit?: number; usedCredits?: number; remainingCredits?: number; level?: string; totalJobs?: number; }
interface NotificationRecord { id: string; title: string; message?: string; priority: string; isRead: boolean; createdAt: string; }
interface OperationalStatus { status: string; observedAt: string; renderJobs: Record<string, number>; }

@Component({
  selector: 'app-operations-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">RENDER SERVICE OPERATIONS</span><h1>Operations</h1><p>Read persisted publication, scheduling, QA and credit state. No action is implied by these records.</p></div></header>
    @if (loading()) { <section class="state-panel section-band"><span class="spinner"></span><strong>Loading operational state</strong></section> }
    @else if (error()) { <section class="state-panel state-panel--error section-band"><strong>Operational state unavailable</strong><p>{{ error() }}</p><button class="button button--secondary" type="button" (click)="load()">Retry</button></section> }
    @else {
      <section class="metric-strip" aria-label="Operational counts"><div><span>Render health</span><strong>{{ operational()?.status || '—' }}</strong><small>{{ operational()?.observedAt ? date(operational()!.observedAt) : 'No status snapshot' }}</small></div><div><span>Publications</span><strong>{{ publications().length }}</strong><small>Persisted publication jobs</small></div><div><span>Scheduled</span><strong>{{ scheduled().length }}</strong><small>Persisted schedules</small></div><div><span>QA review</span><strong>{{ reviews().length }}</strong><small>Pending review records</small></div><div><span>Credits</span><strong>{{ credits() }}</strong><small>{{ budget()?.level || 'Reported budget state' }}</small></div></section>
      <div class="dashboard-grid">
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PUBLICATION QUEUE</span><h2>Recent publication jobs</h2></div><span class="data-freshness">Persisted API records</span></div>@if (!publications().length) { <div class="state-panel compact-state"><strong>No publication jobs</strong><p>The render service has not recorded a publication job.</p></div> } @else { <table class="data-table"><thead><tr><th>Platform</th><th>Title</th><th>Status</th><th>Queued</th></tr></thead><tbody>@for (job of publications(); track job.id) {<tr><td>{{ job.platform }}</td><td>{{ job.title || 'Untitled publication' }}</td><td><span class="status-badge">{{ job.status }}</span></td><td>{{ date(job.queuedAt) }}</td></tr>}</tbody></table> }</section>
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">SCHEDULE</span><h2>Scheduled publications</h2></div><span class="data-freshness">Persisted API records</span></div>@if (!scheduled().length) { <div class="state-panel compact-state"><strong>No scheduled publications</strong><p>No schedule is currently recorded.</p></div> } @else { <table class="data-table"><thead><tr><th>Platform</th><th>Title</th><th>Status</th><th>Scheduled</th></tr></thead><tbody>@for (item of scheduled(); track item.id) {<tr><td>{{ item.platform }}</td><td>{{ item.title || 'Untitled publication' }}</td><td>{{ item.status }}</td><td>{{ date(item.scheduledAt) }}</td></tr>}</tbody></table> }</section>
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
  protected readonly notifications = signal<NotificationRecord[]>([]);
  protected readonly unreadCount = signal(0);
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
    }).subscribe({
      next: data => { this.publications.set(data.publications); this.scheduled.set(data.scheduled); this.reviews.set(data.reviews); this.budget.set(data.budget); this.notifications.set(data.notifications); this.unreadCount.set(data.notifications.filter(item => !item.isRead).length); this.operational.set(data.operational); this.loading.set(false); },
      error: response => { this.error.set(response.error?.detail || response.error?.message || 'The render service did not respond.'); this.loading.set(false); },
    });
  }

  protected number(value: number | undefined): string { return value === undefined ? '—' : new Intl.NumberFormat('en').format(value); }
  protected date(value: string | undefined): string { return value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'; }
  protected markRead(item: NotificationRecord): void { this.http.post(`/api/v1/notifications/${item.id}/read`, {}).subscribe({ next: () => { this.notifications.update(items => items.map(value => value.id === item.id ? { ...value, isRead: true } : value)); this.unreadCount.update(value => Math.max(0, value - 1)); }, error: response => this.error.set(response.error?.message || 'Notification could not be marked read.') }); }
  protected markAllRead(): void { this.http.post('/api/v1/notifications/read-all', {}).subscribe({ next: () => { this.notifications.update(items => items.map(item => ({ ...item, isRead: true }))); this.unreadCount.set(0); }, error: response => this.error.set(response.error?.message || 'Notifications could not be marked read.') }); }
}
