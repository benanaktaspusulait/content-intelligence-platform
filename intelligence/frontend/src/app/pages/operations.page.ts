import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin } from 'rxjs';

interface PublicationJob { id: string; platform: string; status: string; title?: string; queuedAt?: string; completedAt?: string; }
interface ScheduledPublication { id: string; platform: string; status: string; title?: string; scheduledAt?: string; }
interface QaReview { id: string; decision?: string; decisionReason?: string; requiresHumanReview?: boolean; createdAt?: string; }
interface BudgetStatus { monthlyLimit?: number; monthlyUsed?: number; remainingCredits?: number; status?: string; }

@Component({
  selector: 'app-operations-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">RENDER SERVICE OPERATIONS</span><h1>Operations</h1><p>Read persisted publication, scheduling, QA and credit state. No action is implied by these records.</p></div></header>
    @if (loading()) { <section class="state-panel section-band"><span class="spinner"></span><strong>Loading operational state</strong></section> }
    @else if (error()) { <section class="state-panel state-panel--error section-band"><strong>Operational state unavailable</strong><p>{{ error() }}</p><button class="button button--secondary" type="button" (click)="load()">Retry</button></section> }
    @else {
      <section class="metric-strip" aria-label="Operational counts"><div><span>Publications</span><strong>{{ publications().length }}</strong><small>Persisted publication jobs</small></div><div><span>Scheduled</span><strong>{{ scheduled().length }}</strong><small>Persisted schedules</small></div><div><span>QA review</span><strong>{{ reviews().length }}</strong><small>Pending review records</small></div><div><span>Credits</span><strong>{{ credits() }}</strong><small>{{ budget()?.status || 'Reported budget state' }}</small></div></section>
      <div class="dashboard-grid">
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PUBLICATION QUEUE</span><h2>Recent publication jobs</h2></div><span class="data-freshness">Persisted API records</span></div>@if (!publications().length) { <div class="state-panel compact-state"><strong>No publication jobs</strong><p>The render service has not recorded a publication job.</p></div> } @else { <table class="data-table"><thead><tr><th>Platform</th><th>Title</th><th>Status</th><th>Queued</th></tr></thead><tbody>@for (job of publications(); track job.id) {<tr><td>{{ job.platform }}</td><td>{{ job.title || 'Untitled publication' }}</td><td><span class="status-badge">{{ job.status }}</span></td><td>{{ date(job.queuedAt) }}</td></tr>}</tbody></table> }</section>
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">SCHEDULE</span><h2>Scheduled publications</h2></div><span class="data-freshness">Persisted API records</span></div>@if (!scheduled().length) { <div class="state-panel compact-state"><strong>No scheduled publications</strong><p>No schedule is currently recorded.</p></div> } @else { <table class="data-table"><thead><tr><th>Platform</th><th>Title</th><th>Status</th><th>Scheduled</th></tr></thead><tbody>@for (item of scheduled(); track item.id) {<tr><td>{{ item.platform }}</td><td>{{ item.title || 'Untitled publication' }}</td><td>{{ item.status }}</td><td>{{ date(item.scheduledAt) }}</td></tr>}</tbody></table> }</section>
      </div>
      <div class="dashboard-grid">
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">HUMAN QA</span><h2>Pending review</h2></div><span class="data-freshness">Decision endpoint remains protected</span></div>@if (!reviews().length) { <div class="state-panel compact-state"><strong>No pending review records</strong><p>Nothing is waiting for human QA.</p></div> } @else { <table class="data-table"><thead><tr><th>Review ID</th><th>Decision</th><th>Reason</th><th>Created</th></tr></thead><tbody>@for (item of reviews(); track item.id) {<tr><td><code>{{ item.id }}</code></td><td>{{ item.decision || 'PENDING' }}</td><td>{{ item.decisionReason || 'No decision recorded' }}</td><td>{{ date(item.createdAt) }}</td></tr>}</tbody></table> }</section>
        <section class="section-band"><div class="section-heading"><div><span class="eyebrow">CREDITS</span><h2>Budget status</h2></div><span class="data-freshness">Reported by render service</span></div><dl class="compact-facts"><div><dt>Monthly limit</dt><dd>{{ number(budget()?.monthlyLimit) }}</dd></div><div><dt>Monthly used</dt><dd>{{ number(budget()?.monthlyUsed) }}</dd></div><div><dt>Remaining credits</dt><dd>{{ number(budget()?.remainingCredits) }}</dd></div><div><dt>Status</dt><dd>{{ budget()?.status || '—' }}</dd></div></dl></section>
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
  protected readonly credits = () => this.budget()?.remainingCredits ?? '—';

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true); this.error.set('');
    forkJoin({
      publications: this.http.get<PublicationJob[]>('/api/v1/publications'),
      scheduled: this.http.get<ScheduledPublication[]>('/api/v1/scheduled'),
      reviews: this.http.get<QaReview[]>('/api/v1/qa/reviews/pending'),
      budget: this.http.get<BudgetStatus>('/api/v1/budget/status'),
    }).subscribe({
      next: data => { this.publications.set(data.publications); this.scheduled.set(data.scheduled); this.reviews.set(data.reviews); this.budget.set(data.budget); this.loading.set(false); },
      error: response => { this.error.set(response.error?.detail || response.error?.message || 'The render service did not respond.'); this.loading.set(false); },
    });
  }

  protected number(value: number | undefined): string { return value === undefined ? '—' : new Intl.NumberFormat('en').format(value); }
  protected date(value: string | undefined): string { return value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'; }
}
