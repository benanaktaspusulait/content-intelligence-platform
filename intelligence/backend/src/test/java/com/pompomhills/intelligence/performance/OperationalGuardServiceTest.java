package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Deterministic tests for operational guard evaluation and publication review acknowledgement.
 *
 * <p>Covers: evidence filtering, maturity, policy changes, render independence, and auditability.
 */
@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class OperationalGuardServiceTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom");

  @DynamicPropertySource
  static void registerPgProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add("spring.datasource.driver-class-name", () -> "org.postgresql.Driver");
  }

  @Autowired JdbcTemplate jdbc;
  @Autowired OperationalGuardService guardService;
  @Autowired PublicationReviewAcknowledgementService acknowledgementService;

  private final Clock fixedClock = Clock.fixed(Instant.parse("2026-10-01T12:00:00Z"), ZoneOffset.UTC);
  private UUID videoId;

  @BeforeEach
  void setUp() {
    jdbc.execute("TRUNCATE operational_guard_decisions, publication_review_acknowledgements, effective_performance_observations, performance_observations, videos CASCADE");
    videoId = UUID.randomUUID();
    jdbc.update(
        "INSERT INTO videos(id, title, content_hash) VALUES (?, 'test-video', 'hash123')",
        videoId);
  }

  // =========================================================================
  // Evidence filtering tests
  // =========================================================================

  @Test
  void insufficientEvidenceWhenNoObservations() {
    var snapshot = guardService.evaluate("facebook");
    assertThat(snapshot.enabled()).isTrue();
    assertThat(snapshot.decisions()).hasSize(2);

    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    assertThat(distribution.state()).isEqualTo("INSUFFICIENT_EVIDENCE");
    assertThat(distribution.evidenceCount()).isZero();
  }

  @Test
  void filtersOutUnavailableDataQualityObservations() {
    // Insert an observation with UNAVAILABLE data quality status
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 0.5, 'UNAVAILABLE', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(24)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    assertThat(distribution.state()).isEqualTo("INSUFFICIENT_EVIDENCE");
    assertThat(distribution.evidenceCount()).isZero();
  }

  @Test
  void filtersOutNullRecommendationPercentage() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, NULL, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(24)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    assertThat(distribution.state()).isEqualTo("INSUFFICIENT_EVIDENCE");
  }

  @Test
  void usesOnlyLatestObservationPerVideoVariant() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    // Insert two observations for the same video; only the latest should count.
    // Default floor is 20.0 (percentage). First observation is below floor, second is above.
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(24)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(1)), ZoneOffset.UTC));

    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 30.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(12)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    // Should use the latest (30.0), which is above floor (20.0) -> HEALTHY
    assertThat(distribution.state()).isEqualTo("HEALTHY");
    assertThat(distribution.evidenceCount()).isEqualTo(1);
  }

  // =========================================================================
  // Maturity tests
  // =========================================================================

  @Test
  void immatureObservationsAreExcluded() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    // Observation measured only 1 hour after publication (maturity is 24 hours by default)
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 30.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(1)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    assertThat(distribution.state()).isEqualTo("INSUFFICIENT_EVIDENCE");
  }

  @Test
  void matureObservationsAreIncluded() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    // Observation measured 48 hours after publication (maturity is 24 hours by default).
    // Default floors: recommendation=20.0, completion_rate=35.0, avg_watch_seconds=4.0
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, completion_rate, average_watch_seconds,
          data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 30.0, 50.0, 30.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    var retention = snapshot.decisions().stream()
        .filter(d -> "RETENTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();

    assertThat(distribution.state()).isEqualTo("HEALTHY");
    assertThat(retention.state()).isEqualTo("HEALTHY");
  }

  // =========================================================================
  // Policy threshold tests
  // =========================================================================

  @Test
  void lowRecommendationPercentageProducesPublicationReviewRequired() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    // recommendation_percentage = 10.0, below default floor (20.0)
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    assertThat(distribution.state()).isEqualTo("PUBLICATION_REVIEW_REQUIRED");
  }

  @Test
  void weakRetentionProducesWeakRetentionState() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    // completion_rate = 10.0, below default floor (35.0)
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, completion_rate, average_watch_seconds,
          data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 30.0, 10.0, 5.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var retention = snapshot.decisions().stream()
        .filter(d -> "RETENTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();
    assertThat(retention.state()).isEqualTo("WEAK_RETENTION");
  }

  // =========================================================================
  // Render independence tests
  // =========================================================================

  @Test
  void guardEvaluationDoesNotAffectVideoRecord() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    // Evaluate guard
    guardService.evaluate("facebook");

    // Video record must remain unchanged
    String title = jdbc.queryForObject("SELECT title FROM videos WHERE id=?", String.class, videoId);
    assertThat(title).isEqualTo("test-video");
  }

  @Test
  void guardEvaluationDoesNotCreateRuleEvidence() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    guardService.evaluate("facebook");

    // No rule evidence should be created by guard evaluation
    Integer evidenceCount = jdbc.queryForObject(
        "SELECT count(*) FROM rule_evidence WHERE created_at > ?", Integer.class,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(1)), ZoneOffset.UTC));
    assertThat(evidenceCount).isZero();
  }

  // =========================================================================
  // Auditability tests
  // =========================================================================

  @Test
  void guardDecisionsAreAppendOnly() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 30.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    guardService.evaluate("facebook");

    // Verify decisions are persisted
    Integer count = jdbc.queryForObject(
        "SELECT count(*) FROM operational_guard_decisions WHERE platform='facebook'",
        Integer.class);
    assertThat(count).isEqualTo(2); // DISTRIBUTION + RETENTION

    // Verify decisions carry policy version and evidence
    String evidence = jdbc.queryForObject(
        "SELECT evidence FROM operational_guard_decisions WHERE guard_type='DISTRIBUTION' ORDER BY evaluated_at DESC LIMIT 1",
        String.class);
    assertThat(evidence).contains("recommendation_percentage");
    assertThat(evidence).contains("descriptive_distribution_signal_only");
  }

  @Test
  void multipleEvaluationsProduceDistinctDecisions() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 30.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    guardService.evaluate("facebook");
    guardService.evaluate("facebook");

    Integer count = jdbc.queryForObject(
        "SELECT count(*) FROM operational_guard_decisions WHERE platform='facebook'",
        Integer.class);
    assertThat(count).isEqualTo(4); // 2 evaluations x 2 guard types
  }

  // =========================================================================
  // Platform scope tests
  // =========================================================================

  @Test
  void platformNormalizationIsCaseInsensitive() {
    var snapshot1 = guardService.evaluate("Facebook");
    var snapshot2 = guardService.evaluate("FACEBOOK");
    assertThat(snapshot1.platform()).isEqualTo("facebook");
    assertThat(snapshot2.platform()).isEqualTo("facebook");
  }

  @Test
  void platformIsRequired() {
    assertThatThrownBy(() -> guardService.evaluate(null))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("platform is required");
  }

  // =========================================================================
  // Publication review acknowledgement tests
  // =========================================================================

  @Test
  void acknowledgementRecordsOperatorReview() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var distribution = snapshot.decisions().stream()
        .filter(d -> "DISTRIBUTION".equals(d.guardType()))
        .findFirst()
        .orElseThrow();

    // Acknowledge the decision
    var ack = acknowledgementService.acknowledge(
        "facebook", distribution.id(), "test-operator", "Reviewed, acceptable for now");

    assertThat(ack.guardDecisionId()).isEqualTo(distribution.id());
    assertThat(ack.acknowledgedBy()).isEqualTo("test-operator");
    assertThat(ack.notes()).isEqualTo("Reviewed, acceptable for now");

    // Verify isAcknowledged
    assertThat(acknowledgementService.isAcknowledged("facebook", distribution.id())).isTrue();
  }

  @Test
  void acknowledgementRequiresValidInputs() {
    UUID decisionId = UUID.randomUUID();
    assertThatThrownBy(() -> acknowledgementService.acknowledge(null, decisionId, "actor", null))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("platform is required");

    assertThatThrownBy(() -> acknowledgementService.acknowledge("facebook", null, "actor", null))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("guardDecisionId is required");

    assertThatThrownBy(() -> acknowledgementService.acknowledge("facebook", decisionId, null, null))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("acknowledgedBy is required");
  }

  @Test
  void latestAcknowledgementReturnsMostRecent() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var decision = snapshot.decisions().getFirst();

    acknowledgementService.acknowledge("facebook", decision.id(), "operator-1", "First review");
    acknowledgementService.acknowledge("facebook", decision.id(), "operator-2", "Second review");

    var latest = acknowledgementService.latestAcknowledgement("facebook");
    assertThat(latest).isNotNull();
    // Both acknowledge the same decision, so latest is the second one
    assertThat(latest.acknowledgedBy()).isEqualTo("operator-2");
  }

  @Test
  void acknowledgementListReturnsAllRecords() {
    Instant now = Instant.parse("2026-10-01T10:00:00Z");
    jdbc.update(
        """
        INSERT INTO performance_observations(
          id, video_id, platform, publication_timestamp, measurement_timestamp,
          recommendation_percentage, data_quality_status, created_at
        ) VALUES (?, ?, 'facebook', ?, ?, 10.0, 'OK', ?)
        """,
        UUID.randomUUID(), videoId,
        OffsetDateTime.ofInstant(now.minus(Duration.ofHours(48)), ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC),
        OffsetDateTime.ofInstant(now, ZoneOffset.UTC));

    var snapshot = guardService.evaluate("facebook");
    var decision = snapshot.decisions().getFirst();

    acknowledgementService.acknowledge("facebook", decision.id(), "operator-1", "First");
    acknowledgementService.acknowledge("facebook", decision.id(), "operator-2", "Second");

    var list = acknowledgementService.listAcknowledgements("facebook");
    assertThat(list).hasSize(2);
  }

  @Test
  void noAcknowledgementReturnsNull() {
    var latest = acknowledgementService.latestAcknowledgement("facebook");
    assertThat(latest).isNull();
  }
}
