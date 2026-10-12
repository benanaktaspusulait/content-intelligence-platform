import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, CharacterIdentity, CharacterReference, ContentSummary } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-content-history-page',
  imports: [],
  template: `
    <header class="page-header">
      <div>
        <span class="eyebrow">HISTORICAL BROWSER</span>
        <h1>Content History</h1>
        <p>Browse characters, content records, and their historical references.</p>
      </div>
    </header>

    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading history</strong></div> }
    @else if (error()) { <div class="state-panel"><strong>Error</strong><p class="muted">{{ error() }}</p></div> }
    @else {

      <!-- Characters -->
      <section class="section-band">
        <div class="section-heading">
          <div><span class="eyebrow">CHARACTERS</span><h2>Character History</h2></div>
        </div>
        @if (characters().length === 0) { <p class="muted">No characters found.</p> }
        @else {
          <div class="metric-strip">@for (ch of characters(); track ch.id) {
            <div class="metric-card" style="cursor:pointer" (click)="selectCharacter(ch)">
              <span>{{ ch.name }}</span>
              <strong>{{ ch.status.toLowerCase() }}</strong>
              <small>@if (ch.active) { Active } @else { Inactive }</small>
              @if (selectedCharacter()?.id === ch.id) { <span class="status-badge">Selected</span> }
            </div>
          }</div>
        }
      </section>

      <!-- Character References -->
      @if (selectedCharacter(); as ch) {
        <section class="section-band">
          <div class="section-heading">
            <div><span class="eyebrow">REFERENCES</span><h2>{{ ch.name }} — Reference Images</h2></div>
          </div>
          @if (charRefLoading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading references</strong></div> }
          @else if (characterReferences().length === 0) { <p class="muted">No reference images for this character.</p> }
          @else {
            <div class="metric-strip">@for (ref of characterReferences(); track ref.id) {
              <div class="metric-card">
                <span>@if (ref.approved) { <span class="status-badge">Approved</span> } {{ ref.description ?? 'Reference' }}</span>
                @if (ref.previewUrl) { <a [href]="ref.previewUrl" target="_blank" rel="noopener">View image</a> }
                <small>Uploaded {{ date(ref.uploadedAt) }}</small>
                @if (ref.approvedBy) { <small>by {{ ref.approvedBy }}</small> }
              </div>
            }</div>
          }
        </section>
      }

      <!-- Content Records -->
      <section class="section-band">
        <div class="section-heading">
          <div><span class="eyebrow">CONTENT RECORDS</span><h2>Historical Content</h2></div>
        </div>
        @if (contentLoading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading content records</strong></div> }
        @else if (contentRecords().length === 0) { <p class="muted">No content records found.</p> }
        @else {
          <div class="table-wrapper">
            <table>
              <thead><tr><th>Title</th><th>Type</th><th>Status</th><th>Latest Version</th><th>Updated</th></tr></thead>
              <tbody>@for (cr of contentRecords(); track cr.id) {
                <tr>
                  <td><strong>{{ cr.title }}</strong></td>
                  <td>{{ cr.type }}</td>
                  <td><span class="status-badge">{{ cr.status.toLowerCase() }}</span></td>
                  <td>v{{ cr.latestPromptVersionNumber ?? '—' }}</td>
                  <td>{{ date(cr.updatedAt) }}</td>
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
export class ContentHistoryPage {
  private readonly service = inject(CreativeIntelligenceService);

  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly characters = signal<CharacterIdentity[]>([]);
  protected readonly characterReferences = signal<CharacterReference[]>([]);
  protected readonly charRefLoading = signal(false);
  protected readonly contentRecords = signal<ContentSummary[]>([]);
  protected readonly contentLoading = signal(true);

  protected readonly selectedCharacter = signal<CharacterIdentity | null>(null);

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true);
    this.service.getCharacters().subscribe({
      next: characters => {
        this.characters.set(characters);
        this.loading.set(false);
      },
      error: err => { this.error.set(err.error?.message || 'Failed to load characters.'); this.loading.set(false); },
    });
    this.service.getContentWorkspaces().subscribe({
      next: records => { this.contentRecords.set(records); this.contentLoading.set(false); },
      error: () => { this.contentRecords.set([]); this.contentLoading.set(false); },
    });
  }

  protected selectCharacter(ch: CharacterIdentity): void {
    this.selectedCharacter.set(ch);
    this.charRefLoading.set(true);
    this.service.getCharacterReferences(ch.id).subscribe({
      next: refs => { this.characterReferences.set(refs); this.charRefLoading.set(false); },
      error: () => { this.characterReferences.set([]); this.charRefLoading.set(false); },
    });
  }

  protected date(value: string | null): string { return value ? new Date(value).toLocaleString() : '—'; }
}
