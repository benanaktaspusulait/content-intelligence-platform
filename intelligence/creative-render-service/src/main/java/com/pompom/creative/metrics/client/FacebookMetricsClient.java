package com.pompom.creative.metrics.client;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.service.CredentialManager;
import java.io.IOException;
import java.time.Instant;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/** Read-only Facebook Page video metrics client. */
@Component
@Slf4j
@RequiredArgsConstructor
public class FacebookMetricsClient implements PlatformMetricsClient {

  private static final String GRAPH_API_VERSION = "v18.0";
  private static final String GRAPH_API_BASE_URL =
      "https://graph.facebook.com/" + GRAPH_API_VERSION;

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public VideoMetrics fetchMetrics(String platformVideoId) throws IOException {
    String token = credentialManager.getActiveAccessToken(PlatformType.FACEBOOK);
    String url =
        GRAPH_API_BASE_URL
            + "/"
            + platformVideoId
            + "?fields=id,views,likes.summary(true),comments.summary(true),shares"
            + "&access_token="
            + token;
    String body = restClientBuilder.build().get().uri(url).retrieve().body(String.class);
    JsonNode json = objectMapper.readTree(body);
    if (json.has("error")) {
      throw new IOException(
          "Facebook video metrics failed: " + json.get("error").path("message").asText());
    }
    return VideoMetrics.builder()
        .platform(PlatformType.FACEBOOK)
        .platformVideoId(platformVideoId)
        .views(optionalLong(json, "views"))
        .likes(summaryCount(json.path("likes")))
        .comments(summaryCount(json.path("comments")))
        .shares(summaryCount(json.path("shares")))
        .impressions(optionalLong(json, "impressions"))
        .reach(optionalLong(json, "reach"))
        .collectedAt(Instant.now())
        .build();
  }

  @Override
  public PlatformType getPlatform() {
    return PlatformType.FACEBOOK;
  }

  private Long optionalLong(JsonNode object, String field) {
    JsonNode value = object.get(field);
    return value == null || value.isNull() ? null : value.asLong();
  }

  private Long summaryCount(JsonNode object) {
    JsonNode summary = object.path("summary").path("total_count");
    if (!summary.isMissingNode() && !summary.isNull()) return summary.asLong();
    JsonNode count = object.path("count");
    return count.isMissingNode() || count.isNull() ? null : count.asLong();
  }
}
