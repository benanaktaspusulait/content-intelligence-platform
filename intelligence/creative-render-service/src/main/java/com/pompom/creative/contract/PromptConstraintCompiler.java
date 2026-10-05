package com.pompom.creative.contract;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Compiles only scoped, generation-relevant intent; evaluative rules stay out of the prompt. */
@Component
public class PromptConstraintCompiler {
  public CompiledGenerationConstraints compile(CreativeProductionContract contract) {
    List<String> constraints = new ArrayList<>();
    Map<String, Object> intent = contract.intent();
    Map<String, Object> mechanic = map(intent.get("mechanicIntent"));
    Map<String, Object> payoff = map(intent.get("payoffIntent"));
    Map<String, Object> opening = map(intent.get("openingIntent"));
    if (!opening.isEmpty()) constraints.add("Make the opening relationship and central anomaly readable immediately.");
    if (!mechanic.isEmpty()) constraints.add("Preserve one clear primary mechanic and its causal participants throughout.");
    if (intent.containsKey("timingIntent")) constraints.add("Preserve the planned beat order and visible state changes.");
    List<String> attempts = attemptActions(intent.get("timingIntent"));
    if (attempts.size() > 1) {
      constraints.add("Use visibly different primary actions in this order: " + String.join(", ", attempts) + ".");
    }
    if (!payoff.isEmpty()) {
      String strategy = first(payoff, "emphasisStrategy", "emphasis", "motionStrategy");
      if (strategy != null && strategy.toUpperCase().contains("REDUCTION")) {
        constraints.add("At the payoff, reduce non-essential motion so the consequence and reaction remain readable.");
      } else if (strategy != null && strategy.toUpperCase().contains("SPIKE")) {
        constraints.add("At the payoff, create one clear visual motion spike while controlling background motion.");
      } else {
        constraints.add("Make the planned payoff consequence and reaction visually distinct from the preceding beat.");
      }
    }
    if (!map(intent.get("loopIntent")).isEmpty()) {
      constraints.add("End in a visual or action state that can naturally reconnect to the planned opening.");
    }
    if (constraints.stream().noneMatch(value -> value.startsWith("Make the opening")) && !intent.isEmpty()) {
      constraints.add("Keep the main subject, object and action readable in a clean composition.");
    }
    return new CompiledGenerationConstraints(
        CreativeProductionContractService.COMPILER_VERSION,
        contract.status().equals("READY") ? "READY" : "PARTIAL",
        List.copyOf(dedupe(constraints)),
        List.of());
  }

  private List<String> dedupe(List<String> values) {
    return values.stream().distinct().toList();
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> map(Object value) {
    return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
  }

  private String first(Map<String, Object> map, String... keys) {
    for (String key : keys) if (map.get(key) != null) return String.valueOf(map.get(key));
    return null;
  }

  private List<String> attemptActions(Object value) {
    if (!(value instanceof List<?> values)) return List.of();
    List<String> result = new ArrayList<>();
    for (Object item : values) {
      Map<String, Object> beat = map(item);
      Object marked = beat.get("isAttempt");
      if (Boolean.TRUE.equals(marked)) {
        String action = first(beat, "primaryAction", "primaryVerb", "action");
        if (action != null && !action.isBlank()) result.add(action.toUpperCase());
      }
    }
    return result;
  }
}
