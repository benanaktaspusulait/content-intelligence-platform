package com.pompomhills.intelligence.quality;

import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.*;

/** Explicit editorial surface. Does not save, regrade or authorize production. */
@RestController
@RequestMapping("/api/v1/intelligence/workflow/short-form")
public class ShortFormController {
  private final QualityMlClient client;

  public ShortFormController(QualityMlClient client) {
    this.client = client;
  }

  public record ShortFormRequest(
      @NotBlank @Size(max = 50000) String text,
      @DecimalMin("0.01") @DecimalMax("600") Double desiredDuration) {}

  @PostMapping("/evaluate")
  public Map<String, Object> evaluate(@Valid @RequestBody ShortFormRequest request) {
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("text", request.text());
    if (request.desiredDuration() != null) payload.put("desiredDuration", request.desiredDuration());
    return client.workflow("short-form/evaluate", payload);
  }
}
