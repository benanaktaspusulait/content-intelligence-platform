package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class MetaConnectionPersistenceTest {
  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add("pompom.security.encryption.key", () -> "integration-test-encryption-key");
  }

  @Autowired MetaConnectionRepository repository;

  @Test
  void roundTripsEncryptedTokenMaterialAndJsonCapabilityStateThroughPostgres() {
    MetaTokenEncryptionService encryption =
        new MetaTokenEncryptionService("integration-test-encryption-key");
    MetaConnectionEntity entity =
        MetaConnectionEntity.connected(
            "owner-1",
            new MetaProviderAdapter.AuthorizationResult(
                "meta-user-1",
                "page-1",
                "instagram-1",
                "PROFESSIONAL",
                "user-secret",
                "page-secret",
                "refresh-secret",
                Set.of("pages_show_list", "pages_read_engagement", "instagram_basic"),
                Instant.parse("2026-10-01T12:00:00Z"),
                Instant.parse("2026-10-01T13:00:00Z"),
                true,
                true,
                null),
            encryption,
            Map.of(
                MetaCapability.META_FACEBOOK_ANALYTICS_READ, MetaCapabilityStatus.SUPPORTED,
                MetaCapability.META_INSTAGRAM_PUBLISH, MetaCapabilityStatus.MISSING_PERMISSION));

    repository.saveAndFlush(entity);

    MetaConnectionEntity reloaded = repository.findById(entity.getId()).orElseThrow();

    assertThat(reloaded.getOwnerKey()).isEqualTo("owner-1");
    assertThat(reloaded.getFacebookPageId()).isEqualTo("page-1");
    assertThat(reloaded.getInstagramAccountId()).isEqualTo("instagram-1");
    assertThat(reloaded.getGrantedScopes())
        .containsExactlyInAnyOrder("pages_show_list", "pages_read_engagement", "instagram_basic");
    assertThat(reloaded.getCapabilities())
        .containsEntry(
            MetaCapability.META_FACEBOOK_ANALYTICS_READ, MetaCapabilityStatus.SUPPORTED)
        .containsEntry(
            MetaCapability.META_INSTAGRAM_PUBLISH, MetaCapabilityStatus.MISSING_PERMISSION);
    assertThat(reloaded.getEncryptedUserAccessToken()).isNotEqualTo("user-secret");
    assertThat(reloaded.getEncryptedPageAccessToken()).isNotEqualTo("page-secret");
    assertThat(reloaded.getEncryptedRefreshToken()).isNotEqualTo("refresh-secret");
    assertThat(reloaded.decryptTokens(encryption).userAccessToken()).isEqualTo("user-secret");
    assertThat(reloaded.decryptTokens(encryption).pageAccessToken()).isEqualTo("page-secret");
    assertThat(reloaded.decryptTokens(encryption).refreshToken()).isEqualTo("refresh-secret");
  }
}
