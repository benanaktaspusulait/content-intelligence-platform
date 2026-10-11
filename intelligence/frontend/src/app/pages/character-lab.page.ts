import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CharacterCoverage, CharacterIdentity, CreativeIntelligenceService } from '../core/creative-intelligence.service';

interface FormatColumn { label: string; key: string; }

@Component({
  selector: 'app-character-lab-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">CHARACTER LAB</span><h1>Coverage Matrix</h1><p>Coverage is calculated only from imported observations assigned to a character.</p></div></header>
    <section class="coverage-key"><span><i class="coverage-cell level-0"></i>No evidence</span><span><i class="coverage-cell level-1"></i>1–3</span><span><i class="coverage-cell level-2"></i>4–8</span><span><i class="coverage-cell level-3"></i>9+</span></section>
    <section class="matrix-shell">
      @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading character evidence</strong></div> }
      @else if (error()) { <div class="state-panel state-panel--error"><strong>Character evidence unavailable</strong><p>{{ error() }}</p></div> }
      @else { <div class="matrix-scroll"><table class="coverage-matrix"><thead><tr><th>Character</th>@for (format of formats; track format.key) {<th>{{ format.label }}</th>}<th>Observations</th><th>Confidence</th></tr></thead><tbody>
        @for (character of characters(); track character.id) {<tr><th><span class="character-chip" [style.--character-color]="color(character.name)"><i>{{ code(character.name) }}</i><span><strong>{{ character.name }}</strong><small>{{ readable(character.status) }}</small></span></span></th>@for (format of formats; track format.key) {<td><span class="coverage-cell" [class.level-0]="level(count(character, format.key)) === 0" [class.level-1]="level(count(character, format.key)) === 1" [class.level-2]="level(count(character, format.key)) === 2" [class.level-3]="level(count(character, format.key)) === 3"><span>{{ countLabel(count(character, format.key)) }}</span></span></td>}<td class="numeric tabular"><strong>{{ character.observations }}</strong></td><td><span class="confidence" [class.confidence--high]="character.confidence === 'HIGH'" [class.confidence--medium]="character.confidence === 'MEDIUM'">{{ readable(character.confidence) }}</span></td></tr>}
      </tbody></table></div> }
    </section>
    @if (!loading() && !error() && gap(); as item) { <section class="section-band evidence-gap"><div><span class="eyebrow">EVIDENCE GAP</span><h2>{{ item.name }} has no imported performance evidence</h2><p>Import performance observations and assign matching videos to {{ item.name }} before character-level comparison.</p></div></section> }
    @if (!loading() && !error()) { <section class="section-band"><div class="section-heading"><div><span class="eyebrow">CANONICAL IDENTITIES</span><h2>Character records</h2></div><span class="data-freshness">Persisted character registry</span></div><div class="data-table-scroll"><table class="data-table"><thead><tr><th>Character</th><th>Status</th><th>Identity ID</th><th>Notes</th><th>References</th></tr></thead><tbody>@for (character of identities(); track character.id) {<tr><td><strong>{{ character.name }}</strong></td><td>{{ readable(character.status) }}</td><td><code>{{ character.id }}</code></td><td>{{ character.notes || '—' }}</td><td><button type="button" class="reference-action" (click)="openReferences(character)">Manage references</button></td></tr>}</tbody></table></div></section>
      @if (referenceCharacter(); as character) { <section class="section-band character-reference-manager"><div class="section-heading"><div><span class="eyebrow">CANONICAL VISUAL IDENTITY</span><h2>{{ character.name }} reference images</h2><p>Upload a real reference, inspect it, then explicitly approve it. Approval records the immutable image hash; it never generates an image.</p></div><button type="button" class="reference-action" (click)="referenceCharacter.set(null)">Close</button></div><div class="reference-upload"><label>Upload reference image (PNG, JPEG or WebP, up to 15 MB)<input type="file" accept="image/png,image/jpeg,image/webp" (change)="uploadReference($event)" [disabled]="referenceBusy()" /></label><label>Description / source note<input type="text" [value]="referenceDescription()" (input)="referenceDescription.set(($any($event.target)).value)" placeholder="Canonical source and what this reference shows" /></label></div>@if (referenceError()) { <p class="state-panel state-panel--error">{{ referenceError() }}</p> }<div class="character-reference-list">@for (reference of characterReferences(); track reference.id) {<article><img [src]="reference.previewUrl" [alt]="character.name + ' reference candidate v' + reference.version" /><div><strong>Version {{ reference.version }} · {{ readable(reference.status) }}</strong><p>{{ reference.description || 'No description supplied' }}</p><code>{{ reference.sha256 }}</code><small>Uploaded {{ reference.createdAt }} {{ reference.approvedAt ? '· Approved ' + reference.approvedAt + ' by ' + reference.approvedBy : '' }}</small>@if (reference.status === 'PENDING_REVIEW') {<label class="approval-field">Reviewer<input type="text" [value]="reviewerName()" (input)="reviewerName.set(($any($event.target)).value)" placeholder="Your name" /></label><button type="button" class="reference-action reference-action--approve" [disabled]="referenceBusy() || !reviewerName().trim()" (click)="approveReference(reference)">I reviewed this image — approve</button>}</div></article>} @empty {<p>No reference image has been uploaded for {{ character.name }}.</p>}</div></section> }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`.character-reference-manager{margin-top:1rem}.reference-upload{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem;margin:1rem 0}.reference-upload label,.approval-field{display:grid;gap:.4rem}.character-reference-list{display:grid;gap:.75rem}.character-reference-list article{display:grid;grid-template-columns:180px minmax(0,1fr);gap:1rem;padding:1rem;border:1px solid #d8e1ec;border-radius:10px;background:#fff}.character-reference-list img{width:180px;max-height:200px;object-fit:contain;background:#f3f5f3;border-radius:6px}.character-reference-list article>div{display:grid;align-content:start;gap:.5rem}.character-reference-list p{margin:0}.character-reference-list code{overflow-wrap:anywhere}.reference-action{padding:.55rem .8rem;border:1px solid #b7c8ba;border-radius:6px;background:#fff;color:#31583b;font-weight:700;cursor:pointer}.reference-action--approve{justify-self:start;background:#31583b;color:white}.reference-action:disabled{opacity:.5}.state-panel--error{color:#9c3426}@media(max-width:650px){.reference-upload,.character-reference-list article{grid-template-columns:1fr}.character-reference-list img{width:100%;max-height:280px}}`],
})
export class CharacterLabPage {
  private readonly service = inject(CreativeIntelligenceService);
  private readonly http = inject(HttpClient);
  protected readonly formats: FormatColumn[] = [
    { label: 'Reveal', key: 'REVEAL' },
    { label: 'Pick One', key: 'PICK_ONE' },
    { label: 'Word Game', key: 'WORD_GAME' },
    { label: 'Grammar', key: 'GRAMMAR' },
    { label: 'Mini Sitcom', key: 'MINI_SITCOM' },
    { label: 'Audio Quiz', key: 'AUDIO_QUIZ' },
  ];
  protected readonly characters = signal<CharacterCoverage[]>([]);
  protected readonly identities = signal<CharacterIdentity[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly referenceCharacter = signal<CharacterIdentity | null>(null);
  protected readonly characterReferences = signal<any[]>([]);
  protected readonly referenceBusy = signal(false);
  protected readonly referenceError = signal('');
  protected readonly referenceDescription = signal('');
  protected readonly reviewerName = signal('');
  protected readonly gap = computed(() => this.characters().find(item => item.observations === 0) || null);

  constructor() {
    this.service.getCharacterCoverage().subscribe({
      next: records => { this.characters.set(records); this.service.getCharacters().subscribe({ next: identities => { this.identities.set(identities); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The character registry did not respond.'); this.loading.set(false); } }); },
      error: response => { this.error.set(response.error?.message || 'The evidence API did not respond.'); this.loading.set(false); },
    });
  }

  protected count(character: CharacterCoverage, format: string): number { return character.formatObservations[format] || 0; }
  protected level(value: number): number { return value === 0 ? 0 : value <= 3 ? 1 : value <= 8 ? 2 : 3; }
  protected countLabel(value: number): string { return value === 0 ? '—' : String(value); }
  protected code(name: string): string { return name.slice(0, 2).toUpperCase(); }
  protected color(name: string): string { return ({ Kiko: '#e8a5b1', Opa: '#a5c58c', Mimi: '#91b9d2', Arda: '#d8b46d', Luca: '#9caeb4', Noah: '#c69bd3' } as Record<string, string>)[name] || '#aab2aa'; }
  protected readable(value: string): string { return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()); }
  protected openReferences(character: CharacterIdentity): void { this.referenceCharacter.set(character); this.characterReferences.set([]); this.referenceError.set(''); this.http.get<any[]>(`/api/v1/characters/${character.id}/references`).subscribe({ next: rows => this.characterReferences.set(rows), error: response => this.referenceError.set(response.error?.message || 'Could not load character references.') }); }
  protected uploadReference(event: Event): void { const file=(event.target as HTMLInputElement).files?.[0]; const character=this.referenceCharacter(); if(!file||!character)return; const form=new FormData(); form.append('file',file); this.referenceBusy.set(true); this.referenceError.set(''); this.http.post<any>(`/api/v1/characters/${character.id}/references?description=${encodeURIComponent(this.referenceDescription())}`,form).subscribe({next:()=>{this.referenceDescription.set('');this.referenceBusy.set(false);this.openReferences(character);},error:response=>{this.referenceError.set(response.error?.message||'Could not upload the reference image.');this.referenceBusy.set(false);}}); }
  protected approveReference(reference: any): void { const character=this.referenceCharacter(); if(!character||!this.reviewerName().trim())return; this.referenceBusy.set(true); this.referenceError.set(''); this.http.post(`/api/v1/characters/${character.id}/references/${reference.id}/approve`,{reviewer:this.reviewerName().trim()}).subscribe({next:()=>{this.referenceBusy.set(false);this.openReferences(character);},error:response=>{this.referenceError.set(response.error?.message||'Could not approve this reference.');this.referenceBusy.set(false);}}); }
}
