package com.pompom.creative.worker;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public interface ScheduledPublicationClaimRepository {
  List<UUID> claimDueSchedules(
      String leaseOwner, Instant now, Instant leaseExpiresAt, int batchSize);
}
