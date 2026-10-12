package com.pompom.creative.api.controller;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Exposes individual worker diagnostics for the Operations page.
 *
 * <p>Reads active leases, queued attempts, and error summaries from the canonical
 * render_attempts and publication_attempts tables so the operator can see which worker
 * instance owns which attempt and whether any lease has expired (indicating a crashed worker).
 */
@RestController
@RequestMapping("/api/v1/operational/workers")
@RequiredArgsConstructor
public class WorkerDiagnosticsController {

  private final JdbcTemplate jdbcTemplate;

  @Value("${pompom.render.worker.enabled:true}")
  private boolean renderWorkerEnabled;

  @Value("${pompom.render.worker.batch-size:5}")
  private int renderWorkerBatchSize;

  @Value("${pompom.render.worker.lease-duration:PT15M}")
  private String renderWorkerLeaseDuration;

  @Value("${pompom.publication.worker.enabled:true}")
  private boolean publicationWorkerEnabled;

  @Value("${pompom.publication.worker.batch-size:5}")
  private int publicationWorkerBatchSize;

  @Value("${pompom.publication.worker.lease-duration:PT15M}")
  private String publicationWorkerLeaseDuration;

  @GetMapping
  public WorkerDiagnosticsSnapshot diagnostics() {
    return new WorkerDiagnosticsSnapshot(
        Instant.now(),
        new WorkerStatus(
            "render",
            renderWorkerEnabled,
            renderWorkerBatchSize,
            renderWorkerLeaseDuration,
            getRenderActiveLeases(),
            getRenderStageCounts(),
            getRenderErrors()),
        new WorkerStatus(
            "publication",
            publicationWorkerEnabled,
            publicationWorkerBatchSize,
            publicationWorkerLeaseDuration,
            getPublicationActiveLeases(),
            getPublicationStageCounts(),
            getPublicationErrors()));
  }

  private List<Map<String, Object>> getRenderActiveLeases() {
    return jdbcTemplate.queryForList(
        """
        SELECT ra.id,
               ra.render_job_id,
               ra.attempt_number,
               ra.stage,
               ra.lease_owner,
               ra.lease_expires_at,
               ra.lease_heartbeat_at,
               ra.error_code,
               ra.error_message,
               CASE
                 WHEN ra.lease_expires_at < NOW() THEN 'EXPIRED'
                 ELSE 'ACTIVE'
               END AS lease_state
        FROM render_attempts ra
        WHERE ra.lease_owner IS NOT NULL
          AND ra.lease_expires_at IS NOT NULL
          AND ra.stage NOT IN ('COMPLETE', 'FAILED', 'ABANDONED')
        ORDER BY ra.lease_expires_at
        """);
  }

  private Map<String, Integer> getRenderStageCounts() {
    List<Map<String, Object>> rows = jdbcTemplate.queryForList(
        """
        SELECT stage, COUNT(*) AS cnt
        FROM render_attempts
        GROUP BY stage
        ORDER BY stage
        """);
    return rows.stream().collect(
        java.util.stream.Collectors.toMap(
            r -> (String) r.get("stage"),
            r -> ((Number) r.get("cnt")).intValue()));
  }

  private List<Map<String, Object>> getRenderErrors() {
    return jdbcTemplate.queryForList(
        """
        SELECT ra.id,
               ra.render_job_id,
               ra.attempt_number,
               ra.stage,
               ra.error_code,
               ra.error_message,
               ra.completed_at
        FROM render_attempts ra
        WHERE ra.error_code IS NOT NULL
        ORDER BY ra.completed_at DESC
        LIMIT 20
        """);
  }

  private List<Map<String, Object>> getPublicationActiveLeases() {
    return jdbcTemplate.queryForList(
        """
        SELECT pa.id,
               pa.publication_job_id,
               pa.attempt_number,
               pa.stage,
               pa.lease_owner,
               pa.lease_expires_at,
               pa.error_code,
               pa.error_message,
               CASE
                 WHEN pa.lease_expires_at < NOW() THEN 'EXPIRED'
                 ELSE 'ACTIVE'
               END AS lease_state
        FROM publication_attempts pa
        WHERE pa.lease_owner IS NOT NULL
          AND pa.lease_expires_at IS NOT NULL
          AND pa.stage NOT IN ('COMPLETE', 'FAILED')
        ORDER BY pa.lease_expires_at
        """);
  }

  private Map<String, Integer> getPublicationStageCounts() {
    List<Map<String, Object>> rows = jdbcTemplate.queryForList(
        """
        SELECT stage, COUNT(*) AS cnt
        FROM publication_attempts
        GROUP BY stage
        ORDER BY stage
        """);
    return rows.stream().collect(
        java.util.stream.Collectors.toMap(
            r -> (String) r.get("stage"),
            r -> ((Number) r.get("cnt")).intValue()));
  }

  private List<Map<String, Object>> getPublicationErrors() {
    return jdbcTemplate.queryForList(
        """
        SELECT pa.id,
               pa.publication_job_id,
               pa.attempt_number,
               pa.stage,
               pa.error_code,
               pa.error_message,
               pa.completed_at
        FROM publication_attempts pa
        WHERE pa.error_code IS NOT NULL
        ORDER BY pa.completed_at DESC
        LIMIT 20
        """);
  }

  public record WorkerDiagnosticsSnapshot(
      Instant observedAt,
      WorkerStatus render,
      WorkerStatus publication) {}

  public record WorkerStatus(
      String name,
      boolean enabled,
      int batchSize,
      String leaseDuration,
      List<Map<String, Object>> activeLeases,
      Map<String, Integer> stageCounts,
      List<Map<String, Object>> recentErrors) {}
}
