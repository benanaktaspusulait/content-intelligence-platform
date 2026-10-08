import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { CreativeIntelligenceService, ModelVersionRecord } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-models-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">MODEL REGISTRY</span><h1>Model Versions</h1><p>Historical model registrations. Pre-publish predictions use a verified statistical champion when available; otherwise cold-start remains active. Live predictions retain their separate baseline.</p></div></header>
    <section class="section-band"><label>Training platform<select [value]="trainingPlatform()" (change)="trainingPlatform.set(value($event))"><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="tiktok">TikTok</option></select></label><label>Reason<input [value]="trainingReason()" (input)="trainingReason.set(value($event))"></label><button type="button" [disabled]="training() || !trainingReason().trim()" (click)="train()">{{training() ? 'Training…' : 'Train verified 72H challenger'}}</button><p>Requires 30 independent parent videos, verified publications and pre-publish feature snapshots. Training does not activate the challenger.</p></section>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading models</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Models unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else { <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PERSISTED REGISTRY</span><h2>{{ models().length }} versions</h2></div><span class="status-badge">Backend policy</span></div>@if (!models().length) { <div class="state-panel compact-state"><strong>No model versions registered</strong><p>Training and registration must happen through the existing backend workflow.</p></div> } @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Model</th><th>Platform</th><th>Status</th><th>Dataset</th><th>Features</th><th>Trained</th><th></th></tr></thead><tbody>@for (model of models(); track model.id) { <tr><td><strong>{{ model.modelType }} · {{ model.version }}</strong><small>{{ model.id }}</small></td><td>{{ model.platform }}</td><td><span class="status-badge"  [class.status-badge--amber]="model.status === 'CHALLENGER'">{{ model.status }}</span></td><td>{{ model.trainingDatasetVersion }}</td><td>{{ model.featureVersion }}</td><td>{{ date(model.trainedAt) }}</td><td>@if (model.status === 'CHALLENGER') { <button class="button button--compact" type="button" [disabled]="!canPromote(model) || !!promoting()" (click)="promote(model)">{{ promoting() === model.id ? 'Promoting…' : canPromote(model) ? 'Promote verified artifact' : 'Promotion unavailable' }}</button> } @else { <span class="muted">{{ model.status === 'CHAMPION' && verified(model) ? 'Active pre-publish artifact' : 'Historical registry metadata' }}</span>@if (model.status === 'RETIRED' && verified(model)) {<button type="button" (click)="rollback(model)" [disabled]="!!promoting()">Restore verified artifact</button>} }</td></tr> }</tbody></table></div> } @if (actionError()) { <p class="amber-text">{{ actionError() }}</p> }</section> }
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
  protected readonly trainingPlatform=signal('instagram');
  protected readonly trainingReason=signal('');
  protected readonly training=signal(false);
  protected value(event: Event): string {return (event.target as HTMLInputElement).value;}
  protected verified(model: ModelVersionRecord): boolean {return model.metrics?.['pipelineVersion']==='grouped-ridge-72h-v1';}
  protected canPromote(model: ModelVersionRecord): boolean {return this.verified(model) && (model.metrics?.['metrics'] as any)?.promotionEligible === true;}
  protected train(): void {
    if(!this.trainingReason().trim()) return;
    this.training.set(true);this.actionError.set('');
    this.service.trainModel(this.trainingPlatform(),this.trainingReason().trim()).subscribe({next:()=>{this.training.set(false);this.load();},error:response=>{this.training.set(false);this.actionError.set(response.error?.message || response.error?.detail || 'Training data ineligible; no model activated.');}});
  }
  protected rollback(model: ModelVersionRecord): void {
    this.promoting.set(model.id);
    this.service.rollbackModel(model.id,'Operator restored a verified prior model').subscribe({next:()=>{this.promoting.set('');this.load();},error:response=>{this.promoting.set('');this.actionError.set(response.error?.message || 'Rollback rejected');}});
  }
  constructor() { this.load(); }
  protected load(): void { this.loading.set(true); this.error.set(''); this.service.getModels().subscribe({ next: value => { this.models.set(value); this.loading.set(false); }, error: response => { this.error.set(response.error?.message || 'The model registry did not respond.'); this.loading.set(false); } }); }
  protected promote(model: ModelVersionRecord): void { if (!window.confirm(`Promote ${model.modelType} ${model.version} to champion?`)) return; this.promoting.set(model.id); this.actionError.set(''); this.service.promoteModel(model.id, 'Operator promotion from Model Versions').subscribe({ next: updated => { this.models.update(items => items.map(item => item.platform === updated.platform && item.modelType === updated.modelType ? (item.id === updated.id ? updated : { ...item, status: item.status === 'CHAMPION' ? 'RETIRED' : item.status }) : item)); this.promoting.set(''); }, error: response => { this.actionError.set(response.error?.message || 'Model promotion was rejected.'); this.promoting.set(''); } }); }
  protected date(value: string): string { return new Date(value).toLocaleString(); }
}
