import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { CreateVariantRequest, CreativeIntelligenceService, DiscoveryProfile, VideoVariant } from './creative-intelligence.service';

describe('CreativeIntelligenceService discovery profile', () => {
  let service: CreativeIntelligenceService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CreativeIntelligenceService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('requests the selected platform discovery profile', () => {
    const response: DiscoveryProfile = {
      videoId: 'video-1', platform: 'instagram', cutoff: '2026-09-30T12:00:00Z',
      audienceObservedAt: null, countryObservedAt: null, followerShare: null,
      nonFollowerShare: null, usAudienceShare: null, estimatedUsAudience: null,
      recommendationShare: null, followsPerThousandViews: null,
      newAudienceQualityScore: null, algorithmVersion: 'new-audience-quality-v1',
      dataQualityStatus: 'UNAVAILABLE', components: {},
    };

    service.getDiscoveryProfile('video-1', 'instagram').subscribe(profile => expect(profile).toEqual(response));

    const request = http.expectOne(request => request.url === '/api/v1/performance/video/video-1/discovery-profile');
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('platform')).toBe('instagram');
    request.flush(response);
  });
});

describe('CreativeIntelligenceService variants', () => {
  let service: CreativeIntelligenceService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CreativeIntelligenceService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists variants for a video', () => {
    const response: VideoVariant[] = [{
      id: 'variant-1', videoId: 'video-1', parentVariantId: null,
      variantType: 'HOOK_COLD_OPEN', generatedPath: 'library/x/hook.mp4',
      editOperations: [], createdAt: '2026-10-04T00:00:00Z',
    }];

    service.listVariants('video-1').subscribe(variants => expect(variants).toEqual(response));

    const request = http.expectOne('/api/v1/videos/video-1/variants');
    expect(request.request.method).toBe('GET');
    request.flush(response);
  });

  it('creates a variant for a video', () => {
    const response: VideoVariant = {
      id: 'variant-2', videoId: 'video-1', parentVariantId: 'variant-1',
      variantType: 'TRIMMED', generatedPath: 'library/x/trimmed.mp4',
      editOperations: [{ op: 'trim', startMs: 0, endMs: 5000 }], createdAt: '2026-10-04T00:00:00Z',
    };

    service.createVariant('video-1', {
      parentVariantId: 'variant-1', variantType: 'TRIMMED',
      generatedPath: 'library/x/trimmed.mp4', editOperations: [{ op: 'trim', startMs: 0, endMs: 5000 }],
    }).subscribe(variant => expect(variant).toEqual(response));

    const request = http.expectOne('/api/v1/videos/video-1/variants');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      parentVariantId: 'variant-1', variantType: 'TRIMMED',
      generatedPath: 'library/x/trimmed.mp4', editOperations: [{ op: 'trim', startMs: 0, endMs: 5000 }],
    });
    request.flush(response);
  });
});
