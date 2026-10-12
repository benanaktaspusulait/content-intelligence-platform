import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CreativeIntelligenceService, ContentSummary, PromptVersionSummary, PromptQualityRecord } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-prompt-workspace-page',
  imports: [FormsModule, RouterLink],
  template: `
    <header class="page-header">
      <div>
        <span class="eyebrow">CONTENT WORKSPACE</span>
        <h1>Prompt Versions</h1>
        <p>Browse and manage content records, prompt versions, and quality assessments.</p>
      </div>
    </header>

    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading workspace</strong></div> }
    @else if (error()) { <div class="state-panel"><strong>Error</strong><p class="muted">{{ error() }}</p></div> }
    @else {

      <!-- Content Workspaces -->
      <section class="section-band">
        <div class="section-heading">
          <div><span class="eyebrow">CONTENT RECORDS</span><h2>Workspaces</h2></div>
          <button class="button button--compact" type="button" (click)="showCreateForm()">New workspace</button>
        </div>

        @if (createFormVisible()) {
          <div class="state-panel" style="margin-bottom:1rem">
            <form (ngSubmit)="createWorkspace()">
              <label>Title<input [(ngModel)]="newTitle" name="title" required placeholder="Content title" /></label>
              <label>Description<textarea [(ngModel)]="newDescription" name="description" rows="2" placeholder="Optional description"></textarea></label>
              <label>Type<select [(ngModel)]="newType" name="type"><option value="SHORT">Short</option><option value="REEL">Reel</option><option value="EPISODE">Episode</option></select></label>
              <div style="display:flex;gap:0.5rem;margin-top:0.5rem">
                <button class="button" type="submit" [disabled]="creating()">Create</button>
                <button class="button button--secondary" type="button" (click)="createFormVisible.set(false)">Cancel</button>
              </div>
            </form>
          </div>
        }

        @if (workspaces().length === 0) { <p class="muted">No content workspaces found.</p> }
        @else {
          <div class="metric-strip">@for (ws of workspaces(); track ws.id) {
            <div class="metric-card" style="cursor:pointer" (click)="selectWorkspace(ws)">
              <span>{{ ws.title }}</span>
              <strong>{{ ws.type }}</strong>
              <small>v{{ ws.latestPromptVersionNumber ?? '—' }} · {{ ws.status.toLowerCase() }}</small>
              @if (selectedWorkspace()?.id === ws.id) { <span class="status-badge">Selected</span> }
            </div>
          }</div>
        }
      </section>

      <!-- Prompt Versions -->
      @if (selectedWorkspace(); as ws) {
        <section class="section-band">
          <div class="section-heading">
            <div><span class="eyebrow">PROMPT VERSIONS</span><h2>{{ ws.title }}</h2></div>
            <button class="button button--compact" type="button" (click)="showNewPromptForm()">New version</button>
          </div>

          @if (showNewPrompt()) {
            <div class="state-panel" style="margin-bottom:1rem">
              <form (ngSubmit)="createPrompt()">
                <label>Prompt text<textarea [(ngModel)]="newPromptText" name="rawText" rows="6" required placeholder="Enter prompt text"></textarea></label>
                <label>Parent version<select [(ngModel)]="newPromptParent" name="parent"><option [value]="null">None (root version)</option>@for (pv of versions(); track pv.id) { <option [value]="pv.id">v{{ pv.versionNumber }}</option> }</select></label>
                <div style="display:flex;gap:0.5rem;margin-top:0.5rem">
                  <button class="button" type="submit" [disabled]="creatingPrompt()">Save version</button>
                  <button class="button button--secondary" type="button" (click)="showNewPrompt.set(false)">Cancel</button>
                </div>
              </form>
            </div>
          }

          @if (versions().length === 0) { <p class="muted">No prompt versions for this content.</p> }
          @else {
            <div class="table-wrapper">
              <table>
                <thead><tr><th>Version</th><th>Source</th><th>Created</th><th>Actions</th></tr></thead>
                <tbody>@for (pv of versions(); track pv.id) {
                  <tr @if (selectedVersion()?.id === pv.id) { style="background:var(--surface-2,#f5f5f5)" }
                    <td><strong>v{{ pv.versionNumber }}</strong></td>
                    <td><code>{{ pv.sourcePath ?? '—' }}</code></td>
                    <td>{{ date(pv.createdAt) }}</td>
                    <td><button class="button button--compact" type="button" (click)="selectVersion(pv)">View</button></td>
                  </tr>
                }</tbody>
              </table>
            </div>
          }
        </section>

        <!-- Selected Version Detail -->
        @if (selectedVersion(); as pv) {
          <section class="section-band">
            <div class="section-heading">
              <div><span class="eyebrow">PROMPT DETAIL</span><h2>Version {{ pv.versionNumber }}</h2></div>
            </div>
            <div class="state-panel">
              <pre style="white-space:pre-wrap;word-break:break-word;font-size:0.875rem">{{ pv.rawText ?? 'No text' }}</pre>
              @if (pv.sourcePath) { <p class="muted">Source: {{ pv.sourcePath }}</p> }
              @if (pv.sourceSha256) { <p class="muted">SHA-256: <code>{{ pv.sourceSha256 }}</code></p> }
            </div>
          </section>

          <!-- Linked Videos -->
          <section class="section-band">
            <div class="section-heading">
              <div><span class="eyebrow">LINEAGE</span><h2>Linked Videos</h2></div>
            </div>
            @if (linkedVideosLoading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading linked videos</strong></div> }
            @else if (linkedVideos().length === 0) { <p class="muted">No videos linked to this prompt version yet.</p> }
            @else {
              <div class="metric-strip">@for (v of linkedVideos(); track v.videoId) {
                <div class="metric-card">
                  <span><a [routerLink]="['/videos', v.videoId]">{{ v.videoId.substring(0, 8) }}</a></span>
                  <small><code>{{ v.relativePath }}</code></small>
                </div>
              }</div>
            }
          </section>

          <!-- Creative Provenance -->
          <section class="section-band">
            <div class="section-heading">
              <div><span class="eyebrow">PROVENANCE</span><h2>Creative Origin</h2></div>
            </div>
            @if (provenanceLoading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading provenance</strong></div> }
            @else if (provenance()) {
              <div class="state-panel">
                <dl class="compact-facts">
                  <div><dt>Origin</dt><dd>{{ provenance()!.origin || 'MANUAL_OR_LEGACY' }}</dd></div>
                  @if (provenance()!.provider) { <div><dt>Provider</dt><dd>{{ provenance()!.provider }}</dd></div> }
                  @if (provenance()!.model) { <div><dt>Model</dt><dd>{{ provenance()!.model }}</dd></div> }
                  @if (provenance()!.operatorEdited !== undefined) { <div><dt>Operator edited</dt><dd>{{ provenance()!.operatorEdited ? 'Yes' : 'No' }}</dd></div> }
                </dl>
              </div>
            } @else { <p class="muted">No creative provenance recorded for this version.</p> }
          </section>
        }
      }

      <!-- Quality Summary -->
      <section class="section-band">
        <div class="section-heading">
          <div><span class="eyebrow">QUALITY ASSESSMENT</span><h2>Prompt Quality Records</h2></div>
        </div>
        @if (qualityLoading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading quality records</strong></div> }
        @else if (qualityRecords().length === 0) { <p class="muted">No quality records found.</p> }
        @else {
          <div class="table-wrapper">
            <table>
              <thead><tr><th>Title</th><th>Version</th><th>Grade</th><th>Readiness</th><th>Score</th><th>Summary</th></tr></thead>
              <tbody>@for (qr of qualityRecords(); track qr.contentId) {
                <tr>
                  <td><strong>{{ qr.title }}</strong></td>
                  <td>v{{ qr.versionNumber ?? '—' }}</td>
                  <td>@if (qr.latestQuality?.creativeGrade) { <span class="status-badge">{{ qr.latestQuality.creativeGrade }}</span> } @else { <span class="muted">—</span> }</td>
                  <td>{{ qr.latestQuality?.readiness ?? '—' }}</td>
                  <td>{{ number(qr.latestQuality?.overallScore) }}</td>
                  <td class="muted">{{ qr.latestQuality?.summary ?? '—' }}</td>
                </tr>
              }</tbody>
            </table>
          </div>
        }
      </section>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromptWorkspacePage {
  private readonly service = inject(CreativeIntelligenceService);

  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly workspaces = signal<ContentSummary[]>([]);
  protected readonly versions = signal<PromptVersionSummary[]>([]);
  protected readonly qualityRecords = signal<PromptQualityRecord[]>([]);
  protected readonly qualityLoading = signal(true);

  protected readonly selectedWorkspace = signal<ContentSummary | null>(null);
  protected readonly selectedVersion = signal<PromptVersionSummary | null>(null);

  protected readonly createFormVisible = signal(false);
  protected readonly showNewPrompt = signal(false);
  protected readonly creating = signal(false);
  protected readonly creatingPrompt = signal(false);
  protected readonly linkedVideos = signal<Array<{videoId: string; relativePath: string}>>([]);
  protected readonly linkedVideosLoading = signal(false);
  protected readonly provenance = signal<Record<string, unknown> | null>(null);
  protected readonly provenanceLoading = signal(false);

  protected newTitle = '';
  protected newDescription = '';
  protected newType = 'SHORT';
  protected newPromptText = '';
  protected newPromptParent: number | null = null;

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true);
    this.service.getContentWorkspaces().subscribe({
      next: workspaces => {
        this.workspaces.set(workspaces);
        this.loading.set(false);
        if (workspaces.length > 0) this.selectWorkspace(workspaces[0]);
      },
      error: err => { this.error.set(err.error?.message || 'Failed to load workspaces.'); this.loading.set(false); },
    });
    this.loadQuality();
  }

  private loadQuality(): void {
    this.qualityLoading.set(true);
    this.service.getPromptQualitySummary().subscribe({
      next: records => { this.qualityRecords.set(records); this.qualityLoading.set(false); },
      error: () => { this.qualityRecords.set([]); this.qualityLoading.set(false); },
    });
  }

  protected showCreateForm(): void { this.createFormVisible.set(true); this.newTitle = ''; this.newDescription = ''; this.newType = 'SHORT'; }

  protected createWorkspace(): void {
    if (!this.newTitle.trim()) return;
    this.creating.set(true);
    this.service.createContentWorkspace({ title: this.newTitle.trim(), description: this.newDescription || undefined, type: this.newType }).subscribe({
      next: ws => {
        this.workspaces.update(arr => [ws, ...arr]);
        this.creating.set(false);
        this.createFormVisible.set(false);
        this.selectWorkspace(ws);
      },
      error: err => { this.creating.set(false); this.error.set(err.error?.message || 'Failed to create workspace.'); },
    });
  }

  protected selectWorkspace(ws: ContentSummary): void {
    this.selectedWorkspace.set(ws);
    this.selectedVersion.set(null);
    this.service.getPromptVersions(ws.id).subscribe({
      next: versions => this.versions.set(versions),
      error: () => this.versions.set([]),
    });
  }

  protected showNewPromptForm(): void { this.showNewPrompt.set(true); this.newPromptText = ''; this.newPromptParent = null; }

  protected createPrompt(): void {
    const ws = this.selectedWorkspace();
    if (!ws || !this.newPromptText.trim()) return;
    this.creatingPrompt.set(true);
    this.service.createPromptVersion(ws.id, { rawText: this.newPromptText.trim(), parentPromptVersionId: this.newPromptParent || undefined }).subscribe({
      next: pv => {
        this.versions.update(arr => [pv, ...arr]);
        this.creatingPrompt.set(false);
        this.showNewPrompt.set(false);
        this.selectedVersion.set(pv);
      },
      error: err => { this.creatingPrompt.set(false); this.error.set(err.error?.message || 'Failed to create prompt version.'); },
    });
  }

  protected selectVersion(pv: PromptVersionSummary): void {
    this.selectedVersion.set(pv);
    const ws = this.selectedWorkspace();
    if (!ws) return;
    // Load linked videos
    this.linkedVideosLoading.set(true);
    this.service.getPromptLinkedVideos(ws.id, pv.id).subscribe({
      next: videos => { this.linkedVideos.set(videos); this.linkedVideosLoading.set(false); },
      error: () => { this.linkedVideos.set([]); this.linkedVideosLoading.set(false); },
    });
    // Load creative provenance
    this.provenanceLoading.set(true);
    this.service.getPromptCreativeProvenance(ws.id, pv.id).subscribe({
      next: p => { this.provenance.set(p); this.provenanceLoading.set(false); },
      error: () => { this.provenance.set(null); this.provenanceLoading.set(false); },
    });
  }

  protected date(value: string | null): string { return value ? new Date(value).toLocaleString() : '—'; }
  protected number(value: number | null | undefined): string { return value === null || value === undefined ? '—' : value.toFixed(2); }
}
