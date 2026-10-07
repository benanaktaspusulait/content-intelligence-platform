package com.pompomhills.intelligence.meta;

import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/meta")
public class MetaConnectionController {
  private final MetaConnectionService service;
  private final MetaConnectionLifecycleService lifecycle;

  public MetaConnectionController(
      MetaConnectionService service, MetaConnectionLifecycleService lifecycle) {
    this.service = service;
    this.lifecycle = lifecycle;
  }

  @GetMapping("/connection")
  public MetaConnectionResponse connection() {
    return service.getConnection();
  }

  @PostMapping("/connection/refresh")
  public MetaConnectionResponse refresh(
      @RequestParam(name = "connectionId", required = false) UUID connectionId) {
    if (connectionId != null) {
      return lifecycle.refreshIfNeeded(connectionId);
    }
    return lifecycle
        .currentConnection()
        .map(response -> lifecycle.refreshIfNeeded(response.connectionId()))
        .orElseGet(lifecycle::getConnection);
  }

  @PostMapping("/connection/disconnect")
  public MetaConnectionResponse disconnect(@RequestParam UUID connectionId) {
    return lifecycle.disconnect(connectionId);
  }
}
