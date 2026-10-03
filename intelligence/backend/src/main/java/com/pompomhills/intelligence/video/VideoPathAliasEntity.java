package com.pompomhills.intelligence.video;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.CreationTimestamp;

@Entity
@Table(name = "video_path_aliases")
public class VideoPathAliasEntity {
  @Id @GeneratedValue private UUID id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "video_id")
  private VideoEntity video;

  @Column(name = "relative_path", nullable = false, unique = true)
  private String relativePath;

  @Column(name = "content_hash", nullable = false, length = 64)
  private String contentHash;

  @CreationTimestamp
  @Column(name = "discovered_at", nullable = false, updatable = false)
  private Instant discoveredAt;

  protected VideoPathAliasEntity() {}

  public VideoPathAliasEntity(VideoEntity video, String relativePath, String contentHash) {
    this.video = video;
    this.relativePath = relativePath;
    this.contentHash = contentHash;
  }

  public UUID getId() {
    return id;
  }

  public VideoEntity getVideo() {
    return video;
  }

  public String getRelativePath() {
    return relativePath;
  }

  public String getContentHash() {
    return contentHash;
  }

  public Instant getDiscoveredAt() {
    return discoveredAt;
  }
}
