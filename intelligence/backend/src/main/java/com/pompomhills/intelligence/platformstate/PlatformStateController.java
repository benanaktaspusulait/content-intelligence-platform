package com.pompomhills.intelligence.platformstate;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/videos/{videoId}")
public class PlatformStateController {
  private final PlatformStateService service;

  public PlatformStateController(PlatformStateService service) {
    this.service = service;
  }

  @PostMapping("/platform-states")
  PlatformStateService.ObservationView observe(
      @PathVariable UUID videoId,
      @Valid @RequestBody AddObservation request,
      @RequestHeader(value = "X-Actor", defaultValue = "local-user") String actor) {
    return service.observe(
        videoId,
        new PlatformStateService.ObservationRequest(
            request.variantId(),
            request.platform(),
            request.stateType(),
            request.stateValue(),
            request.observedAt(),
            request.source(),
            request.sourceImportId(),
            request.confidence(),
            request.notes(),
            request.evidenceRelativePath(),
            request.ocrResult(),
            request.manuallyVerified(),
            request.correctionOfObservationId()),
        actor);
  }

  @PostMapping(
      path = "/platform-states/reach-further/screenshot",
      consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
  PlatformStateService.ObservationView screenshot(
      @PathVariable UUID videoId,
      @RequestPart("file") MultipartFile file,
      @RequestParam(defaultValue = "facebook") String platform,
      @RequestParam(defaultValue = "ACTIVE") String stateValue,
      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant observedAt,
      @RequestParam(required = false) String notes,
      @RequestParam(required = false) String ocrResult,
      @RequestParam(defaultValue = "false") boolean manuallyVerified,
      @RequestHeader(value = "X-Actor", defaultValue = "local-user") String actor)
      throws IOException {
    if (file.isEmpty()) throw new IllegalArgumentException("Screenshot evidence is empty");
    try (var input = file.getInputStream()) {
      return service.observeScreenshot(
          videoId,
          platform,
          stateValue,
          observedAt,
          notes,
          ocrResult,
          manuallyVerified,
          file.getOriginalFilename(),
          file.getContentType(),
          input,
          actor);
    }
  }

  @GetMapping("/platform-states")
  List<PlatformStateService.ObservationView> observations(
      @PathVariable UUID videoId, @RequestParam(required = false) String platform) {
    return service.observations(videoId, platform);
  }

  @GetMapping("/platform-states/reach-further")
  PlatformStateService.ReachFurtherSummary reachFurther(
      @PathVariable UUID videoId, @RequestParam(defaultValue = "facebook") String platform) {
    return service.reachFurtherSummary(videoId, platform);
  }

  @GetMapping("/platform-states/live-features")
  PlatformStateService.LiveFeatures liveFeatures(
      @PathVariable UUID videoId,
      @RequestParam(defaultValue = "facebook") String platform,
      @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant cutoff,
      @RequestParam(defaultValue = "LIVE") String predictionType) {
    return service.liveFeatures(videoId, platform, cutoff, predictionType);
  }

  @PostMapping("/publication-context")
  PlatformStateService.PublicationView publication(
      @PathVariable UUID videoId,
      @Valid @RequestBody PublicationContext request,
      @RequestHeader(value = "X-Actor", defaultValue = "local-user") String actor) {
    return service.recordPublication(
        videoId,
        new PlatformStateService.PublicationRequest(
            request.variantId(),
            request.platform(),
            request.platformContentId(),
            request.platformUrl(),
            request.publishedAt(),
            request.publicationTimezone(),
            request.offPeakPublish(),
            request.source(),
            request.notes()),
        actor);
  }

  public record AddObservation(
      UUID variantId,
      @NotBlank String platform,
      @NotBlank String stateType,
      @NotBlank String stateValue,
      Instant observedAt,
      @NotBlank String source,
      UUID sourceImportId,
      double confidence,
      String notes,
      String evidenceRelativePath,
      String ocrResult,
      boolean manuallyVerified,
      UUID correctionOfObservationId) {}

  public record PublicationContext(
      UUID variantId,
      @NotBlank String platform,
      String platformContentId,
      String platformUrl,
      @NotNull Instant publishedAt,
      @NotBlank String publicationTimezone,
      Boolean offPeakPublish,
      @NotBlank String source,
      String notes) {}
}
