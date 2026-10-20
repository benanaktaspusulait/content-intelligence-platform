import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { RenderPreparationPage } from './render-preparation.page';
import { RenderDashboardPage } from './render-dashboard.page';
import { routes } from '../app.routes';

const originalUrl = window.location.href;
const context = {
  contentId: '8',
  promptVersionId: '8',
  promptVersionNumber: '1',
  workflowReviewId: 'review8',
  analysisId: 'review8',
};
const review = {
  recordId: 'review8',
  contentId: 8,
  promptVersionId: 8,
  boundRequest: {
    prompt: 'Mimi stands beside the cabinet.',
    generator: 'SEEDANCE_2_0_MINI',
    desiredDuration: 15,
    references: [],
  },
  generation: {
    apiModelId: 'byte-plus-seedance-2-mini',
    mode: 'image2video',
    supportedRenderDuration: 15,
    settings: { aspectRatio: '9:16' },
  },
  family8: { renderAuthorization: { status: 'BLOCKED', reason: 'Missing visual evidence' } },
};

describe('Render Preparation separation and immutable input safety', () => {
  afterEach(() => {
    TestBed.resetTestingModule();
    localStorage.clear();
    window.history.replaceState(window.history.state, '', originalUrl);
  });
  async function setup(params: any = context) {
    const query = new BehaviorSubject(convertToParamMap(params));
    await TestBed.configureTestingModule({
      imports: [RenderPreparationPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: query } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(RenderPreparationPage);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
      query,
    };
  }
  function restore(http: HttpTestingController) {
    http.expectOne('/api/v1/intelligence/workflow/records/review8').flush(review);
    http
      .expectOne((r) => r.url === '/api/v1/intelligence/workflow/visual-preparation')
      .flush({
        contentId: 8,
        promptVersionId: 8,
        firstFrameSpecification: 'Saved exact-source specification',
        firstFrameImagePrompt: 'Saved exact-source image prompt',
      });
    http
      .expectOne((r) => r.url === '/api/v1/visual-reference-plans/prompts/8/8')
      .flush({
        planId: null,
        contentId: 8,
        promptVersionId: 8,
        promptVersionNumber: 1,
        promptSha256: 'hash8',
        firstFrameCandidates: [],
        referenceBindings: [],
        capabilities: {},
        cost: {},
      });
    http.expectOne('/api/v1/characters').flush([{ id: 'mimi', name: 'Mimi' }]);
    http.expectOne('/api/v1/characters/mimi/references').flush([]);
    http
      .expectOne(
        (r) => r.url === '/api/v1/intelligence/workflow/production-review/reference-binding',
      )
      .flush({ status: 'MISSING' });
    http.expectOne('/api/v1/characters/mimi/workspace-references').flush([]);
    http
      .expectOne('/api/v1/intelligence/contents/8')
      .flush({ id: 8, title: "Mimi's Sticky Note Mystery" });
    http
      .expectOne((r) => r.url === '/api/v1/intelligence/workflow/production-settings')
      .flush({ generator: 'SEEDANCE_2_0_MINI', desiredDuration: 15, aspectRatio: '9:16' });
    http
      .expectOne('/api/v1/openart/references/configuration')
      .flush({ configured: false, mock: true });
    http
      .expectOne('/api/v1/openart/references/capabilities')
      .flush({ videoSingleStartFrame: 'SUPPORTED' });
  }
  it('restores the exact project using GET requests only, with version number distinct from database ID', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain("Mimi's Sticky Note Mystery");
    expect(fixture.nativeElement.textContent).toContain('Prompt v1 · ID 8');
    expect(component.queueContentId()).toBe('8');
    expect(component.analysisId).toBe('review8');
    expect(fixture.nativeElement.textContent).not.toContain('Queued');
    expect(fixture.nativeElement.textContent).not.toContain('Generating jobs');
    http.expectNone(
      (req) =>
        req.method !== 'GET' || req.url.includes('/render-jobs') || req.url.includes('/sse/'),
    );
    http.verify();
    fixture.destroy();
  });
  it('uses a recoverable context-free route without fetching another project', async () => {
    const { fixture, http } = await setup({});
    expect(fixture.nativeElement.textContent).toContain('Open a saved creative project');
    http.expectNone(() => true);
    fixture.destroy();
  });
  it('builds and saves specification only after explicit actions, without an image provider request', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.selectTab('first-frame');
    component.draftFirstFramePrompt();
    expect(component.firstFrameSpecification()).toContain('Mimi');
    expect(component.firstFrameImagePrompt()).toContain('cabinet');
    http.expectNone((req) => req.method === 'POST');
    component.saveVisualPreparation();
    const save = http.expectOne('/api/v1/intelligence/workflow/visual-preparation');
    expect(save.request.body.providerCallPerformed).toBe(false);
    expect(save.request.body.promptVersionId).toBe(8);
    save.flush({ savedAt: 'now' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.portrait')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Generate Start Frame');
    http.verify();
    fixture.destroy();
  });
  it('keeps absent character references unresolved and retains tab only within exact workflow identity', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.selectTab('characters');
    fixture.detectChanges();
    expect(component.characterReady).toBe(false);
    expect(fixture.nativeElement.textContent).toContain(
      'No reference assets found for this project.',
    );
    expect(localStorage.getItem('pompom-preparation-tab:8:8:review8')).toBe('characters');
    expect(localStorage.getItem('pompom-preparation-tab:9:8:review8')).toBeNull();
    http.verify();
    fixture.destroy();
  });
  it.each(['BLOCKED', 'BLOCKED_TECHNICAL_FAILURE', 'UNKNOWN', null, ''])(
    'fails closed for authorization %s even when capability is supported',
    (status) => {
      const http = { post: vi.fn() };
      const component = new RenderPreparationPage(http as any, {} as any, {} as any);
      component.workflowReviewId = 'review8';
      component.workflowReview = { ...review, family8: { renderAuthorization: { status } } };
      component.queueContentId.set('8');
      component.queuePromptVersionId.set('8');
      component.queueValidationId.set('12');
      component.queueRender();
      expect(component.canQueue()).toBe(false);
      expect(http.post).not.toHaveBeenCalled();
    },
  );
  it('requires fresh explicit render consent bound to the exact inputs and visible estimate', () => {
    const http={post:vi.fn()};const page=new RenderPreparationPage(http as any,{} as any,{} as any);
    page.workflowReviewId='review';page.workflowReview={bindingHash:'original'};
    vi.spyOn(page,'canQueue').mockReturnValue(true);vi.spyOn(page,'renderFrameIsCanonicallyVerified').mockReturnValue(true);
    page.queueContentId.set('8');page.queuePromptVersionId.set('8');page.queueValidationId.set('12');
    page.queueRender();expect(http.post).not.toHaveBeenCalled();expect(page.queueError()).toContain('explicitly authorize');
    page.renderEstimate.set({estimatedCredits:15});page.onRenderConsent(true);page.workflowReview.bindingHash='changed';
    page.queueRender();expect(http.post).not.toHaveBeenCalled();
  });
  it('rejects stale first-frame contract after a settings, character, mode or prompt change', () => {
    const component = new RenderPreparationPage({} as any, {} as any, {} as any);
    component.workflowReview = review;
    component.queueModel.set('byte-plus-seedance-2-mini');
    component.savedSettings = { aspectRatio: '9:16' };
    component.characterBinding = {
      referenceId: 'char8',
      sha256: 'charhash',
      approvalStatus: 'APPROVED',
    };
    const binding = {
      role: 'FIRST_FRAME',
      accepted: true,
      sha256: 'framehash',
      evidence: {
        promptHash: 'prompt8',
        aspectRatio: '9:16',
        model: 'byte-plus-seedance-2-mini',
        mode: 'image2video',
        characterReferenceAssetId: 'char8',
        checksum: 'framehash',
      },
    };
    component.visualReferencePlan.set({
      promptSha256: 'prompt8',
      referenceBindings: [binding],
    } as any);
    expect(component.frameReady).toBe(true);
    for (const [key, value] of [
      ['aspectRatio', '16:9'],
      ['characterReferenceAssetId', 'other'],
      ['mode', 'text2video'],
      ['promptHash', 'prompt7'],
      ['checksum', 'changed'],
    ]) {
      const stale = { ...binding, evidence: { ...binding.evidence, [key]: value } };
      expect(component.frameContextMatches(stale)).toBe(false);
    }
  });
  it('has dedicated monitoring and preparation routes with legacy compatibility', () => {
    expect(routes.some((route) => route.path === 'render-preparation')).toBe(true);
    expect(routes.some((route) => route.path === 'render-jobs')).toBe(true);
    expect(routes.find((route) => route.path === 'render')?.canActivate).toBeDefined();
  });
  it('retains real job monitoring without preparation forms', async () => {
    await TestBed.configureTestingModule({
      imports: [RenderDashboardPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    const fixture = TestBed.createComponent(RenderDashboardPage);
    const component = fixture.componentInstance;
    component.loading.set(false);
    component.jobs.set([
      {
        id: 'job1',
        contentTitle: 'Real persisted project',
        status: 'QUEUED',
        promptVersionNumber: 1,
        queuedAt: new Date().toISOString(),
      },
    ] as any);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Real persisted project');
    expect(fixture.nativeElement.querySelector('.stats-section')).not.toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Save Specification');
    fixture.destroy();
  });
  it('sends exact source/settings acceptance context and never auto-queues', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.visualReferencePlan.set({
      planId: 'plan8',
      contentId: 8,
      promptVersionId: 8,
      referenceBindings: [],
    } as any);
    component.characterBinding = {
      referenceId: 'char8',
      sha256: 'charhash',
      approvalStatus: 'APPROVED',
    };
    component.acceptPromptImportedFirstFrame('frame8');
    const accept = http.expectOne(
      '/api/v1/visual-reference-plans/plan8/first-frame/imported/frame8/accept',
    );
    expect(accept.request.body).toEqual({
      aspectRatio: '9:16',
      model: 'byte-plus-seedance-2-mini',
      characterReferenceAssetId: 'char8',
      mode: 'image2video',
    });
    accept.flush({}, { status: 409, statusText: 'Conflict' });
    expect(component.visualReferenceError()).toContain('could not be accepted');
    http.expectNone((req) => req.url === '/api/v1/render-jobs');
    http.verify();
    fixture.destroy();
  });
  it('does not upload invalid MIME or mismatched image dimensions', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.visualReferencePlan.set({ planId: 'plan8' } as any);
    await component.uploadPromptFirstFrame({
      target: { files: [new File(['invalid'], 'bad.svg', { type: 'image/svg+xml' })] },
    } as any);
    expect(component.visualReferenceError()).toContain('PNG, JPEG or WebP');
    http.expectNone((req) => req.method === 'POST');
    vi.spyOn(component as any, 'decodeImage').mockResolvedValue({ width: 1536, height: 1024 });
    await component.uploadPromptFirstFrame({
      target: { files: [new File(['image'], 'landscape.png', { type: 'image/png' })] },
    } as any);
    expect(component.visualReferenceError()).toContain('saved 9:16 aspect ratio');
    http.expectNone((req) => req.method === 'POST');
    http.verify();
    fixture.destroy();
  });
  it('uploads a valid local image through the prompt-bound asset service without acceptance or generation', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.visualReferencePlan.set({ planId: 'plan8' } as any);
    vi.spyOn(component as any, 'decodeImage').mockResolvedValue({ width: 1080, height: 1920 });
    await component.uploadPromptFirstFrame({
      target: { files: [new File(['image'], 'portrait.png', { type: 'image/png' })] },
    } as any);
    const upload = http.expectOne('/api/v1/visual-reference-plans/plan8/first-frame/upload');
    expect(upload.request.body instanceof FormData).toBe(true);
    upload.flush({});
    http
      .expectOne((req) => req.url === '/api/v1/visual-reference-plans/prompts/8/8')
      .flush({
        planId: 'plan8',
        contentId: 8,
        promptVersionId: 8,
        firstFrameCandidates: [],
        referenceBindings: [
          {
            assetId: 'upload8',
            role: 'FIRST_FRAME',
            accepted: false,
            validationStatus: 'METADATA_VERIFIED',
          },
        ],
      });
    expect(component.frameReady).toBe(false);
    http.expectNone((req) => req.url.includes('/accept') || req.url === '/api/v1/render-jobs');
    http.verify();
    fixture.destroy();
  });

  it('supports roving focus and all standard tab navigation keys', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    fixture.detectChanges();
    const tabButtons = () =>
      Array.from(fixture.nativeElement.querySelectorAll('[role="tab"]')) as HTMLButtonElement[];
    expect(tabButtons().map((button) => button.tabIndex)).toEqual([0, -1, -1, -1, -1]);
    fixture.nativeElement.querySelector('#tab-overview').focus();
    for (const [key, expected] of [
      ['ArrowRight', 'characters'],
      ['End', 'review'],
      ['ArrowRight', 'overview'],
      ['ArrowLeft', 'review'],
      ['Home', 'overview'],
    ]) {
      const focused = fixture.nativeElement.querySelector(
        `#tab-${component.tab()}`,
      ) as HTMLButtonElement;
      focused.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true }));
      fixture.detectChanges();
      expect(component.tab()).toBe(expected);
      expect(document.activeElement?.id).toBe(`tab-${expected}`);
      expect(tabButtons().filter((button) => button.tabIndex === 0)).toHaveLength(1);
    }
    http.verify();
    fixture.destroy();
  });
  it('displays readable authorization and missing-image reasons while preserving exact codes in disclosure', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.workflowReview.family8.renderAuthorization = {
      status: 'BLOCKED_TECHNICAL_FAILURE',
      reason: 'Unknown evidence for required input: startFrame',
      reasons: [{ code: 'MISSING_START_FRAME', message: 'Missing startFrame' }],
    };
    component.selectTab('review');
    fixture.detectChanges();
    const rows = Array.from(
      fixture.nativeElement.querySelectorAll('.review-summary dd'),
    ) as HTMLElement[];
    expect(
      rows.some((row) => row.textContent?.includes('Blocked: readiness validation failed')),
    ).toBe(true);
    expect(fixture.nativeElement.querySelector('.blockers').textContent).toContain(
      'Opening image is missing',
    );
    expect(fixture.nativeElement.querySelector('details').textContent).toContain(
      'BLOCKED_TECHNICAL_FAILURE',
    );
    expect(component.canQueue()).toBe(false);
    http.verify();
    fixture.destroy();
  });
  it('lets explicit local upload establish its own image plan after file validation', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.selectTab('first-frame');
    fixture.detectChanges();
    const fileInput = fixture.nativeElement.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput.disabled).toBe(false);
    vi.spyOn(component as any, 'decodeImage').mockResolvedValue({ width: 1080, height: 1920 });
    const action = component.uploadPromptFirstFrame({
      target: { files: [new File(['image'], 'portrait.png', { type: 'image/png' })] },
    } as any);
    await Promise.resolve();
    const inspect = http.expectOne('/api/v1/visual-reference-plans/prompts/8/8/inspect');
    expect(inspect.request.body.model).toBe('byte-plus-seedance-2-mini');
    inspect.flush({
      planId: 'new-plan8',
      contentId: 8,
      promptVersionId: 8,
      firstFrameCandidates: [],
      referenceBindings: [],
    });
    await action;
    const upload = http.expectOne('/api/v1/visual-reference-plans/new-plan8/first-frame/upload');
    upload.flush({});
    http
      .expectOne((req) => req.url === '/api/v1/visual-reference-plans/prompts/8/8')
      .flush({
        planId: 'new-plan8',
        contentId: 8,
        promptVersionId: 8,
        firstFrameCandidates: [],
        referenceBindings: [],
      });
    http.expectNone((req) => req.url.includes('/accept') || req.url === '/api/v1/render-jobs');
    http.verify();
    fixture.destroy();
  });
  it('retains a changed tab after contextual-link refresh without refetching while switching tabs', async () => {
    window.history.replaceState(
      window.history.state,
      '',
      `/render-preparation?${new URLSearchParams({ ...context, tab: 'characters' })}`,
    );
    const { fixture, component, http } = await setup({ ...context, tab: 'characters' });
    restore(http);
    component.selectTab('first-frame');
    const currentUrl = new URL(window.location.href);
    expect(currentUrl.searchParams.get('tab')).toBe('first-frame');
    expect(currentUrl.searchParams.get('workflowReviewId')).toBe('review8');
    http.expectNone(() => true);
    http.verify();
    fixture.destroy();
    TestBed.resetTestingModule();
    const reopened = await setup(Object.fromEntries(currentUrl.searchParams));
    restore(reopened.http);
    expect(reopened.component.tab()).toBe('first-frame');
    reopened.http.verify();
    reopened.fixture.destroy();
  });

  it('shows View Render Jobs link after a job is successfully queued', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    component.queuedJobId.set('job-abc-123');
    fixture.detectChanges();
    const link = fixture.nativeElement.querySelector('a[routerLink="/render-jobs"]');
    expect(link).not.toBeNull();
    expect(link?.textContent).toContain('View Render Jobs');
    http.verify();
    fixture.destroy();
  });

  it('overview checklist has separate status badge, description and action for each item', async () => {
    const { fixture, http } = await setup();
    restore(http);
    fixture.detectChanges();
    const articles = fixture.nativeElement.querySelectorAll('.checklist article');
    expect(articles.length).toBeGreaterThanOrEqual(5);
    for (const article of Array.from(articles) as HTMLElement[]) {
      const status = article.querySelector('.status');
      expect(status).not.toBeNull();
      const heading = article.querySelector('h3');
      expect(heading?.textContent?.trim().length).toBeGreaterThan(0);
      const action = article.querySelector('button, a');
      expect(action).not.toBeNull();
    }
    http.verify();
    fixture.destroy();
  });

  it('provider SUPPORTED status does not appear as render authorization in the overview', async () => {
    const { fixture, component, http } = await setup();
    restore(http);
    // The overview must show SUPPORTED (capability) and BLOCKED (authorization) as separate items
    fixture.detectChanges();
    const checklist = fixture.nativeElement.querySelector('.checklist');
    expect(checklist?.textContent).toContain('Blocked');
    // The word SUPPORTED appearing in capability article must not bleed into authorization article
    const articles = Array.from(checklist?.querySelectorAll('article') ?? []) as HTMLElement[];
    const authArticle = articles[articles.length - 1]; // Canonical authorization is last
    expect(authArticle?.textContent).not.toContain('SUPPORTED');
    expect(authArticle?.textContent?.toLowerCase()).toContain('blocked');
    http.verify();
    fixture.destroy();
  });

  it('render jobs page has actionable empty state when there are no jobs', async () => {
    await TestBed.configureTestingModule({
      imports: [RenderDashboardPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    const fixture = TestBed.createComponent(RenderDashboardPage);
    const component = fixture.componentInstance;
    component.loading.set(false);
    component.jobs.set([]);
    fixture.detectChanges();
    const empty = fixture.nativeElement.querySelector('.empty-state');
    expect(empty).not.toBeNull();
    expect(empty?.textContent).toContain('No render jobs yet');
    const link = fixture.nativeElement.querySelector('.empty-state a');
    expect(link).not.toBeNull();
    fixture.destroy();
  });

  it('step 7 page does not contain queued/generating/complete stat counters', async () => {
    const { fixture, http } = await setup();
    restore(http);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).not.toMatch(/Queued\s+\d/);
    expect(text).not.toContain('Generating jobs');
    expect(text).not.toContain('stats-section');
    expect(fixture.nativeElement.querySelector('.stats-section')).toBeNull();
    http.verify();
    fixture.destroy();
  });
});
