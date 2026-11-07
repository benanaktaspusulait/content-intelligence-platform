import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AutonomousProductionPage } from './autonomous-production.page';

describe('autonomous production entry point', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AutonomousProductionPage],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
  });
  afterEach(() => { TestBed.inject(HttpTestingController).verify(); TestBed.resetTestingModule(); });

  it('starts one idempotent run through the application API and displays its blockers without dispatching a provider', () => {
    const fixture = TestBed.createComponent(AutonomousProductionPage);
    fixture.detectChanges();
    fixture.nativeElement.querySelector('button').click();
    const request = TestBed.inject(HttpTestingController).expectOne('/api/v1/intelligence/autonomous-production/runs');
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.has('Idempotency-Key')).toBe(true);
    expect(request.request.body).toEqual({});
    request.flush({
      runId: 'run-1', status: 'AWAITING_BUDGET_AUTHORIZATION', selectedCandidateId: null,
      candidateEvaluations: [], characterReference: { status: 'NOT_APPLICABLE' },
      firstFrame: { status: 'NOT_APPLICABLE' }, productionPrompt: { status: 'NOT_CREATED' },
      modelConfiguration: {}, validationEvidence: {},
      blockers: [{ code: 'RUN_LEVEL_SPENDING_AUTHORIZATION_MISSING', detail: 'Set a run limit.' }],
      providerRequests: 0, nextApplicationAction: 'Authorize this run in the application.',
    });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('AWAITING BUDGET AUTHORIZATION');
    expect(fixture.nativeElement.textContent).toContain('RUN_LEVEL_SPENDING_AUTHORIZATION_MISSING');
    expect(fixture.nativeElement.textContent).toContain('Provider requests: 0');
    TestBed.inject(HttpTestingController).expectNone(request => request.url.includes('/render-jobs'));
    fixture.destroy();
  });
});
