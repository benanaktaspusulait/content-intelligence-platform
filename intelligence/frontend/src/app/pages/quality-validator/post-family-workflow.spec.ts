import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PostFamilyWorkflowComponent } from './post-family-workflow.component';

describe('post-family operator workflow', () => {
  afterEach(() => { window.history.replaceState(window.history.state, '', window.location.pathname); localStorage.clear(); });
  async function setup() {
    localStorage.clear();
    await TestBed.configureTestingModule({
      imports: [PostFamilyWorkflowComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    const fixture = TestBed.createComponent(PostFamilyWorkflowComponent);
    fixture.componentRef.setInput('prompt', '0-6 SEC\nLuca opens a box.');
    fixture.componentRef.setInput('contentId', '1');
    fixture.componentRef.setInput('promptVersionId', '2');
    fixture.detectChanges();
    const setupHttp = TestBed.inject(HttpTestingController);
    setupHttp.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([]);
    setupHttp.expectOne('/api/v1/characters').flush([{ name: 'Luca' }]);
    setupHttp.expectOne('/api/v1/intelligence/workflow/production-settings?contentId=1&promptVersionId=2').flush({});
    return fixture;
  }
  it('restores the exact saved version using read requests and invalidates changed settings', async () => {
    await TestBed.configureTestingModule({ imports: [PostFamilyWorkflowComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
    const fixture = TestBed.createComponent(PostFamilyWorkflowComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('prompt', 'Luca opens a box.');
    fixture.componentRef.setInput('contentId', '7');
    fixture.componentRef.setInput('promptVersionId', '9');
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([
      { recordId: 'other', contentId: 7, promptVersionId: 8 },
      { recordId: 'saved', contentId: 7, promptVersionId: 9, bindingHash: 'binding', decisionPolicyVersion: 'impact-review-v1', boundRequest: { prompt: 'Luca opens a box.', generator: 'SEEDANCE_2_5', desiredDuration: 15, settings: { aspectRatio: '16:9' } } },
    ]);
    http.expectOne('/api/v1/characters').flush([{ name: 'Luca' }]);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=ACTUAL_RENDER_QA').flush([{ recordId: 'qa', bindingHash: 'binding', videoId: 'exact-video' }]);
    expect(component.restoredRecordId).toBe('saved');
    expect(component.generator).toBe('SEEDANCE_2_5');
    expect(component.qa.videoId).toBe('exact-video');
    expect(component.isCurrent()).toBe(true);
    component.desiredDuration = 20;
    expect(component.isCurrent()).toBe(false);
    http.expectNone(request => request.method === 'POST');
    http.verify();
    fixture.destroy();
    TestBed.resetTestingModule();
  });
  it('isolates saved review restoration by content identity', async () => {
    await TestBed.configureTestingModule({ imports: [PostFamilyWorkflowComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
    const fixture = TestBed.createComponent(PostFamilyWorkflowComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('prompt', 'Kiko discovers a box.');
    fixture.componentRef.setInput('contentId', '2');
    fixture.componentRef.setInput('promptVersionId', '2');
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([
      { recordId: 'mimi-review', contentId: 1, promptVersionId: 2, bindingHash: 'mimi-hash', boundRequest: { prompt: 'Mimi opens a cabinet.' } },
      { recordId: 'kiko-review', contentId: 2, promptVersionId: 2, bindingHash: 'kiko-hash', boundRequest: { prompt: 'Kiko discovers a box.' } },
    ]);
    http.expectOne('/api/v1/characters').flush([{ name: 'Kiko' }]);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=ACTUAL_RENDER_QA').flush([]);
    expect(component.restoredRecordId).toBe('kiko-review');
    expect(component.review?.recordId).toBe('kiko-review');
    expect(component.review?.bindingHash).toBe('kiko-hash');
    http.verify();
    fixture.destroy();
    TestBed.resetTestingModule();
  });
  it('requires explicit post-family selection and does not generate media', async () => {
    const fixture = await setup();
    expect(fixture.componentInstance.profile).toBe('FROZEN');
    expect(fixture.nativeElement.textContent).toContain('WORKFLOW OVERVIEW');
    TestBed.inject(HttpTestingController).expectNone('/api/v1/render-jobs');
  });
  it('keeps downstream analysis, repair and video QA out of the production review stage', async () => {
    const fixture = await setup();
    const component = fixture.componentInstance;
    expect(component.activeStage).toBe(4);
    expect(fixture.nativeElement.textContent).toContain('Continue to Quality Analysis');
    expect(fixture.nativeElement.querySelector('.analysis-tabs')).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Actual render QA');
    expect(fixture.nativeElement.textContent).not.toContain('Bounded repair session');
    expect(fixture.nativeElement.textContent).not.toContain('Quality Analysis completed');
    expect(component.productionTabs.map(tab => tab.title)).toEqual(['Overview', 'Creative & Settings', 'Execution Plan', 'References']);
    fixture.destroy();
  });
  it('keeps one stage action bar across all Production Review tabs', async () => {
    const f = await setup();
    const c = f.componentInstance;
    for (const tab of c.productionTabs) c.selectProductionTab(tab.id);
    expect(c.productionTabs).toHaveLength(4);
    expect(f.nativeElement.querySelectorAll('.stage-action-bar')).toHaveLength(1);
    expect(f.nativeElement.querySelectorAll('.overview-next button')).toHaveLength(0);
    TestBed.inject(HttpTestingController).expectNone(r => r.method === 'POST');
  });
  it('keeps one PDF toolbar identity across all Analysis tabs without a provider request', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.review = { recordId: 'review-kiko', contentId: 1, promptVersionId: 2, bindingHash: 'hash', boundRequest: { prompt: c.prompt } };
    c['reviewedInputs'] = c['inputSnapshot']();
    c.activeStage = 5;
    f.detectChanges();
    for (const tab of c.analysisTabs) {
      c.selectAnalysisTab(tab.id);
      expect(c.analysisExportState).toBe('ANALYSIS_AVAILABLE');
    }
    expect(f.nativeElement.querySelectorAll('.analysis-stage-toolbar')).toHaveLength(1);
    TestBed.inject(HttpTestingController).expectNone(r => r.method === 'POST');
  });
  it('navigates from References to Quality Analysis and back to Prompt with the same workflow instance', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.selectProductionTab('references');
    expect(c.activeProductionTab).toBe('references');
    c.review = { recordId: 'review-kiko', contentId: 1, promptVersionId: 2, bindingHash: 'hash', boundRequest: { prompt: c.prompt } };
    c['reviewedInputs'] = c['inputSnapshot']();
    c.selectStage(5);
    expect(c.activeStage).toBe(5);
    c.selectStage(3);
    expect(c.activeStage).toBe(3);
    expect(c.activeProductionTab).toBe('references');
    TestBed.inject(HttpTestingController).expectNone(r => r.method === 'POST');
  });
  it('persists an explicitly accepted opening strategy through the settings contract', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = 'Kiko discovers a shiny box and finds colorful ribbons.';
    c.openingStrategy = 'AUTO';
    c.acceptOpeningSuggestion();
    const request = TestBed.inject(HttpTestingController).expectOne('/api/v1/intelligence/workflow/production-settings');
    expect(request.request.body.openingStrategy).toBe('CURIOSITY_DISCOVERY');
    request.flush({ savedAt: '2026-10-10T12:00:00Z' });
    expect(c.openingStrategy).toBe('CURIOSITY_DISCOVERY');
  });
  it('covers actual-newline, legacy, unicode-dash and invalid timeline fixtures', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = '0-3s: Kiko spots a box.\n3–6s: Kiko opens it.\n6.0-9.0 SEC: Kiko finds ribbons.';
    expect(c.timedRanges.map(r => [r.start, r.end])).toEqual([[0,3],[3,6],[6,9]]);
    c.prompt = 'A legacy prompt with no timeline; Kiko discovers a box.';
    expect(c.timedRanges).toHaveLength(0);
    c.prompt = '0-3s: first.\n3-2s: invalid backwards range.';
    expect(c.timedRanges.map(r => [r.start, r.end])).toEqual([[0,3]]);
  });
  it('keeps source-event candidates separate from semantic beat classification', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = '0-3s: Kiko spots a box.\n3-6s: Kiko opens it.';
    expect(c.sourceEvents.every(event => event.evidence === 'SOURCE_EVENT_CANDIDATE')).toBe(true);
    expect(c.sourceEvents.every(event => event.semanticStatus === 'PENDING')).toBe(true);
    expect(c.executionEvidenceStatus).toContain('classification pending');
  });
  it('shows a non-destructive profile mismatch advisory without overriding the operator', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = 'Kiko discovers a shiny box, finds colorful ribbons and forms a rainbow arch.';
    c.contentProfile = 'ABSURD_PHYSICS';
    expect(c.profileMismatch).toBe(true);
    expect(c.contentProfile).toBe('ABSURD_PHYSICS');
  });
  it('reviews the immutable version with all three generators available', async () => {
    const f = await setup();
    f.componentInstance.profile = 'post-family-v1';
    f.componentInstance.runReview();
    const request = TestBed.inject(HttpTestingController).expectOne(
      '/api/v1/intelligence/workflow/review',
    );
    expect(request.request.body.contentId).toBe(1);
    expect(request.request.body.promptVersionId).toBe(2);
    expect(request.request.body.options.profile).toBe('post-family-v1');
    request.flush({
      recordId: 'r',
      bindingHash: 'b',
      family8: { renderAuthorization: { status: 'BLOCKED_PENDING_EVIDENCE', reasons: [] } },
      generalProducibility: { status: 'UNKNOWN' },
      generation: { selectedGenerator: 'SEEDANCE_2_0_MINI' },
      routing: { contentProfile: 'UNKNOWN' },
      opening: { strategy: 'CURIOSITY_DISCOVERY' },
      executionReview: { status: 'UNKNOWN', findings: [] },
      finalPrompt: 'Prompt',
    });
    await f.whenStable();
    expect(f.nativeElement.textContent).toContain('BLOCKED_PENDING_EVIDENCE');
    expect(f.nativeElement.textContent).toContain('Summary');
    expect(f.nativeElement.textContent).not.toContain('Raw plan, generator and authorization evidence');
    expect(f.componentInstance.isCurrent()).toBe(true);
    f.componentInstance.generator = 'SEEDANCE_2_0';
    expect(f.componentInstance.isCurrent()).toBe(false);
  });
  it('keeps platform IDs as text and exposes pending reference evidence', async () => {
    const f = await setup();
    f.componentInstance.platformContentId = '99999999999999999999';
    expect(f.componentInstance.platformContentId).toBe('99999999999999999999');
    expect(f.nativeElement.textContent).toContain('reference');
  });
  it('extracts source timing without treating every range as a major beat', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = 'Mimi / ANIMATION (15s, 16:9)\n0–3s: Mimi enters.\n3-6s: The note flips.\n6.0-10.0s: Notes multiply.\n10-13s: Mimi hides.\n00:13-00:15: Hard cut.';
    expect(c.timedRanges.map(range => [range.start, range.end])).toEqual([[0, 3], [3, 6], [6, 10], [10, 13], [13, 15]]);
    expect(c.timedRanges.every(range => range.quote.length > 0)).toBe(true);
    expect(c.extractedIntent).toContain('Mimi enters');
    expect(c.sourceEvents).toHaveLength(5);
    expect(c.sourceEvents[0].evidence).toBe('SOURCE_EVENT_CANDIDATE');
    expect(c.sourceEvents[4].semanticStatus).toBe('PENDING');
    expect(c.sourceEvents[0].action).not.toMatch(/^s:/);
    c.toggleSourceQuote(c.sourceEvents[1].id);
    expect(c.isSourceQuoteOpen(c.sourceEvents[1].id)).toBe(true);
    expect(c.sourceEvents[1].sourceQuote).toContain('The note flips');
  });
  it('splits literal escaped-newline timelines into bounded source events', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = 'TITLE / FORMAT\nKiko Discovery\nTIMED SHOT PLAN\n0.0-3.0 SEC: Kiko spots a shiny box\\n3.0-6.0 SEC: Kiko opens the box with excitement\\n6.0-9.0 SEC: Kiko discovers colorful ribbons inside\\n9.0-12.0 SEC: Kiko pulls ribbons into patterns\\n12.0-15.0 SEC: The ribbons form a rainbow arch';
    expect(c.timedRanges.map(range => [range.start, range.end])).toEqual([[0, 3], [3, 6], [6, 9], [9, 12], [12, 15]]);
    expect(c.timedRanges[0].quote).toContain('spots a shiny box');
    expect(c.timedRanges[0].quote).not.toContain('opens the box');
    expect(c.timedRanges[4].quote).toContain('rainbow arch');
    expect(c.sourceEvents[0].semanticStatus).toBe('PENDING');
    expect(c.sourceEvents[0].object).toBe('shiny box');
    expect(c.sourceEvents[2].object).toBe('ribbons');
  });
  it('stops the final timed shot at the next document section and preserves multiline spans', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = `TITLE / FORMAT
Mimi / Animated Short

TIMED SHOT PLAN
0-3s: Mimi holds the note.
3-6s: The note flips in the air.
6-10s: Mimi peels it off.
10-13s: Notes multiply and return.
13-15s: Mimi is covered completely;
only her wide eyes remain.

AUDIO
Playful music and paper sounds.

NEGATIVE CONSTRAINTS
No dark themes.

FINAL CUT
Hard cut.`;
    const finalRange = c.timedRanges.at(-1)!;
    expect(c.timedRanges.map(range => [range.start, range.end])).toEqual([[0, 3], [3, 6], [6, 10], [10, 13], [13, 15]]);
    expect(finalRange.quote).toContain('only her wide eyes remain');
    expect(finalRange.quote).not.toContain('AUDIO');
    expect(finalRange.quote).not.toContain('NEGATIVE CONSTRAINTS');
    expect(finalRange.quote).not.toContain('FINAL CUT');
    expect(finalRange.quoteStart).toBeGreaterThanOrEqual(0);
    expect(finalRange.quoteEnd).toBeGreaterThan(finalRange.quoteStart);
  });
  it('keeps missing source identity incomplete and restores saved settings without a 9:16 fallback', async () => {
    const f = await setup();
    const c = f.componentInstance;
    expect(c.analysisReady).toBe(true);
    c.aspectRatio = '';
    c.prompt = '15 seconds, 16:9';
    c['hydrateSettingsFromPrompt']();
    expect(c.aspectRatio).toBe('16:9');
    expect(c.desiredDuration).toBe(15);
    expect(c.aspectRatio).not.toBe('9:16');
  });
  it('binds a local patch to Unicode code points and the exact source quote', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = '🎈0-6 SEC\nLuca pushes the box. CUT.';
    c.review = { recordId: 'r' };
    c.patchOriginal = 'CUT.';
    c.patchReplacement = 'Hold.';
    c.repair();
    const request = TestBed.inject(HttpTestingController).expectOne(
      '/api/v1/intelligence/workflow/records/r/repair',
    );
    const patch = request.request.body.patches[0];
    expect(patch.sourceQuote).toBe('CUT.');
    expect(Array.from(c.prompt).slice(patch.start, patch.end).join('')).toBe('CUT.');
    request.flush({ finalPrompt: 'Verified final prompt', repairPasses: 1 });
  });
  it('keeps intent source-bound, review dimensions separate and outcomes outside evaluator input', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.profile = 'post-family-v1';
    c.intentRequirementsText =
      '[{"id":"reveal","level":"ESSENTIAL","sourceQuote":"Luca opens a box.","sourceSpan":[8,25],"eventIds":["source_0"]}]';
    c.creativeEvidenceText = '[]';
    c.views = 100000;
    c.runReview();
    const req = TestBed.inject(HttpTestingController).expectOne(
      '/api/v1/intelligence/workflow/review',
    );
    expect(req.request.body.options.intentRequirements[0].level).toBe('ESSENTIAL');
    expect(req.request.body.options.views).toBeUndefined();
    req.flush({
      recordId: 'r',
      operatorReport: [{ label: 'DECISION', text: 'Proceed to evidence' }],
      reviewDimensions: {
        promptPlanQuality: { status: 'HYPOTHESIS' },
        generatorExecutionRisk: { status: 'ADVISORY_RISK' },
        actualRenderQuality: { status: 'UNKNOWN' },
        audienceDistributionOutcome: { status: 'NOT_JOINED' },
      },
    });
    await f.whenStable();
    expect(f.nativeElement.textContent).toContain('Proceed to evidence');
    expect(f.nativeElement.textContent).toContain('Audience / distribution outcome');
    c.intentRequirementsText = '[]';
    expect(c.isCurrent()).toBe(false);
  });
  it('restores an exact bounded repair session without making a provider request', async () => {
    const fixture=await setup();const component=fixture.componentInstance;const http=TestBed.inject(HttpTestingController);
    component.reopenRepairSession('saved-session');
    http.expectOne('/api/v1/intelligence/workflow/repair-sessions/saved-session').flush({sessionId:'saved-session',contentId:1,originalPromptVersionId:2,bestPromptVersionId:3,bestReviewId:'verified-best',state:'STOPPED',attempts:2,maxAttempts:2,reservedCostUsd:.02,history:[{promptVersionId:3,reviewId:'verified-best',diff:'exact patch'}]});
    expect(component.repairSession.bestReviewId).toBe('verified-best');http.expectNone(r=>r.method==='POST');http.verify();fixture.destroy();TestBed.resetTestingModule();
  });
  async function startAutomaticRepair() {
    const fixture = await setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    component.review = { recordId: 'review' };
    component.isCurrent = () => true;
    component.repairConsent = true; component.repairBudget = 0.1;
    component.startRepairSession();
    http.expectOne('/api/v1/intelligence/workflow/repair-sessions').flush({ sessionId: 'bounded', state: 'READY', attempts: 0, maxAttempts: 2 });
    return { fixture, component, http };
  }
  it('automatically advances only independently reviewed improvements within two attempts', async () => {
    const { fixture, component, http } = await startAutomaticRepair();
    const path = '/api/v1/intelligence/workflow/repair-sessions/bounded/step';
    http.expectOne(path).flush({ sessionId: 'bounded', state: 'READY', attempts: 1, maxAttempts: 2, stopReason: 'NEXT_ATTEMPT_AVAILABLE', history: [{ stage: 'INDEPENDENTLY_REVIEWED' }] });
    http.expectOne(path).flush({ sessionId: 'bounded', state: 'STOPPED', attempts: 2, maxAttempts: 2, stopReason: 'ATTEMPT_LIMIT' });
    expect(component.repairSession.attempts).toBe(2);
    http.expectNone(r => r.method === 'POST'); http.verify(); fixture.destroy();
  });
  it('does not advance or overwrite cancellation when a previous attempt responds late', async () => {
    const { fixture, component, http } = await startAutomaticRepair();
    const attempt = http.expectOne('/api/v1/intelligence/workflow/repair-sessions/bounded/step');
    component.decideRepair('CANCELLED');
    http.expectOne('/api/v1/intelligence/workflow/repair-sessions/bounded/decision').flush({ sessionId: 'bounded', state: 'CANCELLED' });
    attempt.flush({ sessionId: 'bounded', state: 'READY', attempts: 1, maxAttempts: 2, stopReason: 'NEXT_ATTEMPT_AVAILABLE', history: [{ stage: 'INDEPENDENTLY_REVIEWED' }] });
    expect(component.repairSession.state).toBe('CANCELLED');
    http.expectNone(r => r.method === 'POST'); http.verify(); fixture.destroy();
  });
  it('never resumes automatic provider work from GET or after the screen is destroyed', async () => {
    const { fixture, component, http } = await startAutomaticRepair();
    const attempt = http.expectOne('/api/v1/intelligence/workflow/repair-sessions/bounded/step');
    fixture.destroy();
    attempt.flush({ sessionId: 'bounded', state: 'READY', attempts: 1, maxAttempts: 2, stopReason: 'NEXT_ATTEMPT_AVAILABLE', history: [{ stage: 'INDEPENDENTLY_REVIEWED' }] });
    http.expectNone(r => r.method === 'POST'); http.verify();
    TestBed.resetTestingModule();
    window.history.replaceState(window.history.state, '', window.location.pathname);
    const reopened = await setup(); const rehttp = TestBed.inject(HttpTestingController);
    reopened.componentInstance.reopenRepairSession('bounded');
    rehttp.expectOne('/api/v1/intelligence/workflow/repair-sessions/bounded').flush({ sessionId: 'bounded', contentId: 1, originalPromptVersionId: 2, state: 'READY', attempts: 1, maxAttempts: 2 });
    rehttp.expectNone(r => r.method === 'POST'); rehttp.verify(); reopened.destroy();
  });
  it('stale inputs cannot request canonical profile admission', async () => {
    const fixture=await setup();const component=fixture.componentInstance;const http=TestBed.inject(HttpTestingController);
    component.review={recordId:'old-review'};component.desiredDuration=20;component.validateCanonicalProfile();
    http.expectNone(r=>r.method==='POST');http.verify();fixture.destroy();TestBed.resetTestingModule();
  });

  it('reports overlapping source quote coverage using Unicode spans without claiming completeness', async () => {
    const f = await setup();
    f.componentInstance.prompt = '🎈abcd';
    expect(f.componentInstance.evidenceCoverage({claims: [{span:[0,3]}, {span:[2,4]}, {span:[-1,2]}, {span:[0,99]}]})).toBe('4/5 Unicode characters (80%)');
    expect(f.componentInstance.evidenceCoverage({claims:[]})).toBe('0/5 Unicode characters (0%)');
  });

});
