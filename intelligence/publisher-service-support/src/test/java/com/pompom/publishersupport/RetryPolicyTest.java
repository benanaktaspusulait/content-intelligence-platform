package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.publishercontract.PublishErrorClass;
import java.time.Duration;
import org.junit.jupiter.api.Test;

class RetryPolicyTest {

  private final RetryPolicy policy =
      new RetryPolicy(3, Duration.ofSeconds(2), Duration.ofSeconds(10));

  @Test
  void retriesARecoverablePreSubmissionFailureWithBoundedExponentialBackoff() {
    ProviderErrorMapper.Classification transientFailure =
        new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, false);

    RetryPolicy.Decision decision = policy.decide(transientFailure, 2);

    assertThat(decision.shouldRetry()).isTrue();
    assertThat(decision.reconciliationRequired()).isFalse();
    assertThat(decision.backoff()).isEqualTo(Duration.ofSeconds(4));
  }

  @Test
  void neverRetriesAnUncertainSubmissionAndSignalsReconciliation() {
    ProviderErrorMapper.Classification uncertainFailure =
        new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, true);

    RetryPolicy.Decision decision = policy.decide(uncertainFailure, 1);

    assertThat(decision.shouldRetry()).isFalse();
    assertThat(decision.reconciliationRequired()).isTrue();
  }

  @Test
  void doesNotRetryTerminalErrorsOrPastTheAttemptLimit() {
    ProviderErrorMapper.Classification rejected =
        new ProviderErrorMapper.Classification(PublishErrorClass.PROVIDER_REJECTED, false, false);
    ProviderErrorMapper.Classification retryable =
        new ProviderErrorMapper.Classification(PublishErrorClass.TRANSIENT, true, false);

    assertThat(policy.decide(rejected, 1).shouldRetry()).isFalse();
    assertThat(policy.decide(retryable, 3).shouldRetry()).isFalse();
  }
}
