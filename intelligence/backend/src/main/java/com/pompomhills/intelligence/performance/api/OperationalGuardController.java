package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.OperationalGuardService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/performance/operational-guards")
public class OperationalGuardController {
  private final OperationalGuardService service;

  public OperationalGuardController(OperationalGuardService service) {
    this.service = service;
  }

  @GetMapping
  OperationalGuardService.GuardSnapshot latest(
      @RequestParam(defaultValue = "facebook") String platform,
      @RequestParam(defaultValue = "false") boolean evaluate) {
    return evaluate ? service.evaluate(platform) : service.latest(platform);
  }
}
