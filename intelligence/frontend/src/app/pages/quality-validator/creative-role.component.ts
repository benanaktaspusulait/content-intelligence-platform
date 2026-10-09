import { ChangeDetectorRef, Component, EventEmitter, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
@Component({ selector: 'app-creative-role', standalone: true, imports: [CommonModule, FormsModule], template: `
<details class="creative-role-assistance"><summary>Optional story and production prompt assistance</summary><div class="creative-role-content"><p>Existing prompts can proceed directly to review. Story uses configured DeepSeek; prompt construction uses configured OpenAI. Server configuration and an explicit budget are required.</p>
<div class="creative-role-status"><p *ngIf="readiness">Server execution: {{ readiness.enabled ? 'enabled' : 'disabled' }} · live verification: {{ readiness.liveVerified ? 'verified' : 'not performed' }}</p><p *ngFor="let role of readiness?.roles">{{ role.role }} · {{ role.provider }} · {{ role.model || 'model not configured' }} · {{ role.configured ? 'credentials/model configured' : 'configuration missing' }}</p></div>
<div class="creative-role-fields"><label class="creative-role-story">Story idea or selected story<textarea aria-label="Story idea or selected story" [(ngModel)]="text"></textarea></label><label>Constraints<input [(ngModel)]="constraints"></label><label>Lesson content profile<select [(ngModel)]="contentProfile"><option value="CURIOSITY_ADVENTURE">Curiosity</option><option value="EDUCATIONAL">Educational</option><option value="ABSURD_PHYSICS">Absurd physics</option></select></label><label>Lesson model/profile version<input [(ngModel)]="lessonModelVersion"></label><label>Lesson generator<input [(ngModel)]="lessonGenerator"></label><label>Lesson aspect ratio<input [(ngModel)]="lessonAspectRatio"></label><label>Planned duration<input type="number" [(ngModel)]="duration"></label><label>Maximum cost (USD)<input type="number" min="0" [(ngModel)]="budget"></label></div>
<label class="creative-role-consent"><input type="checkbox" [(ngModel)]="consent"> <span>I approve this single text role call within this budget.</span></label><div class="creative-role-actions"><button type="button" (click)="run('STORY')" [disabled]="busy || !readiness?.enabled || !consent || budget <= 0 || !text.trim()">Request story alternatives</button><button type="button" (click)="run('BUILD_PROMPT')" [disabled]="busy || !readiness?.enabled || !consent || budget <= 0 || !text.trim()">Build production prompt</button></div><p *ngIf="error" class="creative-role-error">{{ error }}</p></div>
<div *ngFor="let story of result?.result?.alternatives"><p>{{ story }}</p><button type="button" (click)="chooseStory(story)">Choose and edit story</button></div>
<div *ngIf="result?.result?.prompt"><pre>{{ result.result.prompt }}</pre><button type="button" (click)="draft.emit({prompt:result.result.prompt, recordId:result.recordId})">Use draft in editor</button></div><p *ngFor="let lesson of result?.retrievedLessons">Verified lesson {{lesson.recordId}} · {{lesson.retrievalReason || lesson.hypothesis}}</p><p *ngIf="result">{{ result.provider }} · {{ result.model }} · {{ result.recordId }} · NOT_VALIDATED · Cost ceiling {{ result.costUpperBoundUsd }}</p></details>`, styles: [`
.creative-role-assistance { margin: 1.25rem 0; padding: 0; border: 1px solid #dfe5e8; border-radius: 8px; background: #fff; }
.creative-role-assistance > summary { padding: 1rem 1.2rem; color: #26352c; cursor: pointer; font-size: 1rem; font-weight: 700; }
.creative-role-content { display: grid; gap: 1rem; padding: 0 1.2rem 1.2rem; }
.creative-role-content p { margin: 0; color: #52616b; line-height: 1.5; }
.creative-role-status { display: grid; gap: .35rem; padding: .75rem; border-radius: 6px; background: #f7faf5; }
.creative-role-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; }
.creative-role-fields label { display: grid; min-width: 0; gap: .4rem; color: #40515a; font-size: .78rem; font-weight: 700; }
.creative-role-fields .creative-role-story { grid-column: 1 / -1; }
.creative-role-fields input, .creative-role-fields select, .creative-role-fields textarea { width: 100%; min-width: 0; padding: .65rem .7rem; border: 1px solid #cbd6ce; border-radius: 6px; background: #fff; color: #2c3e50; font: inherit; font-weight: 400; }
.creative-role-fields textarea { min-height: 110px; resize: vertical; }
.creative-role-consent { display: flex; align-items: flex-start; gap: .5rem; color: #40515a; font-size: .78rem; }
.creative-role-consent input { margin-top: .15rem; }
.creative-role-actions { display: flex; flex-wrap: wrap; gap: .6rem; }
.creative-role-actions button { padding: .65rem .85rem; border: 1px solid #cbd6ce; border-radius: 6px; background: #eef1ed; color: #31583b; cursor: pointer; font-weight: 700; }
.creative-role-actions button:disabled { cursor: default; opacity: .55; }
.creative-role-error { color: #a33d32 !important; }
@media (max-width: 850px) { .creative-role-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 560px) { .creative-role-fields { grid-template-columns: 1fr; } .creative-role-fields .creative-role-story { grid-column: auto; } }
` ] })
export class CreativeRoleComponent {
 private changeDetector = inject(ChangeDetectorRef);
 private http = inject(HttpClient); @Output() draft = new EventEmitter<{prompt:string;recordId:string}>();
 readiness: any = null;
 constructor() { this.http.get<any>('/api/v1/intelligence/workflow/creative-role/readiness').subscribe({ next: readiness => {this.readiness = readiness;this.changeDetector.markForCheck();}, error: () => {this.error = 'Role readiness unavailable; execution stays disabled.';this.changeDetector.markForCheck();} }); }
 storyRecordId = '';
 chooseStory(story: string) {this.text = story;this.storyRecordId = this.result.recordId;}
 contentProfile='CURIOSITY_ADVENTURE';lessonModelVersion='';lessonGenerator='AUTO';lessonAspectRatio='9:16';duration=15;
 text = ''; constraints = ''; budget = 0; consent = false; busy = false; error = ''; result: any = null;
 run(role: string): void {
  if (!this.readiness?.enabled || !this.consent || this.budget <= 0 || !this.text.trim()) return;
  this.busy = true; this.error = ''; this.result = null;
  this.http.post<any>('/api/v1/intelligence/workflow/creative-role', { role, text: this.text, maxCostUsd: this.budget, context: { sourceStoryRecordId:this.storyRecordId || null, constraints: this.constraints, lessonContext: {contentProfile:this.contentProfile, modelVersion:this.lessonModelVersion, duration:this.duration,generator:this.lessonGenerator,settings:{mode:"image2video",aspectRatio:this.lessonAspectRatio,resolution:"480p"}} } }).subscribe({ next: result => { this.result = result; this.busy = false; this.consent = false; this.changeDetector.markForCheck(); }, error: response => { this.error = response.error?.detail || 'Creative role unavailable; no automatic fallback or retry.'; this.busy = false; this.consent = false; this.changeDetector.markForCheck(); } });
 }
}
