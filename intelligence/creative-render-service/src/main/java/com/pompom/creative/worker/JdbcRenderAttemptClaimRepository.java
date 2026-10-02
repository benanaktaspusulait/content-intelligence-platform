package com.pompom.creative.worker;

import com.pompom.creative.domain.RenderExecutionStage;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Atomically claims eligible render attempts using a single statement: a CTE selects eligible
 * attempt IDs with {@code FOR UPDATE SKIP LOCKED} (so concurrent callers never block on, or
 * double-claim, the same row - a locked-but-not-yet-committed row is simply skipped rather than
 * waited on), then an {@code UPDATE ... FROM} sets the lease fields on exactly those rows and
 * returns their IDs, all within one transaction.
 */
@Repository
public class JdbcRenderAttemptClaimRepository implements RenderAttemptClaimRepository {

  // Built from RenderExecutionStage.unclaimableStages() - the single source of truth also used
  // by RenderAttempt.isTerminal() - rather than a hand-written literal list, so this query can
  // never drift out of sync with which stages are actually unclaimable.
  private static final String UNCLAIMABLE_STAGES_SQL =
      RenderExecutionStage.unclaimableStages().stream()
          .map(stage -> "'" + stage.name() + "'")
          .collect(Collectors.joining(", "));

  private static final String CLAIM_SQL =
      """
      WITH eligible AS (
          SELECT id
          FROM render_attempts
          WHERE stage NOT IN (%s)
            AND eligible_at <= ?
            AND (next_poll_at IS NULL OR next_poll_at <= ?)
            AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
          ORDER BY eligible_at
          FOR UPDATE SKIP LOCKED
          LIMIT ?
      )
      UPDATE render_attempts
      SET lease_owner = ?,
          lease_expires_at = ?,
          lease_heartbeat_at = ?,
          updated_at = ?
      FROM eligible
      WHERE render_attempts.id = eligible.id
      RETURNING render_attempts.id
      """
          .formatted(UNCLAIMABLE_STAGES_SQL);

  private final JdbcTemplate jdbcTemplate;

  public JdbcRenderAttemptClaimRepository(JdbcTemplate jdbcTemplate) {
    this.jdbcTemplate = jdbcTemplate;
  }

  @Override
  @Transactional(propagation = Propagation.REQUIRES_NEW)
  public List<UUID> claimEligibleAttempts(
      String leaseOwner, Instant now, Instant leaseExpiresAt, int batchSize) {
    Timestamp nowTs = Timestamp.from(now);
    Timestamp leaseExpiresTs = Timestamp.from(leaseExpiresAt);

    return jdbcTemplate.query(
        CLAIM_SQL,
        (rs, rowNum) -> UUID.fromString(rs.getString("id")),
        nowTs,
        nowTs,
        nowTs,
        batchSize,
        leaseOwner,
        leaseExpiresTs,
        nowTs,
        nowTs);
  }
}
