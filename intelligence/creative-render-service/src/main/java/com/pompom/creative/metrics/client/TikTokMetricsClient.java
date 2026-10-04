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
 * TikTok Research API client for fetching video metrics.
 *
 * <p>Uses TikTok Research API: - GET /v2/research/video/query/: Query video details and metrics -
 * Fields: video_id, create_time, view_count, like_count, comment_count, share_count
 *
 * <p>API Documentation: https://developers.tiktok.com/doc/research-api-specs-query-videos
 *
 * <p>Note: TikTok has rate limits: - 1000 requests per day per app - 100 requests per hour per app
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class TikTokMetricsClient implements PlatformMetricsClient {

  private static final String API_BASE_URL = "https://open.tiktokapis.com/v2";
  private static final String VIDEO_QUERY_URL = API_BASE_URL + "/research/video/query/";

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public VideoMetrics fetchMetrics(String platformVideoId) throws IOException {
    log.info("Fetching TikTok metrics: videoId={}", platformVideoId);

    String accessToken = credentialManager.getActiveAccessToken(PlatformType.TIKTOK);

    RestClient restClient = restClientBuilder.build();

    // Build query request
    String requestBody =
        objectMapper.writeValueAsString(
            new java.util.HashMap<String, Object>() {
              {
                put(
                    "query",
                    new java.util.HashMap<String, Object>() {
                      {
                        put(
                            "and",
                            new java.util.ArrayList<>() {
                              {
                                add(
                                    new java.util.HashMap<String, Object>() {
                                      {
                                        put("field_name", "video_id");
                                        put("operation", "EQ");
                                        put("field_values", new String[] {platformVideoId});
                                      }
                                    });
                              }
                            });
                      }
                    });
                put(
                    "fields",
                    new String[] {
                      "id",
                      "create_time",
                      "video_description",
                      "view_count",
                      "like_count",
                      "comment_count",
                      "share_count",
                      "music_id",
                      "region_code",
                      "video_duration"
                    });
                put("max_count", 1);
              }
            });

    String response =
        restClient
            .post()
            .uri(VIDEO_QUERY_URL)
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
            .header(HttpHeaders.CONTENT_TYPE, "application/json")
            .body(requestBody)
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);

    if (json.has("error")) {
      throw new IOException(
          "TikTok metrics fetch failed: " + json.get("error").get("message").asText());
    }

    if (!json.has("data")
        || !json.get("data").has("videos")
        || json.get("data").get("videos").isEmpty()) {
      throw new IOException("Video not found: " + platformVideoId);
    }

    JsonNode video = json.get("data").get("videos").get(0);

    // Extract metrics
    long views = video.has("view_count") ? video.get("view_count").asLong() : 0;
    long likes = video.has("like_count") ? video.get("like_count").asLong() : 0;
    long comments = video.has("comment_count") ? video.get("comment_count").asLong() : 0;
    long shares = video.has("share_count") ? video.get("share_count").asLong() : 0;

    VideoMetrics metrics =
        VideoMetrics.builder()
            .platform(PlatformType.TIKTOK)
            .platformVideoId(platformVideoId)
            .views(views)
            .likes(likes)
            .comments(comments)
            .shares(shares)
            .saves(0L) // TikTok doesn't provide saves in basic API
            .completionRate(null)
            .avgWatchTimeSeconds(null)
            .impressions(null)
            .reach(null)
            .collectedAt(Instant.now())
            .build();

    log.info(
        "TikTok metrics fetched: videoId={}, views={}, likes={}", platformVideoId, views, likes);

    return metrics;
  }

  @Override
  public PlatformType getPlatform() {
    return PlatformType.TIKTOK;
  }

}
