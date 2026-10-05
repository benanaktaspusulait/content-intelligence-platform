package com.pompomhills.intelligence.video.context;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public final class VideoCreativeContextDtos {
  private VideoCreativeContextDtos() {}

  public record Response(
      UUID videoId,
      List<CharacterContext> characters,
      PromptContext prompt,
      String evidenceStatus) {}

  public record CharacterContext(
      UUID id,
      String name,
      String participation,
      String role,
      Double screenTimeRatio,
      Double actionShare,
      Double speakingShare,
      String source,
      String confidence,
      String promptSourcePath,
      String resolverVersion,
      String evidenceReference,
      boolean manuallyConfirmed) {}

  public record PromptContext(
      Long contentId,
      String title,
      String type,
      String status,
      Long promptVersionId,
      Integer versionNumber,
      String rawText,
      String parsedIr,
      String sourcePath,
      Instant createdAt,
      String linkage) {}
}
