package com.pompomhills.intelligence.video.workbench;

import com.pompomhills.intelligence.video.VideoService;
import com.pompomhills.intelligence.video.job.AnalysisJobService;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import static com.pompomhills.intelligence.video.workbench.VideoAnalysisWorkbenchDtos.*;

@Service
public class VideoAnalysisWorkbenchService {
  private final JdbcClient jdbc;
  private final AnalysisJobService jobs;

  public VideoAnalysisWorkbenchService(JdbcClient jdbc, AnalysisJobService jobs) {
    this.jdbc = jdbc;
    this.jobs = jobs;
  }

  @Transactional(readOnly = true)
  public PageResponse page(int page, int size, String analysisStatus, String triage,
      String publicationState, UUID characterId, String characterRole, Boolean unresolvedCharacter, String query, String sort,
      String direction) {
    int safePage = Math.max(0, page);
    int safeSize = Math.min(100, Math.max(1, size));
    String where = whereClause(analysisStatus, triage, publicationState, characterId, characterRole, unresolvedCharacter, query);
    String order = orderBy(sort, direction);
    var params = params(analysisStatus, triage, publicationState, characterId, characterRole, unresolvedCharacter, query);
    long total = scalar("SELECT count(*) " + fromClause() + where, params);
    List<Row> rows = jdbc.sql(
            """
            SELECT v.id,v.original_filename,v.relative_path,v.duration_ms,v.width,v.height,v.status,v.ingested_at,
                   ca.analysis_version,ca.classification,ca.confidence,ca.reason,
                   CASE WHEN aj.state IN ('QUEUED','RUNNING') THEN 'RUNNING'
                        WHEN aj.state='FAILED' THEN 'FAILED'
                        WHEN ca.id IS NULL THEN 'MISSING'
                        WHEN ca.analysis_version=:current THEN 'CURRENT' ELSE 'STALE' END AS analysis_status,
                   CASE WHEN aj.state IN ('QUEUED','RUNNING','FAILED') OR ca.id IS NULL THEN 'INCOMPLETE'
                        WHEN ca.classification='BAD' THEN 'REGENERATE'
                        WHEN ca.classification='AVERAGE_FIXABLE' THEN 'EDIT_PLAN'
                        WHEN ca.classification IN ('GOOD','WINNER_CANDIDATE') THEN 'READY'
                        ELSE 'REVIEW' END AS triage,
                   CASE WHEN pub.publications > 0 THEN 'PUBLISHED' ELSE 'UNPUBLISHED' END AS publication_state,
                   perf.observed_views,perf.observation_count
            FROM videos v
            LEFT JOIN LATERAL (SELECT a.* FROM creative_analyses a WHERE a.video_id=v.id
                                ORDER BY (a.analysis_version=:current) DESC,a.created_at DESC LIMIT 1) ca ON true
            LEFT JOIN LATERAL (SELECT j.state FROM analysis_jobs j WHERE j.video_id=v.id
                               ORDER BY j.created_at DESC LIMIT 1) aj ON true
            LEFT JOIN LATERAL (SELECT count(*) AS publications FROM video_publications p WHERE p.video_id=v.id) pub ON true
            LEFT JOIN LATERAL (SELECT max(o.views) AS observed_views,count(*)::int AS observation_count
                               FROM effective_performance_observations o WHERE o.video_id=v.id) perf ON true
            """ + where + order + " LIMIT :limit OFFSET :offset")
        .params(params)
        .param("current", VideoService.CURRENT_ANALYSIS_VERSION)
        .param("limit", safeSize)
        .param("offset", safePage * safeSize)
        .query((rs, ignored) -> mapRow(rs))
        .list();
    rows = attachCharacters(rows);
    return new PageResponse(rows, safePage, safeSize, total,
        (int) Math.ceil(total / (double) safeSize), summary(where, params));
  }

  @Transactional
  public BulkResponse bulk(BulkRequest request) {
    List<UUID> ids = request.videoIds() == null ? new ArrayList<>() : new ArrayList<>(request.videoIds());
    if (request.allMatching()) ids = matchingIds(request);
    int accepted = 0, skipped = 0, running = 0, failed = 0;
    List<UUID> jobsCreated = new ArrayList<>();
    for (UUID id : ids) {
      try {
        var result = jobs.enqueue(id, request.reanalyzeSelected());
        if (result.created()) { accepted++; if (result.job() != null) jobsCreated.add(result.job().id()); }
        else if (result.job() != null && ("QUEUED".equals(result.job().state()) || "RUNNING".equals(result.job().state()))) running++;
        else skipped++;
      } catch (RuntimeException error) { failed++; }
    }
    return new BulkResponse(ids.size(), accepted, skipped, running, failed, jobsCreated);
  }

  private List<UUID> matchingIds(BulkRequest r) {
    return jdbc.sql("SELECT v.id " + fromClause() + whereClause(r.analysisStatus(), r.triage(), r.publicationState(), r.characterId(), r.characterRole(), r.unresolvedCharacter(), r.query()) + " ORDER BY v.ingested_at DESC")
        .params(params(r.analysisStatus(), r.triage(), r.publicationState(), r.characterId(), r.characterRole(), r.unresolvedCharacter(), r.query()))
        .query(UUID.class).list();
  }

  private Summary summary(String where, java.util.Map<String,Object> params) {
    return jdbc.sql("""
        SELECT count(*) total,
          count(*) FILTER (WHERE ca.id IS NOT NULL AND ca.analysis_version=:current AND (aj.state IS NULL OR aj.state='COMPLETED')) current_count,
          count(*) FILTER (WHERE ca.id IS NOT NULL AND ca.analysis_version<>:current AND (aj.state IS NULL OR aj.state='COMPLETED')) stale,
          count(*) FILTER (WHERE ca.id IS NULL AND (aj.state IS NULL OR aj.state='COMPLETED')) missing,
          count(*) FILTER (WHERE aj.state IN ('QUEUED','RUNNING')) running,
          count(*) FILTER (WHERE aj.state='FAILED') failed,
          count(*) FILTER (WHERE (aj.state IS NULL OR aj.state='COMPLETED') AND ca.classification IN ('GOOD','WINNER_CANDIDATE')) ready,
          count(*) FILTER (WHERE (aj.state IS NULL OR aj.state='COMPLETED') AND ca.classification IS NOT NULL AND ca.classification NOT IN ('BAD','AVERAGE_FIXABLE','GOOD','WINNER_CANDIDATE')) review,
          count(*) FILTER (WHERE (aj.state IS NULL OR aj.state='COMPLETED') AND ca.classification='BAD') regenerate,
          count(*) FILTER (WHERE (aj.state IS NULL OR aj.state='COMPLETED') AND ca.classification='AVERAGE_FIXABLE') edit_plan,
          count(*) FILTER (WHERE aj.state IN ('QUEUED','RUNNING','FAILED') OR ca.id IS NULL) incomplete
        """ + fromClause() + where
        ).params(params).param("current", VideoService.CURRENT_ANALYSIS_VERSION)
        .query((rs, ignored) -> new Summary(rs.getLong("total"),rs.getLong("current_count"),rs.getLong("stale"),rs.getLong("missing"),rs.getLong("running"),rs.getLong("failed"),rs.getLong("ready"),rs.getLong("review"),rs.getLong("regenerate"),rs.getLong("edit_plan"),rs.getLong("incomplete"))).single();
  }

  private List<Row> attachCharacters(List<Row> rows) {
    for (int i=0;i<rows.size();i++) {
      Row row=rows.get(i);
      List<CharacterAssociation> chars=jdbc.sql("SELECT c.id,c.name,vc.participation,vc.role,vc.association_source,vc.confidence,vc.evidence_reference FROM video_characters vc JOIN characters c ON c.id=vc.character_id WHERE vc.video_id=:id ORDER BY CASE WHEN vc.participation='PRIMARY' THEN 0 ELSE 1 END,c.name")
          .param("id",row.id()).query((rs, ignored) -> new CharacterAssociation(rs.getObject("id",UUID.class),rs.getString("name"),rs.getString("participation"),rs.getString("role"),rs.getString("association_source"),rs.getString("confidence"),rs.getString("evidence_reference"))).list();
      rows.set(i,new Row(row.id(),row.title(),row.relativePath(),row.durationMs(),row.width(),row.height(),row.videoStatus(),row.ingestedAt(),row.analysisStatus(),row.analysisVersion(),row.classification(),row.confidence(),row.reason(),row.triage(),row.publicationState(),row.observedViews(),row.observationCount(),chars));
    }
    return rows;
  }

  private Row mapRow(ResultSet rs) throws SQLException { return new Row(rs.getObject("id",UUID.class),rs.getString("original_filename"),rs.getString("relative_path"),rs.getLong("duration_ms"),rs.getInt("width"),rs.getInt("height"),rs.getString("status"),instant(rs,"ingested_at"),rs.getString("analysis_status"),rs.getString("analysis_version"),rs.getString("classification"), (Double)rs.getObject("confidence"),rs.getString("reason"),rs.getString("triage"),rs.getString("publication_state"),(Long)rs.getObject("observed_views"),(Integer)rs.getObject("observation_count"),List.of()); }
  private Instant instant(ResultSet rs,String c)throws SQLException { var value=rs.getObject(c,java.time.OffsetDateTime.class); return value==null?null:value.toInstant(); }
  private long scalar(String sql, java.util.Map<String,Object> params) { return jdbc.sql(sql).params(params).query(Long.class).single(); }
  private String fromClause() { return """
      FROM videos v
      LEFT JOIN LATERAL (SELECT a.* FROM creative_analyses a WHERE a.video_id=v.id ORDER BY (a.analysis_version=:current) DESC,a.created_at DESC LIMIT 1) ca ON true
      LEFT JOIN LATERAL (SELECT j.state FROM analysis_jobs j WHERE j.video_id=v.id ORDER BY j.created_at DESC LIMIT 1) aj ON true
      LEFT JOIN LATERAL (SELECT count(*) AS publications FROM video_publications p WHERE p.video_id=v.id) pub ON true
      LEFT JOIN LATERAL (SELECT max(o.views) AS observed_views,count(*)::int AS observation_count FROM effective_performance_observations o WHERE o.video_id=v.id) perf ON true
      """; }
  private java.util.Map<String,Object> params(String a,String t,String p,UUID c,String r,Boolean u,String q){var m=new java.util.HashMap<String,Object>();m.put("current",VideoService.CURRENT_ANALYSIS_VERSION);if(a!=null&&!a.isBlank())m.put("analysisStatus",a);if(t!=null&&!t.isBlank())m.put("triage",t);if(p!=null&&!p.isBlank())m.put("publicationState",p);if(c!=null)m.put("characterId",c);if(r!=null&&!r.isBlank())m.put("characterRole",r);if(u!=null)m.put("unresolvedCharacter",u);if(q!=null&&!q.isBlank())m.put("query",q.toLowerCase());return m;}
  private String whereClause(String a,String t,String p,UUID c,String r,Boolean u,String q){StringBuilder s=new StringBuilder(" WHERE 1=1 ");if(a!=null&&!a.isBlank())s.append(" AND (CASE WHEN aj.state IN ('QUEUED','RUNNING') THEN 'RUNNING' WHEN aj.state='FAILED' THEN 'FAILED' WHEN ca.id IS NULL THEN 'MISSING' WHEN ca.analysis_version=:current THEN 'CURRENT' ELSE 'STALE' END)=:analysisStatus");if(t!=null&&!t.isBlank())s.append(" AND (CASE WHEN aj.state IN ('QUEUED','RUNNING','FAILED') OR ca.id IS NULL THEN 'INCOMPLETE' WHEN ca.classification='BAD' THEN 'REGENERATE' WHEN ca.classification='AVERAGE_FIXABLE' THEN 'EDIT_PLAN' WHEN ca.classification IN ('GOOD','WINNER_CANDIDATE') THEN 'READY' ELSE 'REVIEW' END)=:triage");if(p!=null&&!p.isBlank())s.append(" AND (CASE WHEN pub.publications>0 THEN 'PUBLISHED' ELSE 'UNPUBLISHED' END)=:publicationState");if(c!=null)s.append(" AND EXISTS (SELECT 1 FROM video_characters fvc WHERE fvc.video_id=v.id AND fvc.character_id=:characterId)");if(r!=null&&!r.isBlank())s.append(" AND EXISTS (SELECT 1 FROM video_characters fvr WHERE fvr.video_id=v.id AND fvr.role=:characterRole)");if(Boolean.TRUE.equals(u))s.append(" AND NOT EXISTS (SELECT 1 FROM video_characters fvu WHERE fvu.video_id=v.id)");if(q!=null&&!q.isBlank())s.append(" AND (lower(v.original_filename) LIKE '%'||:query||'%' OR lower(v.relative_path) LIKE '%'||:query||'%')");return s.toString();}
  private String orderBy(String sort,String direction){String col=switch(sort==null?"date":sort){case "title"->"v.original_filename";case "status"->"v.status";case "analysis"->"analysis_status";case "triage"->"triage";case "views"->"perf.observed_views";default->"v.ingested_at";};return " ORDER BY "+col+(("asc".equalsIgnoreCase(direction))?" ASC":" DESC")+",v.id";}
}
