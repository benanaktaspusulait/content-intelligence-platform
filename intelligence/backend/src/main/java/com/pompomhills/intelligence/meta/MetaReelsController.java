package com.pompomhills.intelligence.meta;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

/**
 * Read-only Instagram Reels discovery and analytics snapshot endpoints. GET and append-only POST.
 */
@RestController
@RequestMapping("/api/v1/meta/instagram/reels")
public class MetaReelsController {
  private final MetaReelsService service;

  public MetaReelsController(MetaReelsService service) {
    this.service = service;
  }

  @GetMapping
  public MetaReelsResponse list(
      @RequestParam(name = "after", required = false) String after,
      @RequestParam(name = "limit", required = false) Integer limit) {
    return service.listReels(after, limit);
  }

  @GetMapping("/{mediaId}")
  public MetaReelsResponse.ReelSummary reel(@PathVariable("mediaId") String mediaId) {
    return service.getReel(mediaId);
  }

  @GetMapping("/{mediaId}/analytics")
  public MetaReelAnalyticsResponse analytics(@PathVariable("mediaId") String mediaId) {
    return service.getAnalytics(mediaId);
  }

  @PostMapping("/{mediaId}/snapshots")
  @ResponseStatus(HttpStatus.CREATED)
  public MetaSnapshotResponse captureSnapshot(@PathVariable("mediaId") String mediaId) {
    return service.captureSnapshot(mediaId);
  }

  @ExceptionHandler(MetaNotConfiguredException.class)
  public ResponseEntity<Map<String, Object>> handleNotConfigured(MetaNotConfiguredException error) {
    return error(HttpStatus.SERVICE_UNAVAILABLE, error.getMessage());
  }

  @ExceptionHandler(IllegalArgumentException.class)
  public ResponseEntity<Map<String, Object>> handleInvalidArgument(IllegalArgumentException error) {
    return error(HttpStatus.BAD_REQUEST, error.getMessage());
  }

  @ExceptionHandler(MetaGraphException.class)
  public ResponseEntity<Map<String, Object>> handleGraphError(MetaGraphException error) {
    HttpStatus status =
        switch (error.httpStatus()) {
          case 400, 404 -> HttpStatus.NOT_FOUND;
          case 403 -> HttpStatus.FORBIDDEN;
          default -> HttpStatus.BAD_GATEWAY;
        };
    return error(status, "Meta Graph API request could not be completed.");
  }

  private ResponseEntity<Map<String, Object>> error(HttpStatus status, String message) {
    return ResponseEntity.status(status).body(Map.of("status", status.value(), "message", message));
  }
}
