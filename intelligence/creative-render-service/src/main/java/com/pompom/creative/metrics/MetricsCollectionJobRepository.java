package com.pompom.creative.metrics;

import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

@Repository
public interface MetricsCollectionJobRepository extends JpaRepository<MetricsCollectionJob, UUID> {

  List<MetricsCollectionJob> findByStatus(MetricsCollectionJob.JobStatus status);

  List<MetricsCollectionJob> findByPublicationJobId(UUID publicationJobId);

  @Query(
      "SELECT j FROM MetricsCollectionJob j WHERE j.status = 'PENDING' "
          + "AND j.scheduledAt <= :now ORDER BY j.scheduledAt ASC")
  List<MetricsCollectionJob> findDueJobs(@Param("now") Instant now);

  @Query(
      "SELECT j FROM MetricsCollectionJob j WHERE j.status = 'FAILED' "
          + "AND j.retryCount < j.maxRetries")
  List<MetricsCollectionJob> findRetryableJobs();

  @Query(
      "SELECT COUNT(j) FROM MetricsCollectionJob j WHERE j.publicationJob.id = :jobId "
          + "AND j.status = 'COMPLETED'")
  Long countCompletedByPublicationJob(@Param("jobId") UUID jobId);
}
