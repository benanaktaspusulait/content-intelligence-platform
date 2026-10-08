package com.pompom.creative.workflow;

import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.queue.QueueRenderJobRequest;
import java.util.Map;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

/** Additional gate; the frozen validation policy remains mandatory. */
@Component
public class PostFamilyAdmissionClient {
  private final RestClient client;

  public PostFamilyAdmissionClient(@Value("${pompom.intelligence-base-url}") String baseUrl) {
    var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(5000);
    factory.setReadTimeout(20000);
    this.client = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
  }

  public void validate(QueueRenderJobRequest request) {
    if (request.jobType() == RenderJob.JobType.FIRST_FRAME) return;
    Map<String, Object> params = request.openartParams();
    if (params == null || !params.containsKey("workflowProfile")) return;
    if (!"post-family-v1".equals(params.get("workflowProfile")))
      throw new IllegalArgumentException("Unsupported workflow profile");
    if (!(params.get("workflowReviewId") instanceof String id)
        || !(params.get("workflowBindingHash") instanceof String binding)
        || !binding.matches("[0-9a-f]{64}"))
      throw new IllegalArgumentException("Post-family review and exact binding required");
    UUID.fromString(id);
    var response =
        client
            .post()
            .uri("/api/v1/intelligence/workflow/records/{id}/admission", id)
            .body(
                Map.of(
                    "bindingHash",
                    binding,
                    "contentId",
                    request.contentId(),
                    "promptVersionId",
                    request.promptVersionId(),
                    "model",
                    request.openartModel(),
                    "settings",
                    params))
            .retrieve()
            .body(Map.class);
    if (response == null
        || !"AUTHORIZED".equals(response.get("renderAuthorization"))
        || !binding.equals(response.get("bindingHash")))
      throw new IllegalStateException("Post-family admission pending or stale");
  }
}
