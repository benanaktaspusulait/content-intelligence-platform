package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.*;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class MetaGraphInsightsContractTest {
  @Test
  void readsObjectInsightsWithBoundedGraphContract() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaReadProperties properties = new MetaReadProperties(true, "v26.0", "", "", "token", "", Duration.ofSeconds(5), Duration.ofSeconds(5));
    MetaGraphReadClient client = new MetaGraphReadClient(builder.build(), new ObjectMapper(), properties, new MetaOAuthTokenStore());
    server.expect(requestTo("https://graph.facebook.com/v26.0/123/insights?metric=reach,views"))
        .andRespond(withSuccess("{\"data\":[{\"name\":\"reach\",\"value\":42}]}", MediaType.APPLICATION_JSON));
    assertThat(client.getObjectInsights("123", "reach,views").data().get(0).resolveValue()).isEqualTo(42L);
    server.verify();
  }
}
