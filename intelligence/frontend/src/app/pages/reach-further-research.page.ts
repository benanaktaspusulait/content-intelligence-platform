import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  CreativeIntelligenceService,
  PlatformTempoResearch,
  ReachFurtherComparison,
  ReachFurtherResearch,
} from '../core/creative-intelligence.service';

@Component({
  selector: 'app-reach-further-research-page',
  imports: [RouterLink],
  template: `
    <header class="page-header"><div><span class="eyebrow">POST-PUBLISH PLATFORM SIGNAL</span><h1>Reach Further Research</h1><p>Track what happened after the Meta state was first observed.</p></div><span class="status-badge status-badge--amber">OBSERVATIONAL</span></header>
    @if (loading()) { <section class="state-panel section-band"><span class="spinner"></span><strong>Calculating descriptive cohorts</strong></section> }
    @else if (error()) { <section class="state-panel section-band"><strong>Research view unavailable</strong><p>{{ error() }}</p></section> }
    @else if (research(); as data) {
      <div class="causal-notice"><span>!</span><p><strong>Evidence, not an explanation.</strong> {{ data.disclaimer }}</p></div>
      <section class="detail-metrics research-metrics"><div><span>Observed videos</span><strong>{{ data.observedVideos }}</strong><small>Explicit evidence only</small></div><div><span>Median at first observation</span><strong>{{ number(data.medianViewsAtFirstObservation) }}</strong><small>Views</small></div><div><span>Median 24h result</span><strong>{{ number(data.median24hViews) }}</strong><small>Available cases</small></div><div><span>Median 7d result</span><strong>{{ number(data.median7dViews) }}</strong><small>Available cases</small></div></section>

      @if (tempo(); as platformTempo) {
        <section class="section-band comparison-panel tempo-panel"><div class="section-heading"><div><span class="eyebrow">PLATFORM-SPECIFIC TIME PROFILE</span><h2>Burst and long-tail signals</h2></div><span class="status-badge">CLEAN ORGANIC ONLY</span></div><div class="comparison-groups"><div><span>Instagram burst ratio</span><strong>{{ ratio(platformTempo.instagram.medianRatio) }}</strong><small>first 6h / first 24h · n={{ platformTempo.instagram.ratioEligibleCount }}</small></div><div><span>Facebook tail ratio</span><strong>{{ ratio(platformTempo.facebook.medianRatio) }}</strong><small>after 24h / first 24h · n={{ platformTempo.facebook.ratioEligibleCount }}</small></div><div><span>Excluded purity risk</span><strong>{{ platformTempo.instagram.intervenedExcludedCount + platformTempo.facebook.intervenedExcludedCount }}</strong><small>intervened platform trajectories excluded</small></div></div><footer><strong>Instagram is evaluated for early burst; Facebook for persistent tail.</strong><span>{{ platformTempo.disclaimer }}</span></footer></section>
      }

      <div class="research-grid">
        <section class="section-band distribution-panel"><div class="section-heading"><div><span class="eyebrow">OUTCOME SPREAD</span><h2>Performance bands</h2></div></div>@if (entries(data.performanceBands).length) { <div class="distribution-list">@for (item of entries(data.performanceBands); track item[0]) { <div><span>{{ readable(item[0]) }}</span><div><i [style.width.%]="share(item[1], data.observedVideos)"></i></div><strong>{{ item[1] }}</strong></div> }</div> } @else { <p class="empty-distribution">Awaiting explicit observations.</p> }</section>
        <section class="section-band distribution-panel"><div class="section-heading"><div><span class="eyebrow">TIMING</span><h2>First-observed cohorts</h2></div></div>@if (entries(data.cohorts).length) { <div class="distribution-list">@for (item of entries(data.cohorts); track item[0]) { <div><span>{{ readable(item[0]) }}</span><div><i [style.width.%]="share(item[1], data.observedVideos)"></i></div><strong>{{ item[1] }}</strong></div> }</div> } @else { <p class="empty-distribution">No timing cohort is measurable yet.</p> }</section>
        <section class="section-band distribution-panel"><div class="section-heading"><div><span class="eyebrow">TRAJECTORY</span><h2>Growth patterns</h2></div></div>@if (entries(data.trajectories).length) { <div class="distribution-list">@for (item of entries(data.trajectories); track item[0]) { <div><span>{{ readable(item[0]) }}</span><div><i [style.width.%]="share(item[1], data.observedVideos)"></i></div><strong>{{ item[1] }}</strong></div> }</div> } @else { <p class="empty-distribution">Import timestamped checkpoints to classify growth.</p> }</section>
      </div>

      @if (comparison(); as comparisonData) {
        <section class="section-band comparison-panel"><div class="section-heading"><div><span class="eyebrow">DESCRIPTIVE COMPARISON</span><h2>Observed vs not observed</h2></div><span class="status-badge" [class.status-badge--green]="comparisonData.matched.comparisonEligible" [class.status-badge--amber]="!comparisonData.matched.comparisonEligible">{{ comparisonData.matched.comparisonEligible ? 'MATCHED SAMPLE READY' : 'LOW SAMPLE' }}</span></div><div class="comparison-groups"><div><span>Reach Further observed</span><strong>{{ number(comparisonData.reachFurtherObserved.medianCurrentViews) }}</strong><small>median views · n={{ comparisonData.reachFurtherObserved.sampleSize }}</small></div><div><span>Not observed</span><strong>{{ number(comparisonData.reachFurtherNotObserved.medianCurrentViews) }}</strong><small>median views · n={{ comparisonData.reachFurtherNotObserved.sampleSize }}</small></div><div><span>Matched pairs</span><strong>{{ comparisonData.matched.pairCount }}</strong><small>{{ comparisonData.matched.method }}</small></div></div><footer><strong>{{ comparisonData.causalDisclaimer }}</strong><span>{{ comparisonData.limitations }}</span></footer></section>
      }

      <section class="section-band cases-panel"><div class="section-heading"><div><span class="eyebrow">INDIVIDUAL CASES</span><h2>Reach Further performance profiles</h2></div><span class="data-freshness">{{ data.cases.length }} cases</span></div><div class="data-table-scroll"><table class="data-table research-table"><thead><tr><th>Video</th><th>First observed</th><th>Video age</th><th class="numeric">Views then</th><th>Trajectory</th><th>Engine</th><th>Character</th><th>Band</th><th></th></tr></thead><tbody>@for (item of data.cases; track item.videoId) { <tr><td><strong>{{ item.video }}</strong><small>{{ item.cohort }}</small></td><td>{{ date(item.firstObservedAt) }}</td><td>{{ age(item.videoAgeAtFirstObservationSeconds) }}</td><td class="numeric tabular">{{ number(item.atFirstObservation?.views) }}</td><td>{{ readable(item.trajectoryType) }}</td><td>{{ item.creativeEngine || 'Unknown' }}</td><td>{{ item.character || 'Unknown' }}</td><td><span class="status-badge">{{ item.performanceBand }}</span></td><td><a class="icon-button table-action" [routerLink]="['/videos', item.videoId]" title="Open evidence record" aria-label="Open evidence record">↗</a></td></tr> }</tbody></table></div></section>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReachFurtherResearchPage {
  private readonly service = inject(CreativeIntelligenceService);
  protected readonly research = signal<ReachFurtherResearch | null>(null);
  protected readonly comparison = signal<ReachFurtherComparison | null>(null);
  protected readonly tempo = signal<PlatformTempoResearch | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  constructor() {
    forkJoin({ research: this.service.getReachFurtherResearch(), comparison: this.service.getReachFurtherComparison(), tempo: this.service.getPlatformTempoResearch() }).subscribe({
      next: data => { this.research.set(data.research); this.comparison.set(data.comparison); this.tempo.set(data.tempo); this.loading.set(false); },
      error: response => { this.error.set(response.error?.message || 'Could not calculate Reach Further cohorts.'); this.loading.set(false); },
    });
  }
  protected entries(value: Record<string, number>): Array<[string, number]> { return Object.entries(value).sort((a, b) => b[1] - a[1]); }
  protected share(value: number, total: number): number { return total ? Math.max(3, value / total * 100) : 0; }
  protected number(value: number | null | undefined): string { return value === null || value === undefined ? '—' : new Intl.NumberFormat('en', { maximumFractionDigits: 0 }).format(value); }
  protected date(value: string | null): string { return value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : 'Unknown'; }
  protected age(seconds: number | null): string { return seconds === null ? 'Unknown' : `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`; }
  protected readable(value: string): string { return value.replaceAll('_', ' ').toLowerCase().replace(/(^|\s)\S/g, letter => letter.toUpperCase()); }
  protected ratio(value: number | null): string { return value === null ? '—' : `${value.toFixed(2)}×`; }
}
