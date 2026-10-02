package com.pompomhills.intelligence.meta;

import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Deterministically links an Instagram media object to a locally registered video publication.
 *
 * <p>Matching is strict: it uses the exact external platform content id first, then a canonicalized
 * permalink. Fuzzy matching on caption, filename, or title is intentionally forbidden to avoid
 * attributing analytics to the wrong local video.
 */
@Component
public class MetaMediaMatcher {
  private static final String PLATFORM = "instagram";

  private final JdbcClient jdbc;

  public MetaMediaMatcher(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Transactional(readOnly = true)
  public MatchResult match(String mediaId, String permalink) {
    String contentId = mediaId == null ? "" : mediaId.trim();
    List<PublicationRow> byContentId =
        contentId.isBlank()
            ? List.of()
            : jdbc.sql(
                    """
                    SELECT id, video_id FROM video_publications
                    WHERE platform = :platform AND platform_content_id = :contentId
                    """)
                .param("platform", PLATFORM)
                .param("contentId", contentId)
                .query(
                    (rs, ignored) ->
                        new PublicationRow(
                            rs.getObject("id", UUID.class), rs.getObject("video_id", UUID.class)))
                .list();

    String canonicalPermalink = canonicalize(permalink);
    List<PublicationRow> byPermalink =
        canonicalPermalink == null
            ? List.of()
            : jdbc
                .sql(
                    """
                    SELECT id, video_id, platform_url FROM video_publications
                    WHERE platform = :platform AND platform_url IS NOT NULL
                    """)
                .param("platform", PLATFORM)
                .query(
                    (rs, ignored) ->
                        new PermalinkRow(
                            rs.getObject("id", UUID.class),
                            rs.getObject("video_id", UUID.class),
                            rs.getString("platform_url")))
                .list()
                .stream()
                .filter(row -> canonicalPermalink.equals(canonicalize(row.platformUrl())))
                .map(row -> new PublicationRow(row.id(), row.videoId()))
                .distinct()
                .toList();

    PublicationRow contentMatch = singleDistinctVideo(byContentId);
    PublicationRow permalinkMatch = singleDistinctVideo(byPermalink);

    if (byContentId.size() > 1 && contentMatch == null) {
      return MatchResult.ambiguous("Multiple publications share this external content id.");
    }
    if (byPermalink.size() > 1 && permalinkMatch == null) {
      return MatchResult.ambiguous("Multiple publications share this permalink.");
    }

    if (contentMatch != null && permalinkMatch != null) {
      if (!contentMatch.videoId().equals(permalinkMatch.videoId())) {
        return MatchResult.conflict("Content id and permalink resolve to different local videos.");
      }
      return MatchResult.exact(
          contentMatch.videoId(), contentMatch.id(), MatchMethod.PLATFORM_CONTENT_ID);
    }
    if (contentMatch != null) {
      return MatchResult.exact(
          contentMatch.videoId(), contentMatch.id(), MatchMethod.PLATFORM_CONTENT_ID);
    }
    if (permalinkMatch != null) {
      return MatchResult.exact(
          permalinkMatch.videoId(), permalinkMatch.id(), MatchMethod.PERMALINK);
    }
    return MatchResult.unmatched("No local publication matches this media.");
  }

  private PublicationRow singleDistinctVideo(List<PublicationRow> rows) {
    if (rows.isEmpty()) {
      return null;
    }
    UUID first = rows.get(0).videoId();
    boolean allSame = rows.stream().allMatch(row -> row.videoId().equals(first));
    return allSame ? rows.get(0) : null;
  }

  /**
   * Canonicalizes an Instagram permalink for exact comparison: lowercases scheme/host, drops any
   * query string or fragment, and normalizes a single trailing slash. Returns {@code null} when the
   * input is blank or not an absolute http(s) URL.
   */
  static String canonicalize(String url) {
    if (url == null) {
      return null;
    }
    String trimmed = url.trim();
    if (trimmed.isBlank()) {
      return null;
    }
    java.net.URI uri;
    try {
      uri = java.net.URI.create(trimmed);
    } catch (IllegalArgumentException invalid) {
      return null;
    }
    String scheme = uri.getScheme();
    String host = uri.getHost();
    if (scheme == null || host == null) {
      return null;
    }
    String normalizedScheme = scheme.toLowerCase(Locale.ROOT);
    if (!normalizedScheme.equals("http") && !normalizedScheme.equals("https")) {
      return null;
    }
    String normalizedHost = host.toLowerCase(Locale.ROOT);
    if (normalizedHost.startsWith("www.")) {
      normalizedHost = normalizedHost.substring(4);
    }
    String path = uri.getPath() == null ? "" : uri.getPath();
    while (path.endsWith("/")) {
      path = path.substring(0, path.length() - 1);
    }
    return "https://" + normalizedHost + path;
  }

  public enum MatchMethod {
    PLATFORM_CONTENT_ID,
    PERMALINK,
    MANUAL
  }

  public enum MatchStatus {
    EXACT,
    UNMATCHED,
    AMBIGUOUS,
    CONFLICT
  }

  public record MatchResult(
      MatchStatus status,
      UUID videoId,
      UUID publicationId,
      MatchMethod matchMethod,
      String detail) {
    static MatchResult exact(UUID videoId, UUID publicationId, MatchMethod method) {
      return new MatchResult(MatchStatus.EXACT, videoId, publicationId, method, null);
    }

    static MatchResult unmatched(String detail) {
      return new MatchResult(MatchStatus.UNMATCHED, null, null, null, detail);
    }

    static MatchResult ambiguous(String detail) {
      return new MatchResult(MatchStatus.AMBIGUOUS, null, null, null, detail);
    }

    static MatchResult conflict(String detail) {
      return new MatchResult(MatchStatus.CONFLICT, null, null, null, detail);
    }
  }

  private record PublicationRow(UUID id, UUID videoId) {}

  private record PermalinkRow(UUID id, UUID videoId, String platformUrl) {}
}
