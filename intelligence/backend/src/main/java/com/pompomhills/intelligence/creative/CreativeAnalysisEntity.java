package com.pompomhills.intelligence.creative;

import com.pompomhills.intelligence.video.VideoEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "creative_analyses")
public class CreativeAnalysisEntity {
  @Id @GeneratedValue private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "video_id")
  private VideoEntity video;

  @Column(nullable = false)
  private String analysisVersion;

  @Column(nullable = false)
  private String analysisType;

  @Column(nullable = false)
  private String primaryEngine;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  private List<String> secondaryEngines;

  @Column(nullable = false)
  private String classification;

  @Column(nullable = false)
  private double actionDnaScore;

  @Column(nullable = false)
  private double confidence;

  @Column(nullable = false)
  private String reason;

  private String storyboardPath;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  private List<Map<String, Object>> timeline;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  private Map<String, Object> rawResult;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private Instant createdAt;

  protected CreativeAnalysisEntity() {}

  public CreativeAnalysisEntity(
      VideoEntity video,
      String analysisVersion,
      String analysisType,
      String primaryEngine,
      List<String> secondaryEngines,
      String classification,
      double actionDnaScore,
      double confidence,
      String reason,
      String storyboardPath,
      List<Map<String, Object>> timeline,
      Map<String, Object> rawResult) {
    this.video = video;
    this.analysisVersion = analysisVersion;
    this.analysisType = analysisType;
    this.primaryEngine = primaryEngine;
    this.secondaryEngines = secondaryEngines;
    this.classification = classification;
    this.actionDnaScore = actionDnaScore;
    this.confidence = confidence;
    this.reason = reason;
    this.storyboardPath = storyboardPath;
    this.timeline = timeline;
    this.rawResult = rawResult;
  }

  public UUID getId() {
    return id;
  }

  public VideoEntity getVideo() {
    return video;
  }

  public String getAnalysisVersion() {
    return analysisVersion;
  }

  public String getAnalysisType() {
    return analysisType;
  }

  public Double getMotionHeuristicScore() {
    return actionDnaScore;
  }

  public Double getMeasurementConfidence() {
    return confidence;
  }

  public Map<String, Object> getMeasurementQuality() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("measurementQuality"));
  }

  public Map<String, Object> getSampling() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("sampling"));
  }

  public Map<String, Object> getMotion() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("motion"));
  }

  public Map<String, Object> getVisualSimilarity() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("visualSimilarity"));
  }

  public List<Map<String, Object>> getDarkFrameCandidates() {
    if (rawResult == null || !(rawResult.get("darkFrameCandidates") instanceof List<?> values)) return List.of();
    return values.stream().filter(Map.class::isInstance).map(value -> (Map<String, Object>) value).toList();
  }

  public List<Map<String, Object>> getTimeline() {
    return timeline == null ? List.of() : timeline;
  }

  public Map<String, Object> getTemporalProfile() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("temporalProfile"));
  }

  public Map<String, Object> getPresentation() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("presentation"));
  }

  public Map<String, Object> getSemanticVideoEvidence() {
    return rawResult == null ? Map.of() : castMap(rawResult.get("semanticVideoEvidence"));
  }

  @SuppressWarnings("unchecked")
  public Map<String, Object> getRawResult() {
    return rawResult == null ? Map.of() : rawResult;
  }

  public void updateRawResult(Map<String, Object> value) {
    this.rawResult = value;
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> castMap(Object value) {
    return value instanceof Map<?, ?> map ? (Map<String, Object>) map : Map.of();
  }

  public String getPrimaryEngine() {
    return primaryEngine;
  }

  public List<String> getSecondaryEngines() {
    return secondaryEngines;
  }

  public String getClassification() {
    return classification;
  }

  public double getActionDnaScore() {
    return actionDnaScore;
  }

  public double getConfidence() {
    return confidence;
  }

  public String getReason() {
    return reason;
  }

  public String getStoryboardPath() {
    return storyboardPath;
  }

  public void updateFrom(
      String analysisType,
      String primaryEngine,
      List<String> secondaryEngines,
      String classification,
      double actionDnaScore,
      double confidence,
      String reason,
      String storyboardPath,
      List<Map<String, Object>> timeline,
      Map<String, Object> rawResult) {
    this.analysisType = analysisType;
    this.primaryEngine = primaryEngine;
    this.secondaryEngines = secondaryEngines;
    this.classification = classification;
    this.actionDnaScore = actionDnaScore;
    this.confidence = confidence;
    this.reason = reason;
    this.storyboardPath = storyboardPath;
    this.timeline = timeline;
    this.rawResult = rawResult;
  }
}
