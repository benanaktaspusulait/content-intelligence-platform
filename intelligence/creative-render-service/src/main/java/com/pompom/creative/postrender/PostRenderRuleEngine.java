package com.pompom.creative.postrender;

import java.io.InputStream;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import org.yaml.snakeyaml.Yaml;

/** Evaluates immutable post-render policy against measured evidence. */
@Service
@Slf4j
public class PostRenderRuleEngine {
  public static final String RULESET_VERSION = "POST_RENDER_RULESET_1.0";
  private static final String RESOURCE = "post-render-rules/POST_RENDER_RULESET_1.0.yaml";

  private final List<PostRenderRuleDefinition> rules;

  public PostRenderRuleEngine() {
    this.rules = loadRules();
  }

  public String rulesetVersion() {
    return RULESET_VERSION;
  }

  public List<PostRenderRuleResult> evaluate(RenderEvidenceIR evidence) {
    return rules.stream().map(rule -> evaluate(rule, evidence)).toList();
  }

  private PostRenderRuleResult evaluate(PostRenderRuleDefinition rule, RenderEvidenceIR evidence) {
    Instant now = Instant.now();
    Object actual = evidence.valueAt(rule.source());
    EvidenceStatus status = evidence.statusAt(rule.source());
    if (actual == null || status != EvidenceStatus.AVAILABLE) {
      return missing(rule, status, now);
    }
    boolean conditionPasses = compare(actual, rule.operator(), rule.expected());
    if (conditionPasses && "INFO".equals(rule.policyEffect())) {
      return result(rule, PostRenderOutcome.PASS, actual, false,
          "Informational evidence: " + rule.description(), now);
    }
    if ("HUMAN_REVIEW".equals(rule.policyEffect())) {
      return conditionPasses
          ? result(rule, PostRenderOutcome.FAIL, actual, true, rule.description(), now)
          : result(rule, PostRenderOutcome.PASS, actual, false,
              "Evidence does not require human review.", now);
    }
    if (conditionPasses) {
      return result(rule, outcome(rule.resultWhenMatched()), actual, false,
          rule.description(), now);
    }
    return result(rule, PostRenderOutcome.FAIL, actual, false,
        "Evidence violates the rule: " + rule.description(), now);
  }

  private PostRenderRuleResult missing(PostRenderRuleDefinition rule, EvidenceStatus status, Instant now) {
    return switch (rule.missingEvidence()) {
      case "FAIL_CLOSED" -> result(rule, PostRenderOutcome.FAIL, null, false,
          "Required evidence is unavailable: " + status, now, PostRenderSeverity.BLOCKER);
      case "REVIEW" -> result(rule, PostRenderOutcome.UNKNOWN, null, true,
          "Evidence requires human review: " + status, now);
      case "NOT_APPLICABLE" -> result(rule, PostRenderOutcome.NOT_APPLICABLE, null, false,
          "Evidence is not applicable: " + status, now);
      case "SERVICE_ERROR" -> result(rule, PostRenderOutcome.SERVICE_ERROR, null, false,
          "Evidence service failed: " + status, now);
      default -> result(rule, PostRenderOutcome.UNKNOWN, null, false,
          "Evidence is unavailable: " + status, now);
    };
  }

  private PostRenderRuleResult result(PostRenderRuleDefinition rule, PostRenderOutcome outcome,
      Object actual, boolean reviewRequired, String message, Instant evaluatedAt) {
    return result(rule, outcome, actual, reviewRequired, message, evaluatedAt, rule.severity());
  }

  private PostRenderRuleResult result(PostRenderRuleDefinition rule, PostRenderOutcome outcome,
      Object actual, boolean reviewRequired, String message, Instant evaluatedAt,
      PostRenderSeverity severity) {
    return new PostRenderRuleResult(rule.id(), rule.version(), RULESET_VERSION, "POST_RENDER",
        rule.family(), severity, outcome, message, actual, rule.expectedCondition(),
        Map.of("source", rule.source()), "POST_RENDER_RULE_ENGINE", reviewRequired, evaluatedAt);
  }

  private boolean compare(Object actual, String operator, Object expected) {
    return switch (operator) {
      case "EQUALS" -> String.valueOf(actual).equals(String.valueOf(expected));
      case "NOT_EQUALS" -> !String.valueOf(actual).equals(String.valueOf(expected));
      case "GREATER_THAN" -> number(actual) > number(expected);
      case "GREATER_THAN_OR_EQUAL" -> number(actual) >= number(expected);
      case "LESS_THAN" -> number(actual) < number(expected);
      case "LESS_THAN_OR_EQUAL" -> number(actual) <= number(expected);
      default -> false;
    };
  }

  private double number(Object value) {
    return value instanceof Number number ? number.doubleValue() : Double.parseDouble(value.toString());
  }

  private PostRenderOutcome outcome(String value) {
    try {
      return PostRenderOutcome.valueOf(value);
    } catch (IllegalArgumentException error) {
      return PostRenderOutcome.SERVICE_ERROR;
    }
  }

  @SuppressWarnings("unchecked")
  private List<PostRenderRuleDefinition> loadRules() {
    try (InputStream input = new ClassPathResource(RESOURCE).getInputStream()) {
      Map<String, Object> root = (Map<String, Object>) new Yaml().load(input);
      String version = String.valueOf(root.get("version"));
      if (!RULESET_VERSION.equals(version)) throw new IllegalStateException("Unexpected post-render ruleset version");
      List<Map<String, Object>> configured = (List<Map<String, Object>>) root.getOrDefault("rules", List.of());
      List<PostRenderRuleDefinition> definitions = new ArrayList<>();
      for (Map<String, Object> rule : configured) {
        definitions.add(new PostRenderRuleDefinition(
            String.valueOf(rule.get("id")), String.valueOf(rule.get("ruleVersion")),
            String.valueOf(rule.get("family")), PostRenderSeverity.valueOf(String.valueOf(rule.get("severity"))),
            String.valueOf(rule.get("source")), String.valueOf(rule.get("operator")), rule.get("expected"),
            String.valueOf(rule.getOrDefault("missingEvidence", "UNKNOWN")),
            String.valueOf(rule.getOrDefault("resultWhenMatched", "FAIL")),
            String.valueOf(rule.getOrDefault("policyEffect", "")),
            String.valueOf(rule.getOrDefault("description", rule.get("id")))));
      }
      return List.copyOf(definitions);
    } catch (Exception error) {
      log.error("Could not load {}", RESOURCE, error);
      throw new IllegalStateException("Post-render ruleset is unavailable", error);
    }
  }
}
