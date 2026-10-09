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
    page.idea='Kiko sınava giriyor'; page.storyConsent=true; page.budget=0.01; page.requestStories();
    const story=http.expectOne('/api/v1/intelligence/workflow/creative-role'); expect(story.request.body.text).toBe('Kiko sınava giriyor'); story.flush({recordId:'story-1',result:{alternatives:['Kiko kalemiyle konuşur.']}});
    await fixture.whenStable(); page.selectStory(page.candidates[0]); page.approveStory();
    const approval=http.expectOne('/api/v1/intelligence/workflow/creative-role/story-1/approve-story'); expect(approval.request.body.approvedText).toContain('kalemiyle'); approval.flush({recordId:'approval-1'});
    await fixture.whenStable(); page.promptConsent=true; page.buildPrompt();
    const build=http.expectOne('/api/v1/intelligence/workflow/creative-role'); expect(build.request.body.role).toBe('BUILD_PROMPT'); expect(build.request.body.context.sourceStoryRecordId).toBe('story-1'); expect(build.request.body.text).toContain('kalemiyle'); build.flush({recordId:'builder-1',result:{prompt:'Kiko enters a classroom and the pencil moves.'}});
    expect(page.builderRecordId).toBe('builder-1'); http.match(r=>r.method==='PUT').forEach(r=>r.flush({})); http.verify(); fixture.destroy(); TestBed.resetTestingModule();
  });
});
