package com.pompom.creative.oauth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.dto.OAuthToken;
import java.io.IOException;
import java.time.Instant;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.util.UriComponentsBuilder;

/**
 * OAuth 2.0 service for multi-platform authentication. Supports TikTok, YouTube, Facebook,
 * Instagram.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class OAuthService {

  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Value("${pompom.oauth.callback-url:http://localhost:8080/api/v1/oauth/callback}")
  private String callbackUrl;

  // Platform client credentials (should be in environment variables)
  @Value("${pompom.oauth.tiktok.client-id:}")
  private String tiktokClientId;

  @Value("${pompom.oauth.tiktok.client-secret:}")
  private String tiktokClientSecret;

  @Value("${pompom.oauth.youtube.client-id:}")
  private String youtubeClientId;

  @Value("${pompom.oauth.youtube.client-secret:}")
  private String youtubeClientSecret;

  @Value("${pompom.oauth.facebook.app-id:}")
  private String facebookAppId;

  @Value("${pompom.oauth.facebook.app-secret:}")
  private String facebookAppSecret;

  @Value("${pompom.oauth.instagram.app-id:}")
  private String instagramAppId;

  @Value("${pompom.oauth.instagram.app-secret:}")
  private String instagramAppSecret;

  /**
   * Generate OAuth authorization URL for a platform.
   *
   * @param platform Target platform
   * @param state CSRF token (should be stored in session)
   * @return Authorization URL to redirect user to
   */
  public String generateAuthorizationUrl(PlatformType platform, String state) {
    log.info("Generating authorization URL for platform: {}", platform);

    String clientId = getClientId(platform);
    String scope = getPlatformScope(platform);

    UriComponentsBuilder builder =
        UriComponentsBuilder.fromUriString(platform.getAuthorizationUrl())
            .queryParam("client_id", clientId)
            .queryParam("redirect_uri", callbackUrl)
            .queryParam("response_type", "code")
            .queryParam("scope", scope)
            .queryParam("state", state);

    // Platform-specific parameters
    if (platform == PlatformType.TIKTOK) {
      builder.queryParam("response_type", "code");
    } else if (platform == PlatformType.YOUTUBE) {
      builder.queryParam("access_type", "offline"); // Get refresh token
      builder.queryParam("prompt", "consent");
    }

    String authUrl = builder.build().toUriString();
    log.info("Authorization URL generated: {}", authUrl);

    return authUrl;
  }

  /**
   * Exchange authorization code for access token.
   *
   * @param platform Target platform
   * @param code Authorization code from callback
   * @return OAuth token with access/refresh tokens
   */
  public OAuthToken exchangeCodeForToken(PlatformType platform, String code) {
    log.info("Exchanging authorization code for token: platform={}", platform);

    try {
      String clientId = getClientId(platform);
      String clientSecret = getClientSecret(platform);

      // Build token request
      MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
      params.add("client_id", clientId);
      params.add("client_secret", clientSecret);
      params.add("code", code);
      params.add("grant_type", "authorization_code");
      params.add("redirect_uri", callbackUrl);

      RestClient restClient = restClientBuilder.build();

      String response =
          restClient
              .post()
              .uri(platform.getTokenUrl())
              .contentType(MediaType.APPLICATION_FORM_URLENCODED)
              .body(params)
              .retrieve()
              .body(String.class);

      return parseTokenResponse(platform, response);

    } catch (Exception e) {
      log.error("Failed to exchange code for token: platform={}", platform, e);
      throw new RuntimeException("OAuth token exchange failed: " + e.getMessage(), e);
    }
  }

  /**
   * Refresh an expired access token.
   *
   * @param platform Target platform
   * @param refreshToken Refresh token
   * @return New OAuth token
   */
  public OAuthToken refreshAccessToken(PlatformType platform, String refreshToken) {
    log.info("Refreshing access token: platform={}", platform);

    try {
      String clientId = getClientId(platform);
      String clientSecret = getClientSecret(platform);

      MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
      params.add("client_id", clientId);
      params.add("client_secret", clientSecret);
      params.add("refresh_token", refreshToken);
      params.add("grant_type", "refresh_token");

      RestClient restClient = restClientBuilder.build();

      String response =
          restClient
              .post()
              .uri(platform.getTokenUrl())
              .contentType(MediaType.APPLICATION_FORM_URLENCODED)
              .body(params)
              .retrieve()
              .body(String.class);

      OAuthToken newToken = parseTokenResponse(platform, response);

      // Some platforms don't return new refresh token, keep the old one
      if (newToken.getRefreshToken() == null) {
        newToken.setRefreshToken(refreshToken);
      }

      log.info("Access token refreshed successfully: platform={}", platform);

      return newToken;

    } catch (Exception e) {
      log.error("Failed to refresh access token: platform={}", platform, e);
      throw new RuntimeException("Token refresh failed: " + e.getMessage(), e);
    }
  }

  /** Parse token response from platform. */
  private OAuthToken parseTokenResponse(PlatformType platform, String response) throws IOException {
    JsonNode json = objectMapper.readTree(response);

    OAuthToken.OAuthTokenBuilder builder =
        OAuthToken.builder()
            .accessToken(json.get("access_token").asText())
            .tokenType(json.has("token_type") ? json.get("token_type").asText() : "Bearer");

    if (json.has("refresh_token")) {
      builder.refreshToken(json.get("refresh_token").asText());
    }

    if (json.has("expires_in")) {
      long expiresIn = json.get("expires_in").asLong();
      builder.expiresIn(expiresIn);
      builder.expiresAt(Instant.now().plusSeconds(expiresIn));
    }

    if (json.has("scope")) {
      builder.scope(json.get("scope").asText());
    }

    // Platform-specific user info
    if (platform == PlatformType.TIKTOK && json.has("open_id")) {
      builder.platformUserId(json.get("open_id").asText());
    } else if (platform == PlatformType.YOUTUBE && json.has("id_token")) {
      // Would need to decode JWT to get user ID
      builder.platformUserId("youtube_user");
    }

    return builder.build();
  }

  /** Get client ID for platform. */
  private String getClientId(PlatformType platform) {
    return switch (platform) {
      case TIKTOK -> tiktokClientId;
      case YOUTUBE -> youtubeClientId;
      case FACEBOOK -> facebookAppId;
      case INSTAGRAM -> instagramAppId;
    };
  }

  /** Get client secret for platform. */
  private String getClientSecret(PlatformType platform) {
    return switch (platform) {
      case TIKTOK -> tiktokClientSecret;
      case YOUTUBE -> youtubeClientSecret;
      case FACEBOOK -> facebookAppSecret;
      case INSTAGRAM -> instagramAppSecret;
    };
  }

  /** Get required OAuth scope for platform. */
  private String getPlatformScope(PlatformType platform) {
    return switch (platform) {
      case TIKTOK -> "user.info.basic,video.upload,video.publish";
      case YOUTUBE ->
          "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube";
      case FACEBOOK -> "pages_manage_posts,pages_read_engagement,pages_show_list";
      case INSTAGRAM -> "instagram_basic,instagram_content_publish";
    };
  }

  /** Validate that platform credentials are configured. */
  public boolean isPlatformConfigured(PlatformType platform) {
    String clientId = getClientId(platform);
    String clientSecret = getClientSecret(platform);

    return clientId != null
        && !clientId.isEmpty()
        && clientSecret != null
        && !clientSecret.isEmpty();
  }
}
