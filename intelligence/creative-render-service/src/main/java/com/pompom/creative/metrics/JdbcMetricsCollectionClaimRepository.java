package com.pompom.creative.metrics;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/** Claims due metric jobs atomically so multiple workers cannot collect the same point. */
@Repository
public class JdbcMetricsCollectionClaimRepository {

  private static final String CLAIM_SQL =
      """
      WITH eligible AS (
          SELECT id
          FROM metrics_collection_jobs
          WHERE ((status = 'PENDING' AND scheduled_at <= ?)
             OR (status = 'FAILED' AND retry_count < max_retries AND scheduled_at <= ?))
            AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
          ORDER BY scheduled_at
          FOR UPDATE SKIP LOCKED
          LIMIT ?
      )
      UPDATE metrics_collection_jobs
      SET status = 'IN_PROGRESS', lease_owner = ?, lease_expires_at = ?, executed_at = ?, error_message = NULL
      FROM eligible
      WHERE metrics_collection_jobs.id = eligible.id
      RETURNING metrics_collection_jobs.id
      """;

  private final JdbcTemplate jdbcTemplate;

  public JdbcMetricsCollectionClaimRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public List<UUID> claimDueJobs(
      String leaseOwner, Instant now, Instant leaseExpiresAt, int batchSize) {
    Timestamp timestamp = Timestamp.from(now);
    return jdbcTemplate.query(
        CLAIM_SQL,
        (resultSet, rowNumber) -> UUID.fromString(resultSet.getString("id")),
        timestamp,
        timestamp,
        timestamp,
        batchSize,
        leaseOwner,
        Timestamp.from(leaseExpiresAt),
        timestamp);
  }
}
