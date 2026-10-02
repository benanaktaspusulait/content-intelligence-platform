package com.pompom.creative.api.dto;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.Builder;
import lombok.Data;

/** DTO for render job API responses. */
@Data
@Builder
public class RenderJobDto {

  private UUID id;
  private Long contentId;
  private String contentTitle;
  private Long promptVersionId;
  private Integer promptVersionNumber;
  private String jobType;
  private String status;
  private Integer attemptNumber;
  private Integer maxAttempts;
  private String openartJobId;
  private BigDecimal creditsEstimated;
  private BigDecimal creditsActual;
  private Instant queuedAt;
  private Instant startedAt;
  private Instant completedAt;
  private Instant failedAt;
  private String errorCode;
  private String errorMessage;
  private QaResultDto qaResult;

  @Data
  @Builder
  public static class QaResultDto {
    private UUID id;
    private String decision;
    private String decisionReason;
    private Integer complianceScore;
    private Double confidence;
    private Boolean hasDeadAir;
    private Boolean characterIdentityVerified;
    private String characterIdentityIssues;
    private Boolean requiresHumanReview;
  }
}
