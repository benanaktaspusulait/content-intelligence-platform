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
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/**
 * YouTube Data API v3 client for fetching video metrics.
 *
 * <p>Uses YouTube Data API v3: - GET /youtube/v3/videos: Get video details and statistics - Parts:
 * statistics, contentDetails - Fields: viewCount, likeCount, commentCount, averageViewDuration,
 * averageViewPercentage
 *
 * <p>API Documentation: https://developers.google.com/youtube/v3/docs/videos/list
 *
 * <p>Note: YouTube Analytics API can provide more detailed metrics but requires additional setup.
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class YouTubeMetricsClient implements PlatformMetricsClient {

  private static final String API_BASE_URL = "https://www.googleapis.com/youtube/v3";
  private static final String VIDEOS_URL = API_BASE_URL + "/videos";

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public VideoMetrics fetchMetrics(String platformVideoId) throws IOException {
    log.info("Fetching YouTube metrics: videoId={}", platformVideoId);

    String accessToken = credentialManager.getActiveAccessToken(PlatformType.YOUTUBE);

    RestClient restClient = restClientBuilder.build();

    String url = VIDEOS_URL + "?part=statistics" + "&id=" + platformVideoId;

    String response =
        restClient
            .get()
            .uri(url)
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);

    if (json.has("error")) {
      throw new IOException(
          "YouTube metrics fetch failed: " + json.get("error").get("message").asText());
    }

    if (!json.has("items") || json.get("items").isEmpty()) {
      throw new IOException("Video not found: " + platformVideoId);
    }

    JsonNode video = json.get("items").get(0);
    JsonNode statistics = video.get("statistics");
    // Extract metrics
    long views = statistics.has("viewCount") ? statistics.get("viewCount").asLong() : 0;
    long likes = statistics.has("likeCount") ? statistics.get("likeCount").asLong() : 0;
    long comments = statistics.has("commentCount") ? statistics.get("commentCount").asLong() : 0;

    VideoMetrics metrics =
        VideoMetrics.builder()
            .platform(PlatformType.YOUTUBE)
            .platformVideoId(platformVideoId)
            .views(views)
            .likes(likes)
            .comments(comments)
            .shares(0L)
            .saves(0L) // YouTube doesn't provide saves
            .completionRate(null)
            .avgWatchTimeSeconds(null)
            .impressions(null)
            .reach(null)
            .collectedAt(Instant.now())
            .build();

    log.info(
        "YouTube metrics fetched: videoId={}, views={}, likes={}", platformVideoId, views, likes);

    return metrics;
  }

  @Override
  public PlatformType getPlatform() {
    return PlatformType.YOUTUBE;
  }
}
