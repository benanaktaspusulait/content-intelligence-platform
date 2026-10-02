package com.pompom.creative.performance;

import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/** Repository for Reach Further events. */
@Repository
public interface ReachFurtherEventRepository extends JpaRepository<ReachFurtherEvent, UUID> {

  /** Find all Reach Further events for a publication job. */
  List<ReachFurtherEvent> findByPublicationJobIdOrderByDetectedAtDesc(UUID publicationJobId);

  /** Find Reach Further event by publication job and platform. */
  Optional<ReachFurtherEvent> findByPublicationJobIdAndPlatform(
      UUID publicationJobId, PlatformType platform);

  /** Find all Reach Further events for a platform within date range. */
  @Query(
      "SELECT r FROM ReachFurtherEvent r WHERE r.platform = :platform "
          + "AND r.detectedAt BETWEEN :startDate AND :endDate "
          + "ORDER BY r.detectedAt DESC")
  List<ReachFurtherEvent> findByPlatformAndDateRange(
      @Param("platform") PlatformType platform,
      @Param("startDate") Instant startDate,
      @Param("endDate") Instant endDate);

  /** Find strong Reach Further events (high non-follower %, good growth). */
  @Query(
      "SELECT r FROM ReachFurtherEvent r WHERE r.nonFollowerPercentage > :minNonFollower "
          + "AND r.views24hAfter > r.viewsBefore * :minGrowthMultiplier "
          + "ORDER BY r.detectedAt DESC")
  List<ReachFurtherEvent> findStrongReachFurtherEvents(
      @Param("minNonFollower") java.math.BigDecimal minNonFollower,
      @Param("minGrowthMultiplier") Long minGrowthMultiplier);

  /** Count Reach Further events by platform. */
  long countByPlatform(PlatformType platform);
}
