package com.pompom.creative.api.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.ValidationEvidenceIncompleteRemoteException;
import com.pompom.creative.evidence.ValidationEvidenceNotFoundException;
import com.pompom.creative.queue.IdempotencyKeyConflictException;
import com.pompom.creative.queue.QueueRenderJobRequest;
import com.pompom.creative.queue.QueueRenderJobResponse;
import com.pompom.creative.queue.RenderJobQueueService;
import com.pompom.creative.queue.ValidationEvidenceRejectedException;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

/**
 * HTTP-level coverage for {@code POST /api/v1/render-jobs}: the required {@code Idempotency-Key}
 * header, the 202/Location/Idempotent-Replay response shape, and the stable problem codes for every
 * rejection path. {@link com.pompom.creative.queue.RenderJobQueueServiceTest} already covers the
 * queueing logic itself with mocks; this test covers only the HTTP boundary.
 */
class RenderJobControllerQueueTest {

  private RenderJobQueueService queueService;
  private MockMvc mvc;
  private final ObjectMapper objectMapper = new ObjectMapper();

  @BeforeEach
  void setUp() {
    queueService = mock(RenderJobQueueService.class);
    RenderJobController controller =
        new RenderJobController(
            mock(RenderJobRepository.class), mock(RenderQaResultRepository.class), queueService);
    mvc = MockMvcBuilders.standaloneSetup(controller).build();
  }

  @Test
  void returns202WithLocationWhenANewJobIsQueued() throws Exception {
    UUID jobId = UUID.randomUUID();
    when(queueService.queue(eq("key-1"), any()))
        .thenReturn(new QueueRenderJobResponse(jobId, false));

    mvc.perform(
            post("/api/v1/render-jobs")
                .header("Idempotency-Key", "key-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isAccepted())
        .andExpect(header().string("Location", "/api/v1/render-jobs/" + jobId))
        .andExpect(header().string("Idempotent-Replay", "false"))
        .andExpect(jsonPath("$.renderJobId").value(jobId.toString()));
  }

  @Test
  void returns202WithReplayHeaderWhenAnExistingJobIsReplayed() throws Exception {
    UUID jobId = UUID.randomUUID();
    when(queueService.queue(eq("key-1"), any()))
        .thenReturn(new QueueRenderJobResponse(jobId, true));

    mvc.perform(
            post("/api/v1/render-jobs")
                .header("Idempotency-Key", "key-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isAccepted())
        .andExpect(header().string("Idempotent-Replay", "true"));
  }

  @Test
  void rejectsMissingIdempotencyKeyHeader() throws Exception {
    mvc.perform(
            post("/api/v1/render-jobs")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isBadRequest());
  }

  @Test
  void mapsValidationEvidenceRejectedToUnprocessableEntityWithStableCode() throws Exception {
    when(queueService.queue(eq("key-1"), any()))
        .thenThrow(new ValidationEvidenceRejectedException("EVIDENCE_HAS_BLOCKERS", "blocked"));

    mvc.perform(
            post("/api/v1/render-jobs")
                .header("Idempotency-Key", "key-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isUnprocessableEntity())
        .andExpect(jsonPath("$.errorCode").value("EVIDENCE_HAS_BLOCKERS"));
  }

  @Test
  void mapsIdempotencyKeyConflictTo409() throws Exception {
    when(queueService.queue(eq("key-1"), any()))
        .thenThrow(new IdempotencyKeyConflictException("key-1"));

    mvc.perform(
            post("/api/v1/render-jobs")
                .header("Idempotency-Key", "key-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isConflict());
  }

  @Test
  void mapsValidationEvidenceNotFoundTo422() throws Exception {
    when(queueService.queue(eq("key-1"), any()))
        .thenThrow(new ValidationEvidenceNotFoundException(999L));

    mvc.perform(
            post("/api/v1/render-jobs")
                .header("Idempotency-Key", "key-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isUnprocessableEntity());
  }

  @Test
  void mapsValidationEvidenceIncompleteTo422() throws Exception {
    when(queueService.queue(eq("key-1"), any()))
        .thenThrow(new ValidationEvidenceIncompleteRemoteException(999L));

    mvc.perform(
            post("/api/v1/render-jobs")
                .header("Idempotency-Key", "key-1")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(sampleRequest())))
        .andExpect(status().isUnprocessableEntity());
  }

  private QueueRenderJobRequest sampleRequest() {
    return new QueueRenderJobRequest(
        10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 1), null);
  }
}
