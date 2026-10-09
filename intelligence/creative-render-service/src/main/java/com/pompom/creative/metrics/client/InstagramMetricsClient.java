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

/**
 * Instagram Graph API client for fetching Reels metrics.
 *
 * <p>Uses Instagram Graph API: - GET /{media-id}/insights: Get media insights - Metrics:
 * impressions, reach, likes, comments, shares, saves, plays, total_interactions
 *
 * <p>API Documentation:
 * https://developers.facebook.com/docs/instagram-api/reference/ig-media/insights
 *
 * <p>Note: Instagram Insights have a 24-48 hour delay for some metrics.
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class InstagramMetricsClient implements PlatformMetricsClient {

  private static final String GRAPH_API_VERSION = "v18.0";
  private static final String GRAPH_API_BASE_URL =
      "https://graph.facebook.com/" + GRAPH_API_VERSION;

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public VideoMetrics fetchMetrics(String platformVideoId) throws IOException {
    log.info("Fetching Instagram metrics: mediaId={}", platformVideoId);

    String accessToken = credentialManager.getActiveAccessToken(PlatformType.INSTAGRAM);

    RestClient restClient = restClientBuilder.build();

    // First get basic media info
    String mediaUrl =
        GRAPH_API_BASE_URL
            + "/"
            + platformVideoId
            + "?fields=like_count,comments_count,media_type,timestamp"
            ;

    String mediaResponse =
        restClient.get().uri(mediaUrl).headers(headers -> headers.setBearerAuth(accessToken))
            .retrieve().body(String.class);

    JsonNode mediaJson = objectMapper.readTree(mediaResponse);

    if (mediaJson.has("error")) {
      throw new IOException(
          "Instagram media fetch failed: " + mediaJson.get("error").get("message").asText());
    }

    long likes = mediaJson.has("like_count") ? mediaJson.get("like_count").asLong() : 0;
    long comments = mediaJson.has("comments_count") ? mediaJson.get("comments_count").asLong() : 0;

    // Get insights (impressions, reach, saves, plays)
    String insightsUrl =
        GRAPH_API_BASE_URL
            + "/"
            + platformVideoId
            + "/insights"
            + "?metric=impressions,reach,saves,plays,shares,total_interactions"
            ;

    String insightsResponse =
        restClient.get().uri(insightsUrl).headers(headers -> headers.setBearerAuth(accessToken))
            .retrieve().body(String.class);

    JsonNode insightsJson = objectMapper.readTree(insightsResponse);

    // Parse insights data
    long impressions = 0;
    long reach = 0;
    long saves = 0;
    long plays = 0; // Instagram's "views"
    long shares = 0;

    if (insightsJson.has("data")) {
      for (JsonNode metric : insightsJson.get("data")) {
        String name = metric.get("name").asText();
        long value =
            metric.has("values") && !metric.get("values").isEmpty()
                ? metric.get("values").get(0).get("value").asLong()
                : 0;

        switch (name) {
          case "impressions" -> impressions = value;
          case "reach" -> reach = value;
          case "saves" -> saves = value;
          case "plays" -> plays = value;
          case "shares" -> shares = value;
        }
      }
    }

    VideoMetrics metrics =
        VideoMetrics.builder()
            .platform(PlatformType.INSTAGRAM)
            .platformVideoId(platformVideoId)
            .views(plays) // Instagram calls them "plays"
            .likes(likes)
            .comments(comments)
            .shares(shares)
            .saves(saves)
            .completionRate(null)
            .avgWatchTimeSeconds(null)
            .impressions(impressions == 0 ? null : impressions)
            .reach(reach == 0 ? null : reach)
            .collectedAt(Instant.now())
            .build();

    log.info(
        "Instagram metrics fetched: mediaId={}, plays={}, likes={}", platformVideoId, plays, likes);

    return metrics;
  }

  @Override
  public PlatformType getPlatform() {
    return PlatformType.INSTAGRAM;
  }
}
