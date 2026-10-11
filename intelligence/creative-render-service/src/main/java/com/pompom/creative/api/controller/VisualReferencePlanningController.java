package com.pompom.creative.api.controller;

import com.pompom.creative.visual.VisualReferencePlanningService;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.http.MediaType;

/** Render-stage visual reference planning; inspection is deliberately provider-call free. */
@RestController
@RequestMapping("/api/v1/visual-reference-plans")
public class VisualReferencePlanningController {
  private final VisualReferencePlanningService service;

  public VisualReferencePlanningController(VisualReferencePlanningService service) {
    this.service = service;
  }

  @PostMapping("/render-jobs/{renderJobId}/inspect")
  public ResponseEntity<Map<String, Object>> inspect(@PathVariable UUID renderJobId) {
    return ResponseEntity.ok(service.inspect(renderJobId));
  }

  @GetMapping("/render-jobs/{renderJobId}")
  public ResponseEntity<Map<String, Object>> inspectReadOnly(@PathVariable UUID renderJobId) {
    return ResponseEntity.ok(service.inspect(renderJobId));
  }

  @GetMapping("/prompts/{contentId}/{promptVersionId}")
  public ResponseEntity<Map<String, Object>> readPrompt(@PathVariable Long contentId, @PathVariable Long promptVersionId,
      @org.springframework.web.bind.annotation.RequestParam(defaultValue = "") String model) {
    return ResponseEntity.ok(service.readPrompt(contentId, promptVersionId, model));
  }

  @GetMapping("/{planId}/assets/{assetId}/media")
  public ResponseEntity<org.springframework.core.io.Resource> referenceMedia(@PathVariable UUID planId, @PathVariable UUID assetId) throws java.io.IOException {
    var path = service.referenceMedia(planId, assetId);
    String type = java.nio.file.Files.probeContentType(path);
    return ResponseEntity.ok().contentType(MediaType.parseMediaType(type == null ? "application/octet-stream" : type))
        .body(new org.springframework.core.io.FileSystemResource(path));
  }

  @PostMapping("/prompts/{contentId}/{promptVersionId}/inspect")
  public ResponseEntity<Map<String, Object>> inspectPrompt(
      @PathVariable Long contentId,
      @PathVariable Long promptVersionId,
      @RequestBody(required = false) Map<String, Object> request) {
    String model = request == null ? "" : String.valueOf(request.getOrDefault("model", ""));
    return ResponseEntity.ok(service.inspectPrompt(contentId, promptVersionId, model));
  }

  @PostMapping("/{planId}/first-frame/accept")
  public ResponseEntity<Map<String, Object>> acceptFirstFrame(
      @PathVariable UUID planId, @RequestBody AcceptFirstFrameRequest request) {
    return ResponseEntity.ok(service.acceptFirstFrame(planId, request.renderAssetId(), request.contract()));
  }

  @PostMapping("/{planId}/first-frame/proposal")
  public ResponseEntity<Map<String, Object>> firstFrameProposal(@PathVariable UUID planId) {
    return ResponseEntity.ok(service.prepareFirstFrameProposal(planId));
  }

  @PostMapping("/{planId}/critical-scene/proposal")
  public ResponseEntity<Map<String, Object>> criticalSceneProposal(@PathVariable UUID planId) {
    return ResponseEntity.ok(service.prepareCriticalSceneProposal(planId));
  }

  @PostMapping("/{planId}/validate")
  public ResponseEntity<Map<String, Object>> validate(@PathVariable UUID planId) {
    return ResponseEntity.ok(service.validate(planId));
  }

  @PostMapping(value = "/{planId}/first-frame/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
  public ResponseEntity<Map<String, Object>> uploadFirstFrame(
      @PathVariable UUID planId, @RequestPart("file") org.springframework.web.multipart.MultipartFile file) {
    return ResponseEntity.status(201).body(service.uploadFirstFrame(planId, file));
  }

  @PostMapping("/{planId}/first-frame/imported/{referenceAssetId}/accept")
  public ResponseEntity<Map<String, Object>> acceptImportedFirstFrame(
      @PathVariable UUID planId, @PathVariable UUID referenceAssetId, @RequestBody Map<String, Object> contract) {
    return ResponseEntity.ok(service.acceptImportedFirstFrame(planId, referenceAssetId, contract));
  }

  public record AcceptFirstFrameRequest(UUID renderAssetId, String aspectRatio, String model, String characterReferenceAssetId, String mode) {
    Map<String, Object> contract() {
      Map<String, Object> result = new java.util.LinkedHashMap<>();
      result.put("aspectRatio", aspectRatio == null ? "" : aspectRatio); result.put("model", model == null ? "" : model);
      result.put("characterReferenceAssetId", characterReferenceAssetId == null ? "" : characterReferenceAssetId);
      result.put("mode", mode == null ? "" : mode); return result;
    }
  }

  @org.springframework.web.bind.annotation.ExceptionHandler({IllegalArgumentException.class, IllegalStateException.class})
  public ResponseEntity<Map<String, Object>> invalid(RuntimeException error) {
    return ResponseEntity.status(409).body(Map.of("status", "REJECTED", "detail", error.getMessage() == null ? "Visual reference request was rejected" : error.getMessage()));
  }
}
