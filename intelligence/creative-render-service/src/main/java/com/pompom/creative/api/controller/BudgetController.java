package com.pompom.creative.api.controller;

import com.pompom.creative.service.BudgetAlertService;
import com.pompom.creative.service.CreditTrackingService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** REST API controller for budget and credit tracking. */
@RestController
@RequestMapping("/api/v1/budget")
@Slf4j
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class BudgetController {

  private final CreditTrackingService creditTrackingService;
  private final BudgetAlertService budgetAlertService;

  /** Get current budget status. */
  @GetMapping("/status")
  public ResponseEntity<CreditTrackingService.BudgetStatus> getBudgetStatus() {
    log.info("GET /api/v1/budget/status");

    CreditTrackingService.BudgetStatus status = creditTrackingService.getBudgetStatus();

    return ResponseEntity.ok(status);
  }

  /** Get usage statistics. */
  @GetMapping("/usage-statistics")
  public ResponseEntity<CreditTrackingService.UsageStatistics> getUsageStatistics() {
    log.info("GET /api/v1/budget/usage-statistics");

    CreditTrackingService.UsageStatistics stats = creditTrackingService.getUsageStatistics();

    return ResponseEntity.ok(stats);
  }

  /** Get alert status. */
  @GetMapping("/alerts")
  public ResponseEntity<BudgetAlertService.AlertStatus> getAlertStatus() {
    log.info("GET /api/v1/budget/alerts");

    BudgetAlertService.AlertStatus alertStatus = budgetAlertService.getAlertStatus();

    return ResponseEntity.ok(alertStatus);
  }
}
