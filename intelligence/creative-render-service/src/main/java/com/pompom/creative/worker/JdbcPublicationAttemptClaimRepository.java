package com.pompom.creative.worker;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class JdbcPublicationAttemptClaimRepository implements PublicationAttemptClaimRepository {

  private static final String CLAIM_SQL =
      """
      WITH eligible AS (
          SELECT id
          FROM publication_attempts
          WHERE stage = 'QUEUED'
            AND eligible_at <= ?
            AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
          ORDER BY eligible_at
          FOR UPDATE SKIP LOCKED
          LIMIT ?
      )
      UPDATE publication_attempts
      SET lease_owner = ?, lease_expires_at = ?, updated_at = ?
      FROM eligible
      WHERE publication_attempts.id = eligible.id
      RETURNING publication_attempts.id
      """;

  private final JdbcTemplate jdbcTemplate;

  public JdbcPublicationAttemptClaimRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  @Override
  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public List<UUID> claimQueuedAttempts(
      String leaseOwner, Instant now, Instant leaseExpiresAt, int batchSize) {
    Timestamp nowTimestamp = Timestamp.from(now);
    return jdbcTemplate.query(
        CLAIM_SQL,
        (resultSet, rowNumber) -> UUID.fromString(resultSet.getString("id")),
        nowTimestamp,
        nowTimestamp,
        batchSize,
        leaseOwner,
        Timestamp.from(leaseExpiresAt),
        nowTimestamp);
  }
}
