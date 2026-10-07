package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class MetaOAuthServiceTest {
  @Test
  void exchangesReadOnlyScopesAndNeverRequestsPublishOrCommentScopes() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaOAuthService service =
        new MetaOAuthService(
            new MetaOAuthProperties("app-id", "app-secret", "https://app.test/meta/callback"),
            properties(),
            new MetaOAuthTokenStore(),
            builder.build(),
            Clock.fixed(Instant.parse("2026-10-01T12:00:00Z"), ZoneOffset.UTC));

    String authorizationUrl = service.buildAuthorizationUrl("csrf-state");
    assertThat(authorizationUrl)
        .contains("pages_show_list")
        .contains("pages_read_engagement")
        .contains("instagram_basic")
        .contains("instagram_manage_insights")
        .doesNotContain("pages_manage_posts", "instagram_content_publish", "comment");

    server
        .expect(
            requestTo(
                "https://graph.facebook.com/v26.0/oauth/access_token?client_id=app-id"
                    + "&client_secret=app-secret&redirect_uri=https://app.test/meta/callback"
                    + "&code=authorization-code"))
        .andExpect(method(HttpMethod.GET))
        .andRespond(
            withSuccess(
                "{\"access_token\":\"user-secret\",\"expires_in\":3600,"
                    + "\"user_id\":\"meta-user-1\","
                    + "\"scope\":\"pages_show_list,pages_read_engagement,instagram_basic,instagram_manage_insights\"}",
                MediaType.APPLICATION_JSON));
    server
        .expect(
            requestTo(
                "https://graph.facebook.com/v26.0/me/accounts?fields=id&limit=200"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer user-secret"))
        .andExpect(method(HttpMethod.GET))
        .andRespond(withSuccess("{\"data\":[{\"id\":\"page-1\"}]}", MediaType.APPLICATION_JSON));
    server
        .expect(
            requestTo(
                "https://graph.facebook.com/v26.0/page-1?fields=access_token,instagram_business_account"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer user-secret"))
        .andExpect(method(HttpMethod.GET))
        .andRespond(
            withSuccess(
                "{\"access_token\":\"page-secret\",\"instagram_business_account\":{\"id\":\"instagram-provider-1\"}}",
                MediaType.APPLICATION_JSON));

    MetaProviderAdapter.AuthorizationResult result = service.authorize("authorization-code");

    assertThat(result.providerUserId()).isEqualTo("meta-user-1");
    assertThat(result.facebookPageId()).isEqualTo("page-1");
    assertThat(result.instagramAccountId()).isEqualTo("instagram-provider-1");
    assertThat(result.instagramAccountEligible()).isFalse();
    assertThat(result.expiresAt()).isEqualTo(Instant.parse("2026-10-01T13:00:00Z"));
    assertThat(result.grantedScopes())
        .containsExactlyInAnyOrder(
            "pages_show_list",
            "pages_read_engagement",
            "instagram_basic",
            "instagram_manage_insights");
    server.verify();
  }

  @Test
  void doesNotTreatMissingProviderScopeMetadataAsAFullGrant() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaOAuthService service =
        new MetaOAuthService(
            new MetaOAuthProperties("app-id", "app-secret", "https://app.test/meta/callback"),
            properties(),
            new MetaOAuthTokenStore(),
            builder.build(),
            Clock.fixed(Instant.parse("2026-10-01T12:00:00Z"), ZoneOffset.UTC));

    server
        .expect(
            requestTo(
                "https://graph.facebook.com/v26.0/oauth/access_token?client_id=app-id"
                    + "&client_secret=app-secret&redirect_uri=https://app.test/meta/callback"
                    + "&code=authorization-code"))
        .andRespond(
            withSuccess(
                "{\"access_token\":\"user-secret\",\"expires_in\":3600,"
                    + "\"user_id\":\"meta-user-1\"}",
                MediaType.APPLICATION_JSON));
    server
        .expect(
            requestTo(
                "https://graph.facebook.com/v26.0/me/accounts?fields=id&limit=200"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer user-secret"))
        .andRespond(withSuccess("{\"data\":[{\"id\":\"page-1\"}]}", MediaType.APPLICATION_JSON));
    server
        .expect(
            requestTo(
                "https://graph.facebook.com/v26.0/page-1?fields=access_token,instagram_business_account"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer user-secret"))
        .andRespond(
            withSuccess(
                "{\"access_token\":\"page-secret\",\"instagram_business_account\":{\"id\":\"instagram-provider-1\"}}",
                MediaType.APPLICATION_JSON));

    MetaProviderAdapter.AuthorizationResult result = service.authorize("authorization-code");

    assertThat(result.grantedScopes()).isEmpty();
    server.verify();
  }

  private MetaReadProperties properties() {
    return new MetaReadProperties(
        true,
        "v26.0",
        "",
        "",
        "",
        "",
        Duration.ofSeconds(5),
        Duration.ofSeconds(15),
        false,
        false,
        "owner-1",
        false);
  }
}
