package com.pompomhills.intelligence.performance;

import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PlatformGrowthResearchService {
  private final JdbcClient jdbc;
  private final PlatformGrowthProfileService profiles;

  public PlatformGrowthResearchService(JdbcClient jdbc, PlatformGrowthProfileService profiles) {
    this.jdbc = jdbc;
    this.profiles = profiles;
  }

  @Transactional(readOnly = true)
  public TempoResearch research() {
    return new TempoResearch(
        platform("instagram"),
        platform("facebook"),
        "Only clean-organic videos are included. Ratios are descriptive, use observed checkpoints, and do not establish a platform-wide causal law.");
  }

  private PlatformTempo platform(String platform) {
    int total =
        jdbc.sql(
                "SELECT count(DISTINCT video_id) FROM performance_observations WHERE platform=:platform")
            .param("platform", platform)
            .query(Integer.class)
            .single();
    List<UUID> ids =
        jdbc.sql(
                """
                SELECT DISTINCT p.video_id FROM performance_observations p
                WHERE p.platform=:platform
                  AND NOT EXISTS (SELECT 1 FROM intervention_events i
                                  WHERE i.video_id=p.video_id AND i.platform=:platform)
                ORDER BY p.video_id
                """)
            .param("platform", platform)
            .query(UUID.class)
            .list();
    List<PlatformGrowthProfileService.GrowthProfile> data =
        ids.stream().map(id -> profiles.profile(id, platform, Instant.now())).toList();
    List<Double> ratios =
        data.stream()
            .map(
                item ->
                    "instagram".equals(platform)
                        ? item.instagramBurstRatio()
                        : item.facebookTailRatio())
            .filter(value -> value != null)
            .toList();
    return new PlatformTempo(
        platform, total, ids.size(), total - ids.size(), ratios.size(), median(ratios), data);
  }

  private Double median(List<Double> values) {
    List<Double> clean = values.stream().sorted(Comparator.naturalOrder()).toList();
    if (clean.isEmpty()) return null;
    int middle = clean.size() / 2;
    return clean.size() % 2 == 0
        ? (clean.get(middle - 1) + clean.get(middle)) / 2.0
        : clean.get(middle);
  }

  public record PlatformTempo(
      String platform,
      int totalVideoCount,
      int cleanVideoCount,
      int intervenedExcludedCount,
      int ratioEligibleCount,
      Double medianRatio,
      List<PlatformGrowthProfileService.GrowthProfile> videos) {}

  public record TempoResearch(PlatformTempo instagram, PlatformTempo facebook, String disclaimer) {}
}
