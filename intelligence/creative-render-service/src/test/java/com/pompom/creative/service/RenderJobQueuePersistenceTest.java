package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.when;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.repository.RenderJobRepository;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/**
 * Covers the render queue happy path end-to-end against the module's H2 test datasource with the
 * intelligence boundary mocked: {@code queueRenderJob} fetches a snapshot, copies it onto a new
 * {@link RenderJob}, and persists scalar ids + immutable snapshot fields.
 *
 * <p>Guards the Task 2 fixes: the immutable snapshot columns are stored, and the auto-populated
 * {@code createdAt}/{@code updatedAt} timestamps are non-null on insert (NOT NULL would otherwise
 * reject the row).
 */
@SpringBootTest
@ActiveProfiles("test")
class RenderJobQueuePersistenceTest {

  private static final long CONTENT_ID = 42L;
  private static final long PROMPT_VERSION_ID = 7L;
  private static final String PROMPT_SHA = "b".repeat(64);
  private static final String PROMPT_TEXT = "A gentle orange ball named Kiko in Central Square";

  @Autowired private RenderJobOrchestrator orchestrator;

  @Autowired private RenderJobRepository renderJobRepo;

  @MockitoBean private IntelligenceContentClient intelligenceContentClient;

  @BeforeEach
  void stubBoundary() {
    ContentPromptSnapshot snapshot =
        new ContentPromptSnapshot(
            "v1",
            CONTENT_ID,
            "Kiko Episode",
            "EPISODE",
            "RENDER_READY",
            PROMPT_VERSION_ID,
            4,
            PROMPT_TEXT,
            "{}",
            PROMPT_SHA);
    when(intelligenceContentClient.fetch(anyLong(), anyLong())).thenReturn(snapshot);
  }

  @Test
  void queueRenderJob_persistsSnapshotAndNonNullTimestamps() {
    UUID jobId =
        orchestrator.queueRenderJob(CONTENT_ID, PROMPT_VERSION_ID, RenderJob.JobType.FIRST_FRAME);

    RenderJob persisted = renderJobRepo.findById(jobId).orElseThrow();

    // Scalar ownership + immutable snapshot were copied from the fetched snapshot.
    assertThat(persisted.getContentId()).isEqualTo(CONTENT_ID);
    assertThat(persisted.getPromptVersionId()).isEqualTo(PROMPT_VERSION_ID);
    assertThat(persisted.getContentTitleSnapshot()).isEqualTo("Kiko Episode");
    assertThat(persisted.getPromptVersionNumberSnapshot()).isEqualTo(4);
    assertThat(persisted.getPromptSha256()).isEqualTo(PROMPT_SHA);
    assertThat(persisted.getPromptTextSnapshot()).isEqualTo(PROMPT_TEXT);

    // Status + attempt defaults persisted.
    assertThat(persisted.getStatus()).isEqualTo(RenderJob.RenderJobStatus.QUEUED);
    assertThat(persisted.getAttemptNumber()).isEqualTo(1);
    assertThat(persisted.getMaxAttempts()).isEqualTo(3);

    // Timestamps are non-null on insert (the NOT NULL columns are satisfied).
    assertThat(persisted.getQueuedAt()).isNotNull();
    assertThat(persisted.getCreatedAt()).isNotNull();
    assertThat(persisted.getUpdatedAt()).isNotNull();
  }
}
