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

class MetaGraphPageContractTest {
  @Test
  void readsBoundedFacebookPagePosts() {
    RestClient.Builder builder = RestClient.builder().baseUrl("https://graph.facebook.com");
    MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
    MetaReadProperties properties = new MetaReadProperties(true, "v26.0", "123", "", "token", "", Duration.ofSeconds(5), Duration.ofSeconds(5));
    MetaGraphReadClient client = new MetaGraphReadClient(builder.build(), new ObjectMapper(), properties, new MetaOAuthTokenStore());
    server.expect(requestTo("https://graph.facebook.com/v26.0/123/posts?fields=id,message,created_time,permalink_url&limit=25"))
        .andRespond(withSuccess("{\"data\":[{\"id\":\"p1\",\"message\":\"hello\"}]}", MediaType.APPLICATION_JSON));
    assertThat(client.getPagePosts(100).data()).hasSize(1);
    server.verify();
  }
}
