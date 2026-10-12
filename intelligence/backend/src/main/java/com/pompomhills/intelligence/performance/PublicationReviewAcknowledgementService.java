package com.pompomhills.intelligence.performance;

import java.time.Clock;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Operator acknowledgement of operational guard signals.
 *
 * <p>This service records that a human operator has reviewed a guard decision (e.g.
 * PUBLICATION_REVIEW_REQUIRED) before the next publication attempt. It is a descriptive
 * signal only and does not block rendering or publication execution.
 */
@Service
public class PublicationReviewAcknowledgementService {
  private final JdbcClient jdbc;
  private final Clock clock;

  public PublicationReviewAcknowledgementService(JdbcClient jdbc, Clock clock) {
    this.jdbc = jdbc;
    this.clock = clock;
  }

  /**
   * Record an operator acknowledgement for a guard decision.
   *
   * @param platform    the platform scope (e.g. "facebook")
   * @param guardDecisionId the operational guard decision being acknowledged
   * @param actor       the operator identity
   * @param notes       optional operator notes
   * @return the created acknowledgement view
   */
  @Transactional
  public AcknowledgementView acknowledge(String platform, UUID guardDecisionId, String actor, String notes) {
    if (platform == null || platform.isBlank()) {
      throw new IllegalArgumentException("platform is required");
    }
    if (guardDecisionId == null) {
      throw new IllegalArgumentException("guardDecisionId is required");
    }
    if (actor == null || actor.isBlank()) {
      throw new IllegalArgumentException("acknowledgedBy is required");
    }

    UUID id = UUID.randomUUID();
    OffsetDateTime now = OffsetDateTime.ofInstant(clock.instant(), ZoneOffset.UTC);

    jdbc.sql(
            """
            INSERT INTO publication_review_acknowledgements(id, platform, guard_decision_id, acknowledged_by, acknowledged_at, notes)
            VALUES (:id, :platform, :guardDecisionId, :actor, :now, :notes)
            """)
        .param("id", id)
        .param("platform", platform.toLowerCase(java.util.Locale.ROOT))
        .param("guardDecisionId", guardDecisionId)
        .param("actor", actor)
        .param("now", now)
        .param("notes", notes, java.sql.Types.VARCHAR)
        .update();

    return new AcknowledgementView(id, platform, guardDecisionId, actor, now.toInstant(), notes);
  }

  /**
   * Check whether a specific guard decision has been acknowledged.
   */
  @Transactional(readOnly = true)
  public boolean isAcknowledged(String platform, UUID guardDecisionId) {
    Integer count = jdbc.sql(
            """
            SELECT count(*) FROM publication_review_acknowledgements
            WHERE platform = :platform AND guard_decision_id = :guardDecisionId
            """)
        .param("platform", platform.toLowerCase(java.util.Locale.ROOT))
        .param("guardDecisionId", guardDecisionId)
        .query(Integer.class)
        .single();
    return count > 0;
  }

  /**
   * Return the latest acknowledgement for a platform, if any.
   */
  @Transactional(readOnly = true)
  public AcknowledgementView latestAcknowledgement(String platform) {
    return jdbc.sql(
            """
            SELECT id, platform, guard_decision_id, acknowledged_by, acknowledged_at, notes
            FROM publication_review_acknowledgements
            WHERE platform = :platform
            ORDER BY acknowledged_at DESC LIMIT 1
            """)
        .param("platform", platform.toLowerCase(java.util.Locale.ROOT))
        .query((rs, ignored) -> mapRow(rs))
        .optional()
        .orElse(null);
  }

  /**
   * Return all acknowledgements for a platform, ordered by acknowledged_at descending.
   */
  @Transactional(readOnly = true)
  public List<AcknowledgementView> listAcknowledgements(String platform) {
    return jdbc.sql(
            """
            SELECT id, platform, guard_decision_id, acknowledged_by, acknowledged_at, notes
            FROM publication_review_acknowledgements
            WHERE platform = :platform
            ORDER BY acknowledged_at DESC
            """)
        .param("platform", platform.toLowerCase(java.util.Locale.ROOT))
        .query((rs, ignored) -> mapRow(rs))
        .list();
  }

  private AcknowledgementView mapRow(java.sql.ResultSet rs) throws java.sql.SQLException {
    return new AcknowledgementView(
        rs.getObject("id", UUID.class),
        rs.getString("platform"),
        rs.getObject("guard_decision_id", UUID.class),
        rs.getString("acknowledged_by"),
        rs.getObject("acknowledged_at", OffsetDateTime.class).toInstant(),
        rs.getString("notes"));
  }

  public record AcknowledgementView(
      UUID id,
      String platform,
      UUID guardDecisionId,
      String acknowledgedBy,
      Instant acknowledgedAt,
      String notes) {}

  public record AcknowledgeRequest(
      UUID guardDecisionId,
      String notes) {}
}
