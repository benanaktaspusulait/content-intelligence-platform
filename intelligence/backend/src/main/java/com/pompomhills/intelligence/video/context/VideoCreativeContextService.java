package com.pompomhills.intelligence.video.context;

import com.pompomhills.intelligence.video.context.VideoCreativeContextDtos.CharacterContext;
import com.pompomhills.intelligence.video.context.VideoCreativeContextDtos.PromptContext;
import com.pompomhills.intelligence.video.context.VideoCreativeContextDtos.Response;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import com.pompomhills.intelligence.video.VideoEntity;
import com.pompomhills.intelligence.video.VideoRepository;
import com.pompomhills.intelligence.video.prompt.PromptSourceResolution;
import com.pompomhills.intelligence.video.prompt.VideoPromptSourceResolver;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VideoCreativeContextService {
  private final JdbcClient jdbc;
  private final VideoRepository videos;
  private final VideoPromptSourceResolver promptResolver;

  public VideoCreativeContextService(JdbcClient jdbc, VideoRepository videos,
      VideoPromptSourceResolver promptResolver) {
    this.jdbc = jdbc;
    this.videos = videos;
    this.promptResolver = promptResolver;
  }

  @Transactional(readOnly = true)
  public Response get(UUID videoId) {
    List<CharacterContext> characters = jdbc.sql("""
        SELECT c.id,c.name,vc.participation,vc.role,
               vc.screen_time_ratio,vc.action_share,vc.speaking_share,
               vc.association_source,vc.confidence,vc.source_prompt_path,
               vc.resolver_version,vc.evidence_reference,vc.manually_confirmed
        FROM video_characters vc
        JOIN characters c ON c.id=vc.character_id
        WHERE vc.video_id=:videoId
        ORDER BY CASE WHEN vc.participation='PRIMARY' THEN 0 ELSE 1 END,c.name
        """).param("videoId", videoId)
        .query((rs, ignored) -> new CharacterContext(
            rs.getObject("id", UUID.class), rs.getString("name"),
            rs.getString("participation"), rs.getString("role"),
            nullableDouble(rs, "screen_time_ratio"),
            nullableDouble(rs, "action_share"),
            nullableDouble(rs, "speaking_share"),
            rs.getString("association_source"), rs.getString("confidence"),
            rs.getString("source_prompt_path"), rs.getString("resolver_version"),
            rs.getString("evidence_reference"), rs.getBoolean("manually_confirmed")))
        .list();

    PromptContext prompt = jdbc.sql("""
        SELECT linked.content_id,linked.title,linked.type,linked.status,
               linked.prompt_version_id,linked.version_number,linked.raw_text,
               linked.parsed_ir,linked.source_path,linked.created_at,linked.linkage
        FROM videos v
        LEFT JOIN LATERAL (
          SELECT c.id content_id,c.title,c.type::text,c.status::text,
                 pv.id prompt_version_id,pv.version_number,pv.raw_text,pv.parsed_ir::text,
                 pv.source_path,pv.created_at,'RENDER_ASSET' linkage
          FROM render_assets ra
          JOIN render_jobs rj ON rj.id=ra.render_job_id
          JOIN contents c ON c.id=rj.content_id
          JOIN prompt_versions pv ON pv.id=rj.prompt_version_id
          WHERE ra.relative_path=v.relative_path
            AND ra.asset_type='VIDEO'
          ORDER BY ra.is_current DESC,ra.created_at DESC,pv.version_number DESC
          LIMIT 1
        ) linked ON true
        WHERE v.id=:videoId AND linked.content_id IS NOT NULL
        """).param("videoId", videoId)
        .query((rs, ignored) -> mapPrompt(rs))
        .optional().orElse(null);

    if (prompt == null) {
      prompt = jdbc.sql("""
          SELECT c.id content_id,c.title,c.type::text,c.status::text,
                 pv.id prompt_version_id,pv.version_number,pv.raw_text,pv.parsed_ir::text,
                 pv.source_path,pv.created_at,'FOLDER_SOURCE' linkage
          FROM videos v
          JOIN contents c ON regexp_replace(c.source_path,'/[^/]+$','')=regexp_replace(v.relative_path,'/[^/]+$','')
          JOIN prompt_versions pv ON pv.content_id=c.id
          WHERE v.id=:videoId
          ORDER BY pv.version_number DESC,pv.created_at DESC
          LIMIT 1
          """).param("videoId", videoId)
          .query((rs, ignored) -> mapPrompt(rs))
          .optional().orElse(null);
    }

    if (prompt == null) {
      VideoEntity video = videos.findById(videoId).orElse(null);
      if (video != null) {
        PromptSourceResolution resolution = promptResolver.resolve(video);
        if (resolution.matched()) {
          prompt = new PromptContext(null, resolution.promptPath(), "REEL", "SOURCE_RESOLVED",
              null, null, resolution.promptText(), null, resolution.promptPath(), null,
              "FOLDER_SOURCE_RESOLUTION");
        }
      }
    }

    String evidenceStatus = prompt == null ? "CHARACTER_DATA_ONLY" : "CHARACTER_AND_PROMPT_LINKED";
    return new Response(videoId, characters, prompt, evidenceStatus);
  }

  private PromptContext mapPrompt(ResultSet rs) throws SQLException {
    return new PromptContext(
        rs.getLong("content_id"), rs.getString("title"), rs.getString("type"),
        rs.getString("status"), rs.getLong("prompt_version_id"),
        rs.getInt("version_number"), rs.getString("raw_text"),
        rs.getString("parsed_ir"), rs.getString("source_path"),
        instant(rs, "created_at"), rs.getString("linkage"));
  }

  private Instant instant(ResultSet rs, String column) throws SQLException {
    var timestamp = rs.getTimestamp(column);
    return timestamp == null ? null : timestamp.toInstant();
  }

  private Double nullableDouble(ResultSet rs, String column) throws SQLException {
    double value = rs.getDouble(column);
    return rs.wasNull() ? null : value;
  }
}
