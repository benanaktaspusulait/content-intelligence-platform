package com.pompomhills.intelligence.quality;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Existing-application boundary for starting and inspecting durable production runs. */
@RestController
@RequestMapping("/api/v1/intelligence/autonomous-production/runs")
public class AutonomousProductionController {
  private final QualityMlClient client;

  public AutonomousProductionController(QualityMlClient client) {
    this.client = client;
  }

  @PostMapping
  public Map<String, Object> start(
      @RequestHeader("Idempotency-Key") String idempotencyKey,
      @RequestBody(required = false) Map<String, Object> request) {
    if (idempotencyKey == null || idempotencyKey.isBlank() || idempotencyKey.length() > 200)
      throw new IllegalArgumentException("A 1–200 character Idempotency-Key is required");
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("mode", "EXISTING_ELIGIBLE_FIRST");
    body.put("idempotencyKey", idempotencyKey);
    if (request != null && !request.isEmpty())
      throw new IllegalArgumentException("Production run defaults are fixed; no body options are accepted");
    return client.workflow("autonomous-production/runs", body);
  }

  @GetMapping("/{runId}")
  public Map<String, Object> status(@PathVariable String runId) {
    return client.workflowRead("autonomous-production/runs/" + runId);
  }
}
