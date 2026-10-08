import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, OnDestroy, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { formatStateShare, isStateShareDanger, isStateShareWarning } from './state-share';
import { toSpecializedApplicabilityRows } from './specialized-applicability';
import type { SpecializedApplicability } from './specialized-applicability';
import { TimelineChartComponent } from './timeline-chart.component';

interface PromptEditorInstance {
  getValue(): string;
  setValue(value: string): void;
  updateOptions(options: { readOnly: boolean }): void;
  layout(): void;
  onDidChangeModelContent(listener: () => void): { dispose(): void };
  dispose(): void;
}

const PROMPT_WORKSPACE_ROOT = 'library/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026';

interface QualityReport {
  overallScore: number;
  status: 'RENDER_READY' | 'NEEDS_REVISION' | 'BLOCKED' | 'SERVICE_ERROR';
  rulesetVersion: string;
  blockerCount: number;
  criticalCount: number;
  warningCount: number;
  familyScores: { [key: string]: number | null };
  familyAssessments: { [key: string]: FamilyAssessment };
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
  preRenderAssessment: PreRenderAssessment;
  videoPlanIr: Record<string, any>;
}

interface FamilyAssessment { status: string; score: number | null; evidenceCoverage: number; counts: Record<string, number>; reasons: string[]; }
interface PreRenderDimension { key: string; title: string; status: string; summary: string; observed: string; recommendation: string; evidence_status: string; }
interface FirstFrameAssessment { textual_intent: { status: string; reason: string; evidence?: Record<string, any> }; visual_verification: { status: string; reason: string }; silhouette_verification: { status: string; reason: string }; }
interface RenderAuthorization { status: string; final_video_render: string; creative_failures: string[]; pending_evidence_blockers: string[]; technical_failures: string[]; reason: string; }
interface Family7Aggregation { score: number | null; scoredCount: number; denominator: number; passCount: number; failCount: number; unknownCount: number; notEvaluatedCount: number; notApplicableCount: number; serviceErrorCount: number; evaluationCoverage: number | null; aggregationState: string; }
interface Family8Assessment { creativeQuality: { creativeScore: number | null; creativeGrade: string | null; familyScores: Record<string, number | null> }; evidenceCompleteness: { status: string; evaluationCoverage: number | null; aggregation: Record<string, any> }; renderAuthorization: { status: string; reasons: Array<{ code: string; source: string; message: string; references: string[] }> }; legacy: { grade?: string; readiness?: string }; }
interface PreRenderAssessment { name: string; family8?: Family8Assessment; aggregation?: Family7Aggregation | null; engine_profile?: Record<string, any>; story_structure?: Record<string, any>; temporal_complexity?: Record<string, any>; grade: string; creative_grade?: string | null; creative_score?: number | null; prompt_stage?: string; first_frame?: FirstFrameAssessment; render_authorization?: RenderAuthorization; evidence_completeness?: EvidenceCompleteness | null; specialized_applicability: Record<string, SpecializedApplicability>; readiness: string; assessment_coverage_percent: number; verdict: string; strengths: string[]; concerns: string[]; recommended_changes: string[]; dimensions: PreRenderDimension[]; stable_intent: string[]; provenance: Record<string, any>; }

interface LinkedValidationResponse { validationRecordId: number; report: QualityReport; }
interface StoredValidation { validationRecordId: number; report: QualityReport; analyzedAt: string; }

interface PromptFile {
  name: string;
  title?: string;
  relativePath: string;
  folder: string;
  sizeBytes: number | null;
  modifiedAt: string | null;
  contentId?: number;
  promptVersionId?: number;
  versionNumber?: number;
  rawText?: string;
  sourcePath?: string;
  latestQuality?: PromptQualitySummary | null;
}

interface PromptQualitySummary {
  validationRecordId: number;
  analyzedAt: string;
  rulesetVersion: string;
  overallScore: number;
  status: string;
  creativeGrade?: string | null;
  readiness?: string | null;
  summary?: string | null;
}

interface PromptQualityCard { sourcePath: string; title: string; contentId: number; promptVersionId: number; versionNumber: number; latestQuality?: PromptQualitySummary | null; }
interface PromptQualityRecord { contentId: number; title: string; sourcePath?: string | null; promptVersionId?: number | null; versionNumber?: number | null; latestQuality?: PromptQualitySummary | null; }

interface PromptDirectory { name: string; relativePath: string; promptCount: number; }
interface PromptWorkspace {
  creativeName: string;
  folderPath: string;
  videoCandidates: string[];
  selectedVideoPath: string | null;
  videoId: string | null;
  promptStatus: 'AVAILABLE' | 'NO_PROMPT' | 'AMBIGUOUS';
  promptCandidates: string[];
  promptRecords?: PromptQualityCard[];
  analysisStatus: string;
  modifiedAt: string | null;
}

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
  canonicalEvidenceVersion?: string;
  ruleEngineVersion: string;
  scoringVersion?: string;
  assessmentVersion?: string;
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
  /** PERCENT of the timeline (0-100), not a 0-1 ratio. See state-share.ts. */
  percentage: number;
}

interface EvidenceGap { rule_id: string; family: string; kind: string; message: string; }
interface CanonicalAttemptEvidence {
  count: number;
  activeAttemptCount: number;
  distinctStrategyCount: number;
  beat_ids: string[];
  verbs: string[];
  strategy_families: string[];
  active_seconds: number;
  active_ratio: number;
  sources: Record<string, number>;
  attempts: Array<Record<string, any>>;
}
interface EvidenceCompleteness {
  status: 'COMPLETE' | 'PARTIAL' | 'INCOMPLETE';
  coverage_percent: number;
  gaps: EvidenceGap[];
  unscored_families: { family: string; reason: string }[];
  partial_dimensions: string[];
  canonical_evidence: { beat_count: number; labelled_beats: number; beatAudit: Array<Record<string, any>>; attempts: CanonicalAttemptEvidence };
}

interface BeatEvidence { label: string; role: string; isAttempt: boolean; verb: string; source: string; }

@Component({
  selector: 'app-quality-validator',
  standalone: true,
  imports: [CommonModule, FormsModule, TimelineChartComponent, RouterLink],
  templateUrl: './quality-validator.component.html',
  styleUrls: ['./quality-validator.component.scss']
})
export class QualityValidatorComponent implements AfterViewInit, OnDestroy {
  @ViewChild('promptMonaco') private promptMonaco?: ElementRef<HTMLDivElement>;
  @ViewChild(TimelineChartComponent, { read: ElementRef }) private timelineChart?: ElementRef<HTMLElement>;
  private promptEditor: PromptEditorInstance | null = null;
  private updatingPromptEditor = false;
  exportingPdf = false;
  /** Set only when the shown report was restored from storage rather than freshly validated. */
  reportAnalyzedAt: string | null = null;
  private restoreRequestId = 0;
  prompt: string = '';
  contentTitle: string = '';
  contentType: string = 'SHORT';
  contentId: string = '';
  promptVersionId: string = '';
  validationRecordId: number | null = null;
  report: QualityReport | null = null;
  readonly toSpecializedApplicabilityRows = toSpecializedApplicabilityRows;
  loading: boolean = false;
  error: string | null = null;
  promptFiles: PromptFile[] = [];
  promptLibraryRoot = 'library/POMPOM_HILLS_PRODUCTION';
  promptDirectories: PromptDirectory[] = [];
  selectedPromptDirectory = '';
  promptDirectoriesLoading = false;
  importMessage = '';
  selectedPromptPath = '';
  promptFilesLoading = false;
  selectedPromptLoading = false;
  promptWorkspaces: PromptWorkspace[] = [];
  qualityRecords: PromptQualityRecord[] = [];
  qualityRecordsLoading = false;
  promptWorkspacesLoading = false;
  workspaceQuery = '';
  workspaceMenuOpen = false;
  detailMode = false;
  selectedWorkspace: PromptWorkspace | null = null;
  selectedWorkspacePaths: string[] = [];
  selectedWorkspaceVideoPath = '';
  videoDrafts: Record<string, string> = {};
  newFolderName = '';
  futureVideoName = '';
  creatingFolder = false;
  
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

  constructor(private http: HttpClient, private router: Router, private route: ActivatedRoute, private changeDetector: ChangeDetectorRef) {
    this.detailMode = this.route.snapshot.url.some(segment => segment.path === 'detail');
    this.loadPromptWorkspaces();
    this.loadQualityRecords();
    if (this.detailMode) this.loadLinkedPromptFromRoute();
  }

  private loadLinkedPromptFromRoute(): void {
    const contentId = Number(this.route.snapshot.queryParamMap.get('contentId'));
    const promptVersionId = Number(this.route.snapshot.queryParamMap.get('promptVersionId'));
    if (!Number.isInteger(contentId) || contentId <= 0 || !Number.isInteger(promptVersionId) || promptVersionId <= 0) return;
    this.selectedPromptLoading = true;
    this.http.get<any[]>(`/api/v1/intelligence/contents/${contentId}/prompt-versions`).subscribe({
      next: versions => {
        const version = versions.find(item => item.id === promptVersionId);
        if (!version) { this.error = 'Prompt version could not be found.'; this.selectedPromptLoading = false; return; }
        this.contentId = String(contentId); this.promptVersionId = String(promptVersionId); this.contentTitle = `Content #${contentId}`; this.contentType = 'REEL';
        this.setPromptText(version.rawText || ''); this.selectedPromptPath = version.sourcePath || ''; this.selectedPromptLoading = false;
        this.http.get<any>(`/api/v1/intelligence/contents/${contentId}`).subscribe({ next: content => { this.contentTitle = content.title || this.contentTitle; this.contentType = content.type || this.contentType; this.changeDetector.detectChanges(); }, error: () => this.changeDetector.detectChanges() });
        this.changeDetector.detectChanges(); this.restoreStoredReport();
      },
      error: response => { this.error = response.error?.message || 'Prompt version could not be loaded.'; this.selectedPromptLoading = false; this.changeDetector.detectChanges(); },
    });
  }

  openQualityRecord(record: PromptQualityRecord): void {
    const workspace = record.sourcePath ? this.promptWorkspaces.find(item => record.sourcePath?.startsWith(item.folderPath)) : null;
    if (workspace) {
      this.selectWorkspace(workspace, record.sourcePath || undefined, workspace.videoCandidates.length === 1 ? workspace.videoCandidates[0] : undefined);
      return;
    }
    if (record.promptVersionId) {
      this.router.navigate(['/quality/detail'], { queryParams: { contentId: record.contentId, promptVersionId: record.promptVersionId } });
    }
  }

  loadQualityRecords(): void {
    this.qualityRecordsLoading = true;
    this.http.get<PromptQualityRecord[]>('/api/v1/intelligence/contents/quality-summary').subscribe({
      next: records => { this.qualityRecords = records; this.qualityRecordsLoading = false; this.changeDetector.detectChanges(); },
      error: () => { this.qualityRecords = []; this.qualityRecordsLoading = false; },
    });
  }

  loadPromptWorkspaces(): void {
    this.promptWorkspacesLoading = true;
    this.http.get<PromptWorkspace[]>(`/api/v1/videos/prompt-workspaces?relativeDirectory=${encodeURIComponent(PROMPT_WORKSPACE_ROOT)}`).subscribe({
      next: workspaces => {
        this.promptWorkspaces = workspaces;
        this.promptWorkspacesLoading = false;
        const requestedFolder = this.route.snapshot.queryParamMap.get('workspace');
        const requestedPrompt = this.route.snapshot.queryParamMap.get('prompt') || undefined;
        const requestedWorkspace = requestedFolder ? workspaces.find(item => item.folderPath === requestedFolder) : null;
        if (requestedWorkspace && !this.selectedWorkspace) {
          this.selectedWorkspacePaths = [requestedWorkspace.folderPath];
          this.activateWorkspace(requestedWorkspace, requestedPrompt, undefined, false, false);
        }
        this.changeDetector.detectChanges();
      },
      error: response => { this.error = response.error?.message || 'Prompt workspaces could not be loaded.'; this.promptWorkspacesLoading = false; this.changeDetector.detectChanges(); },
    });
  }

  private normalizedSearch(value: string): string {
    return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  workspaceSearchText(item: PromptWorkspace): string {
    const records = (item.promptRecords || []).map(record => `${record.title} ${record.sourcePath}`).join(' ');
    return this.normalizedSearch(`${item.creativeName} ${item.folderPath} ${item.videoCandidates.join(' ')} ${item.promptCandidates.join(' ')} ${records}`);
  }

  filteredPromptWorkspaces(): PromptWorkspace[] {
    const query = this.normalizedSearch(this.workspaceQuery.trim());
    return this.promptWorkspaces.filter(item => !query || this.workspaceSearchText(item).includes(query));
  }

  openWorkspaceMenu(): void { this.workspaceMenuOpen = true; }
  toggleWorkspaceMenu(event: MouseEvent): void { event.stopPropagation(); this.workspaceMenuOpen = !this.workspaceMenuOpen; }
  closeWorkspaceMenu(): void { this.workspaceMenuOpen = false; }
  setWorkspaceQuery(event: Event): void { this.workspaceQuery = (event.target as HTMLInputElement).value; this.workspaceMenuOpen = true; }

  selectedPromptWorkspaces(): PromptWorkspace[] {
    const selected = new Set(this.selectedWorkspacePaths);
    return this.promptWorkspaces.filter(workspace => selected.has(workspace.folderPath));
  }

  isWorkspaceSelected(path: string): boolean { return this.selectedWorkspacePaths.includes(path); }
  toggleWorkspace(workspace: PromptWorkspace): void {
    if (this.isWorkspaceSelected(workspace.folderPath)) {
      this.selectedWorkspacePaths = this.selectedWorkspacePaths.filter(path => path !== workspace.folderPath);
      if (this.selectedWorkspace?.folderPath === workspace.folderPath) {
        const next = this.selectedPromptWorkspaces()[0] || null;
        this.selectedWorkspace = null;
        if (next) this.activateWorkspace(next, undefined, undefined, false, false);
      }
      return;
    }
    this.selectedWorkspacePaths = [...this.selectedWorkspacePaths, workspace.folderPath];
    if (!this.selectedWorkspace) this.activateWorkspace(workspace, undefined, undefined, false, false);
  }
  selectAllFilteredWorkspaces(): void {
    const paths = new Set(this.selectedWorkspacePaths);
    const filtered = this.filteredPromptWorkspaces();
    filtered.forEach(workspace => paths.add(workspace.folderPath));
    this.selectedWorkspacePaths = [...paths];
    if (!this.selectedWorkspace && filtered[0]) this.activateWorkspace(filtered[0], undefined, undefined, false, false);
  }
  clearWorkspaceSelection(): void { this.selectedWorkspacePaths = []; this.selectedWorkspace = null; this.selectedWorkspaceVideoPath = ''; }
  removeWorkspace(path: string): void {
    const workspace = this.promptWorkspaces.find(item => item.folderPath === path);
    if (workspace) this.toggleWorkspace(workspace);
  }

  ngAfterViewInit(): void {
    if (!this.promptMonaco) return;
    import('monaco-editor/esm/vs/editor/editor.api').then(monaco => {
      if (!this.promptMonaco) return;
      this.promptEditor = monaco.editor.create(this.promptMonaco.nativeElement, {
        value: this.prompt,
        language: 'markdown',
        theme: 'vs-light',
        automaticLayout: true,
        minimap: { enabled: false },
        wordWrap: 'on',
        lineNumbers: 'on',
        readOnly: false,
        padding: { top: 14, bottom: 14 },
        fontSize: 13,
        scrollBeyondLastLine: false,
      });
      this.promptEditor.onDidChangeModelContent(() => {
        if (!this.updatingPromptEditor) this.prompt = this.promptEditor?.getValue() || '';
      });
      window.setTimeout(() => this.promptEditor?.layout(), 0);
    });
  }

  ngOnDestroy(): void { this.promptEditor?.dispose(); }
  private setPromptText(value: string): void {
    this.prompt = value;
    if (this.promptEditor && this.promptEditor.getValue() !== value) {
      this.updatingPromptEditor = true;
      this.promptEditor.setValue(value);
      this.updatingPromptEditor = false;
      window.setTimeout(() => this.promptEditor?.layout(), 0);
    }
  }

  selectWorkspace(workspace: PromptWorkspace, promptPath?: string, videoPath?: string): void {
    if (!this.isWorkspaceSelected(workspace.folderPath)) this.selectedWorkspacePaths = [...this.selectedWorkspacePaths, workspace.folderPath];
    this.activateWorkspace(workspace, promptPath, videoPath, true, true);
  }

  private activateWorkspace(workspace: PromptWorkspace, promptPath?: string, videoPath?: string, scroll = true, navigate = false): void {
    const existingVideoSelection = this.selectedWorkspace?.folderPath === workspace.folderPath ? this.selectedWorkspaceVideoPath : '';
    this.selectedWorkspace = workspace;
    this.workspaceMenuOpen = false;
    this.selectedWorkspaceVideoPath = videoPath || existingVideoSelection || workspace.selectedVideoPath || '';
    if (this.selectedWorkspaceVideoPath) this.videoDrafts[workspace.folderPath] = this.selectedWorkspaceVideoPath;
    this.selectedPromptDirectory = workspace.folderPath;
    this.contentTitle = this.futureVideoName.trim() || workspace.creativeName;
    this.contentType = workspace.folderPath.includes('SOCIAL_REELS') ? 'REEL' : 'SHORT';
    this.contentId = '';
    this.promptVersionId = '';
    this.validationRecordId = null;
    this.report = null;
    this.error = null;
    if (navigate) {
      this.router.navigate(['/quality/detail'], { queryParams: { workspace: workspace.folderPath, ...(promptPath ? { prompt: promptPath } : {}) } });
    }
    const candidate = promptPath || (workspace.promptCandidates.length === 1 ? workspace.promptCandidates[0] : null);
    if (candidate) {
      this.selectPromptFile({ name: candidate.split('/').pop() || 'Prompt', relativePath: candidate, folder: this.promptFolder(candidate, workspace.folderPath), sizeBytes: null, modifiedAt: workspace.modifiedAt });
    } else {
      this.setPromptText('');
      this.selectedPromptPath = '';
    }
    if (scroll) window.setTimeout(() => document.getElementById('prompt-editor')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
  }

  openWorkspace(workspace: PromptWorkspace): void {
    if (workspace.promptStatus !== 'NO_PROMPT' && (workspace.videoCandidates.length > 1 || workspace.promptCandidates.length > 1)) return;
    this.selectWorkspace(workspace, workspace.promptCandidates[0], workspace.videoCandidates.length === 1 ? workspace.videoCandidates[0] : undefined);
  }

  chooseVideoCandidate(workspace: PromptWorkspace, value: string): void {
    this.videoDrafts[workspace.folderPath] = value;
    if (workspace.videoCandidates.includes(value)) this.selectWorkspace(workspace, undefined, value);
  }

  statusLabel(value: string): string { return value.replaceAll('_', ' '); }

  createWorkspaceFolder(): void {
    const name = this.newFolderName.trim();
    if (!name) return;
    this.creatingFolder = true;
    this.http.post<PromptWorkspace>('/api/v1/videos/prompt-workspaces/folders', { parentDirectory: PROMPT_WORKSPACE_ROOT, folderName: name }).subscribe({
      next: workspace => { this.creatingFolder = false; this.newFolderName = ''; this.promptWorkspaces = [workspace, ...this.promptWorkspaces]; this.selectWorkspace(workspace); },
      error: response => { this.creatingFolder = false; this.error = response.error?.message || 'Prompt workspace folder could not be created.'; },
    });
  }

  loadPromptDirectories(): void {
    this.promptDirectoriesLoading = true;
    this.error = null;
    this.http.get<PromptDirectory[]>(`/api/v1/videos/prompt-directories?relativeDirectory=${encodeURIComponent(this.promptLibraryRoot)}`).subscribe({
      next: directories => { this.promptDirectories = directories; this.promptDirectoriesLoading = false; },
      error: response => { this.error = response.error?.message || 'Prompt folders could not be loaded.'; this.promptDirectoriesLoading = false; },
    });
  }

  selectPromptDirectory(): void {
    this.promptFiles = [];
    this.selectedPromptPath = '';
    this.setPromptText('');
    this.importMessage = '';
    if (this.selectedPromptDirectory) this.loadPromptFiles();
  }

  loadPromptFiles(): void {
    if (!this.selectedPromptDirectory) { this.promptFiles = []; return; }
    this.promptFilesLoading = true;
    this.http.get<PromptFile[]>(`/api/v1/videos/prompt-files?relativeDirectory=${encodeURIComponent(this.selectedPromptDirectory)}`).subscribe({
      next: files => { this.promptFiles = files; this.promptFilesLoading = false; this.loadDbPromptLibrary(); },
      error: response => { this.error = response.error?.message || 'Project prompts could not be loaded.'; this.promptFilesLoading = false; },
    });
  }

  importSelectedFolder(): void {
    if (!this.selectedPromptDirectory) return;
    this.loading = true;
    this.importMessage = '';
    this.http.post<{ discovered: number; imported: number; unchanged: number }>('/api/v1/intelligence/contents/import-folder', { relativeDirectory: this.selectedPromptDirectory }).subscribe({
      next: result => { this.loading = false; this.importMessage = `${result.imported} prompt(s) imported to DB; ${result.unchanged} unchanged.`; this.loadDbPromptLibrary(); },
      error: response => { this.loading = false; this.error = response.error?.detail || response.error?.message || 'Prompt folder could not be imported.'; },
    });
  }

  loadDbPromptLibrary(): void {
    if (!this.selectedPromptDirectory) return;
    this.promptFilesLoading = true;
    this.http.get<PromptFile[]>(`/api/v1/intelligence/contents/prompt-library?sourceDirectory=${encodeURIComponent(this.selectedPromptDirectory)}`).subscribe({
      next: files => { if (files.length) this.promptFiles = files.map(file => ({ ...file, name: file.sourcePath?.split('/').pop() || file.title || 'Prompt', relativePath: file.sourcePath || '', folder: this.selectedPromptDirectory, sizeBytes: null, modifiedAt: null })); this.promptFilesLoading = false; },
      error: response => { this.error = response.error?.detail || response.error?.message || 'DB prompt library could not be loaded.'; this.promptFilesLoading = false; },
    });
  }

  selectPromptFile(file: PromptFile): void {
    this.selectedPromptPath = file.relativePath;
    this.selectedPromptLoading = true;
    this.error = null;
    if (file.rawText && file.contentId && file.promptVersionId) {
        this.setPromptText(file.rawText);
          this.contentTitle = this.futureVideoName.trim() || file.title || this.titleFromFolder(file.folder);
      this.contentType = file.folder.includes('SOCIAL_REELS') ? 'REEL' : 'SHORT';
      this.contentId = String(file.contentId);
        this.promptVersionId = String(file.promptVersionId);
        this.validationRecordId = null;
        this.report = null;
        this.selectedPromptLoading = false;
        this.changeDetector.detectChanges();
        this.restoreStoredReport();
      return;
    }
    this.http.get<PromptFile[]>(`/api/v1/intelligence/contents/prompt-library?sourceDirectory=${encodeURIComponent(file.folder)}`).subscribe({
      next: records => {
        const linked = records.find(record => record.sourcePath === file.relativePath);
        if (linked?.rawText && linked.contentId && linked.promptVersionId) {
          this.setPromptText(linked.rawText);
          this.contentTitle = this.futureVideoName.trim() || linked.title || this.titleFromFolder(file.folder);
          this.contentType = file.folder.includes('SOCIAL_REELS') ? 'REEL' : 'SHORT';
          this.contentId = String(linked.contentId);
          this.promptVersionId = String(linked.promptVersionId);
          this.validationRecordId = null;
          this.report = null;
          this.selectedPromptLoading = false;
          this.changeDetector.detectChanges();
          this.restoreStoredReport();
          return;
        }
        this.loadPromptFileFromFilesystem(file);
      },
      error: () => this.loadPromptFileFromFilesystem(file),
    });
  }

  private loadPromptFileFromFilesystem(file: PromptFile): void {
    this.http.get<{ relativePath: string; content: string }>(`/api/v1/videos/metadata?path=${encodeURIComponent(file.relativePath)}`).subscribe({
      next: result => {
        this.setPromptText(result.content);
        this.contentTitle = this.futureVideoName.trim() || this.titleFromFolder(file.folder);
        this.contentType = file.folder.includes('SOCIAL_REELS') ? 'REEL' : 'SHORT';
        this.contentId = '';
        this.promptVersionId = '';
        this.validationRecordId = null;
        this.report = null;
        this.selectedPromptLoading = false;
        this.changeDetector.detectChanges();
        this.restoreStoredReport();
      },
      error: response => { this.error = response.error?.message || 'Selected prompt could not be loaded.'; this.selectedPromptLoading = false; this.changeDetector.detectChanges(); },
    });
  }

  /** Shows the most recent stored analysis of the currently loaded prompt, if one exists. */
  private restoreStoredReport(): void {
    const linked = Boolean(this.contentId.trim() && this.promptVersionId.trim());
    const prompt = this.prompt;
    if (!linked && !prompt.trim()) return;

    const requestId = ++this.restoreRequestId;
    const payload = linked
      ? { contentId: Number(this.contentId), promptVersionId: Number(this.promptVersionId) }
      : { prompt };

    this.http.post<StoredValidation | null>('/api/v1/intelligence/quality/validations/latest', payload).subscribe({
      next: stored => {
        // Ignore stale answers: another prompt was selected, or a fresh validation already produced a report.
        if (!stored || requestId !== this.restoreRequestId || this.report || this.loading) return;
        this.report = stored.report;
        this.validationRecordId = linked ? stored.validationRecordId : null;
        this.reportAnalyzedAt = stored.analyzedAt;
        this.changeDetector.detectChanges();
      },
      error: err => console.warn('Previous analysis could not be loaded:', err),
    });
  }

  promptRecord(workspace: PromptWorkspace, path: string): PromptQualityCard | null {
    return workspace.promptRecords?.find(record => record.sourcePath === path) || null;
  }

  qualityState(record: { latestQuality?: PromptQualitySummary | null } | null): string {
    return record?.latestQuality ? 'ANALYZED' : 'NOT_ANALYZED';
  }

  promptQualitySummary(record: { latestQuality?: PromptQualitySummary | null } | null): string {
    const quality = record?.latestQuality;
    if (!quality) return 'No prompt quality analysis yet';
    return quality.summary || `${quality.status} · score ${quality.overallScore.toFixed(1)}`;
  }

  promptFolder(path: string, fallback: string): string {
    const lastSlash = path.lastIndexOf('/');
    return lastSlash > 0 ? path.slice(0, lastSlash) : fallback;
  }

  promptName(path: string): string {
    const folder = this.promptFolder(path, '');
    return folder.split('/').filter(Boolean).pop() || path.split('/').pop() || 'Prompt';
  }

  startNewPrompt(): void {
    this.setPromptText(''); this.contentTitle = ''; this.futureVideoName = ''; this.contentType = 'SHORT'; this.contentId = ''; this.promptVersionId = '';
    this.selectedPromptPath = ''; this.validationRecordId = null; this.report = null; this.error = null;
    if (!this.detailMode) {
      this.clearWorkspaceSelection();
      return;
    }
    this.router.navigate(['/quality']);
  }

  titleFromFolder(folder: string): string {
    const name = folder.split('/').filter(Boolean).pop() || 'New Pompom Video';
    return name.replaceAll('_', ' ').replace(/(^|\s)\S/g, letter => letter.toUpperCase());
  }


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
    this.promptEditor?.updateOptions({ readOnly: true });
    this.error = null;
    this.report = null;
    this.reportAnalyzedAt = null;
    this.restoreRequestId++;

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
        this.finishValidation();
      },
      error: (err) => {
        this.error = err.error?.message || 'Validation failed. Please try again.';
        this.finishValidation();
        console.error('Validation error:', err);
      }
    });
  }

  private finishValidation(): void {
    this.loading = false;
    this.promptEditor?.updateOptions({ readOnly: false });
    this.changeDetector.detectChanges();
  }

  exportQualityRecordPdf(record: PromptQualityRecord): void {
    if (!record.latestQuality || !record.promptVersionId || this.exportingPdf) return;
    this.exportingPdf = true; this.error = null;
    this.http.post<StoredValidation | null>('/api/v1/intelligence/quality/validations/latest', { contentId: record.contentId, promptVersionId: record.promptVersionId }).subscribe({
      next: stored => {
        if (!stored) { this.error = 'The stored quality report could not be loaded.'; this.exportingPdf = false; return; }
        this.http.post('/api/v1/intelligence/quality/report/export-pdf', {
          report: stored.report, title: record.title, validationRecordId: stored.validationRecordId, timelineChartPng: null,
        }, { responseType: 'blob' }).subscribe({
          next: blob => { this.downloadBlob(blob, `${this.slug(record.title)}-quality-report.pdf`); this.exportingPdf = false; },
          error: async response => { this.error = await this.exportErrorMessage(response); this.exportingPdf = false; },
        });
      },
      error: async response => { this.error = await this.exportErrorMessage(response); this.exportingPdf = false; },
    });
  }

  private slug(value: string): string {
    return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'pompom';
  }

  /** Asks the backend to render the current report as a PDF and downloads it directly. */
  async exportReportPdf(): Promise<void> {
    if (!this.report || this.exportingPdf) return;

    this.exportingPdf = true;
    this.error = null;
    this.changeDetector.detectChanges();

    const timelineChartPng = await this.captureTimelineChartPng();
    const payload = {
      report: this.report,
      title: this.contentTitle || null,
      validationRecordId: this.validationRecordId,
      timelineChartPng,
    };

    this.http.post('/api/v1/intelligence/quality/report/export-pdf', payload, { responseType: 'blob' }).subscribe({
      next: blob => {
        this.downloadBlob(blob, this.pdfFileName());
        this.exportingPdf = false;
        this.changeDetector.detectChanges();
      },
      error: async response => {
        this.error = await this.exportErrorMessage(response);
        this.exportingPdf = false;
        this.changeDetector.detectChanges();
      },
    });
  }

  private pdfFileName(): string {
    const slug = (this.contentTitle || 'pompom')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    return `${slug || 'pompom'}-quality-report.pdf`;
  }

  private downloadBlob(blob: Blob, fileName: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  private async exportErrorMessage(response: any): Promise<string> {
    const fallback = 'PDF export failed. Please try again.';
    if (response?.error instanceof Blob) {
      try {
        const problem = JSON.parse(await response.error.text());
        return problem.detail || problem.message || fallback;
      } catch {
        return fallback;
      }
    }
    return response?.error?.detail || response?.error?.message || fallback;
  }

  /** Rasterises the timeline SVG to a base64 PNG (2x) so the backend can embed it. Returns null on failure. */
  private async captureTimelineChartPng(): Promise<string | null> {
    const svg = this.timelineChart?.nativeElement.querySelector('svg.timeline-svg') as SVGSVGElement | null;
    if (!svg) return null;

    const viewBox = svg.viewBox.baseVal;
    const width = viewBox.width || 1200;
    const height = viewBox.height || 400;
    const scale = 2;

    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', String(width));
    clone.setAttribute('height', String(height));
    clone.setAttribute('font-family', 'Helvetica, Arial, sans-serif');
    const background = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    background.setAttribute('width', String(width));
    background.setAttribute('height', String(height));
    background.setAttribute('fill', '#ffffff');
    clone.insertBefore(background, clone.firstChild);

    const svgUrl = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' }));
    try {
      const image = await new Promise<HTMLImageElement>((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => reject(new Error('Timeline chart could not be rasterised'));
        img.src = svgUrl;
      });
      const canvas = document.createElement('canvas');
      canvas.width = width * scale;
      canvas.height = height * scale;
      const context = canvas.getContext('2d');
      if (!context) return null;
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('image/png');
    } catch (error) {
      console.warn('Timeline chart snapshot skipped:', error);
      return null;
    } finally {
      URL.revokeObjectURL(svgUrl);
    }
  }

  clearPrompt(): void {
    this.setPromptText('');
    this.report = null;
    this.error = null;
    this.validationRecordId = null;
  }

  loadSamplePrompt(): void {
    this.setPromptText(this.samplePrompt);
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

  getFamilyScoreClass(score: number | null): string {
    if (score === null || score === undefined) return 'family-score-unavailable';
    if (score >= 90) return 'family-score-excellent';
    if (score >= 75) return 'family-score-good';
    if (score >= 60) return 'family-score-acceptable';
    return 'family-score-poor';
  }

  getFamilyScoreEntries(): [string, number | null][] {
    if (!this.report?.familyScores) return [];
    return Object.entries(this.report.familyScores).sort((a, b) => {
      if (a[1] === null) return 1;
      if (b[1] === null) return -1;
      return b[1] - a[1];
    });
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

  /** `percent` is already 0-100 (the API contract); it is formatted, never multiplied by 100 again. */
  formatPercentage(percent: number): string {
    return formatStateShare(percent);
  }

  isStateShareWarning(percent: number): boolean {
    return isStateShareWarning(percent);
  }

  isStateShareDanger(percent: number): boolean {
    return isStateShareDanger(percent);
  }

  /** For values that are genuinely 0-1 ratios (for example attempt active_ratio). */
  formatRatioAsPercent(ratio: number): string {
    return `${(ratio * 100).toFixed(0)}%`;
  }

  /** Canonical per-beat evidence (label, role, attempt provenance) from the same parsed VideoPlanIR the rules used. */
  beatEvidence(beat: { startTime: number; endTime: number }): BeatEvidence | null {
    const beats = this.report?.videoPlanIr?.['beats'];
    if (!Array.isArray(beats)) return null;
    const match = beats.find(item => item?.startTime === beat.startTime && item?.endTime === beat.endTime);
    if (!match) return null;
    return {
      label: match.beatLabel || '',
      role: match.beatRole || '',
      isAttempt: !!match.isAttempt,
      verb: match.primaryVerb || '',
      source: match.attemptSource || '',
    };
  }

  /** A family with no evaluable evidence is "not evaluated", not a creative score of 0. */
  isUnscoredFamily(family: string): boolean {
    const assessment = this.report?.familyAssessments?.[family];
    if (assessment) return assessment.score === null || ['UNKNOWN', 'NOT_APPLICABLE', 'SERVICE_ERROR'].includes(assessment.status);
    const unscored = this.report?.preRenderAssessment?.evidence_completeness?.unscored_families;
    return !!unscored?.some(item => item.family === family);
  }

  renderQueueUrl(): string {
    return `/render?contentId=${encodeURIComponent(this.contentId)}&promptVersionId=${encodeURIComponent(this.promptVersionId)}&validationRecordId=${this.validationRecordId}`;
  }
}
