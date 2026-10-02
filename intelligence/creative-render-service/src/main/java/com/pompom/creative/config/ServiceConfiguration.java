package com.pompom.creative.config;

import com.pompom.creative.service.BudgetAlertService;
import com.pompom.creative.service.CreditTrackingService;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;

/** Configuration to wire services and resolve circular dependencies. */
@Configuration
@RequiredArgsConstructor
public class ServiceConfiguration {

  private final CreditTrackingService creditTrackingService;
  private final BudgetAlertService budgetAlertService;

  @PostConstruct
  public void configureServices() {
    // Wire BudgetAlertService into CreditTrackingService
    creditTrackingService.setBudgetAlertService(budgetAlertService);
  }
}
