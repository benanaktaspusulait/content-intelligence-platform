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
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;

/**
 * TikTok Content Posting API publisher.
 *
 * <p>Flow: 1. Initialize upload session (get upload_url) 2. Upload video bytes to upload_url 3.
 * Create post with video_id and metadata
 *
 * <p>API Documentation: https://developers.tiktok.com/doc/content-posting-api-reference
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class TikTokPublisher implements PlatformPublisher {

  private static final String API_BASE_URL = "https://open.tiktokapis.com/v2";
  private static final String UPLOAD_INIT_URL = API_BASE_URL + "/post/publish/inbox/video/init/";
  private static final String CREATE_POST_URL = API_BASE_URL + "/post/publish/video/init/";

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public PublishResponse publish(PublishRequest request) {
    log.info("Publishing to TikTok: video={}", request.getVideoPath());

    try {
      // Step 1: Get access token
      String accessToken = credentialManager.getActiveAccessToken(PlatformType.TIKTOK);

      // Step 2: Initialize upload session
      String uploadUrl = initializeUpload(accessToken, request);

      // Step 3: Upload video file
      uploadVideo(uploadUrl, request.getVideoPath());

      // Step 4: Create post
      PublishResponse response = createPost(accessToken, request);

      log.info("TikTok publish successful: postId={}", response.getPlatformPostId());
      return response;

    } catch (Exception e) {
      log.error("TikTok publish failed: video={}", request.getVideoPath(), e);
      return PublishResponse.failure("TikTok publish failed: " + e.getMessage());
    }
  }

  /** Initialize video upload session. Returns upload URL for video bytes. */
  private String initializeUpload(String accessToken, PublishRequest request) throws IOException {
    log.debug("Initializing TikTok upload session");

    RestClient restClient = restClientBuilder.build();

    // Build request body
    String requestBody =
        objectMapper.writeValueAsString(
            new java.util.HashMap<String, Object>() {
              {
                put(
                    "source_info",
                    new java.util.HashMap<String, Object>() {
                      {
                        put("source", "FILE_UPLOAD");
                        put("video_size", new File(request.getVideoPath()).length());
                      }
                    });
              }
            });

    String response =
        restClient
            .post()
            .uri(UPLOAD_INIT_URL)
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
            .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .body(requestBody)
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);

    if (json.has("error")) {
      throw new RuntimeException(
          "TikTok upload init failed: " + json.get("error").get("message").asText());
    }

    String uploadUrl = json.get("data").get("upload_url").asText();
    log.debug("TikTok upload URL obtained: {}", uploadUrl);

    return uploadUrl;
  }

  /** Upload video bytes to TikTok's upload URL. */
  private void uploadVideo(String uploadUrl, String videoPath) throws IOException {
    log.debug("Uploading video to TikTok: path={}", videoPath);

    File videoFile = new File(videoPath);
    if (!videoFile.exists()) {
      throw new IOException("Video file not found: " + videoPath);
    }

    RestClient restClient = restClientBuilder.build();

    MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
    body.add("video", new FileSystemResource(videoFile));

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.MULTIPART_FORM_DATA);

    String response =
        restClient
            .put()
            .uri(uploadUrl)
            .headers(h -> h.addAll(headers))
            .body(body)
            .retrieve()
            .body(String.class);

    log.debug("TikTok video upload complete");
  }

  /** Create TikTok post with uploaded video. */
  private PublishResponse createPost(String accessToken, PublishRequest request)
      throws IOException {
    log.debug("Creating TikTok post");

    RestClient restClient = restClientBuilder.build();

    // Build post request
    String requestBody =
        objectMapper.writeValueAsString(
            new java.util.HashMap<String, Object>() {
              {
                put(
                    "post_info",
                    new java.util.HashMap<String, Object>() {
                      {
                        put("title", request.getTitle() != null ? request.getTitle() : "");
                        put("description", request.getFullCaption());
                        put(
                            "privacy_level",
                            request.getIsPrivate() != null && request.getIsPrivate()
                                ? "SELF_ONLY"
                                : "PUBLIC_TO_EVERYONE");
                        put("disable_duet", false);
                        put("disable_comment", false);
                        put("disable_stitch", false);
                        put("video_cover_timestamp_ms", 1000); // Cover at 1 second
                      }
                    });
                put(
                    "source_info",
                    new java.util.HashMap<String, Object>() {
                      {
                        put("source", "FILE_UPLOAD");
                      }
                    });
              }
            });

    String response =
        restClient
            .post()
            .uri(CREATE_POST_URL)
            .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
            .header(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .body(requestBody)
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);

    if (json.has("error")) {
      throw new RuntimeException(
          "TikTok post creation failed: " + json.get("error").get("message").asText());
    }

    String publishId = json.get("data").get("publish_id").asText();

    return PublishResponse.success(publishId, null);
  }

  @Override
  public String getPlatformName() {
    return "TikTok";
  }

  @Override
  public boolean isConfigured() {
    return credentialManager.isConnected(PlatformType.TIKTOK);
  }
}
