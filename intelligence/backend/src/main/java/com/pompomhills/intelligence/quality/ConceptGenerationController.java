package com.pompomhills.intelligence.quality;

import com.pompomhills.intelligence.character.CanonicalCharacterIdentity;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.*;

/** Local-only generation dispatch with the current configured canonical cast. */
@RestController
@RequestMapping("/api/v1/intelligence/workflow/concepts")
public class ConceptGenerationController {
  private final QualityMlClient client;
  private final JdbcClient jdbc;

  public ConceptGenerationController(QualityMlClient client, JdbcClient jdbc) {
    this.client = client;
    this.jdbc = jdbc;
  }

  @PostMapping("/semantic/short-form-replay")
  public Map<String, Object> replayStructuredShortForm(@RequestBody Map<String, Object> request) {
    return client.workflow("concepts/semantic/short-form-replay", new LinkedHashMap<>(request));
  }

  /** Reanalysis of the fixed stored experiment; no provider or cast mutation. */
  @PostMapping("/semantic/replay")
  public Map<String, Object> replaySemanticEvidence(@RequestBody Map<String, Object> request) {
    return client.workflow("concepts/semantic/replay", new LinkedHashMap<>(request));
  }

  @PostMapping("/generate")
  public Map<String, Object> generate(@RequestBody Map<String, Object> request) {
    var payload = new LinkedHashMap<String, Object>(request);
    payload.put("canonicalCast", new CanonicalCharacterIdentity(jdbc).activeRegistry());
    return client.workflow("concepts/generate", payload);
  }
}
