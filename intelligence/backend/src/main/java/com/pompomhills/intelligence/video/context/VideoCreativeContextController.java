package com.pompomhills.intelligence.video.context;

import com.pompomhills.intelligence.video.context.VideoCreativeContextDtos.Response;
import java.util.UUID;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/videos/{videoId}/creative-context")
public class VideoCreativeContextController {
  private final VideoCreativeContextService service;

  public VideoCreativeContextController(VideoCreativeContextService service) {
    this.service = service;
  }

  public record LinkRequest(long promptVersionId, String origin, String reason) {}

  @PostMapping("/prompt-link")
  public Response link(@PathVariable UUID videoId, @RequestBody LinkRequest request) {
    return service.link(videoId, request.promptVersionId(), request.origin(), request.reason());
  }

  @GetMapping
  public Response get(@PathVariable UUID videoId) {
    return service.get(videoId);
  }
}
