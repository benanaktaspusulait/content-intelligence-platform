package com.pompomhills.intelligence.video.job;

import com.pompomhills.intelligence.video.VideoService;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.ObjectMapper;

@Service
public class AnalysisJobService {
  private final JdbcClient jdbc;
  private final VideoService videos;
  private final ObjectMapper json;

  public AnalysisJobService(JdbcClient jdbc, VideoService videos, ObjectMapper json) {
    this.jdbc = jdbc;
    this.videos = videos;
    this.json = json;
  }

  public EnqueueResult enqueue(UUID videoId) {
    boolean exists =
        jdbc.sql("SELECT EXISTS(SELECT 1 FROM videos WHERE id=:id)")
            .param("id", videoId)
            .query(Boolean.class)
            .single();
    if (!exists) throw new IllegalArgumentException("Video not found: " + videoId);

    if (videos.hasCurrentAnalysis(videoId)) {
      return new EnqueueResult(false, null);
    }

    var active = findActiveByVideoId(videoId);
    if (active.isPresent()) {
      return new EnqueueResult(false, active.get());
    }

    UUID id = UUID.randomUUID();
    try {
      jdbc.sql(
              """
              INSERT INTO analysis_jobs (id,video_id,job_type,state,request_payload)
              VALUES (:id,:video,'VIDEO_ANALYSIS','QUEUED',CAST(:payload AS jsonb))
              """)
          .param("id", id)
          .param("video", videoId)
          .param("payload", "{\"contractVersion\":\"v1\",\"analysisVersion\":\"sampled-visual-motion-v3\"}")
          .update();
    } catch (DataIntegrityViolationException raceLoss) {
      // Another concurrent request won the V34 unique-index race and already created the active
      // job; fetch and return that one instead of failing the request.
      return new EnqueueResult(
          false,
          findActiveByVideoId(videoId)
              .orElseThrow(
                  () ->
                      new IllegalStateException(
                          "Enqueue race lost but no active job found for video " + videoId,
                          raceLoss)));
    }
    return new EnqueueResult(true, get(id));
  }

  public Optional<JobView> findActiveByVideoId(UUID videoId) {
    return jdbc.sql(
            """
            SELECT id,video_id,job_type,state,attempts,max_attempts,error_message,
                   created_at,started_at,completed_at
            FROM analysis_jobs WHERE video_id=:video AND state IN ('QUEUED','RUNNING')
            """)
        .param("video", videoId)
        .query((rs, ignored) -> map(rs))
        .optional();
  }

  public Optional<JobView> findLatestByVideoId(UUID videoId) {
    return jdbc.sql(
            """
            SELECT id,video_id,job_type,state,attempts,max_attempts,error_message,
                   created_at,started_at,completed_at
            FROM analysis_jobs WHERE video_id=:video ORDER BY created_at DESC LIMIT 1
            """)
        .param("video", videoId)
        .query((rs, ignored) -> map(rs))
        .optional();
  }

  public JobView get(UUID id) {
    return jdbc.sql(
            """
            SELECT id,video_id,job_type,state,attempts,max_attempts,error_message,
                   created_at,started_at,completed_at
            FROM analysis_jobs WHERE id=:id
            """)
        .param("id", id)
        .query((rs, ignored) -> map(rs))
        .optional()
        .orElseThrow(() -> new IllegalArgumentException("Job not found: " + id));
  }

  public JobView retry(UUID id) {
    int changed =
        jdbc.sql(
                """
                UPDATE analysis_jobs SET state='QUEUED',error_message=NULL,available_at=now()
                WHERE id=:id AND state='FAILED' AND attempts<max_attempts
                """)
            .param("id", id)
            .update();
    if (changed == 0) throw new IllegalStateException("Job is not retryable");
    return get(id);
  }

  @Scheduled(fixedDelayString = "${pompom.jobs.poll-delay-ms:2000}")
  public void processNext() {
    var claimed =
        jdbc.sql(
                """
                WITH candidate AS (
                  SELECT id FROM analysis_jobs
                  WHERE state='QUEUED' AND available_at<=now() AND attempts<max_attempts
                  ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1
                )
                UPDATE analysis_jobs j
                SET state='RUNNING',attempts=attempts+1,started_at=now()
                FROM candidate WHERE j.id=candidate.id
                RETURNING j.id,j.video_id
                """)
            .query(
                (rs, ignored) ->
                    new ClaimedJob(
                        rs.getObject("id", UUID.class), rs.getObject("video_id", UUID.class)))
            .optional();
    if (claimed.isEmpty()) return;
    var job = claimed.get();
    try {
      var result = videos.analyse(job.videoId());
      jdbc.sql(
              """
              UPDATE analysis_jobs
              SET state='COMPLETED',result_payload=CAST(:result AS jsonb),completed_at=now()
              WHERE id=:id
              """)
          .param("id", job.id())
          .param(
              "result",
              writeJson(
                  Map.of(
                      "analysisId", result.analysisId(),
                      "videoId", result.videoId(),
                      "classification", result.classification())))
          .update();
    } catch (RuntimeException error) {
      jdbc.sql(
              """
              UPDATE analysis_jobs
              SET state='FAILED',error_message=:error,completed_at=now(),
                  available_at=now() + interval '10 seconds'
              WHERE id=:id
              """)
          .param("id", job.id())
          .param("error", error.getMessage())
          .update();
    }
  }

  private JobView map(java.sql.ResultSet rs) throws java.sql.SQLException {
    return new JobView(
        rs.getObject("id", UUID.class),
        rs.getObject("video_id", UUID.class),
        rs.getString("job_type"),
        rs.getString("state"),
        rs.getInt("attempts"),
        rs.getInt("max_attempts"),
        rs.getString("error_message"),
        instant(rs, "created_at"),
        instant(rs, "started_at"),
        instant(rs, "completed_at"));
  }

  private java.time.Instant instant(java.sql.ResultSet rs, String column)
      throws java.sql.SQLException {
    OffsetDateTime value = rs.getObject(column, OffsetDateTime.class);
    return value == null ? null : value.toInstant();
  }

  private String writeJson(Object value) {
    try {
      return json.writeValueAsString(value);
    } catch (JacksonException error) {
      throw new IllegalStateException("Could not serialize job result", error);
    }
  }

  private record ClaimedJob(UUID id, UUID videoId) {}

  public record EnqueueResult(boolean created, JobView job) {}

  public record JobView(
      UUID id,
      UUID videoId,
      String type,
      String state,
      int attempts,
      int maxAttempts,
      String error,
      java.time.Instant createdAt,
      java.time.Instant startedAt,
      java.time.Instant completedAt) {}
}
