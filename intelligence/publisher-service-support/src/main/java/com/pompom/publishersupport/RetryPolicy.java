package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishErrorClass;
import java.time.Duration;
import java.util.Objects;

/** Provides bounded, provider-neutral retry decisions without performing network calls. */
public final class RetryPolicy {

  public static final int DEFAULT_MAX_ATTEMPTS = 3;
  public static final Duration DEFAULT_INITIAL_BACKOFF = Duration.ofSeconds(1);
  public static final Duration DEFAULT_MAX_BACKOFF = Duration.ofSeconds(30);

  public record Decision(boolean shouldRetry, Duration backoff, boolean reconciliationRequired) {}

  private final int maxAttempts;
  private final Duration initialBackoff;
  private final Duration maxBackoff;

  public RetryPolicy() {
    this(DEFAULT_MAX_ATTEMPTS, DEFAULT_INITIAL_BACKOFF, DEFAULT_MAX_BACKOFF);
  }

  public RetryPolicy(int maxAttempts, Duration initialBackoff, Duration maxBackoff) {
    if (maxAttempts < 1) {
      throw new IllegalArgumentException("maxAttempts must be positive");
    }
    if (initialBackoff.isNegative()
        || maxBackoff.isNegative()
        || maxBackoff.compareTo(initialBackoff) < 0) {
      throw new IllegalArgumentException("backoff bounds are invalid");
    }
    this.maxAttempts = maxAttempts;
    this.initialBackoff = initialBackoff;
    this.maxBackoff = maxBackoff;
  }

  public Decision decide(ProviderErrorMapper.Classification classification, int attemptNumber) {
    return decide(classification, attemptNumber, false);
  }

  /**
   * Decides whether a failure can be retried. Once a submission outcome is uncertain, this method
   * always favors reconciliation over a second provider POST.
   */
  public Decision decide(
      ProviderErrorMapper.Classification classification,
      int attemptNumber,
      boolean submissionStarted) {
    Objects.requireNonNull(classification, "classification");
    if (attemptNumber < 1) {
      throw new IllegalArgumentException("attemptNumber must be positive");
    }

    boolean uncertainAfterSubmission =
        submissionStarted
            && (classification.errorClass() == PublishErrorClass.TRANSIENT
                || classification.errorClass() == PublishErrorClass.UNKNOWN
                || classification.reconciliationRequired());
    if (classification.reconciliationRequired() || uncertainAfterSubmission) {
      return new Decision(false, Duration.ZERO, true);
    }
    if (!classification.retryable() || attemptNumber >= maxAttempts) {
      return new Decision(false, Duration.ZERO, false);
    }
    return new Decision(true, backoffForAttempt(attemptNumber), false);
  }

  public Duration backoffForAttempt(int attemptNumber) {
    if (attemptNumber < 1) {
      throw new IllegalArgumentException("attemptNumber must be positive");
    }
    long multiplier = 1L << Math.min(attemptNumber - 1, 30);
    Duration candidate = initialBackoff.multipliedBy(multiplier);
    return candidate.compareTo(maxBackoff) > 0 ? maxBackoff : candidate;
  }
}
