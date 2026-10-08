import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AnalysisStatus, CreativeIntelligenceService, DiscoveryProfile, MediaFile, VideoApiRecord } from '../core/creative-intelligence.service';
import { VideoDetailPage } from './video-detail.page';

const mediaFile: MediaFile = {
  name: 'giant-sock-hd.mp4', relativePath: 'library/Giant Sock/giant-sock-hd.mp4',
  sizeBytes: 1200, modifiedAt: '2026-09-30T10:00:00Z', ingested: true,
  videoId: 'video-1', status: 'ANALYSED', variantId: null,
};

const video: VideoApiRecord = {
  id: 'video-1', originalFilename: mediaFile.name, relativePath: mediaFile.relativePath,
  durationMs: 15104, width: 1080, height: 1920, fps: 30, aspectRatio: 0.5625,
  codec: 'h264', audioPresent: true, status: 'ANALYSED', ingestedAt: '2026-09-30T10:00:00Z',
};

function serviceWith(discovery: DiscoveryProfile) {
  return {
    mediaContentUrl: () => '/media',
    getMediaFiles: () => of([mediaFile]),
    getVideo: () => of(video),
    getReachFurther: () => of(null),
    getTrajectory: () => of({ videoId: 'video-1', platform: 'facebook', label: '', cleanOrganic: true, interventions: [], points: [] }),
    getPlatformGrowth: () => of(null),
    getDiscoveryProfile: () => of(discovery),
    listVariants: () => of([]),
    triggerAnalysis: () => of(notStartedAnalysis),
    getAnalysisStatus: () => of(notStartedAnalysis),
    getMetadataFile: () => of(null),
    getEditedHandoffs: () => of([]),
    getVideoCreativeContext: () => of({
      videoId: 'video-1',
      characters: [{ id: 'character-mimi', name: 'Mimi', participation: 'PRIMARY', role: 'UNKNOWN', screenTimeRatio: null, actionShare: null, speakingShare: null, source: 'PROMPT_FILE_INFERRED', confidence: 'HIGH', promptSourcePath: 'prompt.txt', resolverVersion: 'v1', evidenceReference: 'matched=Mimi', manuallyConfirmed: false }],
      prompt: null,
      evidenceStatus: 'CHARACTER_DATA_ONLY',
    }),
  };
}

const notStartedAnalysis: AnalysisStatus = {
  videoId: 'video-1', hasCompletedAnalysis: false, jobId: null, jobState: 'NOT_STARTED',
  attempts: null, maxAttempts: null, errorMessage: null, analysisId: null,
  classification: null, actionDnaScore: null, confidence: null, reason: null,
  storyboardPath: null, analysisVersion: null,
};

const baseDiscovery: DiscoveryProfile = {
  videoId: 'video-1', platform: 'facebook', cutoff: '2026-09-30T12:00:00Z',
  audienceObservedAt: '2026-09-30T11:00:00Z', countryObservedAt: '2026-09-30T11:00:00Z',
  followerShare: 1, nonFollowerShare: 99, usAudienceShare: 19.8,
  estimatedUsAudience: null, recommendationShare: null, followsPerThousandViews: 0,
  newAudienceQualityScore: 99, algorithmVersion: 'new-audience-quality-v1',
  dataQualityStatus: 'DERIVED_FROM_REPORTED_SHARES', components: {},
};

describe('VideoDetailPage audience discovery', () => {
  const route = {
    paramMap: of(convertToParamMap({})),
    queryParamMap: of(convertToParamMap({ folder: 'library/Giant Sock', file: mediaFile.relativePath })),
  };

  async function render(discovery: DiscoveryProfile) {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWith(discovery) },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('separates participation, narrative role, association provenance, and missing metrics', async () => {
    const fixture = await render(baseDiscovery);
    (Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[]).find(b => b.textContent?.trim() === 'Creative')!.click();
    fixture.detectChanges();
    const panel = fixture.nativeElement.querySelector('.creative-context-panel') as HTMLElement;

    expect(panel.textContent).toContain('Participation: Primary');
    expect(panel.textContent).toContain('Role: Not classified');
    expect(panel.textContent).toContain('Association: Prompt file inferred');
    expect(panel.textContent).toContain('Confidence: High');
    expect(panel.textContent).toContain('Participation metrics not measured');
    expect(panel.textContent).not.toContain('Primary · Unknown');
  });
  it('renders only verified API discovery values and provenance', async () => {
    const fixture = await render(baseDiscovery);
    (Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[]).find(b => b.textContent?.trim() === 'Performance')!.click();
    fixture.detectChanges();
    const panel = fixture.nativeElement.querySelector('.discovery-profile') as HTMLElement;

    expect(panel.textContent).toContain('99.0%');
    expect(panel.textContent).toContain('19.8%');
    expect(panel.textContent).toContain('99.00');
    expect(panel.textContent).toContain('new-audience-quality-v1');
    expect(panel.textContent).toContain('Derived only from imported, platform-reported audience shares.');
  });

  it('shows explicit missing-data language instead of fallback metrics', async () => {
    const fixture = await render({
      ...baseDiscovery,
      audienceObservedAt: null, countryObservedAt: null, nonFollowerShare: null,
      usAudienceShare: null, followsPerThousandViews: null, newAudienceQualityScore: null,
      dataQualityStatus: 'UNAVAILABLE',
    });
    (Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[]).find(b => b.textContent?.trim() === 'Performance')!.click();
    fixture.detectChanges();
    const panel = fixture.nativeElement.querySelector('.discovery-profile') as HTMLElement;

    expect(panel.textContent).toContain('NO COMPLETE DATA');
    expect(panel.textContent?.match(/No imported value/g)?.length).toBe(4);
    expect(panel.textContent).toContain('Missing values are not estimated.');
  });

  it('opens the exact requested edited file even when its filename has no HD suffix', async () => {
    const edited = {...mediaFile, name:'edited.mp4', relativePath:'library/Giant Sock/edited.mp4'};
    await TestBed.configureTestingModule({imports:[VideoDetailPage], providers:[provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
      {provide:ActivatedRoute,useValue:{paramMap:of(convertToParamMap({})), queryParamMap:of(convertToParamMap({folder:'library/Giant Sock',file:edited.relativePath}))}},
      {provide:CreativeIntelligenceService,useValue:{...serviceWith(baseDiscovery),getMediaFiles:()=>of([edited]),getVideo:()=>of({...video,relativePath:edited.relativePath,originalFilename:edited.name}),getEditedHandoffs:()=>of([{recordId:'saved-edit',videoId:'parent-video',artifactVideoId:video.id,variantId:'edited-variant',durationMs:12083,artifactHash:'verified-hash',reason:'Saved manual edit provenance'}])}}]}).compileComponents();
    const fixture=TestBed.createComponent(VideoDetailPage); fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.selected-file-bar').textContent).toContain('edited.mp4');
    expect(fixture.nativeElement.querySelector('.state-panel--error')).toBeNull();
    (Array.from(fixture.nativeElement.querySelectorAll('button')) as HTMLButtonElement[]).find(b=>b.textContent?.trim()==='Creative')!.click();fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Saved manual edit provenance');
    expect(fixture.nativeElement.querySelector('a[href="/videos/parent-video"]')).not.toBeNull();
  });

  it('groups real technical metadata into video, file, and evidence sections', async () => {
    const fixture = await render(baseDiscovery);
    const groups = Array.from(fixture.nativeElement.querySelectorAll('.technical-group')) as HTMLElement[];

    expect(groups).toHaveLength(3);
    expect(groups[0].querySelector('h3')?.textContent).toBe('Video');
    expect(groups[0].textContent).toContain('15.1s');
    expect(groups[0].textContent).toContain('1080 × 1920');
    expect(groups[1].querySelector('h3')?.textContent).toBe('File');
    expect(groups[1].textContent).toContain('MP4');
    expect(groups[2].querySelector('h3')?.textContent).toBe('Evidence');
    expect(groups[2].textContent).toContain('ANALYSED');
    expect(groups[2].textContent).toContain('Audio / codec');
  });
});

describe('VideoDetailPage variant rail', () => {
  // Deviation from brief: the brief's fixture reused `mediaFile.name` ('giant-sock-hd.mp4') and
  // asserted the rendered label is not 'HD', on the premise that `mediaVariant()` guesses 'HD' for
  // that filename. It does not: `mediaVariant` matches the `_hd` suffix with an underscore, and
  // 'giant-sock-hd' has a hyphen before 'hd', so the filename-guess fallback actually resolves to
  // 'Original' under both old and new code. That makes the `not.toContain('HD')` assertion vacuous
  // (true before and after the fix) and doesn't exercise the regression this test is meant to catch.
  // Renamed to 'giant_sock_hd.mp4' so `mediaVariant()` genuinely guesses 'HD', which is what the old
  // code would render here absent a matched variant, proving the real-variant-type label overrides it.
  const taggedFile: MediaFile = {
    ...mediaFile, name: 'giant_sock_hd.mp4', relativePath: 'library/Giant Sock/giant_sock_hd.mp4', variantId: 'variant-1',
  };

  const route = {
    paramMap: of(convertToParamMap({})),
    queryParamMap: of(convertToParamMap({ folder: 'library/Giant Sock', file: taggedFile.relativePath })),
  };

  function serviceWithVariants() {
    return {
      mediaContentUrl: () => '/media',
      getMediaFiles: () => of([taggedFile]),
      getVideo: () => of(video),
      getReachFurther: () => of(null),
      getTrajectory: () => of({ videoId: 'video-1', platform: 'facebook', label: '', cleanOrganic: true, interventions: [], points: [] }),
      getPlatformGrowth: () => of(null),
      getDiscoveryProfile: () => of(baseDiscovery),
      listVariants: () => of([{
        id: 'variant-1', videoId: 'video-1', parentVariantId: null,
        variantType: 'HOOK_COLD_OPEN', generatedPath: taggedFile.relativePath,
        editOperations: [], createdAt: '2026-10-04T00:00:00Z',
      }]),
      triggerAnalysis: () => of(notStartedAnalysis),
      getAnalysisStatus: () => of(notStartedAnalysis),
      getMetadataFile: () => of(null),
      getEditedHandoffs: () => of([]),
    getVideoCreativeContext: () => of({ videoId: 'video-1', characters: [{ id: 'character-mimi', name: 'Mimi', participation: 'PRIMARY', role: 'UNKNOWN', screenTimeRatio: null, actionShare: null, speakingShare: null, source: 'PROMPT_FILE_INFERRED', confidence: 'HIGH', promptSourcePath: 'prompt.txt', resolverVersion: 'v1', evidenceReference: 'matched=Mimi', manuallyConfirmed: false }], prompt: null, evidenceStatus: 'CHARACTER_DATA_ONLY' }),
    };
  }

  afterEach(() => TestBed.resetTestingModule());

  it('labels a variant-linked file with its real persisted variant type, not a filename guess', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWithVariants() },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();

    const rail = fixture.nativeElement.querySelector('.variant-list');
    expect(rail.textContent).toContain('Hook / Cold Open');
    expect(rail.textContent).not.toContain('HD');
  });
});

describe('VideoDetailPage creative analysis panel', () => {
  const route = {
    paramMap: of(convertToParamMap({})),
    queryParamMap: of(convertToParamMap({ folder: 'library/Giant Sock', file: mediaFile.relativePath })),
  };

  function serviceWithAnalysis(status: AnalysisStatus) {
    return {
      mediaContentUrl: () => '/media',
      getMediaFiles: () => of([mediaFile]),
      getVideo: () => of(video),
      getReachFurther: () => of(null),
      getTrajectory: () => of({ videoId: 'video-1', platform: 'facebook', label: '', cleanOrganic: true, interventions: [], points: [] }),
      getPlatformGrowth: () => of(null),
      getDiscoveryProfile: () => of(baseDiscovery),
      listVariants: () => of([]),
      triggerAnalysis: () => of(status),
      getAnalysisStatus: () => of(status),
      getMetadataFile: () => of(null),
      getEditedHandoffs: () => of([]),
    getVideoCreativeContext: () => of({ videoId: 'video-1', characters: [{ id: 'character-mimi', name: 'Mimi', participation: 'PRIMARY', role: 'UNKNOWN', screenTimeRatio: null, actionShare: null, speakingShare: null, source: 'PROMPT_FILE_INFERRED', confidence: 'HIGH', promptSourcePath: 'prompt.txt', resolverVersion: 'v1', evidenceReference: 'matched=Mimi', manuallyConfirmed: false }], prompt: null, evidenceStatus: 'CHARACTER_DATA_ONLY' }),
    };
  }

  afterEach(() => TestBed.resetTestingModule());

  it('renders completed analysis results instead of a trigger button', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWithAnalysis({
          videoId: 'video-1', hasCompletedAnalysis: true, jobId: null, jobState: 'COMPLETED',
          attempts: null, maxAttempts: null, errorMessage: null, analysisId: 'analysis-1',
          classification: 'GOOD', actionDnaScore: 0.82, confidence: 0.9, reason: 'Clear hook',
          storyboardPath: null, analysisVersion: 'creative-v3',
        }) },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector('.creative-analysis-panel');
    expect(panel.textContent).toContain('GOOD');
    expect(panel.textContent).toContain('Clear hook');
    expect(panel.querySelector('button')?.textContent).toContain('Reanalyze');
  });

  it('shows a trigger button when no analysis exists yet', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWithAnalysis({
          videoId: 'video-1', hasCompletedAnalysis: false, jobId: null, jobState: 'NOT_STARTED',
          attempts: null, maxAttempts: null, errorMessage: null, analysisId: null,
          classification: null, actionDnaScore: null, confidence: null, reason: null,
          storyboardPath: null, analysisVersion: null,
        }) },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();

    const panel = fixture.nativeElement.querySelector('.creative-analysis-panel');
    expect(panel.querySelector('button')?.textContent).toContain('Run analysis');
  });

  it('keeps polling and preserves the last-known analysis status when a tick fails', async () => {
    vi.useFakeTimers();
    try {
      const runningStatus: AnalysisStatus = {
        videoId: 'video-1', hasCompletedAnalysis: false, jobId: 'job-1', jobState: 'RUNNING',
        attempts: 1, maxAttempts: 5, errorMessage: null, analysisId: null,
        classification: null, actionDnaScore: null, confidence: null, reason: null,
        storyboardPath: null, analysisVersion: null,
      };

      let callCount = 0;
      const getAnalysisStatus = vi.fn(() => {
        callCount++;
        // First poll tick (the immediate startWith(0) tick) succeeds and seeds a known-good status.
        if (callCount === 1) return of(runningStatus);
        // Second poll tick (after 5s) fails transiently.
        if (callCount === 2) return throwError(() => new Error('network unreachable'));
        // Third poll tick (after another 5s) succeeds again, proving polling kept going.
        return of(runningStatus);
      });

      await TestBed.configureTestingModule({
        imports: [VideoDetailPage],
        providers: [
          provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
          { provide: ActivatedRoute, useValue: route },
          { provide: CreativeIntelligenceService, useValue: {
            ...serviceWithAnalysis(runningStatus),
            getAnalysisStatus,
          } },
        ],
      }).compileComponents();
      const fixture = TestBed.createComponent(VideoDetailPage);
      fixture.detectChanges();
      await Promise.resolve();

      // Initial tick (startWith(0)) resolved synchronously via `of`.
      expect(getAnalysisStatus).toHaveBeenCalledTimes(1);
      expect(fixture.componentInstance['analysisStatus']()).toEqual(runningStatus);

      // Advance 5s: this tick errors. No exception should propagate, and the subscription
      // must still be alive for the next tick (switchMap's inner observable erroring must
      // not tear down the outer `interval` subscription).
      expect(() => vi.advanceTimersByTime(5000)).not.toThrow();
      await Promise.resolve();
      expect(getAnalysisStatus).toHaveBeenCalledTimes(2);
      // Last-known-good status must be preserved, not wiped to null.
      expect(fixture.componentInstance['analysisStatus']()).toEqual(runningStatus);

      // Advance another 5s: polling must still be attempting ticks after the failure.
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
      expect(getAnalysisStatus).toHaveBeenCalledTimes(3);
      expect(fixture.componentInstance['analysisStatus']()).toEqual(runningStatus);
    } finally {
      vi.useRealTimers();
    }
  });
});
