import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { CreativeIntelligenceService, DiscoveryProfile } from './creative-intelligence.service';

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
