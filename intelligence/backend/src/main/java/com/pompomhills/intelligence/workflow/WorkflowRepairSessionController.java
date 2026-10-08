package com.pompomhills.intelligence.workflow;

import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow/repair-sessions")
public class WorkflowRepairSessionController {
  private final WorkflowRepairSessionService service;

  public WorkflowRepairSessionController(WorkflowRepairSessionService service) {
    this.service = service;
  }

  public record Start(
      UUID reviewId, String idempotencyKey, Integer maxAttempts, Double maxCostUsd) {}

  @PostMapping
  public Map<String, Object> start(@RequestBody Start request) {
    return service.start(
        request.reviewId(),
        request.idempotencyKey(),
        request.maxAttempts() == null ? 2 : request.maxAttempts(),
        request.maxCostUsd() == null ? 0 : request.maxCostUsd());
  }

  @GetMapping("/{id}")
  public Map<String, Object> get(@PathVariable UUID id) {
    return service.get(id);
  }

  @PostMapping("/{id}/step")
  public Map<String, Object> step(@PathVariable UUID id) {
    return service.step(id);
  }

  public record Decision(String decision) {}

  @PostMapping("/{id}/decision")
  public Map<String, Object> decide(@PathVariable UUID id, @RequestBody Decision request) {
    return service.decide(id, request.decision());
  }

  @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
  public org.springframework.http.ResponseEntity<Map<String, Object>> invalid(
      RuntimeException error) {
    return org.springframework.http.ResponseEntity.status(409)
        .body(Map.of("status", "UNKNOWN", "detail", error.getMessage()));
  }
}
