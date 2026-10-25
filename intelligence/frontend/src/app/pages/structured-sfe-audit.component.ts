import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-structured-sfe-audit', standalone: true, imports: [CommonModule, FormsModule],
  template: `<section class="card card-body" aria-label="Structured SFE evidence audit">
    <h2>Short-form evidence source audit</h2>
    <p>Saved semantic response only. No new ideas, provider calls or renders.</p>
    <label>Evidence Source <select aria-label="Short-form evidence source" [(ngModel)]="source" (ngModelChange)="clear()"><option value="timed-text-v1">Timed Text</option><option value="structured-canonical-v1">Structured Canonical</option></select></label>
    <label><input type="checkbox" [(ngModel)]="dual" (ngModelChange)="clear()"> Dual evidence audit — separate scores</label>
    <button type="button" [disabled]="busy" (click)="run()">{{ busy ? 'Reanalyzing…' : 'Analyze stored short-form evidence' }}</button>
    <p *ngIf="error" role="alert">{{ error }}</p>
    <div *ngIf="result as report">
      <p>Provider calls {{ report.providerCalls }} · Scores blended: {{ report.scoresBlended }}</p>
      <article *ngFor="let row of report.candidates"><details><summary>{{ row.ideaId }} · {{ row.title }} · Delta {{ row.delta }}</summary>
        <p>Score {{ chosen(row).shortFormScore }} · {{ chosen(row).status }}</p>
        <p>Legacy {{ row.legacy.shortFormScore }} · Structured {{ row.structured.shortFormScore }}</p>
        <pre>{{ (source === 'structured-canonical-v1' ? row.structuredRecognition : row.legacyRecognition) | json }}</pre>
        <details><summary>Findings and source evidence</summary><pre>{{ chosen(row).findings | json }}</pre><pre>{{ chosen(row).findingEvidence | json }}</pre></details>
        <pre *ngIf="dual">{{ row.dualAudit | json }}</pre>
      </details></article>
    </div>
  </section>`,
})
export class StructuredSfeAuditComponent implements OnDestroy {
  private http = inject(HttpClient);
  private pending?: Subscription;
  source: 'timed-text-v1' | 'structured-canonical-v1' = 'timed-text-v1';
  dual = false; busy = false; result: any = null; error = '';
  clear(): void { this.pending?.unsubscribe(); this.result = null; this.busy = false; this.error = ''; }
  chosen(row: any): any { return this.source === 'structured-canonical-v1' ? row.structured : row.legacy; }
  run(): void {
    if (this.busy) return;
    this.busy = true; this.result = null; this.error = '';
    this.pending = this.http.post<any>('/api/v1/intelligence/workflow/concepts/semantic/short-form-replay', {
      experimentId: 'semantic-live-v1-seed-42-count-40', shortFormEvidenceSourceVersion: this.source, dualEvidenceAudit: this.dual, allowExternalGeneration: false,
    }).subscribe({ next: report => { this.busy = false; if (report?.workflow === 'STRUCTURED_SFE_OFFLINE_REPLAY') this.result = report; else this.error = 'No usable audit returned.'; }, error: () => { this.busy = false; this.error = 'Stored evidence audit failed.'; } });
  }
  ngOnDestroy(): void { this.pending?.unsubscribe(); }
}
