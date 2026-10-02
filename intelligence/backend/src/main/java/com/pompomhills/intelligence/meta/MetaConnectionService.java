package com.pompomhills.intelligence.meta;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;

@Service
public class MetaConnectionService {
  private static final String INSTAGRAM_BASIC = "instagram_basic";
  private static final String INSTAGRAM_MANAGE_INSIGHTS = "instagram_manage_insights";
  private static final String PAGES_READ_ENGAGEMENT = "pages_read_engagement";
  private static final String PAGES_SHOW_LIST = "pages_show_list";
  private static final Duration CACHE_TTL = Duration.ofSeconds(30);

  private final MetaReadProperties properties;
  private final MetaGraphReadClient client;
  private final Clock clock;
  private CacheEntry cachedResponse;

  public MetaConnectionService(
      MetaReadProperties properties, MetaGraphReadClient client, Clock clock) {
    this.properties = properties;
    this.client = client;
    this.clock = clock;
  }

  public synchronized MetaConnectionResponse getConnection() {
    Instant now = clock.instant();
    if (cachedResponse != null && now.isBefore(cachedResponse.expiresAt())) {
      return cachedResponse.response();
    }

    MetaConnectionResponse response = validateConnection();
    cachedResponse = new CacheEntry(response, clock.instant().plus(CACHE_TTL));
    return response;
  }

  private MetaConnectionResponse validateConnection() {
    if (!properties.isConfigured()) {
      return notConfiguredResponse();
    }

    MetaConnectionResponse.Page page = null;
    MetaConnectionResponse.InstagramAccount instagramAccount = null;
    MetaConnectionResponse.PermissionCheck pageCheck;
    MetaConnectionResponse.PermissionCheck instagramCheck;
    MetaConnectionResponse.PermissionCheck insightsCheck;

    try {
      MetaGraphReadClient.FacebookPage graphPage = client.getFacebookPage();
      if (graphPage == null || graphPage.id() == null || graphPage.id().isBlank()) {
        pageCheck = unavailable(PAGES_READ_ENGAGEMENT, "Meta returned no Page data.");
      } else {
        page =
            new MetaConnectionResponse.Page(graphPage.id(), graphPage.name(), graphPage.category());
        pageCheck = available(PAGES_READ_ENGAGEMENT, "Facebook Page read access is available.");
      }
    } catch (MetaGraphException | RestClientException error) {
      pageCheck = unavailable(PAGES_READ_ENGAGEMENT, error);
    }

    try {
      MetaGraphReadClient.InstagramAccount graphAccount = client.getInstagramAccount();
      if (graphAccount == null || graphAccount.id() == null || graphAccount.id().isBlank()) {
        instagramCheck = unavailable(INSTAGRAM_BASIC, "Meta returned no Instagram account data.");
      } else {
        instagramAccount =
            new MetaConnectionResponse.InstagramAccount(
                graphAccount.id(),
                graphAccount.username(),
                graphAccount.accountType(),
                graphAccount.mediaCount(),
                graphAccount.profilePictureUrl());
        instagramCheck =
            available(INSTAGRAM_BASIC, "Instagram Professional Account read access is available.");
      }
    } catch (MetaGraphException | RestClientException error) {
      instagramCheck = unavailable(INSTAGRAM_BASIC, error);
    }

    try {
      client.validateInstagramInsights();
      insightsCheck =
          available(INSTAGRAM_MANAGE_INSIGHTS, "Instagram reach insights access is available.");
    } catch (MetaGraphException | RestClientException error) {
      insightsCheck = unavailable(INSTAGRAM_MANAGE_INSIGHTS, error);
    }

    MetaConnectionResponse.PageManagementVerification verification;
    try {
      verification = client.verifyConfiguredPageManaged();
    } catch (MetaGraphException | RestClientException error) {
      verification = MetaConnectionResponse.PageManagementVerification.UNAVAILABLE;
    }
    MetaConnectionResponse.PermissionCheck pagesShowListCheck = pagesShowListCheck(verification);

    List<MetaConnectionResponse.PermissionCheck> requiredPermissions =
        List.of(instagramCheck, insightsCheck, pageCheck);
    boolean connected =
        requiredPermissions.stream()
            .allMatch(check -> check.status() == MetaConnectionResponse.PermissionStatus.AVAILABLE);
    boolean partiallyAvailable =
        requiredPermissions.stream()
            .anyMatch(check -> check.status() == MetaConnectionResponse.PermissionStatus.AVAILABLE);
    MetaConnectionResponse.Status status =
        connected
            ? MetaConnectionResponse.Status.CONNECTED
            : partiallyAvailable
                ? MetaConnectionResponse.Status.DEGRADED
                : MetaConnectionResponse.Status.UNAVAILABLE;

    return response(
        status,
        connected,
        page,
        instagramAccount,
        clock.instant(),
        requiredPermissions,
        List.of(pagesShowListCheck),
        verification,
        connected
            ? "Meta read-only analytics connection is available."
            : partiallyAvailable
                ? "Meta read-only analytics connection is partially available."
                : "Meta read-only analytics connection is unavailable.");
  }

  private MetaConnectionResponse.PermissionCheck pagesShowListCheck(
      MetaConnectionResponse.PageManagementVerification verification) {
    return switch (verification) {
      case VERIFIED ->
          new MetaConnectionResponse.PermissionCheck(
              PAGES_SHOW_LIST,
              MetaConnectionResponse.PermissionStatus.AVAILABLE,
              "The configured Facebook Page is present among the Pages managed by the authenticated user.");
      case NOT_VERIFIED ->
          new MetaConnectionResponse.PermissionCheck(
              PAGES_SHOW_LIST,
              MetaConnectionResponse.PermissionStatus.UNAVAILABLE,
              "The configured Facebook Page was not found among the managed Pages.");
      case UNAVAILABLE ->
          new MetaConnectionResponse.PermissionCheck(
              PAGES_SHOW_LIST,
              MetaConnectionResponse.PermissionStatus.NOT_REQUESTED,
              "Page management verification was not performed.");
    };
  }

  private MetaConnectionResponse notConfiguredResponse() {
    List<MetaConnectionResponse.PermissionCheck> requiredPermissions =
        List.of(
            unavailable(
                INSTAGRAM_BASIC, "Configuration is incomplete; capability was not checked."),
            unavailable(
                INSTAGRAM_MANAGE_INSIGHTS,
                "Configuration is incomplete; capability was not checked."),
            unavailable(
                PAGES_READ_ENGAGEMENT, "Configuration is incomplete; capability was not checked."));
    return response(
        MetaConnectionResponse.Status.NOT_CONFIGURED,
        false,
        null,
        null,
        null,
        requiredPermissions,
        List.of(
            new MetaConnectionResponse.PermissionCheck(
                PAGES_SHOW_LIST,
                MetaConnectionResponse.PermissionStatus.NOT_REQUESTED,
                "Configuration is incomplete; Page management was not verified.")),
        MetaConnectionResponse.PageManagementVerification.UNAVAILABLE,
        "Meta read-only analytics is not configured.");
  }

  private MetaConnectionResponse response(
      MetaConnectionResponse.Status status,
      boolean connected,
      MetaConnectionResponse.Page page,
      MetaConnectionResponse.InstagramAccount instagramAccount,
      Instant lastValidatedAt,
      List<MetaConnectionResponse.PermissionCheck> requiredPermissions,
      List<MetaConnectionResponse.PermissionCheck> optionalPermissions,
      MetaConnectionResponse.PageManagementVerification pageManagementVerification,
      String message) {
    return new MetaConnectionResponse(
        status,
        connected,
        true,
        page,
        instagramAccount,
        lastValidatedAt,
        properties.apiVersion(),
        requiredPermissions,
        optionalPermissions,
        pageManagementVerification,
        message);
  }

  private MetaConnectionResponse.PermissionCheck available(String permission, String message) {
    return new MetaConnectionResponse.PermissionCheck(
        permission, MetaConnectionResponse.PermissionStatus.AVAILABLE, message);
  }

  private MetaConnectionResponse.PermissionCheck unavailable(String permission, String message) {
    return new MetaConnectionResponse.PermissionCheck(
        permission, MetaConnectionResponse.PermissionStatus.UNAVAILABLE, message);
  }

  private MetaConnectionResponse.PermissionCheck unavailable(
      String permission, RuntimeException error) {
    String message;
    if (error instanceof MetaGraphException graphError && graphError.isPermissionDenied()) {
      message = "Required Meta read permission is unavailable.";
    } else if (error instanceof MetaGraphException graphError
        && graphError.isAuthenticationUnavailable()) {
      message = "Meta authentication is unavailable for this capability.";
    } else {
      message = "Meta Graph API capability validation is unavailable.";
    }
    return unavailable(permission, message);
  }

  private record CacheEntry(MetaConnectionResponse response, Instant expiresAt) {}
}
