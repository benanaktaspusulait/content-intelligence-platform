package com.pompom.creative.postrender;

import java.util.List;
import java.util.Map;

public record PostRenderAssessment(
    String grade,
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
