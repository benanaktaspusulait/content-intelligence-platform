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

class MetaConnectionServiceTest {

  @Test
  void exposesConfiguredPageManagementVerificationWithoutChangingRequiredPermissions() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaGraphReadClient client =
        new MetaGraphReadClient(
            builder.build(), new ObjectMapper(), properties(), new MetaOAuthTokenStore());

    expectGet(
        server,
        "https://graph.facebook.com/v26.0/123456?fields=id,name,category",
        "Bearer page-token",
        "{\"id\":\"123456\",\"name\":\"Pompom Hills\",\"category\":\"Education\"}");
    expectGet(
        server,
        "https://graph.facebook.com/v26.0/987654?fields=id,username,media_count,profile_picture_url",
        "Bearer page-token",
        "{\"id\":\"987654\",\"username\":\"pompomhills\",\"media_count\":12}");
    expectGet(
        server,
        "https://graph.facebook.com/v26.0/987654/insights?metric=reach&period=day",
        "Bearer page-token",
        "{}");
    expectGet(
        server,
        "https://graph.facebook.com/v26.0/me/accounts?fields=id&limit=200",
        "Bearer user-token",
        "{\"data\":[{\"id\":\"123456\"}]}");

    MetaConnectionService service =
        new MetaConnectionService(
            properties(),
            client,
            Clock.fixed(Instant.parse("2026-10-01T12:00:00Z"), ZoneOffset.UTC));

    MetaConnectionResponse response = service.getConnection();

    assertThat(response.page().name()).isEqualTo("Pompom Hills");
    assertThat(response.pageManagementVerification())
        .isEqualTo(MetaConnectionResponse.PageManagementVerification.VERIFIED);
    assertThat(response.requiredPermissions())
        .extracting(MetaConnectionResponse.PermissionCheck::permission)
        .doesNotContain("pages_show_list");
    assertThat(response.optionalPermissions())
        .singleElement()
        .satisfies(
            check -> {
              assertThat(check.permission()).isEqualTo("pages_show_list");
              assertThat(check.status())
                  .isEqualTo(MetaConnectionResponse.PermissionStatus.AVAILABLE);
            });
    server.verify();
  }

  private void expectGet(
      MockRestServiceServer server, String url, String authorization, String responseBody) {
    server
        .expect(requestTo(url))
        .andExpect(method(HttpMethod.GET))
        .andExpect(header(HttpHeaders.AUTHORIZATION, authorization))
        .andRespond(withSuccess(responseBody, MediaType.APPLICATION_JSON));
  }

  private MetaReadProperties properties() {
    return new MetaReadProperties(
        true,
        "v26.0",
        "123456",
        "987654",
        "page-token",
        "user-token",
        Duration.ofSeconds(5),
        Duration.ofSeconds(15));
  }
}
