package com.pompomhills.intelligence.video;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "video_variants")
public class VideoVariantEntity {
  @Id @GeneratedValue private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "video_id")
  private VideoEntity video;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "parent_variant_id")
  private VideoVariantEntity parentVariant;

  @Enumerated(EnumType.STRING)
  @Column(name = "variant_type", nullable = false)
  private VideoVariantType variantType;

  @Column(name = "generated_path", nullable = false, unique = true)
  private String generatedPath;

  @JdbcTypeCode(SqlTypes.JSON)
  @Column(name = "edit_operations", nullable = false, columnDefinition = "jsonb")
  private List<Object> editOperations;

  @CreationTimestamp
  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  protected VideoVariantEntity() {}

  public VideoVariantEntity(
      VideoEntity video,
      VideoVariantEntity parentVariant,
      VideoVariantType variantType,
      String generatedPath,
      List<Object> editOperations) {
    this.video = video;
    this.parentVariant = parentVariant;
    this.variantType = variantType;
    this.generatedPath = generatedPath;
    this.editOperations = editOperations;
  }

  public UUID getId() {
    return id;
  }

  public VideoEntity getVideo() {
    return video;
  }

  public VideoVariantEntity getParentVariant() {
    return parentVariant;
  }

  public VideoVariantType getVariantType() {
    return variantType;
  }

  public String getGeneratedPath() {
    return generatedPath;
  }

  public List<Object> getEditOperations() {
    return editOperations;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }
}
