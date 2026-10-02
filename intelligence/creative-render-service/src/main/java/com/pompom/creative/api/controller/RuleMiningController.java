package com.pompom.creative.api.controller;

import com.pompom.creative.rulemining.RuleCandidate;
import com.pompom.creative.rulemining.RuleMiningService;
import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST controller for rule mining. */
@RestController
@RequestMapping("/api/v1/rules")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class RuleMiningController {

  private final RuleMiningService miningService;

  /** Mine rules from performance patterns. */
  @PostMapping("/mine")
  public ResponseEntity<RuleMiningService.MiningResult> mineRules() {
    log.info("Starting rule mining");

    try {
      RuleMiningService.MiningResult result = miningService.mineRules();
      return ResponseEntity.ok(result);

    } catch (IllegalStateException e) {
      log.error("Mining failed: {}", e.getMessage());
      return ResponseEntity.badRequest().build();
    }
  }

  /** Get rules for a mining run. */
  @GetMapping("/run/{runId}")
  public ResponseEntity<List<RuleCandidate>> getRulesByRunId(@PathVariable UUID runId) {
    log.info("Fetching rules for run: {}", runId);

    List<RuleCandidate> rules = miningService.getRulesByRunId(runId);

    return ResponseEntity.ok(rules);
  }

  /** Get actionable rules. */
  @GetMapping("/actionable")
  public ResponseEntity<List<RuleCandidate>> getActionableRules() {
    log.info("Fetching actionable rules");

    List<RuleCandidate> rules = miningService.getActionableRules();

    return ResponseEntity.ok(rules);
  }

  /** Get high-confidence rules. */
  @GetMapping("/high-confidence")
  public ResponseEntity<List<RuleCandidate>> getHighConfidenceRules(
      @RequestParam(defaultValue = "70") BigDecimal minConfidence) {
    log.info("Fetching high-confidence rules: minConfidence={}", minConfidence);

    List<RuleCandidate> rules = miningService.getHighConfidenceRules(minConfidence);

    return ResponseEntity.ok(rules);
  }
}
