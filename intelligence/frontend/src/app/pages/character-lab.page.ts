import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
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
    @if (!loading() && !error()) { <section class="section-band"><div class="section-heading"><div><span class="eyebrow">CANONICAL IDENTITIES</span><h2>Character records</h2></div><span class="data-freshness">Persisted character registry</span></div><div class="data-table-scroll"><table class="data-table"><thead><tr><th>Character</th><th>Status</th><th>Identity ID</th><th>Notes</th></tr></thead><tbody>@for (character of identities(); track character.id) {<tr><td><strong>{{ character.name }}</strong></td><td>{{ readable(character.status) }}</td><td><code>{{ character.id }}</code></td><td>{{ character.notes || '—' }}</td></tr>}</tbody></table></div></section> }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CharacterLabPage {
  private readonly service = inject(CreativeIntelligenceService);
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
}
