package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class MetaGraphReadClientTest {

  @Test
  void durableConnectionSuppliesReadTokenAndTargetsWithoutStaticAccessToken() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaReadProperties properties =
        new MetaReadProperties(
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
            "owner-1");
    MetaTokenEncryptionService encryption = new MetaTokenEncryptionService("test-key");
    MetaConnectionEntity entity =
        MetaConnectionEntity.connected(
            "owner-1",
            new MetaProviderAdapter.AuthorizationResult(
                "meta-user-1",
                "page-1",
                "instagram-1",
                "PROFESSIONAL",
                "user-secret",
                "page-secret",
                null,
                Set.of("pages_read_engagement", "instagram_basic", "instagram_manage_insights"),
                Instant.parse("2026-10-01T12:00:00Z"),
                Instant.parse("2026-10-01T13:00:00Z"),
                true,
                true,
                null),
            encryption,
            java.util.Map.of());
    MetaConnectionRepository repository = org.mockito.Mockito.mock(MetaConnectionRepository.class);
    when(repository.findTopByOwnerKeyOrderByUpdatedAtDesc("owner-1"))
        .thenReturn(Optional.of(entity));
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(),
            new ObjectMapper(),
            properties,
            new MetaOAuthTokenStore(),
            repository,
            encryption,
            Clock.fixed(Instant.parse("2026-10-01T12:30:00Z"), ZoneOffset.UTC));

    server
        .expect(requestTo("https://graph.facebook.com/v26.0/page-1?fields=id,name,category"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer page-secret"))
        .andRespond(
            withSuccess(
                "{\"id\":\"page-1\",\"name\":\"Pompom Hills\"}",
                MediaType.APPLICATION_JSON));

    assertThat(client.getFacebookPage().id()).isEqualTo("page-1");
    assertThat(client.hasEffectiveAccessToken()).isTrue();
    server.verify();
  }

  @Test
  void revokedDurableConnectionDoesNotFallBackToStaticCredentials() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaReadProperties properties = properties("legacy-user-token");
    MetaTokenEncryptionService encryption = new MetaTokenEncryptionService("test-key");
    MetaConnectionEntity entity =
        MetaConnectionEntity.connected(
            "default",
            new MetaProviderAdapter.AuthorizationResult(
                "meta-user-1",
                "durable-page",
                "durable-instagram",
                "PROFESSIONAL",
                "user-secret",
                "page-secret",
                null,
                Set.of("pages_read_engagement"),
                Instant.parse("2026-10-01T12:00:00Z"),
                Instant.parse("2026-10-01T13:00:00Z"),
                true,
                true,
                null),
            encryption,
            java.util.Map.of());
    entity.setStatus(MetaConnectionStatus.REVOKED);
    MetaConnectionRepository repository = org.mockito.Mockito.mock(MetaConnectionRepository.class);
    when(repository.findTopByOwnerKeyOrderByUpdatedAtDesc("default"))
        .thenReturn(Optional.of(entity));
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(),
            new ObjectMapper(),
            properties,
            new MetaOAuthTokenStore(),
            repository,
            encryption,
            Clock.fixed(Instant.parse("2026-10-01T12:30:00Z"), ZoneOffset.UTC));

    assertThat(client.hasEffectiveAccessToken()).isFalse();
    assertThat(client.hasEffectivePageTarget()).isFalse();
    server.verify();
  }

  @Test
  void verifiesConfiguredPageWithGetMeAccountsAndRequestsIdsOnly() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(),
            new ObjectMapper(),
            properties("user-token"),
            new MetaOAuthTokenStore());

    server
        .expect(requestTo("https://graph.facebook.com/v26.0/me/accounts?fields=id&limit=200"))
        .andExpect(method(HttpMethod.GET))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer user-token"))
        .andRespond(
            withSuccess(
                "{\"data\":[{\"id\":\"other-page\"},{\"id\":\"123456\"}]}",
                MediaType.APPLICATION_JSON));

    assertThat(client.verifyConfiguredPageManaged())
        .isEqualTo(MetaConnectionResponse.PageManagementVerification.VERIFIED);
    server.verify();
  }

  @Test
  void returnsNotVerifiedWhenConfiguredPageIsAbsent() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(),
            new ObjectMapper(),
            properties("user-token"),
            new MetaOAuthTokenStore());

    server
        .expect(requestTo("https://graph.facebook.com/v26.0/me/accounts?fields=id&limit=200"))
        .andRespond(
            withSuccess("{\"data\":[{\"id\":\"other-page\"}]}", MediaType.APPLICATION_JSON));

    assertThat(client.verifyConfiguredPageManaged())
        .isEqualTo(MetaConnectionResponse.PageManagementVerification.NOT_VERIFIED);
    server.verify();
  }

  @Test
  void doesNotCallMetaWhenUserTokenIsUnavailable() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(), new ObjectMapper(), properties(""), new MetaOAuthTokenStore());

    assertThat(client.verifyConfiguredPageManaged())
        .isEqualTo(MetaConnectionResponse.PageManagementVerification.UNAVAILABLE);
    server.verify();
  }

  @Test
  void verificationPrefersFreshOAuthUserTokenOverStaleConfiguredToken() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaOAuthTokenStore tokenStore = new MetaOAuthTokenStore();
    tokenStore.setUserAccessToken("fresh-oauth-user-token");
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(), new ObjectMapper(), properties("stale-env-user-token"), tokenStore);

    server
        .expect(requestTo("https://graph.facebook.com/v26.0/me/accounts?fields=id&limit=200"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer fresh-oauth-user-token"))
        .andRespond(withSuccess("{\"data\":[{\"id\":\"123456\"}]}", MediaType.APPLICATION_JSON));

    assertThat(client.verifyConfiguredPageManaged())
        .isEqualTo(MetaConnectionResponse.PageManagementVerification.VERIFIED);
    server.verify();
  }

  @Test
  void contentCallsUseFreshOAuthPageTokenOverStaleConfiguredToken() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaOAuthTokenStore tokenStore = new MetaOAuthTokenStore();
    tokenStore.setPageAccessToken("fresh-oauth-page-token");
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(), new ObjectMapper(), properties("unused"), tokenStore);

    server
        .expect(requestTo("https://graph.facebook.com/v26.0/123456?fields=id,name,category"))
        .andExpect(header(HttpHeaders.AUTHORIZATION, "Bearer fresh-oauth-page-token"))
        .andRespond(
            withSuccess(
                "{\"id\":\"123456\",\"name\":\"Pompom Hills\",\"category\":\"Education\"}",
                MediaType.APPLICATION_JSON));

    MetaGraphReadClient.FacebookPage page = client.getFacebookPage();

    assertThat(page.name()).isEqualTo("Pompom Hills");
    server.verify();
  }

  @Test
  void noOAuthTokenValueEverAppearsInASanitizedErrorMessage() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaOAuthTokenStore tokenStore = new MetaOAuthTokenStore();
    tokenStore.setUserAccessToken("secret-oauth-user-token");
    tokenStore.setPageAccessToken("secret-oauth-page-token");
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(), new ObjectMapper(), properties("secret-oauth-user-token"), tokenStore);

    server
        .expect(requestTo("https://graph.facebook.com/v26.0/123456?fields=id,name,category"))
        .andRespond(
            withStatusAndBody(
                "{\"error\":{\"message\":\"Bearer secret-oauth-page-token for user "
                    + "secret-oauth-user-token is invalid\",\"type\":\"OAuthException\","
                    + "\"code\":190}}"));

    MetaGraphException error =
        org.junit.jupiter.api.Assertions.assertThrows(
            MetaGraphException.class, client::getFacebookPage);

    assertThat(error.getMessage()).doesNotContain("secret-oauth-page-token");
    assertThat(error.getMessage()).doesNotContain("secret-oauth-user-token");
    assertThat(error.getMessage()).contains("[REDACTED]");
    server.verify();
  }

  private org.springframework.test.web.client.ResponseCreator withStatusAndBody(String body) {
    return org.springframework.test.web.client.response.MockRestResponseCreators.withStatus(
            org.springframework.http.HttpStatus.BAD_REQUEST)
        .body(body)
        .contentType(MediaType.APPLICATION_JSON);
  }

  private MetaReadProperties properties(String userAccessToken) {
    return new MetaReadProperties(
        true,
        "v26.0",
        "123456",
        "987654",
        "page-token",
        userAccessToken,
        Duration.ofSeconds(5),
        Duration.ofSeconds(15));
  }
}
