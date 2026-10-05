import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';

interface Candidate { id: string; proposedRuleName: string; proposedRuleKey: string; evidenceLevel: string; riskTier: string; status: string; supportingObservationCount: number; }
interface Health { ruleKey: string; rulesetVersion: string; status: string; currentSupportingSampleSize: number; supportTrend?: string; }

@Component({
  selector: 'app-rule-governance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <header class="page-header"><div><span class="eyebrow">GOVERNED POLICY</span><h1>Rule Governance</h1><p>Review evidence-backed rule candidates before a new immutable ruleset release.</p></div></header>
    <section class="access-panel">
      <label>Tenant <input [(ngModel)]="tenantId" placeholder="tenant-id" autocomplete="off"></label>
      <label>Governance token <input [(ngModel)]="token" type="password" placeholder="operator token" autocomplete="off"></label>
      <button class="button button--primary" type="button" (click)="load()" [disabled]="loading()">{{ loading() ? 'Loading...' : 'Load governance state' }}</button>
    </section>
    @if (error()) { <div class="error-state">{{ error() }}</div> }
    <section class="governance-grid">
      <article class="panel"><div class="panel-heading"><div><span class="eyebrow">REVIEW QUEUE</span><h2>Rule candidates</h2></div><span class="count">{{ candidates().length }}</span></div>
        @if (!loaded()) { <p class="muted">Authenticate to load persisted candidates.</p> }
        @else if (!candidates().length) { <p class="muted">No governed candidates found.</p> }
        @else { @for (candidate of candidates(); track candidate.id) { <div class="candidate-row"><div><strong>{{ candidate.proposedRuleName }}</strong><small>{{ candidate.proposedRuleKey }} · {{ candidate.evidenceLevel }} · {{ candidate.supportingObservationCount }} observations</small></div><span class="status" [class]="'status status--' + candidate.status.toLowerCase()">{{ candidate.status }}</span></div> } }
      </article>
      <article class="panel"><div class="panel-heading"><div><span class="eyebrow">REVALIDATION</span><h2>Rule health</h2></div><span class="count">{{ health().length }}</span></div>
        @if (!health().length) { <p class="muted">No health records found.</p> }
        @else { @for (item of health(); track item.ruleKey + item.rulesetVersion) { <div class="candidate-row"><div><strong>{{ item.ruleKey }}</strong><small>Ruleset {{ item.rulesetVersion }} · n={{ item.currentSupportingSampleSize }}</small></div><span class="status">{{ item.status }}</span></div> } }
      </article>
    </section>
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
    .candidate-row { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:14px 0; border-bottom:1px solid #edf0f3; } .candidate-row strong { display:block; } .candidate-row small { display:block; color:#75818d; margin-top:4px; }
    .status { white-space:nowrap; font-size:11px; font-weight:800; padding:5px 8px; border-radius:999px; background:#eef2f5; } .status--ready_for_review { background:#fff1c7; } .status--approved { background:#d9f5e6; } .muted { color:#75818d; } .error-state { color:#a52626; background:#fff0f0; padding:12px; margin-bottom:20px; border-radius:6px; }
    @media (max-width: 800px) { .governance-grid { grid-template-columns:1fr; } .access-panel { align-items:stretch; flex-direction:column; } input { min-width:0; } }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RuleGovernancePage {
  private readonly http = inject(HttpClient);
  protected tenantId = '';
  protected token = '';
  protected readonly candidates = signal<Candidate[]>([]);
  protected readonly health = signal<Health[]>([]);
  protected readonly loading = signal(false);
  protected readonly loaded = signal(false);
  protected readonly error = signal('');

  load(): void {
    this.loading.set(true); this.error.set('');
    const headers = new HttpHeaders({ 'X-Tenant-Id': this.tenantId, 'X-Rule-Governance-Token': this.token });
    this.http.get<Candidate[]>('/api/v1/rule-governance/candidates', { headers }).subscribe({ next: value => { this.candidates.set(value); this.loaded.set(true); this.loadHealth(headers); }, error: () => { this.error.set('Governance state could not be loaded. Check tenant and token.'); this.loading.set(false); } });
  }

  private loadHealth(headers: HttpHeaders): void {
    this.http.get<Health[]>('/api/v1/rule-governance/health', { headers }).subscribe({ next: value => { this.health.set(value); this.loading.set(false); }, error: () => { this.error.set('Candidates loaded, but rule health could not be read.'); this.loading.set(false); } });
  }
}
