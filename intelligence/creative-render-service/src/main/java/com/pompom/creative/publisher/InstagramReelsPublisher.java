package com.pompom.creative.publisher;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.creative.service.CredentialManager;
import java.io.IOException;
import java.net.URI;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

/**
 * Instagram Graph API publisher for Reels.
 *
 * <p>Instagram requires the video to already be available through a public HTTP(S) URL. This
 * service does not upload or host media.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class InstagramReelsPublisher implements PlatformPublisher {

  private static final String GRAPH_API_VERSION = "v18.0";
  private static final String GRAPH_API_BASE_URL =
      "https://graph.facebook.com/" + GRAPH_API_VERSION;

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public PublishResponse publish(PublishRequest request) {
    log.info("Publishing to Instagram Reels: video={}", request.getVideoPath());

    try {
      String accessToken = credentialManager.getActiveAccessToken(PlatformType.INSTAGRAM);
      String publicVideoUrl = requirePublicVideoUrl(request.getVideoPath());
      String igUserId = getInstagramBusinessAccountId(accessToken);
      String containerId = createMediaContainer(accessToken, igUserId, publicVideoUrl, request);

      waitForProcessing(accessToken, containerId);

      PublishResponse response = publishMedia(accessToken, igUserId, containerId);
      log.info("Instagram Reels publish successful: mediaId={}", response.getPlatformPostId());
      return response;
    } catch (Exception e) {
      log.error("Instagram Reels publish failed: video={}", request.getVideoPath(), e);
      return PublishResponse.failure("Instagram Reels publish failed: " + e.getMessage());
    }
  }

  private String getInstagramBusinessAccountId(String accessToken) throws IOException {
    log.debug("Fetching Instagram Business Account ID");

    RestClient restClient = restClientBuilder.build();
    String pageResponse =
        restClient
            .get()
            .uri(GRAPH_API_BASE_URL + "/me/accounts?access_token=" + accessToken)
            .retrieve()
            .body(String.class);

    JsonNode pageJson = objectMapper.readTree(pageResponse);
    if (!pageJson.has("data") || pageJson.get("data").isEmpty()) {
      throw new IllegalStateException("No Facebook Pages found");
    }

    String pageId = pageJson.get("data").get(0).get("id").asText();
    String igResponse =
        restClient
            .get()
            .uri(
                GRAPH_API_BASE_URL
                    + "/"
                    + pageId
                    + "?fields=instagram_business_account&access_token="
                    + accessToken)
            .retrieve()
            .body(String.class);

    JsonNode igJson = objectMapper.readTree(igResponse);
    if (!igJson.has("instagram_business_account")) {
      throw new IllegalStateException("No Instagram Business Account connected to this Page");
    }

    String igUserId = igJson.get("instagram_business_account").get("id").asText();
    log.debug("Instagram Business Account ID: {}", igUserId);
    return igUserId;
  }

  private String createMediaContainer(
      String accessToken, String igUserId, String videoUrl, PublishRequest request)
      throws IOException {
    log.debug("Creating Instagram media container");

    RestClient restClient = restClientBuilder.build();
    String url =
        GRAPH_API_BASE_URL
            + "/"
            + igUserId
            + "/media"
            + "?access_token="
            + accessToken
            + "&media_type=REELS"
            + "&video_url="
            + videoUrl
            + "&caption="
            + request.getFullCaption()
            + "&share_to_feed=true";

    String response = restClient.post().uri(url).retrieve().body(String.class);
    JsonNode json = objectMapper.readTree(response);
    String containerId = json.get("id").asText();
    log.debug("Instagram media container created: {}", containerId);
    return containerId;
  }

  private void waitForProcessing(String accessToken, String containerId)
      throws IOException, InterruptedException {
    log.debug("Waiting for Instagram to process video");

    RestClient restClient = restClientBuilder.build();
    int maxAttempts = 60;
    int attempts = 0;

    while (attempts < maxAttempts) {
      String response =
          restClient
              .get()
              .uri(
                  GRAPH_API_BASE_URL
                      + "/"
                      + containerId
                      + "?fields=status_code&access_token="
                      + accessToken)
              .retrieve()
              .body(String.class);

      JsonNode json = objectMapper.readTree(response);
      String statusCode = json.get("status_code").asText();
      if ("FINISHED".equals(statusCode)) {
        log.debug("Instagram video processing complete");
        return;
      }
      if ("ERROR".equals(statusCode)) {
        throw new IllegalStateException("Instagram video processing failed");
      }

      Thread.sleep(5000);
      attempts++;
    }

    throw new IllegalStateException("Instagram video processing timeout");
  }

  private PublishResponse publishMedia(String accessToken, String igUserId, String containerId)
      throws IOException {
    log.debug("Publishing Instagram media");

    RestClient restClient = restClientBuilder.build();
    String url =
        GRAPH_API_BASE_URL
            + "/"
            + igUserId
            + "/media_publish"
            + "?access_token="
            + accessToken
            + "&creation_id="
            + containerId;

    String response = restClient.post().uri(url).retrieve().body(String.class);
    JsonNode json = objectMapper.readTree(response);
    String mediaId = json.get("id").asText();

    return PublishResponse.builder()
        .success(true)
        .platformPostId(mediaId)
        .postUrl("https://www.instagram.com/reel/" + mediaId)
        .status("PUBLISHED")
        .message("Successfully published to Instagram Reels")
        .build();
  }

  private String requirePublicVideoUrl(String videoLocation) throws IOException {
    if (videoLocation == null || videoLocation.isBlank()) {
      throw new IOException("Instagram publishing requires a public video URL");
    }

    try {
      URI uri = URI.create(videoLocation);
      String scheme = uri.getScheme();
      if (("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme))
          && uri.getHost() != null) {
        return videoLocation;
      }
    } catch (IllegalArgumentException ignored) {
      // Report the same actionable message for malformed and local paths.
    }

    throw new IOException("Instagram publishing requires videoPath to be a public HTTP(S) URL");
  }

  @Override
  public String getPlatformName() {
    return "Instagram Reels";
  }

  @Override
  public boolean isConfigured() {
    return credentialManager.isConnected(PlatformType.INSTAGRAM);
  }
}
