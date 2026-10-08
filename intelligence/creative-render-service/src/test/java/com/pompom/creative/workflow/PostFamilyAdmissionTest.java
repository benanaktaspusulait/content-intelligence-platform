package com.pompom.creative.workflow;

import static org.assertj.core.api.Assertions.*;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.queue.QueueRenderJobRequest;
import java.util.Map;
import org.junit.jupiter.api.Test;

class PostFamilyAdmissionTest {
  @Test
  void incompletePostFamilyEvidenceCannotQueueFinalVideo() {
    var client = new PostFamilyAdmissionClient("http://localhost:1");
    var request =
        new QueueRenderJobRequest(
            1,
            2,
            3,
            RenderJob.JobType.VIDEO,
            "model",
            Map.of("workflowProfile", "post-family-v1"),
            null);
    assertThatThrownBy(() -> client.validate(request)).isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void firstFrameAcquisitionAndFrozenRequestsRemainSeparate() {
    var client = new PostFamilyAdmissionClient("http://localhost:1");
    var first =
        new QueueRenderJobRequest(
            1,
            2,
            3,
            RenderJob.JobType.FIRST_FRAME,
            "model",
            Map.of("workflowProfile", "post-family-v1"),
            null);
    var frozen =
        new QueueRenderJobRequest(1, 2, 3, RenderJob.JobType.VIDEO, "model", Map.of(), null);
    assertThatCode(() -> client.validate(first)).doesNotThrowAnyException();
    assertThatCode(() -> client.validate(frozen)).doesNotThrowAnyException();
  }

  @Test
  void pendingBackendVerdictCannotAuthorizeFinalVideo() throws Exception {
    var server =
        com.sun.net.httpserver.HttpServer.create(new java.net.InetSocketAddress("127.0.0.1", 0), 0);
    server.createContext(
        "/api/v1/intelligence/workflow/records/",
        exchange -> {
          byte[] bytes =
              ("{\"renderAuthorization\":\"BLOCKED_PENDING_EVIDENCE\",\"bindingHash\":\""
                      + "a".repeat(64)
                      + "\"}")
                  .getBytes(java.nio.charset.StandardCharsets.UTF_8);
          exchange.getRequestBody().readAllBytes();
          exchange.getResponseHeaders().add("Content-Type", "application/json");
          exchange.sendResponseHeaders(200, bytes.length);
          exchange.getResponseBody().write(bytes);
          exchange.close();
        });
    server.start();
    try {
      var client =
          new PostFamilyAdmissionClient("http://127.0.0.1:" + server.getAddress().getPort());
      var request =
          new QueueRenderJobRequest(
              1,
              2,
              3,
              RenderJob.JobType.VIDEO,
              "model",
              Map.of(
                  "workflowProfile",
                  "post-family-v1",
                  "workflowReviewId",
                  java.util.UUID.randomUUID().toString(),
                  "workflowBindingHash",
                  "a".repeat(64)),
              null);
      assertThatThrownBy(() -> client.validate(request)).isInstanceOf(IllegalStateException.class);
    } finally {
      server.stop(0);
    }
  }
}
