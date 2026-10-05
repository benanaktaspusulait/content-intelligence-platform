import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { TimelineChartComponent } from './timeline-chart.component';

interface QualityReport {
  overallScore: number;
  status: 'RENDER_READY' | 'NEEDS_REVISION' | 'BLOCKED' | 'SERVICE_ERROR';
  rulesetVersion: string;
  blockerCount: number;
  criticalCount: number;
  warningCount: number;
  familyScores: { [key: string]: number };
  failedRules: RuleEvaluation[];
  unknownRules: RuleEvaluation[];
  notApplicableRules: RuleEvaluation[];
  serviceErrors: RuleEvaluation[];
  parserConfidence: number;
  parserWarnings: string[];
  parserAssumptions: string[];
  evidenceMissing: string[];
  topStrengths: string[];
  topWeaknesses: string[];
  provenance: QualityProvenance;
  priorityFixes: PriorityFix[];
  scoreCard: ScoreCard;
  timelineData: TimelineData;
}

interface LinkedValidationResponse { validationRecordId: number; report: QualityReport; }

interface RuleEvaluation {
  ruleId: string;
  ruleName: string;
  family: string;
  severity: string;
  outcome: 'PASS' | 'FAIL' | 'UNKNOWN' | 'NOT_APPLICABLE' | 'SERVICE_ERROR';
  message: string;
  actualValue?: number;
  thresholdValue?: number;
}

interface PriorityFix {
  ruleId: string;
  ruleName: string;
  family: string;
  severity: string;
  issue: string;
  recommendation: string;
  impact: string;
  strategy: 'CONTROLLED_PATCH' | 'REPLACE_CONCEPT' | 'HUMAN_REVIEW';
}

interface QualityProvenance {
  parserVersion: string;
  ruleEngineVersion: string;
  semanticProvider: string;
  semanticModelVersion: string;
  producibilityValidatorVersion: string;
  evaluationStage: 'PRE_RENDER' | 'POST_RENDER';
}

interface ScoreCard {
  score: number;
  label: string;
  color: string;
}

interface TimelineData {
  beats: Beat[];
  consequenceMarkers: ConsequenceMarker[];
  stateSegments: StateSegment[];
}

interface Beat {
  startTime: number;
  endTime: number;
  action: string;
  consequence: string;
  intensity: number;
  isNewConsequence: boolean;
}

interface ConsequenceMarker {
  time: number;
  consequence: string;
  type: string;
}

interface StateSegment {
  stateId: string;
  startTime: number;
  endTime: number;
  percentage: number;
}

@Component({
  selector: 'app-quality-validator',
  standalone: true,
  imports: [CommonModule, FormsModule, TimelineChartComponent],
  templateUrl: './quality-validator.component.html',
  styleUrls: ['./quality-validator.component.scss']
})
export class QualityValidatorComponent {
  prompt: string = '';
  contentTitle: string = '';
  contentType: string = 'SHORT';
  contentId: string = '';
  promptVersionId: string = '';
  validationRecordId: number | null = null;
  report: QualityReport | null = null;
  loading: boolean = false;
  error: string | null = null;
  
  // Sample prompt for testing
  samplePrompt: string = `[TITLE] Kiko's Mat Mystery
[DURATION] 15 seconds
[FORMAT] Instagram Reel (9:16 vertical)

[CHARACTERS]
- Kiko (curious penguin, 3 years)

[SETTING]
Interior shot, Kiko's playroom with colorful mat in center

[LEARNING OBJECTIVE]
Problem-solving through observation and experimentation

[CORE MECHANIC]
Kiko sits on mat that changes color when pressed. Single static state.

[HOOK] 0.0-2.0 SEC
Kiko walks toward colorful mat, notices it's soft

[BEAT 1] 2.0-8.5 SEC
Kiko sits on mat
Visual state: sitting on mat (42% of video = 6.5s)
Consequence: Mat changes to blue
Intensity: 3

[BEAT 2] 8.5-11.0 SEC  
Kiko stays sitting, looks around
Visual state: sitting on mat (continuation)
Consequence: Nothing new happens
Intensity: 2

[BEAT 3] 11.0-13.5 SEC
Kiko shifts weight slightly
Visual state: sitting on mat (continuation)  
Consequence: Mat shifts to lighter blue
Intensity: 3

[PAYOFF] 13.5-15.0 SEC
Kiko smiles while still sitting
Visual state: sitting on mat (continuation)
Consequence: Feels happy about mat
Intensity: 4`;

  constructor(private http: HttpClient) {}


  validatePrompt(): void {
    const linked = Boolean(this.contentId.trim() && this.promptVersionId.trim());
    if (!linked && (!this.prompt || this.prompt.length < 100)) {
      this.error = 'Prompt must be at least 100 characters';
      return;
    }
    if (linked && (![Number(this.contentId), Number(this.promptVersionId)].every(Number.isInteger) || [Number(this.contentId), Number(this.promptVersionId)].some(value => value <= 0))) {
      this.error = 'Content ID and prompt version ID must be positive integers';
      return;
    }

    this.loading = true;
    this.error = null;
    this.report = null;

    const apiUrl = linked ? '/api/v1/intelligence/quality/validate' : '/api/quality/validate';
    const payload = linked ? {
      prompt: '',
      rulesetVersion: 'latest',
      contentId: Number(this.contentId),
      promptVersionId: Number(this.promptVersionId),
    } : { prompt: this.prompt, rulesetVersion: 'latest' };

    this.http.post<QualityReport | LinkedValidationResponse>(apiUrl, payload).subscribe({
      next: (response) => {
        if (linked) {
          const linkedResponse = response as LinkedValidationResponse;
          this.validationRecordId = linkedResponse.validationRecordId;
          this.report = linkedResponse.report;
        } else {
          this.validationRecordId = null;
          this.report = response as QualityReport;
        }
        this.loading = false;
      },
      error: (err) => {
        this.error = err.error?.message || 'Validation failed. Please try again.';
        this.loading = false;
        console.error('Validation error:', err);
      }
    });
  }

  clearPrompt(): void {
    this.prompt = '';
    this.report = null;
    this.error = null;
    this.validationRecordId = null;
  }

  loadSamplePrompt(): void {
    this.prompt = this.samplePrompt;
    this.report = null;
    this.error = null;
    this.validationRecordId = null;
  }

  createContentAndPrompt(): void {
    if (!this.contentTitle.trim() || this.prompt.length < 100) {
      this.error = 'Content title and a prompt of at least 100 characters are required';
      return;
    }
    this.loading = true; this.error = null;
    this.http.post<{ id: number }>('/api/v1/intelligence/contents', {
      title: this.contentTitle.trim(), type: this.contentType, description: 'Pompom Hills local production content',
    }).subscribe({
      next: content => this.http.post<{ id: number }>(`/api/v1/intelligence/contents/${content.id}/prompt-versions`, { rawText: this.prompt, parsedIr: '{}' }).subscribe({
        next: promptVersion => { this.contentId = String(content.id); this.promptVersionId = String(promptVersion.id); this.validationRecordId = null; this.loading = false; },
        error: response => { this.error = response.error?.detail || response.error?.message || 'Prompt version could not be created'; this.loading = false; },
      }),
      error: response => { this.error = response.error?.detail || response.error?.message || 'Content could not be created'; this.loading = false; },
    });
  }

  createRevisionPromptVersion(): void {
    if (!this.contentId || this.prompt.length < 100) {
      this.error = 'A linked content ID and a prompt of at least 100 characters are required';
      return;
    }
    this.loading = true; this.error = null; this.report = null; this.validationRecordId = null;
    this.http.post<{ id: number }>(`/api/v1/intelligence/contents/${Number(this.contentId)}/prompt-versions`, { rawText: this.prompt, parsedIr: '{}' }).subscribe({
      next: version => { this.promptVersionId = String(version.id); this.loading = false; },
      error: response => { this.error = response.error?.detail || response.error?.message || 'Prompt revision could not be saved'; this.loading = false; },
    });
  }

  getStatusBadgeClass(): string {
    if (!this.report) return '';
    
    switch (this.report.status) {
      case 'RENDER_READY':
        return 'badge-success';
      case 'NEEDS_REVISION':
        return 'badge-warning';
      case 'BLOCKED':
        return 'badge-danger';
      case 'SERVICE_ERROR':
        return 'badge-danger';
      default:
        return '';
    }
  }

  getScoreClass(): string {
    if (!this.report) return '';
    
    const score = this.report.overallScore;
    if (score >= 92) return 'score-excellent';
    if (score >= 80) return 'score-good';
    if (score >= 70) return 'score-acceptable';
    if (score >= 60) return 'score-weak';
    return 'score-poor';
  }

  getSeverityBadgeClass(severity: string): string {
    switch (severity) {
      case 'BLOCKER':
        return 'badge-danger';
      case 'CRITICAL':
        return 'badge-danger';
      case 'WARNING':
        return 'badge-warning';
      default:
        return 'badge-secondary';
    }
  }

  getFamilyScoreClass(score: number): string {
    if (score >= 90) return 'family-score-excellent';
    if (score >= 75) return 'family-score-good';
    if (score >= 60) return 'family-score-acceptable';
    return 'family-score-poor';
  }

  getFamilyScoreEntries(): [string, number][] {
    if (!this.report?.familyScores) return [];
    return Object.entries(this.report.familyScores).sort((a, b) => b[1] - a[1]);
  }

  getIntensityColor(intensity: number): string {
    if (intensity >= 8) return '#dc3545'; // red
    if (intensity >= 6) return '#fd7e14'; // orange
    if (intensity >= 4) return '#ffc107'; // yellow
    return '#28a745'; // green
  }

  getStateColor(index: number): string {
    const colors = ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#dc3545', '#fd7e14'];
    return colors[index % colors.length];
  }

  formatTime(seconds: number): string {
    return `${seconds.toFixed(1)}s`;
  }

  formatPercentage(value: number): string {
    return `${(value * 100).toFixed(0)}%`;
  }

  renderQueueUrl(): string {
    return `/render?contentId=${encodeURIComponent(this.contentId)}&promptVersionId=${encodeURIComponent(this.promptVersionId)}&validationRecordId=${this.validationRecordId}`;
  }
}
