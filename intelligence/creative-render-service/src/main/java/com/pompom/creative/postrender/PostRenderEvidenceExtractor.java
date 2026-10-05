package com.pompom.creative.postrender;

import com.pompom.creative.domain.RenderAsset;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
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
  private final PayoffWindowResolver payoffWindowResolver;
  private final PayoffMotionAnalyzer payoffMotionAnalyzer;
  private final PlanRenderFidelityAnalyzer fidelityAnalyzer;
  private final TemporalBeatAlignmentService temporalBeatAlignmentService;

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
    put(technical, "visibilityProfile", Map.of(), EvidenceStatus.NOT_EVALUATED);

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
    Map<String, Object> presentation = new LinkedHashMap<>();
    Map<String, String> analyzerVersions = new LinkedHashMap<>();
    analyzerVersions.put("technical", "asset-metadata-v1");
    analyzerVersions.put("qaHelpers", "qa-helper-current");
    analyzerVersions.put("renderedCreativeEvidence", "rendered-creative-evidence-v1");
    visualMotion.fetch(asset.getVideoId()).ifPresentOrElse(status -> {
      analyzerVersions.put("visualMotion", String.valueOf(status.getOrDefault("analysisVersion", "unknown")));
      copyMap(status.get("motion"), motion);
      copyMap(status.get("sampling"), sampling);
      copyMap(status.get("visualSimilarity"), similarity);
      Map<String, Object> temporal = new LinkedHashMap<>();
      copyMap(status.get("temporalProfile"), temporal);
      motion.put("temporalProfile", temporal);
      copyMap(status.get("presentation"), presentation);
      Object candidates = status.get("darkFrameCandidates");
      if (candidates instanceof List<?> values) dark.put("candidates", values);
      Map<String, Object> visibility = new LinkedHashMap<>();
      Object samplingCount = sampling.get("decodedSamples");
      int decodedSamples = samplingCount instanceof Number number ? number.intValue() : 0;
      int darkCount = candidates instanceof List<?> values ? values.size() : 0;
      visibility.put("darkCandidateCount", darkCount);
      visibility.put("decodedSampleCount", decodedSamples);
      // A full-video dark profile is review evidence, not an automatic failure.
      visibility.put("allSampledFramesDark", decodedSamples > 0 && darkCount >= decodedSamples);
      visibility.put("profileStatus", "AVAILABLE");
      technical.put("visibilityProfile", visibility);
      technical.put("visibilityProfileStatus", EvidenceStatus.AVAILABLE.name());
    }, () -> analyzerVersions.put("visualMotion", "NOT_EVALUATED"));

    Map<String, Object> evidence = new LinkedHashMap<>();
    evidence.put("technical", technical);
    evidence.put("qa", qaEvidence);
    evidence.put("motion", motion);
    evidence.put("sampling", sampling);
    evidence.put("visualSimilarity", similarity);
    evidence.put("darkFrames", dark);
    evidence.put("presentation", presentation);
    PayoffWindow payoff = payoffWindowResolver.resolve(asset.getRenderJob());
    Map<String, Object> payoffEvidence = new LinkedHashMap<>();
    payoffEvidence.put("status", payoff.status().name());
    payoffEvidence.put("statusStatus", EvidenceStatus.AVAILABLE.name());
    payoffEvidence.put("startSeconds", payoff.startSeconds());
    payoffEvidence.put("endSeconds", payoff.endSeconds());
    payoffEvidence.put("source", payoff.source());
    payoffEvidence.put("reason", payoff.reason());
    evidence.put("payoff", payoffEvidence);
    Map<String, Object> payoffMotion = payoffMotionAnalyzer.analyze(
        motion.get("temporalProfile") instanceof Map<?, ?> profile ? cast(profile) : Map.of(), payoff);
    evidence.put("payoffContrast", payoffMotion);
    evidence.put("intentionalHold", payoffMotion);
    evidence.put("planRenderFidelity", fidelityAnalyzer.compare(
        contract(asset.getRenderJob()), payoffMotion));
    Map<String, Object> temporalProfile = motion.get("temporalProfile") instanceof Map<?, ?> profile
        ? cast(profile) : Map.of();
    Map<String, Object> temporal = temporalBeatAlignmentService.align(temporalProfile, contract(asset.getRenderJob()));
    temporal.put("activityDropsStatus", temporalProfile.isEmpty() ? EvidenceStatus.UNKNOWN.name() : EvidenceStatus.AVAILABLE.name());
    temporal.put("activitySpikesStatus", temporalProfile.isEmpty() ? EvidenceStatus.UNKNOWN.name() : EvidenceStatus.AVAILABLE.name());
    temporal.put("unmappedActivityDropsStatus", temporalProfile.isEmpty() ? EvidenceStatus.UNKNOWN.name() : EvidenceStatus.AVAILABLE.name());
    temporal.put("status", temporalProfile.isEmpty() ? EvidenceStatus.UNKNOWN.name() : EvidenceStatus.AVAILABLE.name());
    evidence.put("temporal", temporal);
    Map<String, Object> opening = new LinkedHashMap<>();
    opening.put("causalLegibility", null);
    opening.put("causalLegibilityStatus", EvidenceStatus.NOT_EVALUATED.name());
    Map<String, Object> semanticLoop = new LinkedHashMap<>();
    semanticLoop.put("continuity", null);
    semanticLoop.put("continuityStatus", EvidenceStatus.NOT_EVALUATED.name());
    Map<String, Object> character = new LinkedHashMap<>();
    character.put("primaryContinuity", null);
    character.put("primaryContinuityStatus", EvidenceStatus.NOT_EVALUATED.name());
    evidence.put("opening", opening);
    evidence.put("semanticLoop", semanticLoop);
    evidence.put("character", character);

    return new RenderEvidenceIR(asset.getId(), asset.getRenderJob().getId(), renderAttemptId,
        asset.getVideoId(), asset.getVariantId(), "render-evidence-v2", Instant.now(),
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

  @SuppressWarnings("unchecked")
  private Map<String, Object> cast(Map<?, ?> source) {
    return (Map<String, Object>) source;
  }

  private Map<String, Object> contract(com.pompom.creative.domain.RenderJob job) {
    if (job == null || job.getCreativeContractSnapshot() == null) return Map.of();
    try {
      return new ObjectMapper().readValue(job.getCreativeContractSnapshot(), new TypeReference<>() {});
    } catch (Exception ignored) {
      return Map.of();
    }
  }
}
