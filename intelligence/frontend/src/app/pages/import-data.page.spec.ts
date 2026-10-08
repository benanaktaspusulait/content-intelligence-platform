import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { ImportDataPage } from './import-data.page';

describe('Import exact variant workflow', () => {
 it('loads choices but sends no match until variant and evidence are explicitly confirmed', async () => {
  await TestBed.configureTestingModule({ imports: [ImportDataPage], providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: { get: () => null } } } }] }).compileComponents();
  const fixture = TestBed.createComponent(ImportDataPage); const component = fixture.componentInstance as any;
  const http = TestBed.inject(HttpTestingController);
  http.expectOne(r => r.url === '/api/v1/videos').flush({ last: true, content: [{ id: 'video', originalFilename: 'clip.mp4' }] });
  component.batchId.set('batch'); component.rowCount.set(1); component.unresolvedRows.set(1);
  const row = { id: 'row', sourceRowNumber: 2, rawData: { filename: 'unmatched.mp4' }, matchedVideoId: null, matchStatus: 'UNRESOLVED', matchConfidence: null };
  component.rows.set([row]); fixture.detectChanges();
  expect(fixture.nativeElement.textContent).toContain('clip.mp4');
  component.selectVideo(row, { target: { value: 'video' } });
  http.expectOne('/api/v1/videos/video/variants').flush([{ id: 'variant', videoId: 'video', variantType: 'TRIMMED' }]);
  http.expectNone(r => r.method === 'POST');
  component.selectVariant(row, { target: { value: 'variant' } }); component.setReason(row, { target: { value: 'Exact edited publication checked' } });
  component.resolveRow(row);
  const match = http.expectOne('/api/v1/imports/batch/rows/row/match');
  expect(match.request.body).toEqual({ videoId: 'video', variantId: 'variant', reason: 'Exact edited publication checked' });
  match.flush({ matchedRows: 1, unresolvedRows: 0 });
  http.expectOne('/api/v1/imports/batch/rows').flush([{ ...row, matchedVideoId: 'video', matchedVariantId: 'variant', matchReason: 'Exact edited publication checked', matchStatus: 'MANUAL' }]);
  fixture.detectChanges();
  expect(fixture.nativeElement.textContent).toContain('Exact edited publication checked');
  http.verify(); fixture.destroy(); TestBed.resetTestingModule();
 });
});
