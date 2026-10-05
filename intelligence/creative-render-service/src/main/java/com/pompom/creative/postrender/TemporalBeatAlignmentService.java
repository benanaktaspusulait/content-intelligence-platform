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
    return result;
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
