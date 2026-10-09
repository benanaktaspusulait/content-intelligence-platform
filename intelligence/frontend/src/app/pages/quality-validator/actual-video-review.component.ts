import { ChangeDetectorRef, Component, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-actual-video-review', standalone: true, imports: [CommonModule, FormsModule],
  template: `<section class="section-band"><h3>Actual clip review · original prompt unavailable</h3>
    <p>Describe only what you inspected in this clip. Original plan fidelity remains NOT_EVALUATED.</p>
    <p *ngIf="durationSeconds !== null">Measured clip duration: {{ durationSeconds }} seconds. Safety, coherence and progression need evidence covering the full clip.</p>
    <label>Reviewed start (seconds)<input type="number" [(ngModel)]="start"></label>
    <label>Reviewed end (seconds)<input type="number" [(ngModel)]="end"></label>
    <div *ngFor="let aspect of aspects"><label>{{ aspect.label }}<select [(ngModel)]="values[aspect.key]"><option value="UNKNOWN">Insufficient evidence</option><option *ngFor="let value of aspect.values" [value]="value">{{ value }}</option></select></label><input [(ngModel)]="descriptions[aspect.key]" [attr.aria-label]="aspect.label + ' observation'" placeholder="What was actually observed"></div>
    <label><input type="checkbox" [(ngModel)]="confirmed">I reviewed these intervals in the actual clip.</label>
    <button type="button" (click)="review()" [disabled]="busy || !confirmed || end === null || end <= start">Save actual review</button>
    <p *ngIf="error">{{ error }}</p><p *ngIf="result">Plan fidelity: {{ result.planFidelity }} · Viewer usability: {{ result.viewerFacingUsability }} · {{ result.editorialRecommendation }} · Record {{ result.recordId }}</p>
  </section>`,
})
export class ActualVideoReviewComponent implements OnChanges {
  private http = inject(HttpClient);
  private changeDetector = inject(ChangeDetectorRef);
  @Input() videoId = '';
  @Input() durationSeconds: number | null = null;
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
  private sequence = 0;
  ngOnChanges(changes: SimpleChanges): void {
    const measured = this.durationSeconds !== null && Number.isFinite(this.durationSeconds) && this.durationSeconds > 0 ? this.durationSeconds : null;
    if (changes['durationSeconds'] && !this.confirmed && this.end === null) this.end = measured;
    if (!changes['videoId']) return;
    const sequence = ++this.sequence;
    this.result = null; this.error = ''; this.busy = false; this.confirmed = false; this.start = 0; this.end = measured; this.values = {}; this.descriptions = {};
    if (!this.videoId) return;
    this.http.get<any[]>(`/api/v1/intelligence/workflow/videos/${this.videoId}/qa`).subscribe({ next: records => { if (sequence === this.sequence) {this.result = records[0] || null; this.changeDetector.markForCheck();} }, error: () => { if (sequence === this.sequence) {this.error = 'Saved actual review could not be loaded.';this.changeDetector.markForCheck();} } });
  }
  review(): void {
    if (this.busy || !this.videoId || !this.confirmed || this.end === null || this.end <= this.start) return;
    const experience = Object.fromEntries(this.aspects.map(aspect => [aspect.key, {
      value: this.values[aspect.key] || 'UNKNOWN', start: this.start, end: this.end,
      observed: this.descriptions[aspect.key] || '', confidence: 'HIGH', evidenceBasis: 'HUMAN_REVIEWED_CLIP', reference: this.videoId,
    }]));
    const sequence = this.sequence;
    this.busy = true; this.error = '';
    this.http.post<any>(`/api/v1/intelligence/workflow/videos/${this.videoId}/qa`, {
      humanReviewed: true, observation: { coverage: [this.start, this.end], experience },
    }).subscribe({ next: result => { if(sequence!==this.sequence) return; this.result = result; this.busy = false; this.changeDetector.markForCheck(); }, error: response => {if(sequence!==this.sequence) return; this.error = response.error?.detail || 'Actual review failed.'; this.busy = false; this.changeDetector.markForCheck(); } });
  }
}
