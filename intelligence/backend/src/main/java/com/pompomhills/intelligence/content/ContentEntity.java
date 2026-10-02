package com.pompomhills.intelligence.content;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "contents")
public class ContentEntity {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false, length = 255)
  private String title;

  @Column(columnDefinition = "TEXT")
  private String description;

  @Enumerated(EnumType.STRING)
  @Column(name = "type", nullable = false)
  private ContentType contentType;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private ContentStatus status;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  protected ContentEntity() {}

  public Long getId() {
    return id;
  }

  public String getTitle() {
    return title;
  }

  public ContentType getContentType() {
    return contentType;
  }

  public ContentStatus getStatus() {
    return status;
  }

  public enum ContentType {
    EPISODE,
    SHORT,
    REEL
  }

  public enum ContentStatus {
    DRAFT,
    VALIDATING,
    RENDER_READY,
    RENDERING,
    RENDERED,
    PUBLISHED
  }
}
