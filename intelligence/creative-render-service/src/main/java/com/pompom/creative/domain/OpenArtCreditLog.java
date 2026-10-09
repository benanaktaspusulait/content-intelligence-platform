package com.pompom.creative.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.*;

@Entity
@Table(name = "openart_credit_log")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OpenArtCreditLog {

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @ManyToOne(fetch = FetchType.LAZY)
  @JoinColumn(name = "render_job_id")
  private RenderJob renderJob;

  @Column(name = "prompt_version_id")
  private Long promptVersionId;

  @Column(name = "job_type", length = 50)
  private String jobType;

  @Column(name = "openart_job_id", length = 100)
  private String openartJobId;

  @Column(name = "openart_model", length = 100)
  private String openartModel;

  @Column(name = "operation", nullable = false, length = 50)
  private String operation;

  @org.hibernate.annotations.JdbcTypeCode(org.hibernate.type.SqlTypes.JSON)
  @Column(name = "operation_metadata", columnDefinition = "jsonb")
  private String operationMetadata;

  @Column(name = "credits_before", precision = 10, scale = 2)
  private BigDecimal creditsBefore;

  @Column(name = "credits_spent", nullable = false, precision = 10, scale = 2)
  @Builder.Default
  private BigDecimal creditsSpent = BigDecimal.ZERO;

  @Column(name = "credits_used", nullable = false, precision = 10, scale = 2)
  @Builder.Default
  private BigDecimal creditsUsed = BigDecimal.ZERO;

  @Column(name = "credits_after", precision = 10, scale = 2)
  private BigDecimal creditsAfter;

  @Column(name = "logged_at", nullable = false)
  @Builder.Default
  private Instant loggedAt = Instant.now();
}
