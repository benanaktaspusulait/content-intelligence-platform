package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.PerformanceImportService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/imports")
public class PerformanceImportController {
  private final PerformanceImportService service;

  public PerformanceImportController(PerformanceImportService service) {
    this.service = service;
  }

  @PostMapping(path = "/preview", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
  PerformanceImportService.ImportPreview preview(
      @RequestPart("file") MultipartFile file,
      @RequestParam(required = false) String platform,
      @RequestParam(defaultValue = "UTC") String timezone,
      @RequestParam(required = false) UUID correctionOfBatchId,
      @RequestParam(required = false) String correctionReason) {
    return service.preview(file, platform, timezone, correctionOfBatchId, correctionReason);
  }

  @GetMapping("/{id}")
  PerformanceImportService.ImportPreview get(@PathVariable UUID id) {
    return service.get(id);
  }

  @PostMapping("/{id}/commit")
  PerformanceImportService.ImportPreview commit(@PathVariable UUID id) {
    return service.commit(id);
  }

  @GetMapping("/{id}/rows")
  List<PerformanceImportService.ImportRow> rows(@PathVariable UUID id) {
    return service.rows(id);
  }

  @PostMapping("/{id}/rows/{rowId}/match")
  PerformanceImportService.ImportPreview resolve(
      @PathVariable UUID id, @PathVariable UUID rowId, @Valid @RequestBody MatchRequest request) {
    return service.resolve(id, rowId, request.videoId(), request.variantId(), request.reason());
  }

  record MatchRequest(@NotNull UUID videoId, UUID variantId, String reason) {}
}
