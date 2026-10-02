package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.ScheduledPublication;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.ScheduledPublicationRepository;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class ScheduledPublishingServiceTest {

  @Mock private ScheduledPublicationRepository scheduledPublicationRepository;

  @Mock private PublicationService publicationService;

  @InjectMocks private ScheduledPublishingService scheduledPublishingService;

  @Test
  void schedulePublication_futureTime_createsSchedule() {
    // Given
    PlatformType platform = PlatformType.TIKTOK;
    String videoPath = "/tmp/video.mp4";
    Instant scheduledAt = Instant.now().plus(1, ChronoUnit.HOURS);
    String timezone = "Europe/Istanbul";

    when(scheduledPublicationRepository.save(any(ScheduledPublication.class)))
        .thenAnswer(
            invocation -> {
              ScheduledPublication pub = invocation.getArgument(0);
              pub.setId(UUID.randomUUID());
              return pub;
            });

    // When
    ScheduledPublication result =
        scheduledPublishingService.schedulePublication(
            platform, videoPath, "Title", "Caption", "hashtags", false, scheduledAt, timezone);

    // Then
    assertThat(result).isNotNull();
    assertThat(result.getPlatform()).isEqualTo(platform);
    assertThat(result.getScheduledAt()).isEqualTo(scheduledAt);
    assertThat(result.getTimezone()).isEqualTo(timezone);
    assertThat(result.getIsExecuted()).isFalse();

    verify(scheduledPublicationRepository).save(any(ScheduledPublication.class));
  }

  @Test
  void schedulePublication_pastTime_throwsException() {
    // Given
    Instant pastTime = Instant.now().minus(1, ChronoUnit.HOURS);

    // When/Then
    assertThatThrownBy(
            () ->
                scheduledPublishingService.schedulePublication(
                    PlatformType.YOUTUBE,
                    "/tmp/video.mp4",
                    "Title",
                    "Caption",
                    "hashtags",
                    false,
                    pastTime,
                    "UTC"))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("must be in the future");
  }

  @Test
  void schedulePublication_withZonedDateTime_convertsToInstant() {
    // Given
    ZonedDateTime scheduledAt =
        ZonedDateTime.now(ZoneId.of("America/New_York")).plus(2, ChronoUnit.HOURS);

    when(scheduledPublicationRepository.save(any(ScheduledPublication.class)))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    ScheduledPublication result =
        scheduledPublishingService.schedulePublication(
            PlatformType.FACEBOOK,
            "/tmp/video.mp4",
            "Title",
            "Caption",
            "hashtags",
            false,
            scheduledAt);

    // Then
    assertThat(result.getScheduledAt()).isEqualTo(scheduledAt.toInstant());
    assertThat(result.getTimezone()).isEqualTo("America/New_York");
  }

  @Test
  void executeScheduledPublication_createsPublicationJob() {
    // Given
    UUID scheduleId = UUID.randomUUID();
    ScheduledPublication scheduled =
        ScheduledPublication.builder()
            .id(scheduleId)
            .platform(PlatformType.INSTAGRAM)
            .videoPath("/tmp/video.mp4")
            .title("Title")
            .caption("Caption")
            .hashtags("tag1,tag2")
            .isPrivate(false)
            .scheduledAt(Instant.now())
            .isExecuted(false)
            .build();

    UUID jobId = UUID.randomUUID();
    PublicationJob job = PublicationJob.builder().id(jobId).build();

    when(publicationService.queuePublication(any(), any(), any(), any(), any(), any()))
        .thenReturn(job);
    when(scheduledPublicationRepository.save(any()))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    scheduledPublishingService.executeScheduledPublication(scheduled);

    // Then
    assertThat(scheduled.getIsExecuted()).isTrue();
    assertThat(scheduled.getPublicationJobId()).isEqualTo(jobId);
    assertThat(scheduled.getExecutedAt()).isNotNull();

    verify(publicationService)
        .queuePublication(
            PlatformType.INSTAGRAM, "/tmp/video.mp4", "Title", "Caption", "tag1,tag2", false);
    verify(scheduledPublicationRepository).save(scheduled);
  }

  @Test
  void processScheduledPublications_withDuePublications_executesThem() {
    // Given
    Instant pastTime = Instant.now().minus(10, ChronoUnit.MINUTES);

    ScheduledPublication due1 =
        ScheduledPublication.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.TIKTOK)
            .videoPath("/tmp/video1.mp4")
            .scheduledAt(pastTime)
            .isExecuted(false)
            .build();

    ScheduledPublication due2 =
        ScheduledPublication.builder()
            .id(UUID.randomUUID())
            .platform(PlatformType.YOUTUBE)
            .videoPath("/tmp/video2.mp4")
            .scheduledAt(pastTime)
            .isExecuted(false)
            .build();

    when(scheduledPublicationRepository.findByIsExecutedFalseAndScheduledAtBefore(any()))
        .thenReturn(List.of(due1, due2));

    when(publicationService.queuePublication(any(), any(), any(), any(), any(), any()))
        .thenReturn(PublicationJob.builder().id(UUID.randomUUID()).build());

    when(scheduledPublicationRepository.save(any()))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    scheduledPublishingService.processScheduledPublications();

    // Then
    verify(publicationService, times(2)).queuePublication(any(), any(), any(), any(), any(), any());
    verify(scheduledPublicationRepository, times(2)).save(any());
  }

  @Test
  void getPendingScheduled_returnsUnexecutedPublications() {
    // Given
    List<ScheduledPublication> pending =
        List.of(
            ScheduledPublication.builder().isExecuted(false).build(),
            ScheduledPublication.builder().isExecuted(false).build());

    when(scheduledPublicationRepository.findByIsExecutedFalse()).thenReturn(pending);

    // When
    List<ScheduledPublication> result = scheduledPublishingService.getPendingScheduled();

    // Then
    assertThat(result).hasSize(2);
  }

  @Test
  void cancelScheduled_unexecutedPublication_deletesIt() {
    // Given
    UUID scheduleId = UUID.randomUUID();
    ScheduledPublication scheduled =
        ScheduledPublication.builder().id(scheduleId).isExecuted(false).build();

    when(scheduledPublicationRepository.findById(scheduleId)).thenReturn(Optional.of(scheduled));

    // When
    boolean cancelled = scheduledPublishingService.cancelScheduled(scheduleId);

    // Then
    assertThat(cancelled).isTrue();
    verify(scheduledPublicationRepository).delete(scheduled);
  }

  @Test
  void cancelScheduled_executedPublication_cannotCancel() {
    // Given
    UUID scheduleId = UUID.randomUUID();
    ScheduledPublication scheduled =
        ScheduledPublication.builder().id(scheduleId).isExecuted(true).build();

    when(scheduledPublicationRepository.findById(scheduleId)).thenReturn(Optional.of(scheduled));

    // When
    boolean cancelled = scheduledPublishingService.cancelScheduled(scheduleId);

    // Then
    assertThat(cancelled).isFalse();
    verify(scheduledPublicationRepository, never()).delete(any());
  }

  @Test
  void reschedule_validNewTime_updatesScheduledAt() {
    // Given
    UUID scheduleId = UUID.randomUUID();
    Instant oldTime = Instant.now().plus(1, ChronoUnit.HOURS);
    Instant newTime = Instant.now().plus(2, ChronoUnit.HOURS);

    ScheduledPublication scheduled =
        ScheduledPublication.builder()
            .id(scheduleId)
            .scheduledAt(oldTime)
            .isExecuted(false)
            .build();

    when(scheduledPublicationRepository.findById(scheduleId)).thenReturn(Optional.of(scheduled));
    when(scheduledPublicationRepository.save(any()))
        .thenAnswer(invocation -> invocation.getArgument(0));

    // When
    boolean rescheduled = scheduledPublishingService.reschedule(scheduleId, newTime);

    // Then
    assertThat(rescheduled).isTrue();
    assertThat(scheduled.getScheduledAt()).isEqualTo(newTime);
    verify(scheduledPublicationRepository).save(scheduled);
  }

  @Test
  void reschedule_pastTime_throwsException() {
    // Given
    UUID scheduleId = UUID.randomUUID();
    Instant pastTime = Instant.now().minus(1, ChronoUnit.HOURS);

    ScheduledPublication scheduled =
        ScheduledPublication.builder().id(scheduleId).isExecuted(false).build();

    when(scheduledPublicationRepository.findById(scheduleId)).thenReturn(Optional.of(scheduled));

    // When/Then
    assertThatThrownBy(() -> scheduledPublishingService.reschedule(scheduleId, pastTime))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("must be in the future");
  }

  @Test
  void scheduledPublication_isDue_checksTime() {
    // Given: Publication scheduled in past
    ScheduledPublication past =
        ScheduledPublication.builder()
            .scheduledAt(Instant.now().minus(1, ChronoUnit.HOURS))
            .isExecuted(false)
            .build();

    // Given: Publication scheduled in future
    ScheduledPublication future =
        ScheduledPublication.builder()
            .scheduledAt(Instant.now().plus(1, ChronoUnit.HOURS))
            .isExecuted(false)
            .build();

    // Given: Executed publication (even if in past)
    ScheduledPublication executed =
        ScheduledPublication.builder()
            .scheduledAt(Instant.now().minus(1, ChronoUnit.HOURS))
            .isExecuted(true)
            .build();

    // Then
    assertThat(past.isDue()).isTrue();
    assertThat(future.isDue()).isFalse();
    assertThat(executed.isDue()).isFalse();
  }
}
