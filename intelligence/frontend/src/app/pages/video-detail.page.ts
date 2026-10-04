import { ChangeDetectionStrategy, Component, computed, inject, OnDestroy, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, combineLatest, forkJoin, interval, Observable, of, startWith, Subscription, switchMap } from 'rxjs';
import {
  AnalysisStatus,
  CreativeIntelligenceService,
  DiscoveryProfile,
  MediaFile,
  PlatformGrowthProfile,
  ReachFurtherSummary,
  TrajectoryView,
  VideoApiRecord,
  VideoVariant,
} from '../core/creative-intelligence.service';
import { mediaVariant } from './video-library.page';

type PlatformKey = 'facebook' | 'instagram' | 'tiktok' | 'youtube';
interface ChartDot { left: number; bottom: number; label: string; }
interface VariantView extends MediaFile { label: string; }

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
  imports: [RouterLink],
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
          <div class="video-stage">
            <video controls preload="metadata" [src]="mediaUrl()" [attr.aria-label]="'Preview ' + activeFile()!.name"></video>
          </div>
          <div class="selected-file-bar">
            <div><span class="eyebrow">SELECTED VARIANT</span><strong [title]="activeFile()!.name">{{ activeVariantLabel() }}</strong><small [title]="activeFile()!.name">{{ activeFile()!.name }}</small></div>
            @if (!activeFile()!.ingested) { <button class="button button--primary" type="button" [disabled]="ingesting()" (click)="ingestSelected()">{{ ingesting() ? 'Ingesting…' : 'Ingest for analysis' }}</button> }
            @else { <span class="status-badge status-badge--green">Evidence record linked</span> }
          </div>
        </div>

        <aside class="variant-rail" aria-label="Video variants">
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
        <div class="section-heading"><div><span class="eyebrow">CREATIVE ANALYSIS</span><h2 id="creative-analysis-heading">Automated quality assessment</h2></div>
          @if (!analysisStatus()?.hasCompletedAnalysis) { <button class="button button--primary" type="button" [disabled]="triggeringAnalysis() || analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING'" (click)="triggerAnalysis()">{{ triggeringAnalysis() ? 'Starting…' : analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING' ? (analysisStatus()!.jobState === 'QUEUED' ? 'Queued…' : 'Running…') : 'Trigger analysis' }}</button> }
        </div>
        @if (analysisStatus()?.hasCompletedAnalysis) {
          <dl class="technical-facts">
            <div><dt>Classification</dt><dd>{{ analysisStatus()!.classification }}</dd></div>
            <div><dt>Action DNA score</dt><dd>{{ decimal(analysisStatus()!.actionDnaScore) }}</dd></div>
            <div><dt>Confidence</dt><dd>{{ decimal(analysisStatus()!.confidence) }}</dd></div>
            <div><dt>Reason</dt><dd>{{ analysisStatus()!.reason }}</dd></div>
            <div><dt>Analysis version</dt><dd><code>{{ analysisStatus()!.analysisVersion }}</code></dd></div>
            @if (analysisStatus()!.storyboardPath) { <div><dt>Storyboard</dt><dd><code>{{ analysisStatus()!.storyboardPath }}</code></dd></div> }
          </dl>
        } @else if (analysisStatus()?.jobState === 'FAILED') {
          <div class="state-panel state-panel--error compact-state"><strong>Analysis failed</strong><p>{{ analysisStatus()!.errorMessage || 'The analysis job failed.' }}</p></div>
        } @else if (analysisStatus()?.jobState === 'QUEUED' || analysisStatus()?.jobState === 'RUNNING') {
          <div class="state-panel compact-state"><span class="spinner"></span><strong>{{ analysisStatus()!.jobState === 'QUEUED' ? 'Queued for analysis' : 'Analysis running' }}</strong></div>
        } @else {
          <div class="state-panel compact-state"><strong>No analysis yet</strong><p>Trigger analysis to classify this creative.</p></div>
        }
      </section>

      @if (!activeFile()!.ingested) {
        <section class="section-band un-ingested-state"><span aria-hidden="true">i</span><div><strong>Performance evidence requires ingest and imported platform data</strong><p>This mounted file remains playable. Ingesting creates its evidence identity; it does not invent metrics.</p></div></section>
      } @else {
        <nav class="platform-tabs" aria-label="Performance platform">
          @for (item of platforms; track item.key) { <button type="button" [class.is-active]="platform() === item.key" [attr.aria-current]="platform() === item.key ? 'page' : null" (click)="selectPlatform(item.key)">{{ item.label }}</button> }
        </nav>

        @if (performanceLoading()) {
          <section class="state-panel section-band compact-state"><span class="spinner"></span><strong>Loading {{ platformLabel() }} evidence</strong></section>
        } @else {
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
  protected readonly summary = signal<ReachFurtherSummary | null>(null);
  protected readonly trajectory = signal<TrajectoryView | null>(null);
  protected readonly growth = signal<PlatformGrowthProfile | null>(null);
  protected readonly discovery = signal<DiscoveryProfile | null>(null);
  protected readonly platform = signal<PlatformKey>('facebook');
  protected readonly loading = signal(true);
  protected readonly performanceLoading = signal(false);
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
  protected readonly triggeringAnalysis = signal(false);

  protected readonly folderName = computed(() => this.readableFolder(this.folderPath()));
  protected readonly mediaUrl = computed(() => this.activeFile() ? this.service.mediaContentUrl(this.activeFile()!.relativePath) : '');
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
    this.triggeringAnalysis.set(true);
    this.service.triggerAnalysis(id).subscribe({
      next: status => { this.triggeringAnalysis.set(false); this.analysisStatus.set(status); this.pollAnalysisStatus(id); },
      error: response => { this.triggeringAnalysis.set(false); this.message.set(response.error?.message || 'Could not start analysis.'); },
    });
  }
  protected date(value: string | null | undefined): string { return value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—'; }
  protected number(value: number | null | undefined): string { return value === null || value === undefined ? '—' : new Intl.NumberFormat('en').format(value); }
  protected readable(value: string | null | undefined): string { return value ? value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()) : '—'; }
  protected ratio(value: number | null | undefined): string { return value === null || value === undefined ? '—' : `${value.toFixed(2)}×`; }
  protected percent(value: number | null | undefined): string { return value === null || value === undefined ? '—' : `${value.toFixed(1)}%`; }
  protected decimal(value: number | null | undefined): string { return value === null || value === undefined ? '—' : value.toFixed(2); }
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
        this.service.getMediaFiles(folder, false).subscribe({
          next: files => { if (generation === this.loadGeneration) { this.files.set(files); this.loading.set(false); const selected = files.find(file => file.relativePath === video.relativePath) || files[0]; if (selected) this.activateVariant(selected, video); else this.error.set('No playable media remains in this folder.'); } },
          error: response => { if (generation === this.loadGeneration) { this.loading.set(false); this.error.set(response.error?.message || 'Could not load folder variants.'); } },
        });
      },
      error: response => { if (generation === this.loadGeneration) { this.loading.set(false); this.error.set(response.error?.message || 'Could not load this evidence record.'); } },
    });
  }
  private loadFolder(folder: string, requestedFile: string | null): void {
    const generation = ++this.loadGeneration;
    this.loading.set(true); this.error.set(''); this.folderPath.set(folder);
    this.service.getMediaFiles(folder, false).subscribe({
      next: files => {
        if (generation !== this.loadGeneration) return;
        this.files.set(files); this.loading.set(false);
        const selected = files.find(file => file.relativePath === requestedFile) || files[0];
        if (selected) this.activateVariant(selected); else this.error.set('No supported video files were found in this folder.');
      },
      error: response => { if (generation === this.loadGeneration) { this.loading.set(false); this.error.set(response.error?.message || 'Could not load folder variants.'); } },
    });
  }
  private activateVariant(file: MediaFile, knownVideo?: VideoApiRecord): void {
    this.activeFile.set(file); this.message.set(''); this.video.set(null); this.clearPerformance();
    this.analysisStatus.set(null);
    if (!file.ingested || !file.videoId) { this.videoVariants.set([]); this.analysisPollSubscription?.unsubscribe(); return; }
    if (knownVideo?.id === file.videoId) { this.video.set(knownVideo); this.loadPerformance(); this.loadVariants(file.videoId); this.pollAnalysisStatus(file.videoId); return; }
    this.service.getVideo(file.videoId).subscribe({ next: video => { if (this.activeFile()?.relativePath === file.relativePath) { this.video.set(video); this.loadPerformance(); this.loadVariants(video.id); this.pollAnalysisStatus(video.id); } }, error: response => this.message.set(response.error?.message || 'Technical metadata could not be loaded.') });
  }
  private loadVariants(videoId: string): void {
    this.service.listVariants(videoId).subscribe({ next: variants => this.videoVariants.set(variants), error: () => this.videoVariants.set([]) });
  }
  private pollAnalysisStatus(videoId: string): void {
    this.analysisPollSubscription?.unsubscribe();
    this.analysisPollSubscription = interval(5000)
      .pipe(
        startWith(0),
        switchMap(() => this.service.getAnalysisStatus(videoId).pipe(catchError(() => of(null)))),
      )
      .subscribe(status => {
        if (status === null) return;
        this.analysisStatus.set(status);
        if (status.jobState === 'COMPLETED' || status.jobState === 'FAILED') {
          this.analysisPollSubscription?.unsubscribe();
        }
      });
  }
  private loadPerformance(): void {
    const id = this.video()?.id;
    if (!id) return;
    const platform = this.platform();
    this.performanceLoading.set(true); this.clearPerformance();
    forkJoin({
      summary: this.service.getReachFurther(id, platform).pipe(catchError(() => of(null))),
      trajectory: this.service.getTrajectory(id, platform).pipe(catchError(() => of(null))),
      growth: this.service.getPlatformGrowth(id, platform).pipe(catchError(() => of(null))),
      discovery: this.service.getDiscoveryProfile(id, platform).pipe(catchError(() => of(null))),
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
