package com.pompomhills.intelligence.video.context;

import com.pompomhills.intelligence.video.context.VideoCreativeContextDtos.Response;
import java.util.UUID;
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

  @GetMapping
  public Response get(@PathVariable UUID videoId) {
    return service.get(videoId);
  }
}
