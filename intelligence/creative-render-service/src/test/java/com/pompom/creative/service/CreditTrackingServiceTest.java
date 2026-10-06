package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.OpenArtCreditLog;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.repository.OpenArtCreditLogRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class CreditTrackingServiceTest {

  @Mock private OpenArtCreditLogRepository creditLogRepo;

  private CreditTrackingService creditTrackingService;

  @BeforeEach
  void setUp() {
    creditTrackingService = new CreditTrackingService(creditLogRepo);

    // Set configuration values via reflection
    ReflectionTestUtils.setField(creditTrackingService, "monthlyBudget", new BigDecimal("1000"));
    ReflectionTestUtils.setField(creditTrackingService, "firstFrameCost", new BigDecimal("10"));
    ReflectionTestUtils.setField(creditTrackingService, "videoCost", new BigDecimal("100"));
    ReflectionTestUtils.setField(creditTrackingService, "warningThreshold", 0.2);
  }

  @Test
  void recordUsage_savesLogEntry() {
    // Given
    RenderJob job = createJob(RenderJob.JobType.VIDEO);
    BigDecimal credits = new BigDecimal("100");

    when(creditLogRepo.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(List.of());

    // When
    OpenArtCreditLog log = creditTrackingService.recordUsage(job, credits);

    // Then
    assertThat(log.getRenderJob()).isEqualTo(job);
    assertThat(log.getCreditsUsed()).isEqualTo(credits);
    assertThat(log.getCreditsSpent()).isEqualTo(credits);
    assertThat(log.getOperation()).isEqualTo("PROVIDER_USAGE");
    verify(creditLogRepo).save(any(OpenArtCreditLog.class));
  }

  @Test
  void getEstimatedCost_firstFrame_returns10() {
    // When
    BigDecimal cost = creditTrackingService.getEstimatedCost(RenderJob.JobType.FIRST_FRAME);

    // Then
    assertThat(cost).isEqualTo(new BigDecimal("10"));
  }

  @Test
  void getEstimatedCost_video_returns100() {
    // When
    BigDecimal cost = creditTrackingService.getEstimatedCost(RenderJob.JobType.VIDEO);

    // Then
    assertThat(cost).isEqualTo(new BigDecimal("100"));
  }

  @Test
  void getBudgetStatus_noUsage_returnsHealthy() {
    // Given: No credit usage this month
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(List.of());

    // When
    CreditTrackingService.BudgetStatus status = creditTrackingService.getBudgetStatus();

    // Then
    assertThat(status.getBudgetLimit()).isEqualTo(new BigDecimal("1000"));
    assertThat(status.getUsedCredits()).isEqualTo(BigDecimal.ZERO);
    assertThat(status.getRemainingCredits()).isEqualTo(new BigDecimal("1000"));
    assertThat(status.getRemainingPercent()).isEqualTo(100.0);
    assertThat(status.getLevel()).isEqualTo(CreditTrackingService.BudgetLevel.HEALTHY);
  }

  @Test
  void getBudgetStatus_80percentUsed_returnsWarning() {
    // Given: 800 credits used (80%)
    List<OpenArtCreditLog> logs =
        Arrays.asList(createLog(new BigDecimal("400")), createLog(new BigDecimal("400")));
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(logs);

    // When
    CreditTrackingService.BudgetStatus status = creditTrackingService.getBudgetStatus();

    // Then
    assertThat(status.getUsedCredits()).isEqualTo(new BigDecimal("800"));
    assertThat(status.getRemainingCredits()).isEqualTo(new BigDecimal("200"));
    assertThat(status.getRemainingPercent()).isEqualTo(20.0);
    assertThat(status.getLevel()).isEqualTo(CreditTrackingService.BudgetLevel.WARNING);
  }

  @Test
  void getBudgetStatus_overBudget_returnsExhausted() {
    // Given: 1100 credits used (110%)
    List<OpenArtCreditLog> logs =
        Arrays.asList(createLog(new BigDecimal("600")), createLog(new BigDecimal("500")));
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(logs);

    // When
    CreditTrackingService.BudgetStatus status = creditTrackingService.getBudgetStatus();

    // Then
    assertThat(status.getUsedCredits()).isEqualTo(new BigDecimal("1100"));
    assertThat(status.getRemainingCredits()).isEqualTo(new BigDecimal("-100"));
    assertThat(status.getLevel()).isEqualTo(CreditTrackingService.BudgetLevel.EXHAUSTED);
  }

  @Test
  void canAffordRender_sufficientBudget_returnsTrue() {
    // Given: 500 credits remaining
    when(creditLogRepo.findByLoggedAtAfter(any()))
        .thenReturn(List.of(createLog(new BigDecimal("500"))));

    // When
    boolean canAfford = creditTrackingService.canAffordRender(RenderJob.JobType.VIDEO);

    // Then (100 credits needed, 500 remaining)
    assertThat(canAfford).isTrue();
  }

  @Test
  void canAffordRender_insufficientBudget_returnsFalse() {
    // Given: 50 credits remaining
    when(creditLogRepo.findByLoggedAtAfter(any()))
        .thenReturn(List.of(createLog(new BigDecimal("950"))));

    // When
    boolean canAfford = creditTrackingService.canAffordRender(RenderJob.JobType.VIDEO);

    // Then (100 credits needed, only 50 remaining)
    assertThat(canAfford).isFalse();
  }

  @Test
  void getUsageStatistics_mixedJobs_calculatesCorrectly() {
    // Given: 2 first-frame (10 each), 3 video (100 each)
    List<OpenArtCreditLog> logs =
        Arrays.asList(
            createLog(RenderJob.JobType.FIRST_FRAME, new BigDecimal("10")),
            createLog(RenderJob.JobType.FIRST_FRAME, new BigDecimal("10")),
            createLog(RenderJob.JobType.VIDEO, new BigDecimal("100")),
            createLog(RenderJob.JobType.VIDEO, new BigDecimal("100")),
            createLog(RenderJob.JobType.VIDEO, new BigDecimal("100")));
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(logs);

    // When
    CreditTrackingService.UsageStatistics stats = creditTrackingService.getUsageStatistics();

    // Then
    assertThat(stats.getFirstFrameJobs()).isEqualTo(2);
    assertThat(stats.getVideoJobs()).isEqualTo(3);
    assertThat(stats.getFirstFrameCredits()).isEqualTo(new BigDecimal("20"));
    assertThat(stats.getVideoCredits()).isEqualTo(new BigDecimal("300"));
    assertThat(stats.getTotalJobs()).isEqualTo(5);
    assertThat(stats.getTotalCredits()).isEqualTo(new BigDecimal("320"));
  }

  @Test
  void providerUsage_isIdempotentForTheSameProviderJob() {
    RenderJob job = createJob(RenderJob.JobType.VIDEO);
    when(creditLogRepo.findFirstByOpenartJobIdAndOperation("test-job-123", "PROVIDER_USAGE"))
        .thenReturn(java.util.Optional.empty());
    when(creditLogRepo.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(List.of());

    creditTrackingService.recordProviderUsageIfAbsent(
        job, new BigDecimal("12.5"), "provider-status");

    verify(creditLogRepo).save(any(OpenArtCreditLog.class));
    assertThat(job.getCreditsActual()).isEqualByComparingTo("12.5");
  }

  @Test
  void providerUsageAggregatesAcrossRerenderAttempts() {
    RenderJob job = createJob(RenderJob.JobType.VIDEO);
    when(creditLogRepo.findFirstByOpenartJobIdAndOperation(any(), eq("PROVIDER_USAGE")))
        .thenReturn(java.util.Optional.empty());
    when(creditLogRepo.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
    when(creditLogRepo.findByLoggedAtAfter(any())).thenReturn(List.of());

    creditTrackingService.recordProviderUsageIfAbsent(
        job, new BigDecimal("12.5"), "provider-status");
    job.setOpenartJobId("retry-job-456");
    creditTrackingService.recordProviderUsageIfAbsent(job, new BigDecimal("5"), "provider-status");

    assertThat(job.getCreditsActual()).isEqualByComparingTo("17.5");
  }

  // Helper methods

  private RenderJob createJob(RenderJob.JobType jobType) {
    return RenderJob.builder()
        .id(UUID.randomUUID())
        .contentId(1L)
        .promptVersionId(1L)
        .jobType(jobType)
        .openartJobId("test-job-123")
        .openartModel("test-model")
        .build();
  }

  private OpenArtCreditLog createLog(BigDecimal credits) {
    return createLog(RenderJob.JobType.VIDEO, credits);
  }

  private OpenArtCreditLog createLog(RenderJob.JobType jobType, BigDecimal credits) {
    return OpenArtCreditLog.builder()
        .id(UUID.randomUUID())
        .jobType(jobType.name())
        .creditsUsed(credits)
        .loggedAt(Instant.now())
        .build();
  }
}
