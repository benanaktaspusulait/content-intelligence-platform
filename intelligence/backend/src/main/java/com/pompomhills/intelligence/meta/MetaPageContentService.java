package com.pompomhills.intelligence.meta;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;

/**
 * Read-only reader for recent Facebook Page content. GET only. Results are not persisted and are
 * not connected to the analytics snapshot system.
 */
@Service
public class MetaPageContentService {
  private static final int DEFAULT_LIMIT = 5;

  private final MetaReadProperties properties;
  private final MetaGraphReadClient client;

  public MetaPageContentService(MetaReadProperties properties, MetaGraphReadClient client) {
    this.properties = properties;
    this.client = client;
  }

  public MetaPageContentResponse getRecentContent() {
    if (!properties.isConfigured()) {
      throw new MetaNotConfiguredException();
    }

    MetaPageContentResponse.PageSummary pageSummary = null;
    try {
      MetaGraphReadClient.FacebookPage page = client.getFacebookPage();
      if (page != null && page.id() != null) {
        pageSummary =
            new MetaPageContentResponse.PageSummary(page.id(), page.name(), page.category());
      }
    } catch (MetaGraphException | RestClientException ignored) {
      // Page summary is best-effort context; absence is handled below.
    }

    try {
      MetaGraphReadClient.PagePostsResponse response = client.getPagePosts(DEFAULT_LIMIT);
      List<MetaPageContentResponse.PagePost> posts = new ArrayList<>();
      if (response != null && response.data() != null) {
        for (MetaGraphReadClient.PagePost post : response.data()) {
          if (post == null || post.id() == null) {
            continue;
          }
          posts.add(
              new MetaPageContentResponse.PagePost(
                  post.id(),
                  post.message(),
                  parseTimestamp(post.createdTime()),
                  post.permalinkUrl()));
        }
      }
      MetaPageContentResponse.Availability availability =
          pageSummary == null
              ? MetaPageContentResponse.Availability.PARTIAL
              : MetaPageContentResponse.Availability.AVAILABLE;
      String reason =
          pageSummary == null ? "Facebook Page details were unavailable for this request." : null;
      return new MetaPageContentResponse(
          availability, reason, pageSummary, posts, properties.apiVersion());
    } catch (MetaGraphException error) {
      String reason =
          error.isPermissionDenied()
              ? "The pages_read_engagement permission has not been granted yet."
              : error.isAuthenticationUnavailable()
                  ? "Meta authentication is unavailable for Facebook Page content."
                  : "Facebook Page content is temporarily unavailable.";
      return new MetaPageContentResponse(
          MetaPageContentResponse.Availability.UNAVAILABLE,
          reason,
          pageSummary,
          List.of(),
          properties.apiVersion());
    } catch (RestClientException transportError) {
      return new MetaPageContentResponse(
          MetaPageContentResponse.Availability.UNAVAILABLE,
          "Facebook Page content could not be retrieved from Meta.",
          pageSummary,
          List.of(),
          properties.apiVersion());
    }
  }

  private Instant parseTimestamp(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    try {
      return OffsetDateTime.parse(value).toInstant();
    } catch (DateTimeParseException iso) {
      // Graph returns RFC-822 style offsets without a colon, e.g. 2026-10-01T18:55:59+0000.
      try {
        return OffsetDateTime.parse(value, GRAPH_TIMESTAMP).toInstant();
      } catch (DateTimeParseException rfc822) {
        try {
          return Instant.parse(value);
        } catch (DateTimeParseException ignored) {
          return null;
        }
      }
    }
  }

  private static final java.time.format.DateTimeFormatter GRAPH_TIMESTAMP =
      java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssZ");
}
