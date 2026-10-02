package com.pompomhills.intelligence.platformstate;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ReachFurtherResearchService {
  private final JdbcClient jdbc;
  private final PlatformStateService states;

  public ReachFurtherResearchService(JdbcClient jdbc, PlatformStateService states) {
    this.jdbc = jdbc;
    this.states = states;
  }

  @Transactional(readOnly = true)
  public ResearchView research(String platform) {
    List<PlatformStateService.ReachFurtherSummary> cases = observedCases(platform);
    return new ResearchView(
        cases.size(),
        median(cases.stream().map(item -> views(item.atFirstObservation())).toList()),
        median(windowViews(cases, "24h")),
        median(windowViews(cases, "7d")),
        distribution(
            cases.stream().map(PlatformStateService.ReachFurtherSummary::performanceBand).toList()),
        distribution(
            cases.stream().map(PlatformStateService.ReachFurtherSummary::trajectoryType).toList()),
        distribution(cases.stream().map(item -> value(item.creativeEngine())).toList()),
        distribution(cases.stream().map(item -> value(item.character())).toList()),
        distribution(
            cases.stream().map(PlatformStateService.ReachFurtherSummary::platform).toList()),
        distribution(cases.stream().map(PlatformStateService.ReachFurtherSummary::cohort).toList()),
        cases,
        "Reach Further is an observed Meta UI state. These distributions are descriptive and do not establish causality.");
  }

  @Transactional(readOnly = true)
  public ComparisonView comparison(String platform) {
    String normalized =
        platform == null || platform.isBlank() ? "facebook" : platform.toLowerCase();
    List<PlatformStateService.ReachFurtherSummary> observed = observedCases(normalized);
    List<CurrentOutcome> unobserved =
        jdbc.sql(
                """
                SELECT DISTINCT ON (v.id) v.id,p.views
                FROM videos v
                JOIN performance_observations p ON p.video_id=v.id AND p.platform=:platform
                WHERE NOT EXISTS (
                  SELECT 1 FROM platform_content_states s
                  JOIN platform_content_state_observations o ON o.state_id=s.id
                  WHERE s.video_id=v.id AND s.platform=:platform
                    AND s.state_type='META_REACH_FURTHER' AND o.state_value='ACTIVE'
                    AND NOT EXISTS (SELECT 1 FROM platform_content_state_observations c
                                    WHERE c.correction_of_id=o.id))
                  AND NOT EXISTS (SELECT 1 FROM intervention_events i
                                  WHERE i.video_id=v.id AND i.platform=:platform)
                ORDER BY v.id,p.measurement_timestamp DESC NULLS LAST
                """)
            .param("platform", normalized)
            .query(
                (rs, ignored) ->
                    new CurrentOutcome(rs.getObject("id", UUID.class), nullableLong(rs, "views")))
            .list();
    List<Long> observedViews = observed.stream().map(item -> views(item.current())).toList();
    List<Long> unobservedViews = unobserved.stream().map(CurrentOutcome::views).toList();
    MatchedView matched = matched(normalized);
    return new ComparisonView(
        new GroupView(observed.size(), median(observedViews), bands(observedViews)),
        new GroupView(unobserved.size(), median(unobservedViews), bands(unobservedViews)),
        matched,
        "Groups differ in age, series, engine, and publication period. Medians and distributions are shown; raw means are intentionally omitted.",
        "Observational comparison only. Reach Further appearance is not treated as the cause of later performance.");
  }

  private List<PlatformStateService.ReachFurtherSummary> observedCases(String platform) {
    String normalized =
        platform == null || platform.isBlank() ? "facebook" : platform.toLowerCase();
    List<UUID> ids =
        jdbc.sql(
                """
                SELECT DISTINCT s.video_id FROM platform_content_states s
                JOIN platform_content_state_observations o ON o.state_id=s.id
                WHERE s.platform=:platform AND s.state_type='META_REACH_FURTHER'
                  AND o.state_value='ACTIVE'
                  AND NOT EXISTS (SELECT 1 FROM platform_content_state_observations c
                                  WHERE c.correction_of_id=o.id)
                  AND NOT EXISTS (SELECT 1 FROM intervention_events i
                                  WHERE i.video_id=s.video_id AND i.platform=:platform)
                ORDER BY s.video_id
                """)
            .param("platform", normalized)
            .query(UUID.class)
            .list();
    return ids.stream().map(id -> states.reachFurtherSummary(id, normalized)).toList();
  }

  private MatchedView matched(String platform) {
    List<MatchedPair> pairs =
        jdbc.sql(
                """
                WITH rf AS (
                  SELECT DISTINCT s.video_id
                  FROM platform_content_states s JOIN platform_content_state_observations o ON o.state_id=s.id
                  WHERE s.platform=:platform AND s.state_type='META_REACH_FURTHER' AND o.state_value='ACTIVE'
                    AND NOT EXISTS (SELECT 1 FROM intervention_events i
                                    WHERE i.video_id=s.video_id AND i.platform=:platform)
                ), latest AS (
                  SELECT DISTINCT ON (video_id) video_id,views FROM performance_observations
                  WHERE platform=:platform ORDER BY video_id,measurement_timestamp DESC NULLS LAST
                )
                SELECT rf.video_id AS observed_id,m.control_id,lo.views AS observed_views,lc.views AS control_views
                FROM rf
                JOIN videos vo ON vo.id=rf.video_id
                LEFT JOIN creative_fingerprints fo ON fo.video_id=vo.id
                JOIN LATERAL (
                  SELECT vc.id AS control_id
                  FROM videos vc
                  LEFT JOIN creative_fingerprints fc ON fc.video_id=vc.id
                  WHERE vc.id NOT IN (SELECT video_id FROM rf)
                    AND abs(vc.duration_ms-vo.duration_ms) <= greatest(1000,vo.duration_ms*0.20)
                    AND (fo.creative_quality_score IS NULL OR fc.creative_quality_score IS NULL
                         OR abs(fc.creative_quality_score-fo.creative_quality_score) <= 10)
                    AND EXISTS (SELECT 1 FROM performance_observations p
                                WHERE p.video_id=vc.id AND p.platform=:platform)
                    AND NOT EXISTS (SELECT 1 FROM intervention_events i
                                    WHERE i.video_id=vc.id AND i.platform=:platform)
                  ORDER BY abs(vc.duration_ms-vo.duration_ms) LIMIT 1
                ) m ON true
                LEFT JOIN latest lo ON lo.video_id=rf.video_id
                LEFT JOIN latest lc ON lc.video_id=m.control_id
                """)
            .param("platform", platform)
            .query(
                (rs, ignored) ->
                    new MatchedPair(
                        rs.getObject("observed_id", UUID.class),
                        rs.getObject("control_id", UUID.class),
                        nullableLong(rs, "observed_views"),
                        nullableLong(rs, "control_views")))
            .list();
    return new MatchedView(
        pairs.size(),
        median(pairs.stream().map(MatchedPair::observedViews).toList()),
        median(pairs.stream().map(MatchedPair::controlViews).toList()),
        pairs.size() >= 5,
        pairs.size() >= 5
            ? "Duration and creative-score proximity"
            : "Insufficient matched pairs; no comparative conclusion");
  }

  private List<Long> windowViews(List<PlatformStateService.ReachFurtherSummary> cases, String key) {
    return cases.stream()
        .map(item -> item.performanceWindows().get(key))
        .map(item -> item == null ? null : views(item.observation()))
        .toList();
  }

  private Map<String, Long> bands(List<Long> views) {
    var labels = new ArrayList<String>();
    for (Long value : views) {
      if (value == null) labels.add("UNKNOWN");
      else if (value >= 50_000) labels.add("50K_PLUS");
      else if (value >= 20_000) labels.add("20K_PLUS");
      else if (value >= 5_000) labels.add("5K_PLUS");
      else if (value >= 2_000) labels.add("2K_PLUS");
      else if (value >= 1_000) labels.add("1K_PLUS");
      else labels.add("BELOW_1K");
    }
    return distribution(labels);
  }

  private Map<String, Long> distribution(List<String> values) {
    var result = new LinkedHashMap<String, Long>();
    values.forEach(value -> result.merge(value(value), 1L, Long::sum));
    return result;
  }

  private Double median(List<Long> values) {
    List<Long> present =
        values.stream()
            .filter(java.util.Objects::nonNull)
            .sorted(Comparator.naturalOrder())
            .toList();
    if (present.isEmpty()) return null;
    int middle = present.size() / 2;
    return present.size() % 2 == 1
        ? present.get(middle).doubleValue()
        : (present.get(middle - 1) + present.get(middle)) / 2.0;
  }

  private Long views(PlatformStateService.MetricPoint point) {
    return point == null ? null : point.views();
  }

  private String value(String value) {
    return value == null || value.isBlank() ? "UNKNOWN" : value;
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  private record CurrentOutcome(UUID videoId, Long views) {}

  public record ResearchView(
      int observedVideos,
      Double medianViewsAtFirstObservation,
      Double median24hViews,
      Double median7dViews,
      Map<String, Long> performanceBands,
      Map<String, Long> trajectories,
      Map<String, Long> creativeEngines,
      Map<String, Long> characters,
      Map<String, Long> platforms,
      Map<String, Long> cohorts,
      List<PlatformStateService.ReachFurtherSummary> cases,
      String disclaimer) {}

  public record GroupView(
      int sampleSize, Double medianCurrentViews, Map<String, Long> distribution) {}

  public record MatchedPair(
      UUID observedVideoId, UUID controlVideoId, Long observedViews, Long controlViews) {}

  public record MatchedView(
      int pairCount,
      Double observedMedianViews,
      Double controlMedianViews,
      boolean comparisonEligible,
      String method) {}

  public record ComparisonView(
      GroupView reachFurtherObserved,
      GroupView reachFurtherNotObserved,
      MatchedView matched,
      String limitations,
      String causalDisclaimer) {}
}
