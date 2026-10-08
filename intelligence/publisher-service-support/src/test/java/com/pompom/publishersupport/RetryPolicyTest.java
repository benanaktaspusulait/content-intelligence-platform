package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.publishercontract.PublishErrorClass;
import java.net.SocketTimeoutException;
import java.time.Duration;
import org.junit.jupiter.api.Test;

class RetryPolicyTest {

  private final ProviderErrorMapper mapper = new ProviderErrorMapper();
  private final RetryPolicy policy =
      new RetryPolicy(3, Duration.ofSeconds(2), Duration.ofSeconds(10));

  @Test
  void mapperAndPolicyAllowARecoverableFailureOnlyBeforeSubmission() {
    ProviderErrorMapper.Classification serverFailure = mapper.classify(503);
    ProviderErrorMapper.Classification timeoutFailure =
        mapper.classify(new SocketTimeoutException("provider connection timed out"));

    assertRetryBeforeSubmission(serverFailure);
    assertRetryBeforeSubmission(timeoutFailure);

    assertNoRetryAfterSubmission(serverFailure);
    assertNoRetryAfterSubmission(timeoutFailure);
  }

  @Test
  void unknownFailureAfterSubmissionRequiresReconciliationAndNeverAuthorizesAnotherPost() {
    ProviderErrorMapper.Classification unknownFailure =
        mapper.classify(new IllegalStateException("unexpected response"));

    RetryPolicy.Decision decision =
        policy.decide(unknownFailure, 1, RetryPolicy.SubmissionPhase.SUBMISSION_STARTED);

    assertThat(decision.shouldRetry()).isFalse();
    assertThat(decision.reconciliationRequired()).isTrue();
  }

  @Test
  void rateLimitRemainsExplicitlyRetryableBecauseItIsNotAnUncertainOutcome() {
    ProviderErrorMapper.Classification rateLimit = mapper.classify(429);

    assertThat(
            policy
                .decide(rateLimit, 1, RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED)
                .shouldRetry())
        .isTrue();
    assertThat(
            policy
                .decide(rateLimit, 1, RetryPolicy.SubmissionPhase.SUBMISSION_STARTED)
                .shouldRetry())
        .isTrue();
  }

  @Test
  void doesNotRetryTerminalErrorsOrPastTheAttemptLimit() {
    ProviderErrorMapper.Classification rejected =
        new ProviderErrorMapper.Classification(PublishErrorClass.PROVIDER_REJECTED, false, false);
    ProviderErrorMapper.Classification retryable =
        new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, false);

    assertThat(
            policy
                .decide(rejected, 1, RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED)
                .shouldRetry())
        .isFalse();
    assertThat(
            policy
                .decide(retryable, 3, RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED)
                .shouldRetry())
        .isFalse();
  }

  private void assertRetryBeforeSubmission(ProviderErrorMapper.Classification classification) {
    RetryPolicy.Decision decision =
        policy.decide(classification, 2, RetryPolicy.SubmissionPhase.SUBMISSION_NOT_STARTED);

    assertThat(decision.shouldRetry()).isTrue();
    assertThat(decision.reconciliationRequired()).isFalse();
    assertThat(decision.backoff()).isEqualTo(Duration.ofSeconds(4));
  }

  private void assertNoRetryAfterSubmission(ProviderErrorMapper.Classification classification) {
    RetryPolicy.Decision decision =
        policy.decide(classification, 1, RetryPolicy.SubmissionPhase.SUBMISSION_STARTED);

    assertThat(decision.shouldRetry()).isFalse();
    assertThat(decision.reconciliationRequired()).isTrue();
  }
}
