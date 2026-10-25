import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

/** Read-only projection of saved server evidence; never recompute or approve. */
@Component({
  selector: 'app-story-premise-report',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section *ngIf="premise" aria-label="Long-form story premise assessment">
      <h3>Story premise · {{ premise.status }}</h3>
      <p>{{ premise.humanReadableReport }}</p>
      <p>Premise score {{ premise.score }}/100 · {{ premise.archetype }}.
        This is separate from canonical scoring. Textual support does not verify visual execution or audience response.</p>
      <ul><li *ngFor="let finding of premise.findings">{{ finding.severity }} · {{ finding.message }}</li></ul>
      <h4>Duration suitability</h4>
      <p *ngFor="let duration of premise.durationSuitability | keyvalue">
        {{ duration.key }} · {{ $any(duration.value).status }} — {{ $any(duration.value).reason }}
      </p>
      <details><summary>Story engine and source evidence</summary>
        <dl><ng-container *ngFor="let entry of premise.storyEngineSummary | keyvalue">
          <dt>{{ entry.key }}</dt><dd>{{ entry.value ?? 'Not established' }}</dd>
        </ng-container></dl>
        <article *ngFor="let check of premise.checks">
          <strong>{{ check.checkId }} · {{ check.outcome }}</strong><p>{{ check.reason }}</p>
          <blockquote *ngFor="let evidence of check.evidence">{{ evidence.quote }}</blockquote>
        </article>
        <p *ngFor="let limitation of premise.evidenceLimitations">{{ limitation }}</p>
      </details>
    </section>`,
})
export class StoryPremiseReportComponent {
  @Input() premise: any = null;
}
