import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ConceptRankingPage } from './concept-ranking.page';

describe('local concept generation controls', () => {
  const endpoint = '/api/v1/intelligence/workflow/concepts/generate';
  const run = {
    workflow: 'GENERATE_AND_RANK_SHORT_CONCEPTS', seed: 42, generatorVersion: 'short-concept-generator-v1',
    generationSummary: { rawCandidateCount: 20, eligibleCount: 3, structuralDuplicateCount: 2, catalogExhausted: true },
    engineDistribution: { progressive_growth: 2, repulsion: 1 }, diversityScore: 92,
    dominantEngineWarning: null, generatorMetrics: { eligibilityYield: .15 },
    candidates: [{ candidateId: 'rejected', candidate: { title: 'Preserved failure' }, disposition: 'REVISION_REQUIRED',
      failureReasons: [{ code: 'WEAK_VISUAL_PAYOFF', reason: 'Rule-linked payoff missing.' }], structuralFingerprint: { coreHash: 'core' } }],
    reportLines: ['What should we make today?', 'First production candidate: supplied-a'],
    rankingResult: { firstRenderCandidate: 'supplied-a', productionSlate: [{ candidateId: 'supplied-a' }],
      rankedEligibleCandidates: [], revisionCandidates: [], diversityAdjustments: [], reportLines: [], limitations: [] },
  };
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ConceptRankingPage],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  });
  afterEach(() => { TestBed.inject(HttpTestingController).verify(); TestBed.resetTestingModule(); });

  it('does not generate on page load', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    expect(fixture.componentInstance.candidateCount).toBe(20); expect(fixture.componentInstance.generationSeed).toBe(42);
    TestBed.inject(HttpTestingController).expectNone(endpoint); fixture.destroy();
  });

  it('generates only after explicit action and reuses the ranking result view', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    fixture.nativeElement.querySelector('[aria-label="Local concept generation"] button').click();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.body).toEqual({ count: 20, seed: 42, duration: 15, rank: true, generatorVersion: 'v2' });
    request.flush(run); fixture.detectChanges();
    expect(fixture.componentInstance.result).toEqual(run.rankingResult);
    const text = fixture.nativeElement.textContent;
    for (const expected of ['Generation stats', 'progressive_growth', 'Preserved failure', 'WEAK_VISUAL_PAYOFF', 'Produce first: supplied-a', 'finite recipe catalog']) expect(text).toContain(expected);
    fixture.destroy();
  });

  it('selects V1 explicitly and cancels stale V2 evidence on version changes', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    expect(fixture.componentInstance.generatorVersion).toBe('v2'); fixture.componentInstance.generate();
    const first = TestBed.inject(HttpTestingController).expectOne(endpoint);
    fixture.componentInstance.versionChanged('v1'); expect(first.cancelled).toBe(true);
    fixture.componentInstance.generate(); const second = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(second.request.body.generatorVersion).toBe('v1'); second.flush(run); fixture.detectChanges(); fixture.destroy();
  });

  it('shows V2 additive production ranks and per-candidate distances', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ ...run, generatorVersion: 'short-concept-generator-v2',
      generationEvidence: { finalCandidateCount: 20 }, objectCategoryDistribution: { furniture: 2 }, payoffDistribution: { ROLE_REVERSAL: 3 },
      firstRenderCandidate: 'production-v2', concentrationWarnings: [], humanReadableTop3: ['FRAME ZERO: visible problem'],
      top3ProductionCandidates: [{ title: 'Creative selection', rawRank: 2, productionSlateRank: 1 }],
      candidates: [{ ...run.candidates[0], creativeDistanceSummary: { minimum: .4, engineSimilarity: .5, visualSilhouetteSimilarity: .6 }, rawRank: 2, productionSlateRank: 1 }] });
    fixture.detectChanges(); const text = fixture.nativeElement.textContent;
    for (const value of ['Batch diversity summary','Object distribution','Payoff distribution','Top 3 production slate','Produce first: production-v2','Creative distance 0.4','Engine similarity 0.5','Visual silhouette similarity 0.6','Raw rank 2']) expect(text).toContain(value);
    fixture.destroy();
  });

  it('cancels stale generation after seed/count changes' , () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    fixture.componentInstance.generationChanged('seed', 43); fixture.detectChanges();
    expect(request.cancelled).toBe(true); expect(fixture.componentInstance.result).toBeNull();
    expect(fixture.componentInstance.generationResult).toBeNull(); fixture.destroy();
  });

  it('clears generation evidence when supplied concepts are edited', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush(run); fixture.detectChanges();
    fixture.componentInstance.sourceChanged('Title: supplied'); fixture.detectChanges();
    expect(fixture.componentInstance.generationResult).toBeNull(); expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });

  it('rejects invalid local configuration without sending any request', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    fixture.componentInstance.candidateCount = 101; fixture.componentInstance.generate();
    expect(fixture.componentInstance.error).toContain('10–100');
    TestBed.inject(HttpTestingController).expectNone(endpoint); fixture.destroy();
  });

  it('shows service failure without retaining a first-render recommendation', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush('unavailable', { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Local generation failed');
    expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });
  it('enables Beat Grammar explicitly and clears it when switching to V1', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    expect(fixture.componentInstance.beatGrammarVersion).toBe('');
    fixture.componentInstance.beatVersionChanged('v2'); fixture.componentInstance.generate();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.body.beatGrammarVersion).toBe('v2');
    fixture.componentInstance.versionChanged('v1'); expect(request.cancelled).toBe(true);
    expect(fixture.componentInstance.beatGrammarVersion).toBe(''); fixture.destroy();
  });

  it('shows non-canonical beat metrics and expandable strategy evidence', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ ...run,
      candidates: [{ ...run.candidates[0], beatGrammar: { strategyDiversityScore: 100, consequenceDiversityScore: 75, bodyStateProgressionScore: 80, payoffDistance: .75, beatGrammarQuality: 'STRONG', flags: [] },
        structuredBeatPlan: [{ beatNumber: 2, beatRole: 'TACTIC_CHANGE', characterStrategy: 'ANCHOR_TO_ENVIRONMENT', characterConsequence: 'Body is dragged backward', newInformation: ['NEW_BODY_CONSEQUENCE'] }] }] });
    fixture.detectChanges(); const text = fixture.nativeElement.textContent;
    for (const value of ['Strategy Diversity 100','Consequence Diversity 75','Body Progression 80','Payoff Distance 0.75','Beat Grammar Quality STRONG','Expand structured beats','ANCHOR_TO_ENVIRONMENT','Body is dragged backward','NEW_BODY_CONSEQUENCE']) expect(text).toContain(value);
    fixture.destroy();
  });

  it('enables premise gate explicitly and resets it with Beat Grammar', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    expect(fixture.componentInstance.premiseGateVersion).toBe('');
    fixture.componentInstance.beatVersionChanged('v2');
    fixture.componentInstance.premiseGateChanged('v1'); fixture.componentInstance.generate();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.body.premiseNaturalnessGateVersion).toBe('v1');
    fixture.componentInstance.beatVersionChanged(''); expect(request.cancelled).toBe(true);
    expect(fixture.componentInstance.premiseGateVersion).toBe(''); fixture.destroy();
  });

  it('shows optional non-canonical premise evidence', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ ...run,
      candidates: [{ ...run.candidates[0], premiseNaturalness: {
        premiseNaturalness: 'STRONG', goalInterferenceType: 'DIRECT', objectSpecificity: 'HIGH', objectSpecificityScore: 92,
        functionalIrony: 'HIGH', physicalPayoffPotential: 95, staticFrameLegibility: 85,
        primaryExpectedBehaviors: ['stays around foot'], whyThisObject: 'Retention fails.', flags: [] } }] });
    fixture.detectChanges(); const text = fixture.nativeElement.textContent;
    for (const value of ['Premise Naturalness STRONG', 'Goal Interference DIRECT', 'Object Specificity 92',
      'Functional Irony HIGH', 'Physical Payoff Potential 95', 'Static-Frame Legibility 85', 'Retention fails.']) expect(text).toContain(value);
    fixture.destroy();
  });

  it('explicitly enables shape curation and clears it when the premise gate is disabled', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    fixture.componentInstance.beatVersionChanged('v2'); fixture.componentInstance.premiseGateChanged('v1');
    fixture.componentInstance.shapeVersionChanged('v1'); fixture.componentInstance.generate();
    const request = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(request.request.body.creativeShapeVersion).toBe('v1');
    fixture.componentInstance.premiseGateChanged(''); expect(request.cancelled).toBe(true);
    expect(fixture.componentInstance.creativeShapeVersion).toBe(''); fixture.destroy();
  });

  it('shows optional story shape and historical territory evidence', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ ...run,
      candidates: [{ ...run.candidates[0], creativeShape: { shapeHash: 'story-hash', payoffFamily: 'CONTROL_REVERSAL', finalRelationship: 'OBJECT_CONTROLS_CHARACTER', dimensions: {} },
        templateShapeRisk: { risk: 'HIGH' }, historicalCreativeTerritory: { historicalCreativeTerritoryRisk: 'MEDIUM' }, closestBatchShape: { distance: .4 } }] });
    fixture.detectChanges(); const text = fixture.nativeElement.textContent;
    for (const value of ['Story Shape story-hash', 'Payoff Family CONTROL_REVERSAL', 'Final Relationship OBJECT_CONTROLS_CHARACTER', 'Template Shape Risk HIGH', 'Historical Creative Territory Risk MEDIUM', 'Shape Distance 0.4']) expect(text).toContain(value);
    fixture.destroy();
  });

  it('requires explicit semantic action and exposes a mock-only provider choice', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges();
    fixture.componentInstance.modeChanged('semantic'); fixture.detectChanges();
    TestBed.inject(HttpTestingController).expectNone(endpoint);
    expect(fixture.nativeElement.textContent).toContain('Live execution is disabled');
    fixture.componentInstance.generate(); const missing = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(missing.request.body.generatorMode).toBe('semantic');
    expect(missing.request.body.allowExternalGeneration).toBe(false);
    expect(missing.request.body.semanticProvider).toBeUndefined();
    fixture.componentInstance.mockChanged(true); expect(missing.cancelled).toBe(true);
    fixture.componentInstance.modeChanged('hybrid'); fixture.componentInstance.generate();
    const mock = TestBed.inject(HttpTestingController).expectOne(endpoint);
    expect(mock.request.body.generatorMode).toBe('hybrid');
    expect(mock.request.body.semanticProvider).toEqual({ provider: 'mock', model: 'fixture-v1' });
    mock.flush(run); fixture.detectChanges(); fixture.destroy();
  });

  it('shows semantic generation source without treating provider rationale as a score', () => {
    const fixture = TestBed.createComponent(ConceptRankingPage); fixture.detectChanges(); fixture.componentInstance.generate();
    TestBed.inject(HttpTestingController).expectOne(endpoint).flush({ ...run,
      candidates: [{ ...run.candidates[0], generationSource: 'SEMANTIC_V1' }] });
    fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Generation Source SEMANTIC_V1');
    fixture.destroy();
  });

});
