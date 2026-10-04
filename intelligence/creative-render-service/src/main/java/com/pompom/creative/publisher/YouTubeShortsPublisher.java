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
import org.springframework.web.client.RestClient;

/**
 * YouTube Data API v3 publisher for Shorts.
 *
 * <p>Flow: 1. Create video metadata (videos.insert with snippet, status) 2. Upload video file using
 * resumable upload 3. Mark as Short using #Shorts in title/description
 *
 * <p>API Documentation: https://developers.google.com/youtube/v3/docs/videos/insert
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class YouTubeShortsPublisher implements PlatformPublisher {

  private static final String API_BASE_URL = "https://www.googleapis.com/youtube/v3";
  private static final String UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos";

  private final CredentialManager credentialManager;
  private final RestClient.Builder restClientBuilder;
  private final ObjectMapper objectMapper;

  @Override
  public PublishResponse publish(PublishRequest request) {
    log.info("Publishing to YouTube Shorts: video={}", request.getVideoPath());

    try {
      // Get access token
      String accessToken = credentialManager.getActiveAccessToken(PlatformType.YOUTUBE);

      // Upload video with metadata
      PublishResponse response = uploadVideo(accessToken, request);

      log.info("YouTube Shorts publish successful: videoId={}", response.getPlatformVideoId());
      return response;

    } catch (Exception e) {
      log.error("YouTube Shorts publish failed: video={}", request.getVideoPath(), e);
      return PublishResponse.failure("YouTube Shorts publish failed: " + e.getMessage());
    }
  }

  /**
   * Upload video to YouTube using resumable upload. YouTube automatically detects vertical videos
   * (<60s) as Shorts.
   */
  private PublishResponse uploadVideo(String accessToken, PublishRequest request)
      throws IOException {
    log.debug("Uploading video to YouTube");

    File videoFile = new File(request.getVideoPath());
    if (!videoFile.exists()) {
      throw new IOException("Video file not found: " + request.getVideoPath());
    }

    RestClient restClient = restClientBuilder.build();

    // Prepare metadata
    String title = ensureShortsInTitle(request.getTitle());
    String description = ensureShortsInDescription(request.getFullCaption());

    String metadata =
        objectMapper.writeValueAsString(
            new java.util.HashMap<String, Object>() {
              {
                put(
                    "snippet",
                    new java.util.HashMap<String, Object>() {
                      {
                        put("title", title);
                        put("description", description);
                        put("categoryId", "22"); // People & Blogs (appropriate for kids content)
                        if (request.getHashtags() != null && !request.getHashtags().isEmpty()) {
                          put("tags", request.getHashtags());
                        }
                      }
                    });
                put(
                    "status",
                    new java.util.HashMap<String, Object>() {
                      {
                        put(
                            "privacyStatus",
                            request.getIsPrivate() != null && request.getIsPrivate()
                                ? "private"
                                : "public");
                        put("selfDeclaredMadeForKids", true); // Pompom Hills is kids content
                        put("embeddable", true);
                      }
                    });
              }
            });

    // Step 1: Initialize resumable upload
    String uploadSessionUrl = initializeResumableUpload(restClient, accessToken, metadata);

    // Step 2: Upload video file
    String videoId = uploadVideoFile(restClient, uploadSessionUrl, videoFile);

    return PublishResponse.builder()
        .success(true)
        .platformVideoId(videoId)
        .postUrl(null)
        .status("PUBLISHED")
        .message("Successfully uploaded to YouTube Shorts")
        .build();
  }

  /** Initialize resumable upload session. */
  private String initializeResumableUpload(
      RestClient restClient, String accessToken, String metadata) {
    log.debug("Initializing YouTube resumable upload");

    HttpHeaders headers = new HttpHeaders();
    headers.set(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken);
    headers.set(HttpHeaders.CONTENT_TYPE, "application/json; charset=UTF-8");
    headers.set("X-Upload-Content-Type", "video/*");

    ResponseEntity<Void> response =
        restClient
            .post()
            .uri(UPLOAD_URL + "?uploadType=resumable&part=snippet,status")
            .headers(h -> h.addAll(headers))
            .body(metadata)
            .retrieve()
            .toBodilessEntity();

    String uploadUrl = response.getHeaders().getLocation().toString();
    log.debug("YouTube upload session URL: {}", uploadUrl);

    return uploadUrl;
  }

  /** Upload video file to YouTube. */
  private String uploadVideoFile(RestClient restClient, String uploadUrl, File videoFile)
      throws IOException {
    log.debug("Uploading video file to YouTube: size={} bytes", videoFile.length());

    HttpHeaders headers = new HttpHeaders();
    headers.set(HttpHeaders.CONTENT_TYPE, "video/*");
    headers.setContentLength(videoFile.length());

    String response =
        restClient
            .put()
            .uri(uploadUrl)
            .headers(h -> h.addAll(headers))
            .body(new FileSystemResource(videoFile))
            .retrieve()
            .body(String.class);

    JsonNode json = objectMapper.readTree(response);
    String videoId = json.get("id").asText();

    log.debug("YouTube video uploaded: videoId={}", videoId);
    return videoId;
  }

  /** Ensure title contains #Shorts hashtag for proper categorization. */
  private String ensureShortsInTitle(String title) {
    if (title == null || title.isEmpty()) {
      return "#Shorts";
    }

    if (!title.toLowerCase().contains("#shorts")) {
      return title + " #Shorts";
    }

    return title;
  }

  /** Ensure description contains #Shorts hashtag. */
  private String ensureShortsInDescription(String description) {
    if (description == null || description.isEmpty()) {
      return "#Shorts";
    }

    if (!description.toLowerCase().contains("#shorts")) {
      return description + "\n\n#Shorts";
    }

    return description;
  }

  @Override
  public String getPlatformName() {
    return "YouTube Shorts";
  }

  @Override
  public boolean isConfigured() {
    return credentialManager.isConnected(PlatformType.YOUTUBE);
  }
}
