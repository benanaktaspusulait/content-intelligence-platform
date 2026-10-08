import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { GeneralProducibility, generalProducibilityRows } from './family10-representation';

@Component({
  selector: 'app-general-producibility',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section aria-label="General Producibility" class="producibility">
      <h3>General Producibility</h3>
      <ng-container *ngIf="assessment as value; else missing">
        <p>Canonical status: <code>{{ value.status }}</code></p>
        <p>Duration: {{ value.durationSeconds == null ? 'UNKNOWN' : value.durationSeconds + ' seconds' }} · Source: {{ value.durationSource }}</p>
        <p *ngFor="let reason of value.reasons">{{ reason }}</p>
        <div class="material-risks" *ngIf="value.materialRisks.length">
          <article *ngFor="let key of value.materialRisks">
            <strong>{{ key.replaceAll('_', ' ') }} · {{ value.dimensions[key].level }}</strong>
            <p>{{ value.dimensions[key].reason }}</p>
            <small>Evidence: {{ value.dimensions[key].evidenceReferences.join(', ') || 'UNKNOWN' }}</small>
          </article>
        </div>
        <aside *ngIf="value.unknownDimensions.length"><strong>Missing or unresolved source evidence</strong><p *ngFor="let key of value.unknownDimensions">{{ key }} · {{ value.dimensions[key]?.reason }} · {{ value.dimensions[key]?.evidenceReferences?.join(', ') || 'No grounded source reference' }}</p><p>Add an exact source quote and span in the source plan evidence form, then assess again. Unsupported effects remain UNKNOWN.</p></aside>
        <details>
          <summary>All production dimensions and evidence</summary>
          <article *ngFor="let risk of rows(value)">
            <strong>{{ risk.key.replaceAll('_', ' ') }} · {{ risk.level }}</strong>
            <p>{{ risk.reason }}</p>
            <small>Evidence: {{ risk.evidenceReferences.join(', ') || 'UNKNOWN' }}</small>
          </article>
          <p>Duration load: {{ value.durationLoad.level }} · {{ value.durationLoad.reason }}</p>
          <small>Evaluator: {{ value.provenance.evaluatorVersion }} · Source: {{ value.provenance.source || 'UNKNOWN' }}</small>
          <p *ngIf="value.provenance.sourceEvidence as source">
            Source evidence: {{ source.source || 'UNKNOWN' }} · Prompt hash: {{ source.promptHash || 'UNKNOWN' }} · Fixture: {{ source.fixtureVersion || 'UNKNOWN' }}
          </p>
        </details>
      </ng-container>
      <ng-template #missing><p>Canonical status: <code>UNKNOWN</code> · No General Producibility evidence in this report.</p></ng-template>
    </section>
  `,
  styles: [`.producibility { margin: 1rem 0; padding: 1rem; border: 1px solid #d8dee8; border-radius: .5rem; }
    h3 { margin: 0 0 .6rem; } article { padding: .7rem 0; border-top: 1px solid #e8edf4; }
    p { margin: .4rem 0; } small { overflow-wrap: anywhere; } summary { cursor: pointer; margin: .7rem 0; }`],
})
export class GeneralProducibilityComponent {
  @Input() assessment: GeneralProducibility | null | undefined = null;
  readonly rows = generalProducibilityRows;
}
