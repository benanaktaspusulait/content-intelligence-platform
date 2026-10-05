import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CharacterIdentity, CreativeIntelligenceService, WorkbenchRow, WorkbenchSummary } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-video-analysis-workbench-page',
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="page-header">
      <div><span class="eyebrow">VIDEO LIBRARY / OPERATIONS</span><h1>Analysis Workbench</h1><p>Work through the existing video stock using current evidence and analysis jobs.</p></div>
      <div class="header-actions"><a class="button button--secondary" routerLink="/videos">Video Library</a><button class="button button--primary" type="button" [disabled]="loading()" (click)="load()">Refresh</button></div>
    </header>

    <section class="workbench-summary">
      <div><span>Matching videos</span><strong>{{ summary().total }}</strong></div><div><span>Current</span><strong>{{ summary().current }}</strong></div><div><span>Incomplete</span><strong>{{ summary().incomplete }}</strong></div><div><span>Ready</span><strong>{{ summary().ready }}</strong></div><div><span>Regenerate</span><strong>{{ summary().regenerate }}</strong></div>
    </section>
    <section class="section-band workbench-toolbar">
      <label><span>Stock</span><select [value]="publicationState()" (change)="publicationState.set(value($event)); load()"><option value="UNPUBLISHED">Unpublished stock</option><option value="">All publication states</option><option value="PUBLISHED">Published</option></select></label>
      <label><span>Analysis</span><select [value]="analysisStatus()" (change)="analysisStatus.set(value($event)); load()"><option value="">Any</option><option value="MISSING">Missing</option><option value="STALE">Stale</option><option value="CURRENT">Current</option><option value="RUNNING">Running</option><option value="FAILED">Failed</option></select></label>
      <label><span>Triage</span><select [value]="triage()" (change)="triage.set(value($event)); load()"><option value="">Any</option><option value="READY">Ready</option><option value="REVIEW">Review</option><option value="REGENERATE">Regenerate</option><option value="EDIT_PLAN">Edit plan</option><option value="INCOMPLETE">Incomplete</option></select></label>
      <label><span>Character</span><select [value]="characterId()" (change)="characterId.set(value($event)); load()"><option value="">Any character</option>@for (character of characters(); track character.id) { <option [value]="character.id">{{ character.name }}</option> }</select></label>
      <label class="workbench-search"><span>Search</span><input type="search" placeholder="Filename or path" [value]="query()" (input)="query.set(value($event))" (keyup.enter)="load()"></label>
      <label><span>Sort</span><select [value]="sort()" (change)="sort.set(value($event)); load()"><option value="date">Newest</option><option value="title">Title</option><option value="analysis">Analysis</option><option value="triage">Triage</option><option value="views">Observed views</option></select></label>
      <button class="button button--primary" type="button" [disabled]="selected().size === 0 || bulkRunning()" (click)="analyzeSelected()">{{ bulkRunning() ? 'Queued…' : 'Analyze selected' }}</button>
      <button class="button button--quiet" type="button" [disabled]="bulkRunning()" (click)="analyzeAllMatching()">Analyze all matching</button>
    </section>
    @if (message()) { <div class="context-banner"><span>WORKBENCH</span><strong>{{ message() }}</strong></div> }
    @if (error()) { <div class="state-panel state-panel--error compact-state"><strong>Workbench unavailable</strong><p>{{ error() }}</p></div> }
    <section class="table-shell workbench-table-shell">
      <div class="workbench-table-meta"><strong>{{ total() }} videos</strong><span>Page {{ page() + 1 }} of {{ totalPages() || 1 }}</span><span class="workbench-hint">Selection is scoped to the current page.</span></div>
      @if (loading()) { <div class="state-panel compact-state"><span class="spinner"></span><strong>Loading workbench…</strong></div> }
      @else if (!rows().length) { <div class="state-panel compact-state"><strong>No videos match this filter</strong><p>Change the stock or analysis filter to inspect another cohort.</p></div> }
      @else { <div class="data-table-scroll"><table class="data-table workbench-table"><thead><tr><th><input type="checkbox" [checked]="allSelected()" (change)="togglePage($event)" aria-label="Select visible videos"></th><th>Video</th><th>Characters</th><th>Analysis</th><th>Triage</th><th>Publication</th><th>Observed</th><th></th></tr></thead><tbody>@for (row of rows(); track row.id) { <tr><td><input type="checkbox" [checked]="selected().has(row.id)" (change)="toggle(row.id)" [attr.aria-label]="'Select ' + row.title"></td><td><strong>{{ row.title }}</strong><small>{{ duration(row.durationMs) }} · {{ row.width }}×{{ row.height }}</small></td><td>@if (row.characters.length) { @for (character of row.characters; track character.id) { <span class="character-chip" [class.character-chip--primary]="character.participation === 'PRIMARY'">{{ character.name }}</span> } } @else { <span class="muted">Unresolved</span> }</td><td><span class="status-badge" [class.status-badge--green]="row.analysisStatus === 'CURRENT'" [class.status-badge--amber]="row.analysisStatus === 'RUNNING' || row.analysisStatus === 'STALE'">{{ row.analysisStatus }}</span></td><td><span class="status-badge" [class.status-badge--green]="row.triage === 'READY'">{{ label(row.triage) }}</span></td><td>{{ label(row.publicationState) }}</td><td class="tabular">{{ row.observedViews === null ? '—' : row.observedViews.toLocaleString() }}<small>{{ row.observationCount || 0 }} observations</small></td><td><a class="icon-button table-action" [routerLink]="['/videos', row.id]" title="Open video details" aria-label="Open video details">↗</a></td></tr> }</tbody></table></div> }
      <div class="workbench-pagination"><button class="button button--compact" type="button" [disabled]="page() === 0 || loading()" (click)="go(page() - 1)">Previous</button><button class="button button--compact" type="button" [disabled]="page() + 1 >= totalPages() || loading()" (click)="go(page() + 1)">Next</button></div>
    </section>
  `,
  styles: [`
    .workbench-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));margin-bottom:18px;background:var(--surface);border:1px solid var(--line)}
    .workbench-summary>div{padding:14px 16px;border-right:1px solid var(--line)} .workbench-summary>div:last-child{border-right:0}.workbench-summary span{display:block;color:var(--muted);font-size:10px}.workbench-summary strong{display:block;margin-top:4px;font-family:Georgia,serif;font-size:24px}
    .workbench-toolbar{display:flex;align-items:end;gap:10px;padding:12px;margin-bottom:16px;flex-wrap:wrap}.workbench-toolbar label{display:flex;flex-direction:column;gap:4px;color:var(--muted);font-size:9px;font-weight:800;text-transform:uppercase}.workbench-toolbar input,.workbench-toolbar select{height:34px;padding:0 9px;background:#fbfcf8;border:1px solid var(--line-strong);border-radius:4px;font-size:11px}.workbench-toolbar select{min-width:128px}.workbench-search{min-width:220px;flex:1}.workbench-table-shell{overflow:hidden}.workbench-table-meta{display:flex;gap:18px;align-items:center;padding:13px 16px;border-bottom:1px solid var(--line);font-size:10px;color:var(--muted)}.workbench-table-meta strong{color:var(--ink);font-size:12px}.workbench-hint{margin-left:auto}.workbench-table td,.workbench-table th{vertical-align:middle}.workbench-table td strong{display:block;max-width:320px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.workbench-table td small{display:block;color:var(--muted);font-size:9px}.character-chip{display:inline-flex;margin:2px 3px 2px 0;padding:3px 6px;background:var(--surface-alt);border:1px solid var(--line);border-radius:3px;font-size:9px}.character-chip--primary{color:var(--moss-dark);background:var(--lime-soft);border-color:#cae692;font-weight:800}.muted{color:var(--muted);font-size:10px}.workbench-pagination{display:flex;justify-content:flex-end;gap:8px;padding:12px 16px;border-top:1px solid var(--line)}
    @media(max-width:900px){.workbench-summary{grid-template-columns:repeat(3,1fr)}.workbench-hint{display:none}}
  `],
})
export class VideoAnalysisWorkbenchPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly rows = signal<WorkbenchRow[]>([]); protected readonly summary = signal<WorkbenchSummary>({total:0,current:0,stale:0,missing:0,running:0,failed:0,ready:0,review:0,regenerate:0,editPlan:0,incomplete:0});
  protected readonly loading = signal(false); protected readonly bulkRunning = signal(false); protected readonly error = signal(''); protected readonly message = signal(''); protected readonly page = signal(0); protected readonly total = signal(0); protected readonly totalPages = signal(0); protected readonly selected = signal<Set<string>>(new Set());
  protected readonly publicationState = signal('UNPUBLISHED'); protected readonly analysisStatus = signal(''); protected readonly triage = signal(''); protected readonly characterId = signal(''); protected readonly characters = signal<CharacterIdentity[]>([]); protected readonly query = signal(''); protected readonly sort = signal('date');
  constructor(){this.service.getCharacters().subscribe({next:items=>this.characters.set(items)});this.load();}
  protected load(): void { this.loading.set(true); this.error.set(''); this.service.getAnalysisWorkbench({page:this.page(),size:25,publicationState:this.publicationState(),analysisStatus:this.analysisStatus(),triage:this.triage(),characterId:this.characterId(),query:this.query(),sort:this.sort(),direction:'desc'}).subscribe({next:r=>{this.rows.set(r.content);this.summary.set(r.summary);this.total.set(r.totalElements);this.totalPages.set(r.totalPages);this.loading.set(false)},error:e=>{this.error.set(e.error?.message||'Could not load analysis workbench.');this.loading.set(false)}}); }
  protected go(page:number):void{this.page.set(page);this.selected.set(new Set());this.load()}
  protected toggle(id:string):void{const next=new Set(this.selected());next.has(id)?next.delete(id):next.add(id);this.selected.set(next)}
  protected allSelected():boolean{return this.rows().length>0&&this.rows().every(row=>this.selected().has(row.id))}
  protected togglePage(event:Event):void{const checked=(event.target as HTMLInputElement).checked;const next=new Set(this.selected());this.rows().forEach(row=>checked?next.add(row.id):next.delete(row.id));this.selected.set(next)}
  protected analyzeSelected():void{this.enqueue([...this.selected()],false)}
  protected analyzeAllMatching():void{this.enqueue([],true)}
  private enqueue(videoIds:string[],allMatching:boolean):void{this.bulkRunning.set(true);this.service.bulkAnalyze({videoIds,allMatching,analysisStatus:this.analysisStatus(),triage:this.triage(),characterId:this.characterId(),publicationState:this.publicationState(),query:this.query(),reanalyzeSelected:false}).subscribe({next:r=>{this.message.set(`${r.accepted} analysis job(s) queued; ${r.skipped+r.alreadyRunning} skipped or already running.`);this.bulkRunning.set(false);this.load()},error:e=>{this.error.set(e.error?.message||'Bulk analysis could not be queued.');this.bulkRunning.set(false)}})}
  protected value(event:Event):string{return (event.target as HTMLInputElement|HTMLSelectElement).value}
  protected duration(ms:number):string{return `${Math.round(ms/1000)}s`}
  protected label(value:string):string{return value.replaceAll('_',' ')}
}
