import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { CreativeStudioPage } from './creative-studio.page';

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
});
