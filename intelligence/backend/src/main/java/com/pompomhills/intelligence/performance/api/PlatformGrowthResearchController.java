package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.PlatformGrowthResearchService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/research")
public class PlatformGrowthResearchController {
  private final PlatformGrowthResearchService service;

  public PlatformGrowthResearchController(PlatformGrowthResearchService service) {
    this.service = service;
  }

  @GetMapping("/platform-tempo")
  PlatformGrowthResearchService.TempoResearch research() {
    return service.research();
  }
}
