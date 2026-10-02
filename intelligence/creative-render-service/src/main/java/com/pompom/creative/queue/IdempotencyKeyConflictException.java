package com.pompom.creative.queue;

/**
 * Thrown when a request reuses an {@code Idempotency-Key} with a different canonical payload than
 * the request that originally created the job for that key. Maps to HTTP 409.
 */
public class IdempotencyKeyConflictException extends RuntimeException {
  public IdempotencyKeyConflictException(String idempotencyKey) {
    super(
        "Idempotency-Key %s was already used with a different request payload"
            .formatted(idempotencyKey));
  }
}
