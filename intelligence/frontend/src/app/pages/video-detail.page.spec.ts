import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { CreativeIntelligenceService, DiscoveryProfile, MediaFile, VideoApiRecord } from '../core/creative-intelligence.service';
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
  };
}

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
        provideRouter([]),
        { provide: ActivatedRoute, useValue: route },
        { provide: CreativeIntelligenceService, useValue: serviceWith(discovery) },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(VideoDetailPage);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => TestBed.resetTestingModule());

  it('renders only verified API discovery values and provenance', async () => {
    const fixture = await render(baseDiscovery);
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
    const panel = fixture.nativeElement.querySelector('.discovery-profile') as HTMLElement;

    expect(panel.textContent).toContain('NO COMPLETE DATA');
    expect(panel.textContent?.match(/No imported value/g)?.length).toBe(4);
    expect(panel.textContent).toContain('Missing values are not estimated.');
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
    };
  }

  afterEach(() => TestBed.resetTestingModule());

  it('labels a variant-linked file with its real persisted variant type, not a filename guess', async () => {
    await TestBed.configureTestingModule({
      imports: [VideoDetailPage],
      providers: [
        provideRouter([]),
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
