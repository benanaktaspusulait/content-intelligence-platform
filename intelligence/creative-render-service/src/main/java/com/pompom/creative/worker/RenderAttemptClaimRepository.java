package com.pompom.creative.worker;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Atomically claims eligible {@link com.pompom.creative.domain.RenderAttempt} rows for exclusive
 * processing by one worker. "Eligible" means: non-terminal stage, due ({@code eligible_at <= now}
 * and, when set, {@code next_poll_at <= now}), and no active lease ({@code lease_expires_at} is
 * null or has already passed).
 */
public interface RenderAttemptClaimRepository {

  /**
   * Claims up to {@code batchSize} eligible attempts, assigning {@code leaseOwner} and {@code
   * leaseExpiresAt} to each, and returns their IDs. Safe to call concurrently from multiple worker
   * processes: no two concurrent callers ever receive the same attempt ID.
   */
  List<UUID> claimEligibleAttempts(
      String leaseOwner, Instant now, Instant leaseExpiresAt, int batchSize);
}
