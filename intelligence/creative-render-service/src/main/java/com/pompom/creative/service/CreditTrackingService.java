package com.pompom.creative.service;

import com.pompom.creative.domain.OpenArtCreditLog;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.repository.OpenArtCreditLogRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Service for tracking OpenArt credit usage and budget management. */
@Service
@Slf4j
@RequiredArgsConstructor
public class CreditTrackingService {

  private final OpenArtCreditLogRepository creditLogRepo;
  private BudgetAlertService
      budgetAlertService; // Optional, set via setter to avoid circular dependency

  @Value("${pompom.openart.budget.monthly:1000}")
  private BigDecimal monthlyBudget;

  @Value("${pompom.openart.cost.first-frame:10}")
  private BigDecimal firstFrameCost;

  @Value("${pompom.openart.cost.video:100}")
  private BigDecimal videoCost;

  @Value("${pompom.openart.budget.warning-threshold:0.2}")
  private double warningThreshold; // 20% remaining

  /** Set budget alert service (to avoid circular dependency). */
  public void setBudgetAlertService(BudgetAlertService budgetAlertService) {
    this.budgetAlertService = budgetAlertService;
  }

  /**
   * Record credit usage for a render job.
   *
   * @param job Render job that consumed credits
   * @param actualCredits Actual credits consumed (from OpenArt API)
   * @return Created credit log entry
   */
  @Transactional
  public OpenArtCreditLog recordUsage(RenderJob job, BigDecimal actualCredits) {
    return recordUsage(job, actualCredits, "PROVIDER_USAGE", "provider-status");
  }

  /**
   * Record provider usage exactly once for a remote history id. Poll retries can call this method
   * repeatedly after a worker crash; the provider id makes those retries idempotent and allows
   * separate rerender attempts of the same render job to be charged independently.
   */
  @Transactional
  public OpenArtCreditLog recordProviderUsageIfAbsent(
      RenderJob job, BigDecimal actualCredits, String source) {
    if (actualCredits == null) {
      return null;
    }
    if (actualCredits.signum() < 0) {
      throw new IllegalArgumentException("OpenArt credits cannot be negative");
    }
    String providerJobId = job.getOpenartJobId();
    if (providerJobId == null || providerJobId.isBlank()) {
      throw new IllegalStateException("Cannot record OpenArt usage before provider submission");
    }
    return creditLogRepo
        .findFirstByOpenartJobIdAndOperation(providerJobId, "PROVIDER_USAGE")
        .orElseGet(() -> recordUsage(job, actualCredits, "PROVIDER_USAGE", source));
  }

  private OpenArtCreditLog recordUsage(
      RenderJob job, BigDecimal actualCredits, String operation, String source) {
    if (actualCredits == null || actualCredits.signum() < 0) {
      throw new IllegalArgumentException("OpenArt credits must be zero or greater");
    }
    log.info(
        "Recording credit usage: job={}, credits={}, operation={}",
        job.getId(),
        actualCredits,
        operation);
    job.setCreditsActual(actualCredits);

    OpenArtCreditLog creditLog =
        OpenArtCreditLog.builder()
            .renderJob(job)
            .promptVersionId(job.getPromptVersionId())
            .jobType(job.getJobType() != null ? job.getJobType().name() : null)
            .openartJobId(job.getOpenartJobId())
            .openartModel(job.getOpenartModel())
            .operation(operation)
            .operationMetadata("{\"source\":\"" + source + "\"}")
            .creditsSpent(actualCredits)
            .creditsUsed(actualCredits)
            .build();

    creditLog = creditLogRepo.save(creditLog);

    BudgetStatus status = getBudgetStatus();
    log.info(
        "Budget status after recording: used={}/{}, remaining={}, level={}",
        status.getUsedCredits(),
        status.getBudgetLimit(),
        status.getRemainingCredits(),
        status.getLevel());

    if (budgetAlertService != null) {
      budgetAlertService.checkAndAlert(status);
    }
    return creditLog;
  }

  /**
   * Record estimated credit usage (before actual completion).
   *
   * @param job Render job with estimated credits
   * @return Created credit log entry
   */
  @Transactional
  public OpenArtCreditLog recordEstimatedUsage(RenderJob job) {
    BigDecimal estimatedCredits = job.getCreditsEstimated();

    if (estimatedCredits == null) {
      // Calculate based on job type if not provided
      estimatedCredits = getEstimatedCost(job.getJobType());
    }

    log.info(
        "Recording estimated credit usage: job={}, estimated={}", job.getId(), estimatedCredits);

    return recordUsage(job, estimatedCredits, "ESTIMATE", "queue-estimate");
  }

  /**
   * Get estimated cost for a job type.
   *
   * @param jobType Job type (FIRST_FRAME or VIDEO)
   * @return Estimated credit cost
   */
  public BigDecimal getEstimatedCost(RenderJob.JobType jobType) {
    return jobType == RenderJob.JobType.FIRST_FRAME ? firstFrameCost : videoCost;
  }

  /**
   * Get remaining credits for current month.
   *
   * @return Remaining credits
   */
  public BigDecimal getRemainingCredits() {
    BudgetStatus status = getBudgetStatus();
    return status.getRemainingCredits();
  }

  /**
   * Get current budget status.
   *
   * @return Budget status with usage statistics
   */
  public BudgetStatus getBudgetStatus() {
    Instant monthStart = getMonthStart();

    List<OpenArtCreditLog> monthLogs = creditLogRepo.findByLoggedAtAfter(monthStart);

    BigDecimal usedCredits =
        monthLogs.stream()
            .map(OpenArtCreditLog::getCreditsUsed)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

    BigDecimal remainingCredits = monthlyBudget.subtract(usedCredits);

    // Determine budget level
    BudgetLevel level;
    double remainingPercent =
        remainingCredits.divide(monthlyBudget, 4, BigDecimal.ROUND_HALF_UP).doubleValue();

    if (remainingCredits.compareTo(BigDecimal.ZERO) <= 0) {
      level = BudgetLevel.EXHAUSTED;
    } else if (remainingPercent <= warningThreshold) {
      level = BudgetLevel.WARNING;
    } else {
      level = BudgetLevel.HEALTHY;
    }

    BudgetStatus status = new BudgetStatus();
    status.setBudgetLimit(monthlyBudget);
    status.setUsedCredits(usedCredits);
    status.setRemainingCredits(remainingCredits);
    status.setRemainingPercent(remainingPercent * 100);
    status.setLevel(level);
    status.setMonthStart(monthStart);
    status.setTotalJobs(monthLogs.size());

    return status;
  }

  /**
   * Check if budget allows rendering a job.
   *
   * @param jobType Job type to check
   * @return true if budget allows, false if exhausted
   */
  public boolean canAffordRender(RenderJob.JobType jobType) {
    BigDecimal estimatedCost = getEstimatedCost(jobType);
    BigDecimal remaining = getRemainingCredits();

    boolean canAfford = remaining.compareTo(estimatedCost) >= 0;

    if (!canAfford) {
      log.warn("Insufficient budget: need {} credits, only {} remaining", estimatedCost, remaining);
    }

    return canAfford;
  }

  /**
   * Get credit usage for a specific time period.
   *
   * @param start Period start
   * @param end Period end
   * @return Total credits used in period
   */
  public BigDecimal getUsageForPeriod(Instant start, Instant end) {
    List<OpenArtCreditLog> logs = creditLogRepo.findByLoggedAtBetween(start, end);

    return logs.stream()
        .map(OpenArtCreditLog::getCreditsUsed)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
  }

  /**
   * Get usage statistics by job type.
   *
   * @return Usage statistics
   */
  public UsageStatistics getUsageStatistics() {
    Instant monthStart = getMonthStart();
    List<OpenArtCreditLog> monthLogs = creditLogRepo.findByLoggedAtAfter(monthStart);

    long firstFrameCount =
        monthLogs.stream().filter(log -> "FIRST_FRAME".equals(log.getJobType())).count();

    long videoCount = monthLogs.stream().filter(log -> "VIDEO".equals(log.getJobType())).count();

    BigDecimal firstFrameCredits =
        monthLogs.stream()
            .filter(log -> "FIRST_FRAME".equals(log.getJobType()))
            .map(OpenArtCreditLog::getCreditsUsed)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

    BigDecimal videoCredits =
        monthLogs.stream()
            .filter(log -> "VIDEO".equals(log.getJobType()))
            .map(OpenArtCreditLog::getCreditsUsed)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

    UsageStatistics stats = new UsageStatistics();
    stats.setFirstFrameJobs(firstFrameCount);
    stats.setVideoJobs(videoCount);
    stats.setFirstFrameCredits(firstFrameCredits);
    stats.setVideoCredits(videoCredits);
    stats.setTotalJobs(firstFrameCount + videoCount);
    stats.setTotalCredits(firstFrameCredits.add(videoCredits));

    return stats;
  }

  /** Get start of current month. */
  private Instant getMonthStart() {
    Instant now = Instant.now();
    return now.truncatedTo(ChronoUnit.DAYS)
        .minus(now.atZone(java.time.ZoneId.systemDefault()).getDayOfMonth() - 1, ChronoUnit.DAYS);
  }

  /** Budget status data class. */
  @Data
  public static class BudgetStatus {
    private BigDecimal budgetLimit;
    private BigDecimal usedCredits;
    private BigDecimal remainingCredits;
    private double remainingPercent;
    private BudgetLevel level;
    private Instant monthStart;
    private int totalJobs;
  }

  /** Budget level enum. */
  public enum BudgetLevel {
    HEALTHY, // > 20% remaining
    WARNING, // <= 20% remaining
    EXHAUSTED // <= 0 remaining
  }

  /** Usage statistics data class. */
  @Data
  public static class UsageStatistics {
    private long firstFrameJobs;
    private long videoJobs;
    private BigDecimal firstFrameCredits;
    private BigDecimal videoCredits;
    private long totalJobs;
    private BigDecimal totalCredits;
  }
}
