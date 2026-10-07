package com.pompomhills.intelligence.meta;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Starts and completes the owner-bound Meta OAuth flow without returning provider secrets. */
@RestController
@RequestMapping("/api/v1/meta/oauth")
public class MetaOAuthController {
  private static final String CONNECTION_PAGE = "/meta/connection";

  private final MetaConnectionLifecycleService lifecycle;
  private final MetaOAuthStateStore stateStore;
  private final MetaReadProperties properties;

  public MetaOAuthController(
      MetaConnectionLifecycleService lifecycle,
      MetaOAuthStateStore stateStore,
      MetaReadProperties properties) {
    this.lifecycle = lifecycle;
    this.stateStore = stateStore;
    this.properties = properties;
  }

  @GetMapping("/start")
  public ResponseEntity<Void> start() {
    if (!lifecycle.isConfigured()) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=not_configured");
    }
    String state = stateStore.issue(properties.connectionOwnerKey());
    return redirectTo(lifecycle.buildAuthorizationUrl(state));
  }

  @GetMapping("/callback")
  public ResponseEntity<Void> callback(
      @RequestParam(name = "code", required = false) String code,
      @RequestParam(name = "state", required = false) String state,
      @RequestParam(name = "error", required = false) String error) {
    if (!stateStore.consume(state, properties.connectionOwnerKey())) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=invalid_state");
    }
    if (error != null && !error.isBlank()) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=denied");
    }
    if (code == null || code.isBlank()) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=missing_code");
    }
    try {
      MetaConnectionResponse result = lifecycle.completeAuthorization(code, state);
      if (result.connectionId() != null && result.failureReason() == null) {
        return redirectTo(CONNECTION_PAGE + "?meta_oauth=connected");
      }
      if (result.message() != null && result.message().contains("does not manage")) {
        return redirectTo(CONNECTION_PAGE + "?meta_oauth=not_managed");
      }
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=failed");
    } catch (RuntimeException ignored) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=failed");
    }
  }

  private ResponseEntity<Void> redirectTo(String location) {
    HttpHeaders headers = new HttpHeaders();
    headers.add(HttpHeaders.LOCATION, location);
    return new ResponseEntity<>(headers, HttpStatus.FOUND);
  }
}
