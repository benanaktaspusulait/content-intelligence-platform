import { Component, Input, OnChanges, OnDestroy, ChangeDetectorRef, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';

/** Independent, explicit editorial analysis; never edits a saved canonical report. */
@Component({
  selector: 'app-short-form-report', standalone: true, imports: [CommonModule],
  template: `
    <details *ngIf="sourceText || assessment" aria-label="Short-form assessment">
      <summary>15-second short-form assessment</summary>
      <p>Evaluate the visual plan independently from canonical and long-form scores. No provider calls or renders.</p>
      <button *ngIf="sourceText" type="button" (click)="evaluate()" [disabled]="busy">{{ busy ? 'Evaluating…' : 'Evaluate short-form plan' }}</button>
      <p *ngIf="error" role="alert">{{ error }}</p>
      <section *ngIf="result as report" aria-label="Independent short-form results">
        <h3>{{ report.status }} · {{ report.shortFormScore }}/100</h3>
        <p>{{ report.humanReadableReport }}</p>
        <p>{{ report.instantPremiseLegibility?.reason }}</p>
        <p>Replay: {{ report.rewatchType }} · Duplicate risk: {{ report.duplicateEngineRisk?.status }}</p>
        <p>{{ report.duplicateEngineRisk?.limitation }}</p>
        <table><caption>Independent short-form dimensions</caption><tbody>
          <tr *ngFor="let key of scoreKeys"><th scope="row">{{ key }}</th><td>{{ report[key] }}/100</td></tr>
        </tbody></table>
        <ul><li *ngFor="let finding of report.findings">{{ finding.code }} · {{ finding.severity }} · {{ finding.message }}</li></ul>
        <details><summary>Causal progression and source evidence</summary>
          <article *ngFor="let beat of report.beats">
            <strong>{{ beat.id }} · {{ beat.start ?? '?' }}–{{ beat.end ?? '?' }}s · {{ beat.progressTypes?.join(', ') || 'No supported progress' }}</strong>
            <blockquote>{{ beat.quote }}</blockquote>
          </article>
          <p>Source SHA-256: {{ report.sourceSha256 }}</p>
          <p *ngFor="let limitation of report.evidenceLimitations">{{ limitation }}</p>
        </details>
      </section>
    </details>`,
})
export class ShortFormReportComponent implements OnChanges, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly changeDetector = inject(ChangeDetectorRef);
  @Input() assessment: any = null;
  @Input() sourceText = '';
  result: any = null;
  busy = false;
  error = '';
  private pending?: Subscription;
  readonly scoreKeys = ['hookScore', 'goalScore', 'ruleClarityScore', 'beatDensityScore', 'progressDensityScore',
    'escalationScore', 'payoffScore', 'rewatchScore', 'silentLegibilityScore', 'productionFeasibilityScore'];

  ngOnChanges(changes: SimpleChanges): void {
    this.pending?.unsubscribe(); this.busy = false; this.error = '';
    this.result = changes['sourceText'] && !changes['sourceText'].firstChange && !changes['assessment'] ? null : this.assessment;
  }
  ngOnDestroy(): void { this.pending?.unsubscribe(); }
  evaluate(): void {
    if (this.busy || !this.sourceText.trim()) return;
    this.busy = true; this.error = ''; this.result = null; this.changeDetector.markForCheck();
    this.pending = this.http.post<any>('/api/v1/intelligence/workflow/short-form/evaluate', { text: this.sourceText }).subscribe({
      next: report => {
        this.busy = false; this.changeDetector.markForCheck();
        if (report?.engine !== 'SHORT_FORM_ENGINE') { this.error = 'No usable short-form assessment returned.'; return; }
        this.result = report;
      },
      error: () => { this.busy = false; this.changeDetector.markForCheck(); this.error = 'Short-form assessment failed. Retry when the validation service is available.'; },
    });
  }
}
