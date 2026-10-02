import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { interval } from 'rxjs';
import { startWith, switchMap } from 'rxjs/operators';

interface RenderJob {
  id: string;
  contentId: number;
  contentTitle: string;
  promptVersionId: number;
  promptVersionNumber: number;
  jobType: string;
  status: string;
  attemptNumber: number;
  maxAttempts: number;
  openartJobId?: string;
  creditsEstimated?: number;
  creditsActual?: number;
  queuedAt: string;
  startedAt?: string;
  completedAt?: string;
  failedAt?: string;
  errorCode?: string;
  errorMessage?: string;
  qaResult?: {
    id: string;
    decision: string;
    decisionReason: string;
    complianceScore: number;
    confidence?: number;
    hasDeadAir: boolean;
    characterIdentityVerified: boolean;
    characterIdentityIssues?: string;
    requiresHumanReview: boolean;
  };
}

interface Page<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  size: number;
  number: number;
}

@Component({
  selector: 'app-render-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="render-dashboard">
      <header class="dashboard-header">
        <div class="header-content">
          <div class="title-section">
            <h1>Render Pipeline Dashboard</h1>
            <p class="subtitle">Monitor render jobs, QA results, and production status</p>
          </div>
          <div class="stats-section">
            <div class="stat-card">
              <div class="stat-value">{{ stats().queued }}</div>
              <div class="stat-label">Queued</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats().generating }}</div>
              <div class="stat-label">Generating</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats().complete }}</div>
              <div class="stat-label">Complete</div>
            </div>
            <div class="stat-card alert">
              <div class="stat-value">{{ stats().abandoned }}</div>
              <div class="stat-label">Abandoned</div>
            </div>
          </div>
        </div>
      </header>

      <div class="dashboard-content">
        <div class="jobs-list">
          @if (loading()) {
            <div class="loading-state">
              <div class="spinner"></div>
              <p>Loading render jobs...</p>
            </div>
          } @else if (error()) {
            <div class="error-state">
              <p>{{ error() }}</p>
              <button (click)="loadJobs()">Retry</button>
            </div>
          } @else if (jobs().length === 0) {
            <div class="empty-state">
              <p>No render jobs found</p>
            </div>
          } @else {
            @for (job of jobs(); track job.id) {
              <div class="job-card" [class.has-qa]="job.qaResult">
                <div class="job-header">
                  <div class="job-info">
                    <h3>{{ job.contentTitle }}</h3>
                    <div class="job-meta">
                      <span class="job-id">{{ job.id.substring(0, 8) }}</span>
                      <span class="job-type">{{ job.jobType }}</span>
                      <span class="job-version">v{{ job.promptVersionNumber }}</span>
                      <span class="job-attempt">Attempt {{ job.attemptNumber }}/{{ job.maxAttempts }}</span>
                    </div>
                  </div>
                  <div class="job-status">
                    <span [class]="'status-badge status-' + job.status.toLowerCase()">
                      {{ job.status }}
                    </span>
                  </div>
                </div>

                <div class="job-progress">
                  <div class="progress-bar">
                    <div class="progress-fill" [style.width.%]="getProgress(job)"></div>
                  </div>
                  <div class="progress-labels">
                    <span>{{ getProgressLabel(job) }}</span>
                    @if (job.creditsEstimated) {
                      <span class="credits">{{ job.creditsEstimated }} credits</span>
                    }
                  </div>
                </div>

                @if (job.qaResult) {
                  <div class="qa-results" [class.requires-review]="job.qaResult.requiresHumanReview">
                    <div class="qa-header">
                      <h4>QA Analysis</h4>
                      <span [class]="'qa-decision qa-' + job.qaResult.decision.toLowerCase()">
                        {{ job.qaResult.decision }}
                      </span>
                    </div>
                    <div class="qa-details">
                      <div class="qa-metrics">
                        <div class="metric">
                          <span class="metric-label">Compliance</span>
                          <div class="metric-value-bar">
                            <div class="compliance-bar">
                              <div class="compliance-fill" 
                                   [style.width.%]="job.qaResult.complianceScore"
                                   [class.low]="job.qaResult.complianceScore < 70"></div>
                            </div>
                            <span class="metric-value">{{ job.qaResult.complianceScore }}%</span>
                          </div>
                        </div>
                        @if (job.qaResult.confidence) {
                          <div class="metric">
                            <span class="metric-label">Confidence</span>
                            <span class="metric-value">{{ (job.qaResult.confidence * 100).toFixed(1) }}%</span>
                          </div>
                        }
                      </div>
                      <div class="qa-checks">
                        <div class="check-item" [class.failed]="job.qaResult.hasDeadAir">
                          <span class="check-icon">{{ job.qaResult.hasDeadAir ? '⚠️' : '✓' }}</span>
                          <span>{{ job.qaResult.hasDeadAir ? 'Dead air detected' : 'No dead air' }}</span>
                        </div>
                        <div class="check-item" [class.failed]="!job.qaResult.characterIdentityVerified">
                          <span class="check-icon">{{ job.qaResult.characterIdentityVerified ? '✓' : '✗' }}</span>
                          <span>{{ job.qaResult.characterIdentityVerified ? 'Character verified' : 'Character mismatch' }}</span>
                        </div>
                      </div>
                      <div class="qa-reason">
                        <p>{{ job.qaResult.decisionReason }}</p>
                      </div>
                      @if (job.qaResult.requiresHumanReview) {
                        <div class="human-review-alert">
                          <strong>⚠️ Requires Human Review</strong>
                          @if (job.qaResult.characterIdentityIssues) {
                            <p>{{ job.qaResult.characterIdentityIssues }}</p>
                          }
                        </div>
                      }
                    </div>
                  </div>
                }

                @if (job.errorMessage) {
                  <div class="job-error">
                    <strong>Error:</strong> {{ job.errorMessage }}
                  </div>
                }

                <div class="job-footer">
                  <div class="job-times">
                    <span>Queued: {{ formatTime(job.queuedAt) }}</span>
                    @if (job.completedAt) {
                      <span>Completed: {{ formatTime(job.completedAt) }}</span>
                    }
                  </div>
                </div>
              </div>
            }
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    .render-dashboard {
      min-height: 100vh;
      background: #0a0a0a;
      color: #ffffff;
    }

    .dashboard-header {
      background: linear-gradient(135deg, #1a1a1a 0%, #0f0f0f 100%);
      border-bottom: 1px solid #333;
      padding: 2rem;
    }

    .header-content {
      max-width: 1400px;
      margin: 0 auto;
    }

    .title-section h1 {
      font-size: 2rem;
      font-weight: 600;
      margin: 0 0 0.5rem 0;
    }

    .subtitle {
      color: #888;
      margin: 0;
    }

    .stats-section {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 1rem;
      margin-top: 2rem;
    }

    .stat-card {
      background: #1a1a1a;
      padding: 1rem;
      border-radius: 8px;
      border: 1px solid #333;
      text-align: center;
    }

    .stat-card.alert {
      border-color: #ff6b6b;
    }

    .stat-value {
      font-size: 2rem;
      font-weight: 700;
      color: #4ecdc4;
    }

    .stat-card.alert .stat-value {
      color: #ff6b6b;
    }

    .stat-label {
      color: #888;
      font-size: 0.875rem;
      margin-top: 0.5rem;
    }

    .dashboard-content {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }

    .jobs-list {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .job-card {
      background: #1a1a1a;
      border: 1px solid #333;
      border-radius: 12px;
      padding: 1.5rem;
      transition: border-color 0.2s;
    }

    .job-card:hover {
      border-color: #4ecdc4;
    }

    .job-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .job-info h3 {
      margin: 0 0 0.5rem 0;
      font-size: 1.25rem;
    }

    .job-meta {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      font-size: 0.875rem;
      color: #888;
    }

    .job-meta span {
      padding: 0.25rem 0.5rem;
      background: #0f0f0f;
      border-radius: 4px;
    }

    .status-badge {
      padding: 0.5rem 1rem;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.875rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .status-queued { background: #3498db; }
    .status-generating { background: #9b59b6; }
    .status-polling { background: #f39c12; }
    .status-downloading { background: #16a085; }
    .status-complete { background: #27ae60; }
    .status-failed { background: #e74c3c; }
    .status-abandoned { background: #c0392b; }

    .job-progress {
      margin: 1rem 0;
    }

    .progress-bar {
      height: 8px;
      background: #0f0f0f;
      border-radius: 4px;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #4ecdc4, #44a08d);
      transition: width 0.3s ease;
    }

    .progress-labels {
      display: flex;
      justify-content: space-between;
      margin-top: 0.5rem;
      font-size: 0.875rem;
      color: #888;
    }

    .qa-results {
      margin-top: 1.5rem;
      padding: 1.5rem;
      background: #0f0f0f;
      border-radius: 8px;
      border: 1px solid #333;
    }

    .qa-results.requires-review {
      border-color: #ff6b6b;
    }

    .qa-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }

    .qa-header h4 {
      margin: 0;
      font-size: 1rem;
      color: #4ecdc4;
    }

    .qa-decision {
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.875rem;
    }

    .qa-accept { background: #27ae60; }
    .qa-rerender { background: #f39c12; }
    .qa-abandon { background: #e74c3c; }

    .qa-details {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .qa-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }

    .metric {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .metric-label {
      font-size: 0.875rem;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .metric-value-bar {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .compliance-bar {
      flex: 1;
      height: 8px;
      background: #1a1a1a;
      border-radius: 4px;
      overflow: hidden;
    }

    .compliance-fill {
      height: 100%;
      background: #27ae60;
      transition: width 0.3s ease;
    }

    .compliance-fill.low {
      background: #e74c3c;
    }

    .metric-value {
      font-weight: 600;
      color: #4ecdc4;
    }

    .qa-checks {
      display: flex;
      gap: 1rem;
      flex-wrap: wrap;
    }

    .check-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      background: #1a1a1a;
      border-radius: 6px;
      font-size: 0.875rem;
    }

    .check-item.failed {
      background: rgba(231, 76, 60, 0.1);
      border: 1px solid #e74c3c;
    }

    .check-icon {
      font-size: 1.25rem;
    }

    .qa-reason {
      padding: 1rem;
      background: #1a1a1a;
      border-radius: 6px;
      font-size: 0.9rem;
      color: #ccc;
    }

    .qa-reason p {
      margin: 0;
    }

    .human-review-alert {
      padding: 1rem;
      background: rgba(255, 107, 107, 0.1);
      border: 1px solid #ff6b6b;
      border-radius: 6px;
    }

    .human-review-alert strong {
      display: block;
      margin-bottom: 0.5rem;
      color: #ff6b6b;
    }

    .human-review-alert p {
      margin: 0;
      font-size: 0.875rem;
    }

    .job-error {
      margin-top: 1rem;
      padding: 1rem;
      background: rgba(231, 76, 60, 0.1);
      border: 1px solid #e74c3c;
      border-radius: 6px;
      font-size: 0.875rem;
    }

    .job-footer {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid #333;
    }

    .job-times {
      display: flex;
      gap: 1.5rem;
      font-size: 0.875rem;
      color: #888;
    }

    .loading-state, .error-state, .empty-state {
      text-align: center;
      padding: 4rem 2rem;
      color: #888;
    }

    .spinner {
      width: 40px;
      height: 40px;
      margin: 0 auto 1rem;
      border: 4px solid #333;
      border-top-color: #4ecdc4;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .error-state button {
      margin-top: 1rem;
      padding: 0.75rem 1.5rem;
      background: #4ecdc4;
      color: #0a0a0a;
      border: none;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
    }

    .error-state button:hover {
      background: #44a08d;
    }
  `]
})
export class RenderDashboardPage implements OnInit {
  jobs = signal<RenderJob[]>([]);
  stats = signal({ queued: 0, generating: 0, complete: 0, abandoned: 0 });
  loading = signal(true);
  error = signal<string | null>(null);

  private readonly apiUrl = '/api/v1/render-jobs';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    // Poll every 5 seconds
    interval(5000)
      .pipe(
        startWith(0),
        switchMap(() => this.http.get<Page<RenderJob>>(`${this.apiUrl}?size=50`))
      )
      .subscribe({
        next: (page) => {
          this.jobs.set(page.content);
          this.updateStats(page.content);
          this.loading.set(false);
          this.error.set(null);
        },
        error: (err) => {
          this.error.set('Failed to load render jobs: ' + err.message);
          this.loading.set(false);
        }
      });
  }

  loadJobs() {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<Page<RenderJob>>(`${this.apiUrl}?size=50`).subscribe({
      next: (page) => {
        this.jobs.set(page.content);
        this.updateStats(page.content);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set('Failed to load render jobs: ' + err.message);
        this.loading.set(false);
      }
    });
  }

  private updateStats(jobs: RenderJob[]) {
    const stats = {
      queued: jobs.filter(j => j.status === 'QUEUED').length,
      generating: jobs.filter(j => ['GENERATING', 'POLLING', 'DOWNLOADING'].includes(j.status)).length,
      complete: jobs.filter(j => j.status === 'COMPLETE').length,
      abandoned: jobs.filter(j => j.status === 'ABANDONED').length
    };
    this.stats.set(stats);
  }

  getProgress(job: RenderJob): number {
    const statusProgress: Record<string, number> = {
      'QUEUED': 10,
      'GENERATING': 30,
      'POLLING': 60,
      'DOWNLOADING': 80,
      'COMPLETE': 100,
      'FAILED': 100,
      'ABANDONED': 100
    };
    return statusProgress[job.status] || 0;
  }

  getProgressLabel(job: RenderJob): string {
    const labels: Record<string, string> = {
      'QUEUED': 'Waiting in queue...',
      'GENERATING': 'Generating with OpenArt...',
      'POLLING': 'Waiting for generation...',
      'DOWNLOADING': 'Downloading asset...',
      'COMPLETE': 'Complete',
      'FAILED': 'Failed',
      'ABANDONED': 'Abandoned'
    };
    return labels[job.status] || job.status;
  }

  formatTime(isoString: string): string {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }
}
