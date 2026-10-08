package com.pompom.youtubepublisher;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.pompom.youtubepublisher.api.YouTubePublisherController;
import com.pompom.youtubepublisher.client.YouTubeDataClient;
import com.pompom.youtubepublisher.oauth.YouTubeCredentialService;
import com.pompom.youtubepublisher.security.YouTubeWriteCapabilityGuard;
import com.pompom.youtubepublisher.service.YouTubePublishService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

@SpringBootTest(
    classes = YouTubePublisherApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:youtube;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=none",
      "spring.flyway.enabled=false",
      "publisher.support.flyway.enabled=false",
      "pompom.youtube.write-enabled=false",
      "pompom.youtube.publish-enabled=false",
      "pompom.youtube.dry-run=true",
      "pompom.youtube.access-token=access-token",
      "pompom.youtube.platform-account-id=account-1",
      "pompom.youtube.request-timeout=50ms",
      "pompom.youtube.upload-timeout=100ms"
    })
class YouTubePublisherApplicationTest {

  @Autowired private ApplicationContext applicationContext;
  @Autowired private WebApplicationContext webApplicationContext;

  @Test
  void wiresTheInternalControllerServiceClientCredentialsAndGuard() {
    assertThat(applicationContext.getBean(YouTubePublisherApplication.class)).isNotNull();
    assertThat(applicationContext.getBean(YouTubePublisherController.class)).isNotNull();
    assertThat(applicationContext.getBean(YouTubePublishService.class)).isNotNull();
    assertThat(applicationContext.getBean(YouTubeDataClient.class)).isNotNull();
    assertThat(applicationContext.getBean(YouTubeCredentialService.class)).isNotNull();
    assertThat(applicationContext.getBean(YouTubeWriteCapabilityGuard.class)).isNotNull();
  }

  @Test
  void rejectsUnauthenticatedInternalPublishBeforeProviderAccess() throws Exception {
    MockMvc mockMvc = MockMvcBuilders.webAppContextSetup(webApplicationContext).build();

    mockMvc
        .perform(
            post("/internal/v1/publish")
                .header("X-Publisher-Capability", "youtube_shorts")
                .header("X-YouTube-Publish-Enabled", "true")
                .contentType("application/json")
                .content(
                    """
                    {
                      "publicationJobId":"11111111-1111-1111-1111-111111111111",
                      "publicationAttemptId":"22222222-2222-2222-2222-222222222222",
                      "idempotencyKey":"context-test",
                      "platformAccountId":"account-1",
                      "assetReference":"/tmp/video.mp4",
                      "assetSha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                      "title":"YouTube title",
                      "caption":"caption",
                      "hashtags":[],
                      "isPrivate":false,
                      "providerOptions":{}
                    }
                    """))
        .andExpect(status().isUnauthorized());
  }
}
