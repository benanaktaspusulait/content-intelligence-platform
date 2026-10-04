package com.pompomhills.intelligence.platformstate;

import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.performance.DiscoveryProfileService;
import com.pompomhills.intelligence.performance.InterventionService;
import com.pompomhills.intelligence.performance.PlatformGrowthProfileService;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.sql.Types;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class PlatformStateService {
  public static final String REACH_FURTHER = "META_REACH_FURTHER";
  private static final Set<String> VALUES = Set.of("ACTIVE", "INACTIVE", "UNKNOWN");
  private static final Set<String> SOURCES =
      Set.of("SCREENSHOT", "MANUAL", "CSV", "API", "UI_OBSERVATION");
  private static final Map<String, Duration> WINDOWS =
      Map.of(
          "1h", Duration.ofHours(1),
          "3h", Duration.ofHours(3),
          "6h", Duration.ofHours(6),
          "12h", Duration.ofHours(12),
          "24h", Duration.ofHours(24),
          "48h", Duration.ofHours(48),
          "7d", Duration.ofDays(7));
  private static final Duration CHECKPOINT_TOLERANCE = Duration.ofHours(2);

  private final JdbcClient jdbc;
  private final PompomProperties properties;
  private final PlatformGrowthProfileService growthProfiles;
  private final InterventionService interventions;
  private final DiscoveryProfileService discoveryProfiles;

  public PlatformStateService(
      JdbcClient jdbc,
      PompomProperties properties,
      PlatformGrowthProfileService growthProfiles,
      InterventionService interventions,
      DiscoveryProfileService discoveryProfiles) {
    this.jdbc = jdbc;
    this.properties = properties;
    this.growthProfiles = growthProfiles;
    this.interventions = interventions;
    this.discoveryProfiles = discoveryProfiles;
  }

  @Transactional
  public ObservationView observe(UUID videoId, ObservationRequest request, String actor) {
    requireVideo(videoId);
    String platform = normalize(request.platform());
    String type = requiredUpper(request.stateType(), "stateType");
    String value = requiredUpper(request.stateValue(), "stateValue");
    String source = requiredUpper(request.source(), "source");
    if (!VALUES.contains(value))
      throw new IllegalArgumentException("Unsupported state value: " + value);
    if (!SOURCES.contains(source))
      throw new IllegalArgumentException("Unsupported source: " + source);
    if (("MANUAL".equals(source) || "SCREENSHOT".equals(source)) && request.observedAt() == null) {
      throw new IllegalArgumentException("Manual and screenshot observations require observedAt");
    }
    if (request.confidence() < 0 || request.confidence() > 1) {
      throw new IllegalArgumentException("Confidence must be between 0 and 1");
    }
    UUID stateId = stateId(videoId, request.variantId(), platform, type);
    validateCorrection(stateId, request.correctionOfObservationId());
    boolean duplicate =
        jdbc.sql(
                """
                SELECT EXISTS(
                  SELECT 1 FROM platform_content_state_observations
                  WHERE state_id=:state AND state_value=:value
                    AND observed_at IS NOT DISTINCT FROM CAST(:observed AS timestamptz)
                    AND source=:source AND correction_of_id IS NULL)
                """)
            .param("state", stateId)
            .param("value", value)
            .param("observed", dbTime(request.observedAt()), Types.TIMESTAMP_WITH_TIMEZONE)
            .param("source", source)
            .query(Boolean.class)
            .single();
    if (duplicate && request.correctionOfObservationId() == null) {
      throw new IllegalStateException("Duplicate platform-state observation");
    }
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO platform_content_state_observations
              (id,state_id,state_value,observed_at,source,source_import_id,confidence,notes,
               evidence_relative_path,ocr_result,manually_verified,correction_of_id,recorded_by)
            VALUES (:id,:state,:value,:observed,:source,:import,:confidence,:notes,:evidence,
                    :ocr,:verified,:correction,:actor)
            """)
        .param("id", id)
        .param("state", stateId)
        .param("value", value)
        .param("observed", dbTime(request.observedAt()), Types.TIMESTAMP_WITH_TIMEZONE)
        .param("source", source)
        .param("import", request.sourceImportId(), Types.OTHER)
        .param("confidence", request.confidence())
        .param("notes", request.notes(), Types.VARCHAR)
        .param("evidence", request.evidenceRelativePath(), Types.VARCHAR)
        .param("ocr", request.ocrResult(), Types.VARCHAR)
        .param("verified", request.manuallyVerified())
        .param("correction", request.correctionOfObservationId(), Types.OTHER)
        .param("actor", actor == null || actor.isBlank() ? "local-user" : actor)
        .update();
    jdbc.sql(
            """
            INSERT INTO audit_events(actor,action,entity_type,entity_id,reason,new_state)
            VALUES (:actor,:action,'PLATFORM_STATE_OBSERVATION',:id,:reason,
                    jsonb_build_object('stateType',:type,'stateValue',:value,
                                       'observedAt',CAST(:observed AS timestamptz)))
            """)
        .param("actor", actor == null || actor.isBlank() ? "local-user" : actor)
        .param(
            "action",
            request.correctionOfObservationId() == null
                ? "OBSERVATION_ADDED"
                : "OBSERVATION_CORRECTED")
        .param("id", id)
        .param("reason", request.notes(), Types.VARCHAR)
        .param("type", type)
        .param("value", value)
        .param("observed", dbTime(request.observedAt()), Types.TIMESTAMP_WITH_TIMEZONE)
        .update();
    return getObservation(id);
  }

  @Transactional
  public ObservationView observeScreenshot(
      UUID videoId,
      String platform,
      String stateValue,
      Instant observedAt,
      String notes,
      String ocrResult,
      boolean manuallyVerified,
      String originalFilename,
      String contentType,
      InputStream input,
      String actor) {
    String extension = evidenceExtension(originalFilename, contentType);
    UUID evidenceId = UUID.randomUUID();
    Path directory =
        properties.dataRoot().toAbsolutePath().normalize().resolve("platform-state-evidence");
    Path destination = directory.resolve(evidenceId + extension).normalize();
    try {
      Files.createDirectories(directory);
      Files.copy(input, destination, StandardCopyOption.REPLACE_EXISTING);
    } catch (IOException error) {
      throw new IllegalStateException("Could not store screenshot evidence", error);
    }
    String relative =
        properties.dataRoot().toAbsolutePath().normalize().relativize(destination).toString();
    try {
      return observe(
          videoId,
          new ObservationRequest(
              null,
              platform,
              REACH_FURTHER,
              stateValue,
              observedAt,
              "SCREENSHOT",
              null,
              manuallyVerified ? 1.0 : 0.6,
              notes,
              relative,
              ocrResult,
              manuallyVerified,
              null),
          actor);
    } catch (RuntimeException error) {
      try {
        Files.deleteIfExists(destination);
      } catch (IOException ignored) {
        // The database remains authoritative; orphan cleanup can remove a failed staged file.
      }
      throw error;
    }
  }

  @Transactional
  public PublicationView recordPublication(UUID videoId, PublicationRequest request, String actor) {
    requireVideo(videoId);
    String platform = normalize(request.platform());
    UUID existing =
        jdbc.sql(
                """
                SELECT id FROM video_publications
                WHERE video_id=:video AND variant_id IS NOT DISTINCT FROM :variant AND platform=:platform
                """)
            .param("video", videoId)
            .param("variant", request.variantId(), Types.OTHER)
            .param("platform", platform)
            .query(UUID.class)
            .optional()
            .orElse(null);
    UUID id = existing == null ? UUID.randomUUID() : existing;
    if (existing == null) {
      jdbc.sql(
              """
              INSERT INTO video_publications
                (id,video_id,variant_id,platform,platform_content_id,platform_url,
                 published_at,publication_timezone,off_peak_publish,context_label,source,notes)
              VALUES (:id,:video,:variant,:platform,:platformContentId,:platformUrl,
                      :published,:timezone,:offPeak,:label,:source,:notes)
              """)
          .param("id", id)
          .param("video", videoId)
          .param("variant", request.variantId(), Types.OTHER)
          .param("platform", platform)
          .param("platformContentId", request.platformContentId(), Types.VARCHAR)
          .param("platformUrl", request.platformUrl(), Types.VARCHAR)
          .param("published", dbTime(request.publishedAt()), Types.TIMESTAMP_WITH_TIMEZONE)
          .param("timezone", request.publicationTimezone())
          .param("offPeak", request.offPeakPublish(), Types.BOOLEAN)
          .param("label", contextLabel(request.offPeakPublish()), Types.VARCHAR)
          .param("source", requiredUpper(request.source(), "source"))
          .param("notes", request.notes(), Types.VARCHAR)
          .update();
    } else {
      jdbc.sql(
              """
              UPDATE video_publications SET platform_content_id=:platformContentId,
                platform_url=:platformUrl,published_at=:published,publication_timezone=:timezone,
                off_peak_publish=:offPeak,context_label=:label,source=:source,notes=:notes
              WHERE id=:id
              """)
          .param("platformContentId", request.platformContentId(), Types.VARCHAR)
          .param("platformUrl", request.platformUrl(), Types.VARCHAR)
          .param("published", dbTime(request.publishedAt()), Types.TIMESTAMP_WITH_TIMEZONE)
          .param("timezone", request.publicationTimezone())
          .param("offPeak", request.offPeakPublish(), Types.BOOLEAN)
          .param("label", contextLabel(request.offPeakPublish()), Types.VARCHAR)
          .param("source", requiredUpper(request.source(), "source"))
          .param("notes", request.notes(), Types.VARCHAR)
          .param("id", id)
          .update();
    }
    jdbc.sql(
            """
            INSERT INTO audit_events(actor,action,entity_type,entity_id,reason,new_state)
            VALUES (:actor,:action,'VIDEO_PUBLICATION',:id,:notes,
                    jsonb_build_object('offPeakPublish',CAST(:offPeak AS boolean),
                                       'publishedAt',CAST(:published AS timestamptz),
                                       'platformContentId',CAST(:platformContentId AS text),
                                       'platformUrl',CAST(:platformUrl AS text)))
            """)
        .param("actor", actor == null || actor.isBlank() ? "local-user" : actor)
        .param(
            "action",
            existing == null ? "PUBLICATION_CONTEXT_ADDED" : "PUBLICATION_CONTEXT_CORRECTED")
        .param("id", id)
        .param("notes", request.notes(), Types.VARCHAR)
        .param("offPeak", request.offPeakPublish(), Types.BOOLEAN)
        .param("published", dbTime(request.publishedAt()), Types.TIMESTAMP_WITH_TIMEZONE)
        .param("platformContentId", request.platformContentId(), Types.VARCHAR)
        .param("platformUrl", request.platformUrl(), Types.VARCHAR)
        .update();
    return publication(videoId, request.variantId(), platform).orElseThrow();
  }

  @Transactional(readOnly = true)
  public List<ObservationView> observations(UUID videoId, String platform) {
    requireVideo(videoId);
    return jdbc.sql(
            """
            SELECT o.id,s.id AS state_id,s.platform,s.state_type,o.state_value,o.observed_at,
                   o.source,o.confidence,o.notes,o.evidence_relative_path,o.ocr_result,
                   o.manually_verified,o.correction_of_id,o.recorded_by,o.created_at,
                   EXISTS(SELECT 1 FROM platform_content_state_observations c
                          WHERE c.correction_of_id=o.id) AS superseded
            FROM platform_content_states s
            JOIN platform_content_state_observations o ON o.state_id=s.id
            WHERE s.video_id=:video AND (:platform IS NULL OR s.platform=:platform)
            ORDER BY COALESCE(o.observed_at,o.created_at),o.created_at
            """)
        .param("video", videoId)
        .param("platform", platform == null ? null : normalize(platform), Types.VARCHAR)
        .query((rs, ignored) -> mapObservation(rs))
        .list();
  }

  @Transactional(readOnly = true)
  public ReachFurtherSummary reachFurtherSummary(UUID videoId, String platform) {
    String normalizedPlatform = normalize(platform);
    Profile profile = profile(videoId);
    List<ObservationView> effective =
        observations(videoId, normalizedPlatform).stream()
            .filter(item -> REACH_FURTHER.equals(item.stateType()) && !item.superseded())
            .toList();
    List<ObservationView> active =
        effective.stream().filter(item -> "ACTIVE".equals(item.stateValue())).toList();
    Instant firstSeen =
        active.stream()
            .map(ObservationView::observedAt)
            .filter(java.util.Objects::nonNull)
            .min(Instant::compareTo)
            .orElse(null);
    Instant lastSeen =
        active.stream()
            .map(ObservationView::observedAt)
            .filter(java.util.Objects::nonNull)
            .max(Instant::compareTo)
            .orElse(null);
    Boolean currentlyActive =
        effective.stream()
            .max(
                java.util.Comparator.comparing(
                    item -> Optional.ofNullable(item.observedAt()).orElse(item.recordedAt())))
            .map(
                item ->
                    "UNKNOWN".equals(item.stateValue()) ? null : "ACTIVE".equals(item.stateValue()))
            .orElse(null);
    PublicationView publication = publication(videoId, null, normalizedPlatform).orElse(null);
    Instant publishedAt =
        publication == null
            ? inferredPublication(videoId, normalizedPlatform)
            : publication.publishedAt();
    Long ageSeconds =
        firstSeen == null || publishedAt == null
            ? null
            : Duration.between(publishedAt, firstSeen).getSeconds();
    String cohort = cohort(firstSeen, ageSeconds, active);
    MetricPoint baseline =
        firstSeen == null ? null : pointAtOrBefore(videoId, normalizedPlatform, firstSeen);
    Map<String, WindowPerformance> windows = new LinkedHashMap<>();
    if (firstSeen != null) {
      WINDOWS.entrySet().stream()
          .sorted(Map.Entry.comparingByValue())
          .forEach(
              entry -> {
                MetricPoint point =
                    pointAtOrAfter(videoId, normalizedPlatform, firstSeen.plus(entry.getValue()));
                windows.put(entry.getKey(), window(baseline, point, entry.getValue()));
              });
    }
    Double velocityBefore =
        firstSeen == null
            ? null
            : velocity(
                videoId, normalizedPlatform, firstSeen.minus(Duration.ofHours(3)), firstSeen);
    Double velocityAfter3h =
        firstSeen == null
            ? null
            : velocity(videoId, normalizedPlatform, firstSeen, firstSeen.plus(Duration.ofHours(3)));
    Double acceleration =
        velocityBefore == null || velocityAfter3h == null ? null : velocityAfter3h - velocityBefore;
    MetricPoint current = latestPoint(videoId, normalizedPlatform);
    String trajectory = trajectory(videoId, normalizedPlatform);
    List<String> flags = flags(!active.isEmpty(), current, acceleration, trajectory);
    return new ReachFurtherSummary(
        videoId,
        profile.filename(),
        normalizedPlatform,
        firstSeen,
        lastSeen,
        active.size(),
        currentlyActive,
        publishedAt,
        ageSeconds,
        cohort,
        publication == null ? null : publication.offPeakPublish(),
        publication == null ? null : publication.contextLabel(),
        publication == null ? null : publication.platformContentId(),
        publication == null ? null : publication.platformUrl(),
        baseline,
        current,
        windows,
        velocityBefore,
        velocityAfter3h,
        acceleration,
        trajectory,
        performanceBand(current == null ? null : current.views()),
        profile.creativeEngine(),
        profile.character(),
        profile.series(),
        flags,
        effective,
        "Observed association only; Reach Further is not treated as a cause of performance changes.");
  }

  @Transactional(readOnly = true)
  public LiveFeatures liveFeatures(
      UUID videoId, String platform, Instant cutoff, String predictionType) {
    if ("PRE_PUBLISH".equalsIgnoreCase(predictionType)) {
      return new LiveFeatures(false, "PRE_PUBLISH_LEAKAGE_GUARD", Map.of());
    }
    ReachFurtherSummary summary = reachFurtherSummary(videoId, platform);
    var growth = growthProfiles.profile(videoId, platform, cutoff, null);
    var discovery = discoveryProfiles.profile(videoId, platform, cutoff, null);
    Instant firstIntervention = interventions.firstAtOrBefore(videoId, platform, cutoff);
    var features = new LinkedHashMap<String, Object>();
    features.put("manualEngagementIntervention", firstIntervention != null);
    if (firstIntervention != null) {
      features.put("manualEngagementInterventionAt", firstIntervention.toString());
    }
    if (growth.instagramBurstRatio() != null) {
      features.put("instagramBurstRatio", growth.instagramBurstRatio());
    }
    if (growth.facebookTailRatio() != null) {
      features.put("facebookTailRatio", growth.facebookTailRatio());
      features.put("facebookViewsAfter24h", growth.viewsAfter24h());
    }
    if (discovery.nonFollowerShare() != null) {
      features.put("nonFollowerShare", discovery.nonFollowerShare());
    }
    if (discovery.usAudienceShare() != null) {
      features.put("usAudienceShare", discovery.usAudienceShare());
    }
    if (discovery.newAudienceQualityScore() != null) {
      features.put("newAudienceQualityScore", discovery.newAudienceQualityScore());
      features.put("newAudienceQualityAlgorithm", discovery.algorithmVersion());
    }
    if (discovery.followsPerThousandViews() != null) {
      features.put("followsPerThousandViews", discovery.followsPerThousandViews());
    }
    boolean eligible =
        summary.firstObservedAt() != null && !summary.firstObservedAt().isAfter(cutoff);
    if (!eligible) {
      return new LiveFeatures(true, "NO_REACH_FURTHER_EVIDENCE_BEFORE_CUTOFF", features);
    }
    features.put("reachFurtherObserved", true);
    features.put(
        "timeSinceReachFurtherFirstSeenSeconds",
        Duration.between(summary.firstObservedAt(), cutoff).getSeconds());
    features.put(
        "videoAgeWhenReachFurtherFirstSeenSeconds", summary.videoAgeAtFirstObservationSeconds());
    features.put("velocityBeforeReachFurther", summary.velocityBefore());
    features.put("velocityAfterReachFurther3h", summary.velocityAfter3h());
    features.put("offPeakPublish", summary.offPeakPublish());
    return new LiveFeatures(true, "ELIGIBLE_AT_CUTOFF", features);
  }

  private UUID stateId(UUID videoId, UUID variantId, String platform, String type) {
    jdbc.sql(
            """
            INSERT INTO platform_content_states(video_id,variant_id,platform,state_type)
            VALUES (:video,:variant,:platform,:type) ON CONFLICT DO NOTHING
            """)
        .param("video", videoId)
        .param("variant", variantId, Types.OTHER)
        .param("platform", platform)
        .param("type", type)
        .update();
    return jdbc.sql(
            """
            SELECT id FROM platform_content_states
            WHERE video_id=:video AND variant_id IS NOT DISTINCT FROM :variant
              AND platform=:platform AND state_type=:type
            """)
        .param("video", videoId)
        .param("variant", variantId, Types.OTHER)
        .param("platform", platform)
        .param("type", type)
        .query(UUID.class)
        .single();
  }

  private void validateCorrection(UUID stateId, UUID correctionId) {
    if (correctionId == null) return;
    boolean valid =
        jdbc.sql(
                """
                SELECT EXISTS(SELECT 1 FROM platform_content_state_observations o
                  WHERE o.id=:id AND o.state_id=:state)
                AND NOT EXISTS(SELECT 1 FROM platform_content_state_observations c
                  WHERE c.correction_of_id=:id)
                """)
            .param("id", correctionId)
            .param("state", stateId)
            .query(Boolean.class)
            .single();
    if (!valid)
      throw new IllegalArgumentException("Correction target is invalid or already superseded");
  }

  private ObservationView getObservation(UUID id) {
    return jdbc.sql(
            """
            SELECT o.id,s.id AS state_id,s.platform,s.state_type,o.state_value,o.observed_at,
                   o.source,o.confidence,o.notes,o.evidence_relative_path,o.ocr_result,
                   o.manually_verified,o.correction_of_id,o.recorded_by,o.created_at,false AS superseded
            FROM platform_content_state_observations o
            JOIN platform_content_states s ON s.id=o.state_id WHERE o.id=:id
            """)
        .param("id", id)
        .query((rs, ignored) -> mapObservation(rs))
        .single();
  }

  private ObservationView mapObservation(java.sql.ResultSet rs) throws java.sql.SQLException {
    OffsetDateTime observed = rs.getObject("observed_at", OffsetDateTime.class);
    return new ObservationView(
        rs.getObject("id", UUID.class),
        rs.getObject("state_id", UUID.class),
        rs.getString("platform"),
        rs.getString("state_type"),
        rs.getString("state_value"),
        observed == null ? null : observed.toInstant(),
        rs.getString("source"),
        rs.getDouble("confidence"),
        rs.getString("notes"),
        rs.getString("evidence_relative_path"),
        rs.getString("ocr_result"),
        rs.getBoolean("manually_verified"),
        rs.getObject("correction_of_id", UUID.class),
        rs.getString("recorded_by"),
        rs.getObject("created_at", OffsetDateTime.class).toInstant(),
        rs.getBoolean("superseded"));
  }

  private Optional<PublicationView> publication(UUID videoId, UUID variantId, String platform) {
    return jdbc.sql(
            """
            SELECT id,platform,platform_content_id,platform_url,published_at,
                   publication_timezone,off_peak_publish,context_label,source,notes
            FROM video_publications
            WHERE video_id=:video AND variant_id IS NOT DISTINCT FROM :variant AND platform=:platform
            ORDER BY created_at DESC LIMIT 1
            """)
        .param("video", videoId)
        .param("variant", variantId, Types.OTHER)
        .param("platform", platform)
        .query(
            (rs, ignored) ->
                new PublicationView(
                    rs.getObject("id", UUID.class),
                    rs.getString("platform"),
                    rs.getString("platform_content_id"),
                    rs.getString("platform_url"),
                    rs.getObject("published_at", OffsetDateTime.class).toInstant(),
                    rs.getString("publication_timezone"),
                    (Boolean) rs.getObject("off_peak_publish"),
                    rs.getString("context_label"),
                    rs.getString("source"),
                    rs.getString("notes")))
        .optional();
  }

  private Instant inferredPublication(UUID videoId, String platform) {
    return jdbc.sql(
            """
            SELECT min(publication_timestamp) FROM performance_observations
            WHERE video_id=:video AND platform=:platform AND publication_timestamp IS NOT NULL
            """)
        .param("video", videoId)
        .param("platform", platform)
        .query(OffsetDateTime.class)
        .optional()
        .map(OffsetDateTime::toInstant)
        .orElse(null);
  }

  private MetricPoint pointAtOrBefore(UUID videoId, String platform, Instant at) {
    return point(videoId, platform, at, true);
  }

  private MetricPoint pointAtOrAfter(UUID videoId, String platform, Instant at) {
    return point(videoId, platform, at, false);
  }

  private MetricPoint point(UUID videoId, String platform, Instant at, boolean before) {
    String operator = before ? "<=" : ">=";
    String order = before ? "DESC" : "ASC";
    return jdbc.sql(
            "SELECT measurement_timestamp,views,reach FROM performance_observations "
                + "WHERE video_id=:video AND platform=:platform AND measurement_timestamp "
                + operator
                + " :at ORDER BY measurement_timestamp "
                + order
                + " LIMIT 1")
        .param("video", videoId)
        .param("platform", platform)
        .param("at", dbTime(at), Types.TIMESTAMP_WITH_TIMEZONE)
        .query((rs, ignored) -> metricPoint(rs, at))
        .optional()
        .orElse(null);
  }

  private MetricPoint latestPoint(UUID videoId, String platform) {
    return jdbc.sql(
            """
            SELECT measurement_timestamp,views,reach FROM performance_observations
            WHERE video_id=:video AND platform=:platform AND measurement_timestamp IS NOT NULL
            ORDER BY measurement_timestamp DESC LIMIT 1
            """)
        .param("video", videoId)
        .param("platform", platform)
        .query(
            (rs, ignored) -> {
              Instant measuredAt = rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant();
              return metricPoint(rs, measuredAt);
            })
        .optional()
        .orElse(null);
  }

  private MetricPoint metricPoint(java.sql.ResultSet rs, Instant target) throws java.sql.SQLException {
    Instant measuredAt = rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant();
    boolean withinTolerance =
        Duration.between(measuredAt, target).abs().compareTo(CHECKPOINT_TOLERANCE) <= 0;
    return new MetricPoint(
        measuredAt, nullableLong(rs, "views"), nullableLong(rs, "reach"), withinTolerance);
  }

  private Double velocity(UUID videoId, String platform, Instant from, Instant to) {
    MetricPoint start = pointAtOrAfter(videoId, platform, from);
    MetricPoint end = pointAtOrBefore(videoId, platform, to);
    if (start == null
        || end == null
        || start.views() == null
        || end.views() == null
        || !end.measuredAt().isAfter(start.measuredAt())) return null;
    double hours = Duration.between(start.measuredAt(), end.measuredAt()).toMillis() / 3_600_000.0;
    return (end.views() - start.views()) / hours;
  }

  private WindowPerformance window(MetricPoint baseline, MetricPoint point, Duration target) {
    Long deltaViews =
        baseline == null || point == null || baseline.views() == null || point.views() == null
            ? null
            : point.views() - baseline.views();
    Long deltaReach =
        baseline == null || point == null || baseline.reach() == null || point.reach() == null
            ? null
            : point.reach() - baseline.reach();
    Double velocity = deltaViews == null ? null : deltaViews / (target.toMinutes() / 60.0);
    return new WindowPerformance(point, deltaViews, deltaReach, velocity);
  }

  private String trajectory(UUID videoId, String platform) {
    Double recent =
        velocity(videoId, platform, Instant.now().minus(Duration.ofHours(3)), Instant.now());
    Double prior =
        velocity(
            videoId,
            platform,
            Instant.now().minus(Duration.ofHours(6)),
            Instant.now().minus(Duration.ofHours(3)));
    if (recent == null || prior == null) return "INSUFFICIENT_DATA";
    if (recent > Math.max(50, prior * 1.75)) return "SECOND_WAVE";
    if (recent < 10) return "EARLY_STALL";
    if (recent > prior * 1.1) return "PERSISTENT_GROWTH";
    return "SLOW_GROWTH";
  }

  private Profile profile(UUID videoId) {
    return jdbc.sql(
            """
            SELECT v.original_filename,
              (SELECT ca.primary_engine FROM creative_analyses ca WHERE ca.video_id=v.id ORDER BY ca.created_at DESC LIMIT 1) AS engine,
              (SELECT c.name FROM video_characters vc JOIN characters c ON c.id=vc.character_id
                WHERE vc.video_id=v.id ORDER BY (vc.participation='PRIMARY') DESC,c.name LIMIT 1) AS character,
              s.name AS series
            FROM videos v LEFT JOIN series s ON s.id=v.series_id WHERE v.id=:id
            """)
        .param("id", videoId)
        .query(
            (rs, ignored) ->
                new Profile(
                    rs.getString("original_filename"),
                    rs.getString("engine"),
                    rs.getString("character"),
                    rs.getString("series")))
        .optional()
        .orElseThrow(() -> new IllegalArgumentException("Video not found: " + videoId));
  }

  private void requireVideo(UUID videoId) {
    boolean exists =
        jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
            .param("id", videoId)
            .query(Boolean.class)
            .single();
    if (!exists) throw new IllegalArgumentException("Video not found: " + videoId);
  }

  private String cohort(Instant first, Long ageSeconds, List<ObservationView> active) {
    if (active.isEmpty()) return "NOT_OBSERVED";
    if (first == null || ageSeconds == null || ageSeconds < 0) return "UNKNOWN_TIMING";
    double hours = ageSeconds / 3600.0;
    if (hours <= properties.reachFurtherEarlyHours()) return "REACH_FURTHER_EARLY";
    if (hours <= properties.reachFurtherMidHours()) return "REACH_FURTHER_MID";
    return "REACH_FURTHER_LATE";
  }

  private List<String> flags(
      boolean observed, MetricPoint current, Double acceleration, String trajectory) {
    var flags = new ArrayList<String>();
    if (!observed) return flags;
    flags.add("REACH_FURTHER_OBSERVED");
    if (current != null && current.views() != null && current.views() < 1000)
      flags.add("REACH_FURTHER_LOW_PERFORMANCE");
    if (acceleration != null && acceleration <= 0) flags.add("REACH_FURTHER_NO_ACCELERATION");
    if ("SECOND_WAVE".equals(trajectory)) flags.add("REACH_FURTHER_SECOND_WAVE");
    if ("PERSISTENT_GROWTH".equals(trajectory)) flags.add("REACH_FURTHER_PERSISTENT_GROWTH");
    if ("LATE_BREAKOUT".equals(trajectory)) flags.add("REACH_FURTHER_LATE_BREAKOUT");
    return flags;
  }

  private String performanceBand(Long views) {
    if (views == null) return "UNKNOWN";
    if (views >= 50_000) return "50K_PLUS";
    if (views >= 20_000) return "20K_PLUS";
    if (views >= 5_000) return "5K_PLUS";
    if (views >= 2_000) return "2K_PLUS";
    if (views >= 500) return "500_PLUS";
    return "BELOW_500";
  }

  private String contextLabel(Boolean offPeak) {
    return Boolean.TRUE.equals(offPeak) ? "LOW-SIGNAL / OFF-PEAK TEST" : null;
  }

  private String evidenceExtension(String filename, String contentType) {
    String lower = filename == null ? "" : filename.toLowerCase();
    if (lower.endsWith(".png") || "image/png".equals(contentType)) return ".png";
    if (lower.endsWith(".jpg") || lower.endsWith(".jpeg") || "image/jpeg".equals(contentType))
      return ".jpg";
    if (lower.endsWith(".webp") || "image/webp".equals(contentType)) return ".webp";
    throw new IllegalArgumentException("Evidence must be PNG, JPEG, or WebP");
  }

  private OffsetDateTime dbTime(Instant value) {
    return value == null ? null : OffsetDateTime.ofInstant(value, ZoneOffset.UTC);
  }

  private String normalize(String value) {
    if (value == null || value.isBlank())
      throw new IllegalArgumentException("platform is required");
    return value.trim().toLowerCase();
  }

  private String requiredUpper(String value, String field) {
    if (value == null || value.isBlank())
      throw new IllegalArgumentException(field + " is required");
    return value.trim().toUpperCase();
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  private record Profile(String filename, String creativeEngine, String character, String series) {}

  public record ObservationRequest(
      UUID variantId,
      String platform,
      String stateType,
      String stateValue,
      Instant observedAt,
      String source,
      UUID sourceImportId,
      double confidence,
      String notes,
      String evidenceRelativePath,
      String ocrResult,
      boolean manuallyVerified,
      UUID correctionOfObservationId) {}

  public record ObservationView(
      UUID id,
      UUID stateId,
      String platform,
      String stateType,
      String stateValue,
      Instant observedAt,
      String source,
      double confidence,
      String notes,
      String evidenceRelativePath,
      String ocrResult,
      boolean manuallyVerified,
      UUID correctionOfObservationId,
      String recordedBy,
      Instant recordedAt,
      boolean superseded) {}

  public record PublicationRequest(
      UUID variantId,
      String platform,
      String platformContentId,
      String platformUrl,
      Instant publishedAt,
      String publicationTimezone,
      Boolean offPeakPublish,
      String source,
      String notes) {}

  public record PublicationView(
      UUID id,
      String platform,
      String platformContentId,
      String platformUrl,
      Instant publishedAt,
      String publicationTimezone,
      Boolean offPeakPublish,
      String contextLabel,
      String source,
      String notes) {}

  public record MetricPoint(Instant measuredAt, Long views, Long reach, boolean withinTolerance) {}

  public record WindowPerformance(
      MetricPoint observation, Long deltaViews, Long deltaReach, Double viewsPerHour) {}

  public record ReachFurtherSummary(
      UUID videoId,
      String video,
      String platform,
      Instant firstObservedAt,
      Instant lastObservedAt,
      int observationCount,
      Boolean active,
      Instant publishedAt,
      Long videoAgeAtFirstObservationSeconds,
      String cohort,
      Boolean offPeakPublish,
      String publicationContextLabel,
      String platformContentId,
      String platformUrl,
      MetricPoint atFirstObservation,
      MetricPoint current,
      Map<String, WindowPerformance> performanceWindows,
      Double velocityBefore,
      Double velocityAfter3h,
      Double accelerationAfterStatus,
      String trajectoryType,
      String performanceBand,
      String creativeEngine,
      String character,
      String series,
      List<String> flags,
      List<ObservationView> observations,
      String causalDisclaimer) {}

  public record LiveFeatures(boolean allowed, String reason, Map<String, Object> features) {}
}
