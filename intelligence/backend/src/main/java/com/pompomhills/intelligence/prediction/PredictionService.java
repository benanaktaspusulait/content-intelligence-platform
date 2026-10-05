package com.pompomhills.intelligence.prediction;

import com.pompomhills.intelligence.creative.CreativeFingerprintRepository;
import com.pompomhills.intelligence.platformstate.PlatformStateService;
import com.pompomhills.intelligence.prediction.ml.MlPredictionClient;
import jakarta.persistence.EntityNotFoundException;
import java.time.Clock;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

@Service
public class PredictionService {
  private final PredictionRepository predictions;
  private final CreativeFingerprintRepository fingerprints;
  private final MlPredictionClient ml;
  private final Clock clock;
  private final JdbcClient jdbc;
  private final PlatformStateService platformStates;
  private final ObjectMapper json;

  public PredictionService(
      PredictionRepository predictions,
      CreativeFingerprintRepository fingerprints,
      MlPredictionClient ml,
      Clock clock,
      JdbcClient jdbc,
      PlatformStateService platformStates,
      ObjectMapper json) {
    this.predictions = predictions;
    this.fingerprints = fingerprints;
    this.ml = ml;
    this.clock = clock;
    this.jdbc = jdbc;
    this.platformStates = platformStates;
    this.json = json;
  }

  @Transactional
  public PredictionView generate(UUID videoId, String platform) {
    var fingerprint =
        fingerprints
            .findFirstByVideoIdOrderByCreatedAtDesc(videoId)
            .orElseThrow(() -> new IllegalStateException("Analyse the video before prediction"));
    var cutoff = clock.instant();
    UUID snapshotId = createFeatureSnapshot(videoId, platform, fingerprint, cutoff);
    var response = ml.prepublish(platform, fingerprint.getFeatures(), cutoff);
    Map<String, Object> payload = new LinkedHashMap<>(response.payload());
    payload.put("featureSnapshotId", snapshotId.toString());
    var entity =
        new PredictionEntity(
            UUID.randomUUID(),
            videoId,
            platform,
            PredictionType.PRE_PUBLISH,
            response.modelVersion(),
            response.datasetVersion(),
            response.featureVersion(),
            cutoff,
            payload,
            response.confidence(),
            response.comparableSampleSize());
    return map(predictions.save(entity));
  }

  private UUID createFeatureSnapshot(UUID videoId, String platform,
      com.pompomhills.intelligence.creative.CreativeFingerprintEntity fingerprint,
      java.time.Instant cutoff) {
    UUID id = UUID.randomUUID();
    Map<String, Object> semantic = fingerprint.getAnalysis().getSemanticVideoEvidence();
    String semanticVersion = String.valueOf(semantic.getOrDefault("schemaVersion",
        semantic.getOrDefault("version", "UNKNOWN")));
    jdbc.sql("""
        INSERT INTO prediction_feature_snapshots
          (id,video_id,platform,feature_schema_version,source_analysis_version,
           semantic_schema_version,knowledge_cutoff,features)
        VALUES (:id,:video,:platform,:featureVersion,:analysisVersion,
                :semanticVersion,:cutoff,CAST(:features AS jsonb))
        """)
        .param("id", id).param("video", videoId).param("platform", platform)
        .param("featureVersion", "prediction-feature-snapshot-v1")
        .param("analysisVersion", fingerprint.getAnalysis().getAnalysisVersion())
        .param("semanticVersion", semanticVersion).param("cutoff", cutoff)
        .param("features", json.writeValueAsString(fingerprint.getFeatures())).update();
    return id;
  }

  @Transactional
  public PredictionView generateLive(UUID videoId, String platform, java.time.Instant cutoff) {
    var fingerprint =
        fingerprints
            .findFirstByVideoIdOrderByCreatedAtDesc(videoId)
            .orElseThrow(() -> new IllegalStateException("Analyse the video before prediction"));
    var eligibility = platformStates.liveFeatures(videoId, platform, cutoff, "LIVE");
    if (!eligibility.allowed()) throw new IllegalStateException(eligibility.reason());
    var response = ml.live(platform, fingerprint.getFeatures(), eligibility.features(), cutoff);
    var entity =
        new PredictionEntity(
            UUID.randomUUID(),
            videoId,
            platform,
            PredictionType.LIVE,
            response.modelVersion(),
            response.datasetVersion(),
            response.featureVersion(),
            cutoff,
            response.payload(),
            response.confidence(),
            response.comparableSampleSize());
    return map(predictions.save(entity));
  }

  @Transactional
  public PredictionView lock(UUID id, String reason) {
    var entity =
        predictions
            .findById(id)
            .orElseThrow(() -> new EntityNotFoundException("Prediction not found: " + id));
    entity.lock(clock.instant(), reason);
    return map(predictions.saveAndFlush(entity));
  }

  @Transactional(readOnly = true)
  public List<PredictionView> history(UUID videoId) {
    return predictions.findByVideoIdOrderByCreatedAtDesc(videoId).stream().map(this::map).toList();
  }

  @Transactional(readOnly = true)
  public List<PredictionView> list() {
    return predictions.findAllByOrderByCreatedAtDesc().stream().map(this::map).toList();
  }

  @Transactional
  public PredictionView evaluate(UUID id, int horizonMinutes, double actualValue) {
    var entity =
        predictions
            .findById(id)
            .orElseThrow(() -> new EntityNotFoundException("Prediction not found: " + id));
    if (horizonMinutes <= 0) throw new IllegalArgumentException("Horizon must be positive");
    if (actualValue < 0) throw new IllegalArgumentException("Actual value cannot be negative");
    Double expected = expectedValue(entity.getPayload(), horizonMinutes);
    Double absoluteError = expected == null ? null : Math.abs(expected - actualValue);
    Double logError =
        expected == null
            ? null
            : Math.abs(Math.log1p(Math.max(0, expected)) - Math.log1p(actualValue));
    jdbc.sql(
            """
            INSERT INTO prediction_audits
              (prediction_id,horizon_minutes,actual_value,absolute_error,log_error,audit_payload)
            VALUES (:prediction,:horizon,:actual,:absolute,:log,CAST(:payload AS jsonb))
            ON CONFLICT (prediction_id,horizon_minutes) DO NOTHING
            """)
        .param("prediction", id)
        .param("horizon", horizonMinutes)
        .param("actual", actualValue)
        .param("absolute", absoluteError, java.sql.Types.DOUBLE)
        .param("log", logError, java.sql.Types.DOUBLE)
        .param(
            "payload", "{\"expectedAvailable\":" + (expected != null) + ",\"source\":\"observed\"}")
        .update();
    entity.markEvaluated();
    return map(predictions.saveAndFlush(entity));
  }

  private Double expectedValue(Map<String, Object> payload, int horizonMinutes) {
    Object rawTargets = payload.get("targets");
    if (!(rawTargets instanceof List<?> targets)) return null;
    for (Object rawTarget : targets) {
      if (!(rawTarget instanceof Map<?, ?> target)) continue;
      Object horizon = target.get("horizonMinutes");
      Object expected = target.get("expectedValue");
      if (horizon instanceof Number number
          && number.intValue() == horizonMinutes
          && expected instanceof Number value) return value.doubleValue();
    }
    return null;
  }

  private PredictionView map(PredictionEntity p) {
    return new PredictionView(
        p.getId(),
        p.getVideoId(),
        p.getPlatform(),
        p.getPredictionType(),
        p.getStatus(),
        p.getModelVersion(),
        p.getDatasetVersion(),
        p.getFeatureVersion(),
        p.getKnowledgeCutoff(),
        p.getPayload(),
        p.getConfidence(),
        p.getComparableSampleSize(),
        p.getLockedAt());
  }

  public record PredictionView(
      UUID id,
      UUID videoId,
      String platform,
      PredictionType predictionType,
      PredictionStatus status,
      String modelVersion,
      String datasetVersion,
      String featureVersion,
      java.time.Instant knowledgeCutoff,
      java.util.Map<String, Object> payload,
      String confidence,
      int comparableSampleSize,
      java.time.Instant lockedAt) {}
}
