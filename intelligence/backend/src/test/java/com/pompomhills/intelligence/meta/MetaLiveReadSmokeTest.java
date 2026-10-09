package com.pompomhills.intelligence.meta;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.web.client.RestClient;

/** Opt-in live read-only check. It never runs unless META_LIVE_TEST=true is explicitly set. */
@EnabledIfEnvironmentVariable(named = "META_LIVE_TEST", matches = "true")
class MetaLiveReadSmokeTest {
  @Test
  void readsConfiguredPageWithoutMutation() {
    String token = required("META_LIVE_ACCESS_TOKEN");
    String pageId = required("META_LIVE_PAGE_ID");
    String version = System.getenv().getOrDefault("META_GRAPH_API_VERSION", "v26.0");
    var properties = new MetaReadProperties(true, version, pageId, "", token, "", Duration.ofSeconds(10), Duration.ofSeconds(10));
    var client = new MetaGraphReadClient(RestClient.builder().baseUrl("https://graph.facebook.com").build(), new ObjectMapper(), properties, new MetaOAuthTokenStore());
    assertThat(client.getFacebookPage().id()).isEqualTo(pageId);
  }

  private String required(String name) {
    String value = System.getenv(name);
    if (value == null || value.isBlank()) throw new IllegalStateException(name + " is required when META_LIVE_TEST=true");
    return value;
  }
}
