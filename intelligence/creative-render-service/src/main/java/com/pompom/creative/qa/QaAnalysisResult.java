package com.pompom.creative.qa;

import java.util.List;
import lombok.Builder;
import lombok.Data;

/** Aggregated QA analysis result from Python ML service. */
@Data
@Builder
public class QaAnalysisResult {

  // Dead air analysis
  private boolean hasDeadAir;
  private List<DeadAirSegment> deadAirSegments;
  private int deadAirDurationMs;

  // Character identity verification
  private boolean characterIdentityVerified;
  private double confidence;
  private String characterIdentityIssues;
  private String reasoning;

  // Compliance score (calculated)
  private int complianceScore;

  @Data
  @Builder
  public static class DeadAirSegment {
    private int startMs;
    private int endMs;
    private double duration;
  }
}
