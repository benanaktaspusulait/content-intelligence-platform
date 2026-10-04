package com.pompom.creative.repository;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface PublicationJobRepository extends JpaRepository<PublicationJob, UUID> {

  Optional<PublicationJob> findByIdempotencyKey(String idempotencyKey);

  List<PublicationJob> findByStatus(PublicationStatus status);

  List<PublicationJob> findByStatusIn(List<PublicationStatus> statuses);

  List<PublicationJob> findByPlatformAndStatus(PlatformType platform, PublicationStatus status);

  List<PublicationJob> findByStatusAndQueuedAtBefore(PublicationStatus status, Instant before);

  List<PublicationJob> findAllByOrderByQueuedAtDesc();

  long countByStatus(PublicationStatus status);

  // Search and filter methods
  List<PublicationJob> findByPlatform(PlatformType platform);

  List<PublicationJob> findByQueuedAtBetween(Instant startDate, Instant endDate);

  List<PublicationJob> findByPlatformAndQueuedAtBetween(
      PlatformType platform, Instant startDate, Instant endDate);

  @Query(
      "SELECT j FROM PublicationJob j WHERE "
          + "(:platform IS NULL OR j.platform = :platform) AND "
          + "(:status IS NULL OR j.status = :status) AND "
          + "(:startDate IS NULL OR j.queuedAt >= :startDate) AND "
          + "(:endDate IS NULL OR j.queuedAt <= :endDate) AND "
          + "(:keyword IS NULL OR LOWER(j.title) LIKE LOWER(CONCAT('%', :keyword, '%')) OR LOWER(j.caption) LIKE LOWER(CONCAT('%', :keyword, '%')))")
  Page<PublicationJob> searchJobs(
      @Param("platform") PlatformType platform,
      @Param("status") PublicationStatus status,
      @Param("startDate") Instant startDate,
      @Param("endDate") Instant endDate,
      @Param("keyword") String keyword,
      Pageable pageable);

  @Query(
      "SELECT j FROM PublicationJob j WHERE "
          + "(:platform IS NULL OR j.platform = :platform) AND "
          + "(:status IS NULL OR j.status = :status) AND "
          + "(:startDate IS NULL OR j.queuedAt >= :startDate) AND "
          + "(:endDate IS NULL OR j.queuedAt <= :endDate)")
  List<PublicationJob> findJobsForExport(
      @Param("platform") PlatformType platform,
      @Param("status") PublicationStatus status,
      @Param("startDate") Instant startDate,
      @Param("endDate") Instant endDate);
}
