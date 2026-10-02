package com.pompomhills.intelligence.meta;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Starts and completes the real Meta/Facebook OAuth authorization flow for read-only analytics
 * access. Only redirects are returned to the browser; no token, code, or secret ever appears in a
 * response body, header value shown to the user, or log line.
 */
@RestController
@RequestMapping("/api/v1/meta/oauth")
public class MetaOAuthController {
  private static final String CONNECTION_PAGE = "/meta/connection";

  private final MetaOAuthService oauthService;
  private final MetaOAuthStateStore stateStore;

  public MetaOAuthController(MetaOAuthService oauthService, MetaOAuthStateStore stateStore) {
    this.oauthService = oauthService;
    this.stateStore = stateStore;
  }

  @GetMapping("/start")
  public ResponseEntity<Void> start() {
    if (!oauthService.isConfigured()) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=not_configured");
    }
    String state = stateStore.issue();
    return redirectTo(oauthService.buildAuthorizationUrl(state));
  }

  @GetMapping("/callback")
  public ResponseEntity<Void> callback(
      @RequestParam(name = "code", required = false) String code,
      @RequestParam(name = "state", required = false) String state,
      @RequestParam(name = "error", required = false) String error) {
    if (error != null && !error.isBlank()) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=denied");
    }
    if (!stateStore.consume(state)) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=invalid_state");
    }
    if (code == null || code.isBlank()) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=missing_code");
    }
    try {
      MetaOAuthService.OAuthCompletionResult result = oauthService.completeAuthorization(code);
      return result.success()
          ? redirectTo(CONNECTION_PAGE + "?meta_oauth=connected")
          : redirectTo(CONNECTION_PAGE + "?meta_oauth=not_managed");
    } catch (MetaOAuthException | MetaGraphException error2) {
      return redirectTo(CONNECTION_PAGE + "?meta_oauth=failed");
    }
  }

  private ResponseEntity<Void> redirectTo(String location) {
    HttpHeaders headers = new HttpHeaders();
    headers.add(HttpHeaders.LOCATION, location);
    return new ResponseEntity<>(headers, HttpStatus.FOUND);
  }
}
