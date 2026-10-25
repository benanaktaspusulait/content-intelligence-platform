import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { StructuredSfeAuditComponent } from './structured-sfe-audit.component';

describe('structured SFE audit', () => {
  const url = '/api/v1/intelligence/workflow/concepts/semantic/short-form-replay';
  beforeEach(async () => { await TestBed.configureTestingModule({ imports: [StructuredSfeAuditComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents(); });
  afterEach(() => { TestBed.inject(HttpTestingController).verify(); TestBed.resetTestingModule(); });
  it('defaults to timed text and makes no request on load', () => {
    const f = TestBed.createComponent(StructuredSfeAuditComponent); f.detectChanges();
    expect(f.componentInstance.source).toBe('timed-text-v1'); TestBed.inject(HttpTestingController).expectNone(() => true); f.destroy();
  });
  it('explicitly requests structured dual analysis and displays independent results', () => {
    const f = TestBed.createComponent(StructuredSfeAuditComponent); f.componentInstance.source = 'structured-canonical-v1'; f.componentInstance.dual = true; f.componentInstance.run();
    const r = TestBed.inject(HttpTestingController).expectOne(url); expect(r.request.body.allowExternalGeneration).toBe(false); expect(r.request.body.shortFormEvidenceSourceVersion).toBe('structured-canonical-v1');
    r.flush({ workflow: 'STRUCTURED_SFE_OFFLINE_REPLAY', providerCalls: 0, scoresBlended: false, candidates: [{ ideaId: 'stored', title: 'Existing fixture', delta: 10, legacy: { shortFormScore: 20 }, structured: { shortFormScore: 30, status: 'REVISION_REQUIRED', findings: [] }, structuredRecognition: { payoffPresent: true }, dualAudit: { scoresCombined: false } }] }); f.detectChanges();
    expect(f.nativeElement.textContent).toContain('Score 30'); expect(f.nativeElement.textContent).toContain('Legacy 20'); expect(f.nativeElement.textContent).toContain('payoffPresent'); f.destroy();
  });
  it('cancels a stale source request', () => {
    const f = TestBed.createComponent(StructuredSfeAuditComponent); f.componentInstance.run(); const r = TestBed.inject(HttpTestingController).expectOne(url); f.componentInstance.clear(); expect(r.cancelled).toBe(true); expect(f.componentInstance.result).toBeNull(); f.destroy();
  });
  it('rejects duplicate clicks while running', () => {
    const f = TestBed.createComponent(StructuredSfeAuditComponent); f.componentInstance.run(); f.componentInstance.run(); TestBed.inject(HttpTestingController).expectOne(url).flush({ workflow: 'STRUCTURED_SFE_OFFLINE_REPLAY', candidates: [] }); f.destroy();
  });
});
