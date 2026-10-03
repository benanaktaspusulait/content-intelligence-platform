package com.pompomhills.intelligence.video.api;

import com.pompomhills.intelligence.video.VideoVariantType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class VideoVariantDtos {
  private VideoVariantDtos() {}

  public record CreateVariantRequest(
      UUID parentVariantId,
      @NotNull VideoVariantType variantType,
      @NotBlank String generatedPath,
      List<Object> editOperations) {}

  public record VariantResponse(
      UUID id,
      UUID videoId,
      UUID parentVariantId,
      String variantType,
      String generatedPath,
      List<Object> editOperations,
      Instant createdAt) {}
}
