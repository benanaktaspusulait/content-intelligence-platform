package com.pompomhills.intelligence.performance;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class InterventionService {
  public static final String MANUAL_ENGAGEMENT = "MANUAL_ENGAGEMENT";
  public static final String MANUAL_DISTRIBUTION = "MANUAL_DISTRIBUTION";
  private final JdbcClient jdbc;

  public InterventionService(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Transactional
  public InterventionView record(UUID videoId, InterventionRequest request, String actor) {
    if (request.eventTime() == null) throw new IllegalArgumentException("eventTime is required");
    String platform = request.platform().toLowerCase(Locale.ROOT);
    String eventType = request.eventType() == null ? MANUAL_ENGAGEMENT : request.eventType();
    if (!MANUAL_ENGAGEMENT.equals(eventType) && !MANUAL_DISTRIBUTION.equals(eventType)) {
      throw new IllegalArgumentException("Unsupported intervention event type: " + eventType);
    }
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO intervention_events(id,video_id,platform,event_type,event_time,details)
            VALUES (:id,:video,:platform,:type,:time,
              jsonb_strip_nulls(jsonb_build_object('notes',:notes,'viewsBefore',CAST(:before AS bigint),
                'viewsAfter',CAST(:after AS bigint),'channelType',:channelType,
                'externalChannelRef',:externalChannelRef,'externalChannelLabel',:externalChannelLabel,
                'campaignTag',:campaignTag)))
            """)
        .param("id", id)
        .param("video", videoId)
        .param("platform", platform)
        .param("type", eventType)
        .param("time", OffsetDateTime.ofInstant(request.eventTime(), ZoneOffset.UTC))
        .param("notes", request.notes(), java.sql.Types.VARCHAR)
        .param("before", request.viewsBefore(), java.sql.Types.BIGINT)
        .param("after", request.viewsAfter(), java.sql.Types.BIGINT)
        .param("channelType", request.channelType(), java.sql.Types.VARCHAR)
        .param("externalChannelRef", request.externalChannelRef(), java.sql.Types.VARCHAR)
        .param("externalChannelLabel", request.externalChannelLabel(), java.sql.Types.VARCHAR)
        .param("campaignTag", request.campaignTag(), java.sql.Types.VARCHAR)
        .update();
    jdbc.sql(
            """
            INSERT INTO audit_events(actor,action,entity_type,entity_id,reason,new_state)
            VALUES (:actor,:auditAction,'INTERVENTION_EVENT',:id,:notes,
              jsonb_build_object('videoId',CAST(:video AS uuid),'platform',:platform,'eventTime',:time))
            """)
        .param("actor", actor)
        .param("auditAction", eventType + "_INTERVENTION_RECORDED")
        .param("id", id)
        .param("video", videoId)
        .param("platform", platform)
        .param("time", request.eventTime().toString())
        .param("notes", request.notes())
        .update();
    return byId(id);
  }

  @Transactional(readOnly = true)
  public List<InterventionView> list(UUID videoId, String platform) {
    return jdbc.sql(
            """
            SELECT id,video_id,platform,event_type,event_time,details->>'notes' notes,
              NULLIF(details->>'viewsBefore','')::bigint views_before,
              NULLIF(details->>'viewsAfter','')::bigint views_after
            FROM intervention_events
            WHERE video_id=:video AND platform=:platform ORDER BY event_time
            """)
        .param("video", videoId)
        .param("platform", platform.toLowerCase(Locale.ROOT))
        .query(this::map)
        .list();
  }

  @Transactional(readOnly = true)
  public Instant firstAtOrBefore(UUID videoId, String platform, Instant cutoff) {
    return jdbc.sql(
            """
            SELECT min(event_time) FROM intervention_events
            WHERE video_id=:video AND platform=:platform AND event_time<=:cutoff
            """)
        .param("video", videoId)
        .param("platform", platform.toLowerCase(Locale.ROOT))
        .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
        .query(OffsetDateTime.class)
        .optional()
        .map(OffsetDateTime::toInstant)
        .orElse(null);
  }

  private InterventionView byId(UUID id) {
    return jdbc.sql(
            """
            SELECT id,video_id,platform,event_type,event_time,details->>'notes' notes,
              NULLIF(details->>'viewsBefore','')::bigint views_before,
              NULLIF(details->>'viewsAfter','')::bigint views_after
            FROM intervention_events WHERE id=:id
            """)
        .param("id", id)
        .query(this::map)
        .single();
  }

  private InterventionView map(java.sql.ResultSet rs, int ignored) throws java.sql.SQLException {
    long before = rs.getLong("views_before");
    Long viewsBefore = rs.wasNull() ? null : before;
    long after = rs.getLong("views_after");
    Long viewsAfter = rs.wasNull() ? null : after;
    return new InterventionView(
        rs.getObject("id", UUID.class),
        rs.getObject("video_id", UUID.class),
        rs.getString("platform"),
        rs.getString("event_type"),
        rs.getObject("event_time", OffsetDateTime.class).toInstant(),
        rs.getString("notes"),
        viewsBefore,
        viewsAfter);
  }

  public record InterventionRequest(
      String platform, Instant eventTime, String notes, Long viewsBefore, Long viewsAfter,
      String eventType, String channelType, String externalChannelRef,
      String externalChannelLabel, String campaignTag) {
    public InterventionRequest(
        String platform, Instant eventTime, String notes, Long viewsBefore, Long viewsAfter) {
      this(platform, eventTime, notes, viewsBefore, viewsAfter, null, null, null, null, null);
    }
  }

  public record InterventionView(
      UUID id,
      UUID videoId,
      String platform,
      String eventType,
      Instant eventTime,
      String notes,
      Long viewsBefore,
      Long viewsAfter) {}
}
