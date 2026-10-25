import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ShortFormReportComponent } from './short-form-report.component';

describe('independent short-form report', () => {
  const report = {
    engine: 'SHORT_FORM_ENGINE', status: 'REVISION_REQUIRED', shortFormScore: 56,
    humanReadableReport: 'Five blocks contain one causal development.',
    instantPremiseLegibility: { reason: 'Visible goal and anomaly.' },
    rewatchType: 'OPTIONAL_NOT_ESTABLISHED', duplicateEngineRisk: { status: 'HIGH', limitation: 'Limited corpus.' },
    findings: [{ code: 'HIGH_ACTIVITY_LOW_PROGRESS', severity: 'REVISION_REQUIRED', message: 'Motion is not progress.' }],
    beats: [{ id: 'B1', start: 0, end: 3, quote: 'Kiko tries to sit.', progressTypes: ['UNDERSTANDING'] }],
    evidenceLimitations: ['No video frames inspected.'], sourceSha256: 'source-sha',
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ShortFormReportComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  });
  afterEach(() => { TestBed.inject(HttpTestingController).verify(); TestBed.resetTestingModule(); });

  it('shows no results or requests for an absent historical report', () => {
    const fixture = TestBed.createComponent(ShortFormReportComponent); fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('details')).toBeNull(); fixture.destroy();
  });

  it('projects saved independent scores, limitations and exact source without mutation', () => {
    const fixture = TestBed.createComponent(ShortFormReportComponent);
    const original = JSON.stringify(report);
    fixture.componentRef.setInput('assessment', report); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('HIGH_ACTIVITY_LOW_PROGRESS');
    expect(fixture.nativeElement.textContent).toContain('Kiko tries to sit.');
    expect(fixture.nativeElement.textContent).toContain('No video frames inspected.');
    expect(JSON.stringify(report)).toBe(original); fixture.destroy();
  });

  it('runs only on explicit click and posts only the source text', () => {
    const fixture = TestBed.createComponent(ShortFormReportComponent);
    fixture.componentRef.setInput('sourceText', '0-3s: Kiko tries to sit.'); fixture.detectChanges();
    TestBed.inject(HttpTestingController).expectNone('/api/v1/intelligence/workflow/short-form/evaluate');
    fixture.nativeElement.querySelector('button').click();
    const request = TestBed.inject(HttpTestingController).expectOne('/api/v1/intelligence/workflow/short-form/evaluate');
    expect(request.request.body).toEqual({ text: '0-3s: Kiko tries to sit.' });
    request.flush(report); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('56/100'); fixture.destroy();
  });

  it('clears results when the source changes and cancels stale analysis', () => {
    const fixture = TestBed.createComponent(ShortFormReportComponent);
    fixture.componentRef.setInput('sourceText', 'old'); fixture.detectChanges(); fixture.componentInstance.evaluate();
    const pending = TestBed.inject(HttpTestingController).expectOne('/api/v1/intelligence/workflow/short-form/evaluate');
    fixture.componentRef.setInput('sourceText', 'new'); fixture.detectChanges();
    expect(pending.cancelled).toBe(true); expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });

  it('reports a failed request without creating a successful score', () => {
    const fixture = TestBed.createComponent(ShortFormReportComponent);
    fixture.componentRef.setInput('sourceText', 'source'); fixture.detectChanges(); fixture.componentInstance.evaluate();
    TestBed.inject(HttpTestingController).expectOne('/api/v1/intelligence/workflow/short-form/evaluate')
      .flush('unavailable', { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Short-form assessment failed');
    expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });

  it('does not attach a saved result to subsequently edited source text', () => {
    const fixture = TestBed.createComponent(ShortFormReportComponent);
    fixture.componentRef.setInput('sourceText', 'old'); fixture.componentRef.setInput('assessment', report); fixture.detectChanges();
    expect(fixture.componentInstance.result).toEqual(report);
    fixture.componentRef.setInput('sourceText', 'edited'); fixture.detectChanges();
    expect(fixture.componentInstance.result).toBeNull(); fixture.destroy();
  });
});
