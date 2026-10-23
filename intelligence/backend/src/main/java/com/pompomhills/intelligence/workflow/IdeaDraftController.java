package com.pompomhills.intelligence.workflow;

import java.util.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow/idea-drafts")
public class IdeaDraftController {
  private final IdeaDraftService service;
  private final IdeaCandidateService candidates;
  private final IdeaExplorationService explorations;

  public IdeaDraftController(
      IdeaDraftService service,
      IdeaExplorationService explorations,
      IdeaCandidateService candidates) {
    this.service = service;
    this.candidates = candidates;
    this.explorations = explorations;
  }

  @GetMapping("/{id}/batches")
  public List<Map<String, Object>> batches(
      @PathVariable UUID id, @RequestParam String workspacePath) {
    return candidates.batches(id, workspacePath);
  }

  @GetMapping("/{id}/candidates")
  public List<Map<String, Object>> candidates(
      @PathVariable UUID id, @RequestParam String workspacePath) {
    return candidates.list(id, workspacePath);
  }

  @PostMapping("/{id}/candidates/{candidate}/decision")
  public Map<String, Object> candidateDecision(
      @PathVariable UUID id,
      @PathVariable UUID candidate,
      @RequestBody Map<String, Object> request) {
    return candidates.decide(id, candidate, request);
  }

  @PostMapping("/{id}/candidates/{candidate}/evaluate")
  public Map<String, Object> candidateEvaluation(
      @PathVariable UUID id,
      @PathVariable UUID candidate,
      @RequestBody Map<String, Object> request) {
    return candidates.reevaluate(id, candidate, request);
  }

  @PostMapping("/{id}/candidates/recover")
  public Map<String, Object> recoverCandidates(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return candidates.recoverForDraft(id, request);
  }

  @PostMapping("/{id}/semantic-review/preview")
  public Map<String, Object> reviewPreview(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return candidates.semanticReviewPreview(id, request);
  }

  @PostMapping("/{id}/semantic-review")
  public Map<String, Object> reviewIdeas(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return candidates.semanticReview(id, request);
  }

  @GetMapping("/{id}/semantic-reviews")
  public List<Map<String, Object>> reviewHistory(
      @PathVariable UUID id, @RequestParam String workspacePath) {
    return candidates.semanticReviewHistory(id, workspacePath);
  }

  @GetMapping
  public List<Map<String, Object>> list() {
    return service.list();
  }

  @GetMapping("/{id}")
  public Map<String, Object> get(@PathVariable UUID id, @RequestParam String workspacePath) {
    return service.get(id, workspacePath);
  }

  @PostMapping
  public Map<String, Object> save(@RequestBody Map<String, Object> request) {
    return service.save(request);
  }

  @PostMapping("/{id}/continue")
  public Map<String, Object> proceed(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return service.continueDraft(id, request);
  }

  @GetMapping("/{id}/explorations")
  public List<Map<String, Object>> explorations(
      @PathVariable UUID id, @RequestParam String workspacePath) {
    return explorations.list(id, workspacePath);
  }

  @PostMapping("/{id}/explorations")
  public Map<String, Object> explore(
      @PathVariable UUID id, @RequestBody Map<String, Object> request) {
    return explorations.generate(id, request);
  }

  @PostMapping("/{id}/explorations/{explorationId}/decision")
  public Map<String, Object> decide(
      @PathVariable UUID id,
      @PathVariable UUID explorationId,
      @RequestBody Map<String, Object> request) {
    return explorations.decide(id, explorationId, request);
  }

  @PostMapping(value = "/{id}/explorations/upload", consumes = "multipart/form-data")
  public Map<String, Object> upload(
      @PathVariable UUID id,
      @RequestParam String workspacePath,
      @RequestParam int expectedRevision,
      @RequestParam String sourceNote,
      @RequestPart("file") org.springframework.web.multipart.MultipartFile file) {
    return explorations.upload(id, workspacePath, expectedRevision, file, sourceNote);
  }

  @GetMapping("/{id}/explorations/selection")
  public Map<String, Object> selection(@PathVariable UUID id, @RequestParam String workspacePath) {
    return explorations.selection(id, workspacePath);
  }

  @PostMapping("/{id}/explorations/{explorationId}/select")
  public Map<String, Object> select(
      @PathVariable UUID id,
      @PathVariable UUID explorationId,
      @RequestBody Map<String, Object> request) {
    return explorations.select(id, explorationId, request);
  }

  @GetMapping("/{id}/explorations/{explorationId}/image")
  public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> image(
      @PathVariable UUID id, @PathVariable UUID explorationId, @RequestParam String workspacePath) {
    var resource = explorations.image(id, explorationId, workspacePath);
    return org.springframework.http.ResponseEntity.ok()
        .contentType(
            org.springframework.http.MediaTypeFactory.getMediaType(resource)
                .orElse(org.springframework.http.MediaType.APPLICATION_OCTET_STREAM))
        .header("Cache-Control", "private, no-store")
        .header("X-Exploratory-Asset", "NOT_PRODUCTION_APPROVED")
        .body(resource);
  }
}
