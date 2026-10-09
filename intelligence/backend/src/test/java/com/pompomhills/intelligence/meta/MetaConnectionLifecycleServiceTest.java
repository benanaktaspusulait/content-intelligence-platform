package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.web.client.RestClient;

class MetaConnectionLifecycleServiceTest {
  private static final Instant ISSUED_AT = Instant.parse("2026-10-01T12:00:00Z");
  private static final Instant EXPIRES_AT = Instant.parse("2026-10-01T13:00:00Z");

  private MetaConnectionRepository repository;
  private MetaProviderAdapter provider;
  private MetaConnectionLifecycleService service;

  @BeforeEach
  void setUp() {
    repository = org.mockito.Mockito.mock(MetaConnectionRepository.class);
    provider = org.mockito.Mockito.mock(MetaProviderAdapter.class);
    service =
        new MetaConnectionLifecycleService(
            provider,
            repository,
            new MetaTokenEncryptionService("test-encryption-key"),
            properties(),
            Clock.fixed(ISSUED_AT, ZoneOffset.UTC));
  }

  @Test
  void persistsEncryptedTokensAndCapabilityStateWithoutReturningSecrets() throws Exception {
    when(repository.findByOwnerKeyAndProviderUserIdAndFacebookPageIdAndInstagramAccountId(
            "owner-1", "meta-user-1", "page-1", "instagram-1"))
        .thenReturn(Optional.empty());
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(
            invocation -> {
              MetaConnectionEntity savedEntity = invocation.getArgument(0);
              if (savedEntity.getId() == null) {
                savedEntity.setId(UUID.randomUUID());
              }
              return savedEntity;
            });
    when(provider.authorize("authorization-code"))
        .thenReturn(
            new MetaProviderAdapter.AuthorizationResult(
                "meta-user-1",
                "page-1",
                "instagram-1",
                "PROFESSIONAL",
                "user-secret",
                "page-secret",
                "refresh-secret",
                Set.of(
                    "pages_show_list",
                    "pages_read_engagement",
                    "instagram_basic",
                    "instagram_manage_insights"),
                ISSUED_AT,
                EXPIRES_AT,
                true,
                true,
                null));

    MetaConnectionResponse response =
        service.completeAuthorization("authorization-code", "single-use-state");

    ArgumentCaptor<MetaConnectionEntity> captor =
        ArgumentCaptor.forClass(MetaConnectionEntity.class);
    verify(repository).save(captor.capture());
    MetaConnectionEntity saved = captor.getValue();

    assertThat(saved.getId()).isNotNull();
    assertThat(saved.getOwnerKey()).isEqualTo("owner-1");
    assertThat(saved.getProviderUserId()).isEqualTo("meta-user-1");
    assertThat(saved.getFacebookPageId()).isEqualTo("page-1");
    assertThat(saved.getInstagramAccountId()).isEqualTo("instagram-1");
    assertThat(saved.getGrantedScopes())
        .containsExactlyInAnyOrder(
            "pages_show_list",
            "pages_read_engagement",
            "instagram_basic",
            "instagram_manage_insights");
    assertThat(saved.getIssuedAt()).isEqualTo(ISSUED_AT);
    assertThat(saved.getExpiresAt()).isEqualTo(EXPIRES_AT);
    assertThat(saved.getLastValidatedAt()).isEqualTo(ISSUED_AT);
    assertThat(saved.getEncryptedUserAccessToken()).isNotEqualTo("user-secret");
    assertThat(saved.getEncryptedPageAccessToken()).isNotEqualTo("page-secret");
    assertThat(saved.getEncryptedRefreshToken()).isNotEqualTo("refresh-secret");
    assertThat(saved.getCapabilities().get(MetaCapability.META_FACEBOOK_ANALYTICS_READ))
        .isEqualTo(MetaCapabilityStatus.SUPPORTED);
    assertThat(saved.getCapabilities().get(MetaCapability.META_FACEBOOK_COMMENT_REPLY))
        .isEqualTo(MetaCapabilityStatus.MISSING_PERMISSION);

    assertThat(response.connectionId()).isEqualTo(saved.getId());
    assertThat(response.ownerIdentity()).isEqualTo("owner-1");
    assertThat(response.expiresAt()).isEqualTo(EXPIRES_AT);
    assertThat(response.capabilities().get(MetaCapability.META_INSTAGRAM_PUBLISH))
        .isEqualTo(MetaCapabilityStatus.MISSING_PERMISSION);

    String serialized =
        new ObjectMapper().findAndRegisterModules().writeValueAsString(response);
    assertThat(serialized).doesNotContain("user-secret", "page-secret", "refresh-secret");
    assertThat(serialized).doesNotContain("accessToken", "refreshToken", "encrypted");
  }

  @Test
  void marksExpiredConnectionWhenProviderDoesNotSupportRefresh() {
    MetaConnectionEntity entity = connectedEntity();
    entity.setExpiresAt(ISSUED_AT.minusSeconds(1));
    when(repository.findByIdAndOwnerKey(entity.getId(), "owner-1"))
        .thenReturn(Optional.of(entity));
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(
            invocation -> {
              MetaConnectionEntity savedEntity = invocation.getArgument(0);
              if (savedEntity.getId() == null) {
                savedEntity.setId(UUID.randomUUID());
              }
              return savedEntity;
            });

    MetaConnectionResponse response = service.refreshIfNeeded(entity.getId());

    assertThat(response.connectionStatus()).isEqualTo(MetaConnectionStatus.EXPIRED);
    assertThat(response.failureReason()).contains("refresh");
    assertThat(entity.getStatus()).isEqualTo(MetaConnectionStatus.EXPIRED);
    verify(provider, never()).refresh(any(MetaProviderAdapter.StoredTokens.class));
  }

  @Test
  void refreshesConnectionBeforeExpiryWindow() {
    MetaConnectionEntity entity = connectedEntity();
    entity.setExpiresAt(ISSUED_AT.plusSeconds(120));
    when(repository.findByIdAndOwnerKey(entity.getId(), "owner-1"))
        .thenReturn(Optional.of(entity));
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));
    when(provider.supportsRefresh()).thenReturn(true);
    when(provider.refresh(any(MetaProviderAdapter.StoredTokens.class)))
        .thenReturn(
            new MetaProviderAdapter.TokenRefreshResult(
                "refreshed-user",
                "refreshed-page",
                "refreshed-refresh",
                ISSUED_AT,
                ISSUED_AT.plusSeconds(3600)));

    MetaConnectionResponse response = service.refreshIfNeeded(entity.getId());

    assertThat(response.expiresAt()).isEqualTo(ISSUED_AT.plusSeconds(3600));
    assertThat(entity.decryptTokens(new MetaTokenEncryptionService("test-encryption-key")).pageAccessToken())
        .isEqualTo("refreshed-page");
    verify(provider).refresh(any(MetaProviderAdapter.StoredTokens.class));
  }

  @Test
  void disconnectsAndClearsEncryptedMaterialWithoutPretendingToRevoke() {
    MetaConnectionEntity entity = connectedEntity();
    when(repository.findByIdAndOwnerKey(entity.getId(), "owner-1"))
        .thenReturn(Optional.of(entity));
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(
            invocation -> {
              MetaConnectionEntity savedEntity = invocation.getArgument(0);
              if (savedEntity.getId() == null) {
                savedEntity.setId(UUID.randomUUID());
              }
              return savedEntity;
            });

    MetaConnectionResponse response = service.disconnect(entity.getId());

    assertThat(response.connectionStatus()).isEqualTo(MetaConnectionStatus.REVOKED);
    assertThat(entity.getStatus()).isEqualTo(MetaConnectionStatus.REVOKED);
    assertThat(entity.getEncryptedUserAccessToken()).isNull();
    assertThat(entity.getEncryptedPageAccessToken()).isNull();
    assertThat(entity.getEncryptedRefreshToken()).isNull();
    verify(provider, never()).revoke(any(MetaProviderAdapter.StoredTokens.class));
  }

  @Test
  void supportedRevokeFailureClearsTokensAndMakesGraphReadsFailClosed() {
    MetaConnectionEntity entity = connectedEntity();
    when(repository.findByIdAndOwnerKey(entity.getId(), "owner-1"))
        .thenReturn(Optional.of(entity));
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(
            invocation -> {
              MetaConnectionEntity savedEntity = invocation.getArgument(0);
              if (savedEntity.getId() == null) {
                savedEntity.setId(UUID.randomUUID());
              }
              return savedEntity;
            });
    when(provider.supportsRevoke()).thenReturn(true);
    doThrow(new IllegalStateException("provider access_token=remote-secret"))
        .when(provider)
        .revoke(any(MetaProviderAdapter.StoredTokens.class));

    MetaConnectionResponse response = service.disconnect(entity.getId());

    assertThat(response.connectionStatus()).isEqualTo(MetaConnectionStatus.REVOKED);
    assertThat(response.connected()).isFalse();
    assertThat(response.failureReason())
        .isEqualTo("Meta token revocation could not be confirmed.");
    assertThat(entity.getStatus()).isEqualTo(MetaConnectionStatus.REVOKED);
    assertThat(entity.getEncryptedUserAccessToken()).isNull();
    assertThat(entity.getEncryptedPageAccessToken()).isNull();
    assertThat(entity.getEncryptedRefreshToken()).isNull();
    assertThat(entity.getCapabilities()).doesNotContainValue(MetaCapabilityStatus.SUPPORTED);

    when(repository.findTopByOwnerKeyOrderByUpdatedAtDesc("owner-1"))
        .thenReturn(Optional.of(entity));
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            RestClient.builder().baseUrl("https://graph.facebook.com").build(),
            new ObjectMapper(),
            properties(),
            new MetaOAuthTokenStore(),
            repository,
            new MetaTokenEncryptionService("test-encryption-key"),
            Clock.fixed(ISSUED_AT, ZoneOffset.UTC));

    assertThat(client.hasEffectiveAccessToken()).isFalse();
    assertThat(client.hasEffectivePageTarget()).isFalse();
    assertThat(client.hasEffectiveInstagramTarget()).isFalse();
  }

  @Test
  void sanitizesProviderValidationReasonBeforePersistenceAndResponse() {
    String providerReason =
        "provider rejected access_token=user-secret token=raw-token appsecret_proof=proof-secret "
            + "Bearer bearer-secret\n"
            + "x".repeat(400);
    when(repository.findByOwnerKeyAndProviderUserIdAndFacebookPageIdAndInstagramAccountId(
            "owner-1", "meta-user-1", "page-1", "instagram-1"))
        .thenReturn(Optional.empty());
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(
            invocation -> {
              MetaConnectionEntity savedEntity = invocation.getArgument(0);
              if (savedEntity.getId() == null) {
                savedEntity.setId(UUID.randomUUID());
              }
              return savedEntity;
            });
    when(provider.authorize("authorization-code"))
        .thenReturn(authorizationResult(providerReason));

    MetaConnectionResponse response =
        service.completeAuthorization("authorization-code", "single-use-state");

    ArgumentCaptor<MetaConnectionEntity> captor =
        ArgumentCaptor.forClass(MetaConnectionEntity.class);
    verify(repository).save(captor.capture());
    String persistedReason = captor.getValue().getFailureReason();

    assertThat(persistedReason).hasSizeLessThanOrEqualTo(300);
    assertThat(persistedReason).doesNotContain("user-secret", "raw-token", "proof-secret", "bearer-secret");
    assertThat(persistedReason).doesNotContain("\n", "\r", "\t");
    assertThat(persistedReason).contains("[REDACTED]");
    assertThat(response.failureReason()).isEqualTo(persistedReason);
    assertThat(response.message()).isEqualTo(persistedReason);
  }

  @Test
  void providerValidationFailureDowngradesCapabilityAdmission() {
    when(repository.findByOwnerKeyAndProviderUserIdAndFacebookPageIdAndInstagramAccountId(
            "owner-1", "meta-user-1", "page-1", "instagram-1"))
        .thenReturn(Optional.empty());
    when(repository.save(any(MetaConnectionEntity.class)))
        .thenAnswer(
            invocation -> {
              MetaConnectionEntity savedEntity = invocation.getArgument(0);
              if (savedEntity.getId() == null) {
                savedEntity.setId(UUID.randomUUID());
              }
              return savedEntity;
            });
    when(provider.authorize("authorization-code"))
        .thenReturn(authorizationResult("Provider validation failed."));

    MetaConnectionResponse response =
        service.completeAuthorization("authorization-code", "single-use-state");

    assertThat(response.connectionStatus()).isEqualTo(MetaConnectionStatus.DEGRADED);
    assertThat(response.connected()).isFalse();
    assertThat(response.capabilities()).doesNotContainValue(MetaCapabilityStatus.SUPPORTED);
    assertThat(response.capabilities().get(MetaCapability.META_FACEBOOK_ANALYTICS_READ))
        .isEqualTo(MetaCapabilityStatus.UNKNOWN);
    assertThat(response.capabilities().get(MetaCapability.META_INSTAGRAM_ANALYTICS_READ))
        .isEqualTo(MetaCapabilityStatus.UNKNOWN);
  }

  private MetaProviderAdapter.AuthorizationResult authorizationResult(String validationReason) {
    return new MetaProviderAdapter.AuthorizationResult(
        "meta-user-1",
        "page-1",
        "instagram-1",
        "PROFESSIONAL",
        "user-secret",
        "page-secret",
        "refresh-secret",
        Set.of(
            "pages_show_list",
            "pages_read_engagement",
            "instagram_basic",
            "instagram_manage_insights"),
        ISSUED_AT,
        EXPIRES_AT,
        true,
        true,
        validationReason);
  }

  private MetaConnectionEntity connectedEntity() {
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
                Set.of("pages_read_engagement", "instagram_basic", "instagram_manage_insights"),
                ISSUED_AT,
                EXPIRES_AT,
                true,
                true,
                null),
            new MetaTokenEncryptionService("test-encryption-key"),
            java.util.Map.of());
    entity.setId(UUID.randomUUID());
    return entity;
  }

  private MetaReadProperties properties() {
    return new MetaReadProperties(
        true,
        "v26.0",
        "page-1",
        "instagram-1",
        "",
        "",
        Duration.ofSeconds(5),
        Duration.ofSeconds(15),
        false,
        false,
        "owner-1");
  }
}
