package com.pompom.creative.oauth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.dto.OAuthToken;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestClient;

@ExtendWith(MockitoExtension.class)
class OAuthServiceTest {

  private OAuthService oauthService;
  private ObjectMapper objectMapper;

  @BeforeEach
  void setUp() {
    RestClient.Builder restClientBuilder = RestClient.builder();
    objectMapper = new ObjectMapper();
    oauthService = new OAuthService(restClientBuilder, objectMapper);

    // Set test credentials via reflection
    ReflectionTestUtils.setField(
        oauthService, "callbackUrl", "http://localhost:8080/api/v1/oauth/callback");
    ReflectionTestUtils.setField(oauthService, "tiktokClientId", "test-tiktok-client-id");
    ReflectionTestUtils.setField(oauthService, "tiktokClientSecret", "test-tiktok-secret");
    ReflectionTestUtils.setField(oauthService, "youtubeClientId", "test-youtube-client-id");
    ReflectionTestUtils.setField(oauthService, "youtubeClientSecret", "test-youtube-secret");
  }

  @Test
  void generateAuthorizationUrl_tiktok_containsRequiredParams() {
    // Given
    String state = "test-state-123";

    // When
    String authUrl = oauthService.generateAuthorizationUrl(PlatformType.TIKTOK, state);

    // Then
    assertThat(authUrl).contains("https://www.tiktok.com/v2/auth/authorize/");
    assertThat(authUrl).contains("client_id=test-tiktok-client-id");
    assertThat(authUrl).contains("redirect_uri=http://localhost:8080/api/v1/oauth/callback");
    assertThat(authUrl).contains("response_type=code");
    assertThat(authUrl).contains("state=test-state-123");
    assertThat(authUrl).contains("scope=");
  }

  @Test
  void generateAuthorizationUrl_youtube_includesOfflineAccess() {
    // Given
    String state = "test-state-456";

    // When
    String authUrl = oauthService.generateAuthorizationUrl(PlatformType.YOUTUBE, state);

    // Then
    assertThat(authUrl).contains("https://accounts.google.com/o/oauth2/v2/auth");
    assertThat(authUrl).contains("client_id=test-youtube-client-id");
    assertThat(authUrl).contains("access_type=offline");
    assertThat(authUrl).contains("prompt=consent");
  }

  @Test
  void isPlatformConfigured_withCredentials_returnsTrue() {
    // When
    boolean tiktokConfigured = oauthService.isPlatformConfigured(PlatformType.TIKTOK);
    boolean youtubeConfigured = oauthService.isPlatformConfigured(PlatformType.YOUTUBE);

    // Then
    assertThat(tiktokConfigured).isTrue();
    assertThat(youtubeConfigured).isTrue();
  }

  @Test
  void isPlatformConfigured_withoutCredentials_returnsFalse() {
    // Given: Facebook not configured
    ReflectionTestUtils.setField(oauthService, "facebookAppId", "");
    ReflectionTestUtils.setField(oauthService, "facebookAppSecret", "");

    // When
    boolean facebookConfigured = oauthService.isPlatformConfigured(PlatformType.FACEBOOK);

    // Then
    assertThat(facebookConfigured).isFalse();
  }

  @Test
  void metaPublicationOAuthFailsClosedWhilePublishingIsDisabled() {
    ReflectionTestUtils.setField(oauthService, "facebookAppId", "facebook-app");
    ReflectionTestUtils.setField(oauthService, "facebookAppSecret", "facebook-secret");
    ReflectionTestUtils.setField(oauthService, "metaPublishEnabled", false);

    assertThat(oauthService.isMetaPublicationEnabled()).isFalse();
    assertThat(oauthService.isPlatformConfigured(PlatformType.FACEBOOK)).isFalse();
    assertThatThrownBy(
            () -> oauthService.generateAuthorizationUrl(PlatformType.FACEBOOK, "state"))
        .isInstanceOf(IllegalStateException.class)
        .hasMessage("Meta publication OAuth is disabled.");
  }

  @Test
  void oauthToken_isExpired_checksCorrectly() {
    // Given: Token that expired 1 hour ago
    OAuthToken expiredToken =
        OAuthToken.builder()
            .accessToken("test-token")
            .expiresAt(java.time.Instant.now().minusSeconds(3600))
            .build();

    // Given: Token that expires in 1 hour
    OAuthToken validToken =
        OAuthToken.builder()
            .accessToken("test-token")
            .expiresAt(java.time.Instant.now().plusSeconds(3600))
            .build();

    // Then
    assertThat(expiredToken.isExpired()).isTrue();
    assertThat(validToken.isExpired()).isFalse();
  }

  @Test
  void oauthToken_willExpireSoon_checksWithin5Minutes() {
    // Given: Token that expires in 2 minutes
    OAuthToken soonToExpire =
        OAuthToken.builder()
            .accessToken("test-token")
            .expiresAt(java.time.Instant.now().plusSeconds(120))
            .build();

    // Given: Token that expires in 10 minutes
    OAuthToken notSoonToExpire =
        OAuthToken.builder()
            .accessToken("test-token")
            .expiresAt(java.time.Instant.now().plusSeconds(600))
            .build();

    // Then
    assertThat(soonToExpire.willExpireSoon()).isTrue();
    assertThat(notSoonToExpire.willExpireSoon()).isFalse();
  }
}
