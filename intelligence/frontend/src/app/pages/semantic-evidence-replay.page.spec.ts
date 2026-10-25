import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ConceptRankingPage } from './concept-ranking.page';

describe('stored semantic evidence diagnostics', () => {
  const endpoint = '/api/v1/intelligence/workflow/concepts/semantic/replay';
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ConceptRankingPage], providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  });
  afterEach(() => { TestBed.inject(HttpTestingController).verify(); TestBed.resetTestingModule(); });
  it('makes no request on page load', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    TestBed.inject(HttpTestingController).expectNone(() => true);
    expect(fixture.nativeElement.textContent).toContain('No new concepts'); fixture.destroy();
  });
  it('requires an explicit action and sends only fixed offline replay configuration', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    fixture.componentInstance.replayEvidence(); const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.body).toEqual({ experimentId: 'semantic-live-v1-seed-42-count-40', semanticEvidenceAdapterVersion: 'v1', allowExternalGeneration: false });
    request.flush({ workflow: 'SEMANTIC_EVIDENCE_REPLAY', providerCalls: 0, baselineExact: true, payoffBreakdown: {}, candidates: [{ ideaId: 'stored', title: 'Existing story', projectedCanonicalEvidence: { payoffStatus: 'PAYOFF_PRESENT_UNCLASSIFIED' }, fieldLossAudit: [{ sourceField: 'finalPayoff', status: 'VALIDATOR_EXTRACTION_LOSS', validatorRecognition: 'NOT_RECOGNIZED' }] }] });
    fixture.detectChanges(); const text = fixture.nativeElement.textContent;
    for (const label of ['Raw','Normalized','Projected Evidence','Validator Recognition','VALIDATOR_EXTRACTION_LOSS']) expect(text).toContain(label);
    expect(fixture.nativeElement.querySelector('.evidence-loss')).not.toBeNull(); fixture.destroy();
  });
  it('does not send a second replay while busy', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.componentInstance.replayEvidence(); fixture.componentInstance.replayEvidence();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ workflow: 'SEMANTIC_EVIDENCE_REPLAY', candidates: [] }); fixture.destroy();
  });
  it('cancels replay on destruction', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.componentInstance.replayEvidence();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint); fixture.destroy(); expect(request.cancelled).toBe(true);
  });
  it('clears stale evidence on error', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.componentInstance.evidenceReplay = { stale: true }; fixture.componentInstance.replayEvidence();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush('unavailable', { status: 503, statusText: 'Unavailable' });
    expect(fixture.componentInstance.evidenceReplay).toBeNull(); expect(fixture.componentInstance.evidenceError).toContain('reanalysis failed'); fixture.destroy();
  });
});
