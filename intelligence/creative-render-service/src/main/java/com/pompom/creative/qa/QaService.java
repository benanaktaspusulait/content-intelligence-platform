package com.pompom.creative.qa;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.service.AssetLibraryManager;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Collectors;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

/**
 * Client service for Python QA ML service. Calls FastAPI endpoints for dead air detection and
 * character verification.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class QaService {

  private final RestClient.Builder restClientBuilder;
  private final AssetLibraryManager assetLibraryManager;

  @Value("${pompom.qa.service.url:http://localhost:8001}")
  private String qaServiceUrl;

  @Value("${pompom.data.root:/tmp/pompom-data}")
  private String dataRoot;

  private RestClient restClient;

  /**
   * Analyze render asset for quality issues.
   *
   * @param asset Render asset to analyze
   * @return Aggregated QA analysis result
   */
  public QaAnalysisResult analyzeAsset(RenderAsset asset) {
    log.info("Analyzing asset: {} (type: {})", asset.getId(), asset.getAssetType());

    // Get asset path
    Path assetPath = getAssetPath(asset);

    // Dead air analysis
    DeadAirResponse deadAir = analyzeDeadAir(assetPath);

    // Character verification (title comes from the immutable job snapshot)
    String characterName = extractCharacterName(asset.getRenderJob().getContentTitleSnapshot());
    CharacterIdentityResponse characterIdentity = verifyCharacterIdentity(assetPath, characterName);

    // Calculate compliance score
    int complianceScore = calculateComplianceScore(deadAir, characterIdentity);

    // Aggregate results
    QaAnalysisResult result =
        QaAnalysisResult.builder()
            .hasDeadAir(deadAir.hasDeadAir())
            .deadAirSegments(convertDeadAirSegments(deadAir.deadAirSegments()))
            .deadAirDurationMs(deadAir.totalDeadAirDurationMs())
            .characterIdentityVerified(characterIdentity.characterIdentityVerified())
            .confidence(characterIdentity.confidence())
            .characterIdentityIssues(characterIdentity.characterIdentityIssues())
            .reasoning(characterIdentity.reasoning())
            .complianceScore(complianceScore)
            .build();

    log.info(
        "QA analysis complete: asset={}, compliance={}, deadAir={}, characterVerified={}",
        asset.getId(),
        complianceScore,
        deadAir.hasDeadAir(),
        characterIdentity.characterIdentityVerified());

    return result;
  }

  /** Call Python service to analyze dead air. */
  private DeadAirResponse analyzeDeadAir(Path assetPath) {
    RestClient client = getRestClient();

    DeadAirRequest request = new DeadAirRequest(assetPath.toString());

    try {
      DeadAirResponse response =
          client
              .post()
              .uri("/api/v1/qa/dead-air")
              .body(request)
              .retrieve()
              .body(DeadAirResponse.class);

      log.debug(
          "Dead air analysis: {} segments found", response != null ? response.segmentCount() : 0);

      if (response == null) {
        throw new QaDependencyUnavailableException("Dead-air service returned no evidence");
      }
      return response;
    } catch (Exception e) {
      log.error("Failed to analyze dead air for: {}", assetPath, e);
      if (e instanceof QaDependencyUnavailableException unavailable) {
        throw unavailable;
      }
      throw new QaDependencyUnavailableException("Dead-air evidence is unavailable", e);
    }
  }

  /** Call Python service to verify character identity. */
  private CharacterIdentityResponse verifyCharacterIdentity(Path assetPath, String characterName) {
    RestClient client = getRestClient();

    CharacterIdentityRequest request =
        new CharacterIdentityRequest(
            assetPath.toString(), characterName, null // No reference image for now
            );

    try {
      CharacterIdentityResponse response =
          client
              .post()
              .uri("/api/v1/qa/character-identity")
              .body(request)
              .retrieve()
              .body(CharacterIdentityResponse.class);

      log.debug(
          "Character verification: {} verified={}, confidence={}",
          characterName,
          response != null && response.characterIdentityVerified(),
          response != null ? response.confidence() : 0.0);

      if (response == null) {
        throw new QaDependencyUnavailableException("Character service returned no evidence");
      }
      return response;
    } catch (Exception e) {
      log.error("Failed to verify character identity for: {} ({})", assetPath, characterName, e);
      if (e instanceof QaDependencyUnavailableException unavailable) {
        throw unavailable;
      }
      throw new QaDependencyUnavailableException("Character identity evidence is unavailable", e);
    }
  }

  /**
   * Calculate compliance score from QA results.
   *
   * @param deadAir Dead air analysis result
   * @param characterIdentity Character verification result
   * @return Compliance score (0-100)
   */
  private int calculateComplianceScore(
      DeadAirResponse deadAir, CharacterIdentityResponse characterIdentity) {
    int score = 100;

    // Deduct for dead air
    if (deadAir.hasDeadAir()) {
      score -= 30;
    }

    // Deduct for character mismatch
    if (!characterIdentity.characterIdentityVerified()) {
      score -= 50;
    }

    return Math.max(0, score);
  }

  /** Get asset file path from render asset. */
  private Path getAssetPath(RenderAsset asset) {
    return Path.of(dataRoot).resolve(asset.getRelativePath());
  }

  /**
   * Extract character name from content title. Assumes title format like "Kiko Episode" or "Mimi's
   * Adventure"
   */
  String extractCharacterName(String title) {
    // Simple extraction: first word
    if (title != null && !title.isEmpty()) {
      String firstWord = title.split("\\s+")[0];
      return firstWord.replaceAll("[^a-zA-Z]", "");
    }

    return "Unknown";
  }

  /** Convert dead air segments to domain model. */
  private List<QaAnalysisResult.DeadAirSegment> convertDeadAirSegments(
      List<DeadAirSegmentDto> segments) {
    return segments.stream()
        .map(
            seg ->
                QaAnalysisResult.DeadAirSegment.builder()
                    .startMs(seg.startMs())
                    .endMs(seg.endMs())
                    .duration(seg.duration())
                    .build())
        .collect(Collectors.toList());
  }

  /** Get or create RestClient instance. */
  private RestClient getRestClient() {
    if (restClient == null) {
      restClient = restClientBuilder.baseUrl(qaServiceUrl).build();
    }
    return restClient;
  }

  // DTO classes for Python service API

  private record DeadAirRequest(@JsonProperty("video_path") String videoPath) {}

  record DeadAirResponse(
      @JsonProperty("has_dead_air") boolean hasDeadAir,
      @JsonProperty("dead_air_segments") List<DeadAirSegmentDto> deadAirSegments,
      @JsonProperty("total_dead_air_duration_ms") int totalDeadAirDurationMs,
      @JsonProperty("segment_count") int segmentCount) {}

  private record DeadAirSegmentDto(
      @JsonProperty("start_ms") int startMs, @JsonProperty("end_ms") int endMs, double duration) {}

  private record CharacterIdentityRequest(
      @JsonProperty("video_path") String videoPath,
      @JsonProperty("expected_character") String expectedCharacter,
      @JsonProperty("reference_image_path") String referenceImagePath) {}

  record CharacterIdentityResponse(
      @JsonProperty("character_identity_verified") boolean characterIdentityVerified,
      double confidence,
      @JsonProperty("character_identity_issues") String characterIdentityIssues,
      String reasoning) {}

  public static final class QaDependencyUnavailableException extends RuntimeException {
    public QaDependencyUnavailableException(String message) {
      super(message);
    }

    public QaDependencyUnavailableException(String message, Throwable cause) {
      super(message, cause);
    }
  }
}
