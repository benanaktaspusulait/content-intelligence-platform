package com.pompom.metapublisher;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.metapublisher.api.MetaPublisherController;
import com.pompom.metapublisher.facebook.FacebookReelsClient;
import com.pompom.metapublisher.instagram.InstagramReelsClient;
import com.pompom.metapublisher.security.MetaWriteCapabilityGuard;
import com.pompom.metapublisher.service.MetaPublishService;
import com.pompom.metapublisher.storage.PublicMediaStorage;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;

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
      "pompom.meta.publish-enabled=false"
    })
class MetaPublisherApplicationTest {

  @Autowired private ApplicationContext applicationContext;

  @Test
  void bootsWithPublisherSupportAndFailClosedMetaBeans() {
    assertThat(applicationContext.getBean(MetaPublisherController.class)).isNotNull();
    assertThat(applicationContext.getBean(MetaPublishService.class)).isNotNull();
    assertThat(applicationContext.getBean(FacebookReelsClient.class)).isNotNull();
    assertThat(applicationContext.getBean(InstagramReelsClient.class)).isNotNull();
    assertThat(applicationContext.getBean(PublicMediaStorage.class)).isNotNull();
    assertThat(applicationContext.getBean(MetaWriteCapabilityGuard.class)).isNotNull();
  }
}
