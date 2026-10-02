package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;

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
    String message) {

  public enum Status {
    CONNECTED,
    DEGRADED,
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
