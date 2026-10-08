package com.pompom.publishersupport;

import java.time.Duration;
import java.util.Objects;

/** Provides bounded, provider-neutral retry decisions without performing network calls. */
public final class RetryPolicy {

  public static final int DEFAULT_MAX_ATTEMPTS = 3;
  public static final Duration DEFAULT_INITIAL_BACKOFF = Duration.ofSeconds(1);
  public static final Duration DEFAULT_MAX_BACKOFF = Duration.ofSeconds(30);

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
    if (initialBackoff.isNegative() || initialBackoff.isZero()) {
      throw new IllegalArgumentException("initialBackoff must be positive");
    }
    if (maxBackoff.compareTo(initialBackoff) < 0) {
      throw new IllegalArgumentException("maxBackoff must not be less than initialBackoff");
    }
    this.maxAttempts = maxAttempts;
    this.initialBackoff = initialBackoff;
    this.maxBackoff = maxBackoff;
  }

  /** Submission phase must be explicit so an uncertain outcome cannot authorize another POST. */
  public Decision decide(
      ProviderErrorMapper.Classification classification,
      int attemptNumber,
      SubmissionPhase submissionPhase) {
    Objects.requireNonNull(classification, "classification");
    Objects.requireNonNull(submissionPhase, "submissionPhase");
    if (attemptNumber < 1) {
      throw new IllegalArgumentException("attemptNumber must be positive");
    }

    if (submissionPhase == SubmissionPhase.SUBMISSION_STARTED
        && classification.uncertainAfterSubmission()) {
      return new Decision(false, Duration.ZERO, true);
    }
    if (!classification.safeToRetryBeforeSubmission() || attemptNumber >= maxAttempts) {
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

  public enum SubmissionPhase {
    SUBMISSION_NOT_STARTED,
    SUBMISSION_STARTED
  }

  public record Decision(boolean shouldRetry, Duration backoff, boolean reconciliationRequired) {
    public Decision {
      Objects.requireNonNull(backoff, "backoff");
    }
  }
}
