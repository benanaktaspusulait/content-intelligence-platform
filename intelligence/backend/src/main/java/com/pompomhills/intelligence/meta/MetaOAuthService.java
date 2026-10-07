package com.pompomhills.intelligence.meta;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.time.Clock;
import java.time.Instant;
import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

/** Provider-facing Meta OAuth exchange for the read-only analytics connection. */
@Service
public class MetaOAuthService implements MetaProviderAdapter {
  private static final String AUTH_DIALOG_URL = "https://www.facebook.com/v26.0/dialog/oauth";
  private static final List<String> REQUESTED_SCOPES =
      List.of("pages_show_list", "pages_read_engagement", "instagram_basic", "instagram_manage_insights");

  private final MetaOAuthProperties oauthProperties;
  private final MetaReadProperties readProperties;
  private final RestClient restClient;
  private final Clock clock;

  @Autowired
  public MetaOAuthService(
      MetaOAuthProperties oauthProperties,
      MetaReadProperties readProperties,
      MetaOAuthTokenStore ignoredLegacyTokenStore,
      @Qualifier("metaReadRestClient") RestClient restClient,
      Clock clock) {
    this.oauthProperties = oauthProperties;
    this.readProperties = readProperties;
    this.restClient = restClient;
    this.clock = clock;
  }

  /** Compatibility constructor for isolated provider tests. */
  public MetaOAuthService(
      MetaOAuthProperties oauthProperties,
      MetaReadProperties readProperties,
      MetaOAuthTokenStore ignoredLegacyTokenStore,
      RestClient restClient) {
    this(oauthProperties, readProperties, ignoredLegacyTokenStore, restClient, Clock.systemUTC());
  }

  public boolean isConfigured() {
    return oauthProperties.isConfigured();
  }

  /** Builds the read-only Meta authorization URL. No publish or comment-write scope is requested. */
  public String buildAuthorizationUrl(String state) {
    return UriComponentsBuilder.fromUriString(AUTH_DIALOG_URL)
        .queryParam("client_id", oauthProperties.appId())
        .queryParam("redirect_uri", oauthProperties.redirectUri())
        .queryParam("state", state)
        .queryParam("response_type", "code")
        .queryParam("scope", String.join(",", REQUESTED_SCOPES))
        .build()
        .toUriString();
  }

  public List<String> requestedScopes() {
    return REQUESTED_SCOPES;
  }

  /**
   * Exchanges and validates an authorization code without placing provider tokens in process-local
   * state. The lifecycle service is the only caller that persists the returned internal result.
   */
  @Override
  public AuthorizationResult authorize(String code) {
    if (code == null || code.isBlank()) {
      throw genericOAuthError();
    }
    TokenResponse response = exchangeCodeForUserToken(code);
    String userAccessToken = response.accessToken();
    AccountsResponse accounts = fetchManagedAccounts(userAccessToken);
    String pageId = resolveManagedPageId(accounts);
    if (pageId == null) {
      throw new MetaOAuthException(
          "The authenticated user does not manage an available Facebook Page.");
    }

    PageTokenResponse pageDetails = fetchPageDetails(pageId, userAccessToken);
    String pageAccessToken = pageDetails == null ? null : pageDetails.accessToken();
    if (pageAccessToken == null || pageAccessToken.isBlank()) {
      throw new MetaOAuthException("A Page access token could not be obtained.");
    }

    String configuredInstagramId =
        readProperties.diagnosticOverridesEnabled()
            ? blankToNull(readProperties.instagramAccountId())
            : null;
    String linkedInstagramId =
        pageDetails == null || pageDetails.instagramBusinessAccount() == null
            ? null
            : blankToNull(pageDetails.instagramBusinessAccount().id());
    String instagramAccountId =
        configuredInstagramId == null ? linkedInstagramId : configuredInstagramId;

    Instant issuedAt = clock.instant();
    return new AuthorizationResult(
        response.userId(),
        pageId,
        instagramAccountId,
        null,
        userAccessToken,
        pageAccessToken,
        null,
        grantedScopes(response.scope()),
        issuedAt,
        expiresAt(response, issuedAt),
        true,
        false,
        null);
  }

  /** Compatibility result for callers that only need a sanitized success/failure outcome. */
  public OAuthCompletionResult completeAuthorization(String code) {
    try {
      authorize(code);
      return OAuthCompletionResult.succeeded();
    } catch (MetaOAuthException error) {
      return OAuthCompletionResult.failure(
          MetaErrorSanitizer.sanitize(
              error.getMessage(),
              "The Meta authorization request could not be completed.",
              oauthProperties.appSecret()));
    }
  }

  private String resolveManagedPageId(AccountsResponse accounts) {
    if (accounts == null || accounts.data() == null) {
      return null;
    }
    String configuredPageId =
        readProperties.diagnosticOverridesEnabled()
            ? blankToNull(readProperties.pageId())
            : null;
    return accounts.data().stream()
        .filter(account -> account != null && account.id() != null && !account.id().isBlank())
        .map(Account::id)
        .filter(
            pageId -> configuredPageId == null || configuredPageId.equals(pageId.trim()))
        .map(String::trim)
        .findFirst()
        .orElse(null);
  }

  private TokenResponse exchangeCodeForUserToken(String code) {
    TokenResponse response =
        restClient
            .get()
            .uri(
                uriBuilder ->
                    uriBuilder
                        .pathSegment(readProperties.apiVersion(), "oauth", "access_token")
                        .queryParam("client_id", oauthProperties.appId())
                        .queryParam("client_secret", oauthProperties.appSecret())
                        .queryParam("redirect_uri", oauthProperties.redirectUri())
                        .queryParam("code", code)
                        .build())
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, resp) -> {
                  throw genericOAuthError();
                })
            .body(TokenResponse.class);
    if (response == null || response.accessToken() == null || response.accessToken().isBlank()) {
      throw genericOAuthError();
    }
    return response;
  }

  private AccountsResponse fetchManagedAccounts(String userAccessToken) {
    AccountsResponse response =
        restClient
            .get()
            .uri(
                uriBuilder ->
                    uriBuilder
                        .pathSegment(readProperties.apiVersion(), "me", "accounts")
                        .queryParam("fields", "id")
                        .queryParam("limit", 200)
                        .build())
            .headers(headers -> headers.set(HttpHeaders.AUTHORIZATION, "Bearer " + userAccessToken))
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, resp) -> {
                  throw genericOAuthError();
                })
            .body(AccountsResponse.class);
    return response == null ? new AccountsResponse(List.of()) : response;
  }

  private PageTokenResponse fetchPageDetails(String pageId, String userAccessToken) {
    PageTokenResponse response =
        restClient
            .get()
            .uri(
                uriBuilder ->
                    uriBuilder
                        .pathSegment(readProperties.apiVersion(), pageId)
                        .queryParam("fields", "access_token,instagram_business_account")
                        .build())
            .headers(headers -> headers.set(HttpHeaders.AUTHORIZATION, "Bearer " + userAccessToken))
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, resp) -> {
                  throw genericOAuthError();
                })
            .body(PageTokenResponse.class);
    return response;
  }

  private Set<String> grantedScopes(String scope) {
    if (scope == null || scope.isBlank()) {
      return Set.of();
    }
    LinkedHashSet<String> scopes = new LinkedHashSet<>();
    Arrays.stream(scope.split("[,\\s]+"))
        .map(String::trim)
        .filter(value -> !value.isBlank())
        .forEach(scopes::add);
    return Set.copyOf(scopes);
  }

  private Instant expiresAt(TokenResponse response, Instant issuedAt) {
    if (response.expiresIn() != null && response.expiresIn() > 0) {
      return issuedAt.plusSeconds(response.expiresIn());
    }
    if (response.dataAccessExpirationTime() != null && response.dataAccessExpirationTime() > 0) {
      return Instant.ofEpochSecond(response.dataAccessExpirationTime());
    }
    return null;
  }

  private static String blankToNull(String value) {
    return value == null || value.isBlank() ? null : value.trim();
  }

  private MetaOAuthException genericOAuthError() {
    return new MetaOAuthException("The Meta authorization request could not be completed.");
  }

  public record OAuthCompletionResult(boolean success, String failureReason) {
    public static OAuthCompletionResult succeeded() {
      return new OAuthCompletionResult(true, null);
    }

    public static OAuthCompletionResult failure(String reason) {
      return new OAuthCompletionResult(false, reason);
    }
  }

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record TokenResponse(
      @JsonProperty("access_token") String accessToken,
      @JsonProperty("expires_in") Long expiresIn,
      @JsonProperty("data_access_expiration_time") Long dataAccessExpirationTime,
      @JsonProperty("user_id") String userId,
      String scope) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record AccountsResponse(List<Account> data) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record Account(String id) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record PageTokenResponse(
      @JsonProperty("access_token") String accessToken,
      @JsonProperty("instagram_business_account") InstagramBusinessAccount instagramBusinessAccount) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record InstagramBusinessAccount(String id) {}
}
