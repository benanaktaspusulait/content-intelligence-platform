package com.pompom.creative.postrender;

import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.qa.QaAnalysisResult;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/** Combines measured technical, QA-helper, and visual-motion evidence without applying policy. */
@Service
@RequiredArgsConstructor
public class PostRenderEvidenceExtractor {
  private final VisualMotionEvidenceClient visualMotion;

  public RenderEvidenceIR extract(
      RenderAsset asset, UUID renderAttemptId, QaAnalysisResult qa, String qaStatus) {
    Map<String, Object> technical = new LinkedHashMap<>();
    put(technical, "durationMs", asset.getDurationMs(), EvidenceStatus.AVAILABLE);
    put(technical, "width", asset.getWidth(), EvidenceStatus.AVAILABLE);
    put(technical, "height", asset.getHeight(), EvidenceStatus.AVAILABLE);
    put(technical, "frameRate", asset.getFrameRate(), asset.getFrameRate() == null ? EvidenceStatus.NOT_EVALUATED : EvidenceStatus.AVAILABLE);
    put(technical, "codec", asset.getCodec(), asset.getCodec() == null ? EvidenceStatus.UNKNOWN : EvidenceStatus.AVAILABLE);
    put(technical, "audioPresent", null, EvidenceStatus.NOT_EVALUATED);
    put(technical, "mediaReadable", Boolean.TRUE.equals(asset.getMediaVerified()),
        asset.getMediaVerified() == null ? EvidenceStatus.UNKNOWN : EvidenceStatus.AVAILABLE);
    put(technical, "checksumVerified", asset.getSha256() != null && Boolean.TRUE.equals(asset.getMediaVerified()),
        asset.getSha256() == null || asset.getMediaVerified() == null ? EvidenceStatus.UNKNOWN : EvidenceStatus.AVAILABLE);
    put(technical, "nearBlackFrameRatio", null, EvidenceStatus.NOT_EVALUATED);
    put(technical, "darkFrameCandidates", List.of(), EvidenceStatus.NOT_EVALUATED);

    Map<String, Object> qaEvidence = new LinkedHashMap<>();
    put(qaEvidence, "evidenceAvailable", "AVAILABLE".equals(qaStatus), status(qaStatus));
    put(qaEvidence, "hasDeadAir", qa == null ? null : qa.isHasDeadAir(), status(qaStatus));
    put(qaEvidence, "deadAirDurationMs", qa == null ? null : qa.getDeadAirDurationMs(), status(qaStatus));
    put(qaEvidence, "deadAirSegments", qa == null ? null : qa.getDeadAirSegments(), status(qaStatus));
    put(qaEvidence, "characterIdentityVerified", qa == null ? null : qa.isCharacterIdentityVerified(), status(qaStatus));
    put(qaEvidence, "characterConfidence", qa == null ? null : qa.getConfidence(), status(qaStatus));
    put(qaEvidence, "characterIdentityIssues", qa == null ? null : qa.getCharacterIdentityIssues(), status(qaStatus));

    Map<String, Object> motion = new LinkedHashMap<>();
    Map<String, Object> sampling = new LinkedHashMap<>();
    Map<String, Object> similarity = new LinkedHashMap<>();
    Map<String, Object> dark = new LinkedHashMap<>();
    Map<String, String> analyzerVersions = new LinkedHashMap<>();
    analyzerVersions.put("technical", "asset-metadata-v1");
    analyzerVersions.put("qaHelpers", "qa-helper-current");
    visualMotion.fetch(asset.getVideoId()).ifPresentOrElse(status -> {
      analyzerVersions.put("visualMotion", String.valueOf(status.getOrDefault("analysisVersion", "unknown")));
      copyMap(status.get("motion"), motion);
      copyMap(status.get("sampling"), sampling);
      copyMap(status.get("visualSimilarity"), similarity);
      Object candidates = status.get("darkFrameCandidates");
      if (candidates instanceof List<?> values) dark.put("candidates", values);
    }, () -> analyzerVersions.put("visualMotion", "NOT_EVALUATED"));

    Map<String, Object> evidence = new LinkedHashMap<>();
    evidence.put("technical", technical);
    evidence.put("qa", qaEvidence);
    evidence.put("motion", motion);
    evidence.put("sampling", sampling);
    evidence.put("visualSimilarity", similarity);
    evidence.put("darkFrames", dark);
    evidence.put("semantic", Map.of(
        "characterContinuity", EvidenceStatus.NOT_EVALUATED.name(),
        "objectContinuity", EvidenceStatus.NOT_EVALUATED.name(),
        "mechanicPreserved", EvidenceStatus.NOT_EVALUATED.name(),
        "visualHookReadable", EvidenceStatus.NOT_EVALUATED.name(),
        "causeEffectContinuity", EvidenceStatus.NOT_EVALUATED.name()));

    return new RenderEvidenceIR(asset.getId(), asset.getRenderJob().getId(), renderAttemptId,
        asset.getVideoId(), asset.getVariantId(), "render-evidence-v1", Instant.now(),
        Map.copyOf(analyzerVersions), Map.copyOf(evidence));
  }

  private EvidenceStatus status(String value) {
    return value == null ? EvidenceStatus.UNKNOWN : EvidenceStatus.valueOf(value);
  }

  private void put(Map<String, Object> map, String key, Object value, EvidenceStatus status) {
    map.put(key, value);
    map.put(key + "Status", status.name());
  }

  @SuppressWarnings("unchecked")
  private void copyMap(Object source, Map<String, Object> target) {
    if (source instanceof Map<?, ?> values) values.forEach((key, value) -> target.put(String.valueOf(key), value));
  }
}
