package com.pompom.creative.postrender;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/** Read-only bridge to the intelligence service's versioned visual-motion evidence. */
@Component
@RequiredArgsConstructor
@Slf4j
public class VisualMotionEvidenceClient {
  private final RestClient.Builder restClientBuilder;

  @Value("${pompom.intelligence-base-url:http://localhost:8080}")
  private String intelligenceBaseUrl;

  public Optional<Map<String, Object>> fetch(UUID videoId) {
    if (videoId == null) return Optional.empty();
    try {
      Map<String, Object> status = restClientBuilder.baseUrl(intelligenceBaseUrl).build().get()
          .uri("/api/v1/videos/{id}/analysis/status", videoId)
          .retrieve()
          .body(new ParameterizedTypeReference<>() {});
      if (status == null || !Boolean.TRUE.equals(status.get("hasCompletedAnalysis"))) return Optional.empty();
      if (!"SAMPLED_VISUAL_MOTION".equals(status.get("analysisType"))
          && !"SAMPLED_VISUAL_MOTION_V4".equals(status.get("analysisType"))
          && !"SAMPLED_VISUAL_MOTION_V5".equals(status.get("analysisType"))) return Optional.empty();
      return Optional.of(status);
    } catch (Exception error) {
      log.warn("Visual-motion evidence unavailable for video {}", videoId, error);
      return Optional.empty();
    }
  }
}
