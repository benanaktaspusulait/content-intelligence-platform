package com.pompom.metapublisher.facebook;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.metapublisher.MetaPublisherProperties;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hamcrest.Matchers;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.ExpectedCount;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class FacebookReelsClientTest {

  private static final String TOKEN = "page-write-token";
  private static final String GRAPH = "https://graph.facebook.test";
  private static final String RUPLOAD = "https://rupload.facebook.test/video-upload";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void publishesVideoReelThroughStartUploadStatusFinishAndPermalink() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(3));

    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andExpect(
            org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                .string(
                    Matchers.allOf(
                        Matchers.containsString("upload_phase=start"),
                        Matchers.not(Matchers.containsString("access_token")))))
        .andExpect(
            request -> assertThat(request.getURI().toString()).doesNotContain("access_token"))
        .andRespond(
            withSuccess(
                "{\"video_id\":\"video-1\",\"upload_url\":\"" + RUPLOAD + "/session-1\"}",
                MediaType.APPLICATION_JSON));

    server
        .expect(requestTo(RUPLOAD + "/session-1"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "OAuth " + TOKEN))
        .andExpect(header("file_url", "https://cdn.example/video-1.mp4"))
        .andExpect(
            org.springframework.test.web.client.match.MockRestRequestMatchers.content().string(""))
        .andExpect(
            request -> assertThat(request.getURI().toString()).doesNotContain("access_token"))
        .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));

    server
        .expect(requestTo(GRAPH + "/v26.0/video-1?fields=status"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andRespond(
            withSuccess(
                "{\"status\":{\"uploading_phase\":{\"status\":\"complete\"},\"processing_phase\":{\"status\":\"in_progress\"}}}",
                MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-1?fields=status"))
        .andRespond(
            withSuccess(
                "{\"status\":{\"uploading_phase\":{\"status\":\"complete\"},\"processing_phase\":{\"status\":\"complete\"}}}",
                MediaType.APPLICATION_JSON));

    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andExpect(
            org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                .string(
                    Matchers.allOf(
                        Matchers.containsString("upload_phase=finish"),
                        Matchers.containsString("video_id=video-1"),
                        Matchers.containsString("video_state=PUBLISHED"),
                        Matchers.containsString("description=caption"),
                        Matchers.not(Matchers.containsString("access_token")))))
        .andRespond(
            withSuccess("{\"success\":true,\"post_id\":\"post-1\"}", MediaType.APPLICATION_JSON));

    server
        .expect(requestTo(GRAPH + "/v26.0/video-1?fields=permalink_url"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andRespond(
            withSuccess(
                "{\"id\":\"video-1\",\"permalink_url\":\"https://facebook.example/post-1\"}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.publish(command("https://cdn.example/video-1.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerPostId()).isEqualTo("post-1");
    assertThat(result.providerVideoId()).isEqualTo("video-1");
    assertThat(result.permalink()).isEqualTo("https://facebook.example/post-1");
    assertThat(result.errorClass()).isNull();
    server.verify();
  }

  @Test
  void uploadsLocalBytesWhenNoHostedUrlIsProvided() throws Exception {
    Path video = Files.createTempFile("meta-facebook", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));

      server
          .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
          .andRespond(withSuccess("{\"video_id\":\"video-2\"}", MediaType.APPLICATION_JSON));
      server
          .expect(requestTo(RUPLOAD + "/v26.0/video-2"))
          .andExpect(header(HttpHeaders.AUTHORIZATION, "OAuth " + TOKEN))
          .andExpect(header("offset", "0"))
          .andExpect(header("file_size", "4"))
          .andExpect(header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_OCTET_STREAM_VALUE))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {1, 2, 3, 4}))
          .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));
      server
          .expect(requestTo(GRAPH + "/v26.0/video-2?fields=status"))
          .andRespond(
              withSuccess(
                  "{\"status\":{\"processing_phase\":{\"status\":\"complete\"}}}",
                  MediaType.APPLICATION_JSON));
      server
          .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
          .andRespond(
              withSuccess(
                  "{\"success\":true,\"post_id\":\"video-2\"}", MediaType.APPLICATION_JSON));
      server
          .expect(requestTo(GRAPH + "/v26.0/video-2?fields=permalink_url"))
          .andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video.toString(), "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      assertThat(result.providerPostId()).isEqualTo("video-2");
      assertThat(result.providerVideoId()).isEqualTo("video-2");
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void mapsAuthenticationFailureWithoutLeakingToken() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andExpect(request -> assertThat(request.getURI().toString()).doesNotContain(TOKEN))
        .andRespond(
            withStatus(HttpStatus.UNAUTHORIZED)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"error\":{\"message\":\"bad token " + TOKEN + "\",\"code\":190}}"));

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.AUTHENTICATION.wireValue());
    assertThat(result.message()).doesNotContain(TOKEN);
    server.verify();
  }

  @Test
  void returnsReconciliationRequiredWhenProcessingTimesOut() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client =
        new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1, Duration.ZERO));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(withSuccess("{\"video_id\":\"video-timeout\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(RUPLOAD + "/v26.0/video-timeout"))
        .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-timeout?fields=status"))
        .andRespond(
            withSuccess(
                "{\"status\":{\"processing_phase\":{\"status\":\"in_progress\"}}}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
    assertThat(result.errorClass())
        .isEqualTo(PublishErrorClass.RECONCILIATION_REQUIRED.wireValue());
    server.verify();
  }

  @Test
  void retriesRateLimitedStartBeforeReturningCompletedResult() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(2));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(
            withStatus(HttpStatus.TOO_MANY_REQUESTS)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"error\":{\"message\":\"slow down\",\"code\":613}}"));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(withSuccess("{\"video_id\":\"video-retry\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(RUPLOAD + "/v26.0/video-retry"))
        .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-retry?fields=status"))
        .andRespond(
            withSuccess(
                "{\"status\":{\"processing_phase\":{\"status\":\"complete\"}}}",
                MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(
            withSuccess(
                "{\"success\":true,\"post_id\":\"video-retry\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-retry?fields=permalink_url"))
        .andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerVideoId()).isEqualTo("video-retry");
    server.verify();
  }

  @Test
  void rejectsMissingLocalAssetBeforeCreatingRemoteUploadSession() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));

    PublishResult result = client.publish(command("/path/that/does/not/exist.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
    server.verify();
  }

  @Test
  void reconcilesExistingVideoWithReadOnlyGraphLookup() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-1?fields=id,permalink_url"))
        .andExpect(method(HttpMethod.GET))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andRespond(
            withSuccess(
                "{\"id\":\"video-1\",\"permalink_url\":\"https://facebook.example/post-1\"}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("page-1", null, "video-1");

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerVideoId()).isEqualTo("video-1");
    assertThat(result.permalink()).isEqualTo("https://facebook.example/post-1");
    server.verify();
  }

  @Test
  void appliesConfiguredRequestDeadlineBeforeProviderResponseArrives() throws InterruptedException {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client =
        new FacebookReelsClient(
            builder,
            OBJECT_MAPPER,
            properties(1, Duration.ofSeconds(1), Duration.ofMillis(10), Duration.ofSeconds(1)));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(
            request -> {
              try {
                Thread.sleep(100);
              } catch (InterruptedException failure) {
                Thread.currentThread().interrupt();
              }
              return withSuccess("{\"video_id\":\"video-slow\"}", MediaType.APPLICATION_JSON)
                  .createResponse(request);
            });

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.message()).contains("timed out");
    Thread.sleep(120);
    server.verify();
  }

  @Test
  void mapsServerFailureBeforeCompletionToReconciliationRequired() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(
            withStatus(HttpStatus.SERVICE_UNAVAILABLE)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"error\":{\"message\":\"temporary provider failure\"}}"));

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.errorClass())
        .isEqualTo(PublishErrorClass.RECONCILIATION_REQUIRED.wireValue());
    assertThat(result.reconciliationRequired()).isTrue();
    server.verify();
  }

  @Test
  void finishWithoutPublicationEvidenceRemainsReconciliationRequired() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));

    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(withSuccess("{\"video_id\":\"video-no-proof\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(RUPLOAD + "/v26.0/video-no-proof"))
        .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-no-proof?fields=status"))
        .andRespond(
            withSuccess(
                "{\"status\":{\"processing_phase\":{\"status\":\"complete\"}}}",
                MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-no-proof?fields=permalink_url"))
        .andRespond(withSuccess("{\"id\":\"video-no-proof\"}", MediaType.APPLICATION_JSON));

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
    server.verify();
  }

  @Test
  void finishFailureAfterUploadIsReconciliationRequired() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));

    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(
            withSuccess("{\"video_id\":\"video-finish-failure\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(RUPLOAD + "/v26.0/video-finish-failure"))
        .andRespond(withSuccess("{\"success\":true}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-finish-failure?fields=status"))
        .andRespond(
            withSuccess(
                "{\"status\":{\"processing_phase\":{\"status\":\"complete\"}}}",
                MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
        .andRespond(
            withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"error\":{\"message\":\"finish unavailable\"}}"));

    PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.providerVideoId()).isEqualTo("video-finish-failure");
    server.verify();
  }

  @Test
  void reconciliationWithoutPublishedEvidenceRemainsUncertain() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-upload-session?fields=id,permalink_url"))
        .andExpect(method(HttpMethod.GET))
        .andRespond(withSuccess("{\"id\":\"video-upload-session\"}", MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("page-1", null, "video-upload-session");

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
    server.verify();
  }

  @Test
  void reconciliationRejectsAProviderObjectDifferentFromTheRequestedIdentity() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));
    server
        .expect(requestTo(GRAPH + "/v26.0/video-requested?fields=id,permalink_url"))
        .andRespond(
            withSuccess(
                "{\"id\":\"different-video\",\"permalink_url\":\"https://facebook.example/p/different\"}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("page-1", null, "video-requested");

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.reconciliationRequired()).isTrue();
    server.verify();
  }

  @Test
  void rejectsUnsafeProviderUploadUrlsBeforeSendingOAuth() {
    for (String unsafeUploadUrl :
        List.of(
            "http://rupload.facebook.test/video-upload/session-unsafe",
            "https://user@rupload.facebook.test/video-upload/session-unsafe",
            "https://rupload.facebook.test/video-upload/session-unsafe?access_token=secret",
            "https://rupload.facebook.test/video-upload/../evil",
            "https://rupload.facebook.test/video-upload/./session-unsafe",
            "https://rupload.facebook.test/video-upload/%2e%2e/evil",
            "https://rupload.facebook.test/video-upload/%2E/session-unsafe")) {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      FacebookReelsClient client = new FacebookReelsClient(builder, OBJECT_MAPPER, properties(1));
      server
          .expect(requestTo(GRAPH + "/v26.0/page-1/video_reels"))
          .andRespond(
              withSuccess(
                  "{\"video_id\":\"video-unsafe-upload\",\"upload_url\":\""
                      + unsafeUploadUrl
                      + "\"}",
                  MediaType.APPLICATION_JSON));
      server.expect(ExpectedCount.never(), requestTo(unsafeUploadUrl));

      PublishResult result = client.publish(command("https://cdn.example/video.mp4", "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    }
  }

  private MetaPublisherProperties properties(int maxAttempts) {
    return properties(
        maxAttempts, Duration.ofSeconds(1), Duration.ofSeconds(1), Duration.ofSeconds(1));
  }

  private MetaPublisherProperties properties(int maxAttempts, Duration pollTimeout) {
    return properties(maxAttempts, pollTimeout, Duration.ofSeconds(1), Duration.ofSeconds(1));
  }

  private MetaPublisherProperties properties(
      int maxAttempts, Duration pollTimeout, Duration requestTimeout, Duration uploadTimeout) {
    return new MetaPublisherProperties(
        true,
        true,
        "internal-token",
        "v26.0",
        GRAPH,
        RUPLOAD,
        "page-1",
        TOKEN,
        "",
        "",
        requestTimeout,
        uploadTimeout,
        pollTimeout,
        Duration.ZERO,
        maxAttempts,
        true,
        "",
        "none",
        "",
        "",
        "",
        false);
  }

  private PublishCommand command(String assetReference, String caption) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "facebook-command-" + UUID.randomUUID(),
        "page-1",
        assetReference,
        "a".repeat(64),
        "title",
        caption,
        List.of(),
        false,
        Map.of());
  }
}
