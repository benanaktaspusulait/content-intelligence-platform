package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class MetaGraphPaginationContractTest {
  @Test
  void boundsManagedPageLimitAndCarriesCursor() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaReadProperties p = new MetaReadProperties(true, "v26.0", "", "", "token", "", Duration.ofSeconds(5), Duration.ofSeconds(5));
    MetaGraphReadClient client = new MetaGraphReadClient(builder.build(), new ObjectMapper(), p, new MetaOAuthTokenStore());
    server.expect(requestTo("https://graph.facebook.com/v26.0/me/accounts?fields=id,name,category,access_token,instagram_business_account&limit=50&after=c1"))
        .andRespond(withSuccess("{\"data\":[],\"paging\":{\"cursors\":{\"after\":\"c2\"}}}", MediaType.APPLICATION_JSON));
    assertThat(client.listManagedPages("user", "c1", 500).paging().cursors().after()).isEqualTo("c2");
    server.verify();
  }

  @Test
  void omitsBlankCursorAndUsesMinimumLimit() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaReadProperties p = new MetaReadProperties(true, "v26.0", "", "", "token", "", Duration.ofSeconds(5), Duration.ofSeconds(5));
    var client = new MetaGraphReadClient(builder.build(), new ObjectMapper(), p, new MetaOAuthTokenStore());
    server.expect(requestTo("https://graph.facebook.com/v26.0/me/accounts?fields=id,name,category,access_token,instagram_business_account&limit=1"))
        .andRespond(withSuccess("{\"data\":[]}", MediaType.APPLICATION_JSON));
    assertThat(client.listManagedPages("user", " ", 0).data()).isEmpty();
    server.verify();
  }

  @Test
  void rejectsBlankUserTokenBeforeNetworkCall() {
    MetaReadProperties p = new MetaReadProperties(true, "v26.0", "", "", "token", "", Duration.ofSeconds(5), Duration.ofSeconds(5));
    var client = new MetaGraphReadClient(RestClient.builder().build(), new ObjectMapper(), p, new MetaOAuthTokenStore());
    org.assertj.core.api.Assertions.assertThatThrownBy(() -> client.listManagedPages(" ", null, 10))
        .isInstanceOf(IllegalArgumentException.class);
  }
}
