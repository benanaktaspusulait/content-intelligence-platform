package com.pompom.creative.api.controller;

import com.pompom.creative.oauth.OAuthService;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.oauth.dto.OAuthToken;
import com.pompom.creative.service.CredentialManager;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.view.RedirectView;

/** REST controller for OAuth flow. */
@RestController
@RequestMapping("/api/v1/oauth")
@Slf4j
@RequiredArgsConstructor
public class OAuthController {

  private final OAuthService oauthService;
  private final CredentialManager credentialManager;

  // In-memory state storage (should use Redis in production)
  private final Map<String, PlatformType> stateStore =
      new java.util.concurrent.ConcurrentHashMap<>();

  /** Initiate OAuth flow for a platform. Returns authorization URL to redirect user to. */
  @GetMapping("/connect/{platform}")
  public ResponseEntity<Map<String, String>> initiateOAuth(@PathVariable String platform) {
    log.info("Initiating OAuth for platform: {}", platform);

    PlatformType platformType;
    try {
      platformType = PlatformType.valueOf(platform.toUpperCase());
    } catch (IllegalArgumentException e) {
      return ResponseEntity.badRequest().body(Map.of("error", "Invalid platform: " + platform));
    }

    // Check if platform is configured
    if (!oauthService.isPlatformConfigured(platformType)) {
      return ResponseEntity.badRequest()
          .body(Map.of("error", "Platform not configured: " + platform));
    }

    // Generate CSRF token
    String state = UUID.randomUUID().toString();
    stateStore.put(state, platformType);

    // Generate authorization URL
    String authUrl = oauthService.generateAuthorizationUrl(platformType, state);

    return ResponseEntity.ok(
        Map.of(
            "authorizationUrl", authUrl,
            "platform", platformType.getDisplayName(),
            "state", state));
  }

  /** OAuth callback endpoint. Platform redirects user here after authorization. */
  @GetMapping("/callback")
  public RedirectView handleCallback(
      @RequestParam("code") String code,
      @RequestParam("state") String state,
      @RequestParam(value = "error", required = false) String error) {
    log.info("OAuth callback received: state={}, error={}", state, error);

    // Handle error from platform
    if (error != null) {
      log.error("OAuth authorization failed: {}", error);
      return new RedirectView("/oauth/error?reason=" + error);
    }

    // Validate state token
    PlatformType platform = stateStore.remove(state);
    if (platform == null) {
      log.error("Invalid state token: {}", state);
      return new RedirectView("/oauth/error?reason=invalid_state");
    }

    try {
      // Exchange code for token
      OAuthToken token = oauthService.exchangeCodeForToken(platform, code);

      // Save encrypted credential
      credentialManager.saveCredential(platform, token);

      log.info("OAuth flow completed successfully: platform={}", platform);

      // Redirect to success page
      return new RedirectView(
          String.format("/oauth/success?platform=%s", platform.name().toLowerCase()));

    } catch (Exception e) {
      log.error("Failed to complete OAuth flow: platform={}", platform, e);
      return new RedirectView("/oauth/error?reason=" + e.getMessage());
    }
  }

  /** Get list of connected platforms. */
  @GetMapping("/connected")
  public ResponseEntity<Map<String, Object>> getConnectedPlatforms() {
    Map<String, Map<String, Boolean>> platforms = new HashMap<>();

    for (PlatformType platform : PlatformType.values()) {
      boolean connected = credentialManager.isConnected(platform);
      platforms.put(platform.name().toLowerCase(), Map.of("connected", connected));
    }

    return ResponseEntity.ok(Map.of("platforms", platforms));
  }

  /** Disconnect a platform. */
  @DeleteMapping("/disconnect/{platform}")
  public ResponseEntity<Map<String, String>> disconnectPlatform(@PathVariable String platform) {
    log.info("Disconnecting platform: {}", platform);

    PlatformType platformType;
    try {
      platformType = PlatformType.valueOf(platform.toUpperCase());
    } catch (IllegalArgumentException e) {
      return ResponseEntity.badRequest().body(Map.of("error", "Invalid platform: " + platform));
    }

    credentialManager.disconnectPlatform(platformType);

    return ResponseEntity.ok(
        Map.of("message", "Platform disconnected successfully", "platform", platform));
  }
}
