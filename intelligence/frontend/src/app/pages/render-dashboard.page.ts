import { Component, OnDestroy, OnInit, signal } from '@angular/core';
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
  creativeContractVersion?: string;
  creativeContractStatus?: string;
  compiledGenerationConstraints?: string;
  constraintCompilerVersion?: string;
  attempts?: Array<{
    id: string;
    attemptNumber: number;
    stage: string;
    providerJobId?: string;
    assetId?: string;
    startedAt?: string;
    completedAt?: string;
    errorCode?: string;
    errorMessage?: string;
  }>;
  qaResult?: {
    id: string;
    decision: string;
    decisionReason: string;
    complianceScore?: number;
    confidence?: number;
    hasDeadAir?: boolean;
    characterIdentityVerified?: boolean;
    characterIdentityIssues?: string;
    requiresHumanReview: boolean;
    evidenceVersion?: string;
    rulesetVersion?: string;
    humanDecision?: string;
    canonicalPostRender?: boolean;
  };
}

interface PostRenderRuleResult {
  ruleId: string;
  family: string;
  severity: string;
  outcome: string;
  message: string;
  actualValue: unknown;
  expectedCondition: unknown;
  evidenceReferences: unknown;
  reviewRequired: boolean;
}

interface PostRenderEvaluation {
  id: string;
  evidenceVersion: string;
  rulesetVersion: string;
  analyzerVersions: string;
  evidenceSnapshot?: string;
  decision: string;
  humanReviewRequired: boolean;
  humanDecision?: string;
  assessment?: {
    grade: string;
    decision: string;
    risk: string;
    recommendedAction: string;
    label: string;
    verdict: string;
    evidenceCoveragePercent: number;
    assessmentVersion: string;
    snapshot: {
      strengths?: string[];
      concerns?: string[];
      insights?: Array<{ title: string; detail: string; evidenceStatus: string }>;
      recommendation?: { experiment: string; hypothesis: string; measures: string[] };
    };
  };
  ruleResults: PostRenderRuleResult[];
  evidence?: any;
}

interface Page<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  size: number;
  number: number;
}

interface RenderAsset {
  id: string;
  renderJobId: string;
  contentId: number;
  assetType: string;
  relativePath: string;
  fileSizeBytes: number;
  durationMs?: number;
  width: number;
  height: number;
  frameRate?: number;
  codec?: string;
  downloadUrl?: string;
  downloadedAt: string;
  current: boolean;
  assetVersion: number;
  sha256?: string;
  mediaVerified: boolean;
  mock: boolean;
  quarantined: boolean;
  providerJobId?: string;
  source?: string;
  parentAssetId?: string;
  originalRelativePath?: string;
  originalFileSizeBytes?: number;
  originalWidth?: number;
  originalHeight?: number;
  finalWidth?: number;
  finalHeight?: number;
  processingStatus?: string;
  processingError?: string;
  creditsEstimated?: number;
  creditsActual?: number;
}

interface VisualEvidenceResponse {
  validationRecordId: number;
  visualEvidenceId: number;
  gate: string;
  status: string;
  firstFrameEligible: boolean;
  finalVideoEligible: boolean;
  visualEvidence: Record<string, any>;
  created: boolean;
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
            <h1>Render Jobs</h1>
            <p class="subtitle">Monitor render jobs, QA results, and production status</p>
            <span class="live-indicator">Live stream: {{ liveState() }}</span>
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
              <div class="stat-label">Failed / abandoned</div>
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
              <p>No render jobs yet.</p><a href="/quality">Resume a creative project</a>
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



                @if (job.creativeContractStatus) {
                  <div class="production-contract-summary">
                    <div>
                      <span class="contract-eyebrow">CREATIVE PRODUCTION CONTRACT</span>
                      <strong>{{ job.creativeContractStatus }}</strong>
                      <small>{{ job.creativeContractVersion }} · {{ job.constraintCompilerVersion || 'No compiler snapshot' }}</small>
                    </div>
                    @if (job.compiledGenerationConstraints) {
                      <details>
                        <summary>View compiled generation constraints</summary>
                        <pre>{{ job.compiledGenerationConstraints }}</pre>
                      </details>
                    }
                  </div>
                }

                @if (job.qaResult) {
                  <div class="qa-results" [class.requires-review]="job.qaResult.requiresHumanReview">
                    <div class="qa-header">
                      <h4>{{ job.qaResult.canonicalPostRender ? 'Post-Render QA' : 'Legacy QA' }}</h4>
                      <span [class]="'qa-decision qa-' + job.qaResult.decision.toLowerCase()">
                        {{ job.qaResult.decision }}
                      </span>
                    </div>
                    <div class="qa-details">
                      @if (job.qaResult.canonicalPostRender) {
                        <div class="qa-metrics">
                          <div class="metric"><span class="metric-label">Ruleset</span><span class="metric-value">{{ job.qaResult.rulesetVersion }}</span></div>
                          <div class="metric"><span class="metric-label">Evidence</span><span class="metric-value">{{ job.qaResult.evidenceVersion }}</span></div>
                          @if (job.qaResult.humanDecision) { <div class="metric"><span class="metric-label">Human decision</span><span class="metric-value">{{ job.qaResult.humanDecision }}</span></div> }
                        </div>
                        <button type="button" class="details-button" (click)="loadPostRenderDetails(job.qaResult.id)">
                          {{ postRenderDetails()?.id === job.qaResult.id ? 'Hide assessment' : 'View assessment' }}
                        </button>
                        @if (postRenderDetails()?.id === job.qaResult.id) {
                          @if (postRenderDetails()?.assessment; as assessment) {
                            <section class="post-render-assessment">
                              <div class="assessment-heading">
                                <div><span class="metric-label">Post-render assessment</span><strong>{{ assessment.label }}</strong><small>{{ assessment.decision }} · risk {{ assessment.risk }} · {{ assessment.recommendedAction }}</small></div>
                                <span class="assessment-grade grade-{{ assessment.grade.toLowerCase() }}">Grade {{ assessment.grade }}</span>
                              </div>
                              <p class="assessment-verdict">{{ assessment.verdict }}</p>
                              <div class="assessment-meta"><span>Evidence coverage {{ assessment.evidenceCoveragePercent }}%</span><span>{{ assessment.assessmentVersion }}</span></div>
                              <div class="assessment-columns">
                                <div><h5>Strengths</h5><ul>@for (item of assessment.snapshot.strengths ?? []; track item) { <li>{{ item }}</li> }</ul></div>
                                <div><h5>Concerns</h5><ul>@for (item of assessment.snapshot.concerns ?? []; track item) { <li>{{ item }}</li> }</ul></div>
                              </div>
                              @if (assessment.snapshot.recommendation; as recommendation) {
                                <div class="assessment-recommendation"><h5>Recommended experiment</h5><strong>{{ recommendation.experiment }}</strong><p>{{ recommendation.hypothesis }}</p></div>
                              }
                              <div class="assessment-insights">@for (insight of assessment.snapshot.insights ?? []; track insight.title) { <div><strong>{{ insight.title }}</strong><p>{{ insight.detail }}</p></div> }</div>
                            </section>
                          }
                          @if (postRenderDetails()?.evidence; as evidence) {
                            <section class="post-render-assessment">
                              <h4>Rendered video QC: {{ evidence.videoQc?.storyStatus || 'STORY_QC_NOT_EVALUATED' }} / {{ evidence.videoQc?.status || 'VIDEO_QC_NOT_EVALUATED' }}</h4>
                              @if (evidence.videoQc?.approvalBlocked !== false) {
                                <p>Production approval is blocked until every mandatory visual check passes.</p>
                              }
                              @for (check of evidence.videoQc?.checks ?? []; track check.id) {
                                <p><strong>{{ check.id }} · {{ check.status }}</strong>
                                  @if (check.timestampsSeconds?.length) { <span> · {{ check.timestampsSeconds.join(', ') }}s</span> }
                                  @else if (check.window) { <span> · {{ check.window[0] }}–{{ check.window[1] }}s</span> }
                                  <br>{{ check.reason }}</p>
                              }
                              @if (evidence.videoQc?.reason) { <p>{{ evidence.videoQc.reason }}</p> }
                            </section>
                            <section class="evidence-structure">
                              <div class="assessment-heading"><div><span class="metric-label">V4 creative evidence</span><strong>Plan, render and recurrence</strong></div></div>
                              <div class="evidence-structure__grid">
                                <div><span class="metric-label">Action / beat novelty</span><strong>{{ evidence.temporal?.actionBeatNovelty?.status || evidence.actionBeatNovelty?.status || '—' }}</strong><p>Planned: {{ evidence.temporal?.actionBeatNovelty?.planned || evidence.temporal?.plannedActionNovelty?.status || '—' }} · Observed visually: {{ evidence.temporal?.actionBeatNovelty?.observedVisually || evidence.temporal?.observedVisualBeatNovelty?.status || '—' }}</p><small>Semantic action identity: {{ evidence.temporal?.actionBeatNovelty?.semanticActionStatus || 'NOT_EVALUATED' }}</small></div>
                                <div><span class="metric-label">Plan → render fidelity</span><strong>{{ evidence.temporal?.planRenderFidelity?.status || evidence.planRenderFidelity?.status || '—' }}</strong><p>{{ evidence.temporal?.planRenderFidelity?.reason || evidence.planRenderFidelity?.reason || 'No fidelity explanation available.' }}</p><small>Coverage: {{ evidence.temporal?.planRenderFidelity?.coverage ?? '—' }}%</small></div>
                                <div><span class="metric-label">Repetition</span><strong>{{ evidence.temporal?.profile?.repetitiveMotion?.classification || evidence.repetitiveMotion?.classification || '—' }}</strong><p>{{ evidence.temporal?.profile?.repetitiveMotion?.interpretation || evidence.repetitiveMotion?.interpretation || 'No repetition summary available.' }}</p><small>Recurrence: {{ evidence.temporal?.profile?.recurrence?.detected ? 'detected' : 'not established' }}</small></div>
                                <div><span class="metric-label">Motion measurement</span><strong>{{ evidence.temporal?.profile?.saturationDiagnostics?.warning ? 'Limited discrimination' : 'Available' }}</strong><p>{{ evidence.temporal?.profile?.saturationDiagnostics?.warning ? 'Normalization is saturating across a large part of the timeline.' : 'No widespread normalization saturation was detected.' }}</p><small>Clipped intervals: {{ evidence.temporal?.profile?.saturationDiagnostics?.overallClippedRatio ?? '—' }}</small></div>
                              </div>
                            </section>
                          }
                          <h5 class="rule-results-title">Rule results</h5>
                          <div class="rule-results">
                            @for (rule of postRenderDetails()?.ruleResults ?? []; track rule.ruleId) {
                              <div class="rule-result" [class.rule-failed]="rule.outcome !== 'PASS'">
                                <div class="rule-result-heading">
                                  <strong>{{ rule.ruleId }}</strong>
                                  <span>{{ rule.outcome }}</span>
                                </div>
                                <div class="rule-result-meta">{{ rule.family }} · {{ rule.severity }}{{ rule.reviewRequired ? ' · review required' : '' }}</div>
                                <p>{{ rule.message }}</p>
                                <code>actual={{ formatRuleValue(rule.actualValue) }} · expected={{ formatRuleValue(rule.expectedCondition) }}</code>
                              </div>
                            }
                          </div>
                        }
                      } @else {
                      <div class="qa-metrics">
                        <div class="metric">
                          <span class="metric-label">Compliance</span>
                          <div class="metric-value-bar">
                            <div class="compliance-bar">
                              <div class="compliance-fill" 
                                   [style.width.%]="job.qaResult.complianceScore"
                                   [class.low]="(job.qaResult.complianceScore ?? 0) < 70"></div>
                            </div>
                            <span class="metric-value">{{ job.qaResult.complianceScore ?? '—' }}%</span>
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
                      </div> }
                      <div class="qa-reason">
                        <p>{{ job.qaResult.decisionReason }}</p>
                      </div>
                      @if (job.qaResult.requiresHumanReview) {
                        <div class="human-review-alert">
                          <strong>⚠️ Requires Human Review</strong>
                          @if (job.qaResult.characterIdentityIssues) {
                            <p>{{ job.qaResult.characterIdentityIssues }}</p>
                          }
                          <div class="review-controls">
                            <input type="text" placeholder="Reviewer" [value]="reviewer()" (input)="reviewer.set(($any($event.target)).value)" />
                            <input type="password" placeholder="QA review token" [value]="reviewToken()" (input)="reviewToken.set(($any($event.target)).value)" />
                            <input type="text" placeholder="Decision notes" [value]="reviewNotes()" (input)="reviewNotes.set(($any($event.target)).value)" />
                            <div class="review-actions">
                              <button type="button" (click)="decideQa(job, 'APPROVED')" [disabled]="reviewingQa() === job.id || !canApproveVideoQc(job)">Approve</button>
                              <button type="button" (click)="decideQa(job, 'REJECTED')" [disabled]="reviewingQa() === job.id">Reject</button>
                              <button type="button" (click)="decideQa(job, 'RERENDER_REQUESTED')" [disabled]="reviewingQa() === job.id">Request rerender</button>
                            </div>
                          </div>
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

                @if (job.attempts?.length) {
                  <div class="attempt-history">
                    <strong>Attempt history</strong>
                    @for (attempt of job.attempts; track attempt.id) {
                      <span class="attempt-row">
                        <span>#{{ attempt.attemptNumber }}</span>
                        <span>{{ attempt.stage }}</span>
                        @if (attempt.errorCode) { <span>{{ attempt.errorCode }}</span> }
                        @if (attempt.assetId) { <button type="button" (click)="loadAsset(attempt.assetId)">Asset detail</button> }
                      </span>
                    }
                  </div>
                }

                <div class="job-footer">
                  <div class="job-times">
                    <span>Queued: {{ formatTime(job.queuedAt) }}</span>
                    @if (job.completedAt) {
                      <span>Completed: {{ formatTime(job.completedAt) }}</span>
                    }
                  </div>
                  <div class="job-actions">
                    @if (['QUEUED', 'GENERATING', 'POLLING', 'DOWNLOADING'].includes(job.status)) { <button type="button" (click)="cancelRender(job)" [disabled]="jobAction() === job.id">{{ jobAction() === job.id ? 'Cancelling…' : 'Cancel render' }}</button> }
                    @if (['FAILED', 'ABANDONED'].includes(job.status)) { <button type="button" (click)="retryRender(job)" [disabled]="jobAction() === job.id || job.attemptNumber >= job.maxAttempts">{{ jobAction() === job.id ? 'Retrying…' : 'Retry render' }}</button> }
                  </div>
                </div>
              </div>
            }
            <div class="pagination-bar"><span>Page {{ pageNumber() + 1 }} of {{ totalPages() || 1 }} · {{ totalElements() }} total jobs</span><div><button type="button" [disabled]="pageNumber() === 0 || loading()" (click)="loadJobs(pageNumber() - 1)">Previous</button><button type="button" [disabled]="pageNumber() + 1 >= totalPages() || loading()" (click)="loadJobs(pageNumber() + 1)">Next</button></div></div>
          }
        </div>
      </div>
      @if (assetLoading()) { <section class="section-band asset-detail"><span class="spinner"></span><strong>Loading render asset</strong></section> }
      @else if (assetError()) { <section class="section-band asset-detail"><strong>Asset detail unavailable</strong><p>{{ assetError() }}</p></section> }
      @else if (asset(); as item) { <section class="section-band asset-detail"><div class="section-heading"><div><span class="eyebrow">DURABLE ASSET</span><h2>{{ item.assetType }} · version {{ item.assetVersion }}</h2></div><span class="status-badge">{{ item.mediaVerified ? 'MEDIA VERIFIED' : 'NOT VERIFIED' }}</span></div>@if (item.assetType === 'VIDEO') { <video class="asset-preview" controls preload="metadata" [src]="assetMediaUrl(item)"></video> } @else if (item.assetType === 'FIRST_FRAME') { <img class="asset-preview" [src]="assetMediaUrl(item)" [alt]="item.relativePath" /> }<dl class="compact-facts"><div><dt>Path</dt><dd><code>{{ item.relativePath }}</code></dd></div><div><dt>Dimensions</dt><dd>{{ item.width }} × {{ item.height }}</dd></div><div><dt>Original</dt><dd>{{ item.originalWidth || item.width }} × {{ item.originalHeight || item.height }}</dd></div><div><dt>Codec</dt><dd>{{ item.codec || '—' }}</dd></div><div><dt>SHA-256</dt><dd><code>{{ item.sha256 || '—' }}</code></dd></div><div><dt>Quarantine</dt><dd>{{ item.quarantined ? 'QUARANTINED' : 'Clear' }}</dd></div></dl><div class="asset-actions"><a class="queue-button" [href]="assetDownloadUrl(item)">Download HD</a>@if (item.originalRelativePath) { <a class="queue-button" [href]="assetDownloadUrl(item, true)">Download original</a> }</div></section> }
      @if (asset()?.assetType === 'FIRST_FRAME') {
        <section class="section-band visual-evidence-panel">
          <div class="section-heading"><div><span class="eyebrow">VISUAL EVIDENCE</span><h2>Verify first-frame gates</h2></div><span class="status-badge">EXPLICIT VERIFIER RESULT REQUIRED</span></div>
          <p class="muted">Asset existence never becomes PASS automatically. Submit a human or vision-verifier result for each gate. Use the same evidence set for FIRST_FRAME and SILHOUETTE.</p>
          <div class="queue-fields visual-evidence-fields">
            <label>Gate<select [value]="visualGate()" (change)="visualGate.set(($any($event.target)).value)"><option value="FIRST_FRAME">FIRST_FRAME</option><option value="SILHOUETTE">SILHOUETTE</option></select></label>
            <label>Status<select [value]="visualStatus()" (change)="visualStatus.set(($any($event.target)).value)"><option value="PENDING">PENDING</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option><option value="UNKNOWN">UNKNOWN</option></select></label>
            <label>Evidence set ID<input type="text" [value]="visualEvidenceSetId()" (input)="visualEvidenceSetId.set(($any($event.target)).value)" /></label>
            <label>Verifier<input type="text" [value]="visualVerifier()" (input)="visualVerifier.set(($any($event.target)).value)" /></label>
            <label>Verification ID<input type="text" [value]="visualVerificationId()" (input)="visualVerificationId.set(($any($event.target)).value)" /></label>
            <label class="wide-field">Reason<textarea [value]="visualReason()" (input)="visualReason.set(($any($event.target)).value)"></textarea></label>
            <button type="button" class="queue-button" [disabled]="visualSubmitting()" (click)="submitVisualEvidence()">{{ visualSubmitting() ? 'Submitting…' : 'Submit visual result' }}</button>
          </div>
          @if (visualEvidenceError()) { <p class="queue-error">{{ visualEvidenceError() }}</p> }
          @if (visualEvidenceResult(); as result) { <p class="queue-success">{{ result.gate }} {{ result.status }} · Final video eligible: {{ result.finalVideoEligible ? 'YES' : 'NO' }}</p> }
        </section>
      }
    </div>
  `,
  styleUrl: './render-dashboard.page.scss',
})
export class RenderDashboardPage implements OnInit, OnDestroy {
  jobs = signal<RenderJob[]>([]);
  stats = signal({ queued: 0, generating: 0, complete: 0, abandoned: 0 });
  loading = signal(true);
  error = signal<string | null>(null);
  pageNumber = signal(0);
  totalPages = signal(0);
  totalElements = signal(0);
  liveState = signal('CONNECTING');
  liveUpdate = signal('');
  asset = signal<RenderAsset | null>(null);
  assetLoading = signal(false);
  assetError = signal('');
  reviewer = signal('local-user');
  reviewToken = signal('');
  reviewNotes = signal('');
  reviewingQa = signal<string | null>(null);
  jobAction = signal<string | null>(null);
  postRenderDetails = signal<PostRenderEvaluation | null>(null);
  visualGate = signal('FIRST_FRAME');
  visualStatus = signal('PENDING');
  visualEvidenceSetId = signal(crypto.randomUUID());
  visualVerifier = signal('local-user');
  visualVerificationId = signal('');
  visualReason = signal('');
  visualSubmitting = signal(false);
  visualEvidenceError = signal('');
  visualEvidenceResult = signal<VisualEvidenceResponse | null>(null);
  private readonly apiUrl = '/api/v1/render-jobs';
  private notificationStream: EventSource | null = null;

  constructor(private http: HttpClient) {}

  loadAsset(id: string) {
    this.assetLoading.set(true); this.assetError.set(''); this.asset.set(null); this.visualEvidenceError.set(''); this.visualEvidenceResult.set(null); this.visualEvidenceSetId.set(crypto.randomUUID());
    this.http.get<RenderAsset>(`/api/v1/render-assets/${id}`).subscribe({
      next: asset => { this.asset.set(asset); this.assetLoading.set(false); },
      error: err => { this.assetError.set(err.error?.detail || err.error?.message || 'The render asset could not be read.'); this.assetLoading.set(false); },
    });
  }

  assetMediaUrl(asset: RenderAsset, original = false): string {
    return `/api/v1/render-assets/${asset.id}/${original ? 'original' : 'media'}`;
  }

  assetDownloadUrl(asset: RenderAsset, original = false): string {
    return `/api/v1/render-assets/${asset.id}/${original ? 'original/download' : 'download'}`;
  }

  submitVisualEvidence(): void {
    const asset = this.asset();
    if (!asset || asset.assetType !== 'FIRST_FRAME') return;
    if (!this.visualReason().trim() || !this.visualVerifier().trim()) {
      this.visualEvidenceError.set('Verifier and reason are required.');
      return;
    }
    if (['PASS', 'FAIL'].includes(this.visualStatus()) && (!asset.sha256 || !this.visualVerificationId().trim())) {
      this.visualEvidenceError.set('PASS/FAIL requires the canonical asset SHA-256 and verification ID.');
      return;
    }
    this.visualSubmitting.set(true); this.visualEvidenceError.set(''); this.visualEvidenceResult.set(null);
    this.http.post<VisualEvidenceResponse>(`/api/v1/render-assets/${asset.id}/visual-evidence`, {
      gate: this.visualGate(), status: this.visualStatus(), evidenceSetId: this.visualEvidenceSetId(),
      provenance: { kind: 'HUMAN_VERIFICATION', verifier: this.visualVerifier().trim(), method: 'render-dashboard-visual-review' },
      reason: this.visualReason().trim(), verificationId: this.visualVerificationId().trim() || null,
      verifiedAt: new Date().toISOString(), submissionKey: crypto.randomUUID(),
    }).subscribe({
      next: result => { this.visualSubmitting.set(false); this.visualEvidenceResult.set(result); },
      error: err => { this.visualSubmitting.set(false); this.visualEvidenceError.set(err.error?.detail || err.error?.message || 'Visual evidence could not be submitted.'); },
    });
  }

  cancelRender(job: RenderJob): void {
    this.jobAction.set(job.id);
    this.http.post(`/api/v1/render-jobs/${job.id}/cancel`, {}).subscribe({
      next: () => { this.jobAction.set(null); this.loadJobs(this.pageNumber()); },
      error: err => { this.jobAction.set(null); this.error.set(err.error?.detail || err.error?.message || 'Render could not be cancelled.'); },
    });
  }

  retryRender(job: RenderJob): void {
    this.jobAction.set(job.id);
    this.http.post(`/api/v1/render-jobs/${job.id}/retry`, {}).subscribe({
      next: () => { this.jobAction.set(null); this.loadJobs(this.pageNumber()); },
      error: err => { this.jobAction.set(null); this.error.set(err.error?.detail || err.error?.message || 'Render could not be retried.'); },
    });
  }

  decideQa(job: RenderJob, decision: 'APPROVED' | 'REJECTED' | 'RERENDER_REQUESTED'): void {
    if (decision === 'APPROVED' && !this.canApproveVideoQc(job)) {
      this.error.set('Inspect the video QC evidence; mandatory visual checks must pass before approval.');
      return;
    }
    if (!job.qaResult?.id || !this.reviewToken().trim()) {
      this.error.set('Enter the configured QA review token before submitting a decision.');
      return;
    }
    this.reviewingQa.set(job.id);
    const reviewPath = job.qaResult.canonicalPostRender
      ? `/api/v1/qa/reviews/post-render/${job.qaResult.id}/decision`
      : `/api/v1/qa/reviews/${job.qaResult.id}/decision`;
    this.http.post(reviewPath, {
      decision,
      reviewer: this.reviewer().trim() || 'local-user',
      notes: this.reviewNotes().trim(),
    }, { headers: { 'X-QA-Review-Token': this.reviewToken().trim() } }).subscribe({
      next: () => { this.reviewingQa.set(null); this.reviewNotes.set(''); this.loadJobs(this.pageNumber()); },
      error: err => { this.reviewingQa.set(null); this.error.set(err.error?.detail || err.error?.message || 'QA decision could not be saved.'); },
    });
  }

  canApproveVideoQc(job: RenderJob): boolean {
    if (job.jobType !== 'VIDEO') return true;
    const details = this.postRenderDetails();
    return details?.id === job.qaResult?.id
      && details?.evidence?.videoQc?.storyStatus === 'STORY_QC_PASS'
      && details?.evidence?.videoQc?.status === 'VIDEO_QC_PASS'
      && details?.evidence?.videoQc?.approvalBlocked === false;
  }

  loadPostRenderDetails(evaluationId: string): void {
    if (this.postRenderDetails()?.id === evaluationId) {
      this.postRenderDetails.set(null);
      return;
    }
    this.http.get<PostRenderEvaluation>(`/api/v1/post-render/evaluations/${evaluationId}`).subscribe({
      next: details => this.postRenderDetails.set({ ...details, evidence: this.parseEvidence(details.evidenceSnapshot) }),
      error: err => this.error.set(err.error?.detail || err.error?.message || 'Post-render rule results could not be loaded.'),
    });
  }

  private parseEvidence(value: string | undefined): any {
    if (!value) return null;
    try { return JSON.parse(value); } catch { return null; }
  }

  formatRuleValue(value: unknown): string {
    if (value === null || value === undefined) return '—';
    if (typeof value === 'string') return value;
    try { return JSON.stringify(value); } catch { return String(value); }
  }


  private pollingSubscription?: import('rxjs').Subscription;
  ngOnInit() {
    this.connectLiveNotifications();
    this.pollingSubscription = interval(5000).pipe(startWith(0), switchMap(() => this.http.get<Page<RenderJob>>(`${this.apiUrl}?page=${this.pageNumber()}&size=50`))).subscribe({
      next: page => { this.jobs.set(page.content); this.pageNumber.set(page.number); this.totalPages.set(page.totalPages); this.totalElements.set(page.totalElements); this.updateStats(page.content); this.loading.set(false); this.error.set(null); },
      error: err => { this.error.set('Failed to load render jobs: ' + err.message); this.loading.set(false); }
    });
  }

  ngOnDestroy() {
    this.notificationStream?.close();
    this.pollingSubscription?.unsubscribe();
  }

  private connectLiveNotifications(): void {
    if (typeof EventSource === 'undefined') { this.liveState.set('UNAVAILABLE'); return; }
    this.notificationStream = new EventSource('/api/v1/sse/notifications');
    this.notificationStream.onopen = () => this.liveState.set('CONNECTED');
    this.notificationStream.onmessage = () => { this.liveState.set('CONNECTED'); this.liveUpdate.set(new Date().toLocaleTimeString()); this.loadJobs(this.pageNumber()); };
    this.notificationStream.onerror = () => this.liveState.set('RECONNECTING');
  }

  loadJobs(page = this.pageNumber()) {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<Page<RenderJob>>(`${this.apiUrl}?page=${page}&size=50`).subscribe({
      next: (page) => {
        this.jobs.set(page.content);
        this.pageNumber.set(page.number); this.totalPages.set(page.totalPages); this.totalElements.set(page.totalElements);
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
      abandoned: jobs.filter(j => ['FAILED','ABANDONED'].includes(j.status)).length
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
