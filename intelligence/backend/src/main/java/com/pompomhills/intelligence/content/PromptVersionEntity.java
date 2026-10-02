package com.pompomhills.intelligence.content;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "prompt_versions")
public class PromptVersionEntity {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(fetch = FetchType.LAZY, optional = false)
  @JoinColumn(name = "content_id", nullable = false)
  private ContentEntity content;

  @Column(name = "version_number", nullable = false)
  private Integer versionNumber;

  @Column(name = "raw_text", nullable = false, columnDefinition = "TEXT")
  private String rawText;

  @Column(name = "parsed_ir", columnDefinition = "jsonb")
  private String parsedIr;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  protected PromptVersionEntity() {}

  public Long getId() {
    return id;
  }

  public ContentEntity getContent() {
    return content;
  }

  public Integer getVersionNumber() {
    return versionNumber;
  }

  public String getRawText() {
    return rawText;
  }

  public String getParsedIr() {
    return parsedIr;
  }
}
