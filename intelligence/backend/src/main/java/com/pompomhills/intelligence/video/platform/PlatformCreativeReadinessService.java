package com.pompomhills.intelligence.video.platform;

import com.pompomhills.intelligence.creative.CreativeAnalysisEntity;
import com.pompomhills.intelligence.creative.CreativeAnalysisRepository;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;

/** Read-only qualitative interpretation of canonical V5 evidence. */
@Service
public class PlatformCreativeReadinessService {
  private static final String PROFILE_VERSION = "platform-creative-profile-v1-hypothesis";
  private final CreativeAnalysisRepository analyses;

  public PlatformCreativeReadinessService(CreativeAnalysisRepository analyses) {
    this.analyses = analyses;
  }

  public Map<String, Object> assess(UUID videoId, String requestedPlatform) {
    String platform = normalizePlatform(requestedPlatform);
    CreativeAnalysisEntity analysis = analyses.findFirstByVideoIdOrderByCreatedAtDesc(videoId).orElse(null);
    if (analysis == null) {
      return Map.of("platform", platform, "readinessGrade", "INCOMPLETE", "readinessDecision", "INSUFFICIENT_EVIDENCE",
          "readinessRisk", "UNKNOWN", "assessmentCoverage", 0, "limitations", List.of("No completed V5 analysis exists."));
    }
    Map<String, Object> temporal = analysis.getTemporalProfile();
    Map<String, Object> canonical = map(temporal.get("canonicalAssessments"));
    Map<String, Object> dimensions = map(temporal.get("dimensions"));
    Map<String, Object> loop = map(canonical.getOrDefault("loop", temporal.get("loop")));
    Map<String, Object> hook = map(canonical.getOrDefault("hook", temporal.get("hook")));
    Map<String, Object> novelty = map(temporal.get("visualNovelty"));
    Map<String, Object> action = map(temporal.get("actionBeatNovelty"));
    Map<String, Object> repetition = map(temporal.get("repetitiveMotion"));
    Map<String, Object> payoff = map(canonical.getOrDefault("payoff", temporal.get("payoff")));
    Map<String, Object> trend = map(temporal.get("temporalTrend"));
    Map<String, Object> recovery = map(temporal.get("reboundEvidence"));
    Map<String, Object> temporalAssessment = map(canonical.get("temporalStructure"));

    List<Criterion> criteria = new ArrayList<>();
    criteria.add(criterion("OPENING_HOOK", importance(platform, "OPENING_HOOK"), value(hook, "strength", value(hook, "status", "UNKNOWN")),
        "The measured opening activity is interpreted as a platform hook signal, not a performance prediction."));
    criteria.add(criterion("VISUAL_NOVELTY", importance(platform, "VISUAL_NOVELTY"), value(dimensions, "visualNovelty", "UNKNOWN"),
        "Visual novelty is the shared V5 evidence of structural/perceptual change."));
    criteria.add(criterion("BEAT_NOVELTY", importance(platform, "BEAT_NOVELTY"), value(action, "combinedAssessment", "UNKNOWN"),
        "Observed beat novelty is interpreted qualitatively; semantic action evidence may be unavailable."));
    criteria.add(criterion("LOOP_CONTINUITY", importance(platform, "LOOP_CONTINUITY"), value(loop, "strength", value(loop, "overall", "UNKNOWN")),
        String.valueOf(loop.getOrDefault("summary", "Endpoint similarity and semantic loop continuity are fused."))));
    criteria.add(criterion("PAYOFF", importance(platform, "PAYOFF"), value(payoff, "strength", value(payoff, "status", "UNKNOWN")),
        String.valueOf(payoff.getOrDefault("summary", "Payoff combines semantic resolution and motion support."))));
    criteria.add(criterion("SEMANTIC_RESOLUTION", importance(platform, "SEMANTIC_RESOLUTION"), value(payoff, "semanticStatus", "UNKNOWN"),
        "Semantic resolution is read from the canonical payoff assessment, not motion rebound alone."));
    criteria.add(criterion("TEMPORAL_VARIATION", importance(platform, "TEMPORAL_VARIATION"), value(trend, "trendShape", "UNKNOWN"),
        "Temporal motion trend describes the asset and is not creative escalation."));
    criteria.add(criterion("LOCAL_RECOVERY", importance(platform, "LOCAL_RECOVERY"), value(temporalAssessment, "interpretation", value(recovery, "localRecoveryStatus", "UNKNOWN")),
        String.valueOf(temporalAssessment.getOrDefault("summary", "Local recovery is separate from final payoff."))));
    criteria.add(criterion("REPETITION", importance(platform, "REPETITION"), value(repetition, "classification", "UNKNOWN"),
        "Repetition evidence is a review signal, not a platform outcome."));

    int available = (int) criteria.stream().filter(item -> !"UNKNOWN".equals(item.evidenceStatus())).count();
    int coverage = Math.round(100f * available / criteria.size());
    long highRisks = criteria.stream().filter(item -> "HIGH".equals(item.strengthOrRisk())).count();
    long criticalUnknowns = criteria.stream().filter(item -> "CRITICAL".equals(item.importance()) && "UNKNOWN".equals(item.evidenceStatus())).count();
    long unknowns = criteria.stream().filter(item -> "UNKNOWN".equals(item.evidenceStatus())).count();
    String grade = coverage < 60 || criticalUnknowns > 0 ? "INCOMPLETE" : highRisks >= 3 ? "C" : highRisks >= 1 ? "B" : "A";
    String decision = grade.equals("INCOMPLETE") ? "INSUFFICIENT_EVIDENCE" : grade.equals("A") ? "STRONG_FIT" : grade.equals("B") ? "GOOD_FIT" : "MIXED_FIT";
    String risk = grade.equals("INCOMPLETE") || unknowns >= 3 ? "UNKNOWN" : highRisks >= 2 ? "HIGH" : highRisks == 1 ? "MEDIUM" : "LOW";
    List<String> strengths = criteria.stream().filter(item -> "STRENGTH".equals(item.strengthOrRisk())).map(Criterion::criterion).toList();
    List<String> risks = criteria.stream().filter(item -> "HIGH".equals(item.strengthOrRisk())).map(Criterion::criterion).toList();
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("videoId", videoId);
    result.put("platform", platform);
    result.put("profileVersion", PROFILE_VERSION);
    result.put("evidenceVersion", analysis.getAnalysisVersion());
    result.put("canonicalAssessmentVersion", canonical.getOrDefault("version", "LEGACY_V5_ONLY"));
    result.put("analyzerVersion", analysis.getPrimaryEngine());
    result.put("readinessGrade", grade);
    result.put("readinessDecision", decision);
    result.put("readinessRisk", risk);
    result.put("assessmentCoverage", coverage);
    result.put("strengths", strengths);
    result.put("risks", risks);
    result.put("neutralObservations", List.of("This lens does not use views, likes, retention, or prediction outputs."));
    result.put("criterionAssessments", criteria.stream().map(Criterion::toMap).toList());
    result.put("profilePolicy", policy(platform));
    result.put("comparisonNote", "All platforms consume the same canonical V5 evidence; only policy importance and interpretation differ.");
    result.put("verdict", verdict(grade, platform));
    result.put("limitations", canonical.isEmpty()
        ? List.of("Initial platform profile is a documented policy hypothesis.", "Canonical semantic fusion is unavailable for this historical row.")
        : List.of("Initial platform profile is a documented policy hypothesis.", "Platform performance is not inferred."));
    result.put("createdAt", Instant.now());
    return result;
  }

  private String verdict(String grade, String platform) {
    return grade.equals("INCOMPLETE") ? "Insufficient canonical evidence for a platform-fit assessment." :
        "Grade " + grade + " qualitative creative fit for " + platform + "; this is not a performance prediction.";
  }

  private Criterion criterion(String key, String importance, String evidence, String meaning) {
    boolean unknown = evidence == null || evidence.equals("UNKNOWN") || evidence.equals("NOT_EVALUATED") || evidence.equals("NOT_AVAILABLE");
    boolean weak = evidence.equals("WEAK") || evidence.equals("LOW") || evidence.equals("NONE") || evidence.equals("FAILED");
    String result = unknown ? "UNKNOWN" : weak ? "HIGH" : "STRENGTH";
    String recommendation = weak ? "Review this criterion before publishing for this platform." : unknown ? "Collect or link the missing canonical evidence; do not estimate it." : "No platform-specific correction is indicated by the current evidence.";
    return new Criterion(key, importance, unknown ? "UNKNOWN" : "AVAILABLE", "STRENGTH".equals(result) ? "SUPPORTIVE" : result, evidence, meaning, recommendation);
  }

  private String importance(String platform, String criterion) {
    return switch (platform) {
      case "INSTAGRAM_REELS" -> criterion.equals("OPENING_HOOK") ? "CRITICAL" :
          List.of("VISUAL_NOVELTY", "BEAT_NOVELTY", "LOOP_CONTINUITY", "PAYOFF").contains(criterion) ? "HIGH" : "MEDIUM";
      case "FACEBOOK_REELS" -> criterion.equals("OPENING_HOOK") ? "CRITICAL" :
          List.of("PAYOFF", "SEMANTIC_RESOLUTION", "VISUAL_NOVELTY", "BEAT_NOVELTY").contains(criterion) ? "HIGH" : "MEDIUM";
      case "TIKTOK" -> criterion.equals("OPENING_HOOK") ? "CRITICAL" :
          List.of("BEAT_NOVELTY", "LOOP_CONTINUITY", "LOCAL_RECOVERY").contains(criterion) ? "HIGH" : "MEDIUM";
      case "YOUTUBE_SHORTS" -> List.of("OPENING_HOOK", "PAYOFF", "SEMANTIC_RESOLUTION").contains(criterion) ? "CRITICAL" :
          List.of("BEAT_NOVELTY", "TEMPORAL_VARIATION").contains(criterion) ? "HIGH" : "MEDIUM";
      default -> "MEDIUM";
    };
  }

  private List<String> policy(String platform) {
    return switch (platform) {
      case "INSTAGRAM_REELS" -> List.of("CRITICAL: opening readability", "HIGH: novelty, beat novelty, loop, payoff", "MEDIUM: repetition, temporal variation, semantic resolution");
      case "FACEBOOK_REELS" -> List.of("CRITICAL: readable opening", "HIGH: payoff, semantic resolution, novelty, beat novelty", "MEDIUM: temporal structure, repetition, loop");
      case "TIKTOK" -> List.of("CRITICAL: immediate hook", "HIGH: beat novelty, continuity, loop, local recovery", "MEDIUM: novelty, repetition, payoff, semantic resolution");
      case "YOUTUBE_SHORTS" -> List.of("CRITICAL: opening clarity and resolution", "HIGH: progression, beat novelty, temporal arc", "MEDIUM: loop, novelty, repetition");
      default -> List.of();
    };
  }

  private String normalizePlatform(String value) {
    String normalized = value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
    return switch (normalized) {
      case "INSTAGRAM", "INSTAGRAM_REELS" -> "INSTAGRAM_REELS";
      case "FACEBOOK", "FACEBOOK_REELS" -> "FACEBOOK_REELS";
      case "TIKTOK" -> "TIKTOK";
      case "YOUTUBE", "YOUTUBE_SHORTS" -> "YOUTUBE_SHORTS";
      default -> throw new IllegalArgumentException("Unsupported platform: " + value);
    };
  }

  @SuppressWarnings("unchecked") private Map<String, Object> map(Object value) { return value instanceof Map<?, ?> m ? (Map<String, Object>) m : Map.of(); }
  private String value(Map<String, Object> map, String key, String fallback) { Object value = map.get(key); return value == null ? fallback : String.valueOf(value).toUpperCase(Locale.ROOT); }

  private record Criterion(String criterion, String importance, String evidenceStatus, String strengthOrRisk, String evidence, String meaning, String recommendation) {
    Map<String, Object> toMap() { return Map.of("criterion", criterion, "importance", importance, "evidenceStatus", evidenceStatus, "platformInterpretation", strengthOrRisk, "summary", evidence, "meaning", meaning, "recommendation", recommendation, "evidenceReferences", List.of("V5 temporal profile"), "limitations", List.of("Qualitative policy hypothesis")); }
  }
}
