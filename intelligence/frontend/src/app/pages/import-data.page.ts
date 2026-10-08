import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CreativeIntelligenceService, ImportRow, VideoVariant } from '../core/creative-intelligence.service';

interface DetectedField { source: string; interpretation: string; }

@Component({
  selector: 'app-import-data-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">DATA INTAKE</span><h1>Import Data</h1><p>Validate platform exports before they enter the evidence store.</p></div><span class="step-indicator">STEP {{ step() }} OF 3</span></header>
    <ol class="workflow-steps" aria-label="Import progress"><li class="is-complete"><span>1</span><strong>Source</strong><small>Selected</small></li><li [class.is-active]="step() === 2" [class.is-complete]="step() === 3"><span>2</span><strong>Map fields</strong><small>Review schema</small></li><li [class.is-active]="step() === 3"><span>3</span><strong>Commit</strong><small>Confirm import</small></li></ol>
    <div class="import-layout">
      <section class="section-band upload-panel">
        <div class="section-heading"><div><span class="eyebrow">SOURCE FILE</span><h2>Platform export</h2></div><span class="status-badge status-badge--green">CSV</span></div>
        <label class="file-drop"><input type="file" accept=".csv,.tsv,.xlsx" (change)="fileSelected($event)"><span class="upload-icon" aria-hidden="true">↑</span><strong>{{ fileName() || 'Choose a platform export' }}</strong><small>{{ rowCount() ? rowCount() + ' rows staged' : 'CSV, TSV or XLSX · up to 250 MB' }}</small><span class="button button--secondary">Browse files</span></label>
        <dl class="compact-facts source-facts"><div><dt>Platform</dt><dd><select [value]="platform()" (change)="platform.set(selectValue($event))"><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="tiktok">TikTok</option><option value="youtube">YouTube</option></select></dd></div><div><dt>Matched rows</dt><dd>{{ matchedRows() }}</dd></div><div><dt>Storage</dt><dd>Raw + normalized</dd></div></dl>
      </section>
      <aside class="section-band validation-panel"><span class="eyebrow">VALIDATION</span><h2>{{ unresolvedRows() }} unresolved rows</h2><p>Only exact video IDs or unique filenames are accepted.</p><div class="validation-meter"><span [style.width.%]="matchCoverage()"></span></div><small>{{ matchCoverage() }}% row coverage</small><ul><li class="passed">{{ mappings().length }} fields detected</li><li class="passed">{{ matchedRows() }} exact matches</li><li class="warning">{{ unresolvedRows() }} rows need review</li></ul>@if (error()) { <p class="amber-text">{{ error() }}</p> }</aside>
    </div>
    <section class="section-band mapping-section">
      <div class="section-heading"><div><span class="eyebrow">DETECTED SCHEMA</span><h2>Backend field interpretation</h2></div><span class="data-freshness">Read-only preview</span></div>
      <p class="form-message">The import service uses the source column names and keeps the original payload. These interpretations are informational; no client-side mapping is silently applied.</p>
      <div class="data-table-scroll"><table class="data-table mapping-table"><thead><tr><th>Source field</th><th>Backend interpretation</th></tr></thead><tbody>@for (field of mappings(); track field.source) {<tr><td><strong>{{ field.source }}</strong></td><td>{{ field.interpretation }}</td></tr>}</tbody></table></div>
      @if (unresolvedRows() > 0 && batchId()) {
        <div class="section-heading review-heading"><div><span class="eyebrow">MATCH REVIEW</span><h2>Resolve unmatched rows</h2></div><span class="status-badge status-badge--amber">{{ unresolvedRows() }} unresolved</span></div>
        <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Source row</th><th>Source identity</th><th>Match to canonical video</th></tr></thead><tbody>@for (row of unresolvedRowsList(); track row.id) {<tr><td>{{ row.sourceRowNumber }}</td><td class="code-value">{{ rowIdentity(row) }}</td><td><select [value]="selections()[row.id]?.videoId || ''" (change)="selectVideo(row, $event)" [attr.aria-label]="'Resolve source row ' + row.sourceRowNumber"><option value="">Select video…</option>@for (video of videos(); track video.id) {<option [value]="video.id">{{ video.title }}</option>}</select>
          @if (selections()[row.id]; as selection) {
            <select [value]="selection.variantId" (change)="selectVariant(row, $event)" [disabled]="!selection.ready" aria-label="Exact variant"><option value="">Original video</option>@for (variant of selection.variants; track variant.id) {<option [value]="variant.id">{{ variant.variantType }} · {{ variant.id }}</option>}</select>
            <input aria-label="Match reason" placeholder="Evidence for this exact match" [value]="selection.reason" (input)="setReason(row, $event)">
            <button type="button" [disabled]="loading() || !selection.ready || !selection.reason.trim()" (click)="resolveRow(row)">Confirm exact match</button>
          }
          </td></tr>}</tbody></table></div>
      }
      @if (rows().length) {
        <details [open]="committed()"><summary>Saved exact row associations · batch {{ batchId() }}</summary><table class="data-table"><thead><tr><th>Source row</th><th>Canonical video</th><th>Exact variant</th><th>Evidence reason</th></tr></thead><tbody>@for (row of rows(); track row.id) {<tr><td>{{ row.sourceRowNumber }} · {{ row.matchStatus }}</td><td>{{ row.matchedVideoId || 'Unresolved' }}</td><td>{{ row.matchedVariantId || (row.matchedVideoId ? 'Original video' : 'Unresolved') }}</td><td>{{ row.matchReason || 'Source export matching' }}</td></tr>}</tbody></table></details>
      }
      <footer class="commit-bar"><div><strong>{{ matchedRows() }} of {{ rowCount() }} rows matched</strong><small>Raw source remains append-only; blank metrics stay null.</small></div><button class="button button--primary" type="button" [disabled]="unresolvedRows() > 0 || !batchId() || loading() || committed()" (click)="commit()">{{ committed() ? 'Import committed' : loading() ? 'Working…' : 'Commit import' }} <span aria-hidden="true">→</span></button></footer>
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImportDataPage {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly step = signal(2);
  protected readonly fileName = signal('');
  protected readonly committed = signal(false);
  protected readonly mappings = signal<DetectedField[]>([]);
  protected readonly platform = signal('instagram');
  protected readonly rows = signal<ImportRow[]>([]);
  protected readonly videos = signal<{ id: string; title: string }[]>([]);
  protected readonly batchId = signal('');
  protected readonly rowCount = signal(0);
  protected readonly matchedRows = signal(0);
  protected readonly unresolvedRows = signal(0);
  protected readonly loading = signal(false);
  protected readonly error = signal('');
  protected readonly unresolvedRowsList = computed(() => this.rows().filter(row => row.matchStatus === 'UNRESOLVED'));
  protected readonly matchCoverage = computed(() => this.rowCount() ? Math.round(this.matchedRows() / this.rowCount() * 100) : 0);

  protected readonly selections = signal<Record<string, { videoId: string; variantId: string; reason: string; variants: VideoVariant[]; ready: boolean }>>({});

  constructor() {
    const savedBatch = this.route.snapshot.queryParamMap.get('batchId');
    if (savedBatch) {
      this.loading.set(true);
      this.service.getImportBatch(savedBatch).subscribe({
        next: preview => {
          this.batchId.set(preview.batchId); this.fileName.set(preview.filename);
          this.rowCount.set(preview.rowCount); this.matchedRows.set(preview.matchedRows); this.unresolvedRows.set(preview.unresolvedRows);
          this.committed.set(preview.status === 'COMMITTED');
          this.step.set(preview.status === 'COMMITTED' ? 3 : 2);
          this.mappings.set(preview.columns.map(source => ({ source, interpretation: this.interpretation(source) })));
          this.service.getImportRows(preview.batchId).subscribe({ next: rows => { this.rows.set(rows); this.loading.set(false); }, error: () => { this.error.set('Saved batch rows could not be loaded.'); this.loading.set(false); } });
        }, error: () => { this.error.set('Saved import batch could not be opened.'); this.loading.set(false); },
      });
    }
    this.service.getImportVideoChoices().subscribe({
      next: videos => this.videos.set(videos),
      error: () => this.error.set('Canonical videos could not be loaded. Reload to retry before matching.'),
    });
  }

  protected selectVideo(row: ImportRow, event: Event): void {
    const videoId = this.selectValue(event);
    this.selections.update(current => ({ ...current, [row.id]: { videoId, variantId: '', reason: '', variants: [], ready: false } }));
    if (!videoId) return;
    this.service.listVariants(videoId).subscribe({
      next: variants => {
        if (this.selections()[row.id]?.videoId !== videoId) return;
        this.selections.update(current => ({ ...current, [row.id]: { ...current[row.id], variants, ready: true } }));
      },
      error: () => this.error.set('Variants could not be loaded; this row has not been matched.'),
    });
  }
  protected selectVariant(row: ImportRow, event: Event): void {
    const variantId = this.selectValue(event);
    this.selections.update(current => ({ ...current, [row.id]: { ...current[row.id], variantId } }));
  }
  protected setReason(row: ImportRow, event: Event): void {
    const reason = (event.target as HTMLInputElement).value;
    this.selections.update(current => ({ ...current, [row.id]: { ...current[row.id], reason } }));
  }

  protected fileSelected(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    this.fileName.set(file.name); this.loading.set(true); this.error.set(''); this.committed.set(false);
    this.service.previewImport(file, this.platform(), Intl.DateTimeFormat().resolvedOptions().timeZone).subscribe({
      next: preview => {
        this.batchId.set(preview.batchId); this.router.navigate([], { relativeTo: this.route, queryParams: { batchId: preview.batchId }, replaceUrl: true }); this.rowCount.set(preview.rowCount); this.matchedRows.set(preview.matchedRows); this.unresolvedRows.set(preview.unresolvedRows);
        this.mappings.set(preview.columns.map(column => ({ source: column, interpretation: this.interpretation(column) })));
        this.service.getImportRows(preview.batchId).subscribe({
          next: rows => { this.rows.set(rows); this.loading.set(false); },
          error: response => { this.error.set(response.error?.message || 'Import rows could not be loaded.'); this.loading.set(false); },
        });
      },
      error: response => { this.error.set(response.error?.message || 'Import preview failed.'); this.loading.set(false); },
    });
  }
  protected selectValue(event: Event): string { return (event.target as HTMLSelectElement).value; }
  protected resolveRow(row: ImportRow): void {
    const selection = this.selections()[row.id];
    if (!selection?.ready || !selection.videoId || !selection.reason.trim() || !this.batchId()) return;
    this.loading.set(true); this.error.set('');
    this.service.resolveImportRow(this.batchId(), row.id, selection.videoId, selection.reason.trim(), selection.variantId || null).subscribe({
      next: preview => {
        this.matchedRows.set(preview.matchedRows); this.unresolvedRows.set(preview.unresolvedRows);
        this.service.getImportRows(this.batchId()).subscribe({ next: rows => { this.rows.set(rows); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'Import rows could not be refreshed.'); this.loading.set(false); } });
      },
      error: response => { this.error.set(response.error?.message || 'Row match failed.'); this.loading.set(false); },
    });
  }
  protected rowIdentity(row: ImportRow): string { return row.rawData['video_id'] || row.rawData['videoId'] || row.rawData['filename'] || row.rawData['file_name'] || `row ${row.sourceRowNumber}`; }
  protected commit(): void {
    if (!this.batchId() || this.unresolvedRows() > 0 || this.committed()) return;
    this.loading.set(true); this.error.set('');
    this.service.commitImport(this.batchId()).subscribe({
      next: () => { this.committed.set(true); this.step.set(3); this.loading.set(false); },
      error: response => { this.error.set(response.error?.message || 'Import commit failed.'); this.loading.set(false); },
    });
  }
  private interpretation(column: string): string {
    const key = column.toLowerCase().replace(/[^a-z0-9]/g, '');
    if (key.includes('videoid') || key === 'mediaid') return 'Canonical video match key';
    if (key.includes('filename') || key === 'file') return 'Canonical filename match key';
    if (key.includes('view') || key === 'plays') return 'Views metric';
    if (key.includes('published') || key === 'posted') return 'Publication timestamp';
    if (key.includes('measure') || key === 'date') return 'Measurement timestamp';
    if (key.includes('completion')) return 'Completion rate metric';
    if (key.includes('reach')) return 'Reach metric';
    return 'Raw payload retained; no recognized interpretation';
  }
}
