import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, ReliabilityRecord } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-reliability-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">CALIBRATION</span><h1>Model Reliability</h1><p>Persisted prediction audit evidence only. No client-side confidence is invented.</p></div></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading evaluation evidence</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Reliability unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else { <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PERSISTED AUDITS</span><h2>{{ records().length }} evaluation records</h2></div><span class="status-badge">{{ records().length ? 'AVAILABLE' : 'NO_DATA' }}</span></div>@if (!records().length) { <div class="state-panel compact-state"><strong>No reliability evidence</strong><p>Lock and evaluate predictions before reliability metrics become available.</p></div> } @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Model</th><th>Platform</th><th>Horizon</th><th>Actual</th><th>Absolute error</th><th>80% coverage</th><th>Evaluated</th></tr></thead><tbody>@for (item of records(); track item.id) { <tr><td><strong>{{ item.modelVersion }}</strong><small>{{ item.predictionId }}</small></td><td>{{ item.platform }}</td><td>{{ item.horizonMinutes }} min</td><td class="numeric">{{ value(item.actualValue) }}</td><td class="numeric">{{ value(item.absoluteError) }}</td><td>{{ boolean(item.interval80Covered) }}</td><td>{{ date(item.evaluatedAt) }}</td></tr> }</tbody></table></div> }</section> }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReliabilityPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly records = signal<ReliabilityRecord[]>([]);
  constructor() { this.load(); }
  protected load(): void { this.loading.set(true); this.error.set(''); this.service.getReliability().subscribe({ next: value => { this.records.set(value); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The reliability API did not respond.'); this.loading.set(false); } }); }
  protected value(value: number | null): string { return value === null ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: 3 }); }
  protected boolean(value: boolean | null): string { return value === null ? 'UNKNOWN' : value ? 'Covered' : 'Not covered'; }
  protected date(value: string): string { return new Date(value).toLocaleString(); }
}
