package com.pompomhills.intelligence.rulegovernance;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class EffectiveRulePolicyResolverTest {
  private final EffectiveRulePolicyResolver resolver = new EffectiveRulePolicyResolver();

  @Test
  void specificRuleReplacesOverridableGlobalRule() {
    Map<String, Object> document =
        Map.of(
            "rules",
            List.of(
                Map.of("id", "HOOK_001", "scopeType", "GLOBAL", "overridePolicy", "OVERRIDABLE", "value", "global"),
                Map.of("id", "HOOK_001", "scopeType", "BRAND_OR_ACCOUNT", "scopeId", "brand-a", "overridePolicy", "OVERRIDABLE", "value", "brand")));

    List<Map<String, Object>> result = resolver.resolve(document, "PRESCHOOL", "brand-a", "family-a");

    assertThat(result).singleElement().extracting(rule -> rule.get("value")).isEqualTo("brand");
  }

  @Test
  void nonOverridableGlobalRuleWinsOverSpecificRule() {
    Map<String, Object> document =
        Map.of(
            "rules",
            List.of(
                Map.of("id", "SAFETY_001", "scopeType", "GLOBAL", "overridePolicy", "NON_OVERRIDABLE", "value", "global"),
                Map.of("id", "SAFETY_001", "scopeType", "CONTENT_FAMILY", "scopeId", "family-a", "overridePolicy", "OVERRIDABLE", "value", "family")));

    List<Map<String, Object>> result = resolver.resolve(document, "PRESCHOOL", "brand-a", "family-a");

    assertThat(result).singleElement().extracting(rule -> rule.get("value")).isEqualTo("global");
  }

  @Test
  void bootstrapResolverDoesNotInheritAnotherBrandOrFamilyRule() {
    BootstrapPolicyResolver bootstrap = new BootstrapPolicyResolver(resolver);
    Map<String, Object> document =
        Map.of(
            "rules",
            List.of(
                Map.of("id", "GLOBAL", "scopeType", "GLOBAL"),
                Map.of("id", "DOMAIN", "scopeType", "INDUSTRY_OR_DOMAIN", "scopeId", "PRESCHOOL"),
                Map.of("id", "BRAND", "scopeType", "BRAND_OR_ACCOUNT", "scopeId", "other-brand"),
                Map.of("id", "FAMILY", "scopeType", "CONTENT_FAMILY", "scopeId", "other-family")));

    assertThat(bootstrap.resolveForNewAccount(document, "PRESCHOOL"))
        .extracting(rule -> rule.get("id"))
        .containsExactly("GLOBAL", "DOMAIN");
  }
}
