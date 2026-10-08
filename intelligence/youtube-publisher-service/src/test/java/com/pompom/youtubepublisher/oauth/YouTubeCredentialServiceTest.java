package com.pompom.youtubepublisher.oauth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.youtubepublisher.YouTubePublisherProperties;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class YouTubeCredentialServiceTest {

  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
  private static final String TOKEN = "refresh-token-secret";

  @Test
  void cachesRefreshedAccessTokenAndExposesOnlyRedactedOutcome() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    YouTubePublisherProperties properties = properties();
    YouTubeCredentialService service =
        new YouTubeCredentialService(builder, OBJECT_MAPPER, properties);
    server
        .expect(requestTo("https://oauth.test/token"))
        .andExpect(method(HttpMethod.POST))
        .andRespond(
            withSuccess(
                "{\"access_token\":\"access-secret\",\"expires_in\":3600}",
                MediaType.APPLICATION_JSON));

    assertThat(service.accessToken()).isEqualTo("access-secret");
    assertThat(service.accessToken()).isEqualTo("access-secret");
    assertThat(service.lastRefreshOutcome().status()).isEqualTo("succeeded");
    assertThat(service.lastRefreshOutcome().message()).isNull();
    server.verify();
  }

  @Test
  void mapsInvalidGrantWithoutReturningRefreshToken() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    YouTubeCredentialService service =
        new YouTubeCredentialService(builder, OBJECT_MAPPER, properties());
    server
        .expect(requestTo("https://oauth.test/token"))
        .andRespond(
            withStatus(HttpStatus.BAD_REQUEST)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"error\":\"invalid_grant\",\"error_description\":\"" + TOKEN + "\"}"));

    assertThatThrownBy(service::accessToken)
        .isInstanceOf(YouTubeCredentialService.YouTubeCredentialException.class)
        .satisfies(
            failure -> {
              YouTubeCredentialService.YouTubeCredentialException exception =
                  (YouTubeCredentialService.YouTubeCredentialException) failure;
              assertThat(exception.classification().errorClass())
                  .isEqualTo(PublishErrorClass.AUTHENTICATION);
              assertThat(exception.getMessage()).doesNotContain(TOKEN);
            });
    assertThat(service.lastRefreshOutcome().message()).doesNotContain(TOKEN);
    server.verify();
  }

  private YouTubePublisherProperties properties() {
    return new YouTubePublisherProperties(
        true,
        true,
        false,
        "internal",
        "client-id",
        "client-secret",
        "",
        TOKEN,
        "https://oauth.test/token",
        "https://youtube.test/youtube/v3",
        "https://youtube.test/upload/youtube/v3",
        4,
        100,
        Duration.ofSeconds(2),
        Duration.ofSeconds(2),
        1,
        "22",
        "public",
        null,
        "account-1");
  }
}
