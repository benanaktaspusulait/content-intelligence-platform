package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.publishercontract.PublishErrorClass;
import java.net.SocketTimeoutException;
import org.junit.jupiter.api.Test;

class ProviderErrorMapperTest {

  private final ProviderErrorMapper mapper = new ProviderErrorMapper();

  @Test
  void mapsGenericHttpStatusesToContractErrorClasses() {
    assertThat(mapper.classify(400).errorClass()).isEqualTo(PublishErrorClass.VALIDATION);
    assertThat(mapper.classify(401).errorClass()).isEqualTo(PublishErrorClass.AUTHENTICATION);
    assertThat(mapper.classify(403).errorClass()).isEqualTo(PublishErrorClass.AUTHORIZATION);
    assertThat(mapper.classify(404).errorClass()).isEqualTo(PublishErrorClass.UNSUPPORTED);
    assertThat(mapper.classify(409).errorClass()).isEqualTo(PublishErrorClass.DUPLICATE);
    assertThat(mapper.classify(422).errorClass()).isEqualTo(PublishErrorClass.PROVIDER_REJECTED);
    assertThat(mapper.classify(429).errorClass()).isEqualTo(PublishErrorClass.RATE_LIMITED);
  }

  @Test
  void treatsServerResponsesAsUncertainAndRequiresReconciliation() {
    ProviderErrorMapper.Classification classification = mapper.classify(503);

    assertThat(classification.errorClass()).isEqualTo(PublishErrorClass.TRANSIENT);
    assertThat(classification.retryable()).isTrue();
    assertThat(classification.reconciliationRequired()).isTrue();
  }

  @Test
  void treatsTransportTimeoutsAsTransientWithoutGuessingProviderOutcome() {
    ProviderErrorMapper.Classification classification =
        mapper.classify(new SocketTimeoutException("provider connection timed out"));

    assertThat(classification.errorClass()).isEqualTo(PublishErrorClass.TRANSIENT);
    assertThat(classification.retryable()).isTrue();
    assertThat(classification.reconciliationRequired()).isTrue();
  }

  @Test
  void mapsGenericUnexpectedFailuresToUnknownReconciliation() {
    ProviderErrorMapper.Classification classification =
        mapper.classify(new IllegalStateException("unexpected response"));

    assertThat(classification.errorClass()).isEqualTo(PublishErrorClass.UNKNOWN);
    assertThat(classification.retryable()).isFalse();
    assertThat(classification.reconciliationRequired()).isTrue();
  }
}
