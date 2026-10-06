package com.pompom.creative.postrender;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Interprets local motion evidence around a resolved payoff without changing motion-v3 values. */
@Component
public class PayoffMotionAnalyzer {
  public Map<String, Object> analyze(Map<String, Object> temporalProfile, PayoffWindow payoff) {
    Map<String, Object> result = new LinkedHashMap<>();
    result.put("status", payoff.status().name());
    result.put(
        "statusStatus",
        payoff.status() == PayoffWindowStatus.SERVICE_ERROR
            ? EvidenceStatus.SERVICE_ERROR.name()
            : EvidenceStatus.AVAILABLE.name());
    if (payoff.status() != PayoffWindowStatus.RESOLVED) {
      result.put("contrastStatus", EvidenceStatus.NOT_EVALUATED.name());
      result.put("holdStatus", EvidenceStatus.NOT_EVALUATED.name());
      return result;
    }
    List<Map<String, Object>> segments = maps(temporalProfile.get("segments"));
    double start = payoff.startSeconds();
    double end = payoff.endSeconds();
    double pre = average(segments, Math.max(0, start - 0.8), start);
    double during = average(segments, start, end);
    double post = average(segments, end, end + 0.8);
    boolean available = !Double.isNaN(pre) && !Double.isNaN(during) && !Double.isNaN(post);
    result.put("preStartSeconds", Math.max(0, start - 0.8));
    result.put("preEndSeconds", start);
    result.put("payoffStartSeconds", start);
    result.put("payoffEndSeconds", end);
    result.put("postStartSeconds", end);
    result.put("postEndSeconds", end + 0.8);
    result.put("prePayoffMotion", value(pre));
    result.put("payoffMotion", value(during));
    result.put("postPayoffMotion", value(post));
    if (!available) {
      result.put("contrastDirection", "UNKNOWN");
      result.put("contrastMagnitude", null);
      result.put("contrastStatus", EvidenceStatus.UNKNOWN.name());
      result.put("holdStatus", EvidenceStatus.UNKNOWN.name());
      return result;
    }
    double surrounding = (pre + post) / 2.0;
    double delta = during - surrounding;
    String direction = Math.abs(delta) < 0.1 ? "NONE" : delta < 0 ? "REDUCTION" : "INCREASE";
    result.put("contrastDirection", direction);
    result.put("contrastMagnitude", round(Math.abs(delta)));
    result.put("contrastStatus", EvidenceStatus.AVAILABLE.name());
    boolean hold = direction.equals("REDUCTION") && Math.abs(delta) >= 0.15;
    result.put("holdStatus", EvidenceStatus.AVAILABLE.name());
    // Keep the public evidence key aligned with the post-render contract.
    result.put("intentionalHold", hold);
    result.put("holdStartSeconds", start);
    result.put("holdEndSeconds", end);
    result.put("holdDurationSeconds", round(end - start));
    result.put("technicalFreezeSuspected", false);
    result.put("holdReliability", hold ? "CANDIDATE" : "NOT_DETECTED");
    return result;
  }

  private double average(List<Map<String, Object>> segments, double start, double end) {
    double total = 0;
    double weighted = 0;
    for (Map<String, Object> segment : segments) {
      double segmentStart = number(segment.get("startSeconds"));
      double segmentEnd = number(segment.get("endSeconds"));
      double overlap = Math.max(0, Math.min(end, segmentEnd) - Math.max(start, segmentStart));
      if (overlap <= 0 || !segment.containsKey("averageMotion")) continue;
      weighted += number(segment.get("averageMotion")) * overlap;
      total += overlap;
    }
    return total == 0 ? Double.NaN : weighted / total;
  }

  private List<Map<String, Object>> maps(Object value) {
    if (!(value instanceof List<?> values)) return List.of();
    List<Map<String, Object>> result = new ArrayList<>();
    for (Object item : values)
      if (item instanceof Map<?, ?> map) {
        Map<String, Object> copy = new LinkedHashMap<>();
        map.forEach((key, entry) -> copy.put(String.valueOf(key), entry));
        result.add(copy);
      }
    return result;
  }

  private double number(Object value) {
    return value instanceof Number number
        ? number.doubleValue()
        : Double.parseDouble(String.valueOf(value));
  }

  private Object value(double value) {
    return Double.isNaN(value) ? null : round(value);
  }

  private double round(double value) {
    return Math.round(value * 10000.0) / 10000.0;
  }
}
