import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { vi } from 'vitest';
import { CreativeStudioPage } from './creative-studio.page';

function fingerprint(value:string){let hash=0x811c9dc5;for(let i=0;i<value.length;i++)hash=Math.imul(hash^value.charCodeAt(i),0x01000193);return (hash>>>0).toString(16).padStart(8,'0');}

describe('creative studio idea-first workflow', () => {
  it('accepts a short idea, persists story approval, and sends the approved story to BUILD_PROMPT', async () => {
    localStorage.removeItem('pompom.creative-studio.v1');
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    const fixture=TestBed.createComponent(CreativeStudioPage); const page=fixture.componentInstance; const http=TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({enabled:true,roles:[{role:'STORY',configured:true,model:'fixture'},{role:'BUILD_PROMPT',configured:true,model:'fixture'}]});
    http.expectOne('/api/v1/characters').flush([{id:'00000000-0000-0000-0000-000000000002',name:'Kiko'}]);
    http.expectOne('/api/v1/videos/prompt-workspaces/destinations').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/idea-drafts').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_STUDIO_SESSION').flush([]);
    page.idea='Kiko sınava giriyor'; page.workspacePath='library/fixture'; page.prepareStoryGeneration(); page.storyConsent=true; page.budget=0.01; page.requestStories();
    expect(page.error).toContain('Select a registered Pompom Hills character');
    page.mainCharacterId='00000000-0000-0000-0000-000000000002'; page.requestStories();
    const story=http.expectOne('/api/v1/intelligence/workflow/creative-role'); expect(story.request.body.text).toBe('Kiko sınava giriyor'); story.flush({recordId:'story-1',result:{alternatives:['Kiko kalemiyle konuşur.']}});
    await fixture.whenStable(); page.selectStory(page.candidates[0]); page.approveStory();
    const approval=http.expectOne('/api/v1/intelligence/workflow/creative-role/story-1/approve-story'); expect(approval.request.body.approvedText).toContain('kalemiyle'); approval.flush({recordId:'approval-1'});
    await fixture.whenStable(); page.promptConsent=true; page.buildPrompt();
    const build=http.expectOne('/api/v1/intelligence/workflow/creative-role'); expect(build.request.body.role).toBe('BUILD_PROMPT'); expect(build.request.body.context.sourceStoryRecordId).toBe('story-1'); expect(build.request.body.context.candidateId).toBe(page.selectedCandidateId); expect(build.request.body.context.approvalRecordId).toBe('approval-1'); expect(build.request.body.context.storyRevisionId).toContain('candidate-1-revision-'); expect(build.request.body.text).toContain('kalemiyle'); build.flush({recordId:'builder-1',result:{prompt:'Kiko enters a classroom and the pencil moves.'}});
    expect(page.builderRecordId).toBe('builder-1'); http.match(r=>r.method==='PUT').forEach(r=>r.flush({})); http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
});

describe('saved story reuse', () => {
  it('hydrates a saved STORY record without requesting the provider again', async () => {
    localStorage.removeItem('pompom.creative-studio.v1');
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    const fixture=TestBed.createComponent(CreativeStudioPage); const page=fixture.componentInstance; const http=TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({enabled:true,roles:[{role:'STORY',configured:true,model:'fixture'}]});
    http.expectOne('/api/v1/characters').flush([]);
    http.expectOne('/api/v1/videos/prompt-workspaces/destinations').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([{recordId:'saved-1',role:'STORY',sourceRequest:{text:'Kiko finds a door'},alternatives:['Kiko opens the door and finds a tiny stage.']}]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/idea-drafts').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_STUDIO_SESSION').flush([]);
    await fixture.whenStable();
    expect(page.savedStories).toHaveLength(1);
    page.useSavedStory(page.savedStories[0]);
    expect(page.stage).toBe('STORY');
    expect(page.storyRecordId).toBe('saved-1');
    expect(page.selectedStory).toContain('tiny stage');
    expect(page.activeJourney).toBe('SAVED');
    expect(page.storyCandidates(page.savedStories[0])).toHaveLength(1);
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
});

describe('step 1 journey safety', () => {
  async function createPage() {
    localStorage.removeItem('pompom.creative-studio.v1');
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    const fixture=TestBed.createComponent(CreativeStudioPage); const page=fixture.componentInstance; const http=TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({enabled:true,roles:[{role:'STORY',configured:true,model:'fixture'}]});
    http.expectOne('/api/v1/characters').flush([]);
    http.expectOne('/api/v1/videos/prompt-workspaces/destinations').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/idea-drafts').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_STUDIO_SESSION').flush([]);
    return {fixture,page,http};
  }
  it('preserves an unsaved new draft while reusing a saved story', async () => {
    const {fixture,page,http}=await createPage();
    page.idea='A new unsubmitted idea'; page.title='Unsaved title'; page.persist();
    page.savedStories=[{recordId:'saved-2',idea:'Saved source',result:{alternatives:['Saved candidate']}}];
    page.useSavedStory(page.savedStories[0]);
    expect(page.activeJourney).toBe('SAVED');
    expect(page.selectedStory).toBe('Saved candidate');
    expect(page.newDraftSnapshot.idea).toBe('A new unsubmitted idea');
    page.selectJourney('NEW');
    expect(page.idea).toBe('A new unsubmitted idea');
    expect(page.title).toBe('Unsaved title');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('persists input type and generation strategy independently and removes the empty advanced section', async () => {
    const {fixture,page,http}=await createPage();
    page.inputMode='DETAILED_STORY'; page.storyMode='IMPROVE_EXISTING_STORY'; page.onStoryModeChange(); page.persist();
    const saved=JSON.parse(localStorage.getItem('pompom.creative-studio.v1')!);
    expect(saved.inputMode).toBe('DETAILED_STORY');
    expect(saved.storyMode).toBe('IMPROVE_EXISTING_STORY');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Advanced Settings / Destination');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('keeps reusable work collapsed until the operator explicitly starts a new story', async () => {
    const {fixture,page,http}=await createPage();
    page.savedStories=[{recordId:'saved-3',idea:'Saved source',result:{alternatives:['Saved candidate']}}];
    page.savedStoriesLoading=false;
    page.activeJourney='RESUME';
    await fixture.whenStable();
    fixture.detectChanges();
    expect(page.activeJourney).toBe('RESUME');
    expect(fixture.nativeElement.querySelector('.new-story-form')).toBeNull();
    page.selectJourney('NEW');
    expect(page.activeJourney).toBe('NEW');
    expect(page.newStoryOpen).toBe(true);
    expect(page.storyRecordId).toBe('');
    expect(page.candidates).toEqual([]);
    page.collapseNewStory();
    fixture.detectChanges();
    expect(page.newStoryOpen).toBe(false);
    expect(fixture.nativeElement.querySelector('.new-story-form')).toBeNull();
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('keeps summary fields tied to the active draft after leaving a saved story', async () => {
    const {fixture,page,http}=await createPage();
    page.savedStories=[{recordId:'saved-context',idea:'Saved source',result:{title:'Saved title',alternatives:['Saved candidate'],sourceRequest:{context:{mainCharacter:'Kiko',contentProfile:'EDUCATIONAL',duration:8,aspectRatio:'16:9'}}}}];
    page.useSavedStory(page.savedStories[0]);
    expect(page.activeContextTitle).toBe('Saved title');
    expect(page.activeContextCharacter).toBe('Kiko');
    page.selectJourney('NEW');
    page.title='Fresh draft'; page.mainCharacterId=''; page.profile='AUTO'; page.duration=15; page.aspectRatio='9:16';
    expect(page.storyRecordId).toBe('');
    expect(page.activeContextTitle).toBe('Fresh draft');
    expect(page.activeContextCharacter).toBe('Not selected / Let AI suggest');
    expect(page.activeContextProfile).toBe('AUTO');
    expect(page.activeContextAspectRatio).toBe('9:16');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('falls back to the exact persisted studio session for summary identity and settings', async () => {
    const {fixture,page,http}=await createPage();
    page.sessionId='session-exact'; page.activeJourney='RESUME'; page.storyRecordId='missing-story-row'; page.title='stale narrative title';
    page.savedStudioSessions=[{sessionId:'session-other',title:'Wrong title',profile:'WRONG',duration:99,aspectRatio:'1:1'},
      {sessionId:'session-exact',title:'Mimi Canonical Title',mainCharacter:'Mimi',profile:'ABSURD_PHYSICS',duration:15,aspectRatio:'9:16'}];
    expect(page.activeContextTitle).toBe('Mimi Canonical Title');
    expect(page.activeContextCharacter).toBe('Mimi');
    expect(page.activeContextProfile).toBe('ABSURD_PHYSICS');
    expect(page.activeContextDuration).toBe(15);
    expect(page.activeContextAspectRatio).toBe('9:16');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('does not mark a saved story approved when the stored candidate identity does not match', async () => {
    const {fixture,page,http}=await createPage();
    page.savedStories=[{recordId:'saved-identity',idea:'Saved source',result:{alternatives:[{candidateId:'candidate-1',text:'One'},{candidateId:'candidate-2',text:'Two'}]}}];
    page.savedApprovals=[{recordId:'approval-wrong',storyRecordId:'saved-identity',candidateId:'candidate-99',revisionId:'candidate-99-revision-deadbeef'}];
    page.useSavedStory(page.savedStories[0]);
    expect(page.approvalRecordId).toBe('');
    expect(page.storyApprovalStatus).toBe('REVIEW_REQUIRED');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('does not expose technical workspace paths in the ordinary option label', async () => {
    const {fixture,page,http}=await createPage();
    page.selectJourney('NEW');
    page.workspaces=[{creativeName:'Mimi Studio',folderPath:'library/POMPOM_HILLS_PRODUCTION/secret/long/path'}];
    fixture.detectChanges();
    const option=fixture.nativeElement.querySelector('select option[title]') as HTMLOptionElement;
    expect(option.textContent?.trim()).toBe('Mimi Studio');
    expect(option.title).toContain('library/POMPOM_HILLS_PRODUCTION');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('keeps saved-project actions unavailable until story, approval and session indexes are loaded', async () => {
    localStorage.removeItem('pompom.creative-studio.v1');
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    const fixture=TestBed.createComponent(CreativeStudioPage); const page=fixture.componentInstance; const http=TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({enabled:true});
    http.expectOne('/api/v1/characters').flush([]);
    http.expectOne('/api/v1/videos/prompt-workspaces/destinations').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([{recordId:'story-indexed',role:'STORY',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text:'Saved story.'}]}}]);
    const approvals=http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL');
    const sessions=http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_STUDIO_SESSION');
    http.expectOne('/api/v1/intelligence/workflow/idea-drafts').flush([]);
    fixture.detectChanges();
    expect(page.savedStoriesLoading).toBe(true);
    expect(fixture.nativeElement.querySelector('[aria-label="Saved projects"]')).toBeNull();
    approvals.flush([{recordId:'approval-indexed',storyRecordId:'story-indexed',candidateId:'candidate-1',revisionId:`candidate-1-revision-${fingerprint('Saved story.')}`,contentFingerprint:fingerprint('Saved story.'),approvedText:'Saved story.'}]);
    sessions.flush([]);
    fixture.detectChanges();
    expect(page.savedStoriesLoading).toBe(false);
    expect(fixture.nativeElement.querySelector('[aria-label="Saved projects"]')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Continue to Prompt');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(http.match(r=>r.method==='PUT')).toHaveLength(0);
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('keeps similar generation sessions separate and uses their stored canonical title', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi stands before a messy cabinet and a sticky note.';
    page.savedStories=[
      {recordId:'story-session-a',createdAt:'2026-10-10T12:00:00Z',idea:text,result:{alternatives:[{candidateId:'candidate-1',text}]}},
      {recordId:'story-session-b',createdAt:'2026-10-09T12:00:00Z',idea:text,result:{alternatives:[{candidateId:'candidate-1',text}]}}
    ];
    page.savedStudioSessions=[
      {storyRecordId:'story-session-a',title:'Mimi Sticky Note Mystery'},
      {storyRecordId:'story-session-b',title:'Mimi Sticky Note Mystery'}
    ];
    expect(page.filteredSavedStories).toHaveLength(2);
    expect(page.storyTitle(page.savedStories[0])).toBe('Mimi Sticky Note Mystery');
    expect(page.storySessionLabel(page.savedStories[0])).not.toBe(page.storySessionLabel(page.savedStories[1]));
    expect(page.storyTitle({...page.savedStories[0],title:undefined})).not.toContain('Mimi stands');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('marks only exact candidate, revision, text and fingerprint evidence approved', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi follows a note to a tiny stage.';
    const hash=fingerprint(text);
    const story:any={recordId:'story-exact',lifecycleStatus:'DRAFT',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    page.savedStories=[story];
    page.savedApprovals=[{recordId:'approval-valid',storyRecordId:'story-exact',candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText:text}];
    expect(page.savedLifecycle(story)).toBe('APPROVED');
    page.savedApprovals=[{recordId:'approval-invalid',storyRecordId:'story-exact',candidateId:'None',revisionId:'None',contentFingerprint:'',approvedText:text}];
    expect(page.savedLifecycle(story)).toBe('IN_REVIEW');
    expect(page.savedPrimaryAction(story)).toBe('Review Story');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('keeps project review separate from exact story approval and does not retain a stale approval on selection', async () => {
    const {fixture,page,http}=await createPage();
    const textA='Mimi follows a note to a tiny stage.'; const hashA=fingerprint(textA);
    const textB='Mimi hides from a note under a table.'; const hashB=fingerprint(textB);
    const approved:any={recordId:'story-approved',title:'Mimi’s Sticky Note Mystery',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text:textA}]}};
    const inReview:any={recordId:'story-review',title:'Mimi’s Sticky Note Mystery',lifecycleStatus:'IN_REVIEW',result:{alternatives:[{candidateId:'candidate-1',text:textB}]}};
    page.savedStories=[approved,inReview];
    page.savedApprovals=[{recordId:'approval-a',storyRecordId:'story-approved',candidateId:'candidate-1',revisionId:`candidate-1-revision-${hashA}`,contentFingerprint:hashA,approvedText:textA},
      {recordId:'approval-invalid-b',storyRecordId:'story-review',candidateId:'None',revisionId:'-revision-deadbeef',contentFingerprint:'',approvedText:textB}];
    page.useSavedStory(approved);
    expect(page.approvalRecordId).toBe('approval-a');
    page.builderRecordId='builder-a'; page.builderResult={prompt:'Prompt from project A'}; page.draftPrompt='Prompt from project A';
    page.useSavedStory(inReview);
    expect(page.savedLifecycle(inReview)).toBe('IN_REVIEW');
    expect(page.savedApprovalFor(inReview)).toBeNull();
    expect(page.approvalRecordId).toBe('');
    expect(page.builderRecordId).toBe('');
    expect(page.draftPrompt).toBe('');
    expect(page.storyApprovalStatus).toBe('REVIEW_REQUIRED');
    expect(page.nextAction).toBe('Review Story');
    expect(http.match(r=>r.method==='PUT')).toHaveLength(0);
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('keeps the explicitly selected candidate in review and persists approval only after the operator action', async () => {
    const {fixture,page,http}=await createPage();
    const story:any={recordId:'story-in-review',title:'Mimi’s Sticky Note Mystery',lifecycleStatus:'IN_REVIEW',result:{alternatives:[{candidateId:'candidate-1',text:'Candidate one.'},{candidateId:'candidate-2',text:'Candidate two.'}]}};
    page.savedStories=[story];
    page.savedStudioSessions=[{sessionId:'session-review',storyRecordId:'story-in-review',selectedCandidateIdValue:'candidate-2',profile:'ABSURD_PHYSICS',duration:15,aspectRatio:'9:16'}];
    page.useSavedStory(story);
    expect(page.stage).toBe('STORY');
    expect(page.selectedCandidateId).toBe('candidate-2');
    expect(page.selectedStory).toBe('Candidate two.');
    expect(page.approvalRecordId).toBe('');
    expect(page.storyApprovalStatus).toBe('REVIEW_REQUIRED');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    page.reviewSavedStory();
    page.selectStory(page.candidates[1]);
    page.approveStory();
    const approval=http.expectOne('/api/v1/intelligence/workflow/creative-role/story-in-review/approve-story');
    expect(approval.request.body.candidateId).toBe('candidate-2');
    expect(approval.request.body.approvedText).toBe('Candidate two.');
    expect(approval.request.body.revisionId).toBe(`candidate-2-revision-${fingerprint('Candidate two.')}`);
    approval.flush({recordId:'approval-candidate-2'});
    expect(page.approvalRecordId).toBe('approval-candidate-2');
    expect(page.stage).toBe('PROMPT');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('explains a missing compatible saved prompt while preserving the approved story and paid-call gate', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi follows one impossible sticky note.'; const hash=fingerprint(text);
    const story:any={recordId:'story-approved-without-prompt',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    page.savedStories=[story];
    page.savedApprovals=[{recordId:'approval-exact',storyRecordId:story.recordId,candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText:text}];
    page.useSavedStory(story);
    page.continueApprovedStory();
    fixture.detectChanges();
    expect(page.savedPromptRecoveryRequired).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('Production prompt needs to be created');
    expect(fixture.nativeElement.textContent).toContain('no compatible saved production prompt was found');
    expect(page.approvalRecordId).toBe('approval-exact');
    expect(page.storyRecordId).toBe(story.recordId);
    expect(page.promptConsent).toBe(false);
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(http.match(r=>r.method==='PUT')).toHaveLength(0);
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('does not let a stale session candidate replace the approved immutable revision', async () => {
    const {fixture,page,http}=await createPage();
    const approvedText='Candidate one is the approved immutable story.'; const hash=fingerprint(approvedText);
    const story:any={recordId:'story-approved-session-stale',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text:approvedText},{candidateId:'candidate-2',text:'Candidate two is an unapproved edit.'}]}};
    page.savedStories=[story];
    page.savedApprovals=[{recordId:'approval-candidate-1',storyRecordId:story.recordId,candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText}];
    page.savedStudioSessions=[{sessionId:'session-stale-candidate',storyRecordId:story.recordId,selectedCandidateIdValue:'candidate-2'}];
    page.useSavedStory(story);
    expect(page.approvalRecordId).toBe('approval-candidate-1');
    expect(page.selectedCandidateId).toBe('candidate-1');
    expect(page.selectedStory).toBe(approvedText);
    page.continueApprovedStory();
    expect(page.stage).toBe('PROMPT');
    expect(page.selectedStory).toBe(approvedText);
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(http.match(r=>r.method==='PUT')).toHaveLength(0);
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('ignores a stale server-session response after switching to a different saved project', async () => {
    const {fixture,page,http}=await createPage();
    page.sessionId='shared-session'; page.storyRecordId='story-current'; page.stage='STORY'; page.selectedStory='Current project story';
    (page as any).restoreServer({sessionId:'shared-session',storyRecordId:'story-other',stage:'PROMPT',selectedStory:'Other project story',builderRecordId:'builder-other'});
    expect(page.storyRecordId).toBe('story-current');
    expect(page.selectedStory).toBe('Current project story');
    expect(page.builderRecordId).toBe('');
    expect(page.sessionId).not.toBe('shared-session');
    expect(http.match(r=>r.method==='PUT')).toHaveLength(0);
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('restores exact prompt settings and editor for a same-title project without sharing its session identity', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi follows a note to a tiny stage.'; const hash=fingerprint(text);
    const story:any={recordId:'story-exact-a',title:'Mimi Sticky Note Mystery',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    const other:any={recordId:'story-exact-b',title:'Mimi Sticky Note Mystery',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text:'Another project story.'}]}};
    page.savedStories=[story,other];
    page.savedApprovals=[{recordId:'approval-exact-a',storyRecordId:'story-exact-a',candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText:text},
      {recordId:'approval-exact-b',storyRecordId:'story-exact-b',candidateId:'candidate-1',revisionId:`candidate-1-revision-${fingerprint('Another project story.')}`,contentFingerprint:fingerprint('Another project story.'),approvedText:'Another project story.'}];
    const target={duration:8,aspectRatio:'16:9',selectedGenerator:'SEEDANCE_2_5',contentProfile:'EDUCATIONAL',mainCharacter:'Mimi'};
    (page as any).savedBuildRecords=[{recordId:'build-exact-a',role:'BUILD_PROMPT',requestFingerprint:'fingerprint-a',sourceRequest:{context:{sourceStoryRecordId:'story-exact-a',candidateId:'candidate-1',storyRevisionId:`candidate-1-revision-${hash}`,targetConfiguration:target}},result:{prompt:'Exact project A production prompt.'}},
      {recordId:'build-exact-b',role:'BUILD_PROMPT',requestFingerprint:'fingerprint-b',sourceRequest:{context:{sourceStoryRecordId:'story-exact-b',candidateId:'candidate-1',storyRevisionId:`candidate-1-revision-${fingerprint('Another project story.')}`,targetConfiguration:{...target,duration:15,aspectRatio:'9:16',contentProfile:'ABSURD_PHYSICS'}}},result:{prompt:'Project B prompt.'}}];
    page.sessionId='shared-old-session';
    page.savedStudioSessions=[{sessionId:'shared-old-session',storyRecordId:'story-exact-a',title:'Mimi Sticky Note Mystery',profile:'EDUCATIONAL',duration:8,aspectRatio:'16:9'},
      {sessionId:'shared-old-session',storyRecordId:'story-exact-b',title:'Mimi Sticky Note Mystery',profile:'ABSURD_PHYSICS',duration:15,aspectRatio:'9:16',selectedCandidateIdValue:'candidate-1',approvalRecordId:'approval-exact-b',builderRecordId:'build-exact-b',contentId:'90',promptVersionId:'12',detailUrl:'/quality/detail?contentId=90&promptVersionId=12&studio=1'}];
    page.useSavedStory(other);
    expect(page.sessionId).not.toBe('shared-old-session');
    expect(page.canonicalSavedPrompt?.recordId).toBe('build-exact-b');
    expect(page.contentId).toBe('90');
    expect(page.promptVersionId).toBe('12');
    expect(page.detailUrl).toContain('promptVersionId=12');
    page.openCanonicalSavedPrompt();
    expect(page.draftPrompt).toBe('Project B prompt.');
    expect(page.profile).toBe('ABSURD_PHYSICS');
    expect(page.duration).toBe(15);
    expect(page.aspectRatio).toBe('9:16');
    expect(page.targetGenerator).toBe('SEEDANCE_2_5');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(http.match(r=>r.method==='PUT')).toHaveLength(0);
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('opens only the selected saved prompt and makes no provider call', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi follows a note to a tiny stage.';
    const hash=fingerprint(text);
    const story:any={recordId:'story-a',title:'Mimi Project A',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    page.savedStories=[story];
    page.savedApprovals=[{recordId:'approval-a',storyRecordId:'story-a',candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText:text}];
    (page as any).savedBuildRecords=[
      {recordId:'build-other',role:'BUILD_PROMPT',sourceRequest:{context:{sourceStoryRecordId:'story-b',storyRevisionId:`candidate-1-revision-${hash}`,targetConfiguration:{duration:15,aspectRatio:'9:16',selectedGenerator:'SEEDANCE_2_0_MINI',contentProfile:'AUTO',mainCharacter:''}}},result:{prompt:'Wrong project prompt'}},
      {recordId:'build-a',role:'BUILD_PROMPT',requestFingerprint:'fingerprint-a',sourceRequest:{context:{sourceStoryRecordId:'story-a',storyRevisionId:`candidate-1-revision-${hash}`,targetConfiguration:{duration:15,aspectRatio:'9:16',selectedGenerator:'SEEDANCE_2_0_MINI',contentProfile:'AUTO',mainCharacter:''}}},result:{prompt:'Exact saved prompt'}}
    ];
    page.useSavedStory(story);
    expect(page.canonicalSavedPrompt?.recordId).toBe('build-a');
    page.openCanonicalSavedPrompt();
    expect(page.stage).toBe('PROMPT');
    expect(page.draftPrompt).toContain('Exact saved prompt');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('restores an archived approved story using the backend returned status', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi finds a note.'; const hash=fingerprint(text);
    const story:any={recordId:'story-restore',lifecycleStatus:'ARCHIVED',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    page.savedStories=[story];
    page.savedApprovals=[{recordId:'approval-restore',storyRecordId:'story-restore',candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText:text}];
    page.restoreSavedStory(story);
    const restore=http.expectOne('/api/v1/intelligence/workflow/records/story-restore/lifecycle');
    expect(restore.request.body.status).toBe('DRAFT');
    restore.flush({status:'APPROVED',changedAt:'2026-10-10T12:00:00Z'});
    expect(page.savedLifecycle(story)).toBe('APPROVED');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('saves edits to an approved story as a separate unapproved revision', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi finds a note.';
    const source:any={recordId:'story-parent',title:'Mimi Note',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    page.savedStories=[source]; page.useSavedStory(source); page.selectedStory='Mimi finds a note and follows it.';
    expect(page.hasSelectedStoryEdits()).toBe(true);
    page.saveStoryRevision();
    const save=http.expectOne('/api/v1/intelligence/workflow/records/story-parent/story-revisions');
    expect(save.request.body.candidateId).toBe('candidate-1');
    expect(save.request.body.text).toBe('Mimi finds a note and follows it.');
    save.flush({recordId:'story-revision',title:'Mimi Note',createdAt:'2026-10-10T12:00:00Z',sourceRequest:{context:{parentStoryRecordId:'story-parent'}},result:{alternatives:[{candidateId:'candidate-1',text:'Mimi finds a note and follows it.'}]}});
    expect(page.savedStories[0].recordId).toBe('story-revision');
    expect(page.savedStories[0].lifecycleStatus).toBe('DRAFT');
    expect(source.result.alternatives[0].text).toBe(text);
    expect(page.storySessionLabel(page.savedStories[0])).toContain('parent story-p');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('initializes the saved draft editor after the prompt host appears and replaces a removed host', async () => {
    const {fixture,page,http}=await createPage();
    const internals=page as any;const host=document.createElement('div');const dispose=vi.fn();
    page.draftPrompt='Corrected prompt bytes';
    internals.promptMonaco={nativeElement:host};
    internals.promptEditor={getContainerDomNode:()=>document.createElement('div'),dispose};
    const initialize=vi.spyOn(internals,'initializePromptEditor').mockImplementation(()=>{});
    page.ngAfterViewChecked();
    expect(dispose).toHaveBeenCalledOnce();expect(internals.promptEditor).toBeNull();
    expect(initialize).toHaveBeenCalledOnce();expect(page.draftPrompt).toBe('Corrected prompt bytes');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify();fixture.destroy();TestBed.resetTestingModule();
  });

  it('saves an unchanged first draft once, preserves corrected bytes, and reloads its identity', async () => {
    const {fixture,page,http}=await createPage();
    const raw='TITLE / FORMAT\nMimi 15s\n\nTIMED SHOT PLAN\n0-15s: Corrected action.\n';
    page.contentId='12';page.builderRecordId='builder-recovered';page.builderResult={prompt:raw,productionPlan:{promptTextEdited:true}};
    page.draftPrompt=raw;page.savedPromptBaseline=raw;
    expect((page as any).formatPromptForEditor(raw)).toBe(raw);
    expect(page.promptDirty).toBe(false);
    vi.spyOn(TestBed.inject(Router),'navigateByUrl').mockResolvedValue(true);
    page.savePrompt();page.savePrompt();
    const save=http.expectOne('/api/v1/intelligence/contents/12/prompt-versions');
    expect(save.request.body).toMatchObject({rawText:raw,parentPromptVersionId:null,creativeRoleRecordId:'builder-recovered'});
    save.flush({id:42});
    expect(page.promptVersionId).toBe('42');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    fixture.destroy();
    const reloaded=TestBed.createComponent(CreativeStudioPage);reloaded.detectChanges();
    http.match(r=>r.method==='GET').forEach(r=>r.flush([]));
    expect(reloaded.componentInstance.promptVersionId).toBe('42');
    expect(reloaded.componentInstance.draftPrompt).toBe(raw);
    reloaded.componentInstance.savePrompt();
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify();reloaded.destroy();TestBed.resetTestingModule();
  });

  it('saves a changed prompt as an immutable child version and routes to Production Review', async () => {
    const {fixture,page,http}=await createPage();
    page.contentId='12'; page.promptVersionId='3'; page.builderRecordId='builder-1';
    page.savedPromptBaseline='Original saved prompt'; page.draftPrompt='Operator edited prompt';
    const router=TestBed.inject(Router); vi.spyOn(router,'navigateByUrl').mockResolvedValue(true);
    expect(page.promptDirty).toBe(true);
    page.savePrompt();
    const save=http.expectOne('/api/v1/intelligence/contents/12/prompt-versions');
    expect(save.request.body.rawText).toBe('Operator edited prompt');
    expect(save.request.body.parentPromptVersionId).toBe(3);
    expect(save.request.body.creativeRoleRecordId).toBe('builder-1');
    save.flush({id:4});
    expect(page.promptVersionId).toBe('4');
    expect(page.savedPromptBaseline).toBe('Operator edited prompt');
    expect(page.stage).toBe('PRODUCTION_REVIEW');
    expect(router.navigateByUrl).toHaveBeenCalledWith('/quality/detail?contentId=12&promptVersionId=4&studio=1');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('marks a built prompt incompatible when target settings change', async () => {
    const {fixture,page,http}=await createPage();
    page.duration=15; page.aspectRatio='9:16'; page.targetGenerator='SEEDANCE_2_0_MINI'; page.profile='ABSURD_PHYSICS';
    page.builderResult={productionPlan:{builderContractVersion:'openart-production-prompt-v2',productionConstraints:{duration:15,aspectRatio:'9:16',generator:'SEEDANCE_2_0_MINI',contentProfile:'ABSURD_PHYSICS'}}};
    expect(page.builderInputMismatch).toBe(false);
    page.aspectRatio='16:9';
    expect(page.builderInputMismatch).toBe(true);
    page.aspectRatio='9:16'; page.builderResult.productionPlan.builderContractVersion='legacy';
    expect(page.builderInputMismatch).toBe(true);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('revalidates a legacy saved prompt locally and exposes preliminary review without a paid role call', async () => {
    const {fixture,page,http}=await createPage();
    page.stage='PROMPT'; page.builderRecordId='123e4567-e89b-12d3-a456-426614174000'; page.draftPrompt='Exact immutable saved prompt text';
    page.builderResult={prompt:page.draftPrompt,productionPlan:{builderContractVersion:'legacy',productionConstraints:{duration:15,aspectRatio:'9:16',generator:'SEEDANCE_2_0_MINI',contentProfile:'ABSURD_PHYSICS'}}};
    page.duration=15; page.aspectRatio='9:16'; page.targetGenerator='SEEDANCE_2_0_MINI'; page.profile='ABSURD_PHYSICS';
    expect(page.builderInputMismatch).toBe(true);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Revalidate Saved Draft — No AI Call');
    page.revalidateSavedDraft();
    const request=http.expectOne('/api/v1/intelligence/workflow/records/123e4567-e89b-12d3-a456-426614174000/revalidate-production-spec');
    expect(request.request.method).toBe('POST');
    request.flush({recordId:'migration-1',migrationVersion:'openart-production-prompt-v2-legacy-migration',providerCalls:0,createdAt:'2026-10-11T12:00:00Z',result:{prompt:page.draftPrompt,validationStatus:'NOT_VALIDATED',productionPlan:{builderContractVersion:'openart-production-prompt-v2',productionConstraints:{duration:15,aspectRatio:'9:16',generator:'SEEDANCE_2_0_MINI',contentProfile:'ABSURD_PHYSICS'},characterBindings:[{name:'Mimi',identityStatus:'CATALOG_CONFIRMED',referenceStatus:'MISSING_OR_UNVERIFIED',visualAppearanceStatus:'UNKNOWN_NO_APPROVED_VISUAL_REFERENCE'}],storyPromptFidelity:{status:'NOT_EVALUATED',sourceSentenceCount:null,traceableSentenceCount:null},evidenceLimitations:['Unknown remains unknown']}}});
    expect(page.builderMigration.recordId).toBe('migration-1');
    expect(page.builderResult.prompt).toBe('Exact immutable saved prompt text');
    expect(page.builderInputMismatch).toBe(false);
    expect(page.builderResult.productionPlan.storyPromptFidelity.status).toBe('NOT_EVALUATED');
    expect(page.activeContextCharacter).toBe('Mimi');
    expect(page.activeContextProfile).toBe('ABSURD_PHYSICS');
    expect(page.activeContextDuration).toBe(15);
    expect(page.activeContextAspectRatio).toBe('9:16');
    expect(page.nextAction).toBe('Review locally recovered saved prompt');
    expect(http.match(r=>r.url.includes('/creative-role') && r.method==='POST')).toHaveLength(0);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Review Existing Draft');
    expect(page.builderMigrationRefreshAvailable).toBe(true);
    expect(fixture.nativeElement.textContent).toContain('Refresh Local Evidence — No AI Call');
    expect(fixture.nativeElement.textContent).toContain('Identity: CATALOG CONFIRMED');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('keeps downstream stage tabs locked until their own evidence milestone exists', async () => {
    const {fixture,page,http}=await createPage();
    expect(page.canVisit('ANALYSIS')).toBe(false);
    expect(page.stageAvailabilityReason('ANALYSIS')).toContain('Production Review');
    page.promptVersionId='42';
    expect(page.canVisit('PRODUCTION_REVIEW')).toBe(true);
    expect(page.canVisit('ANALYSIS')).toBe(false);
    fixture.detectChanges();
    const analysis=Array.from(fixture.nativeElement.querySelectorAll('button[aria-label]')).find((button:any)=>button.getAttribute('aria-label').startsWith('Quality Analysis:')) as HTMLButtonElement;
    expect(analysis).toBeTruthy();
    expect(analysis.disabled).toBe(true);
    expect(analysis.title).toContain('Production Review');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('reuses an unchanged prompt version without creating another revision', async () => {
    const {fixture,page,http}=await createPage();
    page.contentId='12'; page.promptVersionId='3'; page.savedPromptBaseline='Same prompt'; page.draftPrompt='Same prompt';
    const router=TestBed.inject(Router); vi.spyOn(router,'navigateByUrl').mockResolvedValue(true);
    page.savePrompt();
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(router.navigateByUrl).toHaveBeenCalledWith('/quality/detail?contentId=12&promptVersionId=3&studio=1');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.match(r=>r.method==='GET' && r.url.endsWith('/story-validation')).forEach(r=>r.flush([])); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
});
