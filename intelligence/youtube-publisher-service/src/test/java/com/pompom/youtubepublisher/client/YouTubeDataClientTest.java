package com.pompom.youtubepublisher.client;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.youtubepublisher.YouTubePublisherProperties;
import com.pompom.youtubepublisher.oauth.YouTubeCredentialService;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hamcrest.Matchers;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class YouTubeDataClientTest {

  private static final String ACCESS_TOKEN = "youtube-access-token";
  private static final String REFRESH_TOKEN = "youtube-refresh-token";
  private static final String API = "https://youtube.test/youtube/v3";
  private static final String UPLOAD_API = "https://youtube.test/upload/youtube/v3";
  private static final String TOKEN_API = "https://oauth.test/token";
  private static final String UPLOAD = "https://upload.youtube.test/session-1";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void uploadsResumableChunksWithShortsMetadataAndCanonicalShareUrl() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4, 5, 6});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubePublisherProperties properties = properties(ACCESS_TOKEN, "", 4, 100);
      YouTubeDataClient client = client(builder, properties);

      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andExpect(method(HttpMethod.POST))
          .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + ACCESS_TOKEN))
          .andExpect(header("X-Upload-Content-Type", "video/*"))
          .andExpect(header("X-Upload-Content-Length", "6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .string(
                      Matchers.allOf(
                          Matchers.containsString("\"title\":\"A title\""),
                          Matchers.containsString("\"description\":\"description\\n\\n#Shorts\""),
                          Matchers.containsString("\"tags\":[\"tag-one\"]"),
                          Matchers.containsString("\"categoryId\":\"22\""),
                          Matchers.containsString("\"privacyStatus\":\"private\""),
                          Matchers.not(Matchers.containsString("selfDeclaredMadeForKids")),
                          Matchers.not(Matchers.containsString(ACCESS_TOKEN)))))
          .andRespond(withStatus(HttpStatus.OK).header("Location", UPLOAD));

      server
          .expect(requestTo(UPLOAD))
          .andExpect(method(HttpMethod.PUT))
          .andExpect(header(HttpHeaders.CONTENT_TYPE, "video/*"))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-3/6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {1, 2, 3, 4}))
          .andRespond(
              withStatus(HttpStatusCode.valueOf(308)).header(HttpHeaders.RANGE, "bytes=0-3"));
      server
          .expect(requestTo(UPLOAD))
          .andExpect(method(HttpMethod.PUT))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 4-5/6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {5, 6}))
          .andRespond(withSuccess("{\"id\":\"video-123\"}", MediaType.APPLICATION_JSON));

      PublishResult result =
          client.publish(command(video, "A title", "description", List.of("tag-one"), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      assertThat(result.providerPostId()).isNull();
      assertThat(result.providerVideoId()).isEqualTo("video-123");
      assertThat(result.permalink()).isEqualTo("https://youtube.com/shorts/video-123");
      assertThat(result.errorClass()).isNull();
      assertThat(result.reconciliationRequired()).isFalse();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void refreshesAccessTokenInsideCredentialBoundaryBeforeInitializingUpload() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubePublisherProperties properties =
          properties("", REFRESH_TOKEN, 4, 100, "client-id", "client-secret");
      YouTubeDataClient client = client(builder, properties);

      server
          .expect(requestTo(TOKEN_API))
          .andExpect(method(HttpMethod.POST))
          .andExpect(header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_FORM_URLENCODED_VALUE))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .string(
                      Matchers.allOf(
                          Matchers.containsString("client_id=client-id"),
                          Matchers.containsString("grant_type=refresh_token"),
                          Matchers.containsString("refresh_token=" + REFRESH_TOKEN))))
          .andRespond(
              withSuccess(
                  "{\"access_token\":\"refreshed-access-token\",\"expires_in\":3600}",
                  MediaType.APPLICATION_JSON));
      expectOneChunkUpload(server, "refreshed-access-token", "video-refresh", UPLOAD);

      PublishResult result =
          client.publish(command(video, "Title", "", List.of(), Map.of("made_for_kids", "true")));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      assertThat(result.providerVideoId()).isEqualTo("video-refresh");
      assertThat(result.message()).isNull();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void doesNotCompleteWhenUploadSessionLocationIsMissing() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.errorClass())
          .isEqualTo(PublishErrorClass.RECONCILIATION_REQUIRED.wireValue());
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void doesNotCompleteWhenFinalChunkHasNoProviderVideoId() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      expectInit(server, UPLOAD);
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-0/1"))
          .andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.providerVideoId()).isNull();
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void rejectsOversizedAndOverlongDescriptionBeforeProviderCalls() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient oversizedClient = client(builder, properties(ACCESS_TOKEN, "", 4, 3));
      YouTubeDataClient validationClient = client(builder, properties(ACCESS_TOKEN, "", 4, 100));

      PublishResult oversized =
          oversizedClient.publish(command(video, "Title", "", List.of(), Map.of()));
      PublishResult overlongDescription =
          validationClient.publish(
              command(
                  video,
                  "Title",
                  "d".repeat(YouTubeDataClient.DESCRIPTION_LIMIT + 1),
                  List.of(),
                  Map.of()));

      assertThat(oversized.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(oversized.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
      assertThat(overlongDescription.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(overlongDescription.errorClass())
          .isEqualTo(PublishErrorClass.VALIDATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void mapsProviderAuthenticationFailureWithoutLeakingAccessToken() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andRespond(
              withStatus(HttpStatus.UNAUTHORIZED)
                  .contentType(MediaType.APPLICATION_JSON)
                  .body("{\"error\":\"invalid token " + ACCESS_TOKEN + "\"}"));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.AUTHENTICATION.wireValue());
      assertThat(result.message()).doesNotContain(ACCESS_TOKEN);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void reconcilesOnlyMatchingProcessedProviderVideoIdentity() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
    server
        .expect(requestTo(API + "/videos?part=id,status&id=video-reconcile"))
        .andExpect(method(HttpMethod.GET))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + ACCESS_TOKEN))
        .andRespond(
            withSuccess(
                "{\"items\":[{\"id\":\"video-reconcile\",\"status\":{\"uploadStatus\":\"processed\"}}]}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("video-reconcile");

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerVideoId()).isEqualTo("video-reconcile");
    assertThat(result.permalink()).isEqualTo("https://youtube.com/shorts/video-reconcile");
    server.verify();
  }

  @Test
  void keepsReconciliationRequiredWhenProviderReturnsDifferentVideoIdentity() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
    server
        .expect(requestTo(API + "/videos?part=id,status&id=video-requested"))
        .andRespond(
            withSuccess(
                "{\"items\":[{\"id\":\"different-video\",\"status\":{\"uploadStatus\":\"processed\"}}]}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("video-requested");

    assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(result.providerVideoId()).isEqualTo("video-requested");
    assertThat(result.reconciliationRequired()).isTrue();
    server.verify();
  }

  @Test
  void mapsProviderServerFailureToReconciliationWithoutRetryingInitialization() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andRespond(
              withStatus(HttpStatus.INTERNAL_SERVER_ERROR)
                  .contentType(MediaType.APPLICATION_JSON)
                  .body("{\"error\":{\"message\":\"provider unavailable\"}}"));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void mapsTerminalReconciliationFailureToProviderRejected() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
    server
        .expect(requestTo(API + "/videos?part=id,status&id=video-failed"))
        .andRespond(
            withSuccess(
                "{\"items\":[{\"id\":\"video-failed\",\"status\":{\"uploadStatus\":\"failed\",\"failureReason\":\"codec\"}}]}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("video-failed");

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.providerVideoId()).isEqualTo("video-failed");
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.PROVIDER_REJECTED.wireValue());
    server.verify();
  }

  @Test
  void rejectsBlankTitleBeforeProviderCalls() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));

      PublishResult result = client.publish(command(video, " ", "caption", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void serializesSharedPrivacyLevel() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .string(Matchers.containsString("\"privacyStatus\":\"private\"")))
          .andRespond(withStatus(HttpStatus.OK).header("Location", UPLOAD));
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-0/1"))
          .andRespond(withSuccess("{\"id\":\"video-privacy\"}", MediaType.APPLICATION_JSON));

      PublishCommand privateCommand =
          new PublishCommand(
              UUID.randomUUID(),
              UUID.randomUUID(),
              "youtube-privacy-level",
              "youtube-account-1",
              video.toString(),
              "a".repeat(64),
              "Title",
              "",
              List.of(),
              false,
              Map.of("privacy_level", "private"));
      PublishResult result = client.publish(privateCommand);

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @ParameterizedTest
  @ValueSource(strings = {"public", "unlisted"})
  void rejectsPublicPrivacyOptionsWhenCommandIsPrivate(String privacy) throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));

      PublishResult result =
          client.publish(command(video, "Title", "", List.of(), Map.of("privacy_level", privacy)));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void rejectsConflictingPrivacyAliasesBeforeProviderCalls() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));

      PublishResult result =
          client.publish(
              command(
                  video,
                  "Title",
                  "",
                  List.of(),
                  Map.of("privacy_level", "private", "privacy_status", "public")));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void resumesFromPartial308Acknowledgement() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4, 5, 6});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      expectInit(server, UPLOAD);
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-3/6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {1, 2, 3, 4}))
          .andRespond(
              withStatus(HttpStatusCode.valueOf(308)).header(HttpHeaders.RANGE, "bytes=0-1"));
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 2-5/6"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .bytes(new byte[] {3, 4, 5, 6}))
          .andRespond(withSuccess("{\"id\":\"video-partial\"}", MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      assertThat(result.providerVideoId()).isEqualTo("video-partial");
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @ParameterizedTest
  @ValueSource(strings = {"", "bytes=bad", "bytes=2-8", "bytes=0-99"})
  void doesNotAdvanceOnInvalid308Acknowledgement(String range) throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4, 5, 6});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      expectInit(server, UPLOAD);
      var response = withStatus(HttpStatusCode.valueOf(308));
      if (!range.isEmpty()) {
        response = response.header(HttpHeaders.RANGE, range);
      }
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-3/6"))
          .andRespond(response);

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @ParameterizedTest
  @ValueSource(strings = {"not#shortsfoo", "#shorts2024", "#shorts_foo"})
  void appendsShortsWhenCaptionContainsOnlyAnEmbeddedSubstring(String caption) throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .string(
                      Matchers.containsString("\"description\":\"" + caption + "\\n\\n#Shorts\"")))
          .andRespond(withStatus(HttpStatus.OK).header("Location", UPLOAD));
      server
          .expect(requestTo(UPLOAD))
          .andRespond(withSuccess("{\"id\":\"video-shorts\"}", MediaType.APPLICATION_JSON));

      PublishResult result = client.publish(command(video, "Title", caption, List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void preservesPunctuationDelimitedShortsTokenWithoutAppendingAnother() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      server
          .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
          .andExpect(
              org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                  .string(Matchers.containsString("\"description\":\"#Shorts!\"")))
          .andRespond(withStatus(HttpStatus.OK).header("Location", UPLOAD));
      server
          .expect(requestTo(UPLOAD))
          .andRespond(
              withSuccess("{\"id\":\"video-shorts-punctuation\"}", MediaType.APPLICATION_JSON));

      PublishResult result =
          client.publish(command(video, "Title", "#Shorts!", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @ParameterizedTest
  @ValueSource(ints = {400, 503})
  void mapsNonFinalChunkFailureWithoutSendingLaterChunks(int status) throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4, 5, 6});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      expectInit(server, UPLOAD);
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-3/6"))
          .andRespond(withStatus(HttpStatusCode.valueOf(status)));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isNotEqualTo(PublishStatus.COMPLETED);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void mapsChunkTimeoutToReconciliationWithoutSendingLaterChunks() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1, 2, 3, 4, 5, 6});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubeDataClient client = client(builder, properties(ACCESS_TOKEN, "", 4, 100));
      expectInit(server, UPLOAD);
      server
          .expect(requestTo(UPLOAD))
          .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-3/6"))
          .andRespond(withException(new IOException("upload read timed out")));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
      assertThat(result.reconciliationRequired()).isTrue();
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  @Test
  void mapsRefreshFailureWithoutInitializingUpload() throws Exception {
    Path video = Files.createTempFile("youtube", ".mp4");
    Files.write(video, new byte[] {1});
    try {
      RestClient.Builder builder = RestClient.builder();
      MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
      YouTubePublisherProperties properties =
          properties("", REFRESH_TOKEN, 4, 100, "client-id", "client-secret");
      YouTubeDataClient client = client(builder, properties);
      server
          .expect(requestTo(TOKEN_API))
          .andRespond(
              withStatus(HttpStatus.BAD_REQUEST)
                  .contentType(MediaType.APPLICATION_JSON)
                  .body(
                      "{\"error\":\"invalid_grant\",\"error_description\":\""
                          + REFRESH_TOKEN
                          + "\"}"));

      PublishResult result = client.publish(command(video, "Title", "", List.of(), Map.of()));

      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.AUTHENTICATION.wireValue());
      assertThat(result.message()).doesNotContain(REFRESH_TOKEN);
      server.verify();
    } finally {
      Files.deleteIfExists(video);
    }
  }

  private YouTubeDataClient client(
      RestClient.Builder builder, YouTubePublisherProperties properties) {
    YouTubeCredentialService credentials =
        new YouTubeCredentialService(builder, OBJECT_MAPPER, properties);
    return new YouTubeDataClient(builder, OBJECT_MAPPER, properties, credentials);
  }

  private void expectInit(MockRestServiceServer server, String uploadUrl) {
    server
        .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
        .andRespond(withStatus(HttpStatus.OK).header("Location", uploadUrl));
  }

  private void expectOneChunkUpload(
      MockRestServiceServer server, String token, String videoId, String uploadUrl) {
    server
        .expect(requestTo(UPLOAD_API + "/videos?uploadType=resumable&part=snippet,status"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + token))
        .andRespond(withStatus(HttpStatus.OK).header("Location", uploadUrl));
    server
        .expect(requestTo(uploadUrl))
        .andExpect(method(HttpMethod.PUT))
        .andExpect(header(HttpHeaders.CONTENT_RANGE, "bytes 0-0/1"))
        .andRespond(withSuccess("{\"id\":\"" + videoId + "\"}", MediaType.APPLICATION_JSON));
  }

  private PublishCommand command(
      Path asset,
      String title,
      String caption,
      List<String> hashtags,
      Map<String, String> options) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "youtube-idempotency-1",
        "youtube-account-1",
        asset.toString(),
        "a".repeat(64),
        title,
        caption,
        hashtags,
        true,
        options);
  }

  private YouTubePublisherProperties properties(
      String accessToken, String refreshToken, int chunkSize, long maxFileSize) {
    return properties(accessToken, refreshToken, chunkSize, maxFileSize, "", "");
  }

  private YouTubePublisherProperties properties(
      String accessToken,
      String refreshToken,
      int chunkSize,
      long maxFileSize,
      String clientId,
      String clientSecret) {
    return new YouTubePublisherProperties(
        true,
        true,
        false,
        "internal-secret",
        clientId,
        clientSecret,
        accessToken,
        refreshToken,
        TOKEN_API,
        API,
        UPLOAD_API,
        chunkSize,
        maxFileSize,
        Duration.ofSeconds(2),
        Duration.ofSeconds(2),
        1,
        "22",
        "public",
        null,
        "youtube-account-1");
  }
}
