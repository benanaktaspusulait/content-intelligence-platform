package com.pompom.creative.performance;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

/** Repository for follower metrics. */
@Repository
public interface FollowerMetricsRepository extends JpaRepository<FollowerMetrics, UUID> {

  /** Find all follower metrics for a publication job. */
  List<FollowerMetrics> findByPublicationJobIdOrderByMeasuredAtDesc(UUID publicationJobId);

  /** Find latest follower metrics for a publication job. */
  Optional<FollowerMetrics> findTopByPublicationJobIdOrderByMeasuredAtDesc(UUID publicationJobId);

  /** Find follower metrics within date range. */
  @Query(
      "SELECT f FROM FollowerMetrics f WHERE f.measuredAt BETWEEN :startDate AND :endDate "
          + "ORDER BY f.measuredAt DESC")
  List<FollowerMetrics> findByDateRange(
      @Param("startDate") Instant startDate, @Param("endDate") Instant endDate);

  /** Find videos with strong discovery (high discovery score). */
  @Query(
      "SELECT f FROM FollowerMetrics f WHERE f.discoveryScore > :minScore "
          + "ORDER BY f.discoveryScore DESC")
  List<FollowerMetrics> findStrongDiscoveryVideos(@Param("minScore") java.math.BigDecimal minScore);

  /** Find videos with strong follower conversion (>5%). */
  @Query(
      "SELECT f FROM FollowerMetrics f WHERE f.followerConversionRate > :minRate "
          + "ORDER BY f.followerConversionRate DESC")
  List<FollowerMetrics> findStrongConverters(@Param("minRate") java.math.BigDecimal minRate);

  /** Find videos with high US audience reach. */
  @Query(
      "SELECT f FROM FollowerMetrics f WHERE f.usAudiencePercentage > :minPercentage "
          + "ORDER BY f.usAudiencePercentage DESC")
  List<FollowerMetrics> findHighUSReachVideos(
      @Param("minPercentage") java.math.BigDecimal minPercentage);

  /** Calculate total followers gained in date range. */
  @Query(
      "SELECT COALESCE(SUM(f.followersGained), 0) FROM FollowerMetrics f "
          + "WHERE f.measuredAt BETWEEN :startDate AND :endDate")
  Integer calculateTotalFollowersGained(
      @Param("startDate") Instant startDate, @Param("endDate") Instant endDate);

  /** Calculate average conversion rate in date range. */
  @Query(
      "SELECT AVG(f.followerConversionRate) FROM FollowerMetrics f "
          + "WHERE f.measuredAt BETWEEN :startDate AND :endDate "
          + "AND f.followerConversionRate IS NOT NULL")
  java.math.BigDecimal calculateAverageConversionRate(
      @Param("startDate") Instant startDate, @Param("endDate") Instant endDate);
}
