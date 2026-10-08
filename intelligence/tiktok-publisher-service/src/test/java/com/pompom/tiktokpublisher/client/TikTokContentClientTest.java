package com.pompom.tiktokpublisher.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.tiktokpublisher.TikTokPublisherProperties;
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
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class TikTokContentClientTest {

  private static final String TOKEN = "tiktok-access-token";
  private static final String API = "https://open.tiktok.test";
  private static final String UPLOAD = "https://upload.tiktok.test/session-1";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void uploadsEveryChunkWithInclusiveContentRangesAndCompletesOnlyAfterProviderStatus()
      throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4, 5, 6});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client = new TikTokContentClient(builder, OBJECT_MAPPER, properties(4));

      expectCreatorValidation(server);
      server
          .expect(requestTo(API + "/v2/post/publish/video/init/"))
          .andExpect(method(HttpMethod.POST))
          .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .string(
                      Matchers.allOf(
                          Matchers.containsString("\"video_size\":6"),
                          Matchers.containsString("\"chunk_size\":4"),
                          Matchers.containsString("\"total_chunk_count\":2"),
                          Matchers.containsString("\"privacy_level\":\"SELF_ONLY\""),
                          Matchers.containsString("\"title\":\"caption #tag\""),
                          Matchers.not(Matchers.containsString(TOKEN)))))
          .andRespond(
              withSuccess(
                  "{\"data\":{\"publish_id\":\"publish-1\",\"upload_url\":\"" + UPLOAD + "\"}}",
                  MediaType.APPLICATION_JSON));

      server
          .expect(requestTo(UPLOAD))
          .andExpect(method(HttpMethod.PUT))
          .andExpect(header(HttpHeaders.CONTENT_TYPE, videoMp4()))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-3/6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {1, 2, 3, 4}))
          .andRespond(withStatus(HttpStatus.OK));
      server
          .expect(requestTo(UPLOAD))
          .andExpect(method(HttpMethod.PUT))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 4-5/6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {5, 6}))
          .andRespond(withStatus(HttpStatus.CREATED));

      expectStatus(server, "PROCESSING_UPLOAD", "publish-1", null);
      server
          .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
          .andExpect(method(HttpMethod.POST))
          .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
          .andRespond(
              withSuccess(
                  "{\"data\":{\"status\":\"PUBLISH_COMPLETE\",\"publish_id\":\"publish-1\",\"share_url\":\"https://tiktok.example/video/1\"}}",
                  MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video.toString(), "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      assertThat(result.providerPostId()).isEqualTo("publish-1");
      assertThat(result.permalink()).isEqualTo("https://tiktok.example/video/1");
      assertThat(result.errorClass()).isNull();
      assertThat(result.reconciliationRequired()).isFalse();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void returnsProviderFailureWhenStatusIsTerminalFailed() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client = new TikTokContentClient(builder, OBJECT_MAPPER, properties(4));

      expectCreatorValidation(server);
      expectInit(server, "publish-failed");
      server.expect(requestTo(UPLOAD)).andRespond(withStatus(HttpStatus.NO_CONTENT));
      server
          .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
          .andRespond(
              withSuccess(
                  "{\"data\":{\"status\":\"FAILED\",\"publish_id\":\"publish-failed\",\"fail_reason\":\"video rejected\"}}",
                  MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video.toString(), "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.providerPostId()).isEqualTo("publish-failed");
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.PROVIDER_REJECTED.wireValue());
      assertThat(result.reconciliationRequired()).isFalse();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void neverTreatsUploadAcceptanceAsCompletedWhenPollingTimesOut() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(builder, OBJECT_MAPPER, properties(4, Duration.ZERO));

      expectCreatorValidation(server);
      expectInit(server, "publish-timeout");
      server.expect(requestTo(UPLOAD)).andRespond(withStatus(HttpStatus.OK));

      PublishResult result = client.publish(command(video.toString(), "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.providerPostId()).isEqualTo("publish-timeout");
      assertThat(result.reconciliationRequired()).isTrue();
      assertThat(result.errorClass())
          .isEqualTo(PublishErrorClass.RECONCILIATION_REQUIRED.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void mapsInitAuthenticationFailureWithoutLeakingAccessToken() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client = new TikTokContentClient(builder, OBJECT_MAPPER, properties(4));

      expectCreatorValidation(server);
      server
          .expect(requestTo(API + "/v2/post/publish/video/init/"))
          .andRespond(
              withStatus(HttpStatus.UNAUTHORIZED)
                  .contentType(MediaType.APPLICATION_JSON)
                  .body("{\"error\":{\"message\":\"bad token " + TOKEN + "\"}}"));

      PublishResult result = client.publish(command(video.toString(), "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.AUTHENTICATION.wireValue());
      assertThat(result.message()).doesNotContain(TOKEN);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void rejectsOversizedAssetBeforeCreatorOrInitCalls() throws Exception {
    Path video = Files.createTempFile("tiktok", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      TikTokContentClient client =
          new TikTokContentClient(builder, OBJECT_MAPPER, properties(4, 3, Duration.ZERO));

      PublishResult result = client.publish(command(video.toString(), "caption"));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void reconcilesOnlyWithStatusEndpointAndRequiresMatchingCompletedIdentity() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    TikTokContentClient client = new TikTokContentClient(builder, OBJECT_MAPPER, properties(4));
    server
        .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andExpect(
            org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                .string(Matchers.containsString("\"publish_id\":\"publish-reconcile\"")))
        .andRespond(
            withSuccess(
                "{\"data\":{\"status\":\"PUBLISH_COMPLETE\",\"publish_id\":\"publish-reconcile\",\"share_url\":\"https://tiktok.example/video/reconcile\"}}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("publish-reconcile");

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerPostId()).isEqualTo("publish-reconcile");
    assertThat(result.permalink()).isEqualTo("https://tiktok.example/video/reconcile");
    server.verify();
  }

  @Test
  void truncatesCaptionAtTheProviderCodePointLimitWithoutSplittingUnicode() {
    String caption = "😀".repeat(TikTokContentClient.CAPTION_LIMIT + 1);

    String normalized = TikTokContentClient.truncateCaption(caption);

    assertThat(normalized.codePointCount(0, normalized.length()))
        .isEqualTo(TikTokContentClient.CAPTION_LIMIT);
    assertThat(normalized).endsWith("…");
  }

  private void expectCreatorValidation(MockRestServiceServer server) {
    server
        .expect(requestTo(API + "/v2/post/publish/creator_info/query/"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andRespond(
            withSuccess(
                "{\"data\":{\"creator_username\":\"creator\",\"creator_avatar_url\":\"https://avatar.example/1\"}}",
                MediaType.APPLICATION_JSON));
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

  private void expectStatus(
      MockRestServiceServer server, String status, String publishId, String shareUrl) {
    String share = shareUrl == null ? "" : ",\"share_url\":\"" + shareUrl + "\"";
    server
        .expect(requestTo(API + "/v2/post/publish/status/fetch/"))
        .andRespond(
            withSuccess(
                "{\"data\":{\"status\":\""
                    + status
                    + "\",\"publish_id\":\""
                    + publishId
                    + "\""
                    + share
                    + "}}",
                MediaType.APPLICATION_JSON));
  }

  private PublishCommand command(String assetReference, String caption) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "idempotency-1",
        "account-1",
        assetReference,
        "a".repeat(64),
        null,
        caption,
        List.of("tag"),
        true,
        Map.of());
  }

  private TikTokPublisherProperties properties(int chunkSize) {
    return properties(chunkSize, Duration.ofSeconds(1));
  }

  private TikTokPublisherProperties properties(int chunkSize, Duration pollTimeout) {
    return properties(chunkSize, 287L * 1024 * 1024, pollTimeout);
  }

  private TikTokPublisherProperties properties(
      int chunkSize, long maxFileSize, Duration pollTimeout) {
    return new TikTokPublisherProperties(
        true,
        true,
        "internal-secret",
        TOKEN,
        API,
        "v2",
        false,
        chunkSize,
        maxFileSize,
        Duration.ofSeconds(2),
        Duration.ofSeconds(2),
        pollTimeout,
        Duration.ZERO,
        1,
        true,
        "SELF_ONLY",
        false,
        false,
        false,
        1000,
        "account-1");
  }

  private static String videoMp4() {
    return MediaType.valueOf("video/mp4").toString();
  }
}
