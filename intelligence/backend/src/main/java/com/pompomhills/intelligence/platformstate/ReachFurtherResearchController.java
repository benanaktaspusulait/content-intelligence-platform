package com.pompomhills.intelligence.platformstate;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/research/reach-further")
public class ReachFurtherResearchController {
  private final ReachFurtherResearchService service;

  public ReachFurtherResearchController(ReachFurtherResearchService service) {
    this.service = service;
  }

  @GetMapping
  ReachFurtherResearchService.ResearchView research(
      @RequestParam(defaultValue = "facebook") String platform) {
    return service.research(platform);
  }

  @GetMapping("/comparison")
  ReachFurtherResearchService.ComparisonView comparison(
      @RequestParam(defaultValue = "facebook") String platform) {
    return service.comparison(platform);
  }
}
