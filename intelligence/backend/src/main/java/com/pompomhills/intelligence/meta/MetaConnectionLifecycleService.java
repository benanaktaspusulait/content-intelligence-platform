package com.pompomhills.intelligence.meta;

import java.time.Clock;
import java.time.Instant;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Owns durable, owner-scoped Meta connection state and fail-closed capability admission. */
@Service
public class MetaConnectionLifecycleService {
  private static final String PAGES_SHOW_LIST = "pages_show_list";
  private static final String PAGES_READ_ENGAGEMENT = "pages_read_engagement";
  private static final String PAGES_READ_USER_CONTENT = "pages_read_user_content";
  private static final String PAGES_MANAGE_ENGAGEMENT = "pages_manage_engagement";
  private static final String PAGES_MANAGE_POSTS = "pages_manage_posts";
  private static final String INSTAGRAM_BASIC = "instagram_basic";
  private static final String INSTAGRAM_MANAGE_INSIGHTS = "instagram_manage_insights";
  private static final String INSTAGRAM_MANAGE_COMMENTS = "instagram_manage_comments";
  private static final String INSTAGRAM_CONTENT_PUBLISH = "instagram_content_publish";

  private final MetaProviderAdapter provider;
  private final MetaConnectionRepository repository;
  private final MetaTokenEncryptionService encryption;
  private final MetaReadProperties properties;
  private final Clock clock;

  public MetaConnectionLifecycleService(
      MetaProviderAdapter provider,
      MetaConnectionRepository repository,
      MetaTokenEncryptionService encryption,
      MetaReadProperties properties,
      Clock clock) {
    this.provider = provider;
    this.repository = repository;
    this.encryption = encryption;
    this.properties = properties;
    this.clock = clock;
  }

  public boolean isConfigured() {
    return provider.isConfigured();
  }

  public String buildAuthorizationUrl(String state) {
    return provider.buildAuthorizationUrl(state);
  }

  @Transactional
  public MetaConnectionResponse completeAuthorization(String code, String state) {
    if (code == null || code.isBlank() || state == null || state.isBlank()) {
      return failureResponse("The Meta authorization callback was incomplete.");
    }
    try {
      MetaProviderAdapter.AuthorizationResult authorization = provider.authorize(code);
      if (authorization.facebookPageId() == null || authorization.facebookPageId().isBlank()) {
        return failureResponse("Meta did not return a managed Facebook Page target.");
      }
      Map<MetaCapability, MetaCapabilityStatus> capabilities = calculateCapabilities(authorization);
      Optional<MetaConnectionEntity> existing = findExisting(authorization);
      MetaConnectionEntity entity =
          existing.orElseGet(
              () ->
                  MetaConnectionEntity.connected(
                      ownerKey(), authorization, encryption, capabilities));
      if (existing.isPresent()) {
        entity.applyAuthorization(authorization, encryption, capabilities);
      }
      entity.setStatus(connectionStatus(capabilities, authorization.expiresAt()));
      entity.setFailureReason(authorization.providerValidationReason());
      MetaConnectionEntity saved = repository.save(entity);
      return toResponse(saved);
    } catch (MetaOAuthException error) {
      return failureResponse(sanitizeFailure(error.getMessage()));
    } catch (RuntimeException error) {
      return failureResponse("The Meta authorization request could not be completed.");
    }
  }

  @Transactional(readOnly = true)
  public Optional<MetaConnectionResponse> currentConnection() {
    return repository.findTopByOwnerKeyOrderByUpdatedAtDesc(ownerKey()).map(this::toResponse);
  }

  @Transactional(readOnly = true)
  public MetaConnectionResponse getConnection() {
    return currentConnection().orElseGet(this::notConfiguredResponse);
  }

  @Transactional
  public MetaConnectionResponse disconnect(UUID connectionId) {
    Optional<MetaConnectionEntity> found = findOwned(connectionId);
    if (found.isEmpty()) {
      return failureResponse("The Meta connection was not found.");
    }
    MetaConnectionEntity entity = found.get();
    if (provider.supportsRevoke()) {
      try {
        provider.revoke(entity.decryptTokens(encryption));
      } catch (RuntimeException error) {
        entity.setStatus(MetaConnectionStatus.DEGRADED);
        entity.setFailureReason("Meta token revocation could not be confirmed.");
        repository.save(entity);
        return toResponse(entity);
      }
    }
    entity.setStatus(MetaConnectionStatus.REVOKED);
    entity.setEncryptedTokens(null, null, null);
    entity.setFailureReason(
        provider.supportsRevoke()
            ? null
            : "The current Meta provider contract does not support remote token revocation.");
    entity.setCapabilities(unknownCapabilities());
    return toResponse(repository.save(entity));
  }

  @Transactional
  public MetaConnectionResponse refreshIfNeeded(UUID connectionId) {
    Optional<MetaConnectionEntity> found = findOwned(connectionId);
    if (found.isEmpty()) {
      return failureResponse("The Meta connection was not found.");
    }
    MetaConnectionEntity entity = found.get();
    if (entity.getStatus() == MetaConnectionStatus.REVOKED) {
      return toResponse(entity);
    }
    Instant now = clock.instant();
    if (entity.getExpiresAt() != null && now.isBefore(entity.getExpiresAt())) {
      return toResponse(entity);
    }
    if (!provider.supportsRefresh()) {
      entity.setStatus(MetaConnectionStatus.EXPIRED);
      entity.setFailureReason(
          "The current Meta provider contract does not support token refresh or extension.");
      entity.setCapabilities(tokenExpiredCapabilities());
      return toResponse(repository.save(entity));
    }

    try {
      MetaProviderAdapter.TokenRefreshResult refreshed =
          provider.refresh(entity.decryptTokens(encryption));
      entity.applyRefresh(refreshed, encryption);
      Map<MetaCapability, MetaCapabilityStatus> capabilities =
          calculateCapabilities(entity.getGrantedScopes(), entity, refreshed.expiresAt());
      entity.setCapabilities(capabilities);
      entity.setStatus(connectionStatus(capabilities, refreshed.expiresAt()));
      entity.setFailureReason(null);
      return toResponse(repository.save(entity));
    } catch (RuntimeException error) {
      entity.setStatus(MetaConnectionStatus.EXPIRED);
      entity.setFailureReason("Meta token refresh could not be completed.");
      entity.setCapabilities(tokenExpiredCapabilities());
      return toResponse(repository.save(entity));
    }
  }

  private Optional<MetaConnectionEntity> findExisting(
      MetaProviderAdapter.AuthorizationResult authorization) {
    Optional<MetaConnectionEntity> exact =
        repository.findByOwnerKeyAndProviderUserIdAndFacebookPageIdAndInstagramAccountId(
            ownerKey(),
            authorization.providerUserId(),
            authorization.facebookPageId(),
            authorization.instagramAccountId());
    if (exact.isPresent()) {
      return exact;
    }
    return repository.findByOwnerKeyAndFacebookPageId(ownerKey(), authorization.facebookPageId());
  }

  private Optional<MetaConnectionEntity> findOwned(UUID connectionId) {
    if (connectionId == null) {
      return Optional.empty();
    }
    return repository.findByIdAndOwnerKey(connectionId, ownerKey());
  }

  private Map<MetaCapability, MetaCapabilityStatus> calculateCapabilities(
      MetaProviderAdapter.AuthorizationResult authorization) {
    return calculateCapabilities(
        authorization.grantedScopes(),
        authorization.facebookPageEligible(),
        authorization.instagramAccountEligible(),
        authorization.instagramAccountType(),
        authorization.expiresAt());
  }

  private Map<MetaCapability, MetaCapabilityStatus> calculateCapabilities(
      List<String> scopes, MetaConnectionEntity entity, Instant expiresAt) {
    return calculateCapabilities(
        Set.copyOf(scopes),
        entity.isFacebookPageEligible(),
        entity.isInstagramAccountEligible(),
        entity.getInstagramAccountType(),
        expiresAt);
  }

  private Map<MetaCapability, MetaCapabilityStatus> calculateCapabilities(
      Set<String> scopes,
      boolean facebookPageEligible,
      boolean instagramAccountEligible,
      String instagramAccountType,
      Instant expiresAt) {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    for (MetaCapability capability : MetaCapability.values()) {
      result.put(
          capability,
          capabilityStatus(
              capability,
              scopes,
              facebookPageEligible,
              instagramAccountEligible,
              instagramAccountType,
              expiresAt));
    }
    return result;
  }

  private MetaCapabilityStatus capabilityStatus(
      MetaCapability capability,
      Set<String> scopes,
      boolean facebookPageEligible,
      boolean instagramAccountEligible,
      String instagramAccountType,
      Instant expiresAt) {
    if (expiresAt == null) {
      return MetaCapabilityStatus.UNKNOWN;
    }
    if (!clock.instant().isBefore(expiresAt)) {
      return MetaCapabilityStatus.TOKEN_EXPIRED;
    }
    boolean facebookCapability = capability.name().contains("FACEBOOK");
    boolean instagramCapability = capability.name().contains("INSTAGRAM");
    if (facebookCapability && !facebookPageEligible) {
      return MetaCapabilityStatus.ACCOUNT_NOT_ELIGIBLE;
    }
    if (instagramCapability && !instagramAccountEligible) {
      return instagramAccountType == null || instagramAccountType.isBlank()
          ? MetaCapabilityStatus.UNKNOWN
          : MetaCapabilityStatus.ACCOUNT_NOT_ELIGIBLE;
    }
    Set<String> requiredScopes = requiredScopes(capability);
    if (!scopes.containsAll(requiredScopes)) {
      return MetaCapabilityStatus.MISSING_PERMISSION;
    }
    if (writeCapabilityDisabled(capability) || requiresReview(capability)) {
      return MetaCapabilityStatus.REQUIRES_REVIEW;
    }
    return MetaCapabilityStatus.SUPPORTED;
  }

  private Set<String> requiredScopes(MetaCapability capability) {
    return switch (capability) {
      case META_FACEBOOK_ANALYTICS_READ -> Set.of(PAGES_READ_ENGAGEMENT);
      case META_INSTAGRAM_ANALYTICS_READ ->
          Set.of(INSTAGRAM_BASIC, INSTAGRAM_MANAGE_INSIGHTS);
      case META_FACEBOOK_COMMENTS_READ -> Set.of(PAGES_READ_USER_CONTENT);
      case META_INSTAGRAM_COMMENTS_READ -> Set.of(INSTAGRAM_MANAGE_COMMENTS);
      case META_FACEBOOK_COMMENT_REPLY -> Set.of(PAGES_MANAGE_ENGAGEMENT);
      case META_INSTAGRAM_COMMENT_REPLY -> Set.of(INSTAGRAM_MANAGE_COMMENTS);
      case META_FACEBOOK_PUBLISH -> Set.of(PAGES_MANAGE_POSTS);
      case META_INSTAGRAM_PUBLISH -> Set.of(INSTAGRAM_CONTENT_PUBLISH);
    };
  }

  private boolean writeCapabilityDisabled(MetaCapability capability) {
    return switch (capability) {
      case META_FACEBOOK_COMMENT_REPLY, META_INSTAGRAM_COMMENT_REPLY ->
          !properties.commentReplyEnabled();
      case META_FACEBOOK_PUBLISH, META_INSTAGRAM_PUBLISH -> !properties.publishEnabled();
      default -> false;
    };
  }

  private boolean requiresReview(MetaCapability capability) {
    return switch (capability) {
      case META_INSTAGRAM_COMMENTS_READ,
          META_FACEBOOK_COMMENT_REPLY,
          META_INSTAGRAM_COMMENT_REPLY,
          META_FACEBOOK_PUBLISH,
          META_INSTAGRAM_PUBLISH -> true;
      case META_FACEBOOK_ANALYTICS_READ,
          META_INSTAGRAM_ANALYTICS_READ,
          META_FACEBOOK_COMMENTS_READ -> false;
    };
  }

  private MetaConnectionStatus connectionStatus(
      Map<MetaCapability, MetaCapabilityStatus> capabilities, Instant expiresAt) {
    if (expiresAt == null) {
      return MetaConnectionStatus.DEGRADED;
    }
    if (!clock.instant().isBefore(expiresAt)) {
      return MetaConnectionStatus.EXPIRED;
    }
    boolean analyticsSupported =
        capabilities.get(MetaCapability.META_FACEBOOK_ANALYTICS_READ)
                == MetaCapabilityStatus.SUPPORTED
            && capabilities.get(MetaCapability.META_INSTAGRAM_ANALYTICS_READ)
                == MetaCapabilityStatus.SUPPORTED;
    return analyticsSupported ? MetaConnectionStatus.CONNECTED : MetaConnectionStatus.DEGRADED;
  }

  private Map<MetaCapability, MetaCapabilityStatus> tokenExpiredCapabilities() {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    for (MetaCapability capability : MetaCapability.values()) {
      result.put(capability, MetaCapabilityStatus.TOKEN_EXPIRED);
    }
    return result;
  }

  private Map<MetaCapability, MetaCapabilityStatus> unknownCapabilities() {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    for (MetaCapability capability : MetaCapability.values()) {
      result.put(capability, MetaCapabilityStatus.UNKNOWN);
    }
    return result;
  }

  private MetaConnectionResponse toResponse(MetaConnectionEntity entity) {
    MetaConnectionStatus effectiveStatus = effectiveStatus(entity);
    Map<MetaCapability, MetaCapabilityStatus> effectiveCapabilities =
        effectiveCapabilities(entity, effectiveStatus);
    MetaConnectionResponse.Status responseStatus =
        switch (effectiveStatus) {
          case CONNECTED -> MetaConnectionResponse.Status.CONNECTED;
          case DEGRADED -> MetaConnectionResponse.Status.DEGRADED;
          case EXPIRED -> MetaConnectionResponse.Status.EXPIRED;
          case REVOKED -> MetaConnectionResponse.Status.REVOKED;
          case NOT_CONFIGURED -> MetaConnectionResponse.Status.NOT_CONFIGURED;
        };
    boolean connected =
        effectiveStatus == MetaConnectionStatus.CONNECTED
            || effectiveStatus == MetaConnectionStatus.DEGRADED;
    return new MetaConnectionResponse(
        responseStatus,
        connected,
        true,
        entity.getFacebookPageId() == null
            ? null
            : new MetaConnectionResponse.Page(entity.getFacebookPageId(), null, null),
        entity.getInstagramAccountId() == null
            ? null
            : new MetaConnectionResponse.InstagramAccount(
                entity.getInstagramAccountId(), null, entity.getInstagramAccountType(), null, null),
        entity.getLastValidatedAt(),
        properties.apiVersion(),
        permissionChecks(effectiveCapabilities),
        List.of(),
        entity.isFacebookPageEligible()
            ? MetaConnectionResponse.PageManagementVerification.VERIFIED
            : MetaConnectionResponse.PageManagementVerification.NOT_VERIFIED,
        message(entity, effectiveStatus),
        entity.getId(),
        entity.getOwnerKey(),
        effectiveStatus,
        entity.getGrantedScopes(),
        effectiveCapabilities,
        entity.getExpiresAt(),
        entity.getFailureReason());
  }

  private MetaConnectionStatus effectiveStatus(MetaConnectionEntity entity) {
    if ((entity.getStatus() == MetaConnectionStatus.CONNECTED
            || entity.getStatus() == MetaConnectionStatus.DEGRADED)
        && entity.getExpiresAt() != null
        && !clock.instant().isBefore(entity.getExpiresAt())) {
      return MetaConnectionStatus.EXPIRED;
    }
    return entity.getStatus();
  }

  private Map<MetaCapability, MetaCapabilityStatus> effectiveCapabilities(
      MetaConnectionEntity entity, MetaConnectionStatus status) {
    return status == MetaConnectionStatus.EXPIRED
        ? tokenExpiredCapabilities()
        : entity.getCapabilities();
  }

  private List<MetaConnectionResponse.PermissionCheck> permissionChecks(
      Map<MetaCapability, MetaCapabilityStatus> capabilities) {
    return List.of(
        permission(
            INSTAGRAM_BASIC,
            capabilities.get(MetaCapability.META_INSTAGRAM_ANALYTICS_READ)),
        permission(
            INSTAGRAM_MANAGE_INSIGHTS,
            capabilities.get(MetaCapability.META_INSTAGRAM_ANALYTICS_READ)),
        permission(
            PAGES_READ_ENGAGEMENT,
            capabilities.get(MetaCapability.META_FACEBOOK_ANALYTICS_READ)));
  }

  private MetaConnectionResponse.PermissionCheck permission(
      String permission, MetaCapabilityStatus capabilityStatus) {
    MetaConnectionResponse.PermissionStatus status =
        capabilityStatus == MetaCapabilityStatus.SUPPORTED
            ? MetaConnectionResponse.PermissionStatus.AVAILABLE
            : capabilityStatus == MetaCapabilityStatus.MISSING_PERMISSION
                ? MetaConnectionResponse.PermissionStatus.UNAVAILABLE
                : MetaConnectionResponse.PermissionStatus.NOT_REQUESTED;
    String message = capabilityStatus == null ? MetaCapabilityStatus.UNKNOWN.name() : capabilityStatus.name();
    return new MetaConnectionResponse.PermissionCheck(permission, status, message);
  }

  private String message(MetaConnectionEntity entity, MetaConnectionStatus status) {
    if (entity.getFailureReason() != null && !entity.getFailureReason().isBlank()) {
      return entity.getFailureReason();
    }
    return switch (status) {
      case CONNECTED -> "Meta read-only analytics connection is available.";
      case DEGRADED -> "Meta connection capabilities are partially available.";
      case EXPIRED -> "Meta connection token has expired.";
      case REVOKED -> "Meta connection has been disconnected.";
      case NOT_CONFIGURED -> "Meta read-only analytics is not configured.";
    };
  }

  private MetaConnectionResponse notConfiguredResponse() {
    return new MetaConnectionResponse(
        MetaConnectionResponse.Status.NOT_CONFIGURED,
        false,
        true,
        null,
        null,
        null,
        properties.apiVersion(),
        List.of(),
        List.of(),
        MetaConnectionResponse.PageManagementVerification.UNAVAILABLE,
        "Meta read-only analytics is not configured.",
        null,
        ownerKey(),
        MetaConnectionStatus.NOT_CONFIGURED,
        List.of(),
        Map.of(),
        null,
        null);
  }

  private MetaConnectionResponse failureResponse(String reason) {
    return new MetaConnectionResponse(
        MetaConnectionResponse.Status.DEGRADED,
        false,
        true,
        null,
        null,
        null,
        properties.apiVersion(),
        List.of(),
        List.of(),
        MetaConnectionResponse.PageManagementVerification.UNAVAILABLE,
        reason,
        null,
        ownerKey(),
        MetaConnectionStatus.DEGRADED,
        List.of(),
        Map.of(),
        null,
        reason);
  }

  private String sanitizeFailure(String reason) {
    if (reason == null || reason.isBlank()) {
      return "The Meta authorization request could not be completed.";
    }
    String sanitized = reason.replaceAll("(?i)bearer\\s+[^\\s,;]+", "Bearer [REDACTED]");
    return sanitized.length() <= 300 ? sanitized : sanitized.substring(0, 300);
  }

  private String ownerKey() {
    return properties.connectionOwnerKey();
  }
}
