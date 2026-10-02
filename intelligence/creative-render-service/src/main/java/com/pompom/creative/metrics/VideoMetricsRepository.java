package com.pompom.creative.metrics;

import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface VideoMetricsRepository extends JpaRepository<VideoMetrics, UUID> {

  List<VideoMetrics> findByPublicationJobId(UUID publicationJobId);

  List<VideoMetrics> findByPlatformVideoId(String platformVideoId);

  Optional<VideoMetrics> findByPublicationJobIdAndTimeSincePublishMinutes(
      UUID publicationJobId, Integer timeSincePublishMinutes);

  @Query("SELECT m FROM VideoMetrics m WHERE m.isFinal = true")
  List<VideoMetrics> findFinalMetrics();

  @Query(
      "SELECT m FROM VideoMetrics m WHERE m.platform = :platform "
          + "AND m.collectedAt >= :startDate ORDER BY m.views DESC")
  List<VideoMetrics> findTopPerformingByPlatform(
      @Param("platform") PlatformType platform, @Param("startDate") Instant startDate);

  @Query(
      "SELECT m FROM VideoMetrics m WHERE m.publicationJob.id = :jobId "
          + "ORDER BY m.collectedAt ASC")
  List<VideoMetrics> findMetricsTimeline(@Param("jobId") UUID jobId);

  @Query(
      "SELECT AVG(m.views) FROM VideoMetrics m WHERE m.isFinal = true "
          + "AND m.platform = :platform")
  Double getAverageViewsByPlatform(@Param("platform") PlatformType platform);
}
