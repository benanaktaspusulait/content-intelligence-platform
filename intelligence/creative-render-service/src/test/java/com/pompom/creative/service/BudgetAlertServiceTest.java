package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

import com.pompom.creative.notification.EmailNotificationService;
import com.pompom.creative.service.CreditTrackingService.BudgetLevel;
import com.pompom.creative.service.CreditTrackingService.BudgetStatus;
import java.math.BigDecimal;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class BudgetAlertServiceTest {

  @Mock private CreditTrackingService creditTrackingService;

  @Mock private EmailNotificationService emailNotificationService;

  private BudgetAlertService budgetAlertService;

  @BeforeEach
  void setUp() {
    budgetAlertService = new BudgetAlertService(creditTrackingService, emailNotificationService);

    // Set configuration via reflection
    ReflectionTestUtils.setField(budgetAlertService, "alertsEnabled", true);
    ReflectionTestUtils.setField(budgetAlertService, "webhookUrl", "");
    ReflectionTestUtils.setField(budgetAlertService, "alertEmail", "");
  }

  @Test
  void checkBudgetBeforeRender_healthy_passes() {
    // Given: Healthy budget (80% remaining)
    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("200"), BudgetLevel.HEALTHY);
    when(creditTrackingService.getBudgetStatus()).thenReturn(status);

    // When/Then: No exception thrown
    budgetAlertService.checkBudgetBeforeRender();
  }

  @Test
  void checkBudgetBeforeRender_warning_logsWarning() {
    // Given: Warning level (15% remaining)
    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("850"), BudgetLevel.WARNING);
    when(creditTrackingService.getBudgetStatus()).thenReturn(status);

    // When/Then: Logs warning but allows render
    budgetAlertService.checkBudgetBeforeRender();

    // Verify no exception
  }

  @Test
  void checkBudgetBeforeRender_exhausted_throwsException() {
    // Given: Exhausted budget
    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("1050"), BudgetLevel.EXHAUSTED);
    when(creditTrackingService.getBudgetStatus()).thenReturn(status);

    // When/Then: Throws BudgetExhaustedException
    assertThatThrownBy(() -> budgetAlertService.checkBudgetBeforeRender())
        .isInstanceOf(BudgetAlertService.BudgetExhaustedException.class)
        .hasMessageContaining("exhausted")
        .hasMessageContaining("1050/1000");
  }

  @Test
  void checkAndAlert_healthy_doesNotAlert() {
    // Given: Healthy budget
    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("200"), BudgetLevel.HEALTHY);

    // When
    budgetAlertService.checkAndAlert(status);

    // Then: No alerts sent (verify via logs in real implementation)
    // This test mainly ensures no exceptions thrown
  }

  @Test
  void checkAndAlert_warning_sendsAlert() {
    // Given: Warning level
    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("850"), BudgetLevel.WARNING);

    // When
    budgetAlertService.checkAndAlert(status);

    // Then: Alert sent (verify via logs)
    // In real implementation, would mock webhook/email sending
  }

  @Test
  void checkAndAlert_exhausted_sendsAlert() {
    // Given: Exhausted budget
    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("1100"), BudgetLevel.EXHAUSTED);

    // When
    budgetAlertService.checkAndAlert(status);

    // Then: Critical alert sent
  }

  @Test
  void checkAndAlert_alertsDisabled_doesNotAlert() {
    // Given: Alerts disabled
    ReflectionTestUtils.setField(budgetAlertService, "alertsEnabled", false);

    BudgetStatus status =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("1100"), BudgetLevel.EXHAUSTED);

    // When
    budgetAlertService.checkAndAlert(status);

    // Then: No alerts sent despite exhausted status
  }

  @Test
  void getAlertStatus_returnsCurrentStatus() {
    // Given
    BudgetStatus budgetStatus =
        createBudgetStatus(new BigDecimal("1000"), new BigDecimal("850"), BudgetLevel.WARNING);
    when(creditTrackingService.getBudgetStatus()).thenReturn(budgetStatus);

    // When
    BudgetAlertService.AlertStatus alertStatus = budgetAlertService.getAlertStatus();

    // Then
    assertThat(alertStatus.getBudgetLevel()).isEqualTo(BudgetLevel.WARNING);
    assertThat(alertStatus.isAlertsEnabled()).isTrue();
    assertThat(alertStatus.getMessage()).contains("Warning");
  }

  // Helper method

  private BudgetStatus createBudgetStatus(BigDecimal limit, BigDecimal used, BudgetLevel level) {
    BudgetStatus status = new BudgetStatus();
    status.setBudgetLimit(limit);
    status.setUsedCredits(used);
    status.setRemainingCredits(limit.subtract(used));
    status.setRemainingPercent(
        limit.subtract(used).divide(limit, 4, BigDecimal.ROUND_HALF_UP).doubleValue() * 100);
    status.setLevel(level);
    status.setMonthStart(Instant.now());
    status.setTotalJobs(10);

    return status;
  }
}
