import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, inject, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-step6-governance', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    <h3>Text acceptance and production preparation</h3>
    <p>Accepting text preserves every canonical result. It does not approve an exception, resolve visual evidence, or authorize rendering.</p>
    <button type="button" (click)="load()" [disabled]="busy || !analysisId">Load current exit policy</button>
    <p *ngIf="error" role="alert">{{ error }}</p>
    <section *ngIf="policy">
      <p>Policy {{ policy.policyVersion }} · {{ policy.blockedReason || 'Current persisted evidence reviewed by the server' }}</p>
      <article *ngFor="let finding of policy.findings">
        <strong>{{ finding.ruleId }} · {{ finding.outcome }} · {{ finding.resolutionType }}</strong>
        <p>{{ finding.message }}</p>
        <small>{{ finding.blocksText ? 'Text review required' : 'Text acceptance does not resolve this finding' }} · Render gate remains enforceable</small>
        <button *ngIf="finding.resolutionType === 'PRODUCTION_RISK_REVIEW'" type="button"
          [disabled]="!allowed('PRODUCTION_RISK_ACKNOWLEDGEMENT') || !confirmed || justification.trim().length < 20 || busy"
          (click)="submit('risk-acknowledgement', {ruleId:finding.ruleId})">Acknowledge this production risk</button>
      </article>
      <p *ngFor="let reason of reasons('TEXT_ACCEPTED_RENDER_BLOCKED')">Text acceptance: {{ reason }}</p>
      <p *ngFor="let reason of reasons('ATTEMPT_COUNT_EXCEPTION_V1')">Attempt exception: {{ reason }}</p>
      <label>Concrete review justification<textarea [(ngModel)]="justification" rows="3"></textarea></label>
      <label><input type="checkbox" [(ngModel)]="confirmed"> I explicitly confirm this action for the displayed saved analysis. Rendering remains separately gated.</label>
      <button type="button" [disabled]="!allowed('TEXT_ACCEPTED_RENDER_BLOCKED') || !confirmed || justification.trim().length < 20 || busy"
        (click)="submit('text-acceptance')">Accept Text · Keep Render Blocked</button>
      <button type="button" [disabled]="!allowed('ATTEMPT_COUNT_EXCEPTION_V1') || !confirmed || justification.trim().length < 20 || busy"
        (click)="submit('exception', {ruleId:'ATTEMPT_001', exceptionPolicy:'ATTEMPT_COUNT_EXCEPTION_V1'})">Approve scoped attempt exception</button>
      <details *ngIf="allowed('INDEPENDENT_EVIDENCE_REVIEW')"><summary>Record independent story evidence</summary>
        <fieldset *ngFor="let proof of proofs"><legend>{{ proof.label }}</legend>
          <label>Exact production prompt quote<textarea [(ngModel)]="proof.sourceQuote"></textarea></label>
          <label>Exact approved story quote<textarea [(ngModel)]="proof.approvedStoryQuote"></textarea></label>
          <label>Independent review explanation<textarea [(ngModel)]="proof.reason"></textarea></label>
        </fieldset>
        <label><input type="checkbox" [(ngModel)]="approvedEventsPreserved"> I independently verified that all approved events remain intact.</label>
        <button type="button" [disabled]="!confirmed || !approvedEventsPreserved || busy || justification.trim().length < 20"
          (click)="submitSupport()">Record independent evidence</button>
        <p>The reviewer cannot approve their own attempt exception.</p>
      </details>
      <p *ngIf="policy.textAcceptance?.recordId">TEXT_ACCEPTED_RENDER_BLOCKED · {{ policy.textAcceptance.principal }} · {{ policy.textAcceptance.createdAt }}</p>
      <p *ngIf="policy.attemptException?.recordId">Scoped exception recorded. Canonical ATTEMPT_001 remains FAIL.</p>
    </section>
    <p *ngIf="saved" role="status">{{ saved.state || saved.exceptionPolicy || 'Audited review recorded' }}. No render permission was granted.</p>
    <a [href]="preparationLink">Continue to Render Preparation</a>
    <p>Reference association, local image preparation and uploads retain their own validation. Generation requires separate explicit authorization.</p>
  `,
  styles: [`:host{display:block} article{border-top:1px solid #d9dde5;padding:12px 0} label{display:block;margin:12px 0} textarea{display:block;width:100%} button,a{margin:6px 8px 6px 0}`]
})
export class Step6GovernanceComponent implements OnChanges {
  @Input() analysisId = '';
  @Input() preparationLink = '';
  private http = inject(HttpClient);
  private cd = inject(ChangeDetectorRef);
  policy: any = null;
  saved: any = null;
  error = '';
  busy = false;
  confirmed = false;
  justification = '';
  proofs = [
    {key:'miniStory', label:'Source-supported mini-story', sourceQuote:'', approvedStoryQuote:'', reason:''},
    {key:'activeProgression', label:'Active progression', sourceQuote:'', approvedStoryQuote:'', reason:''},
    {key:'payoff', label:'Payoff', sourceQuote:'', approvedStoryQuote:'', reason:''}
  ];
  approvedEventsPreserved = false;
  submitSupport() {
    const extra: any = {approvedEventsPreserved:this.approvedEventsPreserved};
    for (const proof of this.proofs) extra[proof.key] = {sourceQuote:proof.sourceQuote, approvedStoryQuote:proof.approvedStoryQuote, reason:proof.reason};
    this.submit('support', extra);
  }
  private epoch = 0;
  ngOnChanges() { this.epoch++; this.policy = null; this.saved = null; this.confirmed = false; this.busy = false; this.justification = ''; this.error = ''; this.approvedEventsPreserved = false; for (const proof of this.proofs) { proof.sourceQuote = ''; proof.approvedStoryQuote = ''; proof.reason = ''; } }
  allowed(action: string): boolean { return this.policy?.analysisId === this.analysisId && this.policy?.allowedActions?.[action]?.allowed === true; }
  reasons(action: string): string[] { return this.policy?.allowedActions?.[action]?.reasons || (this.policy?.blockedReason ? [this.policy.blockedReason] : []); }
  load() {
    if (!this.analysisId || this.busy) return;
    this.busy = true; this.error = ''; const id = this.analysisId, epoch = this.epoch;
    this.http.get<any>(`/api/v1/intelligence/workflow/records/${id}/governance`).subscribe({
      next: value => { if (epoch !== this.epoch) return; this.policy = value; this.busy = false; this.cd.markForCheck(); },
      error: error => { if (epoch !== this.epoch) return; this.policy = null; this.busy = false; this.error = error?.error?.detail || 'Authoritative policy unavailable; approval remains disabled.'; this.cd.markForCheck(); }
    });
  }
  submit(action: string, extra: any = {}) {
    const permission = action === 'support' ? 'INDEPENDENT_EVIDENCE_REVIEW' : action === 'text-acceptance' ? 'TEXT_ACCEPTED_RENDER_BLOCKED' : action === 'exception' ? 'ATTEMPT_COUNT_EXCEPTION_V1' : 'PRODUCTION_RISK_ACKNOWLEDGEMENT';
    if (this.busy || !this.allowed(permission) || !this.confirmed || this.justification.trim().length < 20) return;
    this.busy = true; this.saved = null; const id = this.analysisId, epoch = this.epoch;
    this.http.post<any>(`/api/v1/intelligence/workflow/records/${id}/governance/${action}`, {
      ...extra, justification: this.justification.trim(), operatorConfirmed: true
    }).subscribe({
      next: saved => {
        if (epoch !== this.epoch) return;
        this.busy = false; this.confirmed = false;
        if (saved?.analysisId !== id || !saved.recordId || saved.policyVersion !== 'STEP6_RESOLUTION_V2') {
          this.error = 'The server did not confirm an exact saved governance action.'; this.cd.markForCheck(); return;
        }
        this.saved = saved; this.load(); this.cd.markForCheck();
      },
      error: error => { if (epoch !== this.epoch) return; this.busy = false; this.error = error?.error?.detail || error?.error?.message || 'Governance action rejected; no approval is recorded.'; this.cd.markForCheck(); }
    });
  }
}
