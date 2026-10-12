import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { beforeEach, afterEach, describe, expect, it } from 'vitest';
import { CreativeStudioPage } from './creative-studio.page';

describe('Step 3 rejected provider outcome safety',()=>{
  let http:HttpTestingController;
  beforeEach(async()=>{
    localStorage.clear();
    await TestBed.configureTestingModule({imports:[CreativeStudioPage],providers:[provideHttpClient(),provideHttpClientTesting(),provideRouter([])]}).compileComponents();
    http=TestBed.inject(HttpTestingController);
  });
  afterEach(()=>{http.match(r=>r.method==='PUT').forEach(r=>r.flush({}));http.verify();localStorage.clear();TestBed.resetTestingModule();});
  function open(){
    const fixture=TestBed.createComponent(CreativeStudioPage);fixture.detectChanges();
    http.match(r=>r.method==='GET').forEach(r=>r.flush(r.request.url.endsWith('readiness')?{enabled:true,roles:[{role:'BUILD_PROMPT',configured:true,model:'fixture'}]}:[]));
    const page=fixture.componentInstance;page.stage='PROMPT';page.storyRecordId='story';page.approvalRecordId='approval';
    page.selectedCandidateIdValue='candidate-2';page.selectedStory='Approved story';page.promptConsent=true;page.promptBudget=.15;
    return {fixture,page};
  }
  it('sends one request for a double submission and resets consent before dispatch',()=>{
    const {page}=open();page.buildPrompt();page.buildPrompt();
    expect(page.promptConsent).toBe(false);
    const request=http.expectOne(r=>r.method==='POST');
    expect(request.request.body.context.approvalRecordId).toBe('approval');
    request.flush({recordId:'saved',result:{prompt:'Draft'},calls:1});
    expect(page.builderRecordId).toBe('saved');expect(page.approvalRecordId).toBe('approval');
  });
  it('shows precise rejection without accepting the raw response as a usable prompt',()=>{
    const {fixture,page}=open();page.buildPrompt();
    http.expectOne(r=>r.method==='POST').flush({recordId:'rejected',attemptState:'PROVIDER_RESULT_REJECTED',validationStatus:'REJECTED',calls:1,
      rejectedProviderResponse:'{"prompt":"Rejected prompt"}',attemptDiagnostics:{error:'Beat 2: required non-empty strings: staging',calls:1,persisted:true,retryAutomatically:false}});
    fixture.detectChanges();
    expect(page.builderRecordId).toBe('');expect(page.draftPrompt).toBe('');expect(page.stage).toBe('PROMPT');
    expect(page.buildAttemptState).toBe('PROVIDER_RESULT_REJECTED');
    expect(page.error).toContain('Beat 2');expect(page.error).toContain('saved');
    expect(page.promptConsent).toBe(false);expect(page.busy).toBe(false);
    expect(page.approvalRecordId).toBe('approval');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(fixture.nativeElement.textContent).toContain('Beat 2');
  });
  it('keeps an unknown completion blocked without claiming a zero provider count',()=>{
    const {fixture,page}=open();page.buildPrompt();
    http.expectOne(r=>r.method==='POST').flush({recordId:'unknown',attemptState:'PROVIDER_OUTCOME_UNKNOWN',validationStatus:'UNKNOWN',
      attemptDiagnostics:{exceptionType:'APITimeoutError',providerOutcome:'UNKNOWN',error:'OpenAI completion is unknown.',persisted:true,retryAutomatically:false}});
    fixture.detectChanges();
    expect(page.buildAttemptState).toBe('PROVIDER_OUTCOME_UNKNOWN');
    expect(page.draftPrompt).toBe('');expect(page.builderRecordId).toBe('');
    expect(page.promptConsent).toBe(false);expect(page.error).toContain('will not call the provider again');
    expect(page.buildAttemptDiagnostics?.callsThisAction).toBe('UNKNOWN');
    expect(fixture.nativeElement.textContent).toContain('Historical provider calls: UNKNOWN');
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
  });
  it('does not automatically retry an ambiguous HTTP error',()=>{
    const {page}=open();page.buildPrompt();
    http.expectOne(r=>r.method==='POST').flush({detail:'Provider outcome unknown. Do not retry automatically.'},{status:409,statusText:'Conflict'});
    expect(page.promptConsent).toBe(false);expect(page.busy).toBe(false);
    expect(http.match(r=>r.method==='POST')).toHaveLength(0);
    expect(page.approvalRecordId).toBe('approval');expect(page.draftPrompt).toBe('');
  });
});
