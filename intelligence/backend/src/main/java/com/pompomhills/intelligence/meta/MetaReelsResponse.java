package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** A single page of read-only Instagram media with deterministic local match status. */
public record MetaReelsResponse(
    List<ReelSummary> reels, String nextCursor, boolean hasMore, String apiVersion) {

  public record ReelSummary(
      String mediaId,
      String mediaType,
      String mediaProductType,
      String caption,
      String permalink,
      Instant publishedAt,
      String thumbnailUrl,
      LocalMatch localMatch) {}

  public record LocalMatch(
      MetaMediaMatcher.MatchStatus status,
      UUID videoId,
      UUID publicationId,
      MetaMediaMatcher.MatchMethod matchMethod,
      String detail) {

    public static LocalMatch from(MetaMediaMatcher.MatchResult result) {
      return new LocalMatch(
          result.status(),
          result.videoId(),
          result.publicationId(),
          result.matchMethod(),
          result.detail());
    }
  }
}
