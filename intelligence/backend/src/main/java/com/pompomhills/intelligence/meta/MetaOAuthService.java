package com.pompomhills.intelligence.meta;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

/**
 * Orchestrates the Meta OAuth authorization-code flow for read-only analytics access.
 *
 * <p>Only four read-only scopes are requested: pages_show_list, pages_read_engagement,
 * instagram_basic, instagram_manage_insights. The app secret and all tokens are used strictly
 * server-side; they are never returned to the browser, logged, or placed in any DTO.
 */
@Service
public class MetaOAuthService {
  private static final String AUTH_DIALOG_URL = "https://www.facebook.com/v26.0/dialog/oauth";
  private static final String REQUESTED_SCOPES =
      "pages_show_list,pages_read_engagement,instagram_basic,instagram_manage_insights";

  private final MetaOAuthProperties oauthProperties;
  private final MetaReadProperties readProperties;
  private final MetaOAuthTokenStore tokenStore;
  private final RestClient restClient;

  public MetaOAuthService(
      MetaOAuthProperties oauthProperties,
      MetaReadProperties readProperties,
      MetaOAuthTokenStore tokenStore,
      @Qualifier("metaReadRestClient") RestClient restClient) {
    this.oauthProperties = oauthProperties;
    this.readProperties = readProperties;
    this.tokenStore = tokenStore;
    this.restClient = restClient;
  }

  public boolean isConfigured() {
    return oauthProperties.isConfigured();
  }

  /** Builds the real Meta/Facebook authorization dialog URL for the given CSRF state. */
  public String buildAuthorizationUrl(String state) {
    return UriComponentsBuilder.fromUriString(AUTH_DIALOG_URL)
        .queryParam("client_id", oauthProperties.appId())
        .queryParam("redirect_uri", oauthProperties.redirectUri())
        .queryParam("state", state)
        .queryParam("response_type", "code")
        .queryParam("scope", REQUESTED_SCOPES)
        .build()
        .toUriString();
  }

  /**
   * Completes the OAuth flow for an authorization code already validated against CSRF state by the
   * caller: exchanges the code for a user token (server-side), verifies the configured Page is
   * managed by this user via pages_show_list, obtains the Page access token, and resolves the
   * linked Instagram Professional account id from the Page. The derived Page token is stored in
   * {@link MetaOAuthTokenStore}; nothing is returned to callers beyond a success outcome.
   */
  public OAuthCompletionResult completeAuthorization(String code) {
    String userAccessToken = exchangeCodeForUserToken(code);
    AccountsResponse accounts = fetchManagedAccounts(userAccessToken);
    String configuredPageId = readProperties.pageId();
    boolean pageManaged =
        accounts.data() != null
            && accounts.data().stream()
                .anyMatch(account -> account != null && configuredPageId.equals(account.id()));
    if (!pageManaged) {
      return OAuthCompletionResult.failure(
          "The authenticated user does not manage the configured Facebook Page.");
    }

    String pageAccessToken = fetchPageAccessToken(configuredPageId, userAccessToken);
    if (pageAccessToken == null || pageAccessToken.isBlank()) {
      return OAuthCompletionResult.failure("A Page access token could not be obtained.");
    }

    tokenStore.setUserAccessToken(userAccessToken);
    tokenStore.setPageAccessToken(pageAccessToken);
    return OAuthCompletionResult.succeeded();
  }

  private String exchangeCodeForUserToken(String code) {
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
    return response.accessToken();
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
                        .queryParam("access_token", userAccessToken)
                        .build())
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, resp) -> {
                  throw genericOAuthError();
                })
            .body(AccountsResponse.class);
    return response == null ? new AccountsResponse(List.of()) : response;
  }

  private String fetchPageAccessToken(String pageId, String userAccessToken) {
    PageTokenResponse response =
        restClient
            .get()
            .uri(
                uriBuilder ->
                    uriBuilder
                        .pathSegment(readProperties.apiVersion(), pageId)
                        .queryParam("fields", "access_token")
                        .queryParam("access_token", userAccessToken)
                        .build())
            .retrieve()
            .onStatus(
                status -> status.isError(),
                (request, resp) -> {
                  throw genericOAuthError();
                })
            .body(PageTokenResponse.class);
    return response == null ? null : response.accessToken();
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
  private record TokenResponse(@JsonProperty("access_token") String accessToken) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record AccountsResponse(List<Account> data) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record Account(String id) {}

  @JsonIgnoreProperties(ignoreUnknown = true)
  private record PageTokenResponse(@JsonProperty("access_token") String accessToken) {}
}
