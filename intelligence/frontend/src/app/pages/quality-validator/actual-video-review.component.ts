import { Component, Input, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-actual-video-review', standalone: true, imports: [CommonModule, FormsModule],
  template: `<section class="section-band"><h3>Actual clip review · original prompt unavailable</h3>
    <p>Describe only what you inspected in this clip. Original plan fidelity remains NOT_EVALUATED.</p>
    <label>Reviewed start (seconds)<input type="number" [(ngModel)]="start"></label>
    <label>Reviewed end (seconds)<input type="number" [(ngModel)]="end"></label>
    <div *ngFor="let aspect of aspects"><label>{{ aspect.label }}<select [(ngModel)]="values[aspect.key]"><option value="UNKNOWN">Insufficient evidence</option><option *ngFor="let value of aspect.values" [value]="value">{{ value }}</option></select></label><input [(ngModel)]="descriptions[aspect.key]" [attr.aria-label]="aspect.label + ' observation'" placeholder="What was actually observed"></div>
    <label><input type="checkbox" [(ngModel)]="confirmed">I reviewed these intervals in the actual clip.</label>
    <button type="button" (click)="review()" [disabled]="busy || !confirmed || end === null || end <= start">Save actual review</button>
    <p *ngIf="error">{{ error }}</p><p *ngIf="result">Plan fidelity: {{ result.planFidelity }} · Viewer usability: {{ result.viewerFacingUsability }} · {{ result.editorialRecommendation }} · Record {{ result.recordId }}</p>
  </section>`,
})
export class ActualVideoReviewComponent {
  private http = inject(HttpClient);
  @Input() videoId = '';
  start = 0; end: number | null = null; confirmed = false; busy = false; error = ''; result: any = null;
  values: Record<string, string> = {}; descriptions: Record<string, string> = {};
  aspects = [
    { key: 'coreEventReadability', label: 'Core event readability', values: ['ADEQUATE', 'UNREADABLE'] },
    { key: 'identity', label: 'Identity', values: ['RECOGNIZABLE', 'UNRECOGNIZABLE'] },
    { key: 'safety', label: 'Safety', values: ['APPROPRIATE', 'UNSAFE'] },
    { key: 'coherence', label: 'Coherence', values: ['ADEQUATE', 'DESTROYED'] },
    { key: 'progression', label: 'Progression', values: ['DEVELOPING', 'PURPOSEFUL_REPETITION', 'WEAK'] },
    { key: 'opening', label: 'Opening', values: ['READABLE_EARLY_DEVELOPMENT', 'READABLE_PROMISE', 'UNREADABLE', 'EXCESSIVELY_DELAYED'] },
    { key: 'ending', label: 'Ending', values: ['DELIVERS_PROMISE', 'PURPOSEFUL_UNRESOLVED', 'ARBITRARY_TRUNCATION', 'WEAK'] },
  ];
  review(): void {
    if (!this.videoId || !this.confirmed || this.end === null || this.end <= this.start) return;
    const experience = Object.fromEntries(this.aspects.map(aspect => [aspect.key, {
      value: this.values[aspect.key] || 'UNKNOWN', start: this.start, end: this.end,
      observed: this.descriptions[aspect.key] || '', confidence: 'HIGH', evidenceBasis: 'HUMAN_REVIEWED_CLIP', reference: this.videoId,
    }]));
    this.busy = true; this.error = '';
    this.http.post<any>(`/api/v1/intelligence/workflow/videos/${this.videoId}/qa`, {
      humanReviewed: true, observation: { coverage: [this.start, this.end], experience },
    }).subscribe({ next: result => { this.result = result; this.busy = false; }, error: response => { this.error = response.error?.detail || 'Actual review failed.'; this.busy = false; } });
  }
}
