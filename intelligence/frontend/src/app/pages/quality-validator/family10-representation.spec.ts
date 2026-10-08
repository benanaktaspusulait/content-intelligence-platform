import frozenApiContract from '../../../../../data/golden/pompom-golden-v1/frozen-semantic/family10/api-contract.json';
import { TestBed } from '@angular/core/testing';
import { GeneralProducibility, GeneralProducibilityStatus, generalProducibilityRows } from './family10-representation';
import { GeneralProducibilityComponent } from './general-producibility.component';

function evidence(status: GeneralProducibilityStatus): GeneralProducibility {
  return {
    status, durationSeconds: null, durationSource: 'UNAVAILABLE', materialRisks: ['FINE_MOTOR_PRECISION'], unknownDimensions: ['TEXT_LIP_SYNC_SYMBOL'],
    reasons: ['Exact contact required'],
    dimensions: {
      TEXT_LIP_SYNC_SYMBOL: { level: 'UNKNOWN', reason: 'Text dependency missing', evidenceReferences: [], material: false, requiresRedesign: false },
      FINE_MOTOR_PRECISION: { level: 'HIGH', reason: 'Exact contact required', evidenceReferences: ['beat_02'], material: true, requiresRedesign: false },
      SEGMENT_CONTINUITY: { level: 'NOT_APPLICABLE', reason: 'Single generation', evidenceReferences: [], material: false, requiresRedesign: false },
    },
    durationLoad: { level: 'UNKNOWN', reason: 'Duration unavailable', evidenceReferences: [], material: false, requiresRedesign: false, dependentStateChanges: null, changesPerSecond: null },
    provenance: { evaluatorVersion: 'general-producibility-v1' },
  };
}

describe('Family 10 canonical representation', () => {
  for (const status of ['PRODUCIBLE', 'RISKY', 'NOT_PRODUCIBLE', 'UNKNOWN', 'NOT_APPLICABLE'] as const) {
    it(`preserves ${status}, null duration and risk references in the rendered component`, async () => {
      await TestBed.configureTestingModule({ imports: [GeneralProducibilityComponent] }).compileComponents();
      const fixture = TestBed.createComponent(GeneralProducibilityComponent);
      const input = evidence(status);
      const original = structuredClone(input);
      fixture.componentRef.setInput('assessment', input);
      fixture.detectChanges();
      const panel: HTMLElement = fixture.nativeElement;
      expect(panel.textContent).toContain(`Canonical status: ${status}`);
      expect(panel.textContent).toContain('Duration: UNKNOWN');
      expect(panel.textContent).toContain('FINE MOTOR PRECISION · HIGH');
      expect(panel.textContent).toContain('TEXT LIP SYNC SYMBOL · UNKNOWN');
      expect(panel.textContent).toContain('SEGMENT CONTINUITY · NOT_APPLICABLE');
      expect(panel.textContent).toContain('beat_02');
      expect(panel.textContent).toContain('general-producibility-v1');
      expect(input).toEqual(original);
      expect(panel.textContent).not.toContain('Creative grade');
      expect(panel.textContent).not.toContain('Render authorization');
    });
  }
  it('shows missing historical evidence as UNKNOWN', async () => {
    await TestBed.configureTestingModule({ imports: [GeneralProducibilityComponent] }).compileComponents();
    const fixture = TestBed.createComponent(GeneralProducibilityComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Canonical status: UNKNOWN');
    expect(fixture.nativeElement.textContent).not.toContain('FAIL');
  });
  it('places material risks first without dropping other dimensions or mutating evidence', () => {
    const input = evidence('RISKY');
    const original = structuredClone(input);
    expect(generalProducibilityRows(input).map(row => row.key)).toEqual(['FINE_MOTOR_PRECISION', 'TEXT_LIP_SYNC_SYMBOL', 'SEGMENT_CONTINUITY']);
    expect(input).toEqual(original);
    expect(generalProducibilityRows(null)).toEqual([]);
  });
});

const goldenContract = frozenApiContract as unknown as {
  assets: Record<string, { pre_render_assessment: { general_producibility: GeneralProducibility } }>;
};

describe('Family 10 frozen ML API contract in the actual UI', () => {
  for (const [goldenId, report] of Object.entries(goldenContract.assets)) {
    it(`renders all canonical dimensions and source provenance for ${goldenId}`, async () => {
      await TestBed.configureTestingModule({ imports: [GeneralProducibilityComponent] }).compileComponents();
      const fixture = TestBed.createComponent(GeneralProducibilityComponent);
      const input = report.pre_render_assessment.general_producibility;
      const original = structuredClone(input);
      fixture.componentRef.setInput('assessment', input);
      fixture.detectChanges();
      const text = fixture.nativeElement.textContent as string;
      expect(text).toContain(`Canonical status: ${input.status}`);
      for (const [key, risk] of Object.entries(input.dimensions)) {
        expect(text).toContain(`${key.replaceAll('_', ' ')} · ${risk.level}`);
        expect(text).toContain(risk.reason);
        for (const reference of risk.evidenceReferences) expect(text).toContain(reference);
      }
      expect(Object.keys(input.dimensions)).toHaveLength(15);
      const source = input.provenance.sourceEvidence;
      expect(text).toContain(source?.promptHash);
      expect(text).toContain('FAMILY10_REVIEWED_FROZEN_PROMPT');
      expect(input).toEqual(original);
    });
  }
});
