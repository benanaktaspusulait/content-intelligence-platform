import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { vi } from 'vitest';
import { Router, provideRouter } from '@angular/router';
import { CreativeStudioPage } from './creative-studio.page';

describe('Idea entry ownership and free persistence', () => {
  let http: HttpTestingController;
  beforeEach(async () => { localStorage.clear(); await TestBed.configureTestingModule({ imports:[CreativeStudioPage], providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])] }).compileComponents(); http=TestBed.inject(HttpTestingController); });
  afterEach(()=>{ http.verify(); localStorage.clear(); TestBed.resetTestingModule(); });
  function open(){const fixture=TestBed.createComponent(CreativeStudioPage);fixture.detectChanges();http.match(r=>r.method==='GET').forEach(r=>r.flush(r.request.url.endsWith('readiness')?{enabled:true,roles:[{role:'STORY',configured:true}]}:[]));fixture.detectChanges();return {fixture,page:fixture.componentInstance as any};}
  it('shows a purposeful empty state, neutral examples and no budget warning',()=>{const {fixture}=open();expect(fixture.nativeElement.textContent).toContain('No saved projects yet');expect(fixture.nativeElement.textContent).not.toContain('No saved projects match');expect(fixture.nativeElement.textContent).not.toContain('Enter an authorised budget');expect(fixture.nativeElement.innerHTML).not.toContain('Mimi');});
  it('keeps character guidance contextual without claiming approval from a name alone',()=>{const {page}=open();page.characters=[{id:'opa',name:'Opa',raw:{}}];expect(page.characterGuidance).toContain('Selection may be deferred');page.mainCharacterId='opa';expect(page.characterGuidance).toContain('No authoritative visual reference is confirmed');page.characters[0].raw={referenceStatus:'AVAILABLE'};expect(page.characterGuidance).toContain('available');});
  it('keeps independent sources without provider calls or server writes on edits',()=>{const {page}=open();page.sourceText='Short idea';page.inputMode='DETAILED_STORY';page.onModeChange();expect(page.sourceText).toBe('');page.sourceText='Complete operator story';page.inputMode='EXISTING_PROMPT';page.onModeChange();page.sourceText='Production camera prompt';page.inputMode='IDEA';page.onModeChange();expect(page.sourceText).toBe('Short idea');http.expectNone(r=>r.method!=='GET');});
  it('requires confirmation before copying an idea into detailed story mode and preserves provenance',()=>{const {page}=open();page.sourceText='Türkçe fikir — çığlık: ğüşİ';page.useDetailedStoryMode();expect(page.confirmDialogOpen).toBe(true);expect(page.inputMode).toBe('IDEA');page.resolveConfirmation(false);expect(page.inputMode).toBe('IDEA');expect(page.sourceTexts.IDEA).toBe('Türkçe fikir — çığlık: ğüşİ');page.useDetailedStoryMode();page.resolveConfirmation(true);expect(page.inputMode).toBe('DETAILED_STORY');expect(page.sourceTexts.IDEA).toBe('Türkçe fikir — çığlık: ğüşİ');expect(page.sourceTexts.DETAILED_STORY).toBe('Türkçe fikir — çığlık: ğüşİ');expect(page.sourceText).toBe('Türkçe fikir — çığlık: ğüşİ');http.expectNone(r=>r.method!=='GET');});
  it('labels improvement intent accurately and keeps workspace state unsaved until draft persistence',()=>{const {page}=open();page.storyMode='IMPROVE_EXISTING_STORY';page.inputMode='IDEA';expect(page.storyMode).toBe('IMPROVE_EXISTING_STORY');page.workspacePath='library/work';expect((page as any).ideaDraftRevision).toBe(0);});
  it('blocks paid requests without current operation consent, budget, source and workspace',()=>{const {page}=open();page.idea='An idea';page.requestStories();http.expectNone(r=>r.url.endsWith('/creative-role'));expect(page.generationDialogOpen).toBe(false);page.workspacePath='library/work';page.prepareStoryGeneration();expect(page.generationDialogOpen).toBe(true);expect(page.storyConsent).toBe(false);page.requestStories();http.expectNone(r=>r.url.endsWith('/creative-role'));page.cancelStoryGeneration();expect(page.storyConsent).toBe(false);});
  it('protects closing an edited unsaved draft without creating records',()=>{const {page}=open();page.sourceText='My concept';const spy=vi.spyOn(window,'confirm').mockReturnValue(false);page.collapseNewStory();expect(page.newStoryOpen).toBe(true);expect(page.sourceText).toBe('My concept');spy.mockRestore();http.expectNone(r=>r.method!=='GET');});
  it('saves a free draft once and ignores a duplicate click',()=>{const {page}=open();page.workspacePath='library/work';page.sourceText='My concept';page.saveIdeaDraft();page.saveIdeaDraft();const request=http.expectOne('/api/v1/intelligence/workflow/idea-drafts');expect(request.request.body.expectedRevision).toBe(0);expect(request.request.body.state.idea).toBe('My concept');const id=request.request.body.draftId;request.flush({draftId:id,revision:1,status:'DRAFT',checkpoint:'IDEA',state:request.request.body.state});expect(page.ideaDraftId).toBe(id);expect(page.ideaDraftRevision).toBe(1);expect(page.stage).toBe('IDEA');expect(page.approvalRecordId).toBe('');http.expectNone(r=>r.url.endsWith('/creative-role'));});
  it('keeps newer edits after delayed save and does not falsely mark them saved',()=>{const {page}=open();page.workspacePath='library/work';page.sourceText='First';page.saveIdeaDraft();const r=http.expectOne('/api/v1/intelligence/workflow/idea-drafts');page.sourceText='Newer';r.flush({draftId:r.request.body.draftId,revision:1,state:r.request.body.state,status:'DRAFT',checkpoint:'IDEA'});expect(page.sourceText).toBe('Newer');expect(page.draftDirty).toBe(true);});
  it('continues human story through actual persistence without manufactured approval',()=>{const {page}=open();page.inputMode='DETAILED_STORY';page.onModeChange();page.workspacePath='library/work';page.sourceText='Operator story';page.useManualStory();const save=http.expectOne('/api/v1/intelligence/workflow/idea-drafts');save.flush({draftId:save.request.body.draftId,revision:1,state:save.request.body.state,status:'DRAFT',checkpoint:'IDEA'});const continuation=http.expectOne(`/api/v1/intelligence/workflow/idea-drafts/${page.ideaDraftId}/continue`);continuation.flush({draftId:page.ideaDraftId,revision:1,state:save.request.body.state,storyRecordId:'human-record',result:{alternatives:[{candidateId:'human-candidate',title:'My story',text:'Operator story'}]},checkpoint:'STORY'});expect(page.stage).toBe('STORY');expect(page.storyRecordId).toBe('human-record');expect(page.approvalRecordId).toBe('');expect(page.canVisit('PROMPT')).toBe(false);});
  it('distinguishes loading and API failure from a verified empty database and supports Retry',()=>{const fixture=TestBed.createComponent(CreativeStudioPage);fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('Loading saved projects');http.match(r=>r.method==='GET').forEach(r=>r.request.url.endsWith('idea-drafts')?r.flush({detail:'offline'},{status:503,statusText:'Unavailable'}):r.flush(r.request.url.endsWith('readiness')?{roles:[]}:[]));fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('Saved projects could not be loaded');expect(fixture.nativeElement.textContent).not.toContain('No saved projects yet');fixture.componentInstance.retrySavedProjects();http.match(r=>r.method==='GET').forEach(r=>r.flush([]));fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('No saved projects yet');});
  it('shows filtered-zero explanation only when saved records exist',()=>{const {page,fixture}=open();page.savedIdeaDrafts=[{draftId:'draft-a',state:{title:'Original',idea:'My source',inputMode:'IDEA'},revision:1}];page.savedStoryQuery='Unmatched';fixture.changeDetectorRef.markForCheck();fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('No saved projects match these filters');expect(fixture.nativeElement.textContent).toContain('Clear Filters');page.clearSavedFilters();fixture.changeDetectorRef.markForCheck();fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('Original');});
  it('restores the exact workspace and draft ID without creating a duplicate on reopen',()=>{const {page}=open();const draft={draftId:'saved-draft',revision:2,state:{inputMode:'DETAILED_STORY',idea:'Exact story',title:'Saved',workspacePath:'library/exact',sourceTexts:{IDEA:'Original idea',DETAILED_STORY:'Exact story',EXISTING_PROMPT:''}},checkpoint:'IDEA'};page.restoredCharacterName='Another project character';page.openIdeaDraft(draft);const r=http.expectOne(request=>request.url.endsWith('/idea-drafts/saved-draft'));expect(r.request.params.get('workspacePath')).toBe('library/exact');r.flush(draft);expect(page.restoredCharacterName).toBe('');expect(page.ideaDraftId).toBe('saved-draft');expect(page.sessionId).toBe('saved-draft');expect(page.sourceText).toBe('Exact story');expect(page.workspacePath).toBe('library/exact');expect(page.storyRecordId).toBe('');expect(page.draftDirty).toBe(false);http.expectNone(r=>r.method!=='GET');});
  it('rejects a delayed open response when the operator makes newer form edits',()=>{const {page}=open();const draft={draftId:'old',revision:1,state:{inputMode:'IDEA',idea:'Old source',workspacePath:'library/exact'}};page.openIdeaDraft(draft);const r=http.expectOne(request=>request.url.endsWith('/idea-drafts/old'));page.sourceText='New operator edit';r.flush(draft);expect(page.sourceText).toBe('New operator edit');expect(page.ideaDraftId).toBe('');});
  it('continues a persisted operator prompt directly without generated story or approval',()=>{const {page}=open();vi.spyOn(TestBed.inject(Router),'navigateByUrl').mockResolvedValue(true);page.inputMode='EXISTING_PROMPT';page.onModeChange();page.workspacePath='library/exact';page.sourceText='  Exact camera prompt\nwith shot detail  ';page.useExistingPrompt();const save=http.expectOne('/api/v1/intelligence/workflow/idea-drafts');expect(save.request.body.state.promptText).toBe(page.sourceText);save.flush({draftId:save.request.body.draftId,revision:1,state:save.request.body.state,checkpoint:'IDEA'});const r=http.expectOne(`/api/v1/intelligence/workflow/idea-drafts/${page.ideaDraftId}/continue`);r.flush({draftId:page.ideaDraftId,revision:1,checkpoint:'PRODUCTION_REVIEW',contentId:12,promptVersionId:20,rawText:page.sourceText});expect(page.promptVersionId).toBe('20');expect(page.draftPrompt).toBe('  Exact camera prompt\nwith shot detail  ');expect(page.storyRecordId).toBe('');expect(page.approvalRecordId).toBe('');expect(page.canVisit('PRODUCTION_REVIEW')).toBe(true);expect(page.canVisit('STORY')).toBe(false);http.expectNone(r=>r.url.endsWith('/creative-role'));});
  it('consumes generation consent on dispatch and never retries after failure',()=>{const {page}=open();page.sourceText='A concept';page.workspacePath='library/exact';page.prepareStoryGeneration();page.storyConsent=true;page.budget=.05;page.requestStories();const r=http.expectOne('/api/v1/intelligence/workflow/creative-role');expect(r.request.body.generationAuthorized).toBe(true);expect(page.storyConsent).toBe(false);r.flush({detail:'Provider unavailable'},{status:503,statusText:'Unavailable'});page.requestStories();http.expectNone(r=>r.url.endsWith('/creative-role'));expect(page.approvalRecordId).toBe('');});
  it('offers catalog suggestions without binding a character automatically',()=>{const {page}=open();page.characters=[{id:'real-mimi',name:'Mimi'},{id:'real-kiko',name:'Kiko'}];page.sourceText='Mimi follows a map';expect(page.suggestedCharacter.id).toBe('real-mimi');expect(page.mainCharacterId).toBe('');page.chooseSuggestedCharacter();expect(page.mainCharacterId).toBe('real-mimi');page.mainCharacterId='';page.sourceText='Mimi meets Kiko';expect(page.suggestedCharacter).toBeNull();});
  it('uses the same prompt entry path from the header without a server write',()=>{const {page}=open();page.sourceText='Idea remains separate';page.startExistingPrompt();expect(page.inputMode).toBe('EXISTING_PROMPT');expect(page.sourceText).toBe('');page.sourceText='Prompt';page.inputMode='IDEA';page.onModeChange();expect(page.sourceText).toBe('Idea remains separate');http.expectNone(r=>r.method!=='GET');});
  it('retains source and draft identity after save failure for safe retry',()=>{const {page}=open();page.workspacePath='library/exact';page.sourceText='My source';page.saveIdeaDraft();const first=http.expectOne('/api/v1/intelligence/workflow/idea-drafts');const id=first.request.body.draftId;first.flush({detail:'Offline'},{status:503,statusText:'Unavailable'});expect(page.draftSaving).toBe(false);expect(page.sourceText).toBe('My source');page.saveIdeaDraft();const retry=http.expectOne('/api/v1/intelligence/workflow/idea-drafts');expect(retry.request.body.draftId).toBe(id);retry.flush({draftId:id,revision:1,state:retry.request.body.state,checkpoint:'IDEA'});});
  it('shows workspace errors with Retry rather than treating a failed request as no destinations',()=>{const fixture=TestBed.createComponent(CreativeStudioPage);fixture.detectChanges();http.match(r=>r.method==='GET').forEach(r=>r.request.url.endsWith('destinations')?r.flush({detail:'Offline'},{status:503,statusText:'Unavailable'}):r.flush(r.request.url.endsWith('readiness')?{roles:[]}:[]));fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('Workspaces could not be loaded');expect(fixture.nativeElement.textContent).not.toContain('Create Workspace — free');fixture.componentInstance.loadWorkspaces();http.expectOne('/api/v1/videos/prompt-workspaces/destinations').flush([{folderPath:'library/exact',creativeName:'Exact destination'}]);fixture.detectChanges();expect(fixture.nativeElement.textContent).toContain('Exact destination');});
  it('makes exactly one authorized mocked generation operation and saves unapproved candidates',()=>{const {page}=open();page.workspacePath='library/exact';page.sourceText='A short idea';page.profile='EDUCATIONAL';page.storyMode='EXPLORE_DIFFERENT_STORIES';page.prepareStoryGeneration();page.storyConsent=true;page.budget=.1;page.requestStories();page.requestStories();const r=http.expectOne('/api/v1/intelligence/workflow/creative-role');expect(r.request.body.context.targetConfiguration.contentProfile).toBe('EDUCATIONAL');expect(r.request.body.context.storyGenerationMode).toBe('EXPLORE_DIFFERENT_STORIES');r.flush({recordId:'generated-story',result:{alternatives:[{candidateId:'one',text:'Mock story'}]}});expect(page.candidates.length).toBe(1);expect(page.storyRecordId).toBe('generated-story');expect(page.approvalRecordId).toBe('');expect(page.promptVersionId).toBe('');expect(page.stage).toBe('STORY');http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));http.expectNone(r=>r.url.includes('render'));});
  it('summarizes selected mode and actual values independently of profile and strategy',()=>{const {page}=open();expect(page.activeContextTitle).toBe('Not set');page.title='Operator title';page.inputMode='DETAILED_STORY';page.onModeChange();page.profile='CURIOSITY_ADVENTURE';page.storyMode='EXPLORE_DIFFERENT_STORIES';expect(page.nextAction).toContain('Save and review your story');expect(page.activeContextTitle).toBe('Operator title');expect(page.profile).toBe('CURIOSITY_ADVENTURE');expect(page.storyMode).toBe('EXPLORE_DIFFERENT_STORIES');page.inputMode='EXISTING_PROMPT';page.onModeChange();expect(page.nextAction).toContain('production prompt');});

  it('starts a separate draft with no inherited project or destination',()=>{const {page}=open();page.ideaDraftId='saved-id';page.ideaDraftRevision=1;page.workspacePath='library/old';page.idea='Saved text';page.draftBaseline=page.captureDraft();page.startNewDraft();expect(page.ideaDraftId).toBe('');expect(page.ideaDraftRevision).toBe(0);expect(page.workspacePath).toBe('');expect(page.idea).toBe('');http.expectNone(r=>r.method!=='GET');});
  it('shows an imported story only once as its owning saved project',()=>{const {page}=open();page.savedIdeaDrafts=[{draftId:'owner',storyRecordId:'human-record',state:{idea:'Human',title:'Human'}}];page.savedStories=[{recordId:'human-record',sourceType:'OPERATOR',result:{alternatives:[{candidateId:'one',text:'Human'}]}}];expect(page.allSavedProjectCount).toBe(1);expect(page.filteredSavedStories).toEqual([]);expect(page.storySessionLabel(page.savedStories[0])).toBe('Operator-supplied story');});

  it('classifies title-only near duplicates from body evidence and offers the immutable original',()=>{const {page,fixture}=open();(page as any).loadStoryReviewFixture();fixture.changeDetectorRef.detectChanges();expect(page.storyQuality.classification).toBe('NEAR_DUPLICATE');expect(page.storyQuality.evidenceState).toBe('SAME');expect(page.storyQuality.pairs.every((pair:any)=>pair.evidenceState==='SAME')).toBe(true);expect(page.storyQuality.originalComparisons.length).toBe(3);expect(page.storyQuality.differences).toEqual([]);expect(fixture.nativeElement.textContent).toContain('Original Story · No AI changes');page.selectOriginalStory();expect(page.selectedCandidateIdValue).toBe('ORIGINAL_SOURCE');expect(page.selectedStory).toBe(page.idea);http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));http.expectNone(r=>r.method==='POST');});
  it('keeps malformed review payloads as explicit diagnostic evidence',()=>{const {page}=open();const review=(page as any).normalizeStoryReview('{malformed');expect(review.reviewStatus).toBe('INVALID');expect(review.evidenceLimitations[0]).toContain('malformed');expect(review.rawProviderResponse).toBe('{malformed');});
  it('normalizes nested findings into labelled evidence without flattening objects',()=>{const {page}=open();page.candidates=[{candidateId:'one',title:'Birinci',text:'Türkçe öykü — çığlık'}];page.storyReview={candidateReviews:[{candidateId:'one',findings:[{finding:'Progression is clear',dimension:'escalation',supportingTextEvidence:['Mimi opens the cabinet','Not: çığlık'],confidenceOrEvidenceStatus:null,suggestedMinimalImprovement:null}]}]};const rows=page.normalizedReviewFindings('one');expect(rows).toHaveLength(1);expect(rows[0].finding).toBe('Progression is clear');expect(rows[0].supportingText).toEqual(['Mimi opens the cabinet','Not: çığlık']);expect(rows[0].severity).toBe('Evidence unavailable');expect(rows[0].confidence).toBe('Evidence unavailable');expect(JSON.stringify(rows)).not.toContain('[object Object]');});
  it('labels fixture and unavailable review timestamps without inventing dates',()=>{const {page}=open();page.storyReview={reviewId:'LOCAL_MOCK_REVIEW',reviewModel:'local-mock',reviewTimestamp:'2023-10-05T12:00:00Z'};expect(page.reviewTimestampLabel()).toBe('DEMO / FIXTURE · Review time unavailable');page.storyReview={reviewId:'live',reviewModel:'gpt',reviewTimestamp:'not-a-date'};expect(page.reviewTimestampLabel()).toBe('Review time unavailable');});
  it('renders nested provider findings without object coercion and marks missing concerns unknown',()=>{const {page}=open();page.storyReview={overallConcerns:null};expect(page.reviewFindingsText({opening:{status:'PRESENT',evidence:['Mimi opens']},ending:null})).toContain('opening: status: PRESENT');expect(page.reviewFindingsText({opening:{status:'PRESENT'}})).not.toContain('[object Object]');expect(page.reviewConcernsLabel()).toBe('Unknown');page.storyReview={overallConcerns:[]};expect(page.reviewConcernsLabel()).toBe('0');expect(page.reviewFindingsText(null)).toBe('Evidence unavailable');});
  it('keeps high lexical similarity uncertain when semantic evidence is absent',()=>{const {page}=open();page.candidates=[{candidateId:'a',title:'A',text:'Mimi opens the cabinet and follows the notes to the map.'},{candidateId:'b',title:'B',text:'Mimi opens the cabinet and follows the notes to the door.'}];page.storyQuality=null;(page as any).reconcileStoryComparison();expect(page.storyQuality.classification).toBe('INSUFFICIENT_EVIDENCE');expect(page.storyQuality.evidenceState).toBe('UNKNOWN');});
  it('returns insufficient evidence for lexical differences without invented semantics',()=>{const {page}=open();page.candidates=[{candidateId:'a',title:'Same title',text:'A child opens a red door.'},{candidateId:'b',title:'Same title',text:'A storm crosses the empty harbour while lights fade.'}];page.storyQuality=null;(page as any).reconcileStoryComparison();expect(page.storyQuality.classification).toBe('INSUFFICIENT_EVIDENCE');expect(page.storyQuality.differences).toEqual([]);expect(page.storyQuality.evidenceState).toBe('UNKNOWN');});
  it('sends preservation settings and useful refinement directions without provider-side title comparison',()=>{const {page}=open();page.workspacePath='library/exact';page.sourceText='Türkçe kaynak hikâye';page.storyMode='IMPROVE_EXISTING_STORY';page.lockedRequirements=['PRESERVE_CORE_PREMISE'];page.prepareStoryGeneration();page.storyConsent=true;page.budget=.1;page.requestStories();const request=http.expectOne('/api/v1/intelligence/workflow/creative-role');expect(request.request.body.context.lockedRequirements).toEqual(['PRESERVE_CORE_PREMISE']);expect(request.request.body.context.refinementDirections.length).toBeGreaterThan(0);expect(request.request.body.context.permittedVariation.toLowerCase()).toContain('unchecked');request.flush({recordId:'story',result:{alternatives:[{candidateId:'a',title:'Title A',text:'Exact'}]}});http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));});
  it('shows one primary action while preparing paid generation',()=>{const {page,fixture}=open();page.sourceText='A concept';page.workspacePath='library/exact';page.prepareStoryGeneration();fixture.changeDetectorRef.markForCheck();fixture.detectChanges();expect(fixture.nativeElement.querySelectorAll('.new-story-form .button--primary').length).toBe(1);expect(fixture.nativeElement.querySelector('.new-story-form .button--primary').textContent.trim()).toBe('Confirm generation');});
  it('compact modal shows only selected candidate detail by default and comparison summary at top', () => {
    const { page, fixture } = open();
    page.storyReview = {
      reviewId: 'test-review',
      reviewModel: 'gpt-4o-mini',
      reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewPolicyVersion: 'story-review-v1',
      reviewStatus: 'COMPLETED',
      diversityAssessment: { classification: 'INSUFFICIENT_EVIDENCE', summary: 'Cannot determine' },
      comparativeFindings: [],
      candidateReviews: [
        { candidateId: 'a', overallStatus: 'STRONG_CANDIDATE', editorialRecommendation: 'STRONG_CANDIDATE', strengths: ['Clear opening'], concerns: [], materialFindings: [], suggestedMinimalImprovements: [], confidenceOrEvidenceStatus: 'SUPPORTED' },
        { candidateId: 'b', overallStatus: 'NEEDS_REVISION', editorialRecommendation: 'NEEDS_REVISION', strengths: [], concerns: ['Weak ending'], materialFindings: [], suggestedMinimalImprovements: [], confidenceOrEvidenceStatus: 'POTENTIAL_RISK' }
      ],
      recommendedCandidateId: null,
      recommendationReason: 'No preference supported',
      overallConcerns: [],
      usageAndCost: { provider: 'openai', costUpperBoundUsd: 0.01 },
      evidenceLimitations: [],
      revisionComparison: { resolved: [], remaining: [], newFindings: [] }
    };
    page.candidates = [
      { candidateId: 'a', title: 'Story A', text: 'First candidate text' },
      { candidateId: 'b', title: 'Story B', text: 'Second candidate text' }
    ];
    page.selectedCandidateIdValue = 'a';
    page.storyQuality = { classification: 'INSUFFICIENT_EVIDENCE', summary: 'Cannot determine', pairs: [], differences: [], evidenceState: 'UNKNOWN' };
    page.reviewDialogOpen = true;
    page.stage = 'STORY';
    // reviewDialogTab defaults to '' so reviewDialogSelectedId falls back to selectedCandidateId = 'a'
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges();
    const dialog = fixture.nativeElement.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    // Comparison summary visible
    expect(dialog.textContent).toContain('Canonical comparison');
    expect(dialog.textContent).toContain('INSUFFICIENT EVIDENCE');
    // Candidate selector tabs present
    const tabs = fixture.nativeElement.querySelectorAll('[role="tab"]');
    expect(tabs.length).toBe(2);
    // Selected panel visible, other panel hidden
    const panels = fixture.nativeElement.querySelectorAll('[role="tabpanel"]');
    expect(panels.length).toBe(2);
    expect((panels[0] as HTMLElement).hidden).toBe(false);   // 'a' is selected
    expect((panels[1] as HTMLElement).hidden).toBe(true);    // 'b' is hidden
    // Story text of selected candidate is visible
    expect(panels[0].textContent).toContain('First candidate text');
    // Story text of non-selected candidate is not visible (hidden)
    expect(panels[1].textContent).toContain('Second candidate text'); // still in DOM but hidden
  });

  it('renders structured findings as collapsed details elements, not all-expanded rows', () => {
    const { page, fixture } = open();
    page.storyReview = {
      reviewId: 'r', reviewModel: 'gpt', reviewTimestamp: '2026-10-11T10:00:00Z',
      reviewPolicyVersion: 'v1', reviewStatus: 'COMPLETED',
      diversityAssessment: { classification: 'INSUFFICIENT_EVIDENCE', summary: 'Unknown' },
      comparativeFindings: [],
      candidateReviews: [{
        candidateId: 'c1', overallStatus: 'STRONG_CANDIDATE', editorialRecommendation: 'STRONG_CANDIDATE',
        strengths: [], concerns: [], materialFindings: [], suggestedMinimalImprovements: [],
        confidenceOrEvidenceStatus: 'SUPPORTED',
        findings: [
          { finding: 'Clear opening', dimension: 'opening visual promise', severity: 'low', supportingTextEvidence: ['Mimi opens the cabinet'], confidenceOrEvidenceStatus: 'SUPPORTED', suggestedMinimalImprovement: 'None required' },
          { finding: 'Ambiguous ending', dimension: 'ending/payoff', severity: 'medium', supportingTextEvidence: [], confidenceOrEvidenceStatus: 'POTENTIAL_RISK', suggestedMinimalImprovement: 'Clarify the final action' }
        ]
      }],
      recommendedCandidateId: null, recommendationReason: '',
      overallConcerns: [], usageAndCost: { provider: 'openai', costUpperBoundUsd: 0.01 },
      evidenceLimitations: [], revisionComparison: { resolved: [], remaining: [], newFindings: [] }
    };
    page.candidates = [{ candidateId: 'c1', title: 'Test', text: 'A story' }];
    page.selectedCandidateIdValue = 'c1';
    page.reviewDialogOpen = true;
    page.stage = 'STORY';
    fixture.changeDetectorRef.markForCheck();
    fixture.detectChanges();
    const findingItems = fixture.nativeElement.querySelectorAll('.review-finding-item');
    expect(findingItems.length).toBe(2);
    // Findings are <details> elements — closed by default
    for (const item of Array.from(findingItems)) {
      expect((item as HTMLDetailsElement).open).toBe(false);
    }
    // The headline is visible in the summary
    expect(fixture.nativeElement.querySelector('.review-finding-headline')?.textContent).toContain('Clear opening');
    // The low-severity class is applied to the first finding
    expect(fixture.nativeElement.querySelector('.review-finding-sev--low')).not.toBeNull();
    // Text assessment disclaimer is present
    expect(fixture.nativeElement.querySelector('.review-text-assessment-disclaimer')).not.toBeNull();
  });

});
