package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.pompom.creative.domain.PublicationJob;
import com.pompom.creative.domain.PublicationStatus;
import com.pompom.creative.domain.RenderAsset;
import com.pompom.creative.domain.RenderQaResult;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.publisher.PlatformPublisher;
import com.pompom.creative.repository.PublicationAttemptRepository;
import com.pompom.creative.repository.PublicationJobRepository;
import com.pompom.creative.repository.RenderAssetRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class PublicationServiceTest {

  @Mock private PublicationJobRepository publicationJobRepository;
  @Mock private PublicationAttemptRepository publicationAttemptRepository;
  @Mock private RenderAssetRepository renderAssetRepository;
  @Mock private RenderQaResultRepository qaResultRepository;
  @Mock private AssetLibraryManager assetLibraryManager;

  @Mock private Map<String, PlatformPublisher> publishers;

  @Mock private PlatformPublisher mockPublisher;

  @InjectMocks private PublicationService publicationService;
  @TempDir Path tempDir;

  @Test
  void queuePublication_validRequest_createsJob() throws Exception {
    // queuePublication() persists the job and then calls publishAsync(id), which is
    // annotated @Async in production. @InjectMocks constructs a plain PublicationService
    // with no Spring AOP proxy, so @Async has no effect here and publishAsync() runs
    // synchronously in-process -- but this test only asserts the state of the returned job
    // immediately after queuePublication() returns, before publishAsync() has any observable
    // effect on it. The publisher lookup is exercised by publishAsync() itself, which is
    // covered separately; stubbing it here is unnecessary for this test's assertions.
    // Given
    PlatformType platform = PlatformType.TIKTOK;
    UUID assetId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    Path videoPath = tempDir.resolve("video.mp4");
    Files.writeString(videoPath, "verified-video");
    RenderAsset asset =
        RenderAsset.builder()
            .id(assetId)
            .assetType(RenderAsset.AssetType.VIDEO)
            .isCurrent(true)
            .isMock(false)
            .quarantined(false)
            .mediaVerified(true)
            .sha256("checksum")
            .variantId(variantId)
            .build();
    RenderQaResult qa =
        RenderQaResult.builder()
            .decision(RenderQaResult.QaDecision.ACCEPT)
            .requiresHumanReview(false)
            .build();
    when(renderAssetRepository.findById(assetId)).thenReturn(Optional.of(asset));
    when(qaResultRepository.findTopByRenderAssetIdOrderByCreatedAtDesc(assetId))
        .thenReturn(Optional.of(qa));
    when(assetLibraryManager.resolveStoredPath(asset)).thenReturn(videoPath);
    when(assetLibraryManager.checksum(videoPath)).thenReturn("checksum");
    String title = "Test Video";
    String caption = "Test caption";
    String hashtags = "pompomhills,kids";
    Boolean isPrivate = false;

    when(publicationJobRepository.save(any(PublicationJob.class)))
        .thenAnswer(
            invocation -> {
              PublicationJob job = invocation.getArgument(0);
              job.setId(UUID.randomUUID());
              return job;
            });
    when(publicationJobRepository.findByIdempotencyKey(any())).thenReturn(Optional.empty());

    // When
    PublicationJob job =
        publicationService.queuePublication(
            platform, assetId, "account-1", title, caption, hashtags, isPrivate);

    // Then
    assertThat(job).isNotNull();
    assertThat(job.getPlatform()).isEqualTo(platform);
    assertThat(job.getStatus()).isEqualTo(PublicationStatus.QUEUED);
    assertThat(job.getVideoPath()).isEqualTo(videoPath.toString());
    assertThat(job.getRenderAsset()).isEqualTo(asset);
    assertThat(job.getTitle()).isEqualTo(title);

    verify(publicationJobRepository, atLeastOnce()).save(any(PublicationJob.class));
    verify(publicationAttemptRepository).save(any());
  }

  @Test
  void getJob_existingId_returnsJob() {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationJob job =
        PublicationJob.builder()
            .id(jobId)
            .platform(PlatformType.YOUTUBE)
            .status(PublicationStatus.PUBLISHED)
            .build();

    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.of(job));

    // When
    Optional<PublicationJob> result = publicationService.getJob(jobId);

    // Then
    assertThat(result).isPresent();
    assertThat(result.get().getId()).isEqualTo(jobId);
  }

  @Test
  void getJob_nonExistingId_returnsEmpty() {
    // Given
    UUID jobId = UUID.randomUUID();
    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.empty());

    // When
    Optional<PublicationJob> result = publicationService.getJob(jobId);

    // Then
    assertThat(result).isEmpty();
  }

  @Test
  void getJobsByStatus_queued_returnsQueuedJobs() {
    // Given
    List<PublicationJob> queuedJobs =
        List.of(
            PublicationJob.builder().status(PublicationStatus.QUEUED).build(),
            PublicationJob.builder().status(PublicationStatus.QUEUED).build());

    when(publicationJobRepository.findByStatus(PublicationStatus.QUEUED)).thenReturn(queuedJobs);

    // When
    List<PublicationJob> result = publicationService.getJobsByStatus(PublicationStatus.QUEUED);

    // Then
    assertThat(result).hasSize(2);
    assertThat(result).allMatch(job -> job.getStatus() == PublicationStatus.QUEUED);
  }

  @Test
  void getActiveJobs_returnsNonTerminalJobs() {
    // Given
    List<PublicationJob> activeJobs =
        List.of(
            PublicationJob.builder().status(PublicationStatus.QUEUED).build(),
            PublicationJob.builder().status(PublicationStatus.UPLOADING).build(),
            PublicationJob.builder().status(PublicationStatus.PROCESSING).build());

    when(publicationJobRepository.findByStatusIn(any())).thenReturn(activeJobs);

    // When
    List<PublicationJob> result = publicationService.getActiveJobs();

    // Then
    assertThat(result).hasSize(3);
  }

  @Test
  void cancelJob_activeJob_cancelsSuccessfully() {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationJob job =
        PublicationJob.builder()
            .id(jobId)
            .status(PublicationStatus.QUEUED)
            .progressPercent(0)
            .build();

    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.of(job));
    when(publicationJobRepository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

    // When
    boolean cancelled = publicationService.cancelJob(jobId);

    // Then
    assertThat(cancelled).isTrue();
    assertThat(job.getStatus()).isEqualTo(PublicationStatus.CANCELLED);
  }

  @Test
  void cancelJob_completedJob_cannotCancel() {
    // Given
    UUID jobId = UUID.randomUUID();
    PublicationJob job =
        PublicationJob.builder().id(jobId).status(PublicationStatus.PUBLISHED).build();

    when(publicationJobRepository.findById(jobId)).thenReturn(Optional.of(job));

    // When
    boolean cancelled = publicationService.cancelJob(jobId);

    // Then
    assertThat(cancelled).isFalse();
  }

  @Test
  void getStatistics_returnsJobCounts() {
    // Given
    when(publicationJobRepository.countByStatus(PublicationStatus.QUEUED)).thenReturn(3L);
    when(publicationJobRepository.countByStatus(PublicationStatus.UPLOADING)).thenReturn(1L);
    when(publicationJobRepository.countByStatus(PublicationStatus.PROCESSING)).thenReturn(2L);
    when(publicationJobRepository.countByStatus(PublicationStatus.PUBLISHED)).thenReturn(10L);
    when(publicationJobRepository.countByStatus(PublicationStatus.FAILED)).thenReturn(1L);
    when(publicationJobRepository.countByStatus(PublicationStatus.CANCELLED)).thenReturn(0L);

    // When
    Map<String, Long> stats = publicationService.getStatistics();

    // Then
    assertThat(stats).containsEntry("queued", 3L);
    assertThat(stats).containsEntry("uploading", 1L);
    assertThat(stats).containsEntry("processing", 2L);
    assertThat(stats).containsEntry("published", 10L);
    assertThat(stats).containsEntry("failed", 1L);
    assertThat(stats).containsEntry("cancelled", 0L);
  }

  @Test
  void publicationJob_canRetry_checksRetryCount() {
    // Given: Job with retries remaining
    PublicationJob job =
        PublicationJob.builder()
            .status(PublicationStatus.FAILED)
            .retryCount(1)
            .maxRetries(3)
            .build();

    // Then
    assertThat(job.canRetry()).isTrue();
  }

  @Test
  void publicationJob_cannotRetry_maxRetriesReached() {
    // Given: Job with max retries reached
    PublicationJob job =
        PublicationJob.builder()
            .status(PublicationStatus.FAILED)
            .retryCount(3)
            .maxRetries(3)
            .build();

    // Then
    assertThat(job.canRetry()).isFalse();
  }

  @Test
  void publicationJob_isTerminal_checksStatus() {
    // Given
    PublicationJob published = PublicationJob.builder().status(PublicationStatus.PUBLISHED).build();
    PublicationJob failed = PublicationJob.builder().status(PublicationStatus.FAILED).build();
    PublicationJob cancelled = PublicationJob.builder().status(PublicationStatus.CANCELLED).build();
    PublicationJob uploading = PublicationJob.builder().status(PublicationStatus.UPLOADING).build();

    // Then
    assertThat(published.isTerminal()).isTrue();
    assertThat(failed.isTerminal()).isTrue();
    assertThat(cancelled.isTerminal()).isTrue();
    assertThat(uploading.isTerminal()).isFalse();
  }
}
