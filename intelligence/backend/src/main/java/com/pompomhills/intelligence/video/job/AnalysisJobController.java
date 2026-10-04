package com.pompomhills.intelligence.video.job;

import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/jobs")
public class AnalysisJobController {
  private final AnalysisJobService service;

  public AnalysisJobController(AnalysisJobService service) {
    this.service = service;
  }

  @PostMapping("/video-analysis/{videoId}")
  AnalysisJobService.EnqueueResult enqueue(@PathVariable UUID videoId) {
    return service.enqueue(videoId);
  }

  @GetMapping("/{id}")
  AnalysisJobService.JobView get(@PathVariable UUID id) {
    return service.get(id);
  }

  @PostMapping("/{id}/retry")
  AnalysisJobService.JobView retry(@PathVariable UUID id) {
    return service.retry(id);
  }
}
