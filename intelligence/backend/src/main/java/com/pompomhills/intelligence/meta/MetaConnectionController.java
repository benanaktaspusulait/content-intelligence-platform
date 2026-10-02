package com.pompomhills.intelligence.meta;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/meta")
public class MetaConnectionController {
  private final MetaConnectionService service;

  public MetaConnectionController(MetaConnectionService service) {
    this.service = service;
  }

  @GetMapping("/connection")
  public MetaConnectionResponse connection() {
    return service.getConnection();
  }
}
