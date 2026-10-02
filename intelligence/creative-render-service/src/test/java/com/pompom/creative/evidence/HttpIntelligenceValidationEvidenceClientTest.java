package com.pompom.creative.evidence;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withResourceNotFound;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import java.net.SocketTimeoutException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class HttpIntelligenceValidationEvidenceClientTest {
  private MockRestServiceServer server;
  private IntelligenceValidationEvidenceClient client;

  @BeforeEach
  void setUp() {
    RestClient.Builder builder = RestClient.builder().baseUrl("http://intelligence.test");
    server = MockRestServiceServer.bindTo(builder).build();
    client = new HttpIntelligenceValidationEvidenceClient(builder.build());
  }

  @Test
  void fetchesAndDeserializesEvidence() {
    server
        .expect(
            once(), requestTo("http://intelligence.test/api/v1/internal/validation-evidence/42"))
        .andExpect(method(HttpMethod.GET))
        .andRespond(
            withSuccess(
                """
                {"validationRecordId":42,"contentId":10,"promptVersionId":11,
                 "promptSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                 "status":"RENDER_READY","blockerCount":0,"criticalCount":0,"warningCount":0,
                 "deterministicRulesetVersion":"1.0","semanticProvider":"openai",
                 "semanticModelVersion":"gpt-4o","producibilityValidatorVersion":"1.0",
                 "independentRevalidationId":"8e2c6f1a-0000-0000-0000-000000000000",
                 "independentlyRevalidatedAt":"2026-01-01T00:00:00Z",
                 "validatedAt":"2026-01-01T00:00:00Z","expiresAt":"2026-01-02T00:00:00Z"}
                """,
                MediaType.APPLICATION_JSON));

    ValidationEvidenceDto evidence = client.getEvidence(42L);

    assertThat(evidence.validationRecordId()).isEqualTo(42L);
    assertThat(evidence.contentId()).isEqualTo(10L);
    assertThat(evidence.status()).isEqualTo("RENDER_READY");
    server.verify();
  }

  @Test
  void mapsNotFoundToTypedException() {
    server
        .expect(
            once(), requestTo("http://intelligence.test/api/v1/internal/validation-evidence/404"))
        .andRespond(withResourceNotFound());

    assertThatThrownBy(() -> client.getEvidence(404L))
        .isInstanceOf(ValidationEvidenceNotFoundException.class);
  }

  @Test
  void mapsUnprocessableEntityToTypedIncompleteException() {
    server
        .expect(once(), requestTo("http://intelligence.test/api/v1/internal/validation-evidence/7"))
        .andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY));

    assertThatThrownBy(() -> client.getEvidence(7L))
        .isInstanceOf(ValidationEvidenceIncompleteRemoteException.class);
  }

  @Test
  void mapsServerFailureToTypedException() {
    server
        .expect(once(), requestTo("http://intelligence.test/api/v1/internal/validation-evidence/1"))
        .andRespond(withServerError());

    assertThatThrownBy(() -> client.getEvidence(1L))
        .isInstanceOf(ValidationEvidenceServiceException.class);
  }

  @Test
  void mapsTimeoutToTypedException() {
    RestClient timedOutClient =
        RestClient.builder()
            .requestFactory(
                (uri, httpMethod) -> {
                  throw new SocketTimeoutException("timed out");
                })
            .build();
    IntelligenceValidationEvidenceClient timeoutClient =
        new HttpIntelligenceValidationEvidenceClient(timedOutClient);

    assertThatThrownBy(() -> timeoutClient.getEvidence(1L))
        .isInstanceOf(ValidationEvidenceTimeoutException.class);
  }
}
