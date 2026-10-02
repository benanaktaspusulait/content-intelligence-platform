package com.pompomhills.intelligence.video;

import com.pompomhills.intelligence.common.domain.AuditableEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "videos")
public class VideoEntity extends AuditableEntity {
  @Id private UUID id;

  @Column(nullable = false, unique = true, length = 64)
  private String contentHash;

  @Column(nullable = false)
  private String originalFilename;

  @Column(nullable = false, unique = true)
  private String relativePath;

  @Column(nullable = false)
  private long durationMs;

  @Column(nullable = false)
  private int width;

  @Column(nullable = false)
  private int height;

  @Column(nullable = false)
  private double fps;

  @Column(nullable = false)
  private double aspectRatio;

  @Column(nullable = false)
  private String codec;

  @Column(nullable = false)
  private boolean audioPresent;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private VideoStatus status;

  private UUID seriesId;

  @Column(nullable = false)
  private Instant ingestedAt;

  protected VideoEntity() {}

  public VideoEntity(
      UUID id,
      String contentHash,
      String originalFilename,
      String relativePath,
      long durationMs,
      int width,
      int height,
      double fps,
      double aspectRatio,
      String codec,
      boolean audioPresent,
      UUID seriesId,
      Instant ingestedAt) {
    this.id = id;
    this.contentHash = contentHash;
    this.originalFilename = originalFilename;
    this.relativePath = relativePath;
    this.durationMs = durationMs;
    this.width = width;
    this.height = height;
    this.fps = fps;
    this.aspectRatio = aspectRatio;
    this.codec = codec;
    this.audioPresent = audioPresent;
    this.seriesId = seriesId;
    this.ingestedAt = ingestedAt;
    this.status = VideoStatus.INGESTED;
  }

  public void markAnalysing() {
    status = VideoStatus.ANALYSING;
  }

  public void markAnalysed() {
    status = VideoStatus.ANALYSED;
  }

  public void markFailed() {
    status = VideoStatus.FAILED;
  }

  public UUID getId() {
    return id;
  }

  public String getContentHash() {
    return contentHash;
  }

  public String getOriginalFilename() {
    return originalFilename;
  }

  public String getRelativePath() {
    return relativePath;
  }

  public long getDurationMs() {
    return durationMs;
  }

  public int getWidth() {
    return width;
  }

  public int getHeight() {
    return height;
  }

  public double getFps() {
    return fps;
  }

  public double getAspectRatio() {
    return aspectRatio;
  }

  public String getCodec() {
    return codec;
  }

  public boolean isAudioPresent() {
    return audioPresent;
  }

  public VideoStatus getStatus() {
    return status;
  }

  public UUID getSeriesId() {
    return seriesId;
  }

  public Instant getIngestedAt() {
    return ingestedAt;
  }
}
