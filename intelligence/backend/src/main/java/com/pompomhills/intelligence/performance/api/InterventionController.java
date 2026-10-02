package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.InterventionService;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/videos/{videoId}/interventions")
public class InterventionController {
  private final InterventionService service;

  public InterventionController(InterventionService service) {
    this.service = service;
  }

  @PostMapping
  InterventionService.InterventionView record(
      @PathVariable UUID videoId,
      @RequestBody InterventionService.InterventionRequest request,
      @RequestHeader(defaultValue = "local-user") String actor) {
    return service.record(videoId, request, actor);
  }

  @GetMapping
  List<InterventionService.InterventionView> list(
      @PathVariable UUID videoId, @RequestParam(defaultValue = "facebook") String platform) {
    return service.list(videoId, platform);
  }
}
