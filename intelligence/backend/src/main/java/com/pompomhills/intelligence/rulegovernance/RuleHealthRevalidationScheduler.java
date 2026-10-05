package com.pompomhills.intelligence.rulegovernance;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Flags due rules for human revalidation; it never retires or reverses policy automatically. */
@Component
public class RuleHealthRevalidationScheduler {
  private final RuleGovernanceService service;

  public RuleHealthRevalidationScheduler(RuleGovernanceService service) {
    this.service = service;
  }

  @Scheduled(fixedDelayString = "${pompom.rule-governance.health-poll-ms:3600000}")
  public void flagDueRules() {
    service.flagDueHealthForRevalidation();
  }
}
