import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, Input, OnChanges, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Subscription, timer } from 'rxjs';

@Component({
 selector: 'app-optimization-loop', standalone: true, imports: [CommonModule, FormsModule],
 template: `<section class="bounded-loop" aria-label="Bounded prompt optimization">
 <h3>Automatic prompt optimization</h3>
 <p>One bounded authorization covers generation and independent reviews across rounds. Final text acceptance remains separate.</p>
 <p *ngIf="!auth?.authenticated">Use Owner login above to inspect and authorize a run.</p>
 <ng-container *ngIf="auth?.authenticated">
 <p *ngIf="caps && !caps.realDispatchEnabled" role="status">Real dispatch disabled. Inspection is read only; no paid run can start.</p>
 <fieldset [disabled]="busy || !!run?.runId"><legend>Baseline, target and limits</legend>
 <label>Baseline <select [(ngModel)]="baseline" (ngModelChange)="invalidate()"><option value="SAVED">Current immutable saved prompt</option><option value="DRAFT">Unapproved complete draft</option></select></label>
 <label *ngIf="baseline==='DRAFT'">Complete draft prompt <textarea rows="6" [(ngModel)]="draftPrompt" (ngModelChange)="invalidate()"></textarea></label>
 <label>Quality target <select [(ngModel)]="target" (ngModelChange)="invalidate()"><option value="CANONICAL_RULESET_1_11_A">Canonical Ruleset 1.11: Grade A (92+)</option><option disabled value="CPQ_A_PLUS">CPQ A/A+ unavailable — calibrated grading inactive</option></select></label>
 <label>Routing <select [(ngModel)]="mode" (ngModelChange)="invalidate()"><option>DEEPSEEK_ONLY</option><option>OPENAI_ONLY</option><option>ADAPTIVE</option></select></label>
 <div class="limits"><label>Generation rounds (maximum 5)<input type="number" min="1" max="5" [(ngModel)]="rounds" (ngModelChange)="invalidate()"></label>
 <label>Total provider requests, including reviews<input type="number" min="1" max="15" [(ngModel)]="requests" (ngModelChange)="invalidate()"></label>
 <label>Total USD ceiling<input type="number" min="0.01" max="20" step="0.1" [(ngModel)]="budget" (ngModelChange)="invalidate()"></label>
 <label>Maximum run duration (seconds)<input type="number" min="30" max="1800" [(ngModel)]="seconds" (ngModelChange)="invalidate()"></label></div>
 <details><summary>Explicit allowed provider roles, models, output and spending ceilings</summary>
 <div *ngFor="let op of operations"><b>{{op.role}} · {{op.provider}} / {{op.model}} · reasoning {{op.reasoningEffort}}</b>
 <label>Maximum output tokens<input type="number" min="1024" [max]="op.maximumTokens" [(ngModel)]="op.maxOutputTokens" (ngModelChange)="invalidate()"></label>
 <label>Per-request USD ceiling<input type="number" min="0.01" max="20" step="0.05" [(ngModel)]="op.maxCostUsd" (ngModelChange)="invalidate()"></label></div></details>
 <button type="button" (click)="inspect()">Inspect exact protected source and baseline</button>
 </fieldset>
 <details *ngIf="inspection"><summary>Exact baseline, approved story, owner interpretations and production settings</summary>
 <p>Baseline SHA-256: {{inspection.scope.baselineSha256}}</p><pre>{{inspection.scope.baselinePrompt}}</pre>
 <pre>{{inspection.scope.approvedStory | json}}</pre><pre>{{inspection.scope.ownerDecisions | json}}</pre><pre>{{inspection.scope.settings | json}}</pre></details>
 <label *ngIf="!run?.runId"><input type="checkbox" [(ngModel)]="consent">I confirm the protected source/settings and explicitly authorize all listed operations within these run limits. No automatic retries, prompt approval, grading activation or rendering.</label>
 <button type="button" *ngIf="!run?.runId" (click)="start()" [disabled]="busy || !inspection || !consent || !caps?.realDispatchEnabled">Start bounded optimization</button>
 <p>Stop prevents new calls. An in-flight call remains potentially chargeable and will be collected. Ambiguous/terminal runs cannot replay or resume calls; a changed grant requires fresh authorization.</p>
 <label>Reconnect to run ID<input [(ngModel)]="runId"></label><button type="button" (click)="load()" [disabled]="busy || !runId">Reconnect (read only)</button>
 <section *ngIf="run?.runId" aria-label="Optimization progress" aria-live="polite">
 <p><b>{{run.state}} · {{run.progress.phase}} · Round {{run.progress.round}}</b></p>
 <p>{{run.progress.reason}}</p><p>Run: {{run.runId}} · Deadline: {{run.deadline}}</p>
 <p>Spent USD {{run.cost.spentUsd}} · reserved {{run.cost.reservedUsd}} · unknown charge exposure {{run.cost.unknownReservedUsd}}</p>
 <p>Canonical Ruleset 1.11: {{run.progress.bestEvaluation?.canonical?.score ?? 'pending'}} / {{run.progress.bestEvaluation?.canonical?.grade ?? 'pending'}} · Target A ≥92 · Gap {{gap()}}</p>
 <button type="button" (click)="stop()" [disabled]="busy || !['READY','RUNNING','PAUSED'].includes(run.state) || run.cancel">Stop new calls</button>
 <p *ngIf="run.cancel">Cancellation requested; collect any dispatched result before concluding accounting.</p>
 <details open><summary>Current best draft — unapproved</summary><pre>{{run.progress.bestPrompt}}</pre></details>
 <details><summary>Rounds: complete prompts, actual scores and provenance</summary><article *ngFor="let d of run.drafts"><b>Round {{d.payload.round}} · {{d.payload.evaluation?.canonical?.score}} / {{d.payload.evaluation?.canonical?.grade}}</b><pre>{{d.payload | json}}</pre></article></details>
 <details><summary>Retention/rejection, evaluator integrity, exact diffs and stopping evidence</summary><pre>{{run.events | json}}</pre><pre>{{run.progress.lastAssessment | json}}</pre><pre>{{run.progress.evaluationIntegrity | json}}</pre></details>
 <details><summary>Provider requests, raw results and safe failures</summary><pre>{{run.requests | json}}</pre></details>
 <p>Source fidelity and independent support: {{run.progress.lastAssessment?.sourceFidelity || 'UNKNOWN'}} / {{run.progress.lastAssessment?.independentSupport ?? 'UNKNOWN'}}.</p>
 <fieldset><legend>Separate final prompt acceptance</legend><label><input type="checkbox" [(ngModel)]="acceptConsent">I explicitly approve this exact final draft as a new immutable prompt version; no render or grade activation.</label><button type="button" (click)="accept()" [disabled]="busy || !acceptConsent || run.progress.reason!=='TARGET_REACHED_REVIEW_REQUIRED' || !run.progress.lastAssessment?.retained || !run.progress.lastAssessment?.independentSupport">Accept final reviewed prompt</button><p *ngIf="run.progress.reason!=='TARGET_REACHED_REVIEW_REQUIRED'">Target unmet: best available draft remains unapproved.</p></fieldset>
 <p>Official CPQ grading: INACTIVE. Render authorized: false. Accepting a final revision requires the existing explicit prompt-version approval workflow; this panel never creates an approved version.</p>
 </section></ng-container><p role="status">{{message}}</p></section>`,
 styles: [`.bounded-loop{display:grid;gap:10px;min-width:0;margin:14px 0;padding:14px;border:1px solid #bac9d8;border-radius:8px}.bounded-loop fieldset{min-width:0}.bounded-loop label{display:grid;gap:4px;margin:8px 0}.bounded-loop pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:32rem;overflow:auto}.bounded-loop textarea,.bounded-loop input,.bounded-loop select{max-width:100%;box-sizing:border-box;padding:7px}.limits{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,190px),1fr));gap:10px}`]
})
export class OptimizationLoopComponent implements OnChanges, OnDestroy {
 @Input() analysisId=''; @Input() auth:any=null;
 private http=inject(HttpClient);private cd=inject(ChangeDetectorRef);private polling?:Subscription;
 caps:any;inspection:any;run:any;runId='';message='';busy=false;consent=false;
 acceptConsent=false;baseline='SAVED';draftPrompt='';target='CANONICAL_RULESET_1_11_A';mode='ADAPTIVE';rounds=5;requests=15;budget=1;seconds=600;operations:any[]=[];private key=crypto.randomUUID();private identity='';
 private base='/api/v1/intelligence/workflow/cpq/optimization-runs';
 ngOnChanges(){const id=this.analysisId+':'+!!this.auth?.authenticated;if(id===this.identity)return;this.identity=id;this.polling?.unsubscribe();this.run=null;this.inspection=null;this.consent=false;if(!this.auth?.authenticated||!this.analysisId)return;
 this.http.get<any>(this.base+'/capabilities').subscribe({next:v=>{this.caps=v;this.operations=Object.entries(v.profiles).flatMap(([id,p]:any)=>['GENERATION','SOURCE_FIDELITY','CRITIC'].map(role=>({role,profileId:id,provider:p.provider,model:p.model,reasoningEffort:p.reasoningEffort,maxOutputTokens:p.reviewMaxOutputTokens,maximumTokens:p.reviewMaxOutputTokens,maxCostUsd:.20})));this.cd.markForCheck();},error:()=>this.fail('Capabilities unavailable')});
 this.http.get<any>(this.base+'/latest',{params:{analysisId:this.analysisId}}).subscribe({next:v=>{if(v.runId)this.receive(v);},error:()=>this.fail('Run inspection unavailable')});}
 invalidate(){this.inspection=null;this.consent=false;this.key=crypto.randomUUID();}
 inspect(){this.post('/preflight',{analysisId:this.analysisId,draftPrompt:this.baseline==='DRAFT'?this.draftPrompt:''},v=>{this.inspection=v;this.consent=false;});}
 start(){if(!this.inspection||!this.consent||!this.caps?.realDispatchEnabled||this.busy)return;
 const generation=this.mode==='ADAPTIVE'?['deepseek-primary','openai-escalation']:[this.mode==='DEEPSEEK_ONLY'?'deepseek-primary':'openai-escalation'];
 const operations=this.operations.filter(o=>o.role!=='GENERATION'||generation.includes(o.profileId)).map(({maximumTokens,...op})=>op);
 this.post('',{analysisId:this.analysisId,draftPrompt:this.baseline==='DRAFT'?this.draftPrompt:'',scopeSha256:this.inspection.scopeSha256,idempotencyKey:this.key,target:this.target,mode:this.mode,maxRounds:this.rounds,maxRequests:this.requests,maxRunSeconds:this.seconds,maxTotalUsd:this.budget,operations,authorizePaidInference:true,confirmSourceAuthority:true,automaticRetries:false},v=>this.receive(v));}
 load(){if(!this.runId||this.busy)return;this.http.get<any>(this.base+'/'+encodeURIComponent(this.runId)).subscribe({next:v=>this.receive(v),error:()=>this.fail('Run unavailable; no execution was retried')});}
 accept(){if(!this.acceptConsent||this.run?.progress?.reason!=='TARGET_REACHED_REVIEW_REQUIRED')return;const id=this.run.progress.reviewCandidateId;const draft=this.run.drafts.find((d:any)=>d.draftId===id);if(!draft)return;this.post('/'+this.run.runId+'/accept',{draftId:id,promptSha256:draft.payload.evaluation.promptSha256,approveExactPromptVersion:true,confirmNoRenderOrGrade:true},()=>{this.acceptConsent=false;this.message='Explicit prompt version created; new analysis and all render requirements remain separate.';});}
 stop(){if(this.run?.runId)this.post('/'+this.run.runId+'/stop',{},v=>this.receive(v));}
 gap(){const score=this.run?.progress?.bestEvaluation?.canonical?.score;return typeof score==='number'?Math.max(0,92-score):'UNKNOWN';}
 private receive(v:any){this.run=v;this.runId=v.runId;this.consent=false;this.polling?.unsubscribe();if(['READY','RUNNING','PAUSED'].includes(v.state))this.polling=timer(1500,1500).subscribe(()=>this.load());this.cd.markForCheck();}
 private post(path:string,body:any,done:(v:any)=>void){if(this.busy)return;this.busy=true;this.http.post<any>(this.base+path,body,{headers:{'X-CPQ-CSRF':this.auth?.csrfToken||''}}).subscribe({next:v=>{this.busy=false;done(v);this.cd.markForCheck();},error:()=>{this.busy=false;this.fail('Command blocked or outcome uncertain. Reconnect to saved state; do not retry a provider request.');}});}
 private fail(s:string){this.message=s;this.cd.markForCheck();}
 ngOnDestroy(){this.polling?.unsubscribe();}
}
