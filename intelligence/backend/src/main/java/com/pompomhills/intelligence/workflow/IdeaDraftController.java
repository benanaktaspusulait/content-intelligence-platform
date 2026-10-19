package com.pompomhills.intelligence.workflow;

import java.util.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow/idea-drafts")
public class IdeaDraftController {
  private final IdeaDraftService service;
  private final IdeaExplorationService explorations;

  public IdeaDraftController(IdeaDraftService service, IdeaExplorationService explorations) {
    this.service = service;
    this.explorations = explorations;
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
  public List<Map<String,Object>> explorations(@PathVariable UUID id,@RequestParam String workspacePath) {
    return explorations.list(id,workspacePath);
  }

  @PostMapping("/{id}/explorations")
  public Map<String,Object> explore(@PathVariable UUID id,@RequestBody Map<String,Object> request) {
    return explorations.generate(id,request);
  }

  @PostMapping("/{id}/explorations/{explorationId}/decision")
  public Map<String,Object> decide(@PathVariable UUID id,@PathVariable UUID explorationId,@RequestBody Map<String,Object> request) {
    return explorations.decide(id,explorationId,request);
  }

  @GetMapping("/{id}/explorations/{explorationId}/image")
  public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> image(
      @PathVariable UUID id,@PathVariable UUID explorationId,@RequestParam String workspacePath) {
    return org.springframework.http.ResponseEntity.ok()
        .contentType(org.springframework.http.MediaType.IMAGE_PNG)
        .header("Cache-Control","private, no-store")
        .header("X-Exploratory-Asset","NOT_PRODUCTION_APPROVED")
        .body(explorations.image(id,explorationId,workspacePath));
  }
}
