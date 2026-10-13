import savedAnalysis from '../../../../../backend/src/test/resources/step5-analysis-snapshot.json';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PostFamilyWorkflowComponent } from './post-family-workflow.component';

describe('post-family operator workflow', () => {
  afterEach(() => { window.history.replaceState(window.history.state, '', window.location.pathname); localStorage.clear(); });
  function flushReviewReads() {
    const http=TestBed.inject(HttpTestingController);
    http.match(r=>r.method==='GET' && r.url==='/api/v1/intelligence/workflow/production-review/decisions').forEach(r=>r.flush({decisions:[]}));
    http.match(r=>r.method==='GET' && r.url==='/api/v1/intelligence/workflow/provider-capabilities').forEach(r=>r.flush({models:{}}));
  }
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
    fixture.detectChanges(); flushReviewReads();
    const setupHttp = TestBed.inject(HttpTestingController);
    setupHttp.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([]);
    setupHttp.expectOne('/api/v1/characters').flush([{ name: 'Luca' }]);
    setupHttp.expectOne('/api/v1/intelligence/workflow/production-settings?contentId=1&promptVersionId=2').flush({});
    return fixture;
  }
  it('produces source-bound beats with codepoint offsets and no semantic approval', async () => {
    const f=await setup();const c=f.componentInstance;
    c.prompt='🎬 Duration: 5s\n0-2s: Nori holds a wooden coin.\n2-5s: Nori flips the coin.\nAUDIO\nMusic';
    const plan=c['options']().structuredPlan;
    expect(plan.schemaVersion).toBe('source-bound-beats-v1');expect(plan.events).toBeUndefined();expect(plan.beats).toHaveLength(2);
    for(const beat of plan.beats){expect(Array.from(c.prompt).slice(...beat.sourceSpan).join('')).toBe(beat.sourceQuote);expect(beat.sourceQuote).toContain(beat.action);expect(beat.semanticStatus).toBe('PENDING');}
    c.prompt=savedAnalysis.originalPrompt;
    const livePlan=c['options']().structuredPlan;expect(livePlan.beats).toHaveLength(5);
    for(const beat of livePlan.beats){expect(Array.from(c.prompt).slice(...beat.sourceSpan).join('')).toBe(beat.sourceQuote);expect(beat.sourceQuote).toContain(beat.action);expect(beat.semanticStatus).toBe('PENDING');}
    TestBed.inject(HttpTestingController).expectNone(r=>r.method==='POST');f.destroy();TestBed.resetTestingModule();
  });
  it('keeps read-only extraction distinct from the historical analysis', async () => {
    const f=await setup();const c=f.componentInstance;const http=TestBed.inject(HttpTestingController);
    c.review=structuredClone(savedAnalysis);const original=JSON.stringify(c.review);c.selectAnalysisTab('creative');
    http.expectOne(`/api/v1/intelligence/workflow/records/${c.review.recordId}/source-plan`).flush({kind:'READ_ONLY_SOURCE_EXTRACTION',historicalRunId:c.review.recordId,source:c.review.source,resultId:'separate-extraction',videoPlanIR:{mainCharacter:'Mimi',principalObject:'sticky note',entityEvidence:{mainCharacter:{state:'OBSERVED'},principalObject:{state:'OBSERVED'}},beats:[]}});
    expect(c.sourcePlanStatus).toBe('AVAILABLE');expect(JSON.stringify(c.review)).toBe(original);expect(c.review.family8.renderAuthorization.status).toBe('BLOCKED_TECHNICAL_FAILURE');
    http.expectNone(r=>r.method==='POST');http.verify();f.destroy();TestBed.resetTestingModule();
  });
  it('saves explicit intent, restores the reviewer decision and clears it on a version change', async () => {
    const f=await setup();const c=f.componentInstance;const http=TestBed.inject(HttpTestingController);
    c.confirmIntent();expect(c.intentConfirmed).toBe(false);
    const post=http.expectOne('/api/v1/intelligence/workflow/production-review/decisions');
    expect(post.request.body).toMatchObject({contentId:'1',promptVersionId:'2',decisionType:'CREATIVE_INTENT',sourceQuote:c.prompt});
    const decision={...post.request.body,provenance:'OPERATOR_CONFIRMED',recordId:'explicit-action'};
    post.flush(decision);expect(c.intentConfirmed).toBe(true);
    c.ngOnChanges({promptVersionId:{currentValue:'2'} as any});
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-review/decisions').flush({decisions:[decision]});
    http.expectOne('/api/v1/intelligence/workflow/provider-capabilities').flush({models:{}});
    http.expectOne('/api/v1/characters').flush([{name:'Luca'}]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/records?kind=REVIEW').flush([]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-settings').flush({});
    expect(c.intentConfirmed).toBe(true);
    f.componentRef.setInput('promptVersionId','3');f.detectChanges();
    expect(c.intentConfirmed).toBe(false);expect(c.reviewDecisions).toEqual([]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-review/decisions').flush({decisions:[]});
    http.expectOne('/api/v1/intelligence/workflow/provider-capabilities').flush({models:{}});
    http.expectOne('/api/v1/characters').flush([{name:'Luca'}]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/records?kind=REVIEW').flush([]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-settings').flush({});
    http.expectNone(r=>r.method==='POST');http.verify();f.destroy();TestBed.resetTestingModule();
  });
  it('represents the Mimi doubling and ending with exact current text and preserves UNKNOWN fidelity', async () => {
    const f=await setup();const c=f.componentInstance;
    c.prompt="Duration: 15s\n0-2s: Mimi reaches to the cabinet; the note clings to her finger -> note on finger\n2-5s: Mimi pulls; the note splits into two -> one note on each hand\n5-10s: Each pull doubles the notes, progressively covering Mimi -> Mimi is overwhelmed\n10-12s: Mimi sees herself in the mirror and screams -> Mimi is startled\n12-15s: Mimi sneezes; notes stick to the cabinet -> Mimi is relieved but the cabinet remains messy\nAUDIO\nPlayful music";
    expect(c.sourceEvents.map(e=>[e.start,e.end])).toEqual([[0,2],[2,5],[5,10],[10,12],[12,15]]);
    expect(c.intentMechanism).toContain('Each pull doubles');expect(c.intentEnding).toContain('cabinet remains messy');
    expect(c.sourceEvents[2].consequence).toBe('Mimi is overwhelmed');expect(c.sourceEvents[3].proposedRole).not.toBe('PAYOFF');
    expect(c.sourceEvents[4].consequence).toBe('Mimi is relieved but the cabinet remains messy');
    expect(c.sourceEvents.some(e=>e.consequence.includes('only her eyes'))).toBe(false);
    c.selectProductionTab('execution');f.detectChanges();
    c.setEventDraft('source-event-1','role','TRIGGER');f.detectChanges();
    expect(f.nativeElement.textContent).toContain('UNSAVED DRAFT');
    expect(f.nativeElement.textContent).toContain('Independent semantic fidelity is UNKNOWN');
    TestBed.inject(HttpTestingController).expectNone(r=>r.method==='POST');f.destroy();TestBed.resetTestingModule();
  });
  it('only confirms settings after save and never relabels an AUTO evaluation', async () => {
    const f=await setup();const c=f.componentInstance;const http=TestBed.inject(HttpTestingController);
    c.review={recordId:'old',boundRequest:{contentProfile:'AUTO',prompt:c.prompt}};
    c.contentProfile='ABSURD_PHYSICS';c.desiredDuration=15;c.aspectRatio='9:16';c.generator='SEEDANCE_2_0_MINI';
    expect(c.settingsStatus).not.toBe('CONFIRMED');c.applySettings();
    const save=http.expectOne('/api/v1/intelligence/workflow/production-settings');
    save.flush({savedAt:'2026-10-13T09:00:00Z'});expect(c.settingsStatus).toBe('CONFIRMED');
    expect(c.evaluationProfile).toBe('AUTO');expect(c.review.boundRequest.contentProfile).toBe('AUTO');
    c.desiredDuration=12;expect(c.settingsStatus).not.toBe('CONFIRMED');
    http.expectNone(r=>r.method==='POST');http.verify();f.destroy();TestBed.resetTestingModule();
  });

  it('loads saved Step 4 settings over historical analysis without inheriting approval or changing its score', async () => {
    const f=await setup();const c=f.componentInstance;const http=TestBed.inject(HttpTestingController);
    c.ngOnChanges({workflowProfile:{currentValue:'post-family-v1'} as any});flushReviewReads();
    http.expectOne('/api/v1/characters').flush([{name:'Luca'}]);
    const old={recordId:'historical',contentId:1,promptVersionId:2,decisionPolicyVersion:'impact-review-v1',score:85,
      boundRequest:{prompt:c.prompt,contentProfile:'AUTO',generator:'SEEDANCE_2_0_MINI',desiredDuration:15,settings:{aspectRatio:'9:16'},intentRequirements:[{level:'ESSENTIAL'}]}};
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/records?kind=REVIEW').flush([old]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/records?kind=ACTUAL_RENDER_QA').flush([]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-settings').flush({contentProfile:'ABSURD_PHYSICS',generator:'SEEDANCE_2_0_MINI',desiredDuration:15,aspectRatio:'9:16',savedAt:'now'});
    expect(c.contentProfile).toBe('ABSURD_PHYSICS');expect(c.settingsStatus).toBe('CONFIRMED');
    expect(c.intentConfirmed).toBe(false);expect(c.isCurrent()).toBe(false);
    expect(c.review.score).toBe(85);expect(c.review.boundRequest.contentProfile).toBe('AUTO');
    http.expectNone(r=>r.method==='POST');http.verify();f.destroy();TestBed.resetTestingModule();
  });
  it('reads the existing provider schema and legacy plan without evaluating or approving', async () => {
    const f=await setup();const c=f.componentInstance;const http=TestBed.inject(HttpTestingController);
    c.generator='SEEDANCE_2_0_MINI';c.desiredDuration=15;c.aspectRatio='9:16';
    c.providerCapabilities={models:{SEEDANCE_2_0_MINI:{version:'snapshot',provenance:{schemaSha256:'recorded'},modes:{image2video:{properties:{duration:{minimum:4,maximum:15},aspectRatio:{enum:['9:16']}}}}}}};
    expect(c.capabilityStatus).toContain('Supported by local schema snapshot');expect(c.capabilityStatus).toContain('does not verify creative producibility');
    c.desiredDuration=16;expect(c.capabilityStatus).toContain('UNKNOWN or unsupported');
    c.creativeProvenance={creativeRoleRecordId:'legacy',productionSpecificationStatus:'STALE'};c.loadLegacySpecification();
    http.expectOne('/api/v1/intelligence/workflow/records/legacy').flush({result:{productionPlan:{creativeObjective:'Historical humorous animation',storyPromptFidelity:{traceableSentenceCount:0,sourceSentenceCount:9}}}});
    expect(c.legacyProductionPlan.creativeObjective).toContain('Historical');expect(c.structuredPlanText).toBe('');expect(c.intentConfirmed).toBe(false);
    http.expectNone(r=>r.method==='POST');http.verify();f.destroy();TestBed.resetTestingModule();
  });

  it('renders the persisted live Step 5 contract without object coercion, false contradictions or lost reasons', async () => {
    const f=await setup();const c=f.componentInstance;
    c.review=structuredClone(savedAnalysis);c.activeStage=5;c['reviewedInputs']=c['inputSnapshot']();f.detectChanges();
    const text=f.nativeElement.textContent;
    expect(text).not.toContain('[object Object]');expect(text).toContain('STICKS TO SURFACES');expect(text).toContain('RETRIEVE OR CONTROL OBJECT');
    expect(text).toContain('Production complexity');expect(text).toContain('RISKY');expect(text).toContain('Local execution check');
    const items=c.resolutionItems();expect(items.some(i=>i.category==='SOURCE_EVIDENCE_CONTRADICTION')).toBe(false);
    expect(items.filter(i=>i.relatedReasons?.some((r:any)=>r.source==='REFERENCE_ASSOCIATION'))).toHaveLength(1);
    expect(items.filter(i=>i.category==='REFERENCE_REQUIRED')).toHaveLength(0);
    const reasons=items.flatMap(i=>i.relatedReasons||[]);expect(reasons).toHaveLength(3);
    expect(new Set(reasons.map((r:any)=>r.source)).size).toBe(3);
    const technical=items.find(i=>i.category==='TECHNICAL_ASSESSMENT_REQUIRED');expect(technical).toMatchObject({blocking:true,target:5,promptRevisionRequired:false});
    expect(technical.evidence).toContain('input-contract mismatch');expect(technical.evidence).toContain('UNKNOWN');
    c.resolveFinding(technical);f.detectChanges();expect(c.activeAnalysisTab).toBe('evidence');expect(c.review.family8.renderAuthorization.status).toBe('BLOCKED_TECHNICAL_FAILURE');
    expect(c.review.canonicalRuleEvaluation.score).toBe(85);TestBed.inject(HttpTestingController).expectNone(r=>r.method==='POST');f.destroy();TestBed.resetTestingModule();
  });
  it('keeps multiple reference authorization reasons in one actionable item', async () => {
    const f=await setup();const c=f.componentInstance;c.review=structuredClone(savedAnalysis);
    c.review.family8.renderAuthorization.reasons.push({code:'REFERENCE_IDENTITY_UNVERIFIED',source:'REFERENCE_ASSOCIATION',message:'Character reference requires verification',references:['ref-candidate']});
    const items=c.resolutionItems().filter(i=>i.relatedReasons?.some((r:any)=>r.source==='REFERENCE_ASSOCIATION'));
    expect(items).toHaveLength(1);expect(items[0].relatedReasons).toHaveLength(2);expect(items[0].blocking).toBe(true);
    f.destroy();TestBed.resetTestingModule();
  });

  it('shows stale provider evidence and approved source without importing old beats or approving review', async () => {
    const fixture=await setup();const component=fixture.componentInstance;
    fixture.componentRef.setInput('creativeProvenance',{creativeRoleRecordId:'builder',productionSpecificationStatus:'STALE',promptTextEdited:true,
      approvedStoryText:'Approved Mimi story',storyRevisionId:'candidate-2-revision-exact',sourceStoryRecordId:'story',candidateId:'candidate-2',approvalRecordId:'approval',
      productionPlan:{visualExecution:{beats:[{action:'Old provider event'}]}}});
    fixture.detectChanges(); flushReviewReads();
    expect(fixture.nativeElement.textContent).toContain('Production Specification is STALE');
    expect(fixture.nativeElement.textContent).toContain('Approved Mimi story');
    expect(component.structuredPlanText).toBe('');expect(component.review).toBeNull();expect(component.intentConfirmed).toBe(false);
    component.review={recordId:'old-quality'}; (component as any).reviewedInputs=(component as any).inputSnapshot();
    expect(component.isCurrent()).toBe(true);
    fixture.componentRef.setInput('promptVersionId','3');fixture.detectChanges(); flushReviewReads();
    const http=TestBed.inject(HttpTestingController);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/records?kind=REVIEW').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/production-settings?contentId=1&promptVersionId=3').flush({});http.expectOne('/api/v1/characters').flush([{name:'Luca'}]);
    expect(component.review).toBeNull();expect(component.qa).toBeNull();expect(component.isCurrent()).toBe(false);
    http.expectNone(r=>r.method==='POST');http.verify();fixture.destroy();TestBed.resetTestingModule();
  });

  it('restores the exact saved version using read requests and invalidates changed settings', async () => {
    await TestBed.configureTestingModule({ imports: [PostFamilyWorkflowComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
    const fixture = TestBed.createComponent(PostFamilyWorkflowComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('prompt', 'Luca opens a box.');
    fixture.componentRef.setInput('contentId', '7');
    fixture.componentRef.setInput('promptVersionId', '9');
    fixture.detectChanges(); flushReviewReads();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([
      { recordId: 'other', contentId: 7, promptVersionId: 8 },
      { recordId: 'saved', contentId: 7, promptVersionId: 9, bindingHash: 'binding', decisionPolicyVersion: 'impact-review-v1', boundRequest: { prompt: 'Luca opens a box.', generator: 'SEEDANCE_2_5', desiredDuration: 15, settings: { aspectRatio: '16:9' } } },
    ]);
    http.expectOne('/api/v1/characters').flush([{ name: 'Luca' }]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-settings').flush({});
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
  it('restores the approved character reference binding for the exact saved prompt version', async () => {
    await TestBed.configureTestingModule({ imports: [PostFamilyWorkflowComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
    const fixture = TestBed.createComponent(PostFamilyWorkflowComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('prompt', 'Mimi stands beside a cabinet.');
    fixture.componentRef.setInput('contentId', '7');
    fixture.componentRef.setInput('promptVersionId', '9');
    fixture.detectChanges(); flushReviewReads();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([
      { recordId: 'review-7-9', contentId: 7, promptVersionId: 9, bindingHash: 'review-hash', decisionPolicyVersion: 'impact-review-v1', boundRequest: { prompt: 'Mimi stands beside a cabinet.' } },
    ]);
    http.expectOne('/api/v1/characters').flush([{ id: 'mimi-id', name: 'Mimi' }]);
    const assetRequest = http.expectOne('/api/v1/characters/mimi-id/references');
    assetRequest.flush([{ id: 'ref-v3', status: 'APPROVED', sha256: 'stable-sha256', relativePath: 'character-references/mimi/ref-v3.png', version: 3 }]);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/production-review/reference-binding' && r.params.get('contentId') === '7' && r.params.get('promptVersionId') === '9')
      .flush({ contentId: '7', promptVersionId: '9', characterId: 'mimi-id', referenceId: 'ref-v3', sha256: 'stable-sha256', version: 3, approvalStatus: 'APPROVED' });
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-settings').flush({});
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=ACTUAL_RENDER_QA' && r.params.get('bindingHash') === 'review-hash').flush([]);
    expect(component.selectedReferenceId).toBe('ref-v3');
    expect(component.references[0]).toMatchObject({ id: 'ref-v3', sha256: 'stable-sha256', version: 3, status: 'APPROVED' });
    expect((component as any).inputSnapshot()).toContain('stable-sha256');
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
    fixture.detectChanges(); flushReviewReads();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne(r => r.url === '/api/v1/intelligence/workflow/records?kind=REVIEW').flush([
      { recordId: 'mimi-review', contentId: 1, promptVersionId: 2, bindingHash: 'mimi-hash', boundRequest: { prompt: 'Mimi opens a cabinet.' } },
      { recordId: 'kiko-review', contentId: 2, promptVersionId: 2, bindingHash: 'kiko-hash', boundRequest: { prompt: 'Kiko discovers a box.' } },
    ]);
    http.expectOne('/api/v1/characters').flush([{ name: 'Kiko' }]);
    http.expectOne(r=>r.url==='/api/v1/intelligence/workflow/production-settings').flush({});
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
    expect(component.activeStage).toBe(4);expect(fixture.nativeElement.textContent).not.toContain('{{');
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
  it('routes the analysis summary CTA to findings instead of forcing a prompt repair', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.review = { recordId: 'analysis-1', contentId: 1, promptVersionId: 2, bindingHash: 'hash', family8: { renderAuthorization: { status: 'BLOCKED_PENDING_EVIDENCE', reasons: [] } }, boundRequest: { prompt: c.prompt } };
    c['reviewedInputs'] = c['inputSnapshot']();
    c.activeStage = 5;
    expect(c.nextAnalysisAction).toBe('Resolve Outstanding Findings');
    c.continueFromAnalysis();
    expect(c.activeStage).toBe(4);
    expect(c.activeProductionTab).toBe('creative');
    TestBed.inject(HttpTestingController).expectNone(r => r.method === 'POST');
  });
  it('reuses the exact current saved review when continuing to Quality Analysis', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.profile = 'post-family-v1';
    c.review = { recordId: 'saved-review', contentId: 1, promptVersionId: 2, boundRequest: { prompt: c.prompt } };
    c['reviewedInputs'] = c['inputSnapshot']();
    c.continueToQualityAnalysis();
    expect(c.activeStage).toBe(5);
    TestBed.inject(HttpTestingController).expectNone(r => r.method === 'POST');
    f.destroy();
  });
  it('surfaces every canonical authorization reason as a stable actionable finding', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.review = { recordId: 'analysis-1', contentId: 1, promptVersionId: 2, bindingHash: 'hash', family8: { renderAuthorization: { status: 'BLOCKED_TECHNICAL_FAILURE', reasons: [{ code: 'CONTRADICTORY_SOURCE_EVIDENCE', source: 'TIMELINE_SOURCE', message: 'Two source spans conflict', references: ['prompt-v2:10-25', 'prompt-v2:90-110'] }] } }, boundRequest: { prompt: c.prompt } };
    c['reviewedInputs'] = c['inputSnapshot']();
    const item = c.resolutionItems().find(value => value.id === 'AUTHORIZATION:CONTRADICTORY_SOURCE_EVIDENCE:TIMELINE_SOURCE');
    expect(item).toMatchObject({ category: 'SOURCE_EVIDENCE_CONTRADICTION', blocking: true, target: 4, status: 'UNVERIFIED', revalidationRequired: true });
    expect(item.evidence).toContain('prompt-v2:10-25');
    c.resolveFinding(item);
    expect(c.activeStage).toBe(4);
    expect(c.activeProductionTab).toBe('execution');
    TestBed.inject(HttpTestingController).expectNone(r => r.method === 'POST');
  });
  it('keeps prompt version, database ID and analysis identity in Render Preparation navigation', async () => {
    const f = await setup();
    const c = f.componentInstance;
    f.componentRef.setInput('promptVersionNumber', 1);
    c.review = { recordId: 'analysis-8', contentId: 7, promptVersionId: 8, bindingHash: 'hash', boundRequest: { prompt: c.prompt } };
    const route = new URL(c.renderPreparationLink(), 'http://localhost');
    expect(route.searchParams.get('contentId')).toBe('7');
    expect(route.searchParams.get('promptVersionId')).toBe('8');
    expect(route.searchParams.get('promptVersionNumber')).toBe('1');
    expect(route.searchParams.get('analysisId')).toBe('analysis-8');
    expect(route.searchParams.get('workflowReviewId')).toBe('analysis-8');
    expect(c.authorizationLabel('BLOCKED_TECHNICAL_FAILURE')).toContain('Rendering blocked');
    expect(c.authorizationLabel(null)).toContain('unknown');
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
    expect(c.executionEvidenceStatus).toContain('independent semantic fidelity UNKNOWN');
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
  it('separates sticky notes from the cabinet, proposes only source-supported roles and keeps causal ambiguity actionable', async () => {
    const f = await setup();
    const c = f.componentInstance;
    c.prompt = 'Mimi Animation 15s 9:16\n0-3s: Mimi holds a sticky note in front of the toy cabinet.\n3-6s: The note sticks to Mimi instead of the cabinet.\n6-10s: The notes multiply and fly back onto Mimi.\n10-13s: The notes follow Mimi behind the cabinet.\n13-15s: Notes cover Mimi, leaving only her eyes.';
    const events = c.sourceEvents;
    expect(events.map(event => event.primaryObject)).toEqual(['Sticky notes','Sticky notes','Sticky notes','Sticky notes','Sticky notes']);
    expect(events[0].environment).toContain('Toy cabinet');
    expect(events[0].proposedRole).toBe('SETUP');
    expect(events[1].proposedRole).toBe('TRIGGER');
    expect(events[2].proposedRole).toBe('ESCALATION');
    expect(events[4].proposedRole).toBe('PAYOFF');
    expect(events.every(event => event.semanticStatus === 'PENDING')).toBe(true);
    expect(c.creativeConflicts[0].status).toContain('not a confirmed contradiction');
    expect(c.creativeConflicts[0].sourceEvidence).toContain('notes multiply');
    c.selectProductionTab('execution');
    const http=TestBed.inject(HttpTestingController);
    http.expectNone(r=>r.url==='/api/v1/intelligence/workflow/production-review/decisions');
    const original=c.prompt;
    c.setEventDraft(events[1].id,'role','TRIGGER');
    c.setEventDraft(events[1].id,'primaryObject','Sticky note');
    c.saveEventClassification(events[1]);
    const save=http.expectOne('/api/v1/intelligence/workflow/production-review/decisions');
    expect(save.request.body.sourceQuote).toBe(events[1].sourceQuote);
    expect(save.request.body.primaryObject).toBe('Sticky note');
    expect(save.request.body.provenance).toBeUndefined();
    expect(c.prompt).toBe(original);
    save.flush({decisionType:'EVENT_CLASSIFICATION',decisionId:events[1].id,decision:'TRIGGER',primaryObject:'Sticky note',provenance:'OPERATOR_CONFIRMED'});
    expect(c.prompt).toBe(original);
    http.verify();
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

  it('cleans report punctuation, avoids duplicate opening claims and preserves timed-range evidence', async () => {
    const f = await setup();
    const component = f.componentInstance;
    component.prompt = '0-6s: Mimi opens a box. 6-15s: Notes follow Mimi.';
    expect(component.cleanAnalysisText('Planned ending: : Mimi hides.')).toBe('Planned ending: Mimi hides.');
    expect(component.cleanAnalysisText(': Mimi opens a box.')).toBe('Mimi opens a box.');
    const rows = component.analysisReportRows([
      { label: 'VIEWING MECHANISM', text: ': Mimi opens a box.' },
      { label: 'OPENING', text: 'Mimi opens a box.' },
      { label: 'PROGRESSION', text: 'Insufficient evidence' },
    ]);
    expect(rows[1].text).toContain('Same source observation');
    expect(rows[2].text).toContain('2 timed source range(s) were extracted');
    f.destroy();
  });

});
