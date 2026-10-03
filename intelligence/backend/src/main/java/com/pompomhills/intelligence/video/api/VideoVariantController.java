package com.pompomhills.intelligence.video.api;

import com.pompomhills.intelligence.video.VideoVariantService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/videos/{videoId}/variants")
public class VideoVariantController {
  private final VideoVariantService service;

  public VideoVariantController(VideoVariantService service) {
    this.service = service;
  }

  @PostMapping
  VideoVariantDtos.VariantResponse create(
      @PathVariable UUID videoId,
      @Valid @RequestBody VideoVariantDtos.CreateVariantRequest request) {
    var view =
        service.create(
            videoId,
            request.parentVariantId(),
            request.variantType(),
            request.generatedPath(),
            request.editOperations() == null ? List.of() : request.editOperations());
    return map(view);
  }

  @GetMapping
  List<VideoVariantDtos.VariantResponse> list(@PathVariable UUID videoId) {
    return service.list(videoId).stream().map(this::map).toList();
  }

  @GetMapping("/{variantId}")
  VideoVariantDtos.VariantResponse get(
      @PathVariable UUID videoId, @PathVariable UUID variantId) {
    return map(service.get(videoId, variantId));
  }

  private VideoVariantDtos.VariantResponse map(VideoVariantService.VideoVariantView view) {
    return new VideoVariantDtos.VariantResponse(
        view.id(),
        view.videoId(),
        view.parentVariantId(),
        view.variantType(),
        view.generatedPath(),
        view.editOperations(),
        view.createdAt());
  }
}
