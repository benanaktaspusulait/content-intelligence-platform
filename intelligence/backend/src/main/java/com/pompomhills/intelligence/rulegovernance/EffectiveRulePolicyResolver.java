package com.pompomhills.intelligence.rulegovernance;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Resolves policy precedence in one place; callers must not duplicate scope ordering. */
@Service
public class EffectiveRulePolicyResolver {
  private static final List<String> SPECIFICITY = List.of("GLOBAL", "INDUSTRY_OR_DOMAIN", "BRAND_OR_ACCOUNT", "CONTENT_FAMILY");

  public List<Map<String, Object>> resolve(
      Map<String, Object> rulesetDocument, String domain, String brand, String contentFamily) {
    Object raw = rulesetDocument.get("rules");
    if (!(raw instanceof List<?> rules)) return List.of();
    List<Map<String, Object>> applicable = new ArrayList<>();
    for (Object value : rules) {
      if (!(value instanceof Map<?, ?> map)) continue;
      @SuppressWarnings("unchecked") Map<String, Object> rule = (Map<String, Object>) map;
      if (applies(rule, domain, brand, contentFamily)) applicable.add(rule);
    }
    applicable.sort(Comparator.comparingInt(this::specificity));
    List<Map<String, Object>> resolved = new ArrayList<>();
    for (Map<String, Object> rule : applicable) {
      String key = String.valueOf(rule.getOrDefault("id", rule.getOrDefault("ruleKey", "")));
      int existing = indexOf(resolved, key);
      if (existing < 0) {
        resolved.add(rule);
      } else if (!"NON_OVERRIDABLE".equals(String.valueOf(resolved.get(existing).get("overridePolicy")))) {
        resolved.set(existing, rule);
      }
    }
    return List.copyOf(resolved);
  }

  private boolean applies(Map<String, Object> rule, String domain, String brand, String family) {
    String scope = String.valueOf(rule.getOrDefault("scopeType", "GLOBAL"));
    String scopeId = String.valueOf(rule.getOrDefault("scopeId", ""));
    return switch (scope) {
      case "GLOBAL" -> true;
      case "INDUSTRY_OR_DOMAIN" -> scopeId.equals(domain);
      case "BRAND_OR_ACCOUNT" -> scopeId.equals(brand);
      case "CONTENT_FAMILY" -> scopeId.equals(family);
      default -> false;
    };
  }

  private int specificity(Map<String, Object> rule) {
    return SPECIFICITY.indexOf(String.valueOf(rule.getOrDefault("scopeType", "GLOBAL")));
  }

  private int indexOf(List<Map<String, Object>> rules, String key) {
    for (int i = 0; i < rules.size(); i++) {
      if (String.valueOf(rules.get(i).getOrDefault("id", rules.get(i).getOrDefault("ruleKey", ""))).equals(key)) return i;
    }
    return -1;
  }
}
