import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { CreativeIntelligenceService, ExperimentRecord, VideoRecord } from '../core/creative-intelligence.service';

@Component({
  selector: 'app-experiments-page',
  template: `
    <header class="page-header"><div><span class="eyebrow">RESEARCH PROGRAM</span><h1>Experiments</h1><p>Persisted experiment plans and their canonical video identity.</p></div></header>
    @if (loading()) { <div class="state-panel"><span class="spinner"></span><strong>Loading experiments</strong></div> }
    @else if (error()) { <div class="state-panel state-panel--error"><strong>Experiments unavailable</strong><p>{{ error() }}</p><button class="button" type="button" (click)="load()">Retry</button></div> }
    @else {
      <section class="section-band">
        <div class="section-heading"><div><span class="eyebrow">NEW PLAN</span><h2>Create experiment</h2></div><span class="status-badge">Backend operation</span></div>
        @if (!videos().length) { <p class="muted">A persisted video is required before an experiment can be created.</p> }
        @else {
          <div class="form-grid">
            <label>Video<select [value]="videoId()" (change)="videoId.set(selectValue($event))"><option value="">Select video…</option>@for (video of videos(); track video.id) { <option [value]="video.id">{{ video.title }}</option> }</select></label>
            <label>Platform<select [value]="platform()" (change)="platform.set(selectValue($event))"><option value="instagram">Instagram</option><option value="facebook">Facebook</option><option value="tiktok">TikTok</option><option value="youtube">YouTube</option></select></label>
            <label>Experiment type<select [value]="experimentType()" (change)="experimentType.set(selectValue($event))"><option value="EXPLOIT">Exploit</option><option value="ADJACENT">Adjacent</option><option value="EXPLORE">Explore</option><option value="CHARACTER_CONTROL_TEST">Character control test</option></select></label>
            <label>Planned publish time<input type="datetime-local" [value]="plannedPublishTime()" (input)="plannedPublishTime.set(inputValue($event))"></label>
          </div>
          <label>Hypothesis<input type="text" [value]="hypothesis()" (input)="hypothesis.set(inputValue($event))" placeholder="One measurable creative hypothesis"></label>
          <button class="button button--primary" type="button" [disabled]="creating() || !videoId() || !hypothesis().trim()" (click)="create()">{{ creating() ? 'Creating…' : 'Create experiment' }}</button>
          @if (createError()) { <p class="amber-text">{{ createError() }}</p> }
        }
      </section>
      <section class="section-band"><div class="section-heading"><div><span class="eyebrow">PERSISTED PLANS</span><h2>{{ experiments().length }} experiments</h2></div></div>
        @if (!experiments().length) { <div class="state-panel compact-state"><strong>No experiments recorded</strong><p>Create a plan only when a real persisted video is selected.</p></div> }
        @else { <div class="data-table-scroll"><table class="data-table"><thead><tr><th>Hypothesis</th><th>Video</th><th>Variant</th><th>Type</th><th>Platform</th><th>Status</th><th>Planned</th></tr></thead><tbody>@for (item of experiments(); track item.id) { <tr><td><strong>{{ item.hypothesis }}</strong><small>{{ item.id }}</small></td><td>{{ videoName(item.videoId) }}</td><td>{{ item.variantId || 'Not specified by API' }}</td><td>{{ readable(item.experimentType) }}</td><td>{{ item.platform }}</td><td><span class="status-badge">{{ item.status }}</span></td><td>{{ date(item.plannedPublishTime) }}</td></tr> }</tbody></table></div> }
      </section>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExperimentsPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly loading = signal(true);
  protected readonly creating = signal(false);
  protected readonly error = signal('');
  protected readonly createError = signal('');
  protected readonly experiments = signal<ExperimentRecord[]>([]);
  protected readonly videos = signal<VideoRecord[]>([]);
  protected readonly videoId = signal('');
  protected readonly platform = signal('instagram');
  protected readonly experimentType = signal('EXPLOIT');
  protected readonly hypothesis = signal('');
  protected readonly plannedPublishTime = signal('');
  protected readonly selectedVideo = computed(() => this.videos().find(video => video.id === this.videoId()) || null);

  constructor() { this.load(); }

  protected load(): void {
    this.loading.set(true); this.error.set('');
    forkJoin({ experiments: this.service.getExperiments(), videos: this.service.getVideos() }).subscribe({
      next: data => { this.experiments.set(data.experiments); this.videos.set(data.videos.records); this.loading.set(false); },
      error: response => { this.error.set(response?.error?.message || 'The experiment API did not respond.'); this.loading.set(false); },
    });
  }

  protected create(): void {
    const video = this.selectedVideo();
    if (!video || !this.hypothesis().trim()) return;
    this.creating.set(true); this.createError.set('');
    this.service.createExperiment({
      videoId: video.id,
      platform: this.platform(),
      hypothesis: this.hypothesis().trim(),
      experimentType: this.experimentType(),
      plannedPublishTime: this.plannedPublishTime() ? new Date(this.plannedPublishTime()).toISOString() : null,
    }).subscribe({
      next: item => { this.experiments.update(items => [item, ...items]); this.hypothesis.set(''); this.creating.set(false); },
      error: response => { this.createError.set(response.error?.message || 'Experiment creation failed.'); this.creating.set(false); },
    });
  }

  protected selectValue(event: Event): string { return (event.target as HTMLSelectElement).value; }
  protected inputValue(event: Event): string { return (event.target as HTMLInputElement).value; }
  protected videoName(id: string): string { return this.videos().find(video => video.id === id)?.title || id; }
  protected readable(value: string): string { return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()); }
  protected date(value: string | null): string { return value ? new Date(value).toLocaleString() : 'Not scheduled'; }
}
