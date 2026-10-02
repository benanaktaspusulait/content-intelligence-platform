package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.PlatformGrowthProfileService;
import java.time.Instant;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/performance")
public class PlatformGrowthController {
  private final PlatformGrowthProfileService service;

  public PlatformGrowthController(PlatformGrowthProfileService service) {
    this.service = service;
  }

  @GetMapping("/video/{videoId}/platform-profile")
  PlatformGrowthProfileService.GrowthProfile profile(
      @PathVariable UUID videoId,
      @RequestParam(defaultValue = "facebook") String platform,
      @RequestParam(required = false) Instant cutoff) {
    return service.profile(videoId, platform, cutoff == null ? Instant.now() : cutoff);
  }
}
