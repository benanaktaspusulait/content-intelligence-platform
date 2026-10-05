import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';

interface Candidate { id: string; proposedRuleName: string; proposedRuleKey: string; evidenceLevel: string; riskTier: string; status: string; supportingObservationCount: number; }
interface Health { ruleKey: string; rulesetVersion: string; status: string; currentSupportingSampleSize: number; supportTrend?: string; }
interface Evidence { id: string; evidenceType: string; evidenceLevel: string; metric?: string; sampleSize: number; observedEffect?: number; analysisMethod?: string; analysisVersion?: string; }
interface Conflict { id: string; conflictingRuleKey: string; conflictType: string; overridePolicy: string; resolutionStatus: string; }
interface Review { id: string; decision: string; reviewer: string; reason?: string; resultingAction?: string; createdAt?: string; }
interface HistoryItem { rulesetVersion?: string; status?: string; parentRulesetVersion?: string; proposedRulesetVersion?: string; generatedAt?: string; activatedAt?: string; activatedBy?: string; }

@Component({
  selector: 'app-rule-governance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="page-header"><div><span class="eyebrow">GOVERNED POLICY</span><h1>Rule Governance</h1><p>Review evidence-backed rule candidates before a new immutable ruleset release.</p></div></header>
    <section class="access-panel">
      <label>Tenant <input [(ngModel)]="tenantId" placeholder="tenant-id" autocomplete="off"></label>
      <label>Governance token <input [(ngModel)]="token" type="password" placeholder="operator token" autocomplete="off"></label>
      <label>Reviewer <input [(ngModel)]="reviewer" placeholder="reviewer identity" autocomplete="off"></label>
      <label>Review note <input [(ngModel)]="reviewNote" placeholder="reason for decision" autocomplete="off"></label>
      <label>Parent ruleset <input [(ngModel)]="parentRuleset" placeholder="v1" autocomplete="off"></label>
      <label>New ruleset <input [(ngModel)]="newRuleset" placeholder="v2" autocomplete="off"></label>
      <label>Decision <select [(ngModel)]="reviewDecision"><option value="APPROVE">Approve</option><option value="REJECT">Reject</option><option value="REQUEST_MORE_EVIDENCE">Request more evidence</option><option value="REQUIRE_EXPERIMENT">Require experiment</option><option value="SUPERSEDE_EXISTING_RULE">Supersede existing rule</option></select></label>
      <button class="button button--primary" type="button" (click)="load()" [disabled]="loading()">{{ loading() ? 'Loading...' : 'Load governance state' }}</button>
    </section>
    @if (error()) { <div class="error-state">{{ error() }}</div> }
    <section class="governance-grid">
      <article class="panel"><div class="panel-heading"><div><span class="eyebrow">REVIEW QUEUE</span><h2>Rule candidates</h2></div><span class="count">{{ candidates().length }}</span></div>
        @if (!loaded()) { <p class="muted">Authenticate to load persisted candidates.</p> }
        @else if (!candidates().length) { <p class="muted">No governed candidates found.</p> }
        @else { @for (candidate of candidates(); track candidate.id) { <div class="candidate-row"><div><strong>{{ candidate.proposedRuleName }}</strong><small>{{ candidate.proposedRuleKey }} · {{ candidate.evidenceLevel }} · {{ candidate.supportingObservationCount }} observations</small></div><div class="candidate-actions"><span class="status" [class]="'status status--' + candidate.status.toLowerCase()">{{ candidate.status }}</span><button class="button button--compact" type="button" (click)="inspect(candidate)">Inspect</button>@if (candidate.status === 'PROPOSED' || candidate.status === 'NEEDS_MORE_EVIDENCE') { <button class="button button--compact" type="button" [disabled]="actionLoading() === candidate.id" (click)="qualify(candidate.id)">{{ actionLoading() === candidate.id ? 'Checking…' : 'Qualify' }}</button> } @if (candidate.status === 'READY_FOR_REVIEW') { <button class="button button--compact" type="button" [disabled]="actionLoading() === candidate.id" (click)="review(candidate.id)">{{ actionLoading() === candidate.id ? 'Saving…' : 'Review' }}</button> } @if (candidate.status === 'APPROVED') { <button class="button button--compact" type="button" [disabled]="actionLoading() === candidate.id" (click)="activate(candidate.id)">{{ actionLoading() === candidate.id ? 'Activating…' : 'Activate' }}</button> }</div></div> } }
      </article>
      <article class="panel"><div class="panel-heading"><div><span class="eyebrow">REVALIDATION</span><h2>Rule health</h2></div><span class="count">{{ health().length }}</span></div>
        @if (!health().length) { <p class="muted">No health records found.</p> }
        @else { @for (item of health(); track item.ruleKey + item.rulesetVersion) { <div class="candidate-row"><div><strong>{{ item.ruleKey }}</strong><small>Ruleset {{ item.rulesetVersion }} · n={{ item.currentSupportingSampleSize }}</small></div><span class="status">{{ item.status }}</span></div> } }
      </article>
      <article class="panel"><div class="panel-heading"><div><span class="eyebrow">RULESET HISTORY</span><h2>Versions and changesets</h2></div><span class="count">{{ rulesets().length + changesets().length }}</span></div>
        @if (!rulesets().length && !changesets().length) { <p class="muted">No ruleset history found.</p> }
        @else { @for (item of rulesets(); track item.rulesetVersion) { <div class="candidate-row"><div><strong>{{ item.rulesetVersion }}</strong><small>{{ item.status }} · parent {{ item.parentRulesetVersion || '—' }}</small></div><span class="status">{{ item.activatedAt ? 'Activated' : 'Recorded' }}</span></div> } @for (item of changesets(); track item.proposedRulesetVersion) { <div class="candidate-row"><div><strong>{{ item.proposedRulesetVersion || 'Changeset' }}</strong><small>{{ item.status }} · parent {{ item.parentRulesetVersion || '—' }}</small></div><span class="status">{{ item.activatedAt ? 'Activated' : 'Draft' }}</span></div> } }
      </article>
    </section>
    @if (selected(); as candidate) { <section class="panel detail-panel"><div class="panel-heading"><div><span class="eyebrow">EVIDENCE LINEAGE</span><h2>{{ candidate.proposedRuleName }}</h2></div><button class="button button--compact" type="button" (click)="selected.set(null)">Close</button></div><p class="muted">{{ candidate.proposedRuleKey }} · {{ candidate.evidenceLevel }} · {{ candidate.status }}</p><h3>Supporting evidence</h3>@if (!evidence().length) { <p class="muted">No evidence records returned.</p> } @else { @for (item of evidence(); track item.id) { <div class="candidate-row"><div><strong>{{ item.evidenceType }} · {{ item.evidenceLevel }}</strong><small>{{ item.metric || 'No metric' }} · n={{ item.sampleSize }} · {{ item.analysisMethod || 'Unknown method' }}</small></div><span class="status">{{ item.observedEffect ?? '—' }}</span></div> } }<h3>Conflicts and reviews</h3>@if (!conflicts().length && !reviews().length) { <p class="muted">No conflicts or reviews returned.</p> } @else { @for (item of conflicts(); track item.id) { <div class="candidate-row"><div><strong>{{ item.conflictingRuleKey }}</strong><small>{{ item.conflictType }} · {{ item.overridePolicy }}</small></div><span class="status">{{ item.resolutionStatus }}</span></div> } @for (item of reviews(); track item.id) { <div class="candidate-row"><div><strong>{{ item.decision }}</strong><small>{{ item.reviewer }} · {{ item.reason || 'No reason' }}</small></div><span class="status">{{ item.createdAt || 'Recorded' }}</span></div> } }</section> }
  `,
  styles: [`
    :host { display:block; padding:32px clamp(20px,4vw,56px); color:#17202a; }
    .page-header { margin-bottom:24px; } h1 { margin:4px 0 8px; font-size:34px; } .page-header p { color:#66727d; }
    .eyebrow { color:#7b5cff; font-size:11px; font-weight:800; letter-spacing:.12em; }
    .access-panel { display:flex; align-items:end; gap:14px; flex-wrap:wrap; padding:18px; background:#fff; border:1px solid #e3e7ec; border-radius:8px; margin-bottom:20px; }
    label { display:grid; gap:6px; color:#596572; font-size:12px; font-weight:700; } input { min-width:220px; padding:10px 12px; border:1px solid #ccd3da; border-radius:6px; font:inherit; }
    .button { border:0; border-radius:6px; padding:11px 16px; font-weight:800; cursor:pointer; } .button--primary { background:#17202a; color:#fff; }
    .governance-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:20px; } .panel { background:#fff; border:1px solid #e3e7ec; border-radius:8px; padding:20px; min-height:220px; }
    .panel-heading { display:flex; justify-content:space-between; align-items:start; border-bottom:1px solid #edf0f3; padding-bottom:14px; margin-bottom:4px; } h2 { margin:4px 0 0; font-size:20px; } .count { font-size:24px; font-weight:800; }
    .candidate-row { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:14px 0; border-bottom:1px solid #edf0f3; } .candidate-row strong { display:block; } .candidate-row small { display:block; color:#75818d; margin-top:4px; } .candidate-actions { display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:end; }
    .detail-panel { margin-top:20px; } .detail-panel h3 { margin:20px 0 4px; font-size:15px; }
    .status { white-space:nowrap; font-size:11px; font-weight:800; padding:5px 8px; border-radius:999px; background:#eef2f5; } .status--ready_for_review { background:#fff1c7; } .status--approved { background:#d9f5e6; } .muted { color:#75818d; } .error-state { color:#a52626; background:#fff0f0; padding:12px; margin-bottom:20px; border-radius:6px; }
    @media (max-width: 800px) { .governance-grid { grid-template-columns:1fr; } .access-panel { align-items:stretch; flex-direction:column; } input { min-width:0; } }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RuleGovernancePage {
  private readonly http = inject(HttpClient);
  protected tenantId = '';
  protected token = '';
  protected reviewer = '';
  protected reviewNote = '';
  protected reviewDecision = 'APPROVE';
  protected parentRuleset = '';
  protected newRuleset = '';
  protected readonly candidates = signal<Candidate[]>([]);
  protected readonly health = signal<Health[]>([]);
  protected readonly loading = signal(false);
  protected readonly loaded = signal(false);
  protected readonly error = signal('');
  protected readonly actionLoading = signal('');
  protected readonly selected = signal<Candidate | null>(null);
  protected readonly evidence = signal<Evidence[]>([]);
  protected readonly conflicts = signal<Conflict[]>([]);
  protected readonly reviews = signal<Review[]>([]);
  protected readonly rulesets = signal<HistoryItem[]>([]);
  protected readonly changesets = signal<HistoryItem[]>([]);

  load(): void {
    this.loading.set(true); this.error.set('');
    const headers = new HttpHeaders({ 'X-Tenant-Id': this.tenantId, 'X-Rule-Governance-Token': this.token });
    this.http.get<Candidate[]>('/api/v1/rule-governance/candidates', { headers }).subscribe({ next: value => { this.candidates.set(value); this.loaded.set(true); this.loadHealth(headers); this.loadHistory(headers); }, error: () => { this.error.set('Governance state could not be loaded. Check tenant and token.'); this.loading.set(false); } });
  }

  private loadHealth(headers: HttpHeaders): void {
    this.http.get<Health[]>('/api/v1/rule-governance/health', { headers }).subscribe({ next: value => { this.health.set(value); this.loading.set(false); }, error: () => { this.error.set('Candidates loaded, but rule health could not be read.'); this.loading.set(false); } });
  }

  private loadHistory(headers: HttpHeaders): void {
    this.http.get<HistoryItem[]>('/api/v1/rule-governance/rulesets', { headers }).subscribe({ next: value => this.rulesets.set(value), error: () => this.rulesets.set([]) });
    this.http.get<HistoryItem[]>('/api/v1/rule-governance/changesets', { headers }).subscribe({ next: value => this.changesets.set(value), error: () => this.changesets.set([]) });
  }

  protected inspect(candidate: Candidate): void {
    this.selected.set(candidate); this.evidence.set([]); this.conflicts.set([]); this.reviews.set([]);
    const headers = new HttpHeaders({ 'X-Tenant-Id': this.tenantId, 'X-Rule-Governance-Token': this.token });
    this.http.get<Evidence[]>(`/api/v1/rule-governance/candidates/${candidate.id}/evidence`, { headers }).subscribe({ next: value => this.evidence.set(value), error: () => this.evidence.set([]) });
    this.http.get<Conflict[]>(`/api/v1/rule-governance/candidates/${candidate.id}/conflicts`, { headers }).subscribe({ next: value => this.conflicts.set(value), error: () => this.conflicts.set([]) });
    this.http.get<Review[]>(`/api/v1/rule-governance/candidates/${candidate.id}/reviews`, { headers }).subscribe({ next: value => this.reviews.set(value), error: () => this.reviews.set([]) });
  }

  protected qualify(id: string): void {
    this.actionLoading.set(id); this.error.set('');
    const headers = new HttpHeaders({ 'X-Tenant-Id': this.tenantId, 'X-Rule-Governance-Token': this.token });
    this.http.post(`/api/v1/rule-governance/candidates/${id}/qualify`, {}, { headers }).subscribe({ next: () => { this.actionLoading.set(''); this.load(); }, error: response => { this.actionLoading.set(''); this.error.set(response.error?.message || 'Candidate could not be qualified.'); } });
  }

  protected review(id: string): void {
    if (!this.reviewer.trim() || !this.reviewNote.trim()) { this.error.set('Reviewer and review note are required.'); return; }
    this.actionLoading.set(id); this.error.set('');
    const headers = new HttpHeaders({ 'X-Tenant-Id': this.tenantId, 'X-Rule-Governance-Token': this.token });
    this.http.post(`/api/v1/rule-governance/candidates/${id}/review`, { decision: this.reviewDecision, reviewer: this.reviewer.trim(), reason: this.reviewNote.trim(), conflictsReviewed: [] }, { headers }).subscribe({ next: () => { this.actionLoading.set(''); this.load(); }, error: response => { this.actionLoading.set(''); this.error.set(response.error?.message || 'Candidate review was rejected.'); } });
  }

  protected activate(id: string): void {
    if (!this.parentRuleset.trim() || !this.newRuleset.trim() || !this.reviewer.trim()) { this.error.set('Parent ruleset, new ruleset, and reviewer are required for activation.'); return; }
    this.actionLoading.set(id); this.error.set('');
    const headers = new HttpHeaders({ 'X-Tenant-Id': this.tenantId, 'X-Rule-Governance-Token': this.token });
    this.http.post(`/api/v1/rule-governance/candidates/${id}/activate`, { parentVersion: this.parentRuleset.trim(), newVersion: this.newRuleset.trim(), reviewer: this.reviewer.trim() }, { headers }).subscribe({ next: () => { this.actionLoading.set(''); this.load(); }, error: response => { this.actionLoading.set(''); this.error.set(response.error?.message || 'Ruleset could not be activated.'); } });
  }
}
