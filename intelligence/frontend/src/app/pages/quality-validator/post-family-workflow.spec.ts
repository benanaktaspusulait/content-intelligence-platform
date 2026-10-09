import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PostFamilyWorkflowComponent } from './post-family-workflow.component';

describe('post-family operator workflow', () => {
  afterEach(() => window.history.replaceState(window.history.state, '', window.location.pathname));
  async function setup() {
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
  it('requires explicit post-family selection and does not generate media', async () => {
    const fixture = await setup();
    expect(fixture.componentInstance.profile).toBe('FROZEN');
    expect(fixture.nativeElement.textContent).toContain('Family 1–10');
    TestBed.inject(HttpTestingController).expectNone('/api/v1/render-jobs');
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
      operatorReport: [{ label: 'KARAR', text: 'Kanıt adımına geç' }],
      reviewDimensions: {
        promptPlanQuality: { status: 'HYPOTHESIS' },
        generatorExecutionRisk: { status: 'ADVISORY_RISK' },
        actualRenderQuality: { status: 'UNKNOWN' },
        audienceDistributionOutcome: { status: 'NOT_JOINED' },
      },
    });
    await f.whenStable();
    expect(f.nativeElement.textContent).toContain('Kanıt adımına geç');
    expect(f.nativeElement.textContent).toContain('İzleyici / dağıtım sonucu');
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
