package com.pompom.creative.postrender;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Produces a deterministic ordinal assessment from post-render rule outcomes and evidence. */
@Component
public class PostRenderAssessmentAggregator {
  public static final String VERSION = "post-render-assessment-v1";

  public PostRenderAssessment aggregate(RenderEvidenceIR evidence, List<PostRenderRuleResult> results) {
    long evaluated = results.stream().filter(result -> result.outcome() != PostRenderOutcome.UNKNOWN
        && result.outcome() != PostRenderOutcome.SERVICE_ERROR).count();
    long unavailable = results.stream().filter(result -> result.outcome() == PostRenderOutcome.UNKNOWN
        || result.outcome() == PostRenderOutcome.SERVICE_ERROR).count();
    int coverage = results.isEmpty() ? 0 : (int) Math.round(evaluated * 100.0 / (evaluated + unavailable));

    boolean blockerFailure = results.stream().anyMatch(result -> result.severity() == PostRenderSeverity.BLOCKER
        && result.outcome() == PostRenderOutcome.FAIL);
    boolean serviceFailure = results.stream().anyMatch(result -> result.severity() == PostRenderSeverity.BLOCKER
        && result.outcome() == PostRenderOutcome.SERVICE_ERROR);
    boolean criticalFailure = results.stream().anyMatch(result -> result.severity() == PostRenderSeverity.CRITICAL
        && result.outcome() == PostRenderOutcome.FAIL);
    boolean review = results.stream().anyMatch(result -> result.reviewRequired()
        && !"UNMAPPED_ACTIVITY_DROP".equals(result.ruleId()));
    boolean warningFailure = results.stream().anyMatch(result -> result.severity() == PostRenderSeverity.WARNING
        && result.outcome() == PostRenderOutcome.FAIL
        && !"UNMAPPED_ACTIVITY_DROP".equals(result.ruleId()));
    boolean importantEvidenceMissing = results.stream().anyMatch(result ->
        (result.outcome() == PostRenderOutcome.UNKNOWN || result.outcome() == PostRenderOutcome.SERVICE_ERROR)
            && (result.family().equals("OPENING_STRUCTURE")
                || result.family().equals("PAYOFF_STRUCTURE")
                || result.family().equals("SEMANTIC_LOOP")
                || result.family().equals("CHARACTER_CONTINUITY")));

    String grade;
    if (serviceFailure || coverage < 80 || importantEvidenceMissing) grade = "INCOMPLETE";
    else if (blockerFailure) grade = "F";
    else if (criticalFailure) grade = "D";
    else if (review || warningFailure) grade = "C";
    else if (results.stream().anyMatch(result -> result.outcome() == PostRenderOutcome.FAIL)) grade = "B";
    else grade = "A";

    List<String> strengths = new ArrayList<>();
    List<String> concerns = new ArrayList<>();
    results.stream().filter(result -> result.outcome() == PostRenderOutcome.PASS)
        .limit(3).forEach(result -> strengths.add(result.message()));
    results.stream().filter(result -> result.outcome() == PostRenderOutcome.FAIL
        || result.outcome() == PostRenderOutcome.UNKNOWN
        || result.outcome() == PostRenderOutcome.SERVICE_ERROR)
        .limit(4).forEach(result -> concerns.add(result.message()));
    if (coverage < 100) concerns.add("Some required post-render evidence was unavailable; this assessment is not a complete creative verdict.");
    if (strengths.isEmpty()) strengths.add("No positive rule evidence was recorded.");
    if (concerns.isEmpty()) concerns.add("No rule-level concerns were recorded.");

    List<PostRenderAssessment.Insight> insights = new ArrayList<>();
    addMotionInsight(evidence, insights);
    addTemporalInsight(evidence, insights);
    addSimilarityInsight(evidence, insights);
    addPayoffInsight(evidence, insights);
    if (insights.isEmpty()) insights.add(new PostRenderAssessment.Insight(
        "Evidence coverage", "The assessment is limited to the evidence sources available at evaluation time.", "PARTIAL"));

    String experiment = grade.equals("A") || grade.equals("B")
        ? "Keep the current structure as the control and test one hook or payoff variation."
        : "Re-render one controlled variation that targets the highest-severity failed rule.";
    String hypothesis = grade.equals("A") || grade.equals("B")
        ? "A single controlled change can improve retention without changing the working structure."
        : "Addressing the blocking evidence gap or failed rule will improve post-render quality.";
    PostRenderAssessment.Recommendation recommendation = new PostRenderAssessment.Recommendation(
        experiment, hypothesis, List.of("opening retention", "completion rate", "average watch time"));

    String label = switch (grade) {
      case "A" -> "Strong post-render evidence";
      case "B" -> "Good with targeted improvement";
      case "C" -> "Needs review";
      case "D" -> "Major quality concern";
      case "F" -> "Blocking quality failure";
      default -> "Insufficient evidence";
    };
    String verdict = switch (grade) {
      case "A", "B" -> "The measured post-render evidence supports moving forward with a controlled experiment.";
      case "C", "D", "F" -> "The measured rule outcomes require review before treating this render as a reliable creative control.";
      default -> "Do not assign a final creative grade until the missing required evidence is available.";
    };
    return new PostRenderAssessment(grade, label, verdict, coverage, VERSION,
        List.copyOf(strengths), List.copyOf(concerns), List.copyOf(insights), recommendation);
  }

  private void addMotionInsight(RenderEvidenceIR evidence, List<PostRenderAssessment.Insight> target) {
    Object score = evidence.valueAt("motion.motionHeuristicScore");
    Object density = evidence.valueAt("motion.motionIntervalDensity");
    if (score instanceof Number || density instanceof Number) {
      target.add(new PostRenderAssessment.Insight("Motion evidence",
          "The motion analyzer reports measurable visual change; this is evidence of movement only, not proof of story quality or retention.",
          evidence.statusAt("motion").name()));
    }
  }

  private void addSimilarityInsight(RenderEvidenceIR evidence, List<PostRenderAssessment.Insight> target) {
    Object similarity = evidence.valueAt("visualSimilarity.firstLastSimilarity");
    if (similarity instanceof Number value) {
      String detail = value.doubleValue() >= 0.75
          ? "Opening and ending frames are visually similar, which supports loop continuity but does not prove a semantic loop."
          : "Opening and ending frames are not strongly similar, so no visual loop signal was established.";
      target.add(new PostRenderAssessment.Insight("Opening/ending relationship", detail,
          evidence.statusAt("visualSimilarity").name()));
    }
  }

  private void addTemporalInsight(RenderEvidenceIR evidence, List<PostRenderAssessment.Insight> target) {
    Object profileValue = evidence.valueAt("temporal.profile");
    if (!(profileValue instanceof Map<?, ?> profile)) return;
    Object variation = profile.get("variation");
    Object dropsValue = evidence.valueAt("temporal.activityDrops");
    Object unmappedValue = evidence.valueAt("temporal.unmappedActivityDrops");
    int drops = dropsValue instanceof List<?> values ? values.size() : 0;
    int unmapped = unmappedValue instanceof List<?> values ? values.size() : 0;
    String variationText = variation == null ? "unknown" : String.valueOf(variation).toLowerCase().replace('_', ' ');
    if (unmapped > 0) {
      target.add(new PostRenderAssessment.Insight("Local motion changes",
          "The timeline contains " + unmapped + " unmapped activity drop candidate(s) within " + variationText
              + " motion. This describes measured visual change only; it does not establish a story problem or a retention effect. Review the timestamp against the edit plan.",
          "AVAILABLE"));
    } else if (drops > 0) {
      target.add(new PostRenderAssessment.Insight("Planned motion changes",
          "The timeline contains " + drops + " local activity drop candidate(s), and available plan timing provides lineage for them. This is measured motion evidence, not a performance claim.",
          "AVAILABLE"));
    } else {
      target.add(new PostRenderAssessment.Insight("Motion timeline",
          "The sampled timeline is " + variationText + " with no substantial two-sided local activity drop detected. This does not evaluate story intent, dialogue, or retention.",
          "AVAILABLE"));
    }
  }

  private void addPayoffInsight(RenderEvidenceIR evidence, List<PostRenderAssessment.Insight> target) {
    Object status = evidence.valueAt("payoff.status");
    Object direction = evidence.valueAt("payoffContrast.contrastDirection");
    Object magnitude = evidence.valueAt("payoffContrast.contrastMagnitude");
    if ("RESOLVED".equals(status) && magnitude instanceof Number value && value.doubleValue() < 0.1) {
      target.add(new PostRenderAssessment.Insight("Payoff visual emphasis",
          "Motion remains at a similar level before, during and after the planned payoff. The main beat may be harder to isolate; test a short readable hold or one isolated reaction.", "AVAILABLE"));
    } else if ("RESOLVED".equals(status)) {
      target.add(new PostRenderAssessment.Insight("Payoff window",
          "An explicit payoff window was resolved and the local profile shows " + direction + " contrast with magnitude " + magnitude + ". This is visual evidence, not a retention claim.", "AVAILABLE"));
    } else {
      target.add(new PostRenderAssessment.Insight("Payoff window",
          "No explicit, timestamped payoff window was available, so payoff emphasis was not inferred from motion alone.", String.valueOf(status)));
    }
  }
}
