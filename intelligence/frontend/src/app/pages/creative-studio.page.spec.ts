import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { CreativeStudioPage } from './creative-studio.page';

function fingerprint(value:string){let hash=0x811c9dc5;for(let i=0;i<value.length;i++)hash=Math.imul(hash^value.charCodeAt(i),0x01000193);return (hash>>>0).toString(16).padStart(8,'0');}

describe('creative studio idea-first workflow', () => {
  it('accepts a short idea, persists story approval, and sends the approved story to BUILD_PROMPT', async () => {
    localStorage.removeItem('pompom.creative-studio.v1');
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    const fixture=TestBed.createComponent(CreativeStudioPage); const page=fixture.componentInstance; const http=TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({enabled:true,storyModel:'fixture',promptModel:'fixture'});
    http.expectOne('/api/v1/characters').flush([]);
    http.expectOne('/api/v1/videos/prompt-workspaces?relativeDirectory=library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_STUDIO_SESSION').flush([]);
    page.idea='Kiko sınava giriyor'; page.storyConsent=true; page.budget=0.01; page.requestStories();
    const story=http.expectOne('/api/v1/intelligence/workflow/creative-role'); expect(story.request.body.text).toBe('Kiko sınava giriyor'); story.flush({recordId:'story-1',result:{alternatives:['Kiko kalemiyle konuşur.']}});
    await fixture.whenStable(); page.selectStory(page.candidates[0]); page.approveStory();
    const approval=http.expectOne('/api/v1/intelligence/workflow/creative-role/story-1/approve-story'); expect(approval.request.body.approvedText).toContain('kalemiyle'); approval.flush({recordId:'approval-1'});
    await fixture.whenStable(); page.promptConsent=true; page.buildPrompt();
    const build=http.expectOne('/api/v1/intelligence/workflow/creative-role'); expect(build.request.body.role).toBe('BUILD_PROMPT'); expect(build.request.body.context.sourceStoryRecordId).toBe('story-1'); expect(build.request.body.text).toContain('kalemiyle'); build.flush({recordId:'builder-1',result:{prompt:'Kiko enters a classroom and the pencil moves.'}});
    expect(page.builderRecordId).toBe('builder-1'); http.match(r=>r.method==='PUT').forEach(r=>r.flush({})); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.expectOne('/api/v1/videos/prompt-workspaces?relativeDirectory=library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([{recordId:'saved-1',role:'STORY',sourceRequest:{text:'Kiko finds a door'},alternatives:['Kiko opens the door and finds a tiny stage.']}]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').flush([]);
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.expectOne('/api/v1/videos/prompt-workspaces?relativeDirectory=library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=CREATIVE_ROLE').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/records?kind=STORY_APPROVAL').flush([]);
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('persists input type and generation strategy independently and removes the empty advanced section', async () => {
    const {fixture,page,http}=await createPage();
    page.inputMode='DETAILED_STORY'; page.storyMode='IMPROVE_EXISTING_STORY'; page.onStoryModeChange(); page.persist();
    const saved=JSON.parse(localStorage.getItem('pompom.creative-studio.v1')!);
    expect(saved.inputMode).toBe('DETAILED_STORY');
    expect(saved.storyMode).toBe('IMPROVE_EXISTING_STORY');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Advanced Settings');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
  it('does not mark a saved story approved when the stored candidate identity does not match', async () => {
    const {fixture,page,http}=await createPage();
    page.savedStories=[{recordId:'saved-identity',idea:'Saved source',result:{alternatives:[{candidateId:'candidate-1',text:'One'},{candidateId:'candidate-2',text:'Two'}]}}];
    page.savedApprovals=[{recordId:'approval-wrong',storyRecordId:'saved-identity',candidateId:'candidate-99',revisionId:'candidate-99-revision-deadbeef'}];
    page.useSavedStory(page.savedStories[0]);
    expect(page.approvalRecordId).toBe('');
    expect(page.storyApprovalStatus).toBe('REVIEW_REQUIRED');
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });

  it('opens only the selected saved prompt and makes no provider call', async () => {
    const {fixture,page,http}=await createPage();
    const text='Mimi follows a note to a tiny stage.';
    const hash=fingerprint(text);
    const story:any={recordId:'story-a',title:'Mimi Project A',lifecycleStatus:'APPROVED',result:{alternatives:[{candidateId:'candidate-1',text}]}};
    page.savedStories=[story];
    page.savedApprovals=[{recordId:'approval-a',storyRecordId:'story-a',candidateId:'candidate-1',revisionId:`candidate-1-revision-${hash}`,contentFingerprint:hash,approvedText:text}];
    (page as any).savedBuildRecords=[
      {recordId:'build-other',role:'BUILD_PROMPT',sourceRequest:{context:{sourceStoryRecordId:'story-b',storyRevisionId:`candidate-1-revision-${hash}`}},result:{prompt:'Wrong project prompt'}},
      {recordId:'build-a',role:'BUILD_PROMPT',sourceRequest:{context:{sourceStoryRecordId:'story-a',storyRevisionId:`candidate-1-revision-${hash}`}},result:{prompt:'Exact saved prompt'}}
    ];
    page.useSavedStory(story);
    expect(page.canonicalSavedPrompt?.recordId).toBe('build-a');
    page.openCanonicalSavedPrompt();
    expect(page.stage).toBe('PROMPT');
    expect(page.draftPrompt).toContain('Exact saved prompt');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
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
    http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
});
