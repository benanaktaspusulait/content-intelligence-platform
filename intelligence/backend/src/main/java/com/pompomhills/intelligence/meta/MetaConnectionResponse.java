package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public record MetaConnectionResponse(
    Status status,
    boolean connected,
    boolean readOnlyAnalytics,
    Page page,
    InstagramAccount instagramAccount,
    Instant lastValidatedAt,
    String apiVersion,
    List<PermissionCheck> requiredPermissions,
    List<PermissionCheck> optionalPermissions,
    PageManagementVerification pageManagementVerification,
    String message,
    UUID connectionId,
    String ownerIdentity,
    MetaConnectionStatus connectionStatus,
    List<String> grantedScopes,
    Map<MetaCapability, MetaCapabilityStatus> capabilities,
    Instant expiresAt,
    String failureReason) {

  public MetaConnectionResponse {
    requiredPermissions = requiredPermissions == null ? List.of() : List.copyOf(requiredPermissions);
    optionalPermissions = optionalPermissions == null ? List.of() : List.copyOf(optionalPermissions);
    grantedScopes = grantedScopes == null ? List.of() : List.copyOf(grantedScopes);
    capabilities = capabilities == null ? Map.of() : Map.copyOf(capabilities);
  }

  /** Compatibility constructor for the pre-durable read-only response shape. */
  public MetaConnectionResponse(
      Status status,
      boolean connected,
      boolean readOnlyAnalytics,
      Page page,
      InstagramAccount instagramAccount,
      Instant lastValidatedAt,
      String apiVersion,
      List<PermissionCheck> requiredPermissions,
      List<PermissionCheck> optionalPermissions,
      PageManagementVerification pageManagementVerification,
      String message) {
    this(
        status,
        connected,
        readOnlyAnalytics,
        page,
        instagramAccount,
        lastValidatedAt,
        apiVersion,
        requiredPermissions,
        optionalPermissions,
        pageManagementVerification,
        message,
        null,
        null,
        toConnectionStatus(status),
        List.of(),
        Map.of(),
        null,
        null);
  }

  public String ownerKey() {
    return ownerIdentity;
  }

  private static MetaConnectionStatus toConnectionStatus(Status status) {
    if (status == null) {
      return MetaConnectionStatus.NOT_CONFIGURED;
    }
    return switch (status) {
      case CONNECTED -> MetaConnectionStatus.CONNECTED;
      case DEGRADED, EXPIRED -> MetaConnectionStatus.DEGRADED;
      case REVOKED -> MetaConnectionStatus.REVOKED;
      case UNAVAILABLE, NOT_CONFIGURED -> MetaConnectionStatus.NOT_CONFIGURED;
    };
  }

  public enum Status {
    CONNECTED,
    DEGRADED,
    EXPIRED,
    REVOKED,
    UNAVAILABLE,
    NOT_CONFIGURED
  }

  public enum PageManagementVerification {
    VERIFIED,
    NOT_VERIFIED,
    UNAVAILABLE
  }

  public enum PermissionStatus {
    AVAILABLE,
    UNAVAILABLE,
    NOT_REQUESTED
  }

  public record Page(String id, String name, String category) {}

  public record InstagramAccount(
      String id, String username, String accountType, Long mediaCount, String profilePictureUrl) {}

  public record PermissionCheck(String permission, PermissionStatus status, String message) {}
}
