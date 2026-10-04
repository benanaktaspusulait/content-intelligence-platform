package com.pompom.creative.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** Immutable audit entry for a human decision on uncertain post-render QA. */
@Entity
@Table(name = "qa_human_reviews")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QaHumanReview {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(optional = false)
  @JoinColumn(name = "render_qa_result_id", nullable = false, updatable = false)
  private RenderQaResult renderQaResult;

  @Enumerated(EnumType.STRING)
  @Column(name = "decision", nullable = false, length = 30, updatable = false)
  private Decision decision;

  @Column(name = "reviewer", nullable = false, length = 200, updatable = false)
  private String reviewer;

  @Column(name = "notes", columnDefinition = "TEXT", updatable = false)
  private String notes;

  @Column(name = "created_at", nullable = false, updatable = false)
  @Builder.Default
  private Instant createdAt = Instant.now();

  public enum Decision {
    APPROVED,
    REJECTED,
    RERENDER_REQUESTED
  }
}
