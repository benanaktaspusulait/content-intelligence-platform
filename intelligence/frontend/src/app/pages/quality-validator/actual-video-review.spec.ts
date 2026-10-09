import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActualVideoReviewComponent } from './actual-video-review.component';

describe('Actual-only review', () => {
 it('uses measured duration precisely without attesting inspection or submitting on refresh', async () => {
  await TestBed.configureTestingModule({imports:[ActualVideoReviewComponent],providers:[provideHttpClient(),provideHttpClientTesting()]}).compileComponents();
  const fixture=TestBed.createComponent(ActualVideoReviewComponent);const http=TestBed.inject(HttpTestingController);
  fixture.componentRef.setInput('videoId','exact');fixture.componentRef.setInput('durationSeconds',12.083);fixture.detectChanges();
  http.expectOne('/api/v1/intelligence/workflow/videos/exact/qa').flush([]);await fixture.whenStable();
  expect(fixture.componentInstance.end).toBe(12.083);expect(fixture.componentInstance.confirmed).toBe(false);
  expect(fixture.nativeElement.textContent).toContain('12.083 seconds');http.expectNone(r=>r.method==='POST');http.verify();fixture.destroy();TestBed.resetTestingModule();
 });

 it('reopens the exact video record through GET without running analysis', async () => {
  await TestBed.configureTestingModule({ imports: [ActualVideoReviewComponent], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  const fixture = TestBed.createComponent(ActualVideoReviewComponent);
  fixture.componentRef.setInput('videoId', 'exact-video'); fixture.detectChanges();
  const http = TestBed.inject(HttpTestingController);
  http.expectOne('/api/v1/intelligence/workflow/videos/exact-video/qa').flush([{ recordId: 'saved', planFidelity: 'NOT_EVALUATED', viewerFacingUsability: 'UNKNOWN' }]);
  expect(fixture.componentInstance.result.recordId).toBe('saved');
  await fixture.whenStable();
  expect(fixture.nativeElement.textContent).toContain('Record saved');
  expect(fixture.nativeElement.textContent).toContain('Plan fidelity: NOT_EVALUATED');
  http.expectNone(request => request.method === 'POST'); http.verify();
  fixture.destroy(); TestBed.resetTestingModule();
 });
 it('clears clip-specific human evidence and ignores delayed records from the previous video', async () => {
  await TestBed.configureTestingModule({imports:[ActualVideoReviewComponent],providers:[provideHttpClient(),provideHttpClientTesting()]}).compileComponents();
  const fixture=TestBed.createComponent(ActualVideoReviewComponent); const http=TestBed.inject(HttpTestingController);
  fixture.componentRef.setInput('videoId','old');fixture.detectChanges();const old=http.expectOne('/api/v1/intelligence/workflow/videos/old/qa');
  fixture.componentInstance.confirmed=true;fixture.componentInstance.end=12;fixture.componentInstance.descriptions={identity:'Old clip observation'};
  fixture.componentRef.setInput('videoId','new');fixture.detectChanges();
  old.flush([{recordId:'old-record'}]);http.expectOne('/api/v1/intelligence/workflow/videos/new/qa').flush([{recordId:'new-record',planFidelity:'NOT_EVALUATED',viewerFacingUsability:'UNKNOWN'}]);
  await fixture.whenStable();expect(fixture.componentInstance.confirmed).toBe(false);expect(fixture.componentInstance.end).toBeNull();expect(fixture.componentInstance.descriptions).toEqual({});
  expect(fixture.nativeElement.textContent).toContain('new-record');expect(fixture.nativeElement.textContent).not.toContain('old-record');http.verify();fixture.destroy();TestBed.resetTestingModule();
 });

});
