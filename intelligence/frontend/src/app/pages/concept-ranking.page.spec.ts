import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { routes } from '../app.routes';
import { ConceptRankingPage } from './concept-ranking.page';

describe('supplied concept ranking', () => {
  const endpoint = '/api/v1/intelligence/workflow/concepts/rank';
  const report = {
    workflow: 'CONCEPT_CANDIDATE_RANKING', firstRenderCandidate: 'supplied-a',
    productionSlate: [{ candidateId: 'supplied-a' }],
    rankedEligibleCandidates: [{ candidateId: 'supplied-a', title: 'Supplied concept', rank: 1, rankingScore: 97.6,
      shortFormScore: 100, shortFormEngine: { hookScore: 100, progressDensityScore: 100, payoffScore: 100 },
      eligibility: 'ELIGIBLE', duplicateRisk: 'MODERATE', productionRisk: { flags: [] }, productionEfficiency: { score: 100 },
      rankingDimensions: [{ dimension: 'progressDensity', score: 100, weightPercent: 18, source: 'SHORT_FORM_ENGINE.progressDensityScore' }],
      penalties: [], whyRankedHere: { text: 'Progress 100 vs 60; payoff 100 vs 15.' },
      historicalComparison: { closestHistoricalEngine: 'sticky-ball-01', limitation: 'Limited historical corpus.' },
      cpqPreview: { gradingStatus: 'CALIBRATION_INCOMPLETE' }, normalizedConcept: { id: 'supplied-a' } }],
    revisionCandidates: [{ candidateId: 'incomplete', title: 'Incomplete', eligibilityReasons: [{ code: 'MISSING_FIELD', reason: 'Missing finalPayoff.' }] }],
    diversityAdjustments: [{ code: 'DIVERSITY_PROMOTION', candidateId: 'different-engine' }],
    reportLines: ['Produce first: supplied-a'], limitations: ['No audience performance or render authorization.'],
  };
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ConceptRankingPage],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  });
  afterEach(() => { TestBed.inject(HttpTestingController).verify(); TestBed.resetTestingModule(); });

  it('starts empty and requests no generation or analysis', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    expect(fixture.componentInstance.batchText).toBe('');
    expect(fixture.nativeElement.querySelector('button').disabled).toBe(true);
    TestBed.inject(HttpTestingController).expectNone(endpoint); fixture.destroy();
  });

  it('has an additive route before prompt writing', () => {
    expect(routes.find(route => route.path === 'concept-ranking')?.loadComponent).toBeDefined();
  });

  it('submits only supplied concepts on explicit action', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage);
    fixture.componentInstance.sourceChanged('[{"id":"supplied-a","title":"Supplied"}]'); fixture.detectChanges();
    fixture.nativeElement.querySelector('button').click();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ candidates: [{ id: 'supplied-a', title: 'Supplied' }] });
    request.flush(report); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Produce first: supplied-a'); fixture.destroy();
  });

  it('displays ranking, exclusion, rationale, historical comparison and report without mutation', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage);
    const original = JSON.stringify(report);
    fixture.componentInstance.result = report; fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    for (const expected of ['Hook', 'Progress', 'Payoff', 'Duplicate Risk', 'Production Risk', '97.6', 'Progress 100 vs 60',
      'Missing finalPayoff.', 'sticky-ball-01', 'DIVERSITY_PROMOTION', 'CALIBRATION_INCOMPLETE']) expect(text).toContain(expected);
    expect(JSON.stringify(report)).toBe(original); fixture.destroy();
  });

  it('forwards labeled text batches for server normalization', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage);
    fixture.componentInstance.sourceChanged('Title: A\nGoal: sit\n---\nTitle: B\nGoal: wash hands'); fixture.detectChanges();
    fixture.componentInstance.rank();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.body).toEqual({ candidates: ['Title: A\nGoal: sit', 'Title: B\nGoal: wash hands'] });
    request.flush(report); fixture.destroy();
  });

  it('cancels stale requests and clears rankings after supplied text changes', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage);
    fixture.componentInstance.sourceChanged('Title: A'); fixture.detectChanges(); fixture.componentInstance.rank();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    fixture.componentInstance.sourceChanged('Title: B'); fixture.detectChanges();
    expect(request.cancelled).toBe(true); expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });

  it('does not send malformed JSON or generate substitutes', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage);
    fixture.componentInstance.sourceChanged('[malformed'); fixture.detectChanges(); fixture.componentInstance.rank();
    expect(fixture.componentInstance.error).not.toBe('');
    TestBed.inject(HttpTestingController).expectNone(endpoint); fixture.destroy();
  });

  it('shows failed validation without a first-render recommendation', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage);
    fixture.componentInstance.sourceChanged('Title: A'); fixture.detectChanges(); fixture.componentInstance.rank();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ detail: 'Duplicate candidate IDs: a' }, { status: 422, statusText: 'Invalid' });
    fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Duplicate candidate IDs: a');
    expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });
});
