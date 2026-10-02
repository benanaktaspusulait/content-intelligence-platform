package com.pompom.creative.queue;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.RenderJob;
import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * {@link RequestFingerprint} must produce the same hash regardless of the request's object-key or
 * map-entry insertion order (canonical JSON, sorted keys), and a different hash for any
 * semantically different request - this is what lets {@code RenderJobQueueService} distinguish a
 * legitimate idempotent replay from a conflicting reuse of the same Idempotency-Key.
 */
class RequestFingerprintTest {

  private final RequestFingerprint fingerprints = new RequestFingerprint(new ObjectMapper());

  @Test
  void producesA64CharacterLowercaseHexDigest() {
    String digest = fingerprints.sha256(sampleRequest());

    assertThat(digest).matches("^[0-9a-f]{64}$");
  }

  @Test
  void isStableAcrossRepeatedCalls() {
    QueueRenderJobRequest request = sampleRequest();

    assertThat(fingerprints.sha256(request)).isEqualTo(fingerprints.sha256(request));
  }

  @Test
  void isInsensitiveToOpenartParamsMapEntryOrder() {
    Map<String, Object> orderA = new LinkedHashMap<>();
    orderA.put("seed", 1);
    orderA.put("style", "soft");

    Map<String, Object> orderB = new LinkedHashMap<>();
    orderB.put("style", "soft");
    orderB.put("seed", 1);

    QueueRenderJobRequest requestA =
        new QueueRenderJobRequest(10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", orderA, null);
    QueueRenderJobRequest requestB =
        new QueueRenderJobRequest(10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", orderB, null);

    assertThat(fingerprints.sha256(requestA)).isEqualTo(fingerprints.sha256(requestB));
  }

  @Test
  void differsWhenOpenartParamsValueDiffers() {
    QueueRenderJobRequest requestA =
        new QueueRenderJobRequest(
            10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 1), null);
    QueueRenderJobRequest requestB =
        new QueueRenderJobRequest(
            10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 2), null);

    assertThat(fingerprints.sha256(requestA)).isNotEqualTo(fingerprints.sha256(requestB));
  }

  @Test
  void differsWhenContentIdDiffers() {
    QueueRenderJobRequest requestA = sampleRequest();
    QueueRenderJobRequest requestB =
        new QueueRenderJobRequest(
            999L,
            requestA.promptVersionId(),
            requestA.validationRecordId(),
            requestA.jobType(),
            requestA.openartModel(),
            requestA.openartParams(),
            requestA.requestPromptSha256());

    assertThat(fingerprints.sha256(requestA)).isNotEqualTo(fingerprints.sha256(requestB));
  }

  private QueueRenderJobRequest sampleRequest() {
    return new QueueRenderJobRequest(
        10L, 11L, 42L, RenderJob.JobType.VIDEO, "model-x", Map.of("seed", 1), null);
  }
}
