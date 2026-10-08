package com.pompomhills.intelligence.workflow;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow")
public class WorkflowController {
  private final WorkflowService service;

  @org.springframework.beans.factory.annotation.Autowired
  private com.pompomhills.intelligence.quality.QualityReportPdfService pdf;

  public WorkflowController(WorkflowService service) {
    this.service = service;
  }

  @org.springframework.beans.factory.annotation.Autowired
  private com.pompomhills.intelligence.quality.IntelligenceQualityValidationService
      canonicalValidation;

  @PostMapping("/records/{id}/canonical-validation")
  public com.pompomhills.intelligence.quality.IntelligenceValidateResponse canonicalValidation(
      @PathVariable UUID id) {
    return canonicalValidation.validateWorkflowProfile(service.getByKind(id, "REVIEW"));
  }

  @GetMapping("/learning/retrieve")
  public List<Map<String, Object>> retrieve(
      @RequestParam String contentProfile,
      @RequestParam String modelVersion,
      @RequestParam double duration,
      @RequestParam(defaultValue = "AUTO") String generator,
      @RequestParam(defaultValue = "{}") String settings) {
    try {
      var context = new java.util.LinkedHashMap<String, Object>();
      context.put("generator", generator);
      var parsed = new com.fasterxml.jackson.databind.ObjectMapper().readValue(settings, Map.class);
      if (!parsed.isEmpty()) context.put("settings", parsed);
      return service.retrieveLessons(contentProfile, modelVersion, duration, context);
    } catch (com.fasterxml.jackson.core.JsonProcessingException invalid) {
      throw new IllegalArgumentException("Settings must be a JSON object", invalid);
    }
  }

  @PostMapping("/regeneration-handoff")
  public Map<String, Object> regenerationHandoff(@RequestBody Map<String, Object> request) {
    return service.regenerationHandoff(request);
  }

  @GetMapping("/creative-role/readiness")
  public Map<String, Object> creativeRoleReadiness() {
    return service.creativeRoleReadiness();
  }

  @PostMapping("/creative-role")
  public Map<String, Object> creativeRole(@RequestBody Map<String, Object> request) {
    return service.creativeRole(request);
  }

  @PostMapping("/review")
  public Map<String, Object> review(@RequestBody WorkflowService.ReviewRequest request) {
    return service.runReview(request, true);
  }

  @GetMapping("/records/{id}")
  public Map<String, Object> record(@PathVariable UUID id) {
    return service.get(id);
  }

  @GetMapping("/records")
  public List<Map<String, Object>> records(
      @RequestParam(defaultValue = "REVIEW") String kind,
      @RequestParam(required = false) String contentId,
      @RequestParam(required = false) String promptVersionId,
      @RequestParam(required = false) String bindingHash) {
    return service.list(kind, contentId, promptVersionId, bindingHash);
  }

  @GetMapping(value = "/records/{id}/pdf", produces = "application/pdf")
  public org.springframework.http.ResponseEntity<byte[]> report(@PathVariable UUID id) {
    return org.springframework.http.ResponseEntity.ok()
        .header("Content-Disposition", "inline; filename=pompom-impact-review.pdf")
        .body(pdf.renderWorkflow(service.get(id)));
  }

  @PostMapping("/records/{id}/repair")
  public Map<String, Object> repair(@PathVariable UUID id, @RequestBody Repair request) {
    return service.repair(id, request.patches());
  }

  @PostMapping("/records/{id}/qa")
  public Map<String, Object> qa(@PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.actualQa(id, request);
  }

  @PostMapping("/videos/{videoId}/edited-variant")
  public Map<String, Object> importEdit(
      @PathVariable UUID videoId, @RequestBody Map<String, Object> request) {
    return service.importEditedVariant(videoId, request);
  }

  @GetMapping("/videos/{videoId}/edit-handoffs")
  public List<Map<String, Object>> editedHandoffs(@PathVariable UUID videoId) {
    return service.editedHandoffs(videoId);
  }

  @GetMapping("/videos/{videoId}/qa")
  public List<Map<String, Object>> actualQaRecords(@PathVariable UUID videoId) {
    return service.actualQaRecords(videoId);
  }

  @PostMapping("/videos/{videoId}/qa")
  public Map<String, Object> qaWithoutPlan(
      @PathVariable UUID videoId, @RequestBody Map<String, Object> request) {
    return service.actualQaWithoutPlan(videoId, request);
  }

  @PostMapping("/feedback/{kind}")
  public Map<String, Object> feedback(
      @PathVariable String kind, @RequestBody Map<String, Object> request) {
    return service.feedback(kind, request);
  }

  @PostMapping("/learning/{kind}")
  public Map<String, Object> learning(
      @PathVariable String kind, @RequestBody Map<String, Object> request) {
    return service.lesson(kind, request);
  }

  @PostMapping("/records/{id}/admission")
  public Map<String, Object> admission(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.admission(id, request);
  }

  @PostMapping("/records/{id}/critic")
  public Map<String, Object> critic(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.secondOpinion(id, request);
  }

  @PostMapping("/records/{id}/learning-review")
  public Map<String, Object> learningReview(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.reviewLearning(id, request);
  }

  @ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
  public org.springframework.http.ResponseEntity<Map<String, Object>> invalid(
      RuntimeException error) {
    return org.springframework.http.ResponseEntity.status(409)
        .body(Map.of("status", "UNKNOWN", "detail", error.getMessage()));
  }

  public record Repair(List<Map<String, Object>> patches) {}
}
