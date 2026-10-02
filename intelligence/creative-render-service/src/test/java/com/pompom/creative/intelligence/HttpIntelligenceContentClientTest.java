package com.pompom.creative.intelligence;

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

class HttpIntelligenceContentClientTest {
  private MockRestServiceServer server;
  private IntelligenceContentClient client;

  @BeforeEach
  void setUp() {
    RestClient.Builder builder = RestClient.builder().baseUrl("http://intelligence.test");
    server = MockRestServiceServer.bindTo(builder).build();
    client = new HttpIntelligenceContentClient(builder.build());
  }

  @Test
  void fetchesAndDeserializesSnapshot() {
    server
        .expect(
            once(),
            requestTo(
                "http://intelligence.test/api/v1/intelligence/contents/10/prompt-versions/11"))
        .andExpect(method(HttpMethod.GET))
        .andRespond(
            withSuccess(
                """
                {"contractVersion":"v1","contentId":10,"contentTitle":"Kiko","contentType":"EPISODE","contentStatus":"RENDER_READY","promptVersionId":11,"promptVersionNumber":3,"promptText":"gentle rain","parsedIr":"{}","promptSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
                """,
                MediaType.APPLICATION_JSON));

    ContentPromptSnapshot snapshot = client.fetch(10L, 11L);

    assertThat(snapshot.contentTitle()).isEqualTo("Kiko");
    assertThat(snapshot.promptText()).isEqualTo("gentle rain");
    server.verify();
  }

  @Test
  void mapsNotFoundToTypedException() {
    server
        .expect(
            once(),
            requestTo(
                "http://intelligence.test/api/v1/intelligence/contents/10/prompt-versions/99"))
        .andRespond(withResourceNotFound());

    assertThatThrownBy(() -> client.fetch(10L, 99L))
        .isInstanceOf(IntelligenceContentNotFoundException.class);
  }

  @Test
  void mapsConflictToTypedException() {
    server
        .expect(
            once(),
            requestTo(
                "http://intelligence.test/api/v1/intelligence/contents/10/prompt-versions/11"))
        .andRespond(withStatus(HttpStatus.CONFLICT));

    assertThatThrownBy(() -> client.fetch(10L, 11L))
        .isInstanceOf(IntelligenceContentConflictException.class);
  }

  @Test
  void mapsServerFailureToTypedException() {
    server
        .expect(
            once(),
            requestTo(
                "http://intelligence.test/api/v1/intelligence/contents/10/prompt-versions/11"))
        .andRespond(withServerError());

    assertThatThrownBy(() -> client.fetch(10L, 11L))
        .isInstanceOf(IntelligenceContentServiceException.class);
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
    IntelligenceContentClient timeoutClient = new HttpIntelligenceContentClient(timedOutClient);

    assertThatThrownBy(() -> timeoutClient.fetch(10L, 11L))
        .isInstanceOf(IntelligenceContentTimeoutException.class);
  }
}
