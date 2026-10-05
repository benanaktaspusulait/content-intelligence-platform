import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, TestPlannerView } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-test-planner-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">QUEUE DESIGN</span><h1>Test Planner</h1><p>Read-only planning guidance from the canonical experiment domain.</p></div><span class="status-badge">READ ONLY</span></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading planner</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Planner unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else if (data(); as planner) {
      <div class="dashboard-grid">
        <section class="section-band"><span class="eyebrow">RECOMMENDED ALLOCATION</span><h2>Planning mix</h2><dl class="compact-facts">@for (item of allocation(planner); track item[0]) { <div><dt>{{ readable(item[0]) }}</dt><dd>{{ item[1] }}%</dd></div> }</dl></section>
        <section class="section-band"><span class="eyebrow">CURRENT EXPERIMENT COUNTS</span><h2>Persisted plans</h2><dl class="compact-facts">@for (item of allocation(planner, true); track item[0]) { <div><dt>{{ readable(item[0]) }}</dt><dd>{{ item[1] }}</dd></div> } @empty { <div><dt>Experiments</dt><dd>0</dd></div> }</dl><p class="muted">Characters without a linked experiment: {{ planner.charactersWithoutTests }}</p></section>
      </div>
      <section class="section-band"><span class="eyebrow">GUARDRAILS</span><h2>Current planning rules</h2><ul>@for (guardrail of planner.guardrails; track guardrail) { <li>{{ guardrail }}</li> }</ul></section>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TestPlannerPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly data = signal<TestPlannerView | null>(null);
  constructor() { this.load(); }
  protected load(): void { this.loading.set(true); this.error.set(''); this.service.getTestPlanner().subscribe({ next: value => { this.data.set(value); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The planner API did not respond.'); this.loading.set(false); } }); }
  protected allocation(planner: TestPlannerView, current = false): Array<[string, number]> { return Object.entries(current ? planner.currentExperimentCounts : planner.recommendedAllocation); }
  protected readable(value: string): string { return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()); }
}
