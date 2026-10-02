import { ChangeDetectionStrategy, Component, ElementRef, HostListener, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, concatMap, forkJoin, from, map, of, toArray } from 'rxjs';
import { CreativeIntelligenceService, MediaDirectory, MediaFile } from '../core/creative-intelligence.service';

export interface MediaFileView extends MediaFile {
  displayName: string;
  folderName: string;
  folderPath: string;
  variantName: string;
}

export interface MediaFileGroup {
  folderName: string;
  folderPath: string;
  files: MediaFileView[];
}
interface FolderLoadFailure { folder: string; message: string; }

export function filterMediaDirectories(folders: MediaDirectory[], query: string): MediaDirectory[] {
  const normalized = query.trim().toLocaleLowerCase();
  return normalized ? folders.filter(folder => folder.name.toLocaleLowerCase().includes(normalized)) : folders;
}

export function mergeMediaFiles(groups: MediaFile[][]): MediaFile[] {
  const files = new Map<string, MediaFile>();
  for (const group of groups) for (const file of group) files.set(file.relativePath, file);
  return [...files.values()].sort((left, right) => left.relativePath.localeCompare(right.relativePath));
}

export function groupMediaFilesByFolder(files: MediaFileView[]): MediaFileGroup[] {
  const groups = new Map<string, MediaFileGroup>();
  for (const file of files) {
    const group = groups.get(file.folderPath);
    if (group) group.files.push(file);
    else groups.set(file.folderPath, { folderName: file.folderName, folderPath: file.folderPath, files: [file] });
  }
  return [...groups.values()];
}

export function mediaVariant(filename: string): string {
  const stem = filename.replace(/\.[^.]+$/, '').toLowerCase();
  const versioned = stem.match(/_v(\d+)_(original|hd|hook)$/);
  if (versioned) return `V${versioned[1]} ${versioned[2] === 'original' ? 'Original' : versioned[2].toUpperCase()}`;
  if (stem.endsWith('_hook_endcard_test')) return 'Hook End Card Test';
  if (stem.endsWith('_hook')) return 'Hook';
  if (stem.endsWith('_hd_1080x1920') || stem.endsWith('_hd')) return 'HD';
  if (stem.endsWith('_no_text')) return 'No Text';
  return 'Original';
}

export function resultCountLabel(groupCount: number, fileCount: number): string {
  return `${groupCount} ${groupCount === 1 ? 'group' : 'groups'} · ${fileCount} ${fileCount === 1 ? 'file' : 'files'}`;
}

@Component({
  selector: 'app-video-library-page',
  imports: [RouterLink],
  template: `
    <header class="page-header"><div><span class="eyebrow">CREATIVE EVIDENCE</span><h1>Video Library</h1><p>Browse mounted media and choose which videos become evidence records.</p></div></header>

    <section class="section-band ingest-directory-panel">
      <div><span class="eyebrow">MEDIA LIBRARY</span><h2>Ingest selected folders</h2><p>Selection only previews real files. Ingest starts only when you use the action.</p></div>
      <label class="check-row"><input type="checkbox" [checked]="recursive()" (change)="setRecursive($event)"><span><strong>Include subfolders</strong><small>Scans MP4, MOV and M4V files</small></span></label>
      <button class="button button--primary" type="button" [disabled]="selectedDirectories().length === 0 || ingesting()" (click)="ingestSelected()">{{ ingestButtonLabel() }}</button>
      <details class="advanced-path"><summary>Advanced: manual folder path</summary><div><input type="text" aria-label="Manual folder path" [value]="directory()" (input)="directory.set(($any($event.target)).value)" placeholder="library/Folder name"><button class="button button--compact" type="button" [disabled]="!directory().trim() || ingesting()" (click)="ingestManual()">Ingest path</button></div></details>
    </section>

    @if (message()) { <div class="context-banner"><span>INGEST RESULT</span><strong>{{ message() }}</strong>@if (ingestErrors()) { <p>{{ ingestErrors() }} files could not be processed.</p> }</div> }
    @if (error()) { <div class="state-panel state-panel--error compact-state"><strong>Video library unavailable</strong><p>{{ error() }}</p></div> }

    @if (directoriesLoading()) {
      <section class="section-band folder-directory-state" aria-live="polite"><span class="spinner"></span><strong>Loading media folders</strong></section>
    } @else if (mediaDirectories().length) {
      <section class="section-band media-folder-selector">
        <div class="folder-selector-heading">
          <div><span class="eyebrow">MEDIA FOLDERS</span><strong>{{ mediaDirectories().length }} folders mounted</strong></div>
          <div class="folder-totals"><span><b>{{ selectedDirectories().length }}</b> selected</span><span><b>{{ mediaFiles().length }}</b> files</span></div>
        </div>
        <div class="folder-combobox">
          <label for="folder-search">Find and select folders</label>
          <div class="folder-search-control" [class.is-open]="folderMenuOpen()">
            <span aria-hidden="true">⌕</span>
            <input id="folder-search" type="search" role="combobox" autocomplete="off" aria-autocomplete="list" aria-haspopup="dialog" aria-controls="folder-options" [attr.aria-expanded]="folderMenuOpen()" placeholder="Type a folder name…" [value]="folderQuery()" (focus)="openFolderMenu()" (input)="setFolderQuery($event)" (keydown.escape)="closeFolderMenu($event)">
            <button type="button" aria-label="Toggle folder choices" [attr.aria-expanded]="folderMenuOpen()" (click)="toggleFolderMenu($event)">⌄</button>
          </div>
          @if (folderMenuOpen()) {
            <div class="folder-menu" id="folder-options" role="dialog" aria-label="Choose media folders">
              <div class="folder-menu-actions"><button type="button" [disabled]="filteredDirectories().length === 0" (click)="selectAllFiltered()">Select all filtered</button><span>{{ filteredDirectories().length }} matches</span><button type="button" [disabled]="selectedDirectories().length === 0" (click)="clearSelection()">Clear</button></div>
              <fieldset class="folder-options"><legend class="sr-only">Media folders</legend>
                @for (folder of filteredDirectories(); track folder.relativePath) {
                  <label class="folder-option" [class.is-selected]="isSelected(folder.relativePath)"><input type="checkbox" [checked]="isSelected(folder.relativePath)" (change)="toggleFolder(folder)"><span><strong>{{ folder.name }}</strong><small>{{ folder.videoCount }} videos</small></span></label>
                } @empty { <p class="folder-empty">No folders match “{{ folderQuery() }}”.</p> }
              </fieldset>
            </div>
          }
        </div>
        @if (selectedDirectories().length) {
          <div class="folder-chips" aria-label="Selected folders">@for (folder of selectedDirectories(); track folder.relativePath) { <span>{{ folder.name }} <small>{{ folder.videoCount }}</small><button type="button" [attr.aria-label]="'Remove ' + folder.name" (click)="removeFolder(folder.relativePath)">×</button></span> }</div>
        } @else { <p class="folder-selection-hint">Select one or more folders to combine their files below.</p> }
      </section>
    }

    @if (folderFailures().length) { <div class="folder-failures" role="alert"><strong>{{ folderFailures().length }} folder requests failed</strong>@for (failure of folderFailures(); track failure.folder) { <span><b>{{ failure.folder }}</b>: {{ failure.message }}</span> }</div> }

    <section class="filter-bar" aria-label="Video filters">
      <label class="search-field"><span aria-hidden="true">⌕</span><input type="search" placeholder="Search filename or path" aria-label="Search videos" [value]="query()" (input)="setQuery($event)"></label>
      <label><span>Evidence</span><select aria-label="Filter by evidence state" [value]="evidenceState()" (change)="setEvidenceState($event)"><option>All</option><option>Not ingested</option><option>Ingested</option></select></label>
      <button class="icon-button" type="button" title="Reset filters" aria-label="Reset filters" (click)="resetFilters()">↺</button>
      <span class="result-count">{{ resultCount() }}</span>
    </section>
    <section class="table-shell">
      @if (selectedDirectories().length === 0) { <div class="state-panel"><strong>Select media folders</strong><p>Their real video files will appear together here. Nothing is imported automatically.</p></div> }
      @else if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading {{ selectedDirectories().length }} folders</strong></div> }
      @else if (filteredFiles().length === 0) { <div class="state-panel"><strong>No matching video files</strong><p>Change the search or evidence filter, or choose another folder.</p></div> }
      @else {
        <div class="media-file-groups">
          @for (group of visibleGroups(); track group.folderPath) {
            <section class="media-file-group" [attr.aria-labelledby]="'media-group-' + $index">
              <header class="media-group-header">
                <div><span class="eyebrow">CREATIVE</span><h2 [id]="'media-group-' + $index">{{ group.folderName }}</h2><p [title]="group.folderPath">{{ group.folderPath }}</p></div>
                <div class="media-group-actions"><span class="variant-count"><b>{{ group.files.length }}</b> {{ group.files.length === 1 ? 'variant' : 'variants' }}</span><a class="button button--compact" routerLink="/videos/detail" [queryParams]="{ folder: group.folderPath, file: group.files[0].relativePath }" [attr.aria-label]="'Open details for ' + group.folderName"><span aria-hidden="true">▶</span> Details</a></div>
              </header>
              <div class="data-table-scroll"><table class="data-table media-files-table"><thead><tr><th>Version</th><th>File</th><th>Size</th><th>Modified</th><th>Evidence state</th><th><span class="sr-only">Actions</span></th></tr></thead><tbody>@for (file of group.files; track file.relativePath) { <tr><td><strong>{{ file.variantName }}</strong><small>{{ extension(file.name) }}</small></td><td class="source-path" [title]="file.name">{{ file.name }}</td><td class="tabular">{{ fileSize(file.sizeBytes) }}</td><td>{{ modified(file.modifiedAt) }}</td><td><span class="status-badge" [class.status-badge--green]="file.ingested">{{ file.ingested ? (file.status || 'Ingested') : 'Not ingested' }}</span></td><td>@if (file.videoId) { <a class="icon-button table-action" [routerLink]="['/videos', file.videoId]" title="Open evidence record" [attr.aria-label]="'Open ' + file.displayName">↗</a> } @else { <button class="button button--compact" type="button" [disabled]="processingPath() === file.relativePath" (click)="ingestFile(file)">{{ processingPath() === file.relativePath ? 'Processing…' : 'Ingest' }}</button> }</td></tr> }</tbody></table></div>
            </section>
          }
        </div>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VideoLibraryPage {
  private readonly service = inject(CreativeIntelligenceService);
  private readonly elementRef = inject(ElementRef<HTMLElement>);
  private loadGeneration = 0;
  protected readonly directoriesLoading = signal(true);
  protected readonly loading = signal(false);
  protected readonly ingesting = signal(false);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected readonly ingestErrors = signal(0);
  protected readonly directory = signal('library');
  protected readonly recursive = signal(true);
  protected readonly mediaDirectories = signal<MediaDirectory[]>([]);
  protected readonly selectedPaths = signal<string[]>([]);
  protected readonly mediaFiles = signal<MediaFile[]>([]);
  protected readonly folderFailures = signal<FolderLoadFailure[]>([]);
  protected readonly folderQuery = signal('');
  protected readonly folderMenuOpen = signal(false);
  protected readonly processingPath = signal('');
  protected readonly query = signal('');
  protected readonly evidenceState = signal<'All' | 'Not ingested' | 'Ingested'>('All');
  protected readonly filteredDirectories = computed(() => filterMediaDirectories(this.mediaDirectories(), this.folderQuery()));
  protected readonly selectedDirectories = computed(() => { const selected = new Set(this.selectedPaths()); return this.mediaDirectories().filter(folder => selected.has(folder.relativePath)); });
  protected readonly ingestButtonLabel = computed(() => {
    if (this.ingesting()) return `Ingesting ${this.selectedDirectories().length} folders…`;
    const count = this.selectedDirectories().length;
    return `Ingest ${count} selected folder${count === 1 ? '' : 's'}`;
  });
  protected readonly displayFiles = computed<MediaFileView[]>(() => {
    const totals = new Map<string, number>();
    const positions = new Map<string, number>();
    for (const file of this.mediaFiles()) { const key = `${this.parentPath(file.relativePath)}|${mediaVariant(file.name)}`; totals.set(key, (totals.get(key) || 0) + 1); }
    return this.mediaFiles().map(file => {
      const folderPath = this.parentPath(file.relativePath);
      const variant = mediaVariant(file.name);
      const key = `${folderPath}|${variant}`;
      const position = (positions.get(key) || 0) + 1;
      positions.set(key, position);
      const suffix = (totals.get(key) || 0) > 1 ? `${variant} ${position}` : variant;
      const folderName = this.readableFolder(folderPath);
      return { ...file, folderName, folderPath, variantName: suffix, displayName: `${folderName} · ${suffix}` };
    });
  });
  protected readonly filteredFiles = computed(() => this.displayFiles().filter(item => {
    const search = this.query().trim().toLowerCase();
    return (!search || `${item.displayName} ${item.name} ${item.folderPath}`.toLowerCase().includes(search)) && (this.evidenceState() === 'All' || (this.evidenceState() === 'Ingested' ? item.ingested : !item.ingested));
  }));
  protected readonly visibleGroups = computed(() => groupMediaFilesByFolder(this.filteredFiles()));
  protected readonly resultCount = computed(() => resultCountLabel(this.visibleGroups().length, this.filteredFiles().length));

  constructor() {
    this.service.getMediaDirectories().subscribe({
      next: folders => { this.mediaDirectories.set(folders); this.directoriesLoading.set(false); },
      error: response => { this.directoriesLoading.set(false); this.error.set(response.error?.message || 'The media folder list could not be loaded.'); },
    });
  }

  @HostListener('document:click', ['$event'])
  protected handleOutsideClick(event: MouseEvent): void { if (!this.elementRef.nativeElement.querySelector('.folder-combobox')?.contains(event.target as Node)) this.folderMenuOpen.set(false); }
  protected openFolderMenu(): void { this.folderMenuOpen.set(true); }
  protected toggleFolderMenu(event: MouseEvent): void { event.stopPropagation(); this.folderMenuOpen.update(open => !open); }
  protected closeFolderMenu(event: Event): void { event.preventDefault(); event.stopPropagation(); this.folderMenuOpen.set(false); }
  protected setFolderQuery(event: Event): void { this.folderQuery.set((event.target as HTMLInputElement).value); this.folderMenuOpen.set(true); }
  protected isSelected(path: string): boolean { return this.selectedPaths().includes(path); }
  protected toggleFolder(folder: MediaDirectory): void { this.selectedPaths.update(paths => paths.includes(folder.relativePath) ? paths.filter(path => path !== folder.relativePath) : [...paths, folder.relativePath]); this.loadSelectedFiles(); }
  protected removeFolder(path: string): void { this.selectedPaths.update(paths => paths.filter(item => item !== path)); this.loadSelectedFiles(); }
  protected selectAllFiltered(): void { const paths = new Set(this.selectedPaths()); for (const folder of this.filteredDirectories()) paths.add(folder.relativePath); this.selectedPaths.set([...paths]); this.loadSelectedFiles(); }
  protected clearSelection(): void { this.selectedPaths.set([]); this.folderMenuOpen.set(false); this.loadSelectedFiles(); }
  protected setRecursive(event: Event): void { this.recursive.set((event.target as HTMLInputElement).checked); if (this.selectedPaths().length) this.loadSelectedFiles(); }

  protected ingestSelected(): void {
    const folders = this.selectedDirectories();
    if (!folders.length) return;
    this.ingesting.set(true); this.error.set(''); this.message.set(''); this.ingestErrors.set(0);
    from(folders).pipe(concatMap(folder => this.service.ingestDirectory(folder.relativePath, this.recursive()).pipe(map(result => ({ folder, result, error: '' })), catchError(response => of({ folder, result: null, error: response.error?.message || 'The folder could not be ingested.' })))), toArray()).subscribe(results => {
      const succeeded = results.filter(item => item.result !== null);
      const failed = results.filter(item => item.result === null);
      const ingested = succeeded.reduce((total, item) => total + (item.result?.ingested.length || 0), 0);
      const fileErrors = succeeded.reduce((total, item) => total + (item.result?.errors.length || 0), 0);
      this.ingesting.set(false); this.ingestErrors.set(fileErrors + failed.length); this.message.set(`${ingested} videos ingested across ${succeeded.length} of ${folders.length} selected folders.`);
      if (failed.length) this.error.set(failed.map(item => `${item.folder.name}: ${item.error}`).join(' '));
      this.loadSelectedFiles();
    });
  }
  protected ingestManual(): void {
    const path = this.directory().trim();
    if (!path) return;
    this.ingesting.set(true); this.error.set(''); this.message.set('');
    this.service.ingestDirectory(path, this.recursive()).subscribe({ next: result => { this.ingesting.set(false); this.ingestErrors.set(result.errors.length); this.message.set(`${result.ingested.length} of ${result.discovered} discovered videos ingested from the manual path.`); this.loadSelectedFiles(); }, error: response => { this.ingesting.set(false); this.error.set(response.error?.message || 'The folder could not be ingested.'); } });
  }
  protected ingestFile(file: MediaFile): void {
    this.processingPath.set(file.relativePath); this.error.set(''); this.message.set('');
    this.service.ingestVideo(file.relativePath).subscribe({ next: () => { this.processingPath.set(''); this.message.set(`${this.displayName(file)} was added to the evidence database.`); this.loadSelectedFiles(); }, error: response => { this.processingPath.set(''); this.error.set(response.error?.message || 'The video could not be ingested.'); } });
  }
  protected setQuery(event: Event): void { this.query.set((event.target as HTMLInputElement).value); }
  protected setEvidenceState(event: Event): void { this.evidenceState.set((event.target as HTMLSelectElement).value as 'All' | 'Not ingested' | 'Ingested'); }
  protected resetFilters(): void { this.query.set(''); this.evidenceState.set('All'); }
  protected extension(name: string): string { return name.includes('.') ? name.split('.').pop()!.toUpperCase() : 'VIDEO'; }
  protected fileSize(bytes: number | null): string { return bytes === null ? 'Unavailable' : new Intl.NumberFormat('en', { style: 'unit', unit: 'megabyte', maximumFractionDigits: 1 }).format(bytes / 1_000_000); }
  protected modified(value: string | null): string { return value ? new Date(value).toLocaleString() : 'Unavailable'; }
  private displayName(file: MediaFile): string { return this.displayFiles().find(item => item.relativePath === file.relativePath)?.displayName || file.name; }
  private parentPath(relativePath: string): string { return relativePath.slice(0, Math.max(0, relativePath.lastIndexOf('/'))); }
  private readableFolder(folderPath: string): string { const folder = folderPath.split('/').pop()?.trim() || 'Video'; return folder.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').replace(/\b\p{L}/gu, letter => letter.toUpperCase()); }
  private loadSelectedFiles(): void {
    const paths = this.selectedPaths();
    const generation = ++this.loadGeneration;
    this.folderFailures.set([]);
    if (!paths.length) { this.mediaFiles.set([]); this.loading.set(false); return; }
    this.loading.set(true);
    forkJoin(paths.map(path => this.service.getMediaFiles(path, this.recursive()).pipe(map(files => ({ path, files, error: '' })), catchError(response => of({ path, files: [] as MediaFile[], error: response.error?.message || 'The media API did not respond.' }))))).subscribe(results => {
      if (generation !== this.loadGeneration) return;
      this.mediaFiles.set(mergeMediaFiles(results.map(result => result.files)));
      this.folderFailures.set(results.filter(result => result.error).map(result => ({ folder: this.mediaDirectories().find(folder => folder.relativePath === result.path)?.name || result.path, message: result.error })));
      this.loading.set(false);
    });
  }
}
