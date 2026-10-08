package com.pompom.tiktokpublisher.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.tiktokpublisher.TikTokPublisherProperties;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

class TikTokContentClientReviewFindingsTest {

  private static final String TOKEN = "tiktok-access-token";
  private static final String API = "https://open.tiktok.test";
  private static final String UPLOAD = "https://upload.tiktok.test/session-1";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void doesNotRetryProviderCreatingInitAfterServerError() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(
              builder,
              OBJECT_MAPPER,
              properties(
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ZERO,
                  3));

      expectCreator(server, "{\"creator_username\":\"creator\"}");
      server
          .expect(requestTo(API + "/v2/post/publish/video/init/"))
          .andRespond(withStatus(HttpStatus.BAD_GATEWAY));

      PublishResult result = client.publish(command(video.toString()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      assertThat(result.errorClass())
          .isEqualTo(PublishErrorClass.RECONCILIATION_REQUIRED.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void treatsInitFiveHundredWithAnAuthCodeAsUncertainAfterDispatch() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(
              builder,
              OBJECT_MAPPER,
              properties(
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ZERO,
                  1));

      expectCreator(server, "{\"creator_username\":\"creator\"}");
      server
          .expect(requestTo(API + "/v2/post/publish/video/init/"))
          .andRespond(
              withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                  .contentType(MediaType.APPLICATION_JSON)
                  .body("{\"error\":{\"code\":\"auth\",\"message\":\"provider busy\"}}"));

      PublishResult result = client.publish(command(video.toString()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void doesNotRetryProviderCreatingInitAfterTransportFailure() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(
              builder,
              OBJECT_MAPPER,
              properties(
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ZERO,
                  3));

      expectCreator(server, "{\"creator_username\":\"creator\"}");
      server
          .expect(requestTo(API + "/v2/post/publish/video/init/"))
          .andRespond(
              request -> {
                throw new ResourceAccessException("init timed out");
              });

      PublishResult result = client.publish(command(video.toString()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void rejectsCreatorIdentityThatDoesNotMatchConfiguredAccount() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(
              builder,
              OBJECT_MAPPER,
              properties(
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ZERO,
                  1));

      expectCreator(server, "{\"creator_open_id\":\"different-account\"}");

      PublishResult result = client.publish(command(video.toString()));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.AUTHORIZATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void failsClosedWhenCreatorDataIsEmpty() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(
              builder,
              OBJECT_MAPPER,
              properties(
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ZERO,
                  1));

      expectCreator(server, "{}");

      PublishResult result = client.publish(command(video.toString()));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.AUTHORIZATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void appliesRequestTimeoutToApiUrisAndUploadTimeoutToSignedUploadUris() throws Exception {
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext("/v2/probe", exchange -> delayedResponse(exchange, 300));
    server.createContext("/v2/upload", exchange -> delayedResponse(exchange, 100));
    server.createContext("/upload/session", exchange -> delayedResponse(exchange, 100));
    server.start();
    try {
      String base = "http://127.0.0.1:" + server.getAddress().getPort();
      TikTokPublisherProperties properties =
          properties(
              base,
              Duration.ofMillis(50),
              Duration.ofMillis(500),
              Duration.ofSeconds(1),
              Duration.ZERO,
              1);
      RestClient client =
          RestClient.builder()
              .requestFactory(TikTokContentClient.deadlineRequestFactory(properties))
              .build();

      long started = System.nanoTime();
      assertThatThrownBy(
              () -> client.post().uri(base + "/v2/probe").body("{}").retrieve().toBodilessEntity())
          .isInstanceOf(RestClientException.class);
      Duration apiElapsed = Duration.ofNanos(System.nanoTime() - started);

      assertThat(apiElapsed).isLessThan(Duration.ofMillis(250));
      assertThatCode(
              () ->
                  client
                      .put()
                      .uri(base + "/upload/session")
                      .body(new byte[] {1})
                      .retrieve()
                      .toBodilessEntity())
          .doesNotThrowAnyException();
      assertThatCode(
              () ->
                  client
                      .put()
                      .uri(base + "/v2/upload")
                      .body(new byte[] {1})
                      .retrieve()
                      .toBodilessEntity())
          .doesNotThrowAnyException();
    } finally {
      server.stop(0);
    }
  }

  @Test
  void clampsPollingSleepToTheRemainingDeadline() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(
              builder,
              OBJECT_MAPPER,
              properties(
                  Duration.ofSeconds(1),
                  Duration.ofSeconds(1),
                  Duration.ofMillis(60),
                  Duration.ofSeconds(1),
                  1));

      expectCreator(server, "{\"creator_username\":\"creator\"}");
      expectInit(server, "publish-poll-deadline");
      server.expect(requestTo(UPLOAD)).andRespond(withStatus(HttpStatus.OK));
      server
          .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
          .andRespond(
              withSuccess(
                  "{\"data\":{\"status\":\"PROCESSING_UPLOAD\",\"publish_id\":\"publish-poll-deadline\"}}",
                  MediaType.APPLICATION_JSON));

      long started = System.nanoTime();
      PublishResult result = client.publish(command(video.toString()));
      Duration elapsed = Duration.ofNanos(System.nanoTime() - started);

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(elapsed).isLessThan(Duration.ofMillis(500));
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void doesNotRetryPollingWhenBackoffExceedsRemainingDeadline() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    TikTokContentClient client =
        new TikTokContentClient(
            builder,
            OBJECT_MAPPER,
            properties(
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                Duration.ofMillis(60),
                Duration.ZERO,
                3));
    server
        .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
        .andRespond(withStatus(HttpStatus.TOO_MANY_REQUESTS));

    long started = System.nanoTime();
    PublishResult result = client.reconcile("publish-rate-limited");
    Duration elapsed = Duration.ofNanos(System.nanoTime() - started);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(elapsed).isLessThan(Duration.ofMillis(500));
    server.verify();
  }

  @Test
  void boundsBlockedStatusRequestByPollDeadline() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    TikTokContentClient client =
        new TikTokContentClient(
            builder,
            OBJECT_MAPPER,
            properties(
                Duration.ofSeconds(1),
                Duration.ofSeconds(1),
                Duration.ofMillis(60),
                Duration.ZERO,
                1));
    server
        .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
        .andRespond(
            request -> {
              try {
                Thread.sleep(300);
              } catch (InterruptedException failure) {
                Thread.currentThread().interrupt();
              }
              return withSuccess(
                      "{\"data\":{\"status\":\"PROCESSING_UPLOAD\",\"publish_id\":\"publish-blocked\"}}",
                      MediaType.APPLICATION_JSON)
                  .createResponse(request);
            });

    long started = System.nanoTime();
    PublishResult result = client.reconcile("publish-blocked");
    Duration elapsed = Duration.ofNanos(System.nanoTime() - started);

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(elapsed).isLessThan(Duration.ofMillis(250));
    server.verify();
  }

  private void expectCreator(MockRestServiceServer server, String data) {
    server
        .expect(requestTo(API + "/v2/post/publish/creator_info/query/"))
        .andRespond(withSuccess("{\"data\":" + data + "}", MediaType.APPLICATION_JSON));
  }

  private void expectInit(MockRestServiceServer server, String publishId) {
    server
        .expect(requestTo(API + "/v2/post/publish/video/init/"))
        .andRespond(
            withSuccess(
                "{\"data\":{\"publish_id\":\""
                    + publishId
                    + "\",\"upload_url\":\""
                    + UPLOAD
                    + "\"}}",
                MediaType.APPLICATION_JSON));
  }

  private PublishCommand command(String assetReference) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "idempotency-review",
        "account-1",
        assetReference,
        "a".repeat(64),
        "title",
        "caption",
        List.of(),
        true,
        Map.of());
  }

  private TikTokPublisherProperties properties(
      Duration requestTimeout,
      Duration uploadTimeout,
      Duration pollTimeout,
      Duration pollInterval,
      int maxAttempts) {
    return properties(API, requestTimeout, uploadTimeout, pollTimeout, pollInterval, maxAttempts);
  }

  private TikTokPublisherProperties properties(
      String apiBase,
      Duration requestTimeout,
      Duration uploadTimeout,
      Duration pollTimeout,
      Duration pollInterval,
      int maxAttempts) {
    return new TikTokPublisherProperties(
        true,
        true,
        "internal-secret",
        TOKEN,
        apiBase,
        "v2",
        false,
        4,
        TikTokPublisherProperties.DEFAULT_MAX_FILE_SIZE,
        requestTimeout,
        uploadTimeout,
        pollTimeout,
        pollInterval,
        maxAttempts,
        true,
        "SELF_ONLY",
        false,
        false,
        false,
        1000,
        "account-1");
  }

  private void delayedResponse(HttpExchange exchange, long delayMillis) throws IOException {
    try {
      Thread.sleep(delayMillis);
    } catch (InterruptedException failure) {
      Thread.currentThread().interrupt();
    }
    exchange.sendResponseHeaders(200, -1);
    exchange.close();
  }
}
