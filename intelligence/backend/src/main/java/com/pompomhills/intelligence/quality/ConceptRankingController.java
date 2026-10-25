package com.pompomhills.intelligence.quality;

import java.util.Map;
import org.springframework.web.bind.annotation.*;

/** Stateless editorial ranking; the ML boundary owns the shared input schema. */
@RestController
@RequestMapping("/api/v1/intelligence/workflow/concepts")
public class ConceptRankingController {
  private final QualityMlClient client;

  public ConceptRankingController(QualityMlClient client) { this.client = client; }

  @PostMapping("/rank")
  public Map<String, Object> rank(@RequestBody Map<String, Object> request) {
    return client.workflow("concepts/rank", request);
  }

  @PostMapping("/validate")
  public Map<String, Object> validate(@RequestBody Map<String, Object> request) {
    return client.workflow("concepts/validate", request);
  }
}
