package com.pompom.metapublisher;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.pompom.metapublisher.api.MetaPublisherController;
import com.pompom.metapublisher.facebook.FacebookReelsClient;
import com.pompom.metapublisher.instagram.InstagramReelsClient;
import com.pompom.metapublisher.security.MetaWriteCapabilityGuard;
import com.pompom.metapublisher.service.MetaPublishService;
import com.pompom.metapublisher.storage.PublicMediaStorage;
import com.sun.net.httpserver.HttpServer;
import java.net.InetSocketAddress;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;
import org.springframework.web.context.WebApplicationContext;

@SpringBootTest(
    classes = MetaPublisherApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:meta;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=none",
      "spring.flyway.enabled=false",
      "publisher.support.flyway.enabled=false",
      "pompom.meta.write-enabled=false",
      "pompom.meta.publish-enabled=false",
      "pompom.meta.request-timeout=50ms",
      "pompom.meta.upload-timeout=50ms"
    })
class MetaPublisherApplicationTest {

  private static final String RUPLOAD = "https://rupload.example/video-upload";

  @Autowired private ApplicationContext applicationContext;
  @Autowired private WebApplicationContext webApplicationContext;

  @Test
  void bootsWithPublisherSupportAndFailClosedMetaBeans() {
    assertThat(applicationContext.getBean(MetaPublisherController.class)).isNotNull();
    assertThat(applicationContext.getBean(MetaPublishService.class)).isNotNull();
    assertThat(applicationContext.getBean(FacebookReelsClient.class)).isNotNull();
    assertThat(applicationContext.getBean(InstagramReelsClient.class)).isNotNull();
    assertThat(applicationContext.getBean(PublicMediaStorage.class)).isNotNull();
    assertThat(applicationContext.getBean(MetaWriteCapabilityGuard.class)).isNotNull();
  }

  @Test
  void productionRestClientFactoryBoundsGraphAndUploadTraffic() throws Exception {
    HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext(
        "/",
        exchange -> {
          try {
            Thread.sleep(200);
          } catch (InterruptedException failure) {
            Thread.currentThread().interrupt();
          }
          exchange.sendResponseHeaders(200, 0);
          exchange.getResponseBody().close();
        });
    server.start();
    try {
      RestClient client =
          applicationContext
              .getBean(RestClient.Builder.class)
              .baseUrl("http://127.0.0.1:" + server.getAddress().getPort())
              .build();

      assertThatThrownBy(() -> client.get().uri("/v26.0/probe").retrieve().toBodilessEntity())
          .isInstanceOf(RestClientException.class);
      assertThatThrownBy(
              () ->
                  client
                      .post()
                      .uri("/video-upload/v26.0/probe")
                      .body("video")
                      .retrieve()
                      .toBodilessEntity())
          .isInstanceOf(RestClientException.class);
    } finally {
      server.stop(0);
    }
  }

  @Test
  void rejectsUnsafeGraphPathSegmentsAndNonHttpsEndpoints() {
    assertThatThrownBy(() -> MetaClientSupport.pathSegment("providerId", "video/1"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> MetaClientSupport.pathSegment("providerId", "video?1"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> MetaClientSupport.pathSegment("providerId", "."))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(() -> MetaClientSupport.pathSegment("providerId", ".."))
        .isInstanceOf(IllegalArgumentException.class);
    assertThatThrownBy(
            () -> MetaClientSupport.requireHttpsEndpoint("graphBaseUrl", "http://graph.example"))
        .isInstanceOf(IllegalArgumentException.class);
    assertThat(MetaClientSupport.pathSegment("providerId", "video-1")).isEqualTo("video-1");
    assertThat(MetaClientSupport.pathSegment("providerId", "video.1")).isEqualTo("video.1");
  }

  @Test
  void rejectsRawAndEncodedDotSegmentsInRuploadPaths() {
    for (String unsafePath : List.of("/video-upload/../evil", "/video-upload/./session")) {
      assertThatThrownBy(
              () ->
                  MetaClientSupport.requireSafeUploadUrl(
                      "facebookUploadUrl", "https://rupload.example" + unsafePath, RUPLOAD))
          .isInstanceOf(IllegalArgumentException.class);
    }
    for (String encodedPath : List.of("/video-upload/%2e%2e/evil", "/video-upload/%2E/session")) {
      assertThatThrownBy(
              () ->
                  MetaClientSupport.requireSafeUploadUrl(
                      "facebookUploadUrl", "https://rupload.example" + encodedPath, RUPLOAD))
          .isInstanceOf(IllegalArgumentException.class);
    }
    for (String unsafeBase : List.of("/video-upload/../evil", "/video-upload/%2e%2e/evil")) {
      assertThatThrownBy(
              () ->
                  MetaClientSupport.requireHttpsEndpoint(
                      "ruploadBaseUrl", "https://rupload.example" + unsafeBase))
          .isInstanceOf(IllegalArgumentException.class);
    }

    String safeSignedUrl = RUPLOAD + "/session-1?X-Amz-Signature=abc";
    assertThat(MetaClientSupport.requireSafeUploadUrl("facebookUploadUrl", safeSignedUrl, RUPLOAD))
        .isEqualTo(safeSignedUrl);
  }

  @Test
  void webLayerDeserializesSharedCommandAndRejectsUnauthenticatedCaller() throws Exception {
    MockMvc mockMvc = MockMvcBuilders.webAppContextSetup(webApplicationContext).build();
    mockMvc
        .perform(
            post("/internal/v1/publish")
                .header("X-Publisher-Capability", "facebook_reels")
                .header("X-Meta-Publish-Enabled", "true")
                .contentType("application/json")
                .content(
                    """
                    {
                      "publicationJobId":"11111111-1111-1111-1111-111111111111",
                      "publicationAttemptId":"22222222-2222-2222-2222-222222222222",
                      "idempotencyKey":"context-test",
                      "platformAccountId":"page-1",
                      "assetReference":"https://cdn.example/video.mp4",
                      "assetSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                      "hashtags":[],
                      "isPrivate":false,
                      "providerOptions":{}
                    }
                    """))
        .andExpect(status().isUnauthorized());
  }
}
