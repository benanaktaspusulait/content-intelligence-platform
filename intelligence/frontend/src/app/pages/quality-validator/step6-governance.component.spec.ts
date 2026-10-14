import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Step6GovernanceComponent } from './step6-governance.component';

describe('authoritative Step 6 governance', () => {
  async function setup() {
    await TestBed.configureTestingModule({imports:[Step6GovernanceComponent], providers:[provideHttpClient(),provideHttpClientTesting()]}).compileComponents();
    const f=TestBed.createComponent(Step6GovernanceComponent);
    f.componentRef.setInput('analysisId','saved-run'); f.componentRef.setInput('preparationLink','/render-preparation?analysisId=saved-run'); f.detectChanges();
    return {f,c:f.componentInstance,http:TestBed.inject(HttpTestingController)};
  }
  const policy=(allowed:boolean)=>({policyVersion:'STEP6_RESOLUTION_V2',analysisId:'saved-run',findings:[{ruleId:'ATTEMPT_001',outcome:'FAIL',resolutionType:'POLICY_EXCEPTION_REQUIRED',blocksText:false}],allowedActions:{TEXT_ACCEPTED_RENDER_BLOCKED:{allowed,reasons:allowed?[]:['AUTHENTICATED_PRODUCTION_OPERATOR_REQUIRED']},ATTEMPT_COUNT_EXCEPTION_V1:{allowed:false,reasons:['INDEPENDENT_STORY_PROGRESSION_PAYOFF_EVIDENCE_REQUIRED']}},renderPermission:false});
  afterEach(()=>TestBed.resetTestingModule());
  it('loads policy without a write and leaves unauthenticated actions disabled',async()=>{
    const {f,c,http}=await setup();c.load();http.expectOne('/api/v1/intelligence/workflow/records/saved-run/governance').flush(policy(false));f.detectChanges();
    expect(f.nativeElement.textContent).toContain('AUTHENTICATED_PRODUCTION_OPERATOR_REQUIRED');
    expect(f.nativeElement.textContent).toContain('ATTEMPT_001 · FAIL');
    const button=[...f.nativeElement.querySelectorAll('button')].find((b:any)=>b.textContent.includes('Accept Text')) as HTMLButtonElement;
    expect(button.disabled).toBe(true);c.confirmed=true;c.justification='Concrete source-supported independent explanation.';c.submit('text-acceptance');http.expectNone(r=>r.method==='POST');http.verify();
  });
  it('persists separate text acceptance only after explicit confirmation and never renders',async()=>{
    const {c,http,f}=await setup();c.load();http.expectOne(r=>r.method==='GET').flush(policy(true));
    c.justification='Keep the approved source events while acquiring visual evidence.';c.submit('text-acceptance');http.expectNone(r=>r.method==='POST');
    c.confirmed=true;c.submit('text-acceptance');const req=http.expectOne('/api/v1/intelligence/workflow/records/saved-run/governance/text-acceptance');
    expect(req.request.body.operatorConfirmed).toBe(true);expect(req.request.body.roles).toBeUndefined();
    req.flush({recordId:'acceptance',analysisId:'saved-run',policyVersion:'STEP6_RESOLUTION_V2',state:'TEXT_ACCEPTED_RENDER_BLOCKED'});
    http.expectOne(r=>r.method==='GET').flush({...policy(true),textAcceptance:{recordId:'acceptance',principal:'operator'}});f.detectChanges();
    expect(f.nativeElement.textContent).toContain('TEXT_ACCEPTED_RENDER_BLOCKED');http.expectNone(r=>r.method==='POST');http.verify();
  });
  it('does not claim success when backend rejects or returns a different analysis',async()=>{
    const {c,http}=await setup();c.load();http.expectOne(r=>r.method==='GET').flush(policy(true));c.confirmed=true;c.justification='A concrete source-grounded justification for the exact plan.';
    c.submit('text-acceptance');http.expectOne(r=>r.method==='POST').flush({detail:'Authenticated role unavailable'},{status:403,statusText:'Forbidden'});expect(c.saved).toBeNull();expect(c.error).toContain('role unavailable');http.verify();
  });
  it('invalidates permissions and discards late responses after analysis change',async()=>{
    const {c,f,http}=await setup();c.load();const old=http.expectOne(r=>r.method==='GET');f.componentRef.setInput('analysisId','new-run');f.detectChanges();old.flush(policy(true));expect(c.policy).toBeNull();expect(c.allowed('TEXT_ACCEPTED_RENDER_BLOCKED')).toBe(false);http.verify();
  });
  it('cannot infer approval from a missing or wrong-scope policy response',async()=>{
    const {c,http}=await setup();c.load();http.expectOne(r=>r.method==='GET').flush({...policy(true),analysisId:'other'});c.confirmed=true;c.justification='The server must verify the current exact analysis binding.';c.submit('text-acceptance');http.expectNone(r=>r.method==='POST');http.verify();
  });
});
