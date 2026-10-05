package com.pompom.creative.api.controller;

import com.pompom.creative.domain.RenderJob.RenderJobStatus;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.CreditTrackingService;
import com.pompom.creative.service.PublicationService;
import com.pompom.creative.service.ScheduledPublishingService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read-only operational snapshot for the local render service. */
@RestController
@RequestMapping("/api/v1/operational")
@RequiredArgsConstructor
public class OperationalStatusController {
  private final RenderJobRepository renderJobs;
  private final PublicationService publications;
  private final ScheduledPublishingService schedules;
  private final CreditTrackingService credits;

  @GetMapping("/status")
  public OperationalStatus status() {
    CreditTrackingService.BudgetStatus budget = credits.getBudgetStatus();
    return new OperationalStatus(
        "AVAILABLE",
        Instant.now(),
        Map.of(
            "queued", renderJobs.countByStatus(RenderJobStatus.QUEUED),
            "generating", renderJobs.countByStatus(RenderJobStatus.GENERATING),
            "polling", renderJobs.countByStatus(RenderJobStatus.POLLING),
            "downloading", renderJobs.countByStatus(RenderJobStatus.DOWNLOADING),
            "complete", renderJobs.countByStatus(RenderJobStatus.COMPLETE),
            "failed", renderJobs.countByStatus(RenderJobStatus.FAILED),
            "abandoned", renderJobs.countByStatus(RenderJobStatus.ABANDONED)),
        publications.getStatistics(),
        schedules.getStatistics(),
        new BudgetSnapshot(
            budget.getBudgetLimit(),
            budget.getUsedCredits(),
            budget.getRemainingCredits(),
            budget.getLevel().name(),
            budget.getTotalJobs()));
  }

  public record OperationalStatus(
      String status,
      Instant observedAt,
      Map<String, Integer> renderJobs,
      Map<String, Long> publications,
      Map<String, Long> schedules,
      BudgetSnapshot budget) {}

  public record BudgetSnapshot(
      BigDecimal budgetLimit,
      BigDecimal usedCredits,
      BigDecimal remainingCredits,
      String level,
      int totalJobs) {}
}
