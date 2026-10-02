package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class MetaGraphReadClientTest {

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
