import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { forkJoin, map, Observable } from 'rxjs';

export type Platform = 'Instagram' | 'YouTube' | 'TikTok' | 'Unknown';
export type VideoState = 'Observed' | 'Testing' | 'Queued' | 'Ingested';

export interface VideoRecord {
  id: string;
  title: string;
  format: string;
  character: string;
  platform: Platform;
  state: VideoState;
  hookRate: number;
  completion: number;
  views: number;
  published: string;
}

export interface PredictionRecord {
  id: string;
  videoId: string;
  video: string;
  platform: Platform;
  state: 'DRAFT' | 'LOCKED' | 'EVALUATED';
  predicted: number | null;
  range: string;
  sample: number;
  model: string;
  lockedAt: string;
  datasetVersion: string;
  featureVersion: string;
  knowledgeCutoff: string;
  predictionType: string;
}

export interface ExperimentRecord {
  id: string;
  videoId: string;
  variantId: string | null;
  platform: string;
  hypothesis: string;
  experimentType: string;
  plannedPublishTime: string | null;
  status: string;
}

export interface CreateExperimentRequest {
  videoId: string;
  variantId?: string | null;
  platform: string;
  hypothesis: string;
  experimentType: string;
  plannedPublishTime?: string | null;
  testVariables?: Record<string, unknown>;
  notes?: string;
}

export interface TestPlannerView {
  recommendedAllocation: Record<string, number>;
  currentExperimentCounts: Record<string, number>;
  charactersWithoutTests: number;
  guardrails: string[];
}

export interface ModelVersionRecord {
  id: string;
  version: string;
  modelType: string;
  platform: string;
  trainingDatasetVersion: string;
  featureVersion: string;
  knowledgeCutoff: string;
  metrics: Record<string, unknown>;
  artifactPath: string | null;
  status: 'CHALLENGER' | 'CHAMPION' | 'RETIRED' | string;
  trainedAt: string;
}

export interface ReliabilityRecord {
  id: string;
  predictionId: string;
  modelVersion: string;
  platform: string;
  horizonMinutes: number;
  actualValue: number | null;
  absoluteError: number | null;
  logError: number | null;
  interval50Covered: boolean | null;
  interval80Covered: boolean | null;
  brierScore: number | null;
  evaluatedAt: string;
}

export interface VideoApiRecord {
  id: string;
  originalFilename: string;
  relativePath: string;
  durationMs: number;
  width: number;
  height: number;
  fps: number;
  aspectRatio: number;
  codec: string;
  audioPresent: boolean;
  status: string;
  ingestedAt: string;
}

interface VideoPage { content: VideoApiRecord[]; }

export interface DirectoryIngestResult {
  relativeDirectory: string;
  discovered: number;
  ingested: VideoApiRecord[];
  errors: Array<{ relativePath: string; message: string }>;
}
export interface MediaDirectory { name: string; relativePath: string; videoCount: number; }
export interface MediaFile {
  name: string;
  relativePath: string;
  sizeBytes: number | null;
  modifiedAt: string | null;
  ingested: boolean;
  videoId: string | null;
  status: string | null;
  variantId: string | null;
}

export type VariantType = 'ORIGINAL' | 'HOOK_COLD_OPEN' | 'TRIMMED' | 'NO_CTA' | 'LOOP_CUT' | 'CUSTOM_EDIT';

export interface VideoVariant {
  id: string;
  videoId: string;
  parentVariantId: string | null;
  variantType: string;
  generatedPath: string;
  editOperations: unknown[];
  createdAt: string;
}

export interface CreateVariantRequest {
  parentVariantId: string | null;
  variantType: VariantType;
  generatedPath: string;
  editOperations: unknown[];
}

interface PredictionApiRecord {
  id: string;
  videoId: string;
  platform: string;
  status: 'DRAFT' | 'LOCKED' | 'EVALUATED';
  modelVersion: string;
  payload: { targets?: Array<{ expectedValue?: number | null; interval80?: Array<number | null> }> };
  comparableSampleSize: number;
  lockedAt?: string | null;
  predictionType?: string;
  datasetVersion: string;
  featureVersion: string;
  knowledgeCutoff: string;
}

export interface ImportPreview {
  batchId: string;
  filename: string;
  columns: string[];
  rowCount: number;
  matchedRows: number;
  unresolvedRows: number;
  duplicate: boolean;
  status: string;
}

export interface ImportRow {
  id: string;
  sheetName: string;
  sourceRowNumber: number;
  rawData: Record<string, string>;
  matchedVideoId: string | null;
  matchStatus: string;
  matchConfidence: number | null;
}

export interface OverviewData {
  source: 'api';
  videos: VideoRecord[];
  predictions: PredictionRecord[];
}

export interface CharacterCoverage {
  id: string;
  name: string;
  status: string;
  observations: number;
  formatObservations: Record<string, number>;
  confidence: 'NO_DATA' | 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface CharacterIdentity {
  id: string;
  name: string;
  status: string;
  notes: string | null;
  active: boolean;
}

export interface PlatformStateObservation {
  id: string;
  stateValue: 'ACTIVE' | 'INACTIVE' | 'UNKNOWN';
  observedAt: string | null;
  source: string;
  confidence: number;
  notes: string | null;
  evidenceRelativePath: string | null;
  ocrResult: string | null;
  manuallyVerified: boolean;
  recordedAt: string;
  superseded: boolean;
}

export interface MetricPoint {
  measuredAt: string;
  views: number | null;
  reach: number | null;
  likes?: number | null;
  comments?: number | null;
  shares?: number | null;
  follows?: number | null;
}
export interface WindowPerformance { observation: MetricPoint | null; deltaViews: number | null; deltaReach: number | null; viewsPerHour: number | null; }

export interface ReachFurtherSummary {
  videoId: string;
  video: string;
  platform: string;
  firstObservedAt: string | null;
  lastObservedAt: string | null;
  observationCount: number;
  active: boolean | null;
  publishedAt: string | null;
  videoAgeAtFirstObservationSeconds: number | null;
  cohort: string;
  offPeakPublish: boolean | null;
  publicationContextLabel: string | null;
  platformContentId: string | null;
  platformUrl: string | null;
  atFirstObservation: MetricPoint | null;
  current: MetricPoint | null;
  performanceWindows: Record<string, WindowPerformance>;
  velocityBefore: number | null;
  velocityAfter3h: number | null;
  accelerationAfterStatus: number | null;
  trajectoryType: string;
  performanceBand: string;
  creativeEngine: string | null;
  character: string | null;
  series: string | null;
  flags: string[];
  observations: PlatformStateObservation[];
  causalDisclaimer: string;
}

export interface InterventionEvent {
  id: string;
  videoId: string;
  platform: string;
  eventType: string;
  eventTime: string;
  notes: string | null;
  viewsBefore: number | null;
  viewsAfter: number | null;
}

export interface GrowthCheckpoint { measuredAt: string; views: number; }
export interface PlatformGrowthProfile {
  videoId: string;
  platform: string;
  publishedAt: string | null;
  views6h: GrowthCheckpoint | null;
  views24h: GrowthCheckpoint | null;
  views48h: GrowthCheckpoint | null;
  views7d: GrowthCheckpoint | null;
  latest: GrowthCheckpoint | null;
  instagramBurstRatio: number | null;
  viewsAfter24h: number | null;
  facebookTailRatio: number | null;
  primarySignal: string;
  disclaimer: string;
}
export interface PlatformTempo {
  platform: string;
  totalVideoCount: number;
  cleanVideoCount: number;
  intervenedExcludedCount: number;
  ratioEligibleCount: number;
  medianRatio: number | null;
  videos: PlatformGrowthProfile[];
}
export interface PlatformTempoResearch { instagram: PlatformTempo; facebook: PlatformTempo; disclaimer: string; }

export interface DiscoveryProfile {
  videoId: string;
  platform: string;
  cutoff: string;
  audienceObservedAt: string | null;
  countryObservedAt: string | null;
  followerShare: number | null;
  nonFollowerShare: number | null;
  usAudienceShare: number | null;
  estimatedUsAudience: number | null;
  recommendationShare: number | null;
  followsPerThousandViews: number | null;
  newAudienceQualityScore: number | null;
  algorithmVersion: string;
  dataQualityStatus: string;
  components: Record<string, number | null>;
}

export interface TrajectoryPoint extends MetricPoint { viewsPerHour: number | null; intervened: boolean; }
export interface TrajectoryView { videoId: string; platform: string; label: string; cleanOrganic: boolean; interventions: InterventionEvent[]; points: TrajectoryPoint[]; }

export interface ReachFurtherResearch {
  observedVideos: number;
  medianViewsAtFirstObservation: number | null;
  median24hViews: number | null;
  median7dViews: number | null;
  performanceBands: Record<string, number>;
  trajectories: Record<string, number>;
  creativeEngines: Record<string, number>;
  characters: Record<string, number>;
  platforms: Record<string, number>;
  cohorts: Record<string, number>;
  cases: ReachFurtherSummary[];
  disclaimer: string;
}

export interface OperationalGuardDecision {
  id: string;
  guardType: 'DISTRIBUTION' | 'RETENTION' | string;
  platform: string;
  scopeType: string;
  state: string;
  policyVersion: string;
  evidenceCount: number;
  metricValue: number | null;
  evaluatedAt: string;
  evidence: string;
}

export interface OperationalGuardSnapshot {
  platform: string;
  enabled: boolean;
  decisions: OperationalGuardDecision[];
  policyVersion: string;
}

export interface CaptionResponse {
  caption: string;
  hashtags: string[];
  platform: string;
  language: string;
  characterCount: number;
  withinLimit: boolean;
}

export interface AnalysisStatus {
  videoId: string;
  hasCompletedAnalysis: boolean;
  jobId: string | null;
  jobState: 'NOT_STARTED' | 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  attempts: number | null;
  maxAttempts: number | null;
  errorMessage: string | null;
  analysisId: string | null;
  classification: string | null;
  actionDnaScore: number | null;
  confidence: number | null;
  reason: string | null;
  storyboardPath: string | null;
  analysisVersion: string | null;
}

export interface ReachFurtherComparison {
  reachFurtherObserved: { sampleSize: number; medianCurrentViews: number | null; distribution: Record<string, number> };
  reachFurtherNotObserved: { sampleSize: number; medianCurrentViews: number | null; distribution: Record<string, number> };
  matched: { pairCount: number; observedMedianViews: number | null; controlMedianViews: number | null; comparisonEligible: boolean; method: string };
  limitations: string;
  causalDisclaimer: string;
}

@Injectable({ providedIn: 'root' })
export class CreativeIntelligenceService {
  private readonly baseUrl = '/api/v1';

  constructor(private readonly http: HttpClient) {}

  getOverview(): Observable<OverviewData> {
    return forkJoin({ videos: this.videoRecords(), predictions: this.predictionRecords() }).pipe(
      map(data => ({ ...data, source: 'api' as const })),
    );
  }

  getVideos(): Observable<{ source: 'api'; records: VideoRecord[] }> {
    return this.videoRecords().pipe(
      map(records => ({ source: 'api' as const, records })),
    );
  }

  getPredictions(): Observable<{ source: 'api'; records: PredictionRecord[] }> {
    return this.predictionRecords().pipe(
      map(records => ({ source: 'api' as const, records })),
    );
  }

  generatePrediction(videoId: string, platform: string): Observable<PredictionApiRecord> {
    return this.http.post<PredictionApiRecord>(`${this.baseUrl}/predictions`, { videoId, platform });
  }

  lockPrediction(id: string, reason = 'confirmed for publication'): Observable<PredictionApiRecord> {
    return this.http.post<PredictionApiRecord>(`${this.baseUrl}/predictions/${id}/lock`, { reason });
  }

  evaluatePrediction(id: string, horizonMinutes: number, actualValue: number): Observable<PredictionApiRecord> {
    return this.http.post<PredictionApiRecord>(`${this.baseUrl}/predictions/${id}/evaluate`, { horizonMinutes, actualValue });
  }

  getExperiments(): Observable<ExperimentRecord[]> {
    return this.http.get<ExperimentRecord[]>(`${this.baseUrl}/experiments`);
  }

  createExperiment(request: CreateExperimentRequest): Observable<ExperimentRecord> {
    return this.http.post<ExperimentRecord>(`${this.baseUrl}/experiments`, request);
  }

  getTestPlanner(): Observable<TestPlannerView> {
    return this.http.get<TestPlannerView>(`${this.baseUrl}/test-planner`);
  }

  getModels(): Observable<ModelVersionRecord[]> {
    return this.http.get<ModelVersionRecord[]>(`${this.baseUrl}/models`);
  }

  promoteModel(id: string, reason: string): Observable<ModelVersionRecord> {
    return this.http.post<ModelVersionRecord>(`${this.baseUrl}/models/${id}/promote`, { reason });
  }

  getReliability(): Observable<ReliabilityRecord[]> {
    return this.http.get<ReliabilityRecord[]>(`${this.baseUrl}/predictions/reliability`);
  }

  getPerformanceResearch(platform = 'facebook'): Observable<ReachFurtherResearch> {
    return this.getReachFurtherResearch(platform);
  }

  getCharacterCoverage(): Observable<CharacterCoverage[]> {
    return this.http.get<CharacterCoverage[]>(`${this.baseUrl}/characters/coverage`);
  }

  getCharacters(): Observable<CharacterIdentity[]> {
    return this.http.get<CharacterIdentity[]>(`${this.baseUrl}/characters`);
  }

  previewImport(file: File, platform: string, timezone: string): Observable<ImportPreview> {
    const body = new FormData();
    body.append('file', file);
    return this.http.post<ImportPreview>(`${this.baseUrl}/imports/preview`, body, {
      params: { platform, timezone },
    });
  }

  commitImport(batchId: string): Observable<ImportPreview> {
    return this.http.post<ImportPreview>(`${this.baseUrl}/imports/${batchId}/commit`, {});
  }

  getImportRows(batchId: string): Observable<ImportRow[]> {
    return this.http.get<ImportRow[]>(`${this.baseUrl}/imports/${batchId}/rows`);
  }

  resolveImportRow(batchId: string, rowId: string, videoId: string, reason = 'Manual exact selection'): Observable<ImportPreview> {
    return this.http.post<ImportPreview>(`${this.baseUrl}/imports/${batchId}/rows/${rowId}/match`, { videoId, reason });
  }

  getVideo(id: string): Observable<VideoApiRecord> {
    return this.http.get<VideoApiRecord>(`${this.baseUrl}/videos/${id}`);
  }

  ingestDirectory(relativeDirectory: string, recursive: boolean): Observable<DirectoryIngestResult> {
    return this.http.post<DirectoryIngestResult>(`${this.baseUrl}/videos/ingest-directory`, {
      relativeDirectory, recursive, seriesId: null,
    });
  }

  getMediaDirectories(relativeDirectory = 'library'): Observable<MediaDirectory[]> {
    return this.http.get<MediaDirectory[]>(`${this.baseUrl}/videos/media-directories`, { params: { relativeDirectory } });
  }

  getMediaFiles(relativeDirectory: string, recursive: boolean): Observable<MediaFile[]> {
    return this.http.get<MediaFile[]>(`${this.baseUrl}/videos/media-files`, {
      params: { relativeDirectory, recursive },
    });
  }

  mediaContentUrl(relativePath: string): string {
    return `${this.baseUrl}/videos/content?path=${encodeURIComponent(relativePath)}`;
  }

  ingestVideo(relativePath: string): Observable<VideoApiRecord> {
    return this.http.post<VideoApiRecord>(`${this.baseUrl}/videos/ingest`, { relativePath, seriesId: null });
  }

  listVariants(videoId: string): Observable<VideoVariant[]> {
    return this.http.get<VideoVariant[]>(`${this.baseUrl}/videos/${videoId}/variants`);
  }

  createVariant(videoId: string, request: CreateVariantRequest): Observable<VideoVariant> {
    return this.http.post<VideoVariant>(`${this.baseUrl}/videos/${videoId}/variants`, request);
  }

  triggerAnalysis(videoId: string): Observable<AnalysisStatus> {
    return this.http.post<AnalysisStatus>(`${this.baseUrl}/videos/${videoId}/analysis`, {});
  }

  getAnalysisStatus(videoId: string): Observable<AnalysisStatus> {
    return this.http.get<AnalysisStatus>(`${this.baseUrl}/videos/${videoId}/analysis/status`);
  }

  getReachFurther(id: string, platform = 'facebook'): Observable<ReachFurtherSummary> {
    return this.http.get<ReachFurtherSummary>(`${this.baseUrl}/videos/${id}/platform-states/reach-further`, { params: { platform } });
  }

  getTrajectory(id: string, platform = 'facebook'): Observable<TrajectoryView> {
    return this.http.get<TrajectoryView>(`${this.baseUrl}/performance/video/${id}/trajectory`, { params: { platform } });
  }

  getPlatformGrowth(id: string, platform = 'facebook'): Observable<PlatformGrowthProfile> {
    return this.http.get<PlatformGrowthProfile>(`${this.baseUrl}/performance/video/${id}/platform-profile`, { params: { platform } });
  }

  getDiscoveryProfile(id: string, platform = 'facebook'): Observable<DiscoveryProfile> {
    return this.http.get<DiscoveryProfile>(`${this.baseUrl}/performance/video/${id}/discovery-profile`, { params: { platform } });
  }

  getInterventions(id: string, platform = 'facebook'): Observable<InterventionEvent[]> {
    return this.http.get<InterventionEvent[]>(`${this.baseUrl}/videos/${id}/interventions`, { params: { platform } });
  }

  addManualEngagementIntervention(id: string, eventTime: string, notes: string, viewsBefore: number | null, viewsAfter: number | null, platform = 'facebook'): Observable<InterventionEvent> {
    return this.http.post<InterventionEvent>(`${this.baseUrl}/videos/${id}/interventions`, {
      platform, eventTime, notes, viewsBefore, viewsAfter,
    });
  }

  addReachFurther(id: string, observedAt: string, notes: string, platform = 'facebook'): Observable<PlatformStateObservation> {
    return this.http.post<PlatformStateObservation>(`${this.baseUrl}/videos/${id}/platform-states`, {
      platform, stateType: 'META_REACH_FURTHER', stateValue: 'ACTIVE', observedAt,
      source: 'MANUAL', confidence: 1, notes, manuallyVerified: true,
    });
  }

  uploadReachFurtherEvidence(id: string, file: File, observedAt: string, notes: string, manuallyVerified: boolean, platform = 'facebook'): Observable<PlatformStateObservation> {
    const body = new FormData();
    body.append('file', file);
    body.append('platform', platform);
    body.append('stateValue', 'ACTIVE');
    body.append('observedAt', observedAt);
    body.append('notes', notes);
    body.append('manuallyVerified', String(manuallyVerified));
    return this.http.post<PlatformStateObservation>(`${this.baseUrl}/videos/${id}/platform-states/reach-further/screenshot`, body);
  }

  recordPublicationContext(
    id: string,
    publishedAt: string,
    offPeakPublish: boolean,
    notes: string,
    platform: string,
    platformContentId: string,
    platformUrl: string,
  ): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/videos/${id}/publication-context`, {
      platform, platformContentId, platformUrl, publishedAt,
      publicationTimezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      offPeakPublish, source: 'MANUAL', notes,
    });
  }

  getReachFurtherResearch(platform = 'facebook'): Observable<ReachFurtherResearch> {
    return this.http.get<ReachFurtherResearch>(`${this.baseUrl}/research/reach-further`, { params: { platform } });
  }

  getOperationalGuards(platform = 'facebook', evaluate = false): Observable<OperationalGuardSnapshot> {
    return this.http.get<OperationalGuardSnapshot>(`${this.baseUrl}/performance/operational-guards`, {
      params: { platform, evaluate: String(evaluate) },
    });
  }

  generateCaption(request: {
    videoTitle: string;
    videoDescription: string;
    platform: string;
    language?: string;
    contentType?: string;
    maxLength?: number;
    hashtagCount?: number;
  }): Observable<CaptionResponse> {
    return this.http.post<CaptionResponse>('/api/v1/captions/generate', {
      targetAudience: 'kids 3-6 years old',
      ...request,
    });
  }

  getReachFurtherComparison(platform = 'facebook'): Observable<ReachFurtherComparison> {
    return this.http.get<ReachFurtherComparison>(`${this.baseUrl}/research/reach-further/comparison`, { params: { platform } });
  }

  getPlatformTempoResearch(): Observable<PlatformTempoResearch> {
    return this.http.get<PlatformTempoResearch>(`${this.baseUrl}/research/platform-tempo`);
  }

  private videoRecords(): Observable<VideoRecord[]> {
    return this.http.get<VideoPage>(`${this.baseUrl}/videos`, { params: { size: 200 } }).pipe(
      map(page => page.content.map(item => ({
        id: item.id,
        title: item.originalFilename,
        format: 'Unclassified',
        character: 'Unassigned',
        platform: 'Unknown' as const,
        state: item.status === 'PUBLISHED' ? 'Observed' as const : item.status === 'ANALYSED' ? 'Testing' as const : 'Ingested' as const,
        hookRate: 0,
        completion: 0,
        views: 0,
        published: new Date(item.ingestedAt).toLocaleDateString('en', { month: 'short', day: 'numeric' }),
      }))),
    );
  }

  private predictionRecords(): Observable<PredictionRecord[]> {
    return this.http.get<PredictionApiRecord[]>(`${this.baseUrl}/predictions`).pipe(
      map(items => items.map(item => {
        const target = item.payload.targets?.[0];
        const expected = target?.expectedValue ?? null;
        const interval = target?.interval80;
        return {
          id: item.id,
          videoId: item.videoId,
          video: item.videoId,
          platform: this.platform(item.platform),
          state: item.status,
          predicted: expected,
          range: interval?.every(value => value !== null) ? `${interval[0]}–${interval[1]}` : 'Uncalibrated',
          sample: item.comparableSampleSize,
          model: item.modelVersion,
          lockedAt: item.lockedAt ? new Date(item.lockedAt).toLocaleString() : 'Not locked',
          datasetVersion: item.datasetVersion,
          featureVersion: item.featureVersion,
          knowledgeCutoff: item.knowledgeCutoff,
          predictionType: item.predictionType || 'PRE_PUBLISH',
        };
      })),
    );
  }

  private platform(value: string): Platform {
    const key = value.toLowerCase();
    return key === 'youtube' ? 'YouTube' : key === 'tiktok' ? 'TikTok' : 'Instagram';
  }
}
