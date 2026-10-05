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
    result.putAll(actionEvidence(beats, profile));
    return result;
  }

  private Map<String, Object> actionEvidence(List<Map<String, Object>> beats, Map<String, Object> profile) {
    List<String> actions = beats.stream()
        .map(beat -> String.valueOf(beat.get("plannedAction")))
        .filter(action -> !"UNKNOWN".equals(action))
        .toList();
    if (actions.isEmpty()) {
      return Map.of("actionBeatNovelty", Map.of("status", "NOT_EVALUATED", "reason", "No structured primary actions were present in the plan."),
          "planRenderFidelity", Map.of("status", "UNKNOWN", "reason", "No timestamped planned actions were available."));
    }
    long distinct = actions.stream().distinct().count();
    double repetitionRatio = 1.0 - distinct / (double) actions.size();
    String actionStatus = distinct >= 3 ? "STRONG" : distinct == 2 ? "MODERATE" : "WEAK";
    Map<String, Object> fidelity = visualFidelity(beats, profile);
    return Map.of(
        "plannedActionSequence", actions,
        "plannedActionCount", actions.size(),
        "distinctPrimaryActionCount", distinct,
        "strategyDiversity", round(distinct / (double) actions.size()),
        "repetitionRatio", round(repetitionRatio),
        "actionBeatNovelty", Map.of("status", actionStatus, "planned", actions),
        "planRenderFidelity", fidelity);
  }

  private Map<String, Object> visualFidelity(List<Map<String, Object>> beats, Map<String, Object> profile) {
    Object noveltyValue = profile.get("visualNovelty");
    if (!(noveltyValue instanceof Map<?, ?> novelty) || !(novelty.get("points") instanceof List<?> points)) {
      return Map.of("status", "UNKNOWN", "reason", "Visual novelty evidence is unavailable.");
    }
    int transitions = 0;
    int supported = 0;
    for (int index = 1; index < beats.size(); index++) {
      String before = String.valueOf(beats.get(index - 1).get("plannedAction"));
      String after = String.valueOf(beats.get(index).get("plannedAction"));
      if ("UNKNOWN".equals(before) || "UNKNOWN".equals(after) || before.equals(after)) continue;
      transitions++;
      double start = number(beats.get(index).get("startSeconds"));
      boolean changed = points.stream().anyMatch(point -> point instanceof Map<?, ?> value
          && Math.abs(number(value.get("timestamp")) - start) <= 0.75
          && number(value.get("novelty")) >= 0.15);
      if (changed) supported++;
    }
    if (transitions == 0) return Map.of("status", "NOT_EVALUATED", "reason", "No distinct planned action transition was available.");
    String status = supported == transitions ? "MATCH" : supported > 0 ? "PARTIAL_MATCH" : "UNKNOWN";
    return Map.of("status", status, "plannedTransitions", transitions, "supportedTransitions", supported,
        "reason", "Visual novelty was compared with planned action transitions; pixels alone do not prove semantic action fidelity.");
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
    Object value = map(map(contract.get("intent")).get("timingIntent")).get("beats");
    if (!(value instanceof List<?>)) value = map(contract.get("intent")).get("timingIntent");
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

  private Double firstNumber(Map<String, Object> map, String... keys) {
    for (String key : keys) if (map.get(key) != null) return number(map.get(key));
    return null;
  }

  private double number(Object value) {
    return value instanceof Number number ? number.doubleValue() : Double.parseDouble(String.valueOf(value));
  }

  private double round(double value) { return Math.round(value * 1000.0) / 1000.0; }

  @SuppressWarnings("unchecked")
  private Map<String, Object> map(Object value) { return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of(); }

  @SuppressWarnings("unchecked")
  private List<Map<String, Object>> maps(Object value) {
    if (!(value instanceof List<?> values)) return List.of();
    return values.stream().filter(item -> item instanceof Map<?, ?>).map(item -> (Map<String, Object>) item).toList();
  }
}
