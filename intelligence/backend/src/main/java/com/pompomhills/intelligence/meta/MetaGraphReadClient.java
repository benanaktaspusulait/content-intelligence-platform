package com.pompomhills.intelligence.meta;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public final class MetaGraphReadClient {
  private static final String PAGE_FIELDS = "id,name,category";
  private static final String MANAGED_PAGE_FIELDS =
      "id,name,category,access_token,instagram_business_account";
  private static final int MIN_PAGE_LIMIT = 1;
  private static final int MAX_PAGE_LIMIT = 50;
  private static final String INSTAGRAM_ACCOUNT_FIELDS =
      "id,username,media_count,profile_picture_url";
  private static final String INSTAGRAM_MEDIA_FIELDS =
      "id,media_type,media_product_type,caption,permalink,timestamp,thumbnail_url,media_url";
  private static final String INSTAGRAM_MEDIA_INSIGHT_METRICS =
      "views,reach,shares,saved,total_interactions";
  private static final String PAGE_POSTS_FIELDS = "id,message,created_time,permalink_url";
  private static final Pattern NUMERIC_ID = Pattern.compile("\\d{1,40}");
  private static final int MIN_MEDIA_LIMIT = 1;
  private static final int MAX_MEDIA_LIMIT = 50;
  private static final int MIN_POSTS_LIMIT = 1;
  private static final int MAX_POSTS_LIMIT = 25;
  private final RestClient restClient;
  private final ObjectMapper objectMapper;
  private final MetaReadProperties properties;
  private final MetaOAuthTokenStore oauthTokenStore;
  private final MetaConnectionRepository connectionRepository;
  private final MetaTokenEncryptionService tokenEncryption;
  private final Clock clock;

  @Autowired
  public MetaGraphReadClient(
      @Qualifier("metaReadRestClient") RestClient restClient,
      ObjectMapper objectMapper,
      MetaReadProperties properties,
      MetaOAuthTokenStore oauthTokenStore,
      MetaConnectionRepository connectionRepository,
      MetaTokenEncryptionService tokenEncryption,
      Clock clock) {
    this.restClient = restClient;
    this.objectMapper = objectMapper;
    this.properties = properties;
    this.oauthTokenStore = oauthTokenStore;
    this.connectionRepository = connectionRepository;
    this.tokenEncryption = tokenEncryption;
    this.clock = clock;
  }

  /** Compatibility constructor for read-only unit tests and legacy static-token callers. */
  public MetaGraphReadClient(
      RestClient restClient,
      ObjectMapper objectMapper,
      MetaReadProperties properties,
      MetaOAuthTokenStore oauthTokenStore) {
    this(restClient, objectMapper, properties, oauthTokenStore, null, null, Clock.systemUTC());
  }

  /** The durable Page token wins; static/process-local tokens are fallbacks only before durable state exists. */
  private String effectiveAccessToken() {
    Optional<MetaConnectionEntity> durable = durableConnection();
    if (durable.isPresent()) {
      if (!isActive(durable.get()) || tokenEncryption == null) {
        return "";
      }
      String token = durable.get().decryptTokens(tokenEncryption).pageAccessToken();
      return token == null ? "" : token;
    }
    String oauthToken = oauthTokenStore.getPageAccessToken();
    return oauthToken != null && !oauthToken.isBlank() ? oauthToken : properties.accessToken();
  }

  /** A user token is used only for user-context calls such as GET /me/accounts. */
  private String effectiveUserAccessToken() {
    Optional<MetaConnectionEntity> durable = durableConnection();
    if (durable.isPresent()) {
      if (!isActive(durable.get()) || tokenEncryption == null) {
        return "";
      }
      String token = durable.get().decryptTokens(tokenEncryption).userAccessToken();
      return token == null ? "" : token;
    }
    String oauthUserToken = oauthTokenStore.getUserAccessToken();
    return oauthUserToken != null && !oauthUserToken.isBlank()
        ? oauthUserToken
        : properties.userAccessToken();
  }

  public boolean hasEffectiveAccessToken() {
    return !effectiveAccessToken().isBlank();
  }

  public boolean hasEffectiveTargets() {
    return hasEffectivePageTarget() && hasEffectiveInstagramTarget();
  }

  public boolean hasEffectivePageTarget() {
    return !effectivePageId().isBlank();
  }

  public boolean hasEffectiveInstagramTarget() {
    return !effectiveInstagramAccountId().isBlank();
  }

  private String effectivePageId() {
    Optional<MetaConnectionEntity> durable = durableConnection();
    if (durable.isPresent()) {
      return isActive(durable.get()) ? normalizeTarget(durable.get().getFacebookPageId()) : "";
    }
    return properties.pageId();
  }

  private String effectiveInstagramAccountId() {
    Optional<MetaConnectionEntity> durable = durableConnection();
    if (durable.isPresent()) {
      return isActive(durable.get())
          ? normalizeTarget(durable.get().getInstagramAccountId())
          : "";
    }
    return properties.instagramAccountId();
  }

  private Optional<MetaConnectionEntity> durableConnection() {
    if (connectionRepository == null) {
      return Optional.empty();
    }
    return connectionRepository.findTopByOwnerKeyOrderByUpdatedAtDesc(properties.connectionOwnerKey());
  }

  private Optional<MetaConnectionEntity> activeDurableConnection() {
    return durableConnection().filter(this::isActive);
  }

  private boolean isActive(MetaConnectionEntity connection) {
    return (connection.getStatus() == MetaConnectionStatus.CONNECTED
            || connection.getStatus() == MetaConnectionStatus.DEGRADED)
        && connection.getExpiresAt() != null
        && clock.instant().isBefore(connection.getExpiresAt());
  }

  private String normalizeTarget(String value) {
    return value == null ? "" : value.trim();
  }

  private org.springframework.web.client.RestClient.RequestHeadersSpec<?> withAuth(
      org.springframework.web.client.RestClient.RequestHeadersSpec<?> spec) {
    String token = effectiveAccessToken();
    return token.isBlank()
        ? spec
        : spec.headers(headers -> headers.set(HttpHeaders.AUTHORIZATION, "Bearer " + token));
  }

  public FacebookPage getFacebookPage() {
    return withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder ->
                        uriBuilder
                            .pathSegment(properties.apiVersion(), effectivePageId())
                            .queryParam("fields", PAGE_FIELDS)
                            .build()))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .body(FacebookPage.class);
  }

  /**
   * Lists a bounded page of managed Facebook Pages with a caller-supplied user token. The token is
   * sent only as a Bearer header; it is never added to the request URI or returned in the typed
   * response.
   */
  public PageAccountPage listManagedPages(String userToken, String after, int limit) {
    String token = userToken == null ? "" : userToken.trim();
    if (token.isBlank()) {
      throw new IllegalArgumentException("Meta user access token is required.");
    }
    int boundedLimit = Math.max(MIN_PAGE_LIMIT, Math.min(MAX_PAGE_LIMIT, limit));
    String cursor = after == null || after.isBlank() ? null : after.trim();
    RawPageAccountPage response =
        restClient
            .get()
            .uri(
                uriBuilder -> {
                  uriBuilder
                      .pathSegment(properties.apiVersion(), "me", "accounts")
                      .queryParam("fields", MANAGED_PAGE_FIELDS)
                      .queryParam("limit", boundedLimit);
                  if (cursor != null) {
                    uriBuilder.queryParam("after", cursor);
                  }
                  return uriBuilder.build();
                })
            .headers(headers -> headers.set(HttpHeaders.AUTHORIZATION, "Bearer " + token))
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, responseBody) -> {
                  throw mapError(responseBody.getStatusCode().value(), responseBody.getBody(), token);
                })
            .body(RawPageAccountPage.class);
    if (response == null) {
      return new PageAccountPage(List.of(), null);
    }
    List<PageAccount> pages =
        response.data() == null
            ? List.of()
            : response.data().stream()
                .filter(java.util.Objects::nonNull)
                .map(RawPageAccount::toPageAccount)
                .filter(java.util.Objects::nonNull)
                .toList();
    return new PageAccountPage(pages, response.paging());
  }

  /**
   * Verifies, read-only, that the configured Page id is among the Pages managed by the
   * authenticated user. Uses pages_show_list via GET /me/accounts, requesting only Page ids so no
   * other Page names are retrieved. The list is not returned or persisted.
   */
  public MetaConnectionResponse.PageManagementVerification verifyConfiguredPageManaged() {
    String userToken = effectiveUserAccessToken();
    if (userToken.isBlank()) {
      return MetaConnectionResponse.PageManagementVerification.UNAVAILABLE;
    }
    AccountsResponse response =
        restClient
            .get()
            .uri(
                uriBuilder ->
                    uriBuilder
                        .pathSegment(properties.apiVersion(), "me", "accounts")
                        .queryParam("fields", "id")
                        .queryParam("limit", 200)
                        .build())
            .headers(headers -> headers.set(HttpHeaders.AUTHORIZATION, "Bearer " + userToken))
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, resp) -> {
                  throw mapError(resp.getStatusCode().value(), resp.getBody());
                })
            .body(AccountsResponse.class);
    if (response == null || response.data() == null) {
      return MetaConnectionResponse.PageManagementVerification.UNAVAILABLE;
    }
    boolean present =
        response.data().stream()
            .anyMatch(account -> account != null && effectivePageId().equals(account.id()));
    return present
        ? MetaConnectionResponse.PageManagementVerification.VERIFIED
        : MetaConnectionResponse.PageManagementVerification.NOT_VERIFIED;
  }

  /** Reads recent content published by the configured Facebook Page. GET only, read-only. */
  public PagePostsResponse getPagePosts(int limit) {
    int boundedLimit = Math.max(MIN_POSTS_LIMIT, Math.min(MAX_POSTS_LIMIT, limit));
    return withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder ->
                        uriBuilder
                            .pathSegment(properties.apiVersion(), effectivePageId(), "posts")
                            .queryParam("fields", PAGE_POSTS_FIELDS)
                            .queryParam("limit", boundedLimit)
                            .build()))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .body(PagePostsResponse.class);
  }

  public InstagramAccount getInstagramAccount() {
    return withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder ->
                        uriBuilder
                            .pathSegment(properties.apiVersion(), effectiveInstagramAccountId())
                            .queryParam("fields", INSTAGRAM_ACCOUNT_FIELDS)
                            .build()))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .body(InstagramAccount.class);
  }

  public void validateInstagramInsights() {
    withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder ->
                        uriBuilder
                            .pathSegment(
                                properties.apiVersion(),
                                effectiveInstagramAccountId(),
                                "insights")
                            .queryParam("metric", "reach")
                            .queryParam("period", "day")
                            .build()))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .toBodilessEntity();
  }

  /** Reads a single page of Instagram media for the configured account. GET only. */
  public InstagramMediaPage listInstagramMedia(String after, int limit) {
    int boundedLimit = Math.max(MIN_MEDIA_LIMIT, Math.min(MAX_MEDIA_LIMIT, limit));
    String cursor = (after == null || after.isBlank()) ? null : after.trim();
    return withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder -> {
                      uriBuilder
                          .pathSegment(
                              properties.apiVersion(), effectiveInstagramAccountId(), "media")
                          .queryParam("fields", INSTAGRAM_MEDIA_FIELDS)
                          .queryParam("limit", boundedLimit);
                      if (cursor != null) {
                        uriBuilder.queryParam("after", cursor);
                      }
                      return uriBuilder.build();
                    }))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .body(InstagramMediaPage.class);
  }

  /** Reads a single Instagram media object by its numeric identifier. GET only. */
  public InstagramMedia getInstagramMedia(String mediaId) {
    String validatedId = requireNumericId(mediaId);
    return withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder ->
                        uriBuilder
                            .pathSegment(properties.apiVersion(), validatedId)
                            .queryParam("fields", INSTAGRAM_MEDIA_FIELDS)
                            .build()))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .body(InstagramMedia.class);
  }

  /** Reads read-only insight metrics for a single Instagram media object. GET only. */
  public InstagramInsightsResponse getInstagramMediaInsights(String mediaId) {
    String validatedId = requireNumericId(mediaId);
    return withAuth(
            restClient
                .get()
                .uri(
                    uriBuilder ->
                        uriBuilder
                            .pathSegment(properties.apiVersion(), validatedId, "insights")
                            .queryParam("metric", INSTAGRAM_MEDIA_INSIGHT_METRICS)
                            .build()))
        .retrieve()
        .onStatus(
            status -> status.isError(),
            (request, response) -> {
              throw mapError(response.getStatusCode().value(), response.getBody());
            })
        .body(InstagramInsightsResponse.class);
  }

  private String requireNumericId(String mediaId) {
    String trimmed = mediaId == null ? "" : mediaId.trim();
    if (!NUMERIC_ID.matcher(trimmed).matches()) {
      throw new IllegalArgumentException("Instagram media id must be numeric.");
    }
    return trimmed;
  }

  private MetaGraphException mapError(int httpStatus, java.io.InputStream responseBody) {
    return mapError(httpStatus, responseBody, new String[0]);
  }

  private MetaGraphException mapError(
      int httpStatus, java.io.InputStream responseBody, String... requestCredentials) {
    try {
      MetaErrorEnvelope envelope = objectMapper.readValue(responseBody, MetaErrorEnvelope.class);
      MetaError error = envelope == null ? null : envelope.error();
      if (error == null) {
        return genericError(httpStatus);
      }
      return new MetaGraphException(
          httpStatus,
          error.code(),
          error.errorSubcode(),
          error.type(),
          error.fbTraceId(),
          sanitizeMessage(error.message(), requestCredentials));
    } catch (IOException | RuntimeException ignored) {
      return genericError(httpStatus);
    }
  }

  private MetaGraphException genericError(int httpStatus) {
    return new MetaGraphException(
        httpStatus, null, null, null, null, "Meta Graph API request failed.");
  }

  private String sanitizeMessage(String message, String... requestCredentials) {
    List<String> credentials = new ArrayList<>();
    credentials.add(properties.accessToken());
    credentials.add(properties.userAccessToken());
    credentials.add(oauthTokenStore.getPageAccessToken());
    credentials.add(oauthTokenStore.getUserAccessToken());
    if (requestCredentials != null) {
      credentials.addAll(List.of(requestCredentials));
    }
    if (tokenEncryption != null) {
      try {
        Optional<MetaConnectionEntity> durable = activeDurableConnection();
        if (durable.isPresent()) {
          MetaProviderAdapter.StoredTokens tokens = durable.get().decryptTokens(tokenEncryption);
          credentials.add(tokens.pageAccessToken());
          credentials.add(tokens.userAccessToken());
          credentials.add(tokens.refreshToken());
        }
      } catch (RuntimeException ignored) {
        // Keep generic redaction even if a persisted token cannot be decrypted.
      }
    }
    return MetaErrorSanitizer.sanitize(
        message, "Meta Graph API request failed.", credentials.toArray(String[]::new));
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record RawPageAccountPage(List<RawPageAccount> data, Paging paging) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record RawPageAccount(
      String id,
      String name,
      String category,
      @JsonProperty("access_token") String accessToken,
      @JsonProperty("instagram_business_account") RawInstagramBusinessAccount instagramBusinessAccount) {
    PageAccount toPageAccount() {
      if (id == null || id.isBlank()) {
        return null;
      }
      return new PageAccount(
          id.trim(),
          name,
          category,
          accessToken != null && !accessToken.isBlank(),
          instagramBusinessAccount == null ? null : instagramBusinessAccount.id());
    }
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record RawInstagramBusinessAccount(String id) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record PageAccountPage(List<PageAccount> data, Paging paging) {
    public PageAccountPage {
      data = data == null ? List.of() : List.copyOf(data);
    }

    public String afterCursor() {
      return paging == null || paging.cursors() == null ? null : paging.cursors().after();
    }

    public String nextPageUrl() {
      return paging == null ? null : paging.next();
    }
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record PageAccount(
      String id,
      String name,
      String category,
      boolean accessTokenAvailable,
      String instagramAccountId) {
    public String linkedInstagramAccountId() {
      return instagramAccountId;
    }

    public String instagramBusinessAccountId() {
      return instagramAccountId;
    }
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record FacebookPage(String id, String name, String category) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record AccountsResponse(List<Account> data) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record Account(String id) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record PagePostsResponse(List<PagePost> data) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record PagePost(
      String id,
      String message,
      @JsonProperty("created_time") String createdTime,
      @JsonProperty("permalink_url") String permalinkUrl) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record InstagramAccount(
      String id,
      String username,
      @JsonProperty("account_type") String accountType,
      @JsonProperty("media_count") Long mediaCount,
      @JsonProperty("profile_picture_url") String profilePictureUrl) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record InstagramMedia(
      String id,
      @JsonProperty("media_type") String mediaType,
      @JsonProperty("media_product_type") String mediaProductType,
      String caption,
      String permalink,
      String timestamp,
      @JsonProperty("thumbnail_url") String thumbnailUrl,
      @JsonProperty("media_url") String mediaUrl) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record InstagramMediaPage(List<InstagramMedia> data, Paging paging) {
    public String afterCursor() {
      return paging == null || paging.cursors() == null ? null : paging.cursors().after();
    }

    public String nextPageUrl() {
      return paging == null ? null : paging.next();
    }
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record Paging(Cursors cursors, String next, String previous) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record Cursors(String before, String after) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record InstagramInsightsResponse(List<InsightMetric> data) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record InsightMetric(
      String name, String title, String description, List<InsightValue> values, Long value) {
    public Long resolveValue() {
      if (values != null && !values.isEmpty() && values.get(0) != null) {
        return values.get(0).value();
      }
      return value;
    }
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  public record InsightValue(Long value, @JsonProperty("end_time") String endTime) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record MetaErrorEnvelope(MetaError error) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record MetaError(
      String message,
      String type,
      Integer code,
      @JsonProperty("error_subcode") Integer errorSubcode,
      @JsonProperty("fbtrace_id") String fbTraceId) {}
}
