package com.pompom.creative.postrender;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Aligns local motion candidates to explicit plan beats without inferring story intent. */
@Service
public class TemporalBeatAlignmentService {
  public Map<String, Object> align(Map<String, Object> profile, Map<String, Object> contract) {
    List<Map<String, Object>> beats = beats(contract);
    List<Map<String, Object>> drops = alignCandidates(maps(profile.get("activityDrops")), beats, "DROP");
    List<Map<String, Object>> spikes = alignCandidates(maps(profile.get("activitySpikes")), beats, "SPIKE");
    List<Map<String, Object>> unmapped = drops.stream()
        .filter(candidate -> candidate.get("classification").toString().startsWith("UNMAPPED"))
        .toList();
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("profile", profile);
    result.put("activityDrops", drops);
    result.put("activitySpikes", spikes);
    result.put("unmappedActivityDrops", unmapped);
    result.put("alignmentStatus", profile.isEmpty() ? "UNKNOWN" : beats.isEmpty() ? "NO_PLAN_BEATS" : "AVAILABLE");
    if (contract == null || contract.isEmpty()) {
      result.putAll(Map.of(
          "planAvailability", Map.of("status", "PLAN_NOT_AVAILABLE", "reason", "No immutable production contract is linked to this render."),
          "plannedActionNovelty", Map.of("status", "NOT_EVALUATED", "reason", "No validated creative plan is linked to this asset."),
          "observedVisualBeatNovelty", Map.of("status", "UNKNOWN", "reason", "Observed visual beat novelty requires planned beat windows."),
          "actionBeatNovelty", Map.of("status", "PLAN_NOT_AVAILABLE", "reason", "No validated creative plan is linked to this asset."),
          "planRenderFidelity", unavailableFidelity("PLAN_NOT_AVAILABLE", "No validated creative plan is linked to this asset, so plan/render fidelity cannot be evaluated.")));
    } else {
      result.putAll(actionEvidence(beats, profile));
    }
    return result;
  }

  private Map<String, Object> actionEvidence(List<Map<String, Object>> beats, Map<String, Object> profile) {
    List<String> actions = beats.stream().map(beat -> String.valueOf(beat.get("plannedAction")))
        .filter(action -> !"UNKNOWN".equals(action)).toList();
    if (actions.isEmpty()) {
      return Map.of(
          "plannedActionNovelty", Map.of("status", "NOT_EVALUATED", "reason", "No structured primary actions were present in the validated plan."),
          "observedVisualBeatNovelty", Map.of("status", "UNKNOWN", "reason", "No planned action windows were available for visual comparison."),
          "actionBeatNovelty", Map.of("status", "NOT_EVALUATED", "reason", "No structured primary actions were present in the validated plan."),
          "planRenderFidelity", unavailableFidelity("NOT_EVALUATED", "The production contract is linked, but it contains no timestamped primary actions."));
    }
    List<String> strategies = beats.stream().map(beat -> normalizeStrategy(String.valueOf(beat.get("plannedAction"))))
        .filter(action -> !"UNKNOWN".equals(action)).toList();
    long distinct = strategies.stream().distinct().count();
    double repetitionRatio = 1.0 - distinct / (double) actions.size();
    String actionStatus = distinct >= 3 ? "STRONG" : distinct == 2 ? "MODERATE" : "WEAK";
    Map<String, Object> observed = observedVisualBeatNovelty(beats, profile);
    Map<String, Object> fidelity = fidelity(beats, profile, actionStatus, observed);
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("plannedActionSequence", actions);
    result.put("plannedActionCount", actions.size());
    result.put("actionBeatCount", beats.size());
    result.put("distinctPrimaryActionCount", distinct);
    result.put("distinctStrategyClassCount", distinct);
    result.put("repeatedStrategyCount", actions.size() - distinct);
    result.put("strategyDiversity", round(distinct / (double) strategies.size()));
    result.put("repetitionRatio", round(repetitionRatio));
    result.put("plannedActionNovelty", Map.of("status", actionStatus, "planned", actions, "strategies", strategies,
        "reason", "Strategy classes were normalized from the immutable production contract."));
    result.put("observedVisualBeatNovelty", observed);
    result.put("actionBeatNovelty", Map.of("status", observed.get("status"), "planned", actionStatus,
        "observedVisually", observed.get("status"), "semanticActionStatus", "NOT_EVALUATED",
        "semanticActionReason", "No semantic action-recognition provider is configured."));
    result.put("planRenderFidelity", fidelity);
    return result;
    }

  private Map<String, Object> observedVisualBeatNovelty(List<Map<String, Object>> beats, Map<String, Object> profile) {
    List<Map<String, Object>> signatures = observedSignatures(beats, profile);
    if (signatures.isEmpty()) return Map.of("status", "UNKNOWN", "reason", "V4 temporal evidence did not cover the planned beat windows.");
    List<Map<String, Object>> transitions = new ArrayList<>();
    for (int index = 1; index < signatures.size(); index++) {
      Map<String, Object> before = signatures.get(index - 1);
      Map<String, Object> after = signatures.get(index);
      double change = Math.abs(number(after.get("averageMotion")) - number(before.get("averageMotion")))
          + Math.abs(number(after.get("visualNovelty")) - number(before.get("visualNovelty")));
      transitions.add(Map.of("fromBeatId", before.get("beatId"), "toBeatId", after.get("beatId"), "changeMagnitude", round(change),
          "status", change >= 0.22 ? "DISTINCT" : change >= 0.10 ? "MODERATE" : "SIMILAR"));
    }
    long distinct = transitions.stream().filter(item -> "DISTINCT".equals(item.get("status"))).count();
    String status = distinct == transitions.size() && !transitions.isEmpty() ? "STRONG" : distinct > 0 ? "MODERATE" : "WEAK";
    return Map.of("status", status, "beatSignatures", signatures, "adjacentTransitions", transitions,
        "reason", "Visual beat distinctness is based on motion, medium-range novelty, and state persistence; it does not identify semantic actions.");
  }

  private List<Map<String, Object>> observedSignatures(List<Map<String, Object>> beats, Map<String, Object> profile) {
    List<Map<String, Object>> segments = maps(profile.get("segments"));
    Map<String, Object> novelty = map(profile.get("visualNovelty"));
    List<Map<String, Object>> points = maps(novelty.get("points"));
    List<Map<String, Object>> signatures = new ArrayList<>();
    for (Map<String, Object> beat : beats) {
      double start = number(beat.get("startSeconds")), end = number(beat.get("endSeconds"));
      List<Map<String, Object>> local = segments.stream().filter(segment -> overlap(start, end, number(segment.get("startSeconds")), number(segment.get("endSeconds"))) > 0).toList();
      if (local.isEmpty()) continue;
      double averageMotion = local.stream().mapToDouble(item -> number(item.get("averageMotion"))).average().orElse(0.0);
      double variation = local.stream().mapToDouble(item -> number(item.get("motionVariability"))).average().orElse(0.0);
      double visualNovelty = points.stream().filter(point -> number(point.get("timestamp")) >= start && number(point.get("timestamp")) <= end)
          .mapToDouble(point -> number(point.get("novelty"))).average().orElse(0.0);
      double stateChange = Math.min(1.0, Math.abs(averageMotion - visualNovelty) + visualNovelty);
      Map<String, Object> signature = new LinkedHashMap<>();
      signature.put("beatId", beat.get("id"));
      signature.put("observedStart", start);
      signature.put("observedEnd", end);
      signature.put("averageMotion", round(averageMotion));
      signature.put("motionVariation", round(variation));
      signature.put("visualNovelty", round(visualNovelty));
      signature.put("statePersistence", round(1.0 - visualNovelty));
      signature.put("stateChangeMagnitude", round(stateChange));
      signature.put("entryStateFingerprint", round(averageMotion));
      signature.put("exitStateFingerprint", round(visualNovelty));
      signature.put("evidenceQuality", "V4_VISUAL_WINDOW");
      signatures.add(signature);
    }
    return signatures;
  }

  private Map<String, Object> fidelity(List<Map<String, Object>> beats, Map<String, Object> profile, String plannedStatus, Map<String, Object> observed) {
    if (profile.isEmpty() || maps(profile.get("segments")).isEmpty()) {
      return unavailableFidelity("VISUAL_EVIDENCE_UNAVAILABLE", "No rendered V4 temporal windows are available.");
    }
    Map<String, Object> dimensions = new LinkedHashMap<>();
    dimensions.put("opening", dimension("MATCH", "The first planned beat has a corresponding sampled window.", "NO_ACTION"));
    dimensions.put("mechanic", dimension("MATCH", "A structured mechanic intent is present in the production contract.", "NO_ACTION"));
    String observedStatus = String.valueOf(observed.get("status"));
    String attempts = "STRONG".equals(plannedStatus) && "WEAK".equals(observedStatus) ? "PARTIAL_MATCH" :
        "WEAK".equals(plannedStatus) ? "UNKNOWN" : "STRONG".equals(observedStatus) ? "MATCH" : "PARTIAL_MATCH";
    dimensions.put("attempts", dimension(attempts, "Planned strategy changes were compared with adjacent visual beat signatures.", "PARTIAL_MATCH".equals(attempts) ? "REGENERATE" : "HUMAN_REVIEW"));
    dimensions.put("progression", dimension(attempts, "Visual progression was evaluated without claiming semantic action identity.", "REGENERATE"));
    dimensions.put("payoff", dimension("UNKNOWN", "Payoff fidelity is evaluated by the payoff analyzer separately.", "HUMAN_REVIEW"));
    dimensions.put("loop", dimension("UNKNOWN", "Semantic loop intent is not proven by pixel similarity alone.", "HUMAN_REVIEW"));
    dimensions.put("character", dimension("NOT_EVALUATED", "No character continuity evaluator is configured in this path.", "HUMAN_REVIEW"));
    dimensions.put("visualStyle", dimension("NOT_EVALUATED", "No visual-style evaluator is configured in this path.", "HUMAN_REVIEW"));
    long evaluated = dimensions.values().stream().map(item -> String.valueOf(((Map<?, ?>) item).get("status")))
        .filter(status -> !status.equals("UNKNOWN") && !status.equals("NOT_EVALUATED") && !status.equals("NOT_APPLICABLE")).count();
    long applicable = dimensions.values().stream().map(item -> String.valueOf(((Map<?, ?>) item).get("status")))
        .filter(status -> !status.equals("NOT_APPLICABLE") && !status.equals("NOT_EVALUATED")).count();
    String overall = attempts.equals("MATCH") ? "MATCH" : attempts.equals("PARTIAL_MATCH") ? "PARTIAL_MATCH" : "UNKNOWN";
    String rootCause = "WEAK".equals(observedStatus) && "STRONG".equals(plannedStatus) ? "RENDER_FIDELITY_ISSUE" : "UNKNOWN";
    return Map.of("status", overall, "coverage", round(evaluated * 100.0 / Math.max(applicable, 1)), "dimensions", dimensions,
        "rootCause", rootCause, "recommendedActionType", rootCause.equals("RENDER_FIDELITY_ISSUE") ? "REGENERATE" : "HUMAN_REVIEW",
        "reason", rootCause.equals("RENDER_FIDELITY_ISSUE") ? "The validated plan is more varied than the rendered visual progression." : "Plan intent was compared conservatively with available rendered evidence.");
  }

  private Map<String, Object> unavailableFidelity(String status, String reason) {
    return Map.of("status", status, "coverage", 0.0, "dimensions", Map.of(), "reason", reason, "recommendedActionType", "HUMAN_REVIEW");
  }

  private Map<String, Object> dimension(String status, String reason, String action) {
    return Map.of("status", status, "reason", reason, "recommendedActionType", action);
  }

  private List<Map<String, Object>> alignCandidates(List<Map<String, Object>> candidates, List<Map<String, Object>> beats, String direction) {
    List<Map<String, Object>> result = new ArrayList<>();
    for (Map<String, Object> candidate : candidates) {
      Map<String, Object> copy = new LinkedHashMap<>(candidate);
      double start = number(candidate.get("startSeconds"));
      double end = number(candidate.get("endSeconds"));
      Map<String, Object> best = null;
      double bestOverlap = 0;
      for (Map<String, Object> beat : beats) {
        double overlap = Math.max(0, Math.min(end, number(beat.get("endSeconds"))) - Math.max(start, number(beat.get("startSeconds"))));
        if (overlap > bestOverlap) { bestOverlap = overlap; best = beat; }
      }
      if (best == null || bestOverlap <= 0) {
        copy.put("classification", "UNMAPPED_" + direction);
        copy.put("alignedBeatId", null);
        copy.put("alignedBeatType", null);
        copy.put("beatOverlapSeconds", 0.0);
      } else {
        copy.put("classification", "PLANNED_" + normalizeType(String.valueOf(best.get("type")), direction));
        copy.put("alignedBeatId", best.get("id"));
        copy.put("alignedBeatType", best.get("type"));
        copy.put("beatOverlapSeconds", round(bestOverlap));
      }
      result.add(copy);
    }
    return List.copyOf(result);
  }

  private String normalizeType(String type, String direction) {
    String normalized = type.toUpperCase();
    if (normalized.contains("PAYOFF")) return "PAYOFF";
    if (normalized.contains("REACTION")) return "REACTION";
    if (normalized.contains("TRANSITION")) return "TRANSITION";
    return direction;
  }

  private List<Map<String, Object>> beats(Map<String, Object> contract) {
    Object timing = map(contract.get("intent")).get("timingIntent");
    Object value = timing instanceof Map<?, ?> timingMap ? timingMap.get("beats") : timing;
    if (!(value instanceof List<?>)) value = map(contract.get("intent")).get("beats");
    if (!(value instanceof List<?> values)) return List.of();
    List<Map<String, Object>> result = new ArrayList<>();
    for (Object item : values) {
      Map<String, Object> beat = map(item);
      Double start = firstNumber(beat, "startSeconds", "startTime", "start");
      Double end = firstNumber(beat, "endSeconds", "endTime", "end");
      if (start == null || end == null || end <= start) continue;
      Map<String, Object> normalized = new LinkedHashMap<>();
      normalized.put("id", first(beat, "id", "beatId", "key"));
      normalized.put("type", first(beat, "type", "beatType", "kind", "name"));
      normalized.put("plannedAction", normalizeAction(first(beat, "strategyClass", "primaryAction", "primaryVerb", "action", "strategy")));
      normalized.put("startSeconds", start);
      normalized.put("endSeconds", end);
      result.add(normalized);
    }
    return result;
  }

  private String first(Map<String, Object> map, String... keys) {
    for (String key : keys) if (map.get(key) != null) return String.valueOf(map.get(key));
    return "UNKNOWN";
  }

  private String normalizeAction(String value) {
    return value == null || value.isBlank() || "UNKNOWN".equals(value) ? "UNKNOWN" : value.toUpperCase();
  }

  private String normalizeStrategy(String value) {
    String normalized = normalizeAction(value);
    if (normalized.contains("PUSH")) return "PUSH";
    if (normalized.contains("BLOCK") || normalized.contains("STOP")) return "BLOCK";
    if (normalized.contains("LIFT") || normalized.contains("RAISE") || normalized.contains("UP")) return "LIFT";
    if (normalized.contains("TURN") || normalized.contains("ROTAT")) return "TURN";
    if (normalized.contains("OPEN") || normalized.contains("CLOSE")) return "OPEN_CLOSE";
    if (normalized.contains("FIND") || normalized.contains("SEARCH")) return "FIND";
    return normalized;
  }

  private Double firstNumber(Map<String, Object> map, String... keys) {
    for (String key : keys) if (map.get(key) != null) return number(map.get(key));
    return null;
  }

  private double number(Object value) {
    return value instanceof Number number ? number.doubleValue() : Double.parseDouble(String.valueOf(value));
  }

  private double round(double value) { return Math.round(value * 1000.0) / 1000.0; }

  private double overlap(double startA, double endA, double startB, double endB) {
    return Math.max(0.0, Math.min(endA, endB) - Math.max(startA, startB));
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> map(Object value) { return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of(); }

  @SuppressWarnings("unchecked")
  private List<Map<String, Object>> maps(Object value) {
    if (!(value instanceof List<?> values)) return List.of();
    return values.stream().filter(item -> item instanceof Map<?, ?>).map(item -> (Map<String, Object>) item).toList();
  }
}
