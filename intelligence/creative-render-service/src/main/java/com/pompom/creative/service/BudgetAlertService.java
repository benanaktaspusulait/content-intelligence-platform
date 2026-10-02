package com.pompom.creative.service;

import com.pompom.creative.notification.EmailNotificationService;
import com.pompom.creative.service.CreditTrackingService.BudgetLevel;
import com.pompom.creative.service.CreditTrackingService.BudgetStatus;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

/**
 * Service for budget alerts and notifications. Sends warnings when budget is low and blocks
 * operations when exhausted.
 */
@Service
@Slf4j
@RequiredArgsConstructor
public class BudgetAlertService {

  private final CreditTrackingService creditTrackingService;
  private final EmailNotificationService emailNotificationService;
  private final RestClient restClient = RestClient.create();

  @Value("${pompom.openart.budget.alert.enabled:true}")
  private boolean alertsEnabled;

  @Value("${pompom.openart.budget.alert.webhook-url:}")
  private String webhookUrl;

  @Value("${pompom.openart.budget.alert.email:}")
  private String alertEmail;

  // Track last alert sent to avoid spam
  private final Map<BudgetLevel, Instant> lastAlertTime = new HashMap<>();
  private static final long ALERT_COOLDOWN_MINUTES = 60; // 1 hour between duplicate alerts

  /**
   * Check budget status and send alerts if needed. Called after each credit usage recording.
   *
   * @param status Current budget status
   */
  public void checkAndAlert(BudgetStatus status) {
    if (!alertsEnabled) {
      return;
    }

    BudgetLevel level = status.getLevel();

    // Check if we should send alert (cooldown period)
    if (shouldSendAlert(level)) {
      sendAlert(status);
      lastAlertTime.put(level, Instant.now());
    }
  }

  /**
   * Check if render should be blocked due to budget. Throws exception if budget is exhausted.
   *
   * @throws BudgetExhaustedException if budget is exhausted
   */
  public void checkBudgetBeforeRender() {
    BudgetStatus status = creditTrackingService.getBudgetStatus();

    if (status.getLevel() == BudgetLevel.EXHAUSTED) {
      log.error(
          "Render blocked: Budget exhausted. Used: {}/{}, Remaining: {}",
          status.getUsedCredits(),
          status.getBudgetLimit(),
          status.getRemainingCredits());

      throw new BudgetExhaustedException(
          String.format(
              "Monthly budget exhausted. Used: %s/%s credits. "
                  + "Remaining: %s credits. Renders are blocked until next billing cycle.",
              status.getUsedCredits(), status.getBudgetLimit(), status.getRemainingCredits()));
    }

    // Log warning if at warning level
    if (status.getLevel() == BudgetLevel.WARNING) {
      log.warn(
          "Budget at warning level: {:.1f}% remaining ({}/{})",
          status.getRemainingPercent(), status.getRemainingCredits(), status.getBudgetLimit());
    }
  }

  /** Determine if alert should be sent based on cooldown period. */
  private boolean shouldSendAlert(BudgetLevel level) {
    // Always alert on EXHAUSTED (critical)
    if (level == BudgetLevel.EXHAUSTED) {
      Instant lastAlert = lastAlertTime.get(level);
      if (lastAlert == null) {
        return true;
      }
      // For exhausted, send every 6 hours
      long minutesSinceLastAlert =
          (Instant.now().toEpochMilli() - lastAlert.toEpochMilli()) / 60000;
      return minutesSinceLastAlert >= (ALERT_COOLDOWN_MINUTES * 6);
    }

    // For WARNING, send once per cooldown period
    if (level == BudgetLevel.WARNING) {
      Instant lastAlert = lastAlertTime.get(level);
      if (lastAlert == null) {
        return true;
      }
      long minutesSinceLastAlert =
          (Instant.now().toEpochMilli() - lastAlert.toEpochMilli()) / 60000;
      return minutesSinceLastAlert >= ALERT_COOLDOWN_MINUTES;
    }

    // Don't alert for HEALTHY
    return false;
  }

  /** Send alert via configured channels (webhook, email, log). */
  private void sendAlert(BudgetStatus status) {
    String message = buildAlertMessage(status);

    log.warn("BUDGET ALERT: {}", message);

    // Send webhook notification
    if (webhookUrl != null && !webhookUrl.isEmpty()) {
      sendWebhookAlert(message, status);
    }

    // Send email notification
    if (alertEmail != null && !alertEmail.isEmpty()) {
      sendEmailAlert(message, status);
    }

    // In production, could also:
    // - Send Slack notification
    // - Send PagerDuty alert (for EXHAUSTED)
    // - Create Jira ticket
    // - Update dashboard
  }

  /** Build alert message based on budget status. */
  private String buildAlertMessage(BudgetStatus status) {
    switch (status.getLevel()) {
      case WARNING:
        return String.format(
            "⚠️ OpenArt Budget Warning: Only %.1f%% remaining (%s/%s credits). "
                + "Total jobs this month: %d. Consider reviewing render queue.",
            status.getRemainingPercent(),
            status.getRemainingCredits(),
            status.getBudgetLimit(),
            status.getTotalJobs());

      case EXHAUSTED:
        return String.format(
            "🚨 OpenArt Budget EXHAUSTED: %s/%s credits used (%.1f%% over budget). "
                + "All renders are BLOCKED until next billing cycle. Total jobs: %d.",
            status.getUsedCredits(),
            status.getBudgetLimit(),
            Math.abs(status.getRemainingPercent()),
            status.getTotalJobs());

      default:
        return String.format(
            "✅ OpenArt Budget Healthy: %.1f%% remaining (%s/%s credits)",
            status.getRemainingPercent(), status.getRemainingCredits(), status.getBudgetLimit());
    }
  }

  /** Send webhook notification. */
  private void sendWebhookAlert(String message, BudgetStatus status) {
    if (webhookUrl == null || webhookUrl.isBlank()) {
      log.debug("Webhook URL not configured, skipping webhook alert");
      return;
    }

    log.info("Sending webhook alert to: {}", webhookUrl);

    try {
      Map<String, Object> payload =
          Map.of(
              "message", message,
              "level", status.getLevel().name(),
              "used", status.getUsedCredits(),
              "remaining", status.getRemainingCredits(),
              "limit", status.getBudgetLimit(),
              "timestamp", Instant.now().toString());

      restClient
          .post()
          .uri(webhookUrl)
          .contentType(MediaType.APPLICATION_JSON)
          .body(payload)
          .retrieve()
          .toBodilessEntity();

      log.info("Webhook alert sent successfully");
    } catch (Exception e) {
      log.error("Failed to send webhook alert: {}", e.getMessage());
    }
  }

  /** Send email notification using EmailNotificationService. */
  private void sendEmailAlert(String message, BudgetStatus status) {
    log.info("Sending email alert: level={}", status.getLevel());

    try {
      emailNotificationService.sendBudgetWarningEmail(
          status.getRemainingCredits(), status.getBudgetLimit());
      log.info("Email alert sent successfully");
    } catch (Exception e) {
      log.error("Failed to send email alert: {}", e.getMessage());
    }
  }

  /** Get current alert status (for API/dashboard). */
  public AlertStatus getAlertStatus() {
    BudgetStatus budgetStatus = creditTrackingService.getBudgetStatus();

    AlertStatus alertStatus = new AlertStatus();
    alertStatus.setBudgetLevel(budgetStatus.getLevel());
    alertStatus.setAlertsEnabled(alertsEnabled);
    alertStatus.setMessage(buildAlertMessage(budgetStatus));
    alertStatus.setLastWarningAlert(lastAlertTime.get(BudgetLevel.WARNING));
    alertStatus.setLastExhaustedAlert(lastAlertTime.get(BudgetLevel.EXHAUSTED));

    return alertStatus;
  }

  /** Alert status data class. */
  public static class AlertStatus {
    private BudgetLevel budgetLevel;
    private boolean alertsEnabled;
    private String message;
    private Instant lastWarningAlert;
    private Instant lastExhaustedAlert;

    // Getters and setters
    public BudgetLevel getBudgetLevel() {
      return budgetLevel;
    }

    public void setBudgetLevel(BudgetLevel budgetLevel) {
      this.budgetLevel = budgetLevel;
    }

    public boolean isAlertsEnabled() {
      return alertsEnabled;
    }

    public void setAlertsEnabled(boolean alertsEnabled) {
      this.alertsEnabled = alertsEnabled;
    }

    public String getMessage() {
      return message;
    }

    public void setMessage(String message) {
      this.message = message;
    }

    public Instant getLastWarningAlert() {
      return lastWarningAlert;
    }

    public void setLastWarningAlert(Instant lastWarningAlert) {
      this.lastWarningAlert = lastWarningAlert;
    }

    public Instant getLastExhaustedAlert() {
      return lastExhaustedAlert;
    }

    public void setLastExhaustedAlert(Instant lastExhaustedAlert) {
      this.lastExhaustedAlert = lastExhaustedAlert;
    }
  }

  /** Exception thrown when budget is exhausted. */
  public static class BudgetExhaustedException extends RuntimeException {
    public BudgetExhaustedException(String message) {
      super(message);
    }
  }
}
