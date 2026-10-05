package com.pompom.creative.contract;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/** Derives a small normalized contract from the canonical parsed prompt snapshot. */
@Component
public class CreativeProductionContractService {
  public static final String CONTRACT_VERSION = "creative-production-contract-v1";
  public static final String COMPILER_VERSION = "prompt-constraint-compiler-v1";

  private final ObjectMapper objectMapper;
  private final PromptConstraintCompiler compiler;

  public CreativeProductionContractService(
      ObjectMapper objectMapper, PromptConstraintCompiler compiler) {
    this.objectMapper = objectMapper;
    this.compiler = compiler;
  }

  public ContractCompilation compile(ContentPromptSnapshot snapshot, String preRenderRuleset) {
    if (snapshot.parsedIr() == null || snapshot.parsedIr().isBlank() || "{}".equals(snapshot.parsedIr().trim())) {
      return ContractCompilation.legacy();
    }
    try {
      Map<String, Object> root = objectMapper.readValue(snapshot.parsedIr(), new TypeReference<>() {});
      Map<String, Object> plan = map(root.get("videoPlanIR"));
      if (plan.isEmpty()) plan = root;
      List<String> errors = new ArrayList<>();
      Map<String, Object> intent = new LinkedHashMap<>();
      copy(intent, "metadata", plan.get("metadata"));
      copy(intent, "openingIntent", plan.get("hook"));
      copy(intent, "mechanicIntent", plan.get("coreMechanic"));
      copy(intent, "characterIntent", plan.get("characters"));
      copy(intent, "timingIntent", plan.get("beats"));
      copy(intent, "payoffIntent", plan.get("finalPayoff"));
      copy(intent, "loopIntent", plan.get("loop"));
      copy(intent, "producibilityIntent", plan.get("producibility"));
      if (!intent.containsKey("loopIntent") && map(plan.get("finalPayoff")).containsKey("loopsToOpening")) {
        intent.put("loopIntent", Map.of("loopsToOpening", map(plan.get("finalPayoff")).get("loopsToOpening")));
      }
      if (!intent.containsKey("mechanicIntent")) errors.add("MISSING_MECHANIC_INTENT");
      if (!intent.containsKey("payoffIntent")) errors.add("MISSING_PAYOFF_INTENT");
      if (!intent.containsKey("timingIntent")) errors.add("MISSING_TIMELINE_INTENT");
      String family = string(map(plan.get("metadata")).get("seriesType"), "unknown");
      CreativeProductionContract contract =
          new CreativeProductionContract(
              errors.isEmpty() ? "READY" : "INCOMPLETE",
              CONTRACT_VERSION,
              family,
              string(map(plan.get("metadata")).get("version"), "1"),
              String.valueOf(snapshot.promptVersionNumber()),
              preRenderRuleset,
              intent,
              List.of("canonical-parsed-prompt", "pre-render-validation"),
              List.copyOf(errors));
      CompiledGenerationConstraints constraints = compiler.compile(contract);
      return ContractCompilation.of(contract, constraints, snapshot.promptText(), objectMapper);
    } catch (Exception error) {
      return ContractCompilation.failed(error.getClass().getSimpleName());
    }
  }

  private void copy(Map<String, Object> target, String key, Object value) {
    if (value != null && !(value instanceof String text && text.isBlank())) target.put(key, value);
  }

  @SuppressWarnings("unchecked")
  private Map<String, Object> map(Object value) {
    return value instanceof Map<?, ?> raw ? (Map<String, Object>) raw : Map.of();
  }

  private String string(Object value, String fallback) {
    return value == null ? fallback : String.valueOf(value);
  }

  public record ContractCompilation(
      CreativeProductionContract contract,
      CompiledGenerationConstraints constraints,
      String contractJson,
      String constraintsJson,
      String constraintsSha256,
      String generationPromptSnapshot) {
    public static ContractCompilation of(
        CreativeProductionContract contract,
        CompiledGenerationConstraints constraints,
        String promptText,
        ObjectMapper mapper)
        throws Exception {
      String contractJson = mapper.writeValueAsString(contract);
      String constraintsJson = mapper.writeValueAsString(constraints);
      String hash =
          java.util.HexFormat.of()
              .formatHex(
                  java.security.MessageDigest.getInstance("SHA-256")
                      .digest(constraintsJson.getBytes(java.nio.charset.StandardCharsets.UTF_8)));
      String compiledPrompt =
          promptText
              + "\n\n[COMPILED CREATIVE PRODUCTION CONSTRAINTS]\n- "
              + String.join("\n- ", constraints.constraints());
      return new ContractCompilation(contract, constraints, contractJson, constraintsJson, hash, compiledPrompt);
    }

    public static ContractCompilation legacy() {
      CreativeProductionContract contract =
          new CreativeProductionContract(
              "CONTRACT_NOT_AVAILABLE_LEGACY",
              CONTRACT_VERSION,
              "unknown",
              "unknown",
              "unknown",
              "unknown",
              Map.of(),
              List.of("legacy-prompt-without-parsed-plan"),
              List.of());
      CompiledGenerationConstraints constraints =
          new CompiledGenerationConstraints(COMPILER_VERSION, "NOT_AVAILABLE", List.of(), List.of());
      return new ContractCompilation(contract, constraints, "{}", "{}", null, null);
    }

    public static ContractCompilation failed(String reason) {
      CreativeProductionContract contract =
          new CreativeProductionContract(
              "SERVICE_ERROR", CONTRACT_VERSION, "unknown", "unknown", "unknown", "unknown",
              Map.of(), List.of(), List.of(reason));
      CompiledGenerationConstraints constraints =
          new CompiledGenerationConstraints(COMPILER_VERSION, "SERVICE_ERROR", List.of(), List.of());
      return new ContractCompilation(contract, constraints, "{}", "{}", null, null);
    }
  }
}
