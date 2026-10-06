import { ChangeDetectionStrategy, Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, combineLatest, forkJoin, interval, Observable, of, startWith, Subscription, switchMap } from 'rxjs';
import {
  AnalysisStatus,
  CharacterIdentity,
  CreativeIntelligenceService,
  VideoCharacterAssignment,
  DiscoveryProfile,
  MetadataFile,
  MediaFile,
  PlatformGrowthProfile,
  PlatformCreativeReadiness,
  VideoCreativeContext,
  ReachFurtherSummary,
  TrajectoryView,
  VideoApiRecord,
  VideoVariant,
} from '../core/creative-intelligence.service';
import { isHdFile, mediaVariant } from './video-library.page';

type PlatformKey = 'facebook' | 'instagram' | 'tiktok' | 'youtube';
type CaptionPlatform = 'INSTAGRAM' | 'FACEBOOK' | 'TIKTOK' | 'YOUTUBE';
interface ChartDot { left: number; bottom: number; label: string; }
interface VariantView extends MediaFile { label: string; }
interface DraftCharacter { characterId: string; name: string; participation: 'PRIMARY' | 'SECONDARY'; role: string; }
interface PublicationCopy {
  sourceFile: string | null;
  sourcePath: string | null;
  raw: string;
  title: string;
  body: string;
  hashtags: string;
  tags: string;
}

const EMPTY_PUBLICATION_COPY: PublicationCopy = { sourceFile: null, sourcePath: null, raw: '', title: '', body: '', hashtags: '', tags: '' };

const VARIANT_TYPE_LABELS: Record<string, string> = {
  ORIGINAL: 'Original',
  HOOK_COLD_OPEN: 'Hook / Cold Open',
  TRIMMED: 'Trimmed',
  NO_CTA: 'No CTA',
  LOOP_CUT: 'Loop Cut',
  CUSTOM_EDIT: 'Custom Edit',
};

@Component({
  selector: 'app-video-detail-page',
  imports: [RouterLink, FormsModule],
  template: `
    <header class="page-header detail-header">
      <div>
        <a class="back-link" routerLink="/videos">← Video Library</a>
        <span class="eyebrow">VIDEO REVIEW STUDIO</span>
        <h1>{{ folderName() || 'Video detail' }}</h1>
        <p [title]="folderPath()">{{ folderPath() }}</p>
      </div>
      <div class="header-actions">
        <span class="status-badge" [class.status-badge--green]="activeFile()?.ingested">{{ activeFile()?.ingested ? (activeFile()?.status || 'Ingested') : 'Preview only' }}</span>
        <span class="data-freshness">{{ variants().length }} {{ variants().length === 1 ? 'variant' : 'variants' }}</span>
      </div>
    </header>

    @if (loading()) {
      <section class="state-panel section-band"><span class="spinner"></span><strong>Loading review studio</strong></section>
    } @else if (error()) {
      <section class="state-panel state-panel--error section-band"><strong>Video unavailable</strong><p>{{ error() }}</p><a class="button button--secondary" routerLink="/videos">Return to Video Library</a></section>
    } @else if (activeFile()) {
      <section class="review-workspace" aria-label="Video and variants">
        <div class="video-inspection">
          <div class="video-stage" [class.video-stage--portrait]="isPortrait()">
            <video controls preload="metadata" [src]="mediaUrl()" [attr.aria-label]="'Preview ' + activeFile()!.name"></video>
          </div>
          <div class="selected-file-bar">
            <div><span class="eyebrow">SELECTED VARIANT</span><strong [title]="activeFile()!.name">{{ activeVariantLabel() }}</strong><small [title]="activeFile()!.name">{{ activeFile()!.name }}</small></div>
            @if (!activeFile()!.ingested) { <button class="button button--primary" type="button" [disabled]="ingesting()" (click)="ingestSelected()">{{ ingesting() ? 'Ingesting…' : 'Ingest for analysis' }}</button> }
            @else { <span class="status-badge status-badge--green">Evidence record linked</span> }
          </div>
        </div>

        <aside class="variant-rail" aria-label="Video variants">
          @if (variantsError()) { <p class="amber-text">{{ variantsError() }}</p> }
          <div class="variant-rail-heading"><span class="eyebrow">FOLDER VERSIONS</span><strong>Compare variants</strong></div>
          <div class="variant-list">
            @for (variant of variants(); track variant.relativePath) {
              <button type="button" [class.is-active]="variant.relativePath === activeFile()!.relativePath" (click)="selectVariant(variant)">
                <span class="variant-marker">{{ $index + 1 }}</span>
                <span><strong>{{ variant.label }}</strong><small [title]="variant.name">{{ variant.name }}</small><em>{{ fileSize(variant.sizeBytes) }} · {{ variant.ingested ? (variant.status || 'Ingested') : 'Not ingested' }}</em></span>
              </button>
            }
          </div>
        </aside>
      </section>

      @if (message()) { <p class="form-message studio-message">{{ message() }}</p> }

      <nav class="detail-tabs" aria-label="Video detail sections">
        <button type="button" [class.is-active]="activeTab() === 'overview'" (click)="activeTab.set('overview')">Overview</button>
        <button type="button" [class.is-active]="activeTab() === 'creative'" (click)="activeTab.set('creative')">Creative</button>
        <button type="button" [class.is-active]="activeTab() === 'publication'" (click)="activeTab.set('publication')">Publication</button>
        <button type="button" [class.is-active]="activeTab() === 'performance'" (click)="activeTab.set('performance')">Performance</button>
        <button type="button" [class.is-active]="activeTab() === 'evidence'" (click)="activeTab.set('evidence')">Evidence</button>
      </nav>

      @if (activeTab() === 'creative') {
      <section class="section-band creative-context-panel" aria-labelledby="creative-context-heading">
        <div class="section-heading"><div><span class="eyebrow">CREATIVE CONTEXT</span><h2 id="creative-context-heading">Characters and prompt lineage</h2></div><span class="data-freshness">Read from canonical DB records</span></div>
        @if (creativeContextLoading()) {
          <div class="state-panel compact-state"><span class="spinner"></span><strong>Loading creative context</strong></div>
        } @else if (creativeContextError()) {
          <div class="state-panel state-panel--error compact-state"><strong>Creative context unavailable</strong><p>{{ creativeContextError() }}</p></div>
        } @else {
          <div class="creative-context-grid">
            <section class="context-card" aria-labelledby="context-characters-heading">
              <span class="eyebrow">CHARACTER TOPIC</span><h3 id="context-characters-heading">Characters in this video</h3>
              @if (editingCharacters()) {
                <div class="character-editor" role="group" aria-labelledby="context-characters-heading">
                  @if (!draftCharacters().length) { <div class="compact-empty"><strong>No characters selected</strong><span>Add the main character and any supporting characters below.</span></div> }
                  @for (draft of draftCharacters(); track draft.characterId) {
                    <div class="character-editor-row">
                      <strong>{{ draft.name }}</strong>
                      <label><span>Type</span>
                        <select [ngModel]="draft.participation" (ngModelChange)="setDraftParticipation(draft.characterId, $event)" [attr.aria-label]="'Type for ' + draft.name">
                          <option value="PRIMARY">Main</option>
                          <option value="SECONDARY">Supporting</option>
                        </select>
                      </label>
                      <label><span>Role</span>
                        <select [ngModel]="draft.role" (ngModelChange)="setDraftRole(draft.characterId, $event)" [attr.aria-label]="'Role for ' + draft.name">
                          @for (role of characterRoles; track role) { <option [value]="role">{{ readable(role) }}</option> }
                        </select>
                      </label>
                      <button type="button" class="button button--secondary button--compact" (click)="removeDraftCharacter(draft.characterId)" [attr.aria-label]="'Remove ' + draft.name">Remove</button>
                    </div>
                  }
                  <div class="character-editor-add">
                    <label><span>Add existing character</span>
                      <select [ngModel]="''" (ngModelChange)="addRegistryCharacter($event)" aria-label="Add existing character">
                        <option value="">Select character…</option>
                        @for (option of availableRegistryCharacters(); track option.id) { <option [value]="option.id">{{ option.name }}</option> }
                      </select>
                    </label>
                    <label><span>Or create new character</span>
                      <input type="text" [ngModel]="newCharacterName()" (ngModelChange)="newCharacterName.set($event)" (keydown.enter)="createDraftCharacter()" placeholder="Character name" aria-label="New character name" />
                    </label>
                    <button type="button" class="button button--secondary button--compact" [disabled]="!newCharacterName().trim() || characterSaving()" (click)="createDraftCharacter()">Create and add</button>
                  </div>
                  @if (characterEditError()) { <p class="character-editor-error" role="alert">{{ characterEditError() }}</p> }
                  <div class="character-editor-actions">
                    <button type="button" class="button button--primary button--compact" [disabled]="characterSaving()" (click)="saveCharacters()">{{ characterSaving() ? 'Saving…' : 'Save characters' }}</button>
                    <button type="button" class="button button--secondary button--compact" [disabled]="characterSaving()" (click)="cancelEditCharacters()">Cancel</button>
                  </div>
                </div>
              } @else {
              @if (creativeContext()?.characters?.length) {
                <div class="context-list">
                  @for (character of creativeContext()!.characters; track character.id) {
                    <article><strong>{{ character.name }}</strong><span>{{ readable(character.participation) }} · {{ readable(character.role) }}</span><small>{{ characterMetrics(character) }}</small><small>{{ readable(character.source) }} · {{ readable(character.confidence) }}@if (character.manuallyConfirmed) { · confirmed }</small></article>
                  }
                </div>
              } @else { <div class="compact-empty"><strong>No linked character records</strong><span>No character was found for this video. You can add them manually.</span></div> }
              <button type="button" class="button button--secondary button--compact character-edit-button" (click)="startEditCharacters()">Edit characters</button>
              }
            </section>
            <section class="context-card" aria-labelledby="context-prompt-heading">
              <span class="eyebrow">PROMPT TOPIC</span><h3 id="context-prompt-heading">Source prompt and version</h3>
              @if (creativeContext()?.prompt; as prompt) {
                <dl class="context-facts"><div><dt>Content</dt><dd>{{ prompt.title }}</dd></div><div><dt>Version</dt><dd>v{{ prompt.versionNumber }} · {{ readable(prompt.type) }} · {{ readable(prompt.status) }}</dd></div><div><dt>Source</dt><dd><code>{{ prompt.sourcePath || 'Render lineage' }}</code></dd></div></dl>
                <details class="prompt-preview"><summary>View prompt text</summary><pre>{{ prompt.rawText }}</pre></details>
                @if (prompt.parsedIr) { <details class="prompt-preview"><summary>View parsed plan</summary><pre>{{ prompt.parsedIr }}</pre></details> }
                <a class="button button--secondary button--compact" routerLink="/quality">Open Prompt Quality</a>
              } @else { <div class="compact-empty"><strong>No linked prompt version</strong><span>This video has no persisted render or folder prompt lineage yet.</span><a class="button button--secondary button--compact" routerLink="/quality">Open Prompt Quality</a></div> }
            </section>
          </div>
        }
      </section>
      }

      @if (activeTab() === 'overview') {
      <section class="section-band technical-panel">
        <div class="section-heading"><div><span class="eyebrow">SOURCE FACTS</span><h2>Technical details</h2></div><span class="data-freshness">Real file metadata</span></div>
        <div class="technical-groups">
          <section class="technical-group" aria-labelledby="video-facts-heading">
            <h3 id="video-facts-heading">Video</h3>
            <dl class="technical-facts">
              <div><dt>Duration</dt><dd>{{ duration() }}</dd></div>
              <div><dt>Resolution</dt><dd>{{ video() ? video()!.width + ' × ' + video()!.height : '—' }}</dd></div>
              <div><dt>Frame rate</dt><dd>{{ video() ? video()!.fps.toFixed(2) + ' fps' : '—' }}</dd></div>
            </dl>
          </section>
          <section class="technical-group" aria-labelledby="file-facts-heading">
            <h3 id="file-facts-heading">File</h3>
            <dl class="technical-facts">
              <div><dt>Size</dt><dd>{{ fileSize(activeFile()!.sizeBytes) }}</dd></div>
              <div><dt>Format</dt><dd>{{ extension(activeFile()!.name) }}</dd></div>
              <div><dt>Modified</dt><dd>{{ date(activeFile()!.modifiedAt) }}</dd></div>
            </dl>
          </section>
          <section class="technical-group" aria-labelledby="evidence-facts-heading">
            <h3 id="evidence-facts-heading">Evidence</h3>
            <dl class="technical-facts">
              <div><dt>Ingest state</dt><dd>{{ activeFile()!.ingested ? (activeFile()!.status || 'Ingested') : 'Not ingested' }}</dd></div>
              <div><dt>Ingested</dt><dd>{{ video() ? date(video()!.ingestedAt) : '—' }}</dd></div>
              <div><dt>Audio / codec</dt><dd>{{ video() ? (video()!.audioPresent ? 'Audio' : 'No audio') + ' / ' + video()!.codec : '—' }}</dd></div>
            </dl>
          </section>
        </div>
      </section>

      <section class="section-band creative-analysis-panel" aria-labelledby="creative-analysis-heading">
        <div class="section-heading"><div><span class="eyebrow">VISUAL MOTION ANALYSIS</span><h2 id="creative-analysis-heading">Sampled visual-motion evidence</h2></div>
          <button class="button button--primary" type="button" [disabled]="triggeringAnalysis() || analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING'" (click)="triggerAnalysis()">{{ triggeringAnalysis() ? 'Starting…' : analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING' ? (analysisStatus()!.jobState === 'QUEUED' ? 'Queued…' : 'Running…') : analysisStatus()?.hasCompletedAnalysis ? 'Reanalyze' : 'Run analysis' }}</button>
        </div>
        @if (analysisFeedback()) { <p class="analysis-feedback" [class.analysis-feedback--error]="analysisFeedbackKind() === 'error'" role="status">{{ analysisFeedback() }}</p> }
        <div class="assessment-notice"><strong>Interpretation</strong><span>This is a sampled visual-motion heuristic. It does not use views, reach, likes, comments, follows or retention data.</span></div>
        @if (analysisStatus()?.hasCompletedAnalysis) {
          <section class="creative-evidence-summary" aria-labelledby="creative-evidence-summary-heading">
            <div class="section-heading"><div><span class="eyebrow">WHAT THE EVIDENCE SAYS</span><h3 id="creative-evidence-summary-heading">Human-readable motion interpretation</h3></div><span class="data-freshness">Motion evidence only</span></div>
            <div class="creative-evidence-cards">
              <div><span>Visual activity</span><strong>{{ motionSummary() }}</strong><small>Sampled visual change through the timeline.</small></div>
              <div><span>Motion variation</span><strong>{{ variationSummary() }}</strong><small>This describes motion, not story progression.</small></div>
              <div><span>Opening/ending relationship</span><strong>{{ similaritySummary() }}</strong><small>Visual similarity does not prove a semantic loop.</small></div>
              <div><span>Local activity changes</span><strong>{{ activityDropSummary() }}</strong><small>Canonical V5 temporal events; relative dips are separate from absolute low motion.</small></div>
            </div>
            @if (analysisStatus()!.analysisVersion === 'sampled-visual-motion-v4' || analysisStatus()!.analysisVersion === 'sampled-visual-motion-v5') {
              <div class="creative-evidence-cards creative-evidence-cards--v4">
                <div><span>Visual novelty</span><strong>{{ v4Dimension('visualNovelty') }}</strong><small>Medium-range structural and perceptual state change.</small></div>
                <div><span>Repetition evidence</span><strong>{{ v4Repetition() }}</strong><small>High motion with low state novelty, not a performance verdict.</small></div>
                <div><span>Action / beat novelty</span><strong>{{ v4Dimension('actionBeatNovelty') }}</strong><small>Plan-side semantic evidence is separate from pixels.</small></div>
                <div><span>Plan / render fidelity</span><strong>{{ v4Dimension('planRenderFidelity') }}</strong><small>Aligned when a structured production plan is available.</small></div>
              </div>
              @if (analysisStatus()!.analysisVersion === 'sampled-visual-motion-v5') {
                <div class="creative-evidence-cards creative-evidence-cards--v4">
                  <div><span>Opening hook</span><strong>{{ v5HookSummary() }}</strong><small>{{ v5HookReason() }}</small></div>
                  <div><span>Temporal emphasis</span><strong>{{ v5HoldSummary() }}</strong><small>{{ v5HoldReason() }}</small></div>
                  <div><span>Payoff</span><strong>{{ v5ReboundSummary() }}</strong><small>{{ v5PayoffReason() }}</small></div>
                  <div><span>Loop evidence</span><strong>{{ v5LoopSummary() }}</strong><small>Visual endpoint evidence is separate from semantic loop verification.</small></div>
                  <div><span>Readiness coverage</span><strong>{{ v5CoverageSummary() }}</strong><small>{{ v5CoverageReason() }}</small></div>
                </div>
                  <div class="creative-evidence-cards creative-evidence-cards--v4">
                    <div><span>Temporal motion trend</span><strong>{{ v5TrendSummary() }}</strong><small>{{ v5TrendReason() }}</small></div>
                    <div><span>Temporal structure</span><strong>{{ temporalShapeSummary() }}</strong><small>{{ temporalShapeReason() }}</small></div>
                    <div><span>Local recovery</span><strong>{{ v5RecoverySummary() }}</strong><small>Recovery is distinct from a final rebound.</small></div>
                    <div><span>Final rebound</span><strong>{{ v5FinalReboundSummary() }}</strong><small>Measured recovery from the preceding segment.</small></div>
                    <div><span>Structural attention windows</span><strong>{{ structuralRiskSummary() }}</strong><small>Uncalibrated structural evidence only; never a predicted viewer drop.</small></div>
                  </div>
                @if (platformReadiness().length) {
                  <div class="platform-readiness-strip">
                    <div class="section-heading"><div><span class="eyebrow">PLATFORM LENS</span><h3>Creative fit by platform</h3></div><span class="data-freshness">Policy hypothesis · not prediction</span></div>
                    <div class="creative-evidence-cards creative-evidence-cards--v4">
                      @for (item of platformReadiness(); track item.platform) {
                        <div><span>{{ item.platform.replaceAll('_', ' ') }}</span><strong>{{ item.readinessGrade }} · {{ item.readinessRisk }}</strong><small>{{ item.readinessDecision.replaceAll('_', ' ') }} · {{ item.assessmentCoverage }}% evidence</small></div>
                      }
                    </div>
                  </div>
                }
              }
            }
          </section>
          <section class="semantic-understanding-panel" aria-labelledby="semantic-understanding-heading">
            <div class="section-heading"><div><span class="eyebrow">SEMANTIC VIDEO UNDERSTANDING</span><h2 id="semantic-understanding-heading">Observed story and meaning</h2></div><span class="data-freshness">{{ semanticStatus() }}</span></div>
            @if (!['COMPLETED', 'PARTIAL', 'CACHE_HIT'].includes(semanticStatus())) {
              <div class="state-panel compact-state"><strong>Semantic layer {{ semanticStatus().replaceAll('_', ' ').toLowerCase() }}</strong><p>{{ semanticLimitation() }}</p></div>
            } @else {
              <div class="creative-evidence-cards">
                <div><span>Story arc</span><strong>{{ semanticValue('storyArc', 'arcType') }}</strong><small>Structured observed sequence.</small></div>
                <div><span>Semantic hook</span><strong>{{ semanticValue('opening', 'semanticHookReadable') }}</strong><small>Hook is more than face visibility.</small></div>
                <div><span>Payoff</span><strong>{{ semanticValue('payoff', 'status') }}</strong><small>Semantic resolution is separate from motion rebound.</small></div>
                <div><span>Loop</span><strong>{{ semanticValue('loop', 'status') }}</strong><small>Scene-state compatibility, not pixel similarity alone.</small></div>
              </div>
              <div class="semantic-evidence-list"><span>Characters</span><strong>{{ semanticNames('characters') }}</strong><span>Objects</span><strong>{{ semanticNames('objects') }}</strong><span>Beats</span><strong>{{ semanticBeatSummary() }}</strong><span>Confidence</span><strong>{{ semanticConfidence() }}</strong></div>
              <details class="semantic-technical-details">
                <summary>Semantic evidence provenance</summary>
                <dl class="semantic-provenance-grid">
                  <div><dt>Request fingerprint</dt><dd><code>{{ semanticFingerprint() }}</code></dd></div>
                  <div><dt>Frame manifest</dt><dd>{{ semanticFrameManifestCount() }} exact prepared frame{{ semanticFrameManifestCount() === 1 ? '' : 's' }}</dd></div>
                  <div><dt>Consistency validator</dt><dd>{{ semanticConsistencyStatus() }}</dd></div>
                  <div><dt>Provider / model</dt><dd>{{ semanticProviderModel() }}</dd></div>
                  <div><dt>Prompt / schema</dt><dd>{{ semanticVersion('prompt') }} / {{ semanticVersion('schema') }}</dd></div>
                  <div><dt>Selector / image prep</dt><dd>{{ semanticFrameSelectorVersion() }} / {{ semanticVersion('imagePreparation') }}</dd></div>
                  <div><dt>Provider calls</dt><dd>{{ semanticProviderCalls() }}</dd></div>
                </dl>
              </details>
            }
          </section>
          <section class="temporal-timeline" aria-labelledby="temporal-timeline-heading">
            <div class="section-heading"><div><span class="eyebrow">LOCAL TIMELINE</span><h3 id="temporal-timeline-heading">Motion by segment</h3></div><span class="data-freshness">{{ temporalVersion() }}</span></div>
            @if (timelineSegments().length) {
              <div class="temporal-segment-table" role="table" aria-label="Local motion segment timeline">
              <div class="temporal-segment-row temporal-segment-row--header" role="row"><span>Time</span><span>Activity</span><span>Density</span><span>Coverage</span><span>Shape</span><span>Event</span></div>
                @for (segment of timelineSegments(); track segment['segmentIndex']) {
                  <div class="temporal-segment-row" role="row">
                    <span>{{ segment['startSeconds'] }}–{{ segment['endSeconds'] }}s</span>
                    <span class="temporal-activity"><i [style.width.%]="segmentActivityPercent(segment)"></i><b>{{ segment['averageMotion'] }}</b></span>
                    <span>{{ percentValue(segment['motionDensity']) }}</span>
                    <span>{{ percentValue(segment['coverage']) }}</span>
                    <span>{{ segmentShape(segment) }}</span><span>{{ timelineEventLabel(segment) }}</span>
                  </div>
                }
              </div>
              <p class="analysis-caption">Activity is duration-weighted sampled visual change. It is not a story, audience, or retention measurement.</p>
            } @else { <div class="state-panel compact-state"><strong>No local timeline available</strong><p>Run analysis to create duration-aware motion segments.</p></div> }
          </section>
          <details class="technical-details-collapsible">
            <summary>Technical details</summary>
          <dl class="technical-facts analysis-facts">
            <div><dt>Motion evidence level</dt><dd>{{ analysisStatus()!.classification || '—' }}</dd></div>
            <div><dt>Motion heuristic score</dt><dd>{{ decimal(analysisStatus()!.motionHeuristicScore ?? analysisStatus()!.actionDnaScore) }} / 100</dd></div>
            <div class="analysis-facts__group"><dt>Motion score components</dt><dd><small class="analysis-legacy-note">{{ analysisStatus()!.analysisVersion === 'sampled-visual-motion-v2' ? 'Legacy v2 score formula' : 'Current motion-only formula' }}</small><dl class="analysis-components">
              <div><dt>Opening motion</dt><dd>{{ analysisMetric('openingMotionIntensity') }}</dd></div>
              <div><dt>Overall motion</dt><dd>{{ analysisMetric('overallMotionIntensity') }}</dd></div>
              <div><dt>Motion density</dt><dd>{{ analysisMetric('motionIntervalDensity') }}</dd></div>
              <div><dt>Ending motion</dt><dd>{{ analysisMetric('endingMotionEvidence') }}</dd></div>
            </dl></dd></div>
            <div class="analysis-facts__group"><dt>Other visual evidence</dt><dd><dl class="analysis-components">
              <div><dt>First/last visual similarity</dt><dd>{{ analysisMetric('firstLastVisualSimilarity', true) }}</dd></div>
              <div><dt>Temporal trend</dt><dd>{{ v5TrendSummary() }}</dd></div>
              <div><dt>Low-motion duration</dt><dd>{{ lowMotionDurationSummary() }}</dd></div>
            </dl></dd></div>
            <div class="analysis-facts__group"><dt>Measurement quality</dt><dd><dl class="analysis-components">
              <div><dt>Decode success</dt><dd>{{ analysisPercent('measurementQuality', 'decodeSuccessRatio') }}</dd></div>
              <div><dt>Temporal coverage</dt><dd>{{ analysisPercent('measurementQuality', 'temporalCoverage') }}</dd></div>
              <div><dt>Valid frame pairs</dt><dd>{{ analysisNumber('measurementQuality', 'validFramePairCount') }}</dd></div>
              <div><dt>Failed decode samples</dt><dd>{{ analysisNumber('measurementQuality', 'failedDecodeSamples') }}</dd></div>
              <div><dt>Minimum interval</dt><dd>{{ analysisNumber('measurementQuality', 'minimumDeltaTSeconds') }}s</dd></div>
            </dl></dd></div>
            <div class="analysis-facts__group"><dt>Sampling coverage</dt><dd><dl class="analysis-components">
              <div><dt>Requested samples</dt><dd>{{ analysisNumber('sampling', 'requestedSamples') }}</dd></div>
              <div><dt>Decoded samples</dt><dd>{{ analysisNumber('sampling', 'decodedSamples') }}</dd></div>
              <div><dt>Valid frame pairs</dt><dd>{{ analysisNumber('sampling', 'validFramePairs') }}</dd></div>
              <div><dt>Failed requested times</dt><dd>{{ analysisListLength('sampling', 'failedRequestedTimes') }}</dd></div>
            </dl></dd></div>
            @if (analysisList('motion', 'lowMotionIntervals').length) {
              <div class="analysis-facts__group"><dt>Low-motion intervals</dt><dd><div class="analysis-intervals">
                @for (interval of analysisList('motion', 'lowMotionIntervals'); track $index) {
                  <span>{{ interval['startTime'] }}–{{ interval['endTime'] }}s · {{ interval['duration'] }}s</span>
                }
              </div></dd></div>
            }
            @if (analysisStatus()!.darkFrameCandidates?.length) {
              <div class="analysis-facts__group"><dt>Dark-frame candidates</dt><dd><div class="analysis-intervals">
                @for (candidate of analysisStatus()!.darkFrameCandidates; track $index) {
                  <span>{{ candidate['kind'] || 'DARK_FRAME' }} · {{ candidate['requestedTime'] }}s</span>
                }
              </div></dd></div>
            }
            <div><dt>Measurement confidence</dt><dd>{{ decimal(analysisStatus()!.measurementConfidence ?? analysisStatus()!.confidence) }} <small>(decode and sampling quality only)</small></dd></div>
            <div><dt>Analysis type</dt><dd>{{ analysisStatus()!.analysisType || 'LEGACY' }}</dd></div>
            <div><dt>Interpretation</dt><dd>{{ analysisStatus()!.reason }}</dd></div>
            <div><dt>Analysis version</dt><dd><code>{{ analysisStatus()!.analysisVersion }}</code></dd></div>
            @if (analysisStatus()!.storyboardPath) { <div><dt>Storyboard</dt><dd><code>{{ analysisStatus()!.storyboardPath }}</code></dd></div> }
          </dl>
          </details>
        } @else if (analysisStatus()?.jobState === 'FAILED') {
          <div class="state-panel state-panel--error compact-state"><strong>Analysis failed</strong><p>{{ analysisStatus()!.errorMessage || 'The analysis job failed.' }}</p></div>
        } @else if (analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING') {
          <div class="state-panel compact-state"><span class="spinner"></span><strong>{{ analysisStatus()!.jobState === 'QUEUED' ? 'Queued for analysis' : 'Analysis running' }}</strong></div>
        } @else if (analysisError()) {
          <div class="state-panel state-panel--error compact-state"><strong>Analysis status unavailable</strong><p>{{ analysisError() }}</p><button class="button button--secondary" type="button" (click)="pollAnalysisStatus(video()!.id)">Retry status</button></div>
        } @else {
          <div class="state-panel compact-state"><strong>No analysis yet</strong><p>Trigger visual-motion analysis to measure sampled frame-change evidence.</p></div>
        }
      </section>

      <section class="section-band observed-performance-overview" aria-labelledby="observed-performance-heading">
        <div class="section-heading"><div><span class="eyebrow">OBSERVED PERFORMANCE</span><h2 id="observed-performance-heading">Latest imported platform evidence</h2></div><span class="data-freshness">{{ platformLabel() }}</span></div>
        @if (!activeFile()!.ingested) {
          <div class="state-panel compact-state"><strong>No observed performance yet</strong><p>Ingest the video and import platform checkpoints to separate real audience response from the creative heuristic.</p></div>
        } @else {
          <div class="performance-summary overview-performance-summary">
            @for (metric of summaryMetrics(); track metric.label) { <div><span>{{ metric.label }}</span><strong>{{ number(metric.value) }}</strong><small>{{ metric.value === null || metric.value === undefined ? 'No imported value' : 'Latest persisted checkpoint' }}</small></div> }
          </div>
          <p class="assessment-footnote">Observed performance is evidence from the selected platform. It does not rewrite the creative assessment score.</p>
        }
      </section>
      }

      @if (activeTab() === 'publication') {
      <section class="section-band social-copy-panel" aria-labelledby="social-copy-heading">
        <div class="section-heading"><div><span class="eyebrow">PUBLICATION COPY</span><h2 id="social-copy-heading">Social caption</h2></div><span class="data-freshness">Read from folder metadata</span></div>
        @if (metadataLoading()) { <div class="state-panel compact-state"><span class="spinner"></span><strong>Loading publication metadata</strong></div> }
        @if (metadataError()) { <div class="state-panel state-panel--error compact-state"><strong>Metadata unavailable</strong><p>{{ metadataError() }}</p></div> }
        <nav class="platform-tabs caption-tabs" aria-label="Publication platform">
          @for (item of captionPlatforms; track item.key) { <button type="button" [class.is-active]="captionPlatform() === item.key" [attr.aria-current]="captionPlatform() === item.key ? 'page' : null" (click)="captionPlatform.set(item.key)">{{ item.label }}</button> }
        </nav>
        <div class="caption-platform-grid">
          @let item = currentCaptionPlatform();
          @let copy = publicationCopy()[item.key];
            <article class="caption-card">
              <header><span class="eyebrow">{{ item.label.toUpperCase() }}</span><strong>{{ item.label }}</strong><small class="metadata-source">{{ copy.sourceFile || 'Metadata file not found' }}</small></header>
              @if (copy.sourceFile) {
                @if (copy.title) { <label>Title<textarea [ngModel]="copy.title" (ngModelChange)="updateCopy(item.key, 'title', $event)" rows="2"></textarea></label> }
                @if (copy.body) { <label>{{ item.key === 'YOUTUBE' ? 'Description' : 'Caption' }}<textarea [ngModel]="copy.body" (ngModelChange)="updateCopy(item.key, 'body', $event)" rows="4"></textarea></label> }
                @if (copy.hashtags) { <label>Hashtags<textarea [ngModel]="copy.hashtags" (ngModelChange)="updateCopy(item.key, 'hashtags', $event)" rows="2"></textarea></label> }
                @if (copy.tags) { <label>Tags<textarea [ngModel]="copy.tags" (ngModelChange)="updateCopy(item.key, 'tags', $event)" rows="3"></textarea></label> }
                <footer class="caption-card__footer"><span>{{ copy.sourceFile }}</span><button class="button button--secondary button--compact" type="button" [disabled]="savingCopy() === item.key" (click)="saveCopy(item.key)">{{ savingCopy() === item.key ? 'Saving…' : 'Save changes' }}</button></footer>
                @if (!copy.title && !copy.body && !copy.hashtags && !copy.tags) { <div class="state-panel compact-state"><strong>No copy sections found</strong><p>The metadata file exists but has no supported publication fields.</p></div> }
              } @else {
                <div class="state-panel compact-state"><strong>No {{ item.key === 'YOUTUBE' ? 'youtube.md' : 'social.md' }} found</strong><p>This platform has no folder metadata yet. No copy has been invented.</p></div>
              }
            </article>
        </div>
      </section>
      }

      @if (activeTab() === 'performance') {
      @if (!activeFile()!.ingested) {
        <section class="section-band un-ingested-state"><span aria-hidden="true">i</span><div><strong>Performance evidence requires ingest and imported platform data</strong><p>This mounted file remains playable. Ingesting creates its evidence identity; it does not invent metrics.</p></div></section>
      } @else {
        <nav class="platform-tabs" aria-label="Performance platform">
          @for (item of platforms; track item.key) { <button type="button" [class.is-active]="platform() === item.key" [attr.aria-current]="platform() === item.key ? 'page' : null" (click)="selectPlatform(item.key)">{{ item.label }}</button> }
        </nav>

        @if (performanceLoading()) {
          <section class="state-panel section-band compact-state"><span class="spinner"></span><strong>Loading {{ platformLabel() }} evidence</strong></section>
        } @else {
          @if (performanceError()) { <section class="state-panel state-panel--error section-band compact-state"><strong>Some performance evidence is unavailable</strong><p>{{ performanceError() }}</p><button class="button button--secondary" type="button" (click)="loadPerformance()">Retry evidence</button></section> }
          <section class="performance-summary" aria-label="Latest persisted performance">
            @for (metric of summaryMetrics(); track metric.label) { <div><span>{{ metric.label }}</span><strong>{{ number(metric.value) }}</strong><small>{{ metric.value === null || metric.value === undefined ? 'No imported value' : 'Latest persisted checkpoint' }}</small></div> }
          </section>

          <section class="section-band discovery-profile" aria-labelledby="audience-discovery-title">
            <div class="section-heading discovery-heading">
              <div><span class="eyebrow">AUDIENCE DISCOVERY</span><h2 id="audience-discovery-title">New audience profile</h2></div>
              <span class="status-badge" [class.status-badge--green]="discovery()?.dataQualityStatus === 'DERIVED_FROM_REPORTED_SHARES'">{{ discoveryQualityLabel() }}</span>
            </div>
            <div class="discovery-metrics">
              <div class="discovery-score">
                <span>New audience quality</span>
                <strong>{{ decimal(discovery()?.newAudienceQualityScore) }}</strong>
                <small>{{ metricSource(discovery()?.newAudienceQualityScore, 'Derived score out of 100') }}</small>
              </div>
              <div>
                <span>Non-follower share</span>
                <strong>{{ percent(discovery()?.nonFollowerShare) }}</strong>
                <small>{{ metricSource(discovery()?.nonFollowerShare, 'Reported platform share') }}</small>
              </div>
              <div>
                <span>US audience share</span>
                <strong>{{ percent(discovery()?.usAudienceShare) }}</strong>
                <small>{{ metricSource(discovery()?.usAudienceShare, 'Reported country share') }}</small>
              </div>
              <div>
                <span>Follows / 1,000 views</span>
                <strong>{{ decimal(discovery()?.followsPerThousandViews) }}</strong>
                <small>{{ metricSource(discovery()?.followsPerThousandViews, 'Calculated from imported totals') }}</small>
              </div>
            </div>
            <footer class="discovery-provenance">
              <div><strong>Source quality</strong><span>{{ discoverySourceStatement() }}</span></div>
              <div><strong>Algorithm</strong><code>{{ discovery()?.algorithmVersion || '—' }}</code></div>
              <div><strong>Audience observed</strong><span>{{ date(discovery()?.audienceObservedAt) }}</span></div>
              <div><strong>Country observed</strong><span>{{ date(discovery()?.countryObservedAt) }}</span></div>
            </footer>
          </section>

          <section class="section-band unavailable-metrics">
            <div><span>Hook rate</span><strong>—</strong><small>Not available in imported data</small></div>
            <div><span>Completion rate</span><strong>—</strong><small>Not available in imported data</small></div>
            <div><span>Average watch time</span><strong>—</strong><small>Not available in imported data</small></div>
            <div><span>Retention curve</span><strong>—</strong><small>Not available in imported data</small></div>
          </section>

          @if (summary()?.publicationContextLabel) { <div class="context-banner"><span>TEST CONTEXT</span><strong>{{ summary()!.publicationContextLabel }}</strong><p>Distribution conditions are separated from creative assessment.</p></div> }

          <section class="section-band timeline-panel">
            <div class="section-heading"><div><span class="eyebrow">{{ platformLabel().toUpperCase() }} PERFORMANCE</span><h2>Observed trajectory</h2></div><div class="chart-legend"><span><i class="legend-actual"></i> Views</span>@if (isMeta()) { <span><i class="event-key"></i> Reach Further</span> }<span><i class="intervention-key"></i> Manual intervention</span></div></div>
            @if (chartDots().length < 2) { <div class="state-panel compact-state"><strong>No trajectory available</strong><p>Import at least two timestamped cumulative checkpoints for {{ platformLabel() }}.</p></div> }
            @else {
              <div class="evidence-chart" role="img" [attr.aria-label]="platformLabel() + ' view trajectory'">
                <div class="chart-grid-line line-25"></div><div class="chart-grid-line line-50"></div><div class="chart-grid-line line-75"></div>
                @for (dot of chartDots(); track dot.label) { <i class="chart-dot" [style.left.%]="dot.left" [style.bottom.%]="dot.bottom" [title]="dot.label"></i> }
                @if (isMeta() && eventLeft() !== null) { <div class="event-marker" [style.left.%]="eventLeft()"><span>REACH FURTHER<br>FIRST OBSERVED</span></div> }
                @if (interventionLeft() !== null) { <div class="event-marker intervention-marker" [style.left.%]="interventionLeft()"><span>MANUAL<br>INTERVENTION</span></div> }
              </div>
            }
            <footer class="timeline-footer"><span>{{ date(trajectory()?.points?.[0]?.measuredAt) }}</span><strong>Only imported observations are shown.</strong><span>{{ date(trajectory()?.points?.at(-1)?.measuredAt) }}</span></footer>
          </section>

          @if (platform() === 'facebook' || platform() === 'instagram') {
            <section class="detail-metrics growth-metrics" aria-label="Platform growth profile">
              @if (platform() === 'facebook') {
                <div><span>First 24h</span><strong>{{ number(growth()?.views24h?.views) }}</strong><small>Observed checkpoint</small></div>
                <div><span>Views after 24h</span><strong>{{ number(growth()?.viewsAfter24h) }}</strong><small>Latest minus first 24h</small></div>
                <div><span>Facebook tail ratio</span><strong>{{ ratio(growth()?.facebookTailRatio) }}</strong><small>After 24h / first 24h</small></div>
              } @else {
                <div><span>First 6h</span><strong>{{ number(growth()?.views6h?.views) }}</strong><small>Observed checkpoint</small></div>
                <div><span>First 24h</span><strong>{{ number(growth()?.views24h?.views) }}</strong><small>Observed checkpoint</small></div>
                <div><span>Instagram burst ratio</span><strong>{{ ratio(growth()?.instagramBurstRatio) }}</strong><small>First 6h / first 24h</small></div>
              }
              <div><span>Data purity</span><strong>{{ trajectory()?.cleanOrganic === false ? 'INTERVENED' : trajectory()?.points?.length ? 'CLEAN ORGANIC' : '—' }}</strong><small>{{ trajectory()?.interventions?.length || 0 }} manual events</small></div>
            </section>
          }

      }
      }
      }

      @if (activeTab() === 'evidence' && activeFile()!.ingested) {
          <div class="detail-grid">
            <section class="section-band evidence-ledger">
              <div class="section-heading"><div><span class="eyebrow">EVIDENCE LEDGER</span><h2>{{ isMeta() ? 'Reach Further and interventions' : 'Manual interventions' }}</h2></div></div>
              @if (isMeta()) {
                @if (!summary()?.observations?.length) { <div class="state-panel compact-state"><strong>No explicit Reach Further evidence</strong><p>Views or reach never infer this state.</p></div> }
                @else { <ol class="evidence-list">@for (item of summary()!.observations; track item.id) { <li [class.is-superseded]="item.superseded"><span class="evidence-source">{{ item.source }}</span><div><strong>{{ item.stateValue }}</strong><small>{{ date(item.observedAt) }} · recorded {{ date(item.recordedAt) }}</small><p>{{ item.notes || 'No notes' }}</p>@if (item.evidenceRelativePath) { <code>{{ item.evidenceRelativePath }}</code> }</div><span class="verification" [class.is-verified]="item.manuallyVerified">{{ item.manuallyVerified ? 'VERIFIED' : 'UNVERIFIED' }}</span></li> }</ol> }
              }
              <div class="section-heading ledger-subheading"><div><span class="eyebrow">DATA PURITY</span><h2>Manual interventions</h2></div></div>
              @if (!trajectory()?.interventions?.length) { <div class="state-panel compact-state"><strong>No manual intervention recorded</strong><p>This platform trajectory has no persisted intervention event.</p></div> }
              @else { <ol class="evidence-list intervention-list">@for (item of trajectory()!.interventions; track item.id) { <li><span class="evidence-source evidence-source--rose">MANUAL</span><div><strong>{{ readable(item.eventType) }}</strong><small>{{ date(item.eventTime) }} · {{ number(item.viewsBefore) }} → {{ number(item.viewsAfter) }} views</small><p>{{ item.notes || 'No notes' }}</p></div><span class="verification">INTERVENED</span></li> }</ol> }
            </section>

            <aside class="state-entry-stack">
              @if (isMeta()) {
                <section class="section-band entry-panel"><span class="eyebrow">MANUAL OBSERVATION</span><h2>Record Meta state</h2><label class="check-row"><input type="checkbox" [checked]="reachObserved()" (change)="reachObserved.set(($any($event.target)).checked)"><span><strong>Reach Further observed</strong><small>Explicit Meta UI evidence only</small></span></label><label>Observed timestamp<input type="datetime-local" [value]="observedAt()" (input)="observedAt.set(($any($event.target)).value)"></label><label>Notes<textarea rows="3" [value]="notes()" (input)="notes.set(($any($event.target)).value)"></textarea></label><button class="button button--primary" type="button" [disabled]="!reachObserved() || !observedAt() || saving()" (click)="saveObservation()">{{ saving() ? 'Saving…' : 'Add observation' }}</button></section>
                <section class="section-band entry-panel"><span class="eyebrow">SCREENSHOT EVIDENCE</span><h2>Attach dashboard proof</h2><label class="compact-file"><input type="file" accept="image/png,image/jpeg,image/webp" (change)="selectEvidence($event)"><span>{{ evidence()?.name || 'Choose screenshot' }}</span></label><label class="check-row"><input type="checkbox" [checked]="verified()" (change)="verified.set(($any($event.target)).checked)"><span><strong>Manually verified</strong><small>OCR alone never checks this box</small></span></label><button class="button button--secondary" type="button" [disabled]="!evidence() || !observedAt() || saving()" (click)="uploadEvidence()">Attach evidence</button></section>
              }
              <section class="section-band entry-panel"><span class="eyebrow">PUBLICATION CONTEXT</span><h2>Existing platform publication</h2><label>Platform content ID<input type="text" [value]="platformContentId()" (input)="platformContentId.set(($any($event.target)).value)" placeholder="Meta post/reel ID"></label><label>Canonical publication URL<input type="url" [value]="platformUrl()" (input)="platformUrl.set(($any($event.target)).value)" placeholder="https://www.instagram.com/reel/…"></label><label>Published timestamp<input type="datetime-local" [value]="publishedAt()" (input)="publishedAt.set(($any($event.target)).value)"></label><label class="check-row"><input type="checkbox" [checked]="offPeak()" (change)="offPeak.set(($any($event.target)).checked)"><span><strong>Off-peak publish</strong><small>Marks a low-signal timing test</small></span></label><button class="button button--secondary" type="button" [disabled]="!platformContentId().trim() || !platformUrl().trim() || !publishedAt() || saving()" (click)="savePublication()">Save existing publication</button></section>
              <section class="section-band entry-panel"><span class="eyebrow">DATA PURITY EVENT</span><h2>Record manual engagement</h2><label>Intervention timestamp<input type="datetime-local" [value]="interventionAt()" (input)="interventionAt.set(($any($event.target)).value)"></label><div class="input-pair"><label>Views before<input type="number" min="0" [value]="viewsBefore()" (input)="viewsBefore.set(($any($event.target)).value)"></label><label>Views after<input type="number" min="0" [value]="viewsAfter()" (input)="viewsAfter.set(($any($event.target)).value)"></label></div><label>Notes<textarea rows="3" [value]="interventionNotes()" (input)="interventionNotes.set(($any($event.target)).value)"></textarea></label><button class="button button--secondary" type="button" [disabled]="!interventionAt() || saving()" (click)="saveIntervention()">Mark as intervened</button></section>
            </aside>
          </div>
      }
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VideoDetailPage implements OnDestroy {
  private readonly service = inject(CreativeIntelligenceService);
  private readonly route = inject(ActivatedRoute);
  private loadGeneration = 0;
  private analysisPollSubscription: Subscription | null = null;
  protected readonly platforms: Array<{ key: PlatformKey; label: string }> = [
    { key: 'facebook', label: 'Facebook' },
    { key: 'instagram', label: 'Instagram' },
    { key: 'tiktok', label: 'TikTok' },
    { key: 'youtube', label: 'YouTube' },
  ];
  protected readonly folderPath = signal('');
  protected readonly files = signal<MediaFile[]>([]);
  protected readonly activeFile = signal<MediaFile | null>(null);
  protected readonly video = signal<VideoApiRecord | null>(null);
  protected readonly videoVariants = signal<VideoVariant[]>([]);
  protected readonly variantsError = signal('');
  protected readonly captionPlatforms: Array<{ key: CaptionPlatform; label: string }> = [
    { key: 'INSTAGRAM', label: 'Instagram' },
    { key: 'FACEBOOK', label: 'Facebook' },
    { key: 'TIKTOK', label: 'TikTok' },
    { key: 'YOUTUBE', label: 'YouTube' },
  ];
  protected readonly publicationCopy = signal<Record<CaptionPlatform, PublicationCopy>>({ INSTAGRAM: { ...EMPTY_PUBLICATION_COPY }, FACEBOOK: { ...EMPTY_PUBLICATION_COPY }, TIKTOK: { ...EMPTY_PUBLICATION_COPY }, YOUTUBE: { ...EMPTY_PUBLICATION_COPY } });
  protected readonly captionPlatform = signal<CaptionPlatform>('INSTAGRAM');
  protected readonly currentCaptionPlatform = computed(() => this.captionPlatforms.find(item => item.key === this.captionPlatform()) || this.captionPlatforms[0]);
  protected readonly metadataLoading = signal(false);
  protected readonly metadataError = signal('');
  protected readonly savingCopy = signal<CaptionPlatform | null>(null);
  protected readonly summary = signal<ReachFurtherSummary | null>(null);
  protected readonly trajectory = signal<TrajectoryView | null>(null);
  protected readonly growth = signal<PlatformGrowthProfile | null>(null);
  protected readonly discovery = signal<DiscoveryProfile | null>(null);
  protected readonly platform = signal<PlatformKey>('facebook');
  protected readonly activeTab = signal<'overview' | 'creative' | 'publication' | 'performance' | 'evidence'>('overview');
  protected readonly creativeContext = signal<VideoCreativeContext | null>(null);
  protected readonly creativeContextLoading = signal(false);
  protected readonly creativeContextError = signal('');
  protected readonly characterRoles = ['UNKNOWN', 'PROTAGONIST', 'HELPER', 'RIVAL', 'OBSERVER', 'COMEDIC_TARGET', 'TEACHER'];
  protected readonly editingCharacters = signal(false);
  protected readonly draftCharacters = signal<DraftCharacter[]>([]);
  protected readonly characterRegistry = signal<CharacterIdentity[]>([]);
  protected readonly newCharacterName = signal('');
  protected readonly characterSaving = signal(false);
  protected readonly characterEditError = signal('');
  protected readonly availableRegistryCharacters = computed(() => {
    const used = new Set(this.draftCharacters().map(item => item.characterId));
    return this.characterRegistry().filter(item => item.active && !used.has(item.id));
  });
  protected readonly platformReadiness = signal<PlatformCreativeReadiness[]>([]);
  protected readonly loading = signal(true);
  protected readonly performanceLoading = signal(false);
  protected readonly performanceError = signal('');
  protected readonly ingesting = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly message = signal('');
  protected readonly reachObserved = signal(false);
  protected readonly observedAt = signal(this.localNow());
  protected readonly publishedAt = signal('');
  protected readonly platformContentId = signal('');
  protected readonly platformUrl = signal('');
  protected readonly notes = signal('');
  protected readonly evidence = signal<File | null>(null);
  protected readonly verified = signal(false);
  protected readonly offPeak = signal(false);
  protected readonly interventionAt = signal(this.localNow());
  protected readonly interventionNotes = signal('');
  protected readonly viewsBefore = signal('');
  protected readonly viewsAfter = signal('');
  protected readonly analysisStatus = signal<AnalysisStatus | null>(null);
  protected readonly analysisError = signal('');
  protected readonly triggeringAnalysis = signal(false);
  protected readonly analysisFeedback = signal('');
  protected readonly analysisFeedbackKind = signal<'info' | 'success' | 'error'>('info');
  protected readonly analysisRunActive = signal(false);

  protected readonly folderName = computed(() => this.readableFolder(this.folderPath()));
  protected readonly mediaUrl = computed(() => this.activeFile() ? this.service.mediaContentUrl(this.activeFile()!.relativePath) : '');
  protected readonly isPortrait = computed(() => {
    const source = this.video();
    return source !== null && source.height > source.width;
  });
  protected readonly variants = computed<VariantView[]>(() => {
    const variantTypeById = new Map(this.videoVariants().map(variant => [variant.id, variant.variantType]));
    const labelFor = (file: MediaFile): string => {
      const type = file.variantId ? variantTypeById.get(file.variantId) : undefined;
      return type ? (VARIANT_TYPE_LABELS[type] ?? type) : mediaVariant(file.name);
    };
    const totals = new Map<string, number>();
    const positions = new Map<string, number>();
    for (const file of this.files()) { const base = labelFor(file); totals.set(base, (totals.get(base) || 0) + 1); }
    return this.files().map(file => {
      const base = labelFor(file);
      const position = (positions.get(base) || 0) + 1;
      positions.set(base, position);
      return { ...file, label: (totals.get(base) || 0) > 1 ? `${base} ${position}` : base };
    });
  });
  protected readonly activeVariantLabel = computed(() => this.variants().find(item => item.relativePath === this.activeFile()?.relativePath)?.label || 'Original');
  protected readonly duration = computed(() => this.video() ? `${(this.video()!.durationMs / 1000).toFixed(1)}s` : '—');
  protected readonly platformLabel = computed(() => this.platforms.find(item => item.key === this.platform())?.label || 'Platform');
  protected readonly isMeta = computed(() => this.platform() === 'facebook' || this.platform() === 'instagram');
  protected readonly latestPoint = computed(() => this.trajectory()?.points?.at(-1) || null);
  protected readonly summaryMetrics = computed(() => {
    const point = this.latestPoint();
    return [
      { label: 'Views', value: point?.views },
      { label: 'Reach', value: point?.reach },
      { label: 'Likes', value: point?.likes },
      { label: 'Comments', value: point?.comments },
      { label: 'Shares', value: point?.shares },
      { label: 'Follows', value: point?.follows },
    ];
  });
  protected readonly chartDots = computed<ChartDot[]>(() => {
    const points = (this.trajectory()?.points || []).filter(point => point.views !== null);
    if (points.length < 2) return [];
    const minTime = Date.parse(points[0].measuredAt);
    const maxTime = Date.parse(points.at(-1)!.measuredAt);
    const maxViews = Math.max(...points.map(point => point.views || 0), 1);
    return points.map(point => ({ left: 4 + ((Date.parse(point.measuredAt) - minTime) / Math.max(maxTime - minTime, 1)) * 92, bottom: 8 + ((point.views || 0) / maxViews) * 82, label: `${this.date(point.measuredAt)} · ${this.number(point.views)} views` }));
  });
  protected readonly eventLeft = computed<number | null>(() => this.markerLeft(this.summary()?.firstObservedAt));
  protected readonly interventionLeft = computed<number | null>(() => this.markerLeft(this.trajectory()?.interventions?.[0]?.eventTime));

  constructor() {
    combineLatest([this.route.paramMap, this.route.queryParamMap]).subscribe(([params, query]) => {
      const id = params.get('id');
      const folder = query.get('folder');
      const file = query.get('file');
      if (id) this.loadById(id);
      else if (folder) this.loadFolder(folder, file);
      else { this.loading.set(false); this.error.set('Choose a creative folder from Video Library.'); }
    });
  }

  ngOnDestroy(): void { this.analysisPollSubscription?.unsubscribe(); }

  protected selectVariant(file: MediaFile): void { this.activateVariant(file); }
  protected selectPlatform(platform: PlatformKey): void { if (platform !== this.platform()) { this.platform.set(platform); this.loadPerformance(); } }
  protected ingestSelected(): void {
    const file = this.activeFile();
    if (!file) return;
    this.ingesting.set(true); this.message.set('');
    this.service.ingestVideo(file.relativePath).subscribe({
      next: () => { this.ingesting.set(false); this.message.set('Evidence record created. Performance remains empty until platform data is imported.'); this.loadFolder(this.folderPath(), file.relativePath); },
      error: response => { this.ingesting.set(false); this.message.set(response.error?.message || 'The video could not be ingested.'); },
    });
  }
  protected saveObservation(): void { const id = this.video()?.id; if (id) this.run(this.service.addReachFurther(id, new Date(this.observedAt()).toISOString(), this.notes(), this.platform()), 'Observation recorded.'); }
  protected uploadEvidence(): void { const id = this.video()?.id; const file = this.evidence(); if (id && file) this.run(this.service.uploadReachFurtherEvidence(id, file, new Date(this.observedAt()).toISOString(), this.notes(), this.verified(), this.platform()), 'Screenshot evidence attached.'); }
  protected savePublication(): void {
    const id = this.video()?.id;
    if (id) this.run(
      this.service.recordPublicationContext(
        id,
        new Date(this.publishedAt()).toISOString(),
        this.offPeak(),
        this.notes(),
        this.platform(),
        this.platformContentId().trim(),
        this.platformUrl().trim(),
      ),
      'Existing publication linked; no content was published.',
    );
  }
  protected saveIntervention(): void {
    const id = this.video()?.id;
    if (!id) return;
    const before = this.viewsBefore() === '' ? null : Number(this.viewsBefore());
    const after = this.viewsAfter() === '' ? null : Number(this.viewsAfter());
    this.run(this.service.addManualEngagementIntervention(id, new Date(this.interventionAt()).toISOString(), this.interventionNotes(), before, after, this.platform()), 'Manual intervention recorded.');
  }
  protected selectEvidence(event: Event): void { this.evidence.set((event.target as HTMLInputElement).files?.[0] || null); }
  protected triggerAnalysis(): void {
    const id = this.video()?.id;
    if (!id) return;
    this.triggeringAnalysis.set(true); this.analysisRunActive.set(true); this.analysisError.set('');
    this.analysisFeedbackKind.set('info'); this.analysisFeedback.set('Analysis is being queued…');
    this.service.triggerAnalysis(id, true).subscribe({
      next: status => { this.triggeringAnalysis.set(false); this.analysisStatus.set(status); this.analysisFeedback.set(status.jobState === 'RUNNING' ? 'Analysis is running…' : 'Analysis is queued…'); this.pollAnalysisStatus(id); },
      error: response => { this.triggeringAnalysis.set(false); this.analysisRunActive.set(false); this.analysisFeedbackKind.set('error'); this.analysisFeedback.set(response.error?.message || 'Could not start analysis.'); },
    });
  }
  protected updateCopy(platform: CaptionPlatform, field: 'title' | 'body' | 'hashtags' | 'tags', value: string): void {
    this.publicationCopy.update(current => ({ ...current, [platform]: { ...current[platform], [field]: value } }));
  }
  protected saveCopy(platform: CaptionPlatform): void {
    const copy = this.publicationCopy()[platform];
    if (!copy.sourcePath) return;
    this.savingCopy.set(platform); this.metadataError.set('');
    const content = this.metadataContent(copy, platform);
    this.service.updateMetadataFile(copy.sourcePath, content).subscribe({
      next: file => {
        this.publicationCopy.update(current => ({ ...current, [platform]: { ...current[platform], raw: file.content } }));
        this.savingCopy.set(null); this.message.set(`${platform} metadata saved.`);
      },
      error: response => { this.savingCopy.set(null); this.metadataError.set(response.error?.message || 'Publication metadata could not be saved.'); },
    });
  }
  protected date(value: string | null | undefined): string { return value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'; }
  protected number(value: number | null | undefined): string { return value === null || value === undefined ? '—' : new Intl.NumberFormat('en').format(value); }
  protected readable(value: string | null | undefined): string { return value ? value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()) : '—'; }
  protected characterMetrics(character: VideoCreativeContext['characters'][number]): string {
    const metrics = [
      character.screenTimeRatio === null ? null : `screen ${(character.screenTimeRatio * 100).toFixed(0)}%`,
      character.actionShare === null ? null : `action ${(character.actionShare * 100).toFixed(0)}%`,
      character.speakingShare === null ? null : `speaking ${(character.speakingShare * 100).toFixed(0)}%`,
    ].filter(Boolean);
    return metrics.length ? metrics.join(' · ') : 'No participation ratios recorded';
  }
  protected ratio(value: number | null | undefined): string { return value === null || value === undefined ? '—' : `${value.toFixed(2)}×`; }
  protected percent(value: number | null | undefined): string { return value === null || value === undefined ? '—' : `${value.toFixed(1)}%`; }
  protected decimal(value: number | null | undefined): string { return value === null || value === undefined ? '—' : value.toFixed(2); }
  protected analysisMetric(key: string, similarity = false): string {
    const source = similarity ? this.analysisStatus()?.visualSimilarity : this.analysisStatus()?.motion;
    const value = source?.[key];
    return typeof value === 'number' ? value.toFixed(4) : '—';
  }
  protected analysisNumber(group: 'motion' | 'sampling' | 'measurementQuality', key: string): string {
    const value = this.analysisStatus()?.[group]?.[key];
    return typeof value === 'number' ? value.toFixed(4).replace(/\.0000$/, '') : '—';
  }
  protected analysisPercent(group: 'measurementQuality' | 'sampling', key: string): string {
    const value = this.analysisStatus()?.[group]?.[key];
    return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—';
  }
  protected analysisFeatureValue(key: string): string {
    const value = this.analysisStatus()?.motion?.[key];
    return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—';
  }
  protected analysisList(group: 'motion' | 'sampling', key: string): Array<Record<string, any>> {
    const value = this.analysisStatus()?.[group]?.[key];
    return Array.isArray(value) ? value as Array<Record<string, any>> : [];
  }
  protected analysisListLength(group: 'motion' | 'sampling', key: string): string {
    return String(this.analysisList(group, key).length);
  }
  protected motionSummary(): string {
    const score = this.analysisStatus()?.motionHeuristicScore ?? this.analysisStatus()?.actionDnaScore;
    return typeof score !== 'number' ? 'Not evaluated' : score >= 80 ? 'Strong' : score >= 50 ? 'Moderate' : 'Limited';
  }
  protected variationSummary(): string {
    const value = this.analysisStatus()?.temporalProfile?.['variation'];
    return typeof value === 'string' ? this.readable(value) : 'Not evaluated';
  }
  protected similaritySummary(): string {
    const value = this.analysisStatus()?.visualSimilarity?.['firstLastVisualSimilarity'];
    if (typeof value !== 'number') return 'Not evaluated';
    return value >= 0.9 ? 'Very high' : value >= 0.75 ? 'High' : value >= 0.5 ? 'Moderate' : 'Low';
  }
  protected activityDropSummary(): string {
    const events = this.canonicalTemporalEvents();
    if (!events) return 'Not evaluated';
    const dips = events.filter(item => item['eventClass'] === 'LOCAL_ACTIVITY_DIP');
    const recoveries = events.filter(item => item['eventClass'] === 'LOCAL_ACTIVITY_RECOVERY');
    if (!dips.length) return 'None detected';
    return `${dips.length} local dip${dips.length === 1 ? '' : 's'}${recoveries.length ? ` · ${recoveries.length} recovery` : ''}`;
  }
  protected canonicalTemporalEvents(): Array<Record<string, any>> | null {
    const events = this.analysisStatus()?.temporalProfile?.['temporalActivityEvents'];
    return Array.isArray(events) ? events as Array<Record<string, any>> : null;
  }
  protected semanticEvidence(): Record<string, any> { return (this.analysisStatus()?.semanticVideoEvidence || {}) as Record<string, any>; }
  protected canonicalAssessments(): Record<string, any> { return (this.analysisStatus()?.temporalProfile?.['canonicalAssessments'] || {}) as Record<string, any>; }
  protected semanticStatus(): string { return String(this.semanticEvidence()['status'] || 'NOT_REQUESTED'); }
  protected semanticLimitation(): string {
    const limitations = this.semanticEvidence()['limitations'];
    return Array.isArray(limitations) && limitations.length ? String(limitations[0]) : 'Run the semantic pass when a vision-capable provider is configured.';
  }
  protected semanticValue(group: string, key: string): string {
    const value = (this.semanticEvidence()[group] as Record<string, any> | undefined)?.[key];
    return value === null || value === undefined || value === '' ? 'Unknown' : this.readable(String(value));
  }
  protected semanticNames(group: string): string {
    const values = this.semanticEvidence()[group];
    if (!Array.isArray(values) || !values.length) return 'Unknown';
    return values.map((value: any) => value?.canonicalName || value?.label || value?.objectType || 'Unknown').join(', ');
  }
  protected semanticBeatSummary(): string {
    const values = this.semanticEvidence()['beats'];
    if (!Array.isArray(values) || !values.length) return 'Unknown';
    return `${values.length} observed beat${values.length === 1 ? '' : 's'}`;
  }
  protected semanticConfidence(): string {
    const value = this.semanticEvidence()['confidence'];
    return typeof value === 'number' ? `${(value * 100).toFixed(0)}%` : 'Unknown';
  }
  protected semanticFingerprint(): string {
    const value = this.semanticEvidence()['semanticRequestFingerprint'];
    return typeof value === 'string' && value.length ? value : 'Not persisted for this run';
  }
  protected semanticFrameManifestCount(): number {
    const value = this.semanticEvidence()['semanticFrameManifest'];
    return Array.isArray(value) ? value.length : 0;
  }
  protected semanticConsistencyStatus(): string {
    const value = (this.semanticEvidence()['consistency'] as Record<string, any> | undefined)?.['status'];
    return value ? this.readable(String(value)) : 'Unknown';
  }
  protected semanticProviderModel(): string {
    const evidence = this.semanticEvidence();
    const provider = evidence['provider'] || (evidence['provenance'] as Record<string, any> | undefined)?.['provider'];
    const model = evidence['model'] || (evidence['provenance'] as Record<string, any> | undefined)?.['providerModel'];
    return provider || model ? `${provider || 'Unknown'} / ${model || 'Unknown'}` : 'Unknown';
  }
  protected semanticVersion(key: string): string {
    const value = (this.semanticEvidence()['semanticVersions'] as Record<string, any> | undefined)?.[key];
    return value ? String(value) : 'Unknown';
  }
  protected semanticFrameSelectorVersion(): string {
    const value = (this.semanticEvidence()['semanticFrameManifest'] as Array<Record<string, any>> | undefined);
    const selection = this.semanticEvidence()['frameSelection'] as Record<string, any> | undefined;
    return selection?.['version'] || (value?.length ? 'Persisted manifest' : 'Unknown');
  }
  protected semanticProviderCalls(): string {
    const value = (this.semanticEvidence()['provenance'] as Record<string, any> | undefined)?.['providerCallCount'];
    return typeof value === 'number' ? String(value) : 'Unknown';
  }
  protected timelineSegments(): Array<Record<string, any>> {
    const segments = this.analysisStatus()?.temporalProfile?.['segments'];
    return Array.isArray(segments) ? segments as Array<Record<string, any>> : [];
  }
  protected temporalVersion(): string {
    const value = this.analysisStatus()?.temporalProfile?.['version'];
    return typeof value === 'string' ? value : 'Not evaluated';
  }
  protected segmentActivityPercent(segment: Record<string, any>): number {
    const value = Number(segment['averageMotion']);
    return Number.isFinite(value) ? Math.max(2, Math.min(100, value * 100)) : 2;
  }
  protected percentValue(value: unknown): string {
    return typeof value === 'number' ? `${(value * 100).toFixed(0)}%` : '—';
  }
  protected segmentShape(segment: Record<string, any>): string {
    const value = Number(segment['relativeToPrevious']);
    if (!Number.isFinite(value) || Math.abs(value) < 0.08) return 'Stable';
    return value > 0 ? 'Rising' : 'Falling';
  }
  protected v4Dimension(key: string): string {
    if (key === 'planRenderFidelity') {
      const canonical = this.canonicalAssessments()['planRenderFidelity'];
      if (canonical && typeof canonical === 'object') {
        const value = canonical as Record<string, unknown>;
        return this.readable(String(value['status'] || 'NOT_AVAILABLE'));
      }
    }
    const dimensions = this.analysisStatus()?.temporalProfile?.['dimensions'];
    return dimensions && typeof dimensions === 'object' && typeof (dimensions as Record<string, unknown>)[key] === 'string'
      ? String((dimensions as Record<string, unknown>)[key]).replaceAll('_', ' ')
      : 'Not evaluated';
  }
  protected v4Repetition(): string {
    const repetition = this.analysisStatus()?.temporalProfile?.['repetitiveMotion'];
    if (!repetition || typeof repetition !== 'object') return 'Not evaluated';
    const classification = (repetition as Record<string, unknown>)['classification'];
    return typeof classification === 'string' ? this.readable(classification) : 'Not evaluated';
  }
  protected v5HoldSummary(): string {
    const temporal = this.canonicalAssessments()['temporalStructure'];
    if (temporal && typeof temporal === 'object') {
      const value = temporal as Record<string, unknown>;
      const interpretation = String(value['interpretation'] || 'NOT_AVAILABLE');
      if (interpretation === 'NOT_AVAILABLE') return 'Not available';
      return this.readable(interpretation);
    }
    const events = this.canonicalTemporalEvents();
    if (!events?.length) return 'None detected';
    const holds = events.filter(item => item['eventType'] === 'LIKELY_PURPOSEFUL_HOLD');
    return holds.length ? 'Likely purposeful hold' : 'No contextual hold evidence';
  }
  protected v5HookSummary(): string {
    const canonical = this.canonicalAssessments()['hook'];
    if (canonical && typeof canonical === 'object') return this.readable(String((canonical as Record<string, unknown>)['strength'] || 'UNKNOWN'));
    const hook = this.analysisStatus()?.temporalProfile?.['hook'];
    if (!hook || typeof hook !== 'object') return 'Not evaluated';
    return this.readable(String((hook as Record<string, unknown>)['status'] || 'NOT_EVALUATED'));
  }
  protected v5HookReason(): string {
    const canonical = this.canonicalAssessments()['hook'];
    if (canonical && typeof canonical === 'object') return String((canonical as Record<string, unknown>)['summary'] || 'Canonical hook assessment is available.');
    const hook = this.analysisStatus()?.temporalProfile?.['hook'];
    return hook && typeof hook === 'object' ? String((hook as Record<string, unknown>)['reason'] || 'Opening evidence is limited to sampled visual activity.') : 'Semantic hook evidence is not configured.';
  }
  protected v5HoldReason(): string {
    const temporal = this.canonicalAssessments()['temporalStructure'];
    if (temporal && typeof temporal === 'object') {
      const value = temporal as Record<string, unknown>;
      return String(value['summary'] || 'Canonical temporal evidence is available.');
    }
    const events = this.canonicalTemporalEvents();
    const event = events?.find(item => item['eventType'] === 'LIKELY_PURPOSEFUL_HOLD');
    if (!event) return 'Motion evidence alone cannot classify a local dip as a purposeful hold.';
    return `${event['startSeconds']}–${event['endSeconds']}s · ${String(event['reason'] || 'Context requires review.')}`;
  }
  protected v5ReboundSummary(): string {
    const payoff = this.canonicalAssessments()['payoff'];
    if (payoff && typeof payoff === 'object') return this.readable(String((payoff as Record<string, unknown>)['strength'] || 'UNKNOWN'));
    const rebound = this.analysisStatus()?.temporalProfile?.['reboundEvidence'];
    return rebound && typeof rebound === 'object' && (rebound as Record<string, unknown>)['sustainedRisingActivity'] === true ? 'Sustained rising activity' : 'Not established';
  }
  protected v5PayoffReason(): string {
    const payoff = this.canonicalAssessments()['payoff'];
    if (payoff && typeof payoff === 'object') {
      const value = payoff as Record<string, unknown>;
      return `${String(value['summary'] || 'Canonical payoff assessment.')} Motion support: ${String(value['motionRebound'] || 'UNKNOWN')}.`;
    }
    return 'Motion rebound is supporting evidence, not the payoff assessment.';
  }
  protected v5LoopSummary(): string {
    const canonical = this.canonicalAssessments()['loop'];
    if (canonical && typeof canonical === 'object') return String((canonical as Record<string, unknown>)['summary'] || 'Canonical loop assessment is available.');
    const similarity = this.analysisStatus()?.visualSimilarity?.['firstLastVisualSimilarity'];
    if (typeof similarity !== 'number') return 'Unknown';
    return `${similarity >= 0.9 ? 'Strong visual evidence' : similarity >= 0.75 ? 'Moderate visual evidence' : 'Weak visual evidence'} · semantic unknown`;
  }
  protected v5CoverageSummary(): string {
    const coverage = this.canonicalAssessments()['coverage'];
    if (coverage && typeof coverage === 'object' && typeof (coverage as Record<string, unknown>)['percent'] === 'number') return `${String((coverage as Record<string, unknown>)['percent'])}%`;
    const action = this.analysisStatus()?.temporalProfile?.['actionBeatNovelty'];
    const status = action && typeof action === 'object' ? (action as Record<string, unknown>)['status'] : null;
    return typeof status === 'string' ? this.readable(status) : 'Partial';
  }
  protected v5CoverageReason(): string {
    const coverage = this.canonicalAssessments()['coverage'];
    if (coverage && typeof coverage === 'object') {
      const missing = (coverage as Record<string, unknown>)['missing'];
      return Array.isArray(missing) && missing.length ? `Missing: ${missing.join(', ')}.` : 'Canonical evidence coverage is complete for the applicable dimensions.';
    }
    const fidelity = this.analysisStatus()?.temporalProfile?.['planRenderFidelity'];
    return fidelity && typeof fidelity === 'object' ? String((fidelity as Record<string, unknown>)['reason'] || 'Plan provenance was not supplied.') : 'Plan provenance was not supplied.';
  }
  protected v5TrendSummary(): string {
    const trend = this.analysisStatus()?.temporalProfile?.['temporalTrend'];
    if (!trend || typeof trend !== 'object') return 'Not evaluated';
    return this.readable(String((trend as Record<string, unknown>)['shape'] || (trend as Record<string, unknown>)['trendShape'] || 'UNKNOWN'));
  }
  protected v5TrendReason(): string {
    const trend = this.analysisStatus()?.temporalProfile?.['temporalTrend'];
    return trend && typeof trend === 'object'
      ? `${String((trend as Record<string, unknown>)['humanSummary'] || 'Temporal motion trend available.')} ${String((trend as Record<string, unknown>)['interpretation'] || 'Technical measurement only; not a performance prediction.')}`
      : 'Temporal motion trend is available in V5 analysis.';
  }
  protected temporalShapeSummary(): string { return this.v5TrendSummary(); }
  protected temporalShapeReason(): string { return this.v5TrendReason(); }
  protected v5RecoverySummary(): string {
    const trend = this.analysisStatus()?.temporalProfile?.['temporalTrend'];
    const recoveries = trend && typeof trend === 'object' ? (trend as Record<string, unknown>)['recoveryEvidence'] : null;
    if (!Array.isArray(recoveries)) return 'Not evaluated';
    if (!recoveries.length) return 'None detected';
    const full = recoveries.filter(item => (item as Record<string, unknown>)['status'] === 'FULL').length;
    return full ? `${full} full recovery` : `${recoveries.length} partial recovery`;
  }
  protected v5DipSummary(): string {
    const trend = this.analysisStatus()?.temporalProfile?.['temporalTrend'];
    const dips = trend && typeof trend === 'object' ? (trend as Record<string, unknown>)['localDipEvidence'] : null;
    return Array.isArray(dips) ? dips.length ? `${dips.length} local event${dips.length === 1 ? '' : 's'}` : 'None detected' : 'Not evaluated';
  }
  protected v5FinalReboundSummary(): string {
    const trend = this.analysisStatus()?.temporalProfile?.['temporalTrend'];
    const magnitude = trend && typeof trend === 'object' ? (trend as Record<string, unknown>)['finalReboundMagnitude'] : null;
    return typeof magnitude === 'number' && magnitude > 0 ? `+${magnitude.toFixed(3)}` : 'Not established';
  }
  protected structuralRiskSummary(): string {
    const value = this.analysisStatus()?.temporalProfile?.['structuralRetentionRisk'];
    if (!value || typeof value !== 'object') return 'Not evaluated';
    const windows = (value as Record<string, unknown>)['windows'];
    if (!Array.isArray(windows) || !windows.length) return 'None detected';
    const high = windows.filter(item => (item as Record<string, unknown>)['structuralRisk'] === 'HIGH').length;
    return high ? `${windows.length} window${windows.length === 1 ? '' : 's'} · ${high} high` : `${windows.length} window${windows.length === 1 ? '' : 's'}`;
  }
  protected lowMotionDurationSummary(): string {
    const evidence = this.analysisStatus()?.temporalProfile?.['lowMotionEvidence'];
    if (evidence && typeof evidence === 'object') {
      const value = evidence as Record<string, unknown>;
      if (value['status'] === 'AVAILABLE') {
        const duration = Number(value['durationSeconds']);
        const count = Number(value['intervalCount']);
        return duration > 0 ? `${duration.toFixed(1)}s · ${count} interval${count === 1 ? '' : 's'}` : 'None detected';
      }
      return this.readable(String(value['status'] || 'UNKNOWN'));
    }
    return 'Not evaluated';
  }
  protected timelineEventLabel(segment: Record<string, any>): string {
    const events = this.canonicalTemporalEvents();
    if (!events) return '—';
    const start = Number(segment['startSeconds']); const end = Number(segment['endSeconds']);
    const event = events.find(item => Number((item as Record<string, unknown>)['startSeconds']) < end && Number((item as Record<string, unknown>)['endSeconds']) > start) as Record<string, unknown> | undefined;
    return event ? this.readable(String(event['eventClass'] || event['type'] || 'EVENT')) : '—';
  }
  protected metricSource(value: number | null | undefined, available: string): string { return value === null || value === undefined ? 'No imported value' : available; }
  protected discoveryQualityLabel(): string { return this.discovery()?.dataQualityStatus === 'DERIVED_FROM_REPORTED_SHARES' ? 'REPORTED EVIDENCE' : 'NO COMPLETE DATA'; }
  protected discoverySourceStatement(): string { return this.discovery()?.dataQualityStatus === 'DERIVED_FROM_REPORTED_SHARES' ? 'Derived only from imported, platform-reported audience shares.' : 'No complete imported component set. Missing values are not estimated.'; }
  protected fileSize(value: number | null | undefined): string { if (value === null || value === undefined) return '—'; const units = ['B', 'KB', 'MB', 'GB']; let size = value; let index = 0; while (size >= 1024 && index < units.length - 1) { size /= 1024; index++; } return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`; }
  protected extension(name: string): string { return name.includes('.') ? name.split('.').pop()!.toUpperCase() : '—'; }

  private loadById(id: string): void {
    const generation = ++this.loadGeneration;
    this.loading.set(true); this.error.set('');
    this.service.getVideo(id).subscribe({
      next: video => {
        if (generation !== this.loadGeneration) return;
        const folder = this.parentPath(video.relativePath);
        this.folderPath.set(folder);
        this.loadCreativeContext(video.id);
        this.loadPlatformReadiness(video.id);
        this.loadPublicationCopy(folder, generation);
        this.service.getMediaFiles(folder, false).subscribe({
          next: files => { if (generation === this.loadGeneration) { const hdFiles = files.filter(file => isHdFile(file.name)); this.files.set(hdFiles); this.loading.set(false); const selected = hdFiles.find(file => file.relativePath === video.relativePath) || hdFiles[0]; if (selected) this.activateVariant(selected, video); else this.error.set('No HD media remains in this folder.'); } },
          error: response => { if (generation === this.loadGeneration) { this.loading.set(false); this.error.set(response.error?.message || 'Could not load folder variants.'); } },
        });
      },
      error: response => { if (generation === this.loadGeneration) { this.loading.set(false); this.error.set(response.error?.message || 'Could not load this evidence record.'); } },
    });
  }
  private loadPlatformReadiness(videoId: string): void {
    const platforms = ['INSTAGRAM_REELS', 'FACEBOOK_REELS', 'TIKTOK', 'YOUTUBE_SHORTS'];
    forkJoin(platforms.map(platform => this.service.getPlatformCreativeReadiness(videoId, platform))).subscribe({
      next: values => this.platformReadiness.set(values),
      error: () => this.platformReadiness.set([]),
    });
  }
  protected startEditCharacters(): void {
    this.characterEditError.set(''); this.newCharacterName.set('');
    this.draftCharacters.set((this.creativeContext()?.characters ?? []).map(item => ({
      characterId: item.id,
      name: item.name,
      participation: item.participation === 'PRIMARY' ? 'PRIMARY' : 'SECONDARY',
      role: this.characterRoles.includes(item.role) ? item.role : 'UNKNOWN',
    })));
    this.editingCharacters.set(true);
    this.service.getCharacters().subscribe({
      next: characters => this.characterRegistry.set(characters),
      error: response => this.characterEditError.set(response.error?.message || 'Character list could not be loaded.'),
    });
  }
  protected cancelEditCharacters(): void { this.editingCharacters.set(false); this.characterEditError.set(''); }
  protected setDraftParticipation(characterId: string, participation: 'PRIMARY' | 'SECONDARY'): void {
    // Only one main character per video: promoting one demotes the previous main character.
    this.draftCharacters.update(items => items.map(item =>
      item.characterId === characterId ? { ...item, participation }
        : participation === 'PRIMARY' && item.participation === 'PRIMARY' ? { ...item, participation: 'SECONDARY' } : item));
  }
  protected setDraftRole(characterId: string, role: string): void {
    this.draftCharacters.update(items => items.map(item => item.characterId === characterId ? { ...item, role } : item));
  }
  protected removeDraftCharacter(characterId: string): void {
    this.draftCharacters.update(items => items.filter(item => item.characterId !== characterId));
  }
  protected addRegistryCharacter(characterId: string): void {
    const character = this.characterRegistry().find(item => item.id === characterId);
    if (character) this.addDraftCharacter(character);
  }
  protected createDraftCharacter(): void {
    const name = this.newCharacterName().trim();
    if (!name || this.characterSaving()) return;
    const existing = this.characterRegistry().find(item => item.name.toLowerCase() === name.toLowerCase());
    if (existing) { this.addDraftCharacter(existing); this.newCharacterName.set(''); return; }
    this.characterSaving.set(true); this.characterEditError.set('');
    this.service.createCharacter(name).subscribe({
      next: character => {
        this.characterRegistry.update(items => [...items, character]);
        this.addDraftCharacter(character); this.newCharacterName.set(''); this.characterSaving.set(false);
      },
      error: response => { this.characterSaving.set(false); this.characterEditError.set(response.error?.message || 'Character could not be created.'); },
    });
  }
  protected saveCharacters(): void {
    const videoId = this.video()?.id;
    if (!videoId || this.characterSaving()) return;
    this.characterSaving.set(true); this.characterEditError.set('');
    const payload: VideoCharacterAssignment[] = this.draftCharacters().map(({ characterId, participation, role }) => ({ characterId, participation, role }));
    this.service.replaceVideoCharacters(videoId, payload).subscribe({
      next: () => { this.characterSaving.set(false); this.editingCharacters.set(false); this.loadCreativeContext(videoId); },
      error: response => { this.characterSaving.set(false); this.characterEditError.set(response.error?.message || 'Characters could not be saved.'); },
    });
  }
  private addDraftCharacter(character: CharacterIdentity): void {
    if (this.draftCharacters().some(item => item.characterId === character.id)) return;
    const hasPrimary = this.draftCharacters().some(item => item.participation === 'PRIMARY');
    this.draftCharacters.update(items => [...items, { characterId: character.id, name: character.name, participation: hasPrimary ? 'SECONDARY' : 'PRIMARY', role: 'UNKNOWN' }]);
  }
  private loadCreativeContext(videoId: string): void {
    this.creativeContextLoading.set(true); this.creativeContextError.set(''); this.creativeContext.set(null);
    this.service.getVideoCreativeContext(videoId).subscribe({
      next: context => { this.creativeContext.set(context); this.creativeContextLoading.set(false); },
      error: response => { this.creativeContextLoading.set(false); this.creativeContextError.set(response.error?.message || 'Creative context could not be loaded.'); },
    });
  }
  private loadFolder(folder: string, requestedFile: string | null): void {
    const generation = ++this.loadGeneration;
    this.loading.set(true); this.error.set(''); this.folderPath.set(folder);
    this.loadPublicationCopy(folder, generation);
    this.service.getMediaFiles(folder, false).subscribe({
      next: files => {
        if (generation !== this.loadGeneration) return;
        const hdFiles = files.filter(file => isHdFile(file.name));
        this.files.set(hdFiles); this.loading.set(false);
        const selected = hdFiles.find(file => file.relativePath === requestedFile) || hdFiles[0];
        if (selected) this.activateVariant(selected); else this.error.set('No HD media remains in this folder.');
      },
      error: response => { if (generation === this.loadGeneration) { this.loading.set(false); this.error.set(response.error?.message || 'Could not load folder variants.'); } },
    });
  }

  private loadPublicationCopy(folder: string, generation: number): void {
    this.metadataLoading.set(true);
    this.metadataError.set('');
    this.publicationCopy.set({ INSTAGRAM: { ...EMPTY_PUBLICATION_COPY }, FACEBOOK: { ...EMPTY_PUBLICATION_COPY }, TIKTOK: { ...EMPTY_PUBLICATION_COPY }, YOUTUBE: { ...EMPTY_PUBLICATION_COPY } });
    const base = folder.replace(/\\+$/, '');
    forkJoin({
      social: this.service.getMetadataFile(`${base}/social.md`).pipe(catchError(() => of(null))),
      instagram: this.service.getMetadataFile(`${base}/03_instagram_social.txt`).pipe(catchError(() => of(null))),
      youtube: this.service.getMetadataFile(`${base}/youtube.md`).pipe(catchError(() => of(null))),
    }).subscribe({
      next: files => {
        if (generation !== this.loadGeneration) return;
        const social = files.social ? this.parseMetadata(files.social, 'social.md') : EMPTY_PUBLICATION_COPY;
        const instagram = files.instagram ? this.parseInstagramMetadata(files.instagram) : EMPTY_PUBLICATION_COPY;
        const youtube = files.youtube ? this.parseMetadata(files.youtube, 'youtube.md') : EMPTY_PUBLICATION_COPY;
        this.publicationCopy.set({
          INSTAGRAM: instagram.sourcePath ? instagram : this.socialCopy(social, 'FACEBOOK'),
          FACEBOOK: this.socialCopy(social, 'FACEBOOK'),
          TIKTOK: this.socialCopy(social, 'TIKTOK'),
          YOUTUBE: youtube,
        });
        this.metadataLoading.set(false);
      },
      error: response => { if (generation === this.loadGeneration) { this.metadataLoading.set(false); this.metadataError.set(response.error?.message || 'Publication metadata could not be loaded.'); } },
    });
  }

  private parseMetadata(file: MetadataFile, sourceFile: string): PublicationCopy {
    const section = (...headings: string[]): string => headings.map(heading => this.markdownField(file.content, heading)).find(Boolean) || '';
    return {
      sourceFile,
      sourcePath: file.relativePath,
      raw: file.content,
      title: section('YouTube Title', 'YouTube Shorts title', 'Title'),
      body: section('YouTube Description', 'Caption', 'Primary Instagram / Facebook caption'),
      hashtags: section('Hashtags'),
      tags: section('YouTube Tags', 'Tags'),
    };
  }

  private parseInstagramMetadata(file: MetadataFile): PublicationCopy {
    const parts = this.splitHashtags(file.content);
    return { sourceFile: '03_instagram_social.txt', sourcePath: file.relativePath, raw: file.content, title: '', body: parts.body, hashtags: parts.hashtags, tags: '' };
  }

  private socialCopy(copy: PublicationCopy, platform: CaptionPlatform): PublicationCopy {
    const source = copy.raw;
    if (!source) return copy;
    const sectionLabel = platform === 'TIKTOK' ? 'TikTok caption' : 'Meta / Facebook caption';
    const labeled = this.splitHashtags(this.labeledSection(source, sectionLabel));
    return {
      ...copy,
      title: this.markdownField(source, 'Title') || copy.title,
      body: platform === 'TIKTOK'
        ? (labeled.body || this.markdownField(source, 'Short caption') || this.markdownField(source, 'Alternate short caption') || this.markdownField(source, 'Caption') || copy.body)
        : (labeled.body || this.markdownField(source, 'Caption') || this.markdownField(source, 'Primary Instagram / Facebook caption') || copy.body),
      hashtags: labeled.hashtags || this.markdownField(source, 'Hashtags') || copy.hashtags,
    };
  }

  private metadataContent(copy: PublicationCopy, platform: CaptionPlatform): string {
    if (copy.sourceFile === '03_instagram_social.txt') {
      return [copy.body.trim(), copy.hashtags.trim()].filter(Boolean).join('\n') + '\n';
    }
    if (platform === 'YOUTUBE') {
      let content = copy.raw;
      content = this.replaceMarkdownField(content, ['YouTube Title', 'YouTube Shorts title', 'Title'], copy.title);
      content = this.replaceMarkdownField(content, ['YouTube Description', 'Description'], copy.body);
      content = this.replaceMarkdownField(content, ['YouTube Tags', 'Tags'], copy.tags);
      content = this.replaceMarkdownField(content, ['Hashtags'], copy.hashtags);
      return content;
    }
    const label = platform === 'TIKTOK' ? 'TikTok caption' : 'Meta / Facebook caption';
    return this.replaceLabeledSection(copy.raw, label, [copy.body.trim(), copy.hashtags.trim()].filter(Boolean).join('\n'));
  }

  private markdownField(content: string, heading: string): string {
    const lines = content.split(/\r?\n/);
    const start = lines.findIndex(line => line.trim().toLowerCase() === `## ${heading.toLowerCase()}`);
    if (start < 0) return '';
    const end = lines.slice(start + 1).findIndex(line => /^##\s+/.test(line.trim()));
    return lines.slice(start + 1, end < 0 ? undefined : start + 1 + end).join('\n').trim();
  }
  private splitHashtags(content: string): { body: string; hashtags: string } {
    const lines = content.split(/\r?\n/);
    const hashLines = lines.filter(line => line.trim().startsWith('#'));
    return { body: lines.filter(line => !line.trim().startsWith('#')).join('\n').trim(), hashtags: hashLines.join('\n').trim() };
  }
  private labeledSection(content: string, label: string): string {
    const lines = content.split(/\r?\n/);
    const start = lines.findIndex(line => line.trim().toLowerCase() === `${label.toLowerCase()}:`);
    if (start < 0) return '';
    const end = lines.slice(start + 1).findIndex(line => /^(?:[A-Za-z][^:]{0,80}):\s*$/.test(line.trim()));
    return lines.slice(start + 1, end < 0 ? undefined : start + 1 + end).join('\n').trim();
  }
  private replaceLabeledSection(content: string, label: string, value: string): string {
    const lines = content.split(/\r?\n/);
    const start = lines.findIndex(line => line.trim().toLowerCase() === `${label.toLowerCase()}:`);
    if (start < 0) return content;
    const end = lines.slice(start + 1).findIndex(line => /^(?:[A-Za-z][^:]{0,80}):\s*$/.test(line.trim()));
    const endIndex = end < 0 ? lines.length : start + 1 + end;
    return [...lines.slice(0, start + 1), '', value, '', ...lines.slice(endIndex)].join('\n').replace(/\n{4,}/g, '\n\n\n');
  }
  private replaceMarkdownField(content: string, headings: string[], value: string): string {
    const lines = content.split(/\r?\n/);
    const headingIndex = lines.findIndex(line => headings.some(heading => line.trim().toLowerCase() === `## ${heading.toLowerCase()}`));
    if (headingIndex < 0) return content;
    const end = lines.slice(headingIndex + 1).findIndex(line => /^##\s+/.test(line.trim()));
    const endIndex = end < 0 ? lines.length : headingIndex + 1 + end;
    return [...lines.slice(0, headingIndex + 1), '', value, '', ...lines.slice(endIndex)].join('\n').replace(/\n{4,}/g, '\n\n\n');
  }
  private activateVariant(file: MediaFile, knownVideo?: VideoApiRecord): void {
    this.activeFile.set(file); this.message.set(''); this.video.set(null); this.creativeContext.set(null); this.clearPerformance();
    this.analysisStatus.set(null);
    if (!file.ingested || !file.videoId) { this.videoVariants.set([]); this.analysisPollSubscription?.unsubscribe(); return; }
    if (knownVideo?.id === file.videoId) { this.video.set(knownVideo); this.loadCreativeContext(knownVideo.id); this.loadPerformance(); this.loadVariants(file.videoId); this.pollAnalysisStatus(file.videoId); return; }
    this.service.getVideo(file.videoId).subscribe({ next: video => { if (this.activeFile()?.relativePath === file.relativePath) { this.video.set(video); this.loadCreativeContext(video.id); this.loadPerformance(); this.loadVariants(video.id); this.pollAnalysisStatus(video.id); } }, error: response => this.message.set(response.error?.message || 'Technical metadata could not be loaded.') });
  }
  private loadVariants(videoId: string): void {
    this.variantsError.set('');
    this.service.listVariants(videoId).subscribe({ next: variants => this.videoVariants.set(variants), error: response => { this.videoVariants.set([]); this.variantsError.set(response.error?.message || 'Variant history could not be loaded.'); } });
  }
  protected pollAnalysisStatus(videoId: string): void {
    this.analysisPollSubscription?.unsubscribe();
    this.analysisError.set('');
    let previousState = this.analysisStatus()?.jobState;
    this.analysisPollSubscription = interval(5000)
      .pipe(
        startWith(0),
        switchMap(() => this.service.getAnalysisStatus(videoId).pipe(catchError(response => { this.analysisError.set(response.error?.message || 'The analysis service did not respond.'); return of(null); }))),
      )
      .subscribe(status => {
        if (status === null) return;
        this.analysisStatus.set(status);
        if (this.analysisRunActive()) {
          if (status.jobState === 'QUEUED') { this.analysisFeedbackKind.set('info'); this.analysisFeedback.set('Analysis is queued…'); }
          if (status.jobState === 'RUNNING') { this.analysisFeedbackKind.set('info'); this.analysisFeedback.set('Analysis is running…'); }
          if (status.jobState === 'COMPLETED' && previousState !== 'COMPLETED') {
            const semanticStatus = String(status.semanticVideoEvidence?.['status'] || 'NOT_REQUESTED');
            const partial = ['NOT_REQUESTED', 'NOT_CONFIGURED', 'SERVICE_ERROR', 'FAILED'].includes(semanticStatus);
            this.analysisFeedbackKind.set(partial ? 'info' : 'success');
            this.analysisFeedback.set(partial ? `Deterministic analysis completed; semantic analysis is ${semanticStatus.replaceAll('_', ' ').toLowerCase()}.` : 'Analysis completed. Results updated.');
            this.analysisRunActive.set(false);
          }
          if (status.jobState === 'FAILED') {
            this.analysisFeedbackKind.set('error'); this.analysisFeedback.set(status.errorMessage || 'Analysis failed.'); this.analysisRunActive.set(false);
          }
        }
        previousState = status.jobState;
        if (status.jobState === 'COMPLETED' || status.jobState === 'FAILED') {
          this.analysisPollSubscription?.unsubscribe();
        }
      });
  }
  protected loadPerformance(): void {
    const id = this.video()?.id;
    if (!id) return;
    const platform = this.platform();
    this.performanceLoading.set(true); this.performanceError.set(''); this.clearPerformance();
    forkJoin({
      summary: this.service.getReachFurther(id, platform).pipe(catchError(response => { this.performanceError.set(response.error?.message || 'Summary evidence could not be loaded.'); return of(null); })),
      trajectory: this.service.getTrajectory(id, platform).pipe(catchError(response => { this.performanceError.set(response.error?.message || 'Trajectory evidence could not be loaded.'); return of(null); })),
      growth: this.service.getPlatformGrowth(id, platform).pipe(catchError(response => { this.performanceError.set(response.error?.message || 'Growth evidence could not be loaded.'); return of(null); })),
      discovery: this.service.getDiscoveryProfile(id, platform).pipe(catchError(response => { this.performanceError.set(response.error?.message || 'Discovery evidence could not be loaded.'); return of(null); })),
    }).subscribe(data => {
      if (this.video()?.id !== id || this.platform() !== platform) return;
      this.summary.set(data.summary); this.trajectory.set(data.trajectory); this.growth.set(data.growth); this.discovery.set(data.discovery);
      this.offPeak.set(data.summary?.offPeakPublish === true);
      this.publishedAt.set(data.summary?.publishedAt ? this.localValue(data.summary.publishedAt) : '');
      this.platformContentId.set(data.summary?.platformContentId || '');
      this.platformUrl.set(data.summary?.platformUrl || '');
      this.performanceLoading.set(false);
    });
  }
  private clearPerformance(): void { this.summary.set(null); this.trajectory.set(null); this.growth.set(null); this.discovery.set(null); }
  private run(request: Observable<unknown>, success: string): void {
    this.saving.set(true); this.message.set('');
    request.subscribe({ next: () => { this.saving.set(false); this.message.set(success); this.loadPerformance(); }, error: response => { this.saving.set(false); this.message.set(response.error?.message || 'Could not save evidence.'); } });
  }
  private markerLeft(value: string | null | undefined): number | null {
    const points = this.trajectory()?.points || [];
    if (!value || points.length < 2) return null;
    const min = Date.parse(points[0].measuredAt); const max = Date.parse(points.at(-1)!.measuredAt);
    return Math.max(4, Math.min(96, 4 + ((Date.parse(value) - min) / Math.max(max - min, 1)) * 92));
  }
  private parentPath(path: string): string { return path.includes('/') ? path.slice(0, path.lastIndexOf('/')) : '.'; }
  private readableFolder(path: string): string { const name = path.split('/').filter(Boolean).pop() || path; return name.replace(/^\d+[-_]?/, '').replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase()); }
  private localNow(): string { return this.localValue(new Date().toISOString()); }
  private localValue(value: string): string { const date = new Date(value); const offset = date.getTimezoneOffset() * 60000; return new Date(date.getTime() - offset).toISOString().slice(0, 16); }
}
