package com.pompom.metapublisher.instagram;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.metapublisher.MetaPublisherProperties;
import com.pompom.metapublisher.storage.ConfiguredPublicMediaStorage;
import com.pompom.metapublisher.storage.PublicMediaStorage;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.hamcrest.Matchers;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class InstagramReelsClientTest {

  private static final String TOKEN = "instagram-write-token";
  private static final String GRAPH = "https://graph.instagram.test";
  private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

  @Test
  void createsReelsContainerPollsAndPublishesWithPermalink() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    InstagramReelsClient client =
        new InstagramReelsClient(
            builder,
            OBJECT_MAPPER,
            properties(2, Duration.ofSeconds(1)),
            new ConfiguredPublicMediaStorage(properties(2, Duration.ofSeconds(1))));

    server
        .expect(requestTo(GRAPH + "/v26.0/ig-1/media"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andExpect(
            org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                .string(
                    Matchers.allOf(
                        Matchers.containsString("media_type=REELS"),
                        Matchers.containsString("video_url=https%3A%2F%2Fcdn.example%2Freel.mp4"),
                        Matchers.containsString("caption=caption"),
                        Matchers.containsString("%23reels"),
                        Matchers.containsString("share_to_feed=true"),
                        Matchers.not(Matchers.containsString("access_token")))))
        .andRespond(withSuccess("{\"id\":\"container-1\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/container-1?fields=status_code,status"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andRespond(
            withSuccess(
                "{\"status_code\":\"IN_PROGRESS\",\"status\":\"working\"}",
                MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/container-1?fields=status_code,status"))
        .andRespond(withSuccess("{\"status_code\":\"FINISHED\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/ig-1/media_publish"))
        .andExpect(method(HttpMethod.POST))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andExpect(
            org.springframework.test.web.client.match.MockRestRequestMatchers.content()
                .string(Matchers.containsString("creation_id=container-1")))
        .andRespond(withSuccess("{\"id\":\"media-1\"}", MediaType.APPLICATION_JSON));
    server
        .expect(requestTo(GRAPH + "/v26.0/media-1?fields=permalink"))
        .andRespond(
            withSuccess(
                "{\"id\":\"media-1\",\"permalink\":\"https://instagram.example/p/media-1\"}",
                MediaType.APPLICATION_JSON));

    PublishResult result =
        client.publish(command("https://cdn.example/reel.mp4", "caption", List.of("reels")));

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerPostId()).isEqualTo("media-1");
    assertThat(result.providerVideoId()).isNull();
    assertThat(result.permalink()).isEqualTo("https://instagram.example/p/media-1");
    server.verify();
  }

  @Test
  void rejectsNonHttpsMediaWithoutImplicitLocalExposure() {
    InstagramReelsClient client =
        new InstagramReelsClient(
            RestClient.builder(),
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));

    PublishResult result = client.publish(command("/local/video.mp4", "caption", List.of()));

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.UNSUPPORTED.wireValue());
    assertThat(result.message()).contains("HTTPS");
  }

  @Test
  void rejectsHttpUrlEvenWhenItLooksPublic() {
    InstagramReelsClient client =
        new InstagramReelsClient(
            RestClient.builder(),
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));

    PublishResult result =
        client.publish(command("http://cdn.example/reel.mp4", "caption", List.of()));

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.UNSUPPORTED.wireValue());
  }

  @Test
  void truncatesCaptionAtAuditedInstagramLimit() {
    assertThat(InstagramReelsClient.truncateCaption("x".repeat(2200))).hasSize(2200);
    String truncated = InstagramReelsClient.truncateCaption("x".repeat(2201));
    assertThat(truncated).hasSize(2200).endsWith("…").startsWith("x".repeat(2199));
  }

  @Test
  void mapsContainerErrorAndTimeoutToNormalizedOutcomes() {
    RestClient.Builder errorBuilder = RestClient.builder();
    MockRestServiceServer errorServer = MockRestServiceServer.bindTo(errorBuilder).build();
    InstagramReelsClient errorClient =
        new InstagramReelsClient(
            errorBuilder,
            OBJECT_MAPPER,
            properties(1, Duration.ofSeconds(1)),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ofSeconds(1))));
    errorServer
        .expect(requestTo(GRAPH + "/v26.0/ig-1/media"))
        .andRespond(withSuccess("{\"id\":\"container-error\"}", MediaType.APPLICATION_JSON));
    errorServer
        .expect(requestTo(GRAPH + "/v26.0/container-error?fields=status_code,status"))
        .andRespond(
            withSuccess(
                "{\"status_code\":\"ERROR\",\"status\":\"bad media\"}",
                MediaType.APPLICATION_JSON));

    PublishResult error =
        errorClient.publish(command("https://cdn.example/reel.mp4", "caption", List.of()));

    assertThat(error.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(error.errorClass()).isEqualTo(PublishErrorClass.PROVIDER_REJECTED.wireValue());
    errorServer.verify();

    RestClient.Builder timeoutBuilder = RestClient.builder();
    MockRestServiceServer timeoutServer = MockRestServiceServer.bindTo(timeoutBuilder).build();
    InstagramReelsClient timeoutClient =
        new InstagramReelsClient(
            timeoutBuilder,
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));
    timeoutServer
        .expect(requestTo(GRAPH + "/v26.0/ig-1/media"))
        .andRespond(withSuccess("{\"id\":\"container-timeout\"}", MediaType.APPLICATION_JSON));
    timeoutServer
        .expect(requestTo(GRAPH + "/v26.0/container-timeout?fields=status_code,status"))
        .andRespond(withSuccess("{\"status_code\":\"IN_PROGRESS\"}", MediaType.APPLICATION_JSON));

    PublishResult timeout =
        timeoutClient.publish(command("https://cdn.example/reel.mp4", "caption", List.of()));

    assertThat(timeout.status()).isEqualTo(PublishStatus.RECONCILIATION_REQUIRED);
    assertThat(timeout.reconciliationRequired()).isTrue();
    timeoutServer.verify();
  }

  @Test
  void rejectsCredentialBearingHttpsMediaUrls() {
    InstagramReelsClient client =
        new InstagramReelsClient(
            RestClient.builder(),
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));

    PublishResult result =
        client.publish(
            command("https://cdn.example/reel.mp4?access_token=secret", "caption", List.of()));

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.UNSUPPORTED.wireValue());
    assertThat(result.message()).doesNotContain("secret");
  }

  @Test
  void rejectsCredentialAliasesInHttpsMediaUrls() {
    InstagramReelsClient client =
        new InstagramReelsClient(
            RestClient.builder(),
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));

    for (String url :
        List.of(
            "https://cdn.example/reel.mp4?accessKey=secret",
            "https://cdn.example/reel.mp4?AWSAccessKeyId=secret")) {
      PublishResult result = client.publish(command(url, "caption", List.of()));
      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.UNSUPPORTED.wireValue());
      assertThat(result.message()).doesNotContain("secret");
    }
  }

  @Test
  void rejectsUserInfoAndCredentialFragmentsInHttpsMediaUrls() {
    InstagramReelsClient client =
        new InstagramReelsClient(
            RestClient.builder(),
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));

    for (String url :
        List.of(
            "https://@cdn.example/reel.mp4", "https://cdn.example/reel.mp4#access_token=secret")) {
      PublishResult result = client.publish(command(url, "caption", List.of()));
      assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
      assertThat(result.errorClass()).isEqualTo(PublishErrorClass.UNSUPPORTED.wireValue());
    }
  }

  @Test
  void reconcilesExistingMediaWithReadOnlyGraphLookup() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    InstagramReelsClient client =
        new InstagramReelsClient(
            builder,
            OBJECT_MAPPER,
            properties(1, Duration.ZERO),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ZERO)));
    server
        .expect(requestTo(GRAPH + "/v26.0/media-1?fields=id,permalink"))
        .andExpect(method(HttpMethod.GET))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer " + TOKEN))
        .andRespond(
            withSuccess(
                "{\"id\":\"media-1\",\"permalink\":\"https://instagram.example/p/media-1\"}",
                MediaType.APPLICATION_JSON));

    PublishResult result = client.reconcile("ig-1", "media-1", null);

    assertThat(result.status()).isEqualTo(PublishStatus.COMPLETED);
    assertThat(result.providerPostId()).isEqualTo("media-1");
    assertThat(result.permalink()).isEqualTo("https://instagram.example/p/media-1");
    server.verify();
  }

  @Test
  void mapsPermanentContainerFailureToTerminalProviderResult() {
    RestClient.Builder builder = RestClient.builder();
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    InstagramReelsClient client =
        new InstagramReelsClient(
            builder,
            OBJECT_MAPPER,
            properties(1, Duration.ofSeconds(1)),
            new ConfiguredPublicMediaStorage(properties(1, Duration.ofSeconds(1))));
    server
        .expect(requestTo(GRAPH + "/v26.0/ig-1/media"))
        .andRespond(
            withStatus(HttpStatus.BAD_REQUEST)
                .contentType(MediaType.APPLICATION_JSON)
                .body("{\"error\":{\"message\":\"invalid media\",\"code\":100}}"));

    PublishResult result =
        client.publish(command("https://cdn.example/reel.mp4", "caption", List.of()));

    assertThat(result.status()).isEqualTo(PublishStatus.FAILED);
    assertThat(result.errorClass()).isEqualTo(PublishErrorClass.VALIDATION.wireValue());
    assertThat(result.message()).doesNotContain(TOKEN);
    server.verify();
  }

  @Test
  void explicitTemplateStorageProducesOnlyHttpsAndTracksNoCallerUrlForCleanup() {
    MetaPublisherProperties templateProperties =
        properties(1, Duration.ZERO, "template", "https://storage.example/reels/{filename}");
    PublicMediaStorage storage = new ConfiguredPublicMediaStorage(templateProperties);
    PublishCommand command = command("/tmp/rendered.mp4", "caption", List.of());

    Optional<PublicMediaStorage.HostedMedia> hosted = storage.host(command);

    assertThat(hosted).isPresent();
    assertThat(hosted.orElseThrow().url()).isEqualTo("https://storage.example/reels/rendered.mp4");
    assertThat(hosted.orElseThrow().owned()).isFalse();
    storage.cleanup(hosted.orElseThrow().url());
  }

  @Test
  void explicitPublicDirectoryStorageCopiesAndCleansOnlyOwnedMedia() throws Exception {
    Path source = Files.createTempFile("meta-instagram-source", ".mp4");
    Path directory = Files.createTempDirectory("meta-instagram-public");
    try {
      Files.writeString(source, "video");
      MetaPublisherProperties directoryProperties =
          properties(
              1,
              Duration.ZERO,
              "public_dir",
              "",
              directory.toString(),
              "https://storage.example/reels");
      PublicMediaStorage storage = new ConfiguredPublicMediaStorage(directoryProperties);
      PublishCommand command = command(source.toString(), "caption", List.of());

      PublicMediaStorage.HostedMedia hosted = storage.host(command).orElseThrow();

      assertThat(hosted.url()).startsWith("https://storage.example/reels/");
      assertThat(hosted.owned()).isTrue();
      assertThat(Files.list(directory).findAny()).isPresent();
      storage.cleanup(hosted.url());
      assertThat(Files.list(directory).findAny()).isEmpty();
    } finally {
      Files.deleteIfExists(source);
      Files.deleteIfExists(directory);
    }
  }

  private MetaPublisherProperties properties(int maxAttempts, Duration pollTimeout) {
    return properties(maxAttempts, pollTimeout, "none", "");
  }

  private MetaPublisherProperties properties(
      int maxAttempts, Duration pollTimeout, String storageBackend, String storageTemplate) {
    return properties(maxAttempts, pollTimeout, storageBackend, storageTemplate, "", "");
  }

  private MetaPublisherProperties properties(
      int maxAttempts,
      Duration pollTimeout,
      String storageBackend,
      String storageTemplate,
      String storageDirectory,
      String storageBaseUrl) {
    return new MetaPublisherProperties(
        true,
        true,
        "internal-token",
        "v26.0",
        GRAPH,
        "https://rupload.facebook.test/video-upload",
        "",
        "",
        "ig-1",
        TOKEN,
        Duration.ofSeconds(1),
        Duration.ofSeconds(1),
        pollTimeout,
        Duration.ZERO,
        maxAttempts,
        true,
        "",
        storageBackend,
        storageDirectory,
        storageBaseUrl,
        storageTemplate,
        true);
  }

  private PublishCommand command(String assetReference, String caption, List<String> hashtags) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "instagram-command-" + UUID.randomUUID(),
        "ig-1",
        assetReference,
        "a".repeat(64),
        "title",
        caption,
        hashtags,
        false,
        Map.of());
  }
}
