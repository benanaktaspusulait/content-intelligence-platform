package com.pompomhills.intelligence.meta;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.Types;
import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;

/**
 * Read-only Instagram Reels discovery and append-only analytics snapshots.
 *
 * <p>All Graph access is GET only. Insight metrics that the platform does not report are preserved
 * as null and the availability status is recorded explicitly; they are never coerced to zero.
 */
@Service
public class MetaReelsService {
  private static final String PLATFORM = "instagram";
  private static final String SOURCE = "META_GRAPH_API";
  private static final int DEFAULT_LIMIT = 25;

  private final MetaReadProperties properties;
  private final MetaGraphReadClient client;
  private final MetaMediaMatcher matcher;
  private final JdbcClient jdbc;
  private final ObjectMapper objectMapper;
  private final Clock clock;

  public MetaReelsService(
      MetaReadProperties properties,
      MetaGraphReadClient client,
      MetaMediaMatcher matcher,
      JdbcClient jdbc,
      ObjectMapper objectMapper,
      Clock clock) {
    this.properties = properties;
    this.client = client;
    this.matcher = matcher;
    this.jdbc = jdbc;
    this.objectMapper = objectMapper;
    this.clock = clock;
  }

  public boolean isConfigured() {
    return properties.isConfigured();
  }

  @Transactional(readOnly = true)
  public MetaReelsResponse listReels(String after, Integer limit) {
    requireConfigured();
    int boundedLimit = limit == null ? DEFAULT_LIMIT : limit;
    MetaGraphReadClient.InstagramMediaPage page = client.listInstagramMedia(after, boundedLimit);
    List<MetaReelsResponse.ReelSummary> reels = new ArrayList<>();
    if (page != null && page.data() != null) {
      for (MetaGraphReadClient.InstagramMedia media : page.data()) {
        if (media == null || media.id() == null) {
          continue;
        }
        MetaMediaMatcher.MatchResult match = matcher.match(media.id(), media.permalink());
        reels.add(
            new MetaReelsResponse.ReelSummary(
                media.id(),
                media.mediaType(),
                media.mediaProductType(),
                media.caption(),
                media.permalink(),
                parseTimestamp(media.timestamp()),
                media.thumbnailUrl(),
                MetaReelsResponse.LocalMatch.from(match)));
      }
    }
    String nextCursor = page == null ? null : page.afterCursor();
    boolean hasMore = nextCursor != null && !nextCursor.isBlank();
    return new MetaReelsResponse(reels, nextCursor, hasMore, properties.apiVersion());
  }

  @Transactional(readOnly = true)
  public MetaReelsResponse.ReelSummary getReel(String mediaId) {
    requireConfigured();
    MetaGraphReadClient.InstagramMedia media = client.getInstagramMedia(mediaId);
    MetaMediaMatcher.MatchResult match = matcher.match(media.id(), media.permalink());
    return new MetaReelsResponse.ReelSummary(
        media.id(),
        media.mediaType(),
        media.mediaProductType(),
        media.caption(),
        media.permalink(),
        parseTimestamp(media.timestamp()),
        media.thumbnailUrl(),
        MetaReelsResponse.LocalMatch.from(match));
  }

  @Transactional(readOnly = true)
  public MetaReelAnalyticsResponse getAnalytics(String mediaId) {
    requireConfigured();
    MetaGraphReadClient.InstagramMedia media = client.getInstagramMedia(mediaId);
    MetaMediaMatcher.MatchResult match = matcher.match(media.id(), media.permalink());
    InsightsOutcome outcome = readInsights(media.id());
    List<MetaReelAnalyticsResponse.Snapshot> history = loadHistory(media.id());
    return new MetaReelAnalyticsResponse(
        media.id(),
        media.mediaType(),
        media.mediaProductType(),
        media.caption(),
        media.permalink(),
        parseTimestamp(media.timestamp()),
        media.thumbnailUrl(),
        MetaReelsResponse.LocalMatch.from(match),
        outcome.availability(),
        outcome.reason(),
        outcome.metrics(),
        history,
        properties.apiVersion());
  }

  @Transactional
  public MetaSnapshotResponse captureSnapshot(String mediaId) {
    requireConfigured();
    MetaGraphReadClient.InstagramMedia media = client.getInstagramMedia(mediaId);
    MetaMediaMatcher.MatchResult match = matcher.match(media.id(), media.permalink());
    InsightsOutcome outcome = readInsights(media.id());
    Instant measuredAt = clock.instant();
    UUID collectionRunId = UUID.randomUUID();
    UUID videoId = match.status() == MetaMediaMatcher.MatchStatus.EXACT ? match.videoId() : null;

    UUID observationId = insertObservation(media, outcome, measuredAt, collectionRunId, videoId);

    if (match.status() == MetaMediaMatcher.MatchStatus.EXACT && match.publicationId() != null) {
      recordIdentityMatch(match.publicationId(), match.matchMethod(), measuredAt);
    }

    return new MetaSnapshotResponse(
        media.id(),
        observationId,
        collectionRunId,
        measuredAt,
        observationId != null,
        MetaReelsResponse.LocalMatch.from(match),
        outcome.availability(),
        outcome.reason(),
        outcome.metrics());
  }

  private UUID insertObservation(
      MetaGraphReadClient.InstagramMedia media,
      InsightsOutcome outcome,
      Instant measuredAt,
      UUID collectionRunId,
      UUID videoId) {
    MetaReelAnalyticsResponse.Metrics metrics = outcome.metrics();
    String sourceObservationKey = collectionRunId + ":" + media.id();
    String dataQuality =
        switch (outcome.availability()) {
          case AVAILABLE, PARTIAL -> "API_REPORTED";
          case UNAVAILABLE, NOT_REQUESTED -> "UNAVAILABLE";
        };
    return jdbc.sql(
            """
            INSERT INTO performance_observations
              (video_id, platform, platform_content_id, publication_timestamp,
               measurement_timestamp, metric_semantics, views, reach, shares, saves,
               total_interactions, paid, source, source_version, source_observation_key,
               raw_payload_json, data_quality_status, metric_availability_status,
               insights_unavailable_reason, source_error_code, source_error_subcode,
               source_error_type, collection_run_id)
            VALUES
              (:videoId, :platform, :contentId, :published, :measured, 'SNAPSHOT', :views, :reach,
               :shares, :saved, :totalInteractions, false, :source, :sourceVersion, :sourceKey,
               CAST(:rawPayload AS jsonb), :dataQuality, :availability, :reason, :errorCode,
               :errorSubcode, :errorType, :collectionRunId)
            ON CONFLICT (platform, source, source_observation_key)
              WHERE source_observation_key IS NOT NULL DO NOTHING
            RETURNING id
            """)
        .param("videoId", videoId, Types.OTHER)
        .param("platform", PLATFORM)
        .param("contentId", media.id())
        .param("published", utc(parseTimestamp(media.timestamp())), Types.TIMESTAMP_WITH_TIMEZONE)
        .param("measured", utc(measuredAt), Types.TIMESTAMP_WITH_TIMEZONE)
        .param("views", metrics.views(), Types.BIGINT)
        .param("reach", metrics.reach(), Types.BIGINT)
        .param("shares", metrics.shares(), Types.BIGINT)
        .param("saved", metrics.saved(), Types.BIGINT)
        .param("totalInteractions", metrics.totalInteractions(), Types.BIGINT)
        .param("source", SOURCE)
        .param("sourceVersion", "graph-" + properties.apiVersion())
        .param("sourceKey", sourceObservationKey)
        .param("rawPayload", outcome.rawPayloadJson())
        .param("dataQuality", dataQuality)
        .param("availability", outcome.availability().name())
        .param("reason", outcome.reason(), Types.VARCHAR)
        .param("errorCode", outcome.errorCode(), Types.INTEGER)
        .param("errorSubcode", outcome.errorSubcode(), Types.INTEGER)
        .param("errorType", outcome.errorType(), Types.VARCHAR)
        .param("collectionRunId", collectionRunId, Types.OTHER)
        .query(UUID.class)
        .optional()
        .orElse(null);
  }

  private void recordIdentityMatch(
      UUID publicationId, MetaMediaMatcher.MatchMethod method, Instant at) {
    jdbc.sql(
            """
            UPDATE video_publications
            SET identity_match_method = :method, identity_matched_at = :at
            WHERE id = :id
            """)
        .param("method", method.name())
        .param("at", utc(at), Types.TIMESTAMP_WITH_TIMEZONE)
        .param("id", publicationId)
        .update();
  }

  private List<MetaReelAnalyticsResponse.Snapshot> loadHistory(String mediaId) {
    return jdbc.sql(
            """
            SELECT id, collection_run_id, measurement_timestamp, metric_availability_status,
                   insights_unavailable_reason, views, reach, shares, saves, total_interactions
            FROM performance_observations
            WHERE platform = :platform AND platform_content_id = :mediaId AND source = :source
            ORDER BY measurement_timestamp DESC, created_at DESC
            """)
        .param("platform", PLATFORM)
        .param("mediaId", mediaId)
        .param("source", SOURCE)
        .query(
            (rs, ignored) ->
                new MetaReelAnalyticsResponse.Snapshot(
                    rs.getObject("id", UUID.class),
                    rs.getObject("collection_run_id", UUID.class),
                    toInstant(rs.getObject("measurement_timestamp", OffsetDateTime.class)),
                    parseAvailability(rs.getString("metric_availability_status")),
                    rs.getString("insights_unavailable_reason"),
                    new MetaReelAnalyticsResponse.Metrics(
                        nullableLong(rs.getObject("views")),
                        nullableLong(rs.getObject("reach")),
                        nullableLong(rs.getObject("shares")),
                        nullableLong(rs.getObject("saves")),
                        nullableLong(rs.getObject("total_interactions")))))
        .list();
  }

  private InsightsOutcome readInsights(String mediaId) {
    try {
      MetaGraphReadClient.InstagramInsightsResponse response =
          client.getInstagramMediaInsights(mediaId);
      Map<String, Long> values = new LinkedHashMap<>();
      if (response != null && response.data() != null) {
        for (MetaGraphReadClient.InsightMetric metric : response.data()) {
          if (metric != null && metric.name() != null) {
            values.put(metric.name(), metric.resolveValue());
          }
        }
      }
      if (values.isEmpty()) {
        return InsightsOutcome.partial(
            emptyMetrics(),
            "Insight metrics are not available for this media yet.",
            rawPayload(Map.of("insightsReturned", 0)));
      }
      MetaReelAnalyticsResponse.Metrics metrics =
          new MetaReelAnalyticsResponse.Metrics(
              values.get("views"),
              values.get("reach"),
              values.get("shares"),
              values.get("saved"),
              values.get("total_interactions"));
      boolean complete =
          metrics.views() != null
              && metrics.reach() != null
              && metrics.shares() != null
              && metrics.saved() != null
              && metrics.totalInteractions() != null;
      String payload = rawPayload(Map.of("metrics", values));
      return complete
          ? InsightsOutcome.available(metrics, payload)
          : InsightsOutcome.partial(metrics, "Some insight metrics were not reported.", payload);
    } catch (MetaGraphException error) {
      if (error.isPermissionDenied()) {
        return InsightsOutcome.permissionDenied(error);
      }
      if (error.isAuthenticationUnavailable()) {
        return InsightsOutcome.unavailable(
            "Meta authentication is unavailable for insight metrics.", error);
      }
      return InsightsOutcome.unavailable("Insight metrics are temporarily unavailable.", error);
    } catch (RestClientException transportError) {
      return InsightsOutcome.unavailable("Insight metrics could not be retrieved from Meta.", null);
    }
  }

  private String rawPayload(Map<String, ?> payload) {
    try {
      return objectMapper.writeValueAsString(payload);
    } catch (JsonProcessingException ignored) {
      return "{}";
    }
  }

  private static MetaReelAnalyticsResponse.Metrics emptyMetrics() {
    return new MetaReelAnalyticsResponse.Metrics(null, null, null, null, null);
  }

  private void requireConfigured() {
    if (!properties.isConfigured()) {
      throw new MetaNotConfiguredException();
    }
  }

  private static final java.time.format.DateTimeFormatter GRAPH_TIMESTAMP =
      java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssZ");

  private Instant parseTimestamp(String value) {
    if (value == null || value.isBlank()) {
      return null;
    }
    try {
      return OffsetDateTime.parse(value).toInstant();
    } catch (DateTimeParseException iso) {
      // Graph returns RFC-822 style offsets without a colon, e.g. 2026-10-01T07:49:35+0000.
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

  private OffsetDateTime utc(Instant value) {
    return value == null ? null : OffsetDateTime.ofInstant(value, ZoneOffset.UTC);
  }

  private Instant toInstant(OffsetDateTime value) {
    return value == null ? null : value.toInstant();
  }

  private Long nullableLong(Object value) {
    return value == null ? null : ((Number) value).longValue();
  }

  private MetaReelAnalyticsResponse.MetricAvailability parseAvailability(String value) {
    if (value == null) {
      return MetaReelAnalyticsResponse.MetricAvailability.NOT_REQUESTED;
    }
    try {
      return MetaReelAnalyticsResponse.MetricAvailability.valueOf(value);
    } catch (IllegalArgumentException ignored) {
      return MetaReelAnalyticsResponse.MetricAvailability.NOT_REQUESTED;
    }
  }

  /**
   * Immutable outcome of a single insights read, carrying availability, metrics, and error facts.
   */
  private record InsightsOutcome(
      MetaReelAnalyticsResponse.MetricAvailability availability,
      MetaReelAnalyticsResponse.Metrics metrics,
      String reason,
      Integer errorCode,
      Integer errorSubcode,
      String errorType,
      String rawPayloadJson) {

    static InsightsOutcome available(MetaReelAnalyticsResponse.Metrics metrics, String payload) {
      return new InsightsOutcome(
          MetaReelAnalyticsResponse.MetricAvailability.AVAILABLE,
          metrics,
          null,
          null,
          null,
          null,
          payload);
    }

    static InsightsOutcome partial(
        MetaReelAnalyticsResponse.Metrics metrics, String reason, String payload) {
      return new InsightsOutcome(
          MetaReelAnalyticsResponse.MetricAvailability.PARTIAL,
          metrics,
          reason,
          null,
          null,
          null,
          payload);
    }

    static InsightsOutcome permissionDenied(MetaGraphException error) {
      return new InsightsOutcome(
          MetaReelAnalyticsResponse.MetricAvailability.PARTIAL,
          emptyMetrics(),
          "The instagram_manage_insights permission has not been granted yet.",
          error.graphCode(),
          error.errorSubcode(),
          error.errorType(),
          "{}");
    }

    static InsightsOutcome unavailable(String reason, MetaGraphException error) {
      return new InsightsOutcome(
          MetaReelAnalyticsResponse.MetricAvailability.UNAVAILABLE,
          emptyMetrics(),
          reason,
          error == null ? null : error.graphCode(),
          error == null ? null : error.errorSubcode(),
          error == null ? null : error.errorType(),
          "{}");
    }
  }
}
