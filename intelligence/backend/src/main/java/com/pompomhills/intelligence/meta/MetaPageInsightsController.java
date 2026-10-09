package com.pompomhills.intelligence.meta;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/meta/page")
public class MetaPageInsightsController {
  private final MetaPageInsightsService service;

  public MetaPageInsightsController(MetaPageInsightsService service) {
    this.service = service;
  }

  @GetMapping({"/insights", "/insights/{objectId}"})
  public MetaPageInsightsResponse insights(@PathVariable(value = "objectId", required = false) String objectId) {
    return service.get(objectId);
  }

  @PostMapping({"/insights/snapshots", "/insights/{objectId}/snapshots"})
  @ResponseStatus(HttpStatus.CREATED)
  public MetaPageInsightsResponse snapshot(
      @PathVariable(value = "objectId", required = false) String objectId) {
    return service.capture(objectId);
  }
}
