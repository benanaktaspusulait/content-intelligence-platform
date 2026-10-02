package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.util.List;

/**
 * Read-only recent content published by the connected Facebook Page. Demonstrates
 * pages_read_engagement usage. No reactions, comments, or commenter data are read, and nothing is
 * persisted.
 */
public record MetaPageContentResponse(
    Availability availability,
    String unavailableReason,
    PageSummary page,
    List<PagePost> posts,
    String apiVersion) {

  public enum Availability {
    AVAILABLE,
    PARTIAL,
    UNAVAILABLE
  }

  public record PageSummary(String id, String name, String category) {}

  public record PagePost(String id, String message, Instant publishedAt, String permalinkUrl) {}
}
