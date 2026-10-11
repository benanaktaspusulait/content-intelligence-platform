import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { CreativeStudioPage } from './creative-studio.page';

describe('Creative Studio after an approved test-data reset', () => {
  const studioKey = 'pompom.creative-studio.v1';
  const characters = ['Kiko', 'Mimi', 'Luca', 'Noah', 'Arda', 'Opa'].map((name, index) => ({ id: String(index + 1), name }));

  beforeEach(async () => {
    localStorage.removeItem(studioKey);
    await TestBed.configureTestingModule({
      imports: [CreativeStudioPage],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
  });

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
    localStorage.removeItem(studioKey);
    TestBed.resetTestingModule();
  });

  async function openCleanPage() {
    const fixture = TestBed.createComponent(CreativeStudioPage);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/v1/characters').flush(characters);
    http.expectOne('/api/v1/videos/prompt-workspaces?relativeDirectory=library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026').flush([]);
    http.expectOne('/api/v1/intelligence/workflow/creative-role/readiness').flush({ enabled: true, liveVerified: false, roles: [] });
    for (const kind of ['CREATIVE_ROLE', 'STORY_APPROVAL', 'CREATIVE_STUDIO_SESSION']) {
      http.expectOne(`/api/v1/intelligence/workflow/records?kind=${kind}`).flush([]);
    }
    http.expectOne('/api/v1/intelligence/workflow/idea-drafts').flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
    return { fixture, page: fixture.componentInstance, http };
  }

  it('shows an empty saved-project list and a fresh Idea without inherited identities', async () => {
    const { fixture, page } = await openCleanPage();
    expect(page.stage).toBe('IDEA');
    expect(page.activeJourney).toBe('NEW');
    expect(page.newStoryOpen).toBe(true);
    expect(page.filteredSavedStories).toEqual([]);
    expect(page.savedApprovals).toEqual([]);
    expect(page.savedStudioSessions).toEqual([]);
    for (const value of [page.sessionId, page.contentId, page.storyRecordId, page.approvalRecordId, page.builderRecordId, page.promptVersionId]) {
      expect(value).toBe('');
    }
    expect(fixture.nativeElement.querySelectorAll('.draft-library-row:not(.draft-library-header)')).toHaveLength(0);
    expect(fixture.nativeElement.querySelector('.new-story-form')).not.toBeNull();
    fixture.destroy();
  });

  it('keeps shared characters available without selecting an old project character', async () => {
    const { fixture, page } = await openCleanPage();
    expect(page.characters.map(character => character.name)).toEqual(characters.map(character => character.name));
    expect(page.mainCharacterId).toBe('');
    expect(page.selectedCharacterName).toBe('');
    fixture.destroy();
  });

  it('locks downstream stages and has no inherited story, prompt, review or builder evidence', async () => {
    const { fixture, page } = await openCleanPage();
    expect(page.candidates).toEqual([]);
    expect(page.selectedStory).toBe('');
    expect(page.draftPrompt).toBe('');
    expect(page.storyReview).toBeNull();
    expect(page.builderResult).toBeNull();
    expect(page.canonicalSavedPrompt).toBeNull();
    expect(page.storyApprovalStatus).toBe('NOT_STARTED');
    expect(page.promptAcceptanceStatus).toBe('NOT_STARTED');
    for (const stage of page.stages.filter(stage => stage.key !== 'IDEA')) {
      expect(page.canVisit(stage.key)).toBe(false);
      page.goTo(stage.key);
      expect(page.stage).toBe('IDEA');
    }
    fixture.destroy();
  });

  it('recreates the page without writes, provider generation, render requests or new browser state', async () => {
    for (let visit = 0; visit < 2; visit++) {
      const { fixture, page, http } = await openCleanPage();
      expect(page.sessionId).toBe('');
      expect(localStorage.getItem(studioKey)).toBeNull();
      http.expectNone(request => request.method !== 'GET');
      http.expectNone(request => request.url.includes('/render-jobs'));
      http.expectNone(request => request.url.endsWith('/creative-role'));
      fixture.destroy();
    }
  });
});
