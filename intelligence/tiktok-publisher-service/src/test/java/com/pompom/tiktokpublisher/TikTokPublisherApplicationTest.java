package com.pompom.tiktokpublisher;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.tiktokpublisher.api.TikTokPublisherController;
import com.pompom.tiktokpublisher.client.TikTokContentClient;
import com.pompom.tiktokpublisher.security.TikTokWriteCapabilityGuard;
import com.pompom.tiktokpublisher.service.TikTokPublishService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

@SpringBootTest(
    classes = TikTokPublisherApplication.class,
    properties = {
      "spring.datasource.url=jdbc:h2:mem:tiktok;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=none",
      "spring.flyway.enabled=false",
      "publisher.support.flyway.enabled=false",
      "pompom.tiktok.write-enabled=false",
      "pompom.tiktok.publish-enabled=false",
      "pompom.tiktok.dry-run=true",
      "pompom.tiktok.access-token=access-token",
      "pompom.tiktok.platform-account-id=account-1",
      "pompom.tiktok.request-timeout=50ms",
      "pompom.tiktok.upload-timeout=100ms"
    })
class TikTokPublisherApplicationTest {

  @Autowired private ApplicationContext applicationContext;

  @Test
  void wiresTheTikTokControllerServiceClientAndGuard() {
    assertThat(applicationContext.getBean(TikTokPublisherApplication.class)).isNotNull();
    assertThat(applicationContext.getBean(TikTokPublisherController.class)).isNotNull();
    assertThat(applicationContext.getBean(TikTokPublishService.class)).isNotNull();
    assertThat(applicationContext.getBean(TikTokContentClient.class)).isNotNull();
    assertThat(applicationContext.getBean(TikTokWriteCapabilityGuard.class)).isNotNull();
  }
}
