package com.pompom.creative.api.controller;

import com.pompom.creative.ai.CaptionGeneratorService;
import com.pompom.creative.ai.dto.CaptionRequest;
import com.pompom.creative.ai.dto.CaptionResponse;
import com.pompom.creative.oauth.PlatformType;
import java.util.Map;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for AI caption generation. */
@RestController
@RequestMapping("/api/v1/captions")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class CaptionController {

  private final CaptionGeneratorService captionGeneratorService;

  /** Generate caption for video. */
  @PostMapping("/generate")
  public ResponseEntity<CaptionResponse> generateCaption(
      @RequestBody GenerateCaptionRequest request) {
    log.info(
        "Caption generation request: platform={}, language={}",
        request.getPlatform(),
        request.getLanguage());

    try {
      PlatformType platform = PlatformType.valueOf(request.getPlatform().toUpperCase());

      CaptionRequest captionRequest =
          CaptionRequest.builder()
              .videoTitle(request.getVideoTitle())
              .videoDescription(request.getVideoDescription())
              .targetAudience(
                  request.getTargetAudience() != null
                      ? request.getTargetAudience()
                      : "kids 3-6 years old")
              .contentType(
                  request.getContentType() != null ? request.getContentType() : "educational")
              .platform(platform)
              .language(request.getLanguage() != null ? request.getLanguage() : "en")
              .maxLength(request.getMaxLength())
              .hashtagCount(request.getHashtagCount())
              .build();

      CaptionResponse response = captionGeneratorService.generateCaption(captionRequest);

      return ResponseEntity.ok(response);

    } catch (IllegalArgumentException e) {
      log.error("Invalid platform: {}", request.getPlatform());
      return ResponseEntity.badRequest().build();
    } catch (Exception e) {
      log.error("Caption generation failed", e);
      return ResponseEntity.internalServerError().build();
    }
  }

  /** Check if AI caption generation is configured. */
  @GetMapping("/status")
  public ResponseEntity<Map<String, Object>> getStatus() {
    boolean configured = captionGeneratorService.isConfigured();

    return ResponseEntity.ok(
        Map.of(
            "configured",
            configured,
            "provider",
            "OpenAI",
            "status",
            configured ? "ready" : "not configured"));
  }

  @Data
  public static class GenerateCaptionRequest {
    private String videoTitle;
    private String videoDescription;
    private String targetAudience;
    private String contentType;
    private String platform;
    private String language;
    private Integer maxLength;
    private Integer hashtagCount;
  }
}
