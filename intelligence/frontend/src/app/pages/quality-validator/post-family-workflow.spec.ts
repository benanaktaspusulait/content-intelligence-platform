import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PostFamilyWorkflowComponent } from './post-family-workflow.component';

describe('post-family operator workflow', () => {
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
    TestBed.inject(HttpTestingController).expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([]);
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
    expect(f.nativeElement.textContent).toContain('referans');
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
});
