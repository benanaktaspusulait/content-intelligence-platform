import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, ModelVersionRecord } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-models-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">MODEL REGISTRY</span><h1>Model Versions</h1><p>Historical model registrations. Active predictions use the cold-start baseline; trained inference and promotion are unavailable.</p></div></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading models</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Models unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else { <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PERSISTED REGISTRY</span><h2>{{ models().length }} versions</h2></div><span class="status-badge">Backend policy</span></div>@if (!models().length) { <div class="state-panel compact-state"><strong>No model versions registered</strong><p>Training and registration must happen through the existing backend workflow.</p></div> } @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Model</th><th>Platform</th><th>Status</th><th>Dataset</th><th>Features</th><th>Trained</th><th></th></tr></thead><tbody>@for (model of models(); track model.id) { <tr><td><strong>{{ model.modelType }} · {{ model.version }}</strong><small>{{ model.id }}</small></td><td>{{ model.platform }}</td><td><span class="status-badge"  [class.status-badge--amber]="model.status === 'CHALLENGER'">{{ model.status }}</span></td><td>{{ model.trainingDatasetVersion }}</td><td>{{ model.featureVersion }}</td><td>{{ date(model.trainedAt) }}</td><td>@if (model.status === 'CHALLENGER') { <button class="button button--compact" type="button" [disabled]="true" (click)="promote(model)">{{ promoting() === model.id ? 'Promoting…' : 'Promotion unavailable' }}</button> } @else { <span class="muted">{{ model.status === 'CHAMPION' ? 'Historical champion metadata' : 'Retired' }}</span> }</td></tr> }</tbody></table></div> } @if (actionError()) { <p class="amber-text">{{ actionError() }}</p> }</section> }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModelsPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly actionError = signal('');
  protected readonly promoting = signal('');
  protected readonly models = signal<ModelVersionRecord[]>([]);
  constructor() { this.load(); }
  protected load(): void { this.loading.set(true); this.error.set(''); this.service.getModels().subscribe({ next: value => { this.models.set(value); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The model registry did not respond.'); this.loading.set(false); } }); }
  protected promote(model: ModelVersionRecord): void { if (!window.confirm(`Promote ${model.modelType} ${model.version} to champion?`)) return; this.promoting.set(model.id); this.actionError.set(''); this.service.promoteModel(model.id, 'Operator promotion from Model Versions').subscribe({ next: updated => { this.models.update(items => items.map(item => item.platform === updated.platform && item.modelType === updated.modelType ? (item.id === updated.id ? updated : { ...item, status: item.status === 'CHAMPION' ? 'RETIRED' : item.status }) : item)); this.promoting.set(''); }, error: response => { this.actionError.set(response.error?.message || 'Model promotion was rejected.'); this.promoting.set(''); } }); }
  protected date(value: string): string { return new Date(value).toLocaleString(); }
}
