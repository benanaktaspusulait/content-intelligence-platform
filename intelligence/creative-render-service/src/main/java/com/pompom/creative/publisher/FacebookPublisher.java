package com.pompom.creative.publisher;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import com.pompom.creative.service.CredentialManager;
import java.io.File;
import java.io.IOException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

/**
 * Facebook Graph API publisher for Page videos.
 *
 * <p>Flow: 1. Get Page ID (if not provided) 2. Initialize resumable upload session 3. Upload video
 * file 4. Publish video with metadata
 *
 * <p>API Documentation: https://developers.facebook.com/docs/video-api/guides/publishing
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class FacebookPublisher implements PlatformPublisher {

  private static final String GRAPH_API_VERSION = "v18.0";
  private static final String GRAPH_API_BASE_URL =
      "https://graph.facebook.com/" + GRAPH_API_VERSION;

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Value("${pompom.social.facebook.page-id:}")
  private String facebookPageId;

  @Override
  public PublishResponse publish(PublishRequest request) {
    log.info("Publishing to Facebook: video={}", request.getVideoPath());

    try {
      // Get access token
      String accessToken = credentialManager.getActiveAccessToken(PlatformType.FACEBOOK);

      // Get page ID if not configured
      String pageId = getPageId(accessToken);

      // Initialize upload
      String videoId = initializeUpload(accessToken, pageId, request);

      // Upload video
      uploadVideo(accessToken, videoId, request.getVideoPath());

      // Publish video
      PublishResponse response = publishVideo(accessToken, pageId, videoId, request);

      log.info("Facebook publish successful: videoId={}", response.getPlatformVideoId());
      return response;

    } catch (Exception e) {
      log.error("Facebook publish failed: video={}", request.getVideoPath(), e);
      return PublishResponse.failure("Facebook publish failed: " + e.getMessage());
    }
  }

  /** Get Facebook Page ID. */
  private String getPageId(String accessToken) throws IOException {
    if (facebookPageId != null && !facebookPageId.isEmpty()) {
      return facebookPageId;
    }

    log.debug("Fetching Facebook Page ID");

    RestClient restClient = restClientBuilder.build();

    String response =
        restClient
            .get()
            .uri(GRAPH_API_BASE_URL + "/me/accounts?access_token=" + accessToken)
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);

    if (!json.has("data") || json.get("data").isEmpty()) {
      throw new RuntimeException("No Facebook Pages found for this account");
    }

    String pageId = json.get("data").get(0).get("id").asText();
    log.debug("Facebook Page ID: {}", pageId);

    return pageId;
  }

  /** Initialize resumable video upload. */
  private String initializeUpload(String accessToken, String pageId, PublishRequest request)
      throws IOException {
    log.debug("Initializing Facebook video upload");

    File videoFile = new File(request.getVideoPath());
    if (!videoFile.exists()) {
      throw new IOException("Video file not found: " + request.getVideoPath());
    }

    RestClient restClient = restClientBuilder.build();

    String url =
        GRAPH_API_BASE_URL
            + "/"
            + pageId
            + "/videos"
            + "?access_token="
            + accessToken
            + "&upload_phase=start"
            + "&file_size="
            + videoFile.length();

    String response = restClient.post().uri(url).retrieve().body(String.class);

    JsonNode json = objectMapper.readTree(response);
    String videoId = json.get("video_id").asText();

    log.debug("Facebook video upload initialized: videoId={}", videoId);
    return videoId;
  }

  /** Upload video file. */
  private void uploadVideo(String accessToken, String videoId, String videoPath)
      throws IOException {
    log.debug("Uploading video to Facebook: videoId={}", videoId);

    File videoFile = new File(videoPath);

    RestClient restClient = restClientBuilder.build();

    MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
    body.add("video_file_chunk", new FileSystemResource(videoFile));

    String url =
        GRAPH_API_BASE_URL
            + "/"
            + videoId
            + "?access_token="
            + accessToken
            + "&upload_phase=transfer";

    restClient
        .post()
        .uri(url)
        .contentType(MediaType.MULTIPART_FORM_DATA)
        .body(body)
        .retrieve()
        .body(String.class);

    log.debug("Facebook video upload complete");
  }

  /** Publish video with metadata. */
  private PublishResponse publishVideo(
      String accessToken, String pageId, String videoId, PublishRequest request)
      throws IOException {
    log.debug("Publishing Facebook video: videoId={}", videoId);

    RestClient restClient = restClientBuilder.build();

    String url =
        GRAPH_API_BASE_URL
            + "/"
            + pageId
            + "/videos"
            + "?access_token="
            + accessToken
            + "&upload_phase=finish"
            + "&video_id="
            + videoId
            + "&title="
            + (request.getTitle() != null ? request.getTitle() : "")
            + "&description="
            + request.getFullCaption();

    String response = restClient.post().uri(url).retrieve().body(String.class);

    JsonNode json = objectMapper.readTree(response);

    if (!json.get("success").asBoolean()) {
      throw new RuntimeException("Facebook video publish failed");
    }

    String postUrl = "https://www.facebook.com/" + pageId + "/videos/" + videoId;

    return PublishResponse.builder()
        .success(true)
        .platformVideoId(videoId)
        .postUrl(postUrl)
        .status("PUBLISHED")
        .message("Successfully published to Facebook")
        .build();
  }

  @Override
  public String getPlatformName() {
    return "Facebook";
  }

  @Override
  public boolean isConfigured() {
    return credentialManager.isConnected(PlatformType.FACEBOOK);
  }
}
