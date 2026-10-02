package com.pompomhills.intelligence.creative;

import com.pompomhills.intelligence.video.VideoEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "creative_fingerprints")
public class CreativeFingerprintEntity {
  @Id @GeneratedValue private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "video_id")
  private VideoEntity video;

  @OneToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "analysis_id")
  private CreativeAnalysisEntity analysis;

  @Column(nullable = false)
  private String featureVersion;

  @Column(nullable = false)
  private double creativeQualityScore;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(nullable = false, columnDefinition = "jsonb")
  private Map<String, Object> features;

  @CreationTimestamp
  @Column(nullable = false, updatable = false)
  private Instant createdAt;

  protected CreativeFingerprintEntity() {}

  public CreativeFingerprintEntity(
      VideoEntity video,
      CreativeAnalysisEntity analysis,
      String featureVersion,
      double score,
      Map<String, Object> features) {
    this.video = video;
    this.analysis = analysis;
    this.featureVersion = featureVersion;
    this.creativeQualityScore = score;
    this.features = features;
  }

  public String getFeatureVersion() {
    return featureVersion;
  }

  public Map<String, Object> getFeatures() {
    return features;
  }

  public double getCreativeQualityScore() {
    return creativeQualityScore;
  }
}
