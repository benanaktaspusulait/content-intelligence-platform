package com.pompomhills.intelligence.meta;

import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Read-only Facebook Page content endpoint, demonstrating pages_read_engagement usage. */
@RestController
@RequestMapping("/api/v1/meta/page")
public class MetaPageContentController {
  private final MetaPageContentService service;

  public MetaPageContentController(MetaPageContentService service) {
    this.service = service;
  }

  @GetMapping("/content")
  public MetaPageContentResponse content() {
    return service.getRecentContent();
  }

  @ExceptionHandler(MetaNotConfiguredException.class)
  public ResponseEntity<Map<String, Object>> handleNotConfigured(MetaNotConfiguredException error) {
    return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
        .body(
            Map.of(
                "status", HttpStatus.SERVICE_UNAVAILABLE.value(), "message", error.getMessage()));
  }
}
