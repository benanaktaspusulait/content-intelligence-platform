package com.pompomhills.intelligence.video.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.pompomhills.intelligence.video.VideoVariantService;
import com.pompomhills.intelligence.video.VideoVariantType;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class VideoVariantControllerTest {

  private VideoVariantService service;
  private VideoVariantController controller;

  @BeforeEach
  void setUp() {
    service = mock(VideoVariantService.class);
    controller = new VideoVariantController(service);
  }

  @Test
  void createDelegatesToTheServiceAndMapsTheResponse() {
    UUID videoId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    var view =
        new VideoVariantService.VideoVariantView(
            variantId, videoId, null, "ORIGINAL", "library/a.mp4", List.of(), Instant.now());
    when(service.create(videoId, null, VideoVariantType.ORIGINAL, "library/a.mp4", List.of()))
        .thenReturn(view);

    var request =
        new VideoVariantDtos.CreateVariantRequest(
            null, VideoVariantType.ORIGINAL, "library/a.mp4", List.of());
    var response = controller.create(videoId, request);

    assertThat(response.id()).isEqualTo(variantId);
    assertThat(response.variantType()).isEqualTo("ORIGINAL");
  }

  @Test
  void listDelegatesToTheServiceAndMapsEveryResult() {
    UUID videoId = UUID.randomUUID();
    var view =
        new VideoVariantService.VideoVariantView(
            UUID.randomUUID(),
            videoId,
            null,
            "TRIMMED",
            "library/b.mp4",
            List.of(),
            Instant.now());
    when(service.list(videoId)).thenReturn(List.of(view));

    var response = controller.list(videoId);

    assertThat(response).hasSize(1);
    assertThat(response.get(0).variantType()).isEqualTo("TRIMMED");
  }

  @Test
  void getPropagatesTheServicesNotFoundException() {
    UUID videoId = UUID.randomUUID();
    UUID variantId = UUID.randomUUID();
    when(service.get(videoId, variantId))
        .thenThrow(new jakarta.persistence.EntityNotFoundException("not found"));

    assertThatThrownBy(() -> controller.get(videoId, variantId))
        .isInstanceOf(jakarta.persistence.EntityNotFoundException.class);
  }
}
