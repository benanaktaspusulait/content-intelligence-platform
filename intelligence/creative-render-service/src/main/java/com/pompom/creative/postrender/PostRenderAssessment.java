package com.pompom.creative.postrender;

import java.util.List;

public record PostRenderAssessment(
    String grade,
    String decision,
    String risk,
    String recommendedAction,
    String label,
    String verdict,
    int evidenceCoveragePercent,
    String assessmentVersion,
    List<String> strengths,
    List<String> concerns,
    List<Insight> insights,
    Recommendation recommendation) {
  public record Insight(String title, String detail, String evidenceStatus) {}

  public record Recommendation(String experiment, String hypothesis, List<String> measures) {}
}
