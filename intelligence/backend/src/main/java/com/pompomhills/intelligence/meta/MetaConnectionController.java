package com.pompomhills.intelligence.meta;

import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
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
  private final MetaAccountDiscoveryService discovery;

  @Autowired
  public MetaConnectionController(
      MetaConnectionService service,
      MetaConnectionLifecycleService lifecycle,
      MetaAccountDiscoveryService discovery) {
    this.service = service;
    this.lifecycle = lifecycle;
    this.discovery = discovery;
  }

  /** Compatibility constructor for isolated lifecycle/controller tests. */
  public MetaConnectionController(
      MetaConnectionService service, MetaConnectionLifecycleService lifecycle) {
    this(service, lifecycle, null);
  }

  @GetMapping("/connection")
  public MetaConnectionResponse connection() {
    return service.getConnection();
  }

  @GetMapping("/accounts")
  public MetaAccountDiscoveryResponse accounts() {
    return discovery.discover(null);
  }

  @PostMapping("/accounts/discover")
  public MetaAccountDiscoveryResponse discover(
      @RequestParam(name = "connectionId", required = false) UUID connectionId) {
    return discovery.discover(connectionId);
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
