import { Component, EventEmitter, Output, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
@Component({ selector: 'app-creative-role', standalone: true, imports: [CommonModule, FormsModule], template: `
<details><summary>Optional story and production prompt assistance</summary><p>Existing prompts can proceed directly to review. Story uses configured DeepSeek; prompt construction uses configured OpenAI. Server configuration and an explicit budget are required.</p>
<p *ngIf="readiness">Server execution: {{ readiness.enabled ? 'enabled' : 'disabled' }} · live verification: {{ readiness.liveVerified ? 'verified' : 'not performed' }}</p><p *ngFor="let role of readiness?.roles">{{ role.role }} · {{ role.provider }} · {{ role.model || 'model not configured' }} · {{ role.configured ? 'credentials/model configured' : 'configuration missing' }}</p>
<textarea aria-label="Story idea or selected story" [(ngModel)]="text"></textarea><label>Constraints<input [(ngModel)]="constraints"></label><label>Lesson content profile<select [(ngModel)]="contentProfile"><option value="CURIOSITY_ADVENTURE">Curiosity</option><option value="EDUCATIONAL">Educational</option><option value="ABSURD_PHYSICS">Absurd physics</option></select></label><label>Lesson model/profile version<input [(ngModel)]="lessonModelVersion"></label><label>Planned duration<input type="number" [(ngModel)]="duration"></label><label>Maximum cost (USD)<input type="number" min="0" [(ngModel)]="budget"></label><label><input type="checkbox" [(ngModel)]="consent">I approve this single text role call within this budget.</label>
<button type="button" (click)="run('STORY')" [disabled]="busy || !readiness?.enabled || !consent || budget <= 0 || !text.trim()">Request story alternatives</button><button type="button" (click)="run('BUILD_PROMPT')" [disabled]="busy || !readiness?.enabled || !consent || budget <= 0 || !text.trim()">Build production prompt</button><p *ngIf="error">{{ error }}</p>
<div *ngFor="let story of result?.result?.alternatives"><p>{{ story }}</p><button type="button" (click)="text = story">Choose and edit story</button></div>
<div *ngIf="result?.result?.prompt"><pre>{{ result.result.prompt }}</pre><button type="button" (click)="draft.emit(result.result.prompt)">Use draft in editor</button></div><p *ngFor="let lesson of result?.retrievedLessons">Verified lesson {{lesson.recordId}} · {{lesson.retrievalReason || lesson.hypothesis}}</p><p *ngIf="result">{{ result.provider }} · {{ result.model }} · {{ result.recordId }} · NOT_VALIDATED · Cost ceiling {{ result.costUpperBoundUsd }}</p></details>` })
export class CreativeRoleComponent {
 private http = inject(HttpClient); @Output() draft = new EventEmitter<string>();
 readiness: any = null;
 constructor() { this.http.get<any>('/api/v1/intelligence/workflow/creative-role/readiness').subscribe({ next: readiness => this.readiness = readiness, error: () => this.error = 'Role readiness unavailable; execution stays disabled.' }); }
 contentProfile='CURIOSITY_ADVENTURE';lessonModelVersion='';duration=15;
 text = ''; constraints = ''; budget = 0; consent = false; busy = false; error = ''; result: any = null;
 run(role: string): void {
  if (!this.readiness?.enabled || !this.consent || this.budget <= 0 || !this.text.trim()) return;
  this.busy = true; this.error = ''; this.result = null;
  this.http.post<any>('/api/v1/intelligence/workflow/creative-role', { role, text: this.text, maxCostUsd: this.budget, context: { constraints: this.constraints, lessonContext: {contentProfile:this.contentProfile, modelVersion:this.lessonModelVersion, duration:this.duration} } }).subscribe({ next: result => { this.result = result; this.busy = false; this.consent = false; }, error: response => { this.error = response.error?.detail || 'Creative role unavailable; no automatic fallback or retry.'; this.busy = false; this.consent = false; } });
 }
}
