package com.pompomhills.intelligence.prediction;

import com.pompomhills.intelligence.common.domain.AuditableEntity;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "predictions")
public class PredictionEntity extends AuditableEntity {
  @Id private UUID id;

  @Column(nullable = false)
  private UUID videoId;

  private UUID variantId;

  @Column(nullable = false)
  private String platform;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PredictionType predictionType;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private PredictionStatus status;

  @Column(nullable = false)
  private String modelVersion;

  @Column(nullable = false)
  private String datasetVersion;

  @Column(nullable = false)
  private String featureVersion;

  @Column(nullable = false)
  private Instant knowledgeCutoff;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  private Map<String, Object> payload;

  @Column(nullable = false)
  private String confidence;

  @Column(nullable = false)
  private int comparableSampleSize;

  private Instant lockedAt;
  private String lockReason;

  protected PredictionEntity() {}

  public PredictionEntity(
      UUID id,
      UUID videoId,
      String platform,
      PredictionType type,
      String modelVersion,
      String datasetVersion,
      String featureVersion,
      Instant cutoff,
      Map<String, Object> payload,
      String confidence,
      int sample) {
    this.id = id;
    this.videoId = videoId;
    this.platform = platform;
    this.predictionType = type;
    this.status = PredictionStatus.DRAFT;
    this.modelVersion = modelVersion;
    this.datasetVersion = datasetVersion;
    this.featureVersion = featureVersion;
    this.knowledgeCutoff = cutoff;
    this.payload = payload;
    this.confidence = confidence;
    this.comparableSampleSize = sample;
  }

  public void lock(Instant at, String reason) {
    if (status != PredictionStatus.DRAFT)
      throw new IllegalStateException("Only draft predictions can be locked");
    status = PredictionStatus.LOCKED;
    lockedAt = at;
    lockReason = reason;
  }

  public void markEvaluated() {
    if (status != PredictionStatus.LOCKED)
      throw new IllegalStateException("Only locked predictions can be evaluated");
    status = PredictionStatus.EVALUATED;
  }

  public UUID getId() {
    return id;
  }

  public UUID getVideoId() {
    return videoId;
  }

  public String getPlatform() {
    return platform;
  }

  public PredictionType getPredictionType() {
    return predictionType;
  }

  public PredictionStatus getStatus() {
    return status;
  }

  public String getModelVersion() {
    return modelVersion;
  }

  public String getDatasetVersion() {
    return datasetVersion;
  }

  public String getFeatureVersion() {
    return featureVersion;
  }

  public Instant getKnowledgeCutoff() {
    return knowledgeCutoff;
  }

  public Map<String, Object> getPayload() {
    return payload;
  }

  public String getConfidence() {
    return confidence;
  }

  public int getComparableSampleSize() {
    return comparableSampleSize;
  }

  public Instant getLockedAt() {
    return lockedAt;
  }
}
