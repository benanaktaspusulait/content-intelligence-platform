import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActualVideoReviewComponent } from './actual-video-review.component';

describe('Actual-only review', () => {
 it('reopens the exact video record through GET without running analysis', async () => {
  await TestBed.configureTestingModule({ imports: [ActualVideoReviewComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  const fixture = TestBed.createComponent(ActualVideoReviewComponent);
  fixture.componentRef.setInput('videoId', 'exact-video'); fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  http.expectOne('/api/v1/intelligence/workflow/videos/exact-video/qa').flush([{ recordId: 'saved', planFidelity: 'NOT_EVALUATED', viewerFacingUsability: 'UNKNOWN' }]);
  expect(fixture.componentInstance.result.recordId).toBe('saved');
  http.expectNone(request => request.method === 'POST'); http.verify();
  fixture.destroy(); TestBed.resetTestingModule();
 });
});
