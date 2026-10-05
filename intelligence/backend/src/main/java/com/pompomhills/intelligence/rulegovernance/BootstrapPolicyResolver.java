package com.pompomhills.intelligence.rulegovernance;

import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

/** Cold-start policy: only global and explicitly matching domain rules are inherited. */
@Service
public class BootstrapPolicyResolver {
  private final EffectiveRulePolicyResolver resolver;

  public BootstrapPolicyResolver(EffectiveRulePolicyResolver resolver) {
    this.resolver = resolver;
  }

  public List<Map<String, Object>> resolveForNewAccount(
      Map<String, Object> rulesetDocument, String domain) {
    return resolver.resolve(rulesetDocument, domain, null, null);
  }
}
