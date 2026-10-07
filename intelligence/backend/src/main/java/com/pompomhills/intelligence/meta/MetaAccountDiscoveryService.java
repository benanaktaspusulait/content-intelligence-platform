package com.pompomhills.intelligence.meta;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Performs bounded, owner-scoped Meta Page and linked-account discovery. */
@Service
public class MetaAccountDiscoveryService {
  private static final String PAGES_READ_ENGAGEMENT = "pages_read_engagement";
  private static final String PAGES_READ_USER_CONTENT = "pages_read_user_content";
  private static final String PAGES_MANAGE_ENGAGEMENT = "pages_manage_engagement";
  private static final String PAGES_MANAGE_POSTS = "pages_manage_posts";
  private static final String INSTAGRAM_BASIC = "instagram_basic";
  private static final String INSTAGRAM_MANAGE_INSIGHTS = "instagram_manage_insights";
  private static final String INSTAGRAM_MANAGE_COMMENTS = "instagram_manage_comments";
  private static final String INSTAGRAM_CONTENT_PUBLISH = "instagram_content_publish";
  private static final int PAGE_LIMIT = 25;
  private static final int MAX_PAGE_REQUESTS = 4;
  private static final int MAX_PAGE_TARGETS = 100;

  private final MetaConnectionRepository repository;
  private final MetaGraphReadClient graph;
  private final MetaTokenEncryptionService encryption;
  private final MetaReadProperties properties;
  private final Clock clock;

  @Autowired
  public MetaAccountDiscoveryService(
      MetaConnectionRepository repository,
      MetaGraphReadClient graph,
      MetaTokenEncryptionService encryption,
      MetaReadProperties properties,
      Clock clock) {
    this.repository = repository;
    this.graph = graph;
    this.encryption = encryption;
    this.properties = properties;
    this.clock = clock;
  }

  /** Compatibility constructor for callers that prefer provider-client-first argument ordering. */
  public MetaAccountDiscoveryService(
      MetaGraphReadClient graph,
      MetaConnectionRepository repository,
      MetaTokenEncryptionService encryption,
      MetaReadProperties properties,
      Clock clock) {
    this(repository, graph, encryption, properties, clock);
  }

  @Transactional
  public MetaAccountDiscoveryResponse discover(UUID connectionId) {
    Optional<MetaConnectionEntity> found = findConnection(connectionId);
    if (found.isEmpty()) {
      return unavailableResponse(
          null,
          MetaConnectionStatus.NOT_CONFIGURED,
          "A Meta connection was not found.",
          null,
          unknownCapabilities());
    }

    MetaConnectionEntity connection = found.get();
    Instant now = clock.instant();
    if (connection.getStatus() == MetaConnectionStatus.REVOKED) {
      return responseFor(
          connection,
          MetaConnectionStatus.REVOKED,
          List.of(),
          null,
          null,
          unknownCapabilities(),
          "Meta connection has been disconnected.",
          connection.getFailureReason());
    }
    if (connection.getExpiresAt() == null || !now.isBefore(connection.getExpiresAt())) {
      Map<MetaCapability, MetaCapabilityStatus> expired = tokenExpiredCapabilities();
      return responseFor(
          connection,
          MetaConnectionStatus.EXPIRED,
          List.of(),
          connection.getFacebookPageId(),
          connection.getInstagramAccountId(),
          expired,
          "Meta connection token has expired.",
          "Meta token has expired; account discovery was not performed.");
    }

    MetaProviderAdapter.StoredTokens tokens;
    try {
      tokens = connection.decryptTokens(encryption);
    } catch (RuntimeException error) {
      return failClosed(
          connection,
          "Meta authentication is unavailable; account discovery was not performed.");
    }
    if (tokens.userAccessToken() == null || tokens.userAccessToken().isBlank()) {
      return failClosed(
          connection,
          "Meta authentication is unavailable; account discovery was not performed.");
    }

    List<MetaGraphReadClient.PageAccount> pages;
    try {
      pages = listBoundedPages(tokens.userAccessToken());
    } catch (MetaGraphException error) {
      String message =
          error.isPermissionDenied()
              ? "Meta Page discovery permission is unavailable."
              : error.isAuthenticationUnavailable()
                  ? "Meta authentication is unavailable for Page discovery."
                  : "Meta Page discovery could not be completed.";
      return failClosed(connection, message);
    } catch (RuntimeException error) {
      return failClosed(connection, "Meta Page discovery could not be completed.");
    }

    MetaGraphReadClient.PageAccount selected = selectCanonicalPage(connection, pages);
    if (selected == null) {
      Map<MetaCapability, MetaCapabilityStatus> unknown = unknownCapabilities();
      connection.setCapabilities(unknown);
      connection.setStatus(MetaConnectionStatus.DEGRADED);
      connection.setLastValidatedAt(now);
      connection.setFailureReason("Meta returned no selectable managed Facebook Page.");
      MetaConnectionEntity saved = repository.save(connection);
      return responseFor(
          saved,
          MetaConnectionStatus.DEGRADED,
          pageTargets(pages, null, saved),
          saved.getFacebookPageId(),
          saved.getInstagramAccountId(),
          unknown,
          "Meta returned no selectable managed Facebook Page.",
          saved.getFailureReason());
    }

    String linkedInstagramId = normalize(selected.linkedInstagramAccountId());
    Map<MetaCapability, MetaCapabilityStatus> capabilities =
        calculateCapabilities(connection, selected, linkedInstagramId);
    connection.applyDiscoveryTarget(
        selected.id(),
        linkedInstagramId,
        null,
        true,
        false,
        capabilities,
        now,
        null);
    MetaConnectionStatus connectionStatus = connectionStatus(capabilities, connection.getExpiresAt());
    connection.setStatus(connectionStatus);
    connection.setFailureReason(null);
    MetaConnectionEntity saved = repository.save(connection);

    return responseFor(
        saved,
        connectionStatus,
        pageTargets(pages, selected.id(), saved),
        selected.id(),
        linkedInstagramId,
        capabilities,
        linkedInstagramId == null
            ? "Managed Facebook Page discovered; no linked Instagram account was returned."
            : "Managed Facebook Page and linked Instagram account discovered.",
        null);
  }

  private List<MetaGraphReadClient.PageAccount> listBoundedPages(String userToken) {
    List<MetaGraphReadClient.PageAccount> result = new ArrayList<>();
    Set<String> pageIds = new LinkedHashSet<>();
    Set<String> cursors = new LinkedHashSet<>();
    String after = null;
    for (int request = 0; request < MAX_PAGE_REQUESTS && result.size() < MAX_PAGE_TARGETS; request++) {
      MetaGraphReadClient.PageAccountPage page = graph.listManagedPages(userToken, after, PAGE_LIMIT);
      if (page == null || page.data() == null) {
        break;
      }
      for (MetaGraphReadClient.PageAccount account : page.data()) {
        if (account == null) {
          continue;
        }
        String id = normalize(account.id());
        if (id == null || !pageIds.add(id)) {
          continue;
        }
        result.add(
            new MetaGraphReadClient.PageAccount(
                id,
                normalize(account.name()),
                normalize(account.category()),
                account.accessTokenAvailable(),
                normalize(account.linkedInstagramAccountId())));
        if (result.size() == MAX_PAGE_TARGETS) {
          break;
        }
      }
      String next = page.afterCursor();
      if (next == null || next.isBlank() || !cursors.add(next.trim())) {
        break;
      }
      after = next.trim();
    }
    return List.copyOf(result);
  }

  private MetaGraphReadClient.PageAccount selectCanonicalPage(
      MetaConnectionEntity connection, List<MetaGraphReadClient.PageAccount> pages) {
    String currentPageId = normalize(connection.getFacebookPageId());
    if (currentPageId != null) {
      return pages.stream()
          .filter(page -> currentPageId.equals(normalize(page.id())))
          .findFirst()
          .orElse(null);
    }
    return pages.stream().findFirst().orElse(null);
  }

  private List<MetaAccountDiscoveryResponse.PageTarget> pageTargets(
      List<MetaGraphReadClient.PageAccount> pages,
      String selectedPageId,
      MetaConnectionEntity connection) {
    List<MetaAccountDiscoveryResponse.PageTarget> targets = new ArrayList<>();
    for (MetaGraphReadClient.PageAccount page : pages) {
      String pageId = normalize(page.id());
      if (pageId == null) {
        continue;
      }
      boolean selected = pageId.equals(normalize(selectedPageId));
      String instagramId = normalize(page.linkedInstagramAccountId());
      Map<MetaCapability, MetaCapabilityStatus> capabilities =
          selected
              ? connection.getCapabilities()
              : calculateCapabilities(connection, page, instagramId);
      MetaAccountDiscoveryResponse.InstagramTarget instagram =
          instagramId == null
              ? null
              : new MetaAccountDiscoveryResponse.InstagramTarget(
                  instagramId,
                  selected && instagramId.equals(normalize(connection.getInstagramAccountId())),
                  MetaCapabilityStatus.UNKNOWN,
                  instagramCapabilities(capabilities));
      targets.add(
          new MetaAccountDiscoveryResponse.PageTarget(
              pageId,
              normalize(page.name()),
              normalize(page.category()),
              page.accessTokenAvailable(),
              selected,
              pageEligibility(capabilities),
              capabilities,
              instagram));
    }
    return List.copyOf(targets);
  }

  private MetaCapabilityStatus pageEligibility(
      Map<MetaCapability, MetaCapabilityStatus> capabilities) {
    MetaCapabilityStatus status =
        capabilities.get(MetaCapability.META_FACEBOOK_ANALYTICS_READ);
    return status == MetaCapabilityStatus.SUPPORTED
            || status == MetaCapabilityStatus.MISSING_PERMISSION
        ? status
        : MetaCapabilityStatus.UNKNOWN;
  }

  private Map<MetaCapability, MetaCapabilityStatus> calculateCapabilities(
      MetaConnectionEntity connection,
      MetaGraphReadClient.PageAccount page,
      String linkedInstagramId) {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    Set<String> scopes = Set.copyOf(connection.getGrantedScopes());
    for (MetaCapability capability : MetaCapability.values()) {
      result.put(
          capability,
          capabilityStatus(
              capability,
              scopes,
              page != null,
              page != null && page.accessTokenAvailable(),
              linkedInstagramId != null,
              null,
              connection.getExpiresAt()));
    }
    return Map.copyOf(result);
  }

  private MetaCapabilityStatus capabilityStatus(
      MetaCapability capability,
      Set<String> scopes,
      boolean pageManaged,
      boolean pageTokenAvailable,
      boolean instagramLinked,
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
    if (facebookCapability && (!pageManaged || !pageTokenAvailable)) {
      return MetaCapabilityStatus.UNKNOWN;
    }
    if (instagramCapability && !instagramLinked) {
      return MetaCapabilityStatus.UNKNOWN;
    }
    if (instagramCapability && (instagramAccountType == null || instagramAccountType.isBlank())) {
      return MetaCapabilityStatus.UNKNOWN;
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

  private Map<MetaCapability, MetaCapabilityStatus> instagramCapabilities(
      Map<MetaCapability, MetaCapabilityStatus> capabilities) {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    for (MetaCapability capability : MetaCapability.values()) {
      if (capability.name().contains("INSTAGRAM")) {
        result.put(capability, capabilities.getOrDefault(capability, MetaCapabilityStatus.UNKNOWN));
      }
    }
    return Map.copyOf(result);
  }

  private Set<String> requiredScopes(MetaCapability capability) {
    return switch (capability) {
      case META_FACEBOOK_ANALYTICS_READ -> Set.of(PAGES_READ_ENGAGEMENT);
      case META_INSTAGRAM_ANALYTICS_READ -> Set.of(INSTAGRAM_BASIC, INSTAGRAM_MANAGE_INSIGHTS);
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
    return capabilities.get(MetaCapability.META_FACEBOOK_ANALYTICS_READ)
                == MetaCapabilityStatus.SUPPORTED
            && capabilities.get(MetaCapability.META_INSTAGRAM_ANALYTICS_READ)
                == MetaCapabilityStatus.SUPPORTED
        ? MetaConnectionStatus.CONNECTED
        : MetaConnectionStatus.DEGRADED;
  }

  private MetaAccountDiscoveryResponse failClosed(
      MetaConnectionEntity connection, String message) {
    Map<MetaCapability, MetaCapabilityStatus> unknown = unknownCapabilities();
    connection.setCapabilities(unknown);
    connection.setStatus(MetaConnectionStatus.DEGRADED);
    connection.setLastValidatedAt(clock.instant());
    connection.setFailureReason(message);
    MetaConnectionEntity saved = repository.save(connection);
    return responseFor(
        saved,
        MetaConnectionStatus.DEGRADED,
        List.of(),
        saved.getFacebookPageId(),
        saved.getInstagramAccountId(),
        unknown,
        message,
        saved.getFailureReason());
  }

  private MetaAccountDiscoveryResponse responseFor(
      MetaConnectionEntity connection,
      MetaConnectionStatus status,
      List<MetaAccountDiscoveryResponse.PageTarget> pages,
      String selectedPageId,
      String selectedInstagramAccountId,
      Map<MetaCapability, MetaCapabilityStatus> capabilities,
      String message,
      String failureReason) {
    return new MetaAccountDiscoveryResponse(
        connection == null ? null : connection.getId(),
        connection == null ? properties.connectionOwnerKey() : connection.getOwnerKey(),
        responseStatus(status),
        status,
        pages,
        selectedPageId,
        selectedInstagramAccountId,
        capabilities,
        connection == null ? null : connection.getExpiresAt(),
        message,
        failureReason);
  }

  private MetaAccountDiscoveryResponse unavailableResponse(
      UUID connectionId,
      MetaConnectionStatus status,
      String message,
      String failureReason,
      Map<MetaCapability, MetaCapabilityStatus> capabilities) {
    return new MetaAccountDiscoveryResponse(
        connectionId,
        properties.connectionOwnerKey(),
        responseStatus(status),
        status,
        List.of(),
        null,
        null,
        capabilities,
        null,
        message,
        failureReason);
  }

  private MetaAccountDiscoveryResponse.Status responseStatus(MetaConnectionStatus status) {
    return switch (status) {
      case CONNECTED -> MetaAccountDiscoveryResponse.Status.AVAILABLE;
      case DEGRADED -> MetaAccountDiscoveryResponse.Status.DEGRADED;
      case EXPIRED -> MetaAccountDiscoveryResponse.Status.EXPIRED;
      case REVOKED -> MetaAccountDiscoveryResponse.Status.REVOKED;
      case NOT_CONFIGURED -> MetaAccountDiscoveryResponse.Status.NOT_CONFIGURED;
    };
  }

  private Map<MetaCapability, MetaCapabilityStatus> unknownCapabilities() {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    for (MetaCapability capability : MetaCapability.values()) {
      result.put(capability, MetaCapabilityStatus.UNKNOWN);
    }
    return Map.copyOf(result);
  }

  private Map<MetaCapability, MetaCapabilityStatus> tokenExpiredCapabilities() {
    EnumMap<MetaCapability, MetaCapabilityStatus> result = new EnumMap<>(MetaCapability.class);
    for (MetaCapability capability : MetaCapability.values()) {
      result.put(capability, MetaCapabilityStatus.TOKEN_EXPIRED);
    }
    return Map.copyOf(result);
  }

  private Optional<MetaConnectionEntity> findConnection(UUID connectionId) {
    return connectionId == null
        ? repository.findTopByOwnerKeyOrderByUpdatedAtDesc(properties.connectionOwnerKey())
        : repository.findByIdAndOwnerKey(connectionId, properties.connectionOwnerKey());
  }

  private String normalize(String value) {
    if (value == null) {
      return null;
    }
    String normalized = value.trim();
    return normalized.isBlank() ? null : normalized;
  }
}
