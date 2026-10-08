package com.pompomhills.intelligence.performance;

import com.pompomhills.intelligence.common.config.PompomProperties;
import com.pompomhills.intelligence.platformstate.PlatformStateService;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.sql.Types;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.core.JacksonException;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

@Service
public class PerformanceImportService {
  private static final String PARSER_VERSION = "performance-import-v1";
  private final JdbcClient jdbc;
  private final ObjectMapper json;
  private final ImportFileParser parser;
  private final PompomProperties properties;
  private final DiscoveryScoreProperties discoveryScoreProperties;
  private final PlatformStateService platformStates;

  public PerformanceImportService(
      JdbcClient jdbc,
      ObjectMapper json,
      ImportFileParser parser,
      PompomProperties properties,
      DiscoveryScoreProperties discoveryScoreProperties,
      PlatformStateService platformStates) {
    this.jdbc = jdbc;
    this.json = json;
    this.parser = parser;
    this.properties = properties;
    this.discoveryScoreProperties = discoveryScoreProperties;
    this.platformStates = platformStates;
  }

  @Transactional
  public ImportPreview preview(MultipartFile upload, String platform, String timezone) {
    if (upload.isEmpty()) throw new IllegalArgumentException("Import file is empty");
    String originalName = Optional.ofNullable(upload.getOriginalFilename()).orElse("import.csv");
    Path rawDirectory = properties.dataRoot().resolve("imports/raw").toAbsolutePath().normalize();
    try {
      Files.createDirectories(rawDirectory);
      Path temporary = Files.createTempFile(rawDirectory, ".upload-", ".tmp");
      String hash;
      try (InputStream input = upload.getInputStream();
          var digest = new DigestInputStream(input, MessageDigest.getInstance("SHA-256"))) {
        Files.copy(digest, temporary, StandardCopyOption.REPLACE_EXISTING);
        hash = HexFormat.of().formatHex(digest.getMessageDigest().digest());
      }
      var duplicate = findByHash(hash);
      if (duplicate.isPresent()) {
        Files.deleteIfExists(temporary);
        var context = jdbc.sql("SELECT platform,timezone_assumption FROM import_batches WHERE id=:id")
            .param("id", duplicate.get().batchId()).query((rs, ignored) -> new String[] {rs.getString("platform"), rs.getString("timezone_assumption")}).single();
        String requestedTimezone = timezone == null || timezone.isBlank() ? "UTC" : timezone;
        if (!java.util.Objects.equals(context[0], normalizePlatform(platform)) || !java.util.Objects.equals(context[1], requestedTimezone)) {
          throw new IllegalStateException("Identical source bytes were imported with a different platform or timezone; reuse the original context or provide a corrected export");
        }
        return duplicate.get().withDuplicate(true);
      }
      UUID batchId = UUID.randomUUID();
      Path destination = rawDirectory.resolve(batchId + "-" + safeFilename(originalName));
      Files.move(temporary, destination, StandardCopyOption.ATOMIC_MOVE);
      ImportFileParser.ParsedFile parsed;
      try (InputStream input = Files.newInputStream(destination)) {
        parsed = parser.parse(originalName, input);
      }
      List<RowMatch> matches = parsed.rows().stream().map(this::match).toList();
      long matched = matches.stream().filter(item -> item.videoId() != null).count();
      Map<String, Object> report = new LinkedHashMap<>();
      report.put("columns", parsed.columns());
      report.put("rowCount", parsed.rows().size());
      report.put("matchedRows", matched);
      report.put("unresolvedRows", parsed.rows().size() - matched);
      report.put(
          "rawRelativePath",
          properties.dataRoot().toAbsolutePath().normalize().relativize(destination).toString());
      jdbc.sql(
              """
              INSERT INTO import_batches
                (id,source_filename,source_hash,platform,parser_version,timezone_assumption,column_mapping,quality_report,status)
              VALUES (:id,:name,:hash,:platform,:parser,:timezone,CAST(:mapping AS jsonb),CAST(:report AS jsonb),'PREVIEWED')
              """)
          .param("id", batchId)
          .param("name", originalName)
          .param("hash", hash)
          .param("platform", normalizePlatform(platform), Types.VARCHAR)
          .param("parser", PARSER_VERSION)
          .param("timezone", timezone == null || timezone.isBlank() ? "UTC" : timezone)
          .param("mapping", "{}")
          .param("report", writeJson(report))
          .update();
      for (int index = 0; index < parsed.rows().size(); index++) {
        var row = parsed.rows().get(index);
        var rowMatch = matches.get(index);
        jdbc.sql(
                """
                INSERT INTO import_rows
                  (import_batch_id,sheet_name,source_row_number,raw_data,matched_video_id,
                   matched_variant_id,match_status,match_confidence)
                VALUES (:batch,:sheet,:row,CAST(:raw AS jsonb),:video,:variant,:status,:confidence)
                """)
            .param("batch", batchId)
            .param("sheet", row.sheet())
            .param("row", row.rowNumber())
            .param("raw", writeJson(row.values()))
            .param("video", rowMatch.videoId(), Types.OTHER)
            .param("variant", rowMatch.variantId(), Types.OTHER)
            .param("status", rowMatch.videoId() == null ? "UNRESOLVED" : "EXACT")
            .param("confidence", rowMatch.videoId() == null ? null : 1.0, Types.DOUBLE)
            .update();
      }
      return new ImportPreview(
          batchId,
          originalName,
          hash,
          parsed.columns(),
          parsed.rows().size(),
          matched,
          parsed.rows().size() - matched,
          false,
          "PREVIEWED");
    } catch (IOException | NoSuchAlgorithmException error) {
      throw new IllegalStateException("Could not stage import: " + error.getMessage(), error);
    }
  }

  @Transactional
  public ImportPreview commit(UUID batchId) {
    ImportPreview preview = get(batchId);
    int unresolved =
        jdbc.sql(
                "SELECT count(*) FROM import_rows WHERE import_batch_id=:id AND match_status='UNRESOLVED'")
            .param("id", batchId)
            .query(Integer.class)
            .single();
    if (unresolved > 0) {
      throw new IllegalStateException(
          "Resolve all unmatched rows before commit; unresolved rows: " + unresolved);
    }
    String platform =
        jdbc.sql("SELECT platform FROM import_batches WHERE id=:id")
            .param("id", batchId)
            .query(String.class)
            .optional()
            .filter(value -> !value.isBlank())
            .orElseThrow(() -> new IllegalStateException("A platform is required before commit"));
    var rows =
        jdbc.sql(
                """
                SELECT id,matched_video_id,matched_variant_id,raw_data::text
                FROM import_rows WHERE import_batch_id=:id ORDER BY sheet_name,source_row_number
                """)
            .param("id", batchId)
            .query(
                (rs, ignored) ->
                    new CommitRow(
                        rs.getObject("id", UUID.class),
                        rs.getObject("matched_video_id", UUID.class),
                        rs.getObject("matched_variant_id", UUID.class),
                        readMap(rs.getString("raw_data"))))
            .list();
    rows.forEach(
        row -> {
          writeObservation(row, platform);
          writeExplicitPlatformState(row, platform, batchId);
        });
    jdbc.sql("UPDATE import_batches SET status='COMMITTED' WHERE id=:id AND status='PREVIEWED'")
        .param("id", batchId)
        .update();
    return preview.withStatus("COMMITTED");
  }

  @Transactional(readOnly = true)
  public List<ImportRow> rows(UUID batchId) {
    get(batchId);
    return jdbc.sql(
            """
            SELECT id,sheet_name,source_row_number,raw_data::text,matched_video_id,matched_variant_id,match_status,
                   match_confidence,
                   (SELECT reason FROM audit_events audit WHERE audit.entity_id=import_rows.id
                    AND audit.action='MANUAL_IMPORT_MATCH' ORDER BY audit.created_at DESC LIMIT 1) match_reason
            FROM import_rows WHERE import_batch_id=:id
            ORDER BY sheet_name,source_row_number
            """)
        .param("id", batchId)
        .query(
            (rs, ignored) ->
                new ImportRow(
                    rs.getObject("id", UUID.class),
                    rs.getString("sheet_name"),
                    rs.getInt("source_row_number"),
                    readMap(rs.getString("raw_data")),
                    rs.getObject("matched_video_id", UUID.class),
                    rs.getObject("matched_variant_id", UUID.class),
                    rs.getString("match_status"),
                    (Double) rs.getObject("match_confidence"),
                    rs.getString("match_reason")))
        .list();
  }

  @Transactional
  public ImportPreview resolve(UUID batchId, UUID rowId, UUID videoId, String reason) {
    return resolve(batchId, rowId, videoId, null, reason);
  }

  @Transactional
  public ImportPreview resolve(UUID batchId, UUID rowId, UUID videoId, UUID variantId, String reason) {
    String status =
        jdbc.sql("SELECT status FROM import_batches WHERE id=:id")
            .param("id", batchId)
            .query(String.class)
            .optional()
            .orElseThrow(() -> new IllegalArgumentException("Import batch not found: " + batchId));
    if (!"PREVIEWED".equals(status)) {
      throw new IllegalStateException("Only previewed imports can be resolved");
    }
    boolean videoExists =
        jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
            .param("id", videoId)
            .query(Boolean.class)
            .single();
    if (!videoExists) throw new IllegalArgumentException("Video not found: " + videoId);

    if (variantId != null && !jdbc.sql("SELECT EXISTS(SELECT 1 FROM video_variants WHERE id=:variant AND video_id=:video)")
        .param("variant", variantId).param("video", videoId).query(Boolean.class).single()) {
      throw new IllegalArgumentException("Variant does not belong to the selected video");
    }
    UUID previousVariant = jdbc.sql("SELECT matched_variant_id FROM import_rows WHERE id=:row AND import_batch_id=:batch")
        .param("row", rowId).param("batch", batchId).query(UUID.class).optional().orElse(null);
    UUID previous =
        jdbc.sql(
                "SELECT matched_video_id FROM import_rows WHERE id=:row AND import_batch_id=:batch")
            .param("row", rowId)
            .param("batch", batchId)
            .query(UUID.class)
            .optional()
            .orElse(null);
    int updated =
        jdbc.sql(
                """
                UPDATE import_rows
                SET matched_video_id=:video,matched_variant_id=:variant,match_status='MANUAL',match_confidence=1.0
                WHERE id=:row AND import_batch_id=:batch
                """)
            .param("video", videoId)
            .param("variant", variantId, Types.OTHER)
            .param("row", rowId)
            .param("batch", batchId)
            .update();
    if (updated == 0) throw new IllegalArgumentException("Import row not found: " + rowId);

    jdbc.sql(
            """
            INSERT INTO audit_events(actor,action,entity_type,entity_id,reason,old_state,new_state)
            VALUES ('local-user','MANUAL_IMPORT_MATCH','IMPORT_ROW',:row,:reason,
                    jsonb_build_object('videoId',CAST(:previous AS uuid),'variantId',CAST(:previousVariant AS uuid)),
                    jsonb_build_object('videoId',CAST(:video AS uuid),'variantId',CAST(:variant AS uuid)))
            """)
        .param("row", rowId)
        .param("reason", reason == null || reason.isBlank() ? "Manual exact selection" : reason)
        .param("previous", previous, Types.OTHER)
        .param("previousVariant", previousVariant, Types.OTHER)
        .param("variant", variantId, Types.OTHER)
        .param("video", videoId)
        .update();
    refreshMatchCounts(batchId);
    return get(batchId);
  }

  @Transactional(readOnly = true)
  public ImportPreview get(UUID batchId) {
    return jdbc.sql(
            """
            SELECT id,source_filename,source_hash,quality_report::text,status
            FROM import_batches WHERE id=:id
            """)
        .param("id", batchId)
        .query(
            (rs, ignored) ->
                fromDatabase(
                    rs.getObject("id", UUID.class),
                    rs.getString("source_filename"),
                    rs.getString("source_hash"),
                    rs.getString("quality_report"),
                    rs.getString("status")))
        .optional()
        .orElseThrow(() -> new IllegalArgumentException("Import batch not found: " + batchId));
  }

  private Optional<ImportPreview> findByHash(String hash) {
    return jdbc.sql(
            """
            SELECT id,source_filename,source_hash,quality_report::text,status
            FROM import_batches WHERE source_hash=:hash
            """)
        .param("hash", hash)
        .query(
            (rs, ignored) ->
                fromDatabase(
                    rs.getObject("id", UUID.class),
                    rs.getString("source_filename"),
                    rs.getString("source_hash"),
                    rs.getString("quality_report"),
                    rs.getString("status")))
        .optional();
  }

  private void refreshMatchCounts(UUID batchId) {
    Map<String, Long> counts =
        jdbc.sql(
                """
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE matched_video_id IS NOT NULL) AS matched
                FROM import_rows WHERE import_batch_id=:id
                """)
            .param("id", batchId)
            .query(
                (rs, ignored) ->
                    Map.of("total", rs.getLong("total"), "matched", rs.getLong("matched")))
            .single();
    long total = counts.get("total");
    long matched = counts.get("matched");
    jdbc.sql(
            """
            UPDATE import_batches
            SET quality_report=jsonb_set(
              jsonb_set(quality_report,'{matchedRows}',to_jsonb(CAST(:matched AS bigint)),true),
              '{unresolvedRows}',to_jsonb(CAST(:unresolved AS bigint)),true)
            WHERE id=:id
            """)
        .param("matched", matched)
        .param("unresolved", total - matched)
        .param("id", batchId)
        .update();
  }

  private ImportPreview fromDatabase(
      UUID id, String name, String hash, String reportJson, String status) {
    try {
      Map<String, Object> report = json.readValue(reportJson, new TypeReference<>() {});
      @SuppressWarnings("unchecked")
      List<String> columns = (List<String>) report.getOrDefault("columns", List.of());
      return new ImportPreview(
          id,
          name,
          hash,
          columns,
          number(report, "rowCount"),
          number(report, "matchedRows"),
          number(report, "unresolvedRows"),
          false,
          status);
    } catch (JacksonException error) {
      throw new IllegalStateException("Stored import report is invalid", error);
    }
  }

  private RowMatch match(ImportFileParser.ParsedRow row) {
    var normalized = normalize(row.values());
    String explicitId = first(normalized, "videoid", "video_id");
    UUID resolvedVideoId = null;
    if (explicitId != null) {
      try {
        UUID id = UUID.fromString(explicitId);
        boolean exists =
            jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
                .param("id", id)
                .query(Boolean.class)
                .single();
        if (exists) resolvedVideoId = id;
      } catch (IllegalArgumentException ignored) {
        // Invalid identifiers remain unresolved. Fuzzy matching is intentionally forbidden.
      }
    }
    if (resolvedVideoId == null) {
      String filename = first(normalized, "filename", "videofilename", "video_filename");
      if (filename != null) {
        List<UUID> ids =
            jdbc.sql("SELECT id FROM videos WHERE original_filename=:name ORDER BY created_at")
                .param("name", filename)
                .query(UUID.class)
                .list();
        if (ids.size() == 1) resolvedVideoId = ids.getFirst();
      }
    }
    if (resolvedVideoId == null) return new RowMatch(null, null);
    UUID variantId = resolveVariant(normalized, resolvedVideoId);
    return new RowMatch(resolvedVideoId, variantId);
  }

  /**
   * Resolves an explicit variantid/variant_id import column to a real video_variants row scoped
   * to the already-resolved video - never a filename or fuzzy guess, per the audit's P1-08
   * requirement. Returns null (not an error) when no variant column is present, the value isn't
   * a valid UUID, or the UUID doesn't resolve to a variant of THIS video.
   */
  private UUID resolveVariant(Map<String, String> normalized, UUID videoId) {
    String explicitVariantId = first(normalized, "variantid", "variant_id");
    if (explicitVariantId == null) return null;
    try {
      UUID variantId = UUID.fromString(explicitVariantId);
      boolean belongsToVideo =
          jdbc.sql(
                  "SELECT EXISTS(SELECT 1 FROM video_variants WHERE id=:variant AND video_id=:video)")
              .param("variant", variantId)
              .param("video", videoId)
              .query(Boolean.class)
              .single();
      return belongsToVideo ? variantId : null;
    } catch (IllegalArgumentException ignored) {
      return null;
    }
  }

  private String first(Map<String, String> values, String... keys) {
    for (String key : keys) {
      String value = values.get(key);
      if (value != null && !value.isBlank()) return value.trim();
    }
    return null;
  }

  private void writeObservation(CommitRow row, String platform) {
    Map<String, String> values = normalize(row.raw());
    String semantics =
        Optional.ofNullable(first(values, "metricsemantics", "metric_semantics"))
            .map(String::toUpperCase)
            .filter(
                value ->
                    List.of("DAILY_INCREMENT", "CUMULATIVE", "SNAPSHOT", "UNKNOWN").contains(value))
            .orElse("UNKNOWN");
    UUID observationId =
        jdbc.sql(
                """
            INSERT INTO performance_observations
              (import_row_id,video_id,variant_id,platform,platform_content_id,publication_timestamp,
               measurement_timestamp,metric_semantics,views,reach,unique_viewers,
               three_second_views,fifteen_second_views,average_watch_seconds,total_watch_seconds,
               likes,comments,shares,saves,follows,recommendation_percentage,
               followers_percentage,nonfollowers_percentage,paid,plays,completion_rate,skip_rate,
               profile_visits,follows_attributed,source,source_version,raw_payload_json,
               data_quality_status)
            VALUES
              (:row,:video,:variant,:platform,:contentId,:published,:measured,:semantics,:views,:reach,
               :uniqueViewers,:threeSecond,:fifteenSecond,:averageWatch,:totalWatch,
               :likes,:comments,:shares,:saves,:follows,:recommendation,
               :followers,:nonfollowers,:paid,:plays,:completion,:skipRate,:profileVisits,
               :followsAttributed,'CSV',:sourceVersion,CAST(:rawPayload AS jsonb),'IMPORTED')
            ON CONFLICT (import_row_id) DO NOTHING
            RETURNING id
            """)
            .param("row", row.id())
            .param("video", row.videoId())
            .param("variant", row.variantId(), Types.OTHER)
            .param("platform", platform)
            .param(
                "contentId",
                first(values, "platformcontentid", "contentid", "postid"),
                Types.VARCHAR)
            .param(
                "published",
                utc(
                    instant(
                        first(
                            values,
                            "publicationtimestamp",
                            "publication_timestamp",
                            "publishedat",
                            "published_at",
                            "publisheddate"))),
                Types.TIMESTAMP_WITH_TIMEZONE)
            .param(
                "measured",
                utc(
                    instant(
                        first(
                            values,
                            "measurementtimestamp",
                            "measurement_timestamp",
                            "measuredat",
                            "measured_at",
                            "date"))),
                Types.TIMESTAMP_WITH_TIMEZONE)
            .param("semantics", semantics)
            .param("views", whole(values, "views"), Types.BIGINT)
            .param("reach", whole(values, "reach"), Types.BIGINT)
            .param("uniqueViewers", whole(values, "uniqueviewers", "unique_viewers"), Types.BIGINT)
            .param("threeSecond", whole(values, "3secondviews", "threesecondviews"), Types.BIGINT)
            .param(
                "fifteenSecond", whole(values, "15secondviews", "fifteensecondviews"), Types.BIGINT)
            .param(
                "averageWatch",
                decimal(values, "averagewatchseconds", "avgwatchseconds"),
                Types.DOUBLE)
            .param("totalWatch", decimal(values, "totalwatchseconds"), Types.DOUBLE)
            .param("likes", whole(values, "likes"), Types.BIGINT)
            .param("comments", whole(values, "comments"), Types.BIGINT)
            .param("shares", whole(values, "shares"), Types.BIGINT)
            .param("saves", whole(values, "saves"), Types.BIGINT)
            .param("follows", whole(values, "follows", "followersgained"), Types.BIGINT)
            .param(
                "recommendation",
                decimal(values, "recommendationpercentage", "recommendation_percentage"),
                Types.DOUBLE)
            .param(
                "followers",
                decimal(
                    values,
                    "followerspercentage",
                    "followers_percentage",
                    "followerpercentage",
                    "follower_view_percentage",
                    "follower_share"),
                Types.DOUBLE)
            .param(
                "nonfollowers",
                decimal(
                    values,
                    "nonfollowerspercentage",
                    "nonfollowers_percentage",
                    "nonfollowerpercentage",
                    "non_follower_percentage",
                    "non_follower_view_percentage",
                    "non_follower_share"),
                Types.DOUBLE)
            .param(
                "paid",
                Boolean.parseBoolean(Optional.ofNullable(first(values, "paid")).orElse("false")))
            .param("plays", whole(values, "plays"), Types.BIGINT)
            .param("completion", decimal(values, "completionrate", "completion_rate"), Types.DOUBLE)
            .param("skipRate", decimal(values, "skiprate", "skip_rate"), Types.DOUBLE)
            .param("profileVisits", whole(values, "profilevisits", "profile_visits"), Types.BIGINT)
            .param(
                "followsAttributed",
                whole(values, "followsattributed", "follows_attributed"),
                Types.BIGINT)
            .param("sourceVersion", PARSER_VERSION)
            .param("rawPayload", writeJson(row.raw()))
            .query(UUID.class)
            .optional()
            .orElseGet(
                () ->
                    jdbc.sql("SELECT id FROM performance_observations WHERE import_row_id=:row")
                        .param("row", row.id())
                        .query(UUID.class)
                        .single());
    writeCountryObservations(observationId, values);
    writeNewAudienceQualityMetric(observationId, values);
  }

  private void writeCountryObservations(UUID observationId, Map<String, String> values) {
    Map<String, Double> countries = new LinkedHashMap<>();
    String explicitCode = first(values, "countrycode", "country_code");
    Double explicitPercentage = decimal(values, "countrypercentage", "country_percentage");
    if (explicitCode != null && explicitPercentage != null) {
      String normalizedCode = explicitCode.trim().toUpperCase(Locale.ROOT);
      if (normalizedCode.matches("[A-Z]{2}")) countries.put(normalizedCode, explicitPercentage);
    }
    Pattern[] patterns = {
      Pattern.compile("country_([a-z]{2})_(?:percentage|share)"),
      Pattern.compile("([a-z]{2})_(?:audience_)?(?:percentage|share)")
    };
    values.forEach(
        (key, raw) -> {
          String code = null;
          for (Pattern pattern : patterns) {
            var matcher = pattern.matcher(key);
            if (matcher.matches()) {
              code = matcher.group(1).toUpperCase(Locale.ROOT);
              break;
            }
          }
          if (code == null && key.matches("[a-z]{2}")) code = key.toUpperCase(Locale.ROOT);
          if (code == null) return;
          Double percentage = decimal(Map.of("value", raw), "value");
          if (percentage != null && percentage >= 0 && percentage <= 100) {
            countries.put(code, percentage);
          }
        });
    Long views = whole(values, "views");
    Instant observedAt =
        instant(
            first(values, "measurementtimestamp", "measurement_timestamp", "measuredat", "date"));
    countries.forEach(
        (code, percentage) -> {
          Long estimated =
              views == null ? null : Math.round(views.doubleValue() * percentage / 100.0);
          jdbc.sql(
                  """
                  INSERT INTO country_observations
                    (performance_observation_id,country_code,percentage,estimated_absolute_count,
                     denominator_metric,observed_at,source,data_quality_status)
                  VALUES (:observation,:country,:percentage,:estimated,:denominator,:observed,
                          'CSV','IMPORTED')
                  ON CONFLICT (performance_observation_id,country_code) DO NOTHING
                  """)
              .param("observation", observationId)
              .param("country", code)
              .param("percentage", percentage)
              .param("estimated", estimated, Types.BIGINT)
              .param("denominator", estimated == null ? null : "views_estimate", Types.VARCHAR)
              .param("observed", utc(observedAt), Types.TIMESTAMP_WITH_TIMEZONE)
              .update();
        });
  }

  private void writeNewAudienceQualityMetric(UUID observationId, Map<String, String> values) {
    Double nonFollower =
        decimal(
            values,
            "nonfollowerspercentage",
            "nonfollowers_percentage",
            "nonfollowerpercentage",
            "non_follower_percentage",
            "non_follower_view_percentage",
            "non_follower_share");
    Double usShare = countryPercentage(values, "US");
    if (nonFollower == null || usShare == null) return;
    double target = Math.max(discoveryScoreProperties.usAudienceTargetPercentage(), 0.0001);
    double normalizedUs = Math.min(100.0, usShare / target * 100.0);
    double score =
        discoveryScoreProperties.nonFollowerWeight() * nonFollower
            + discoveryScoreProperties.usAudienceWeight() * normalizedUs;
    Map<String, Object> components = new LinkedHashMap<>();
    components.put("nonFollowerShare", nonFollower);
    components.put("usAudienceShare", usShare);
    components.put("nonFollowerWeight", discoveryScoreProperties.nonFollowerWeight());
    components.put("usAudienceWeight", discoveryScoreProperties.usAudienceWeight());
    components.put("usAudienceTargetPercentage", target);
    jdbc.sql(
            """
            INSERT INTO derived_performance_metrics
              (performance_observation_id,metric_name,metric_value,algorithm_version,components,
               data_quality_status)
            VALUES (:observation,'new_audience_quality_score',:score,
                    'new-audience-quality-v1',CAST(:components AS jsonb),'IMPORTED')
            ON CONFLICT (performance_observation_id,metric_name,algorithm_version) DO NOTHING
            """)
        .param("observation", observationId)
        .param("score", Math.round(score * 100.0) / 100.0)
        .param("components", writeJson(components))
        .update();
  }

  private Double countryPercentage(Map<String, String> values, String countryCode) {
    String lower = countryCode.toLowerCase(Locale.ROOT);
    Double direct =
        decimal(
            values,
            lower,
            lower + "_percentage",
            lower + "_share",
            lower + "_audience_share",
            "country_" + lower + "_percentage",
            "country_" + lower + "_share");
    if (direct != null) return direct;
    String explicitCode = first(values, "countrycode", "country_code");
    return explicitCode != null && countryCode.equalsIgnoreCase(explicitCode.trim())
        ? decimal(values, "countrypercentage", "country_percentage")
        : null;
  }

  private void writeExplicitPlatformState(CommitRow row, String platform, UUID batchId) {
    Map<String, String> values = normalize(row.raw());
    String raw =
        first(values, "reachfurther", "reach_further", "meta_reach_further", "metareachfurther");
    if (raw == null) return;
    String normalized = raw.trim().toLowerCase(Locale.ROOT);
    String stateValue =
        switch (normalized) {
          case "true", "yes", "1", "active", "observed" -> "ACTIVE";
          case "false", "no", "0", "inactive", "not observed" -> "INACTIVE";
          case "unknown" -> "UNKNOWN";
          default ->
              throw new IllegalArgumentException(
                  "Unsupported explicit Reach Further value in import row: " + raw);
        };
    Instant observedAt =
        instant(first(values, "reachfurtherobservedat", "reach_further_observed_at"));
    platformStates.observe(
        row.videoId(),
        new PlatformStateService.ObservationRequest(
            null,
            platform,
            PlatformStateService.REACH_FURTHER,
            stateValue,
            observedAt,
            "CSV",
            batchId,
            1.0,
            "Explicit status field imported from " + batchId,
            null,
            null,
            false,
            null),
        "performance-import");
  }

  private Map<String, String> normalize(Map<String, String> values) {
    var normalized = new LinkedHashMap<String, String>();
    values.forEach((key, value) -> normalized.put(normalizeColumn(key), value));
    return normalized;
  }

  private Long whole(Map<String, String> values, String... keys) {
    String value = first(values, keys);
    if (value == null) return null;
    try {
      return Long.valueOf(value.replace(",", "").trim());
    } catch (NumberFormatException ignored) {
      return null;
    }
  }

  private Double decimal(Map<String, String> values, String... keys) {
    String value = first(values, keys);
    if (value == null) return null;
    try {
      return Double.valueOf(value.replace("%", "").replace(",", "").trim());
    } catch (NumberFormatException ignored) {
      return null;
    }
  }

  private Instant instant(String value) {
    if (value == null) return null;
    try {
      return Instant.parse(value);
    } catch (DateTimeParseException ignored) {
      try {
        return OffsetDateTime.parse(value).toInstant();
      } catch (DateTimeParseException alsoIgnored) {
        return null;
      }
    }
  }

  private OffsetDateTime utc(Instant value) {
    return value == null ? null : OffsetDateTime.ofInstant(value, java.time.ZoneOffset.UTC);
  }

  private Map<String, String> readMap(String source) {
    try {
      return json.readValue(source, new TypeReference<>() {});
    } catch (JacksonException error) {
      throw new IllegalStateException("Stored import row is invalid", error);
    }
  }

  private String normalizeColumn(String value) {
    return value.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_]", "");
  }

  private String normalizePlatform(String platform) {
    return platform == null || platform.isBlank() ? null : platform.toLowerCase(Locale.ROOT);
  }

  private String safeFilename(String name) {
    return Path.of(name).getFileName().toString().replaceAll("[^A-Za-z0-9._-]", "_");
  }

  private String writeJson(Object value) {
    try {
      return json.writeValueAsString(value);
    } catch (JacksonException error) {
      throw new IllegalStateException("Could not serialize import data", error);
    }
  }

  private long number(Map<String, Object> report, String key) {
    Object value = report.get(key);
    return value instanceof Number number ? number.longValue() : 0;
  }

  private record RowMatch(UUID videoId, UUID variantId) {}

  private record CommitRow(UUID id, UUID videoId, UUID variantId, Map<String, String> raw) {}

  public record ImportRow(
      UUID id,
      String sheet,
      int sourceRowNumber,
      Map<String, String> rawData,
      UUID matchedVideoId,
      UUID matchedVariantId,
      String matchStatus,
      Double matchConfidence,
      String matchReason) {}

  public record ImportPreview(
      UUID batchId,
      String filename,
      String sha256,
      List<String> columns,
      long rowCount,
      long matchedRows,
      long unresolvedRows,
      boolean duplicate,
      String status) {
    ImportPreview withDuplicate(boolean value) {
      return new ImportPreview(
          batchId, filename, sha256, columns, rowCount, matchedRows, unresolvedRows, value, status);
    }

    ImportPreview withStatus(String value) {
      return new ImportPreview(
          batchId,
          filename,
          sha256,
          columns,
          rowCount,
          matchedRows,
          unresolvedRows,
          duplicate,
          value);
    }
  }
}
