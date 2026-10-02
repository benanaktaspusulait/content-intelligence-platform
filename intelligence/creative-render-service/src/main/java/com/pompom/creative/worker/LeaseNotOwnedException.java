package com.pompom.creative.worker;

import java.util.UUID;

/**
 * Thrown when a worker attempts to process a {@code RenderAttempt} it does not currently hold the
 * lease for. This can happen if the lease expired and was reclaimed by another worker, or if the
 * caller passes a lease owner that never actually claimed the attempt. Processing must stop
 * immediately - continuing would risk two workers executing the same stage concurrently.
 */
public class LeaseNotOwnedException extends RuntimeException {

  public LeaseNotOwnedException(UUID attemptId, String expectedOwner, String actualOwner) {
    super(
        "Render attempt "
            + attemptId
            + " is not leased by "
            + expectedOwner
            + " (current lease owner: "
            + actualOwner
            + ")");
  }
}
