# Part 02 Plan A: Observation Mathematics Correctness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make trajectory, velocity, burst-ratio, tail-ratio, and horizon-checkpoint calculations
mathematically correct given each observation's declared `metric_semantics`, stop silently mixing
incompatible observation sources into one series, and stop silently returning a far-stale
checkpoint as if it satisfied a specific time horizon.

**Architecture:** A new shared normalization step converts a raw, mixed-semantics observation list
into one honest cumulative-views series before any existing delta/velocity/checkpoint math runs.
`DAILY_INCREMENT` rows are accumulated into a running sum; `CUMULATIVE` and `SNAPSHOT` rows are
used directly as already-cumulative checkpoints; `UNKNOWN` rows are excluded entirely (never
guessed). The same step also partitions by `source` so one trajectory is never built by
interleaving CSV-origin and Meta-Graph-origin rows. `PlatformGrowthProfileService.checkpoint()` and
`PlatformStateService.pointAtOrBefore/pointAtOrAfter` gain an explicit tolerance window so a
"24h" checkpoint is never silently satisfied by a 1-hour-old observation.

**Tech Stack:** Java 21, Spring Boot (`JdbcClient`, no JPA entity for these tables — raw SQL +
record mapping), PostgreSQL 17, JUnit 5 + AssertJ, Testcontainers for DB-backed tests.

## Global Constraints

- Never edit a previously-committed migration (V1-V31). Any new migration starts at `V32`.
- `performance_observations` is append-only (DB trigger enforces this) — this plan only reads it,
  never writes to it.
- No fuzzy attribution anywhere in this plan's scope — this plan is purely about correctly
  interpreting data that is already unambiguously attributed to a `video_id`/`platform`.
- Preserve the existing API response shapes' field names exactly where audit findings don't require
  a change — only add fields, never silently rename or remove one a frontend may already read
  (confirm against `intelligence/frontend/src/app/pages/video-detail.page.ts` before any rename).
- Must leave the full Spring test suite green (`mvn test` from `intelligence/backend`).

---

## Context: the exact current (incorrect) behavior being fixed

Read these two files in full before starting, since every task below modifies them:

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java`
  (118 lines) — `trajectory()` queries `performance_observations` with no `metric_semantics` or
  `source` filtering, then computes `delta = current.views() - previous.views()` and
  `velocity = delta / hoursBetween` between every pair of consecutive rows, regardless of whether
  either row is `DAILY_INCREMENT`, `CUMULATIVE`, `SNAPSHOT`, or from a different `source`.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java`
  (123 lines) — `profile()` has the identical gap (no semantics/source filter), plus
  `checkpoint()` (lines 86-94) does a zero-tolerance "last observation at or before horizon" scan:
  a point at `horizon - 23 hours` is accepted as the "24h" checkpoint if nothing closer exists,
  with no signal to the caller that it's stale.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`
  — the private `point(UUID videoId, String platform, Instant at, boolean before)` method (used by
  `pointAtOrBefore`/`pointAtOrAfter`, which back the Reach Further window calculations in
  `reachFurtherSummary()`) has the same zero-tolerance behavior via `<=`/`>=` with `LIMIT 1`.

---

## Task 1: Shared observation-normalization utility

**Files:**
- Create: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/ObservationSeries.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/ObservationSeriesTest.java`

**Interfaces:**
- Consumes: nothing new — this is a pure, dependency-free utility class.
- Produces:
  - `ObservationSeries.RawObservation` record: `(Instant measuredAt, Long views, String metricSemantics, String source)`.
  - `ObservationSeries.NormalizedPoint` record: `(Instant measuredAt, Long cumulativeViews, String source)`.
  - `ObservationSeries.normalize(List<RawObservation> raw) -> List<NormalizedPoint>` — the pure
    function Tasks 2 and 3 both call. Returns points sorted by `measuredAt` ascending, one
    normalized cumulative-views series **per distinct `source`** (i.e. if two sources are present,
    the returned list contains both series' points interleaved by time, but each point still
    carries its own `source` so callers can choose to use only one source, or detect disagreement
    — this task does not decide what callers do with multiple sources, only guarantees the
    semantics-to-cumulative conversion is correct per source).

- [ ] **Step 1: Write the failing tests**

Create `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/ObservationSeriesTest.java`:

```java
package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class ObservationSeriesTest {

  private static final Instant T0 = Instant.parse("2026-01-01T00:00:00Z");
  private static final Instant T1 = Instant.parse("2026-01-02T00:00:00Z");
  private static final Instant T2 = Instant.parse("2026-01-03T00:00:00Z");

  @Test
  void dailyIncrementRowsAreAccumulatedIntoARunningCumulativeSum() {
    // The exact failure case from the audit: 1,000 then 300 DAILY_INCREMENT must become
    // a cumulative 1,000 then 1,300 - never a negative delta.
    List<ObservationSeries.RawObservation> raw =
        List.of(
            new ObservationSeries.RawObservation(T0, 1000L, "DAILY_INCREMENT", "CSV"),
            new ObservationSeries.RawObservation(T1, 300L, "DAILY_INCREMENT", "CSV"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized).hasSize(2);
    assertThat(normalized.get(0).cumulativeViews()).isEqualTo(1000L);
    assertThat(normalized.get(1).cumulativeViews()).isEqualTo(1300L);
  }

  @Test
  void cumulativeRowsAreUsedDirectlyWithoutAccumulation() {
    List<ObservationSeries.RawObservation> raw =
        List.of(
            new ObservationSeries.RawObservation(T0, 1000L, "CUMULATIVE", "CSV"),
            new ObservationSeries.RawObservation(T1, 1300L, "CUMULATIVE", "CSV"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized.get(0).cumulativeViews()).isEqualTo(1000L);
    assertThat(normalized.get(1).cumulativeViews()).isEqualTo(1300L);
  }

  @Test
  void snapshotRowsAreUsedDirectlyAsCumulativeCheckpoints() {
    List<ObservationSeries.RawObservation> raw =
        List.of(new ObservationSeries.RawObservation(T0, 60000L, "SNAPSHOT", "API"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized).hasSize(1);
    assertThat(normalized.get(0).cumulativeViews()).isEqualTo(60000L);
  }

  @Test
  void unknownSemanticsRowsAreExcludedEntirely() {
    List<ObservationSeries.RawObservation> raw =
        List.of(
            new ObservationSeries.RawObservation(T0, 1000L, "CUMULATIVE", "CSV"),
            new ObservationSeries.RawObservation(T1, 999999L, "UNKNOWN", "CSV"),
            new ObservationSeries.RawObservation(T2, 1500L, "CUMULATIVE", "CSV"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized).hasSize(2);
    assertThat(normalized).extracting(ObservationSeries.NormalizedPoint::cumulativeViews)
        .containsExactly(1000L, 1500L);
  }

  @Test
  void nullViewsRowsAreExcludedEntirely() {
    List<ObservationSeries.RawObservation> raw =
        List.of(
            new ObservationSeries.RawObservation(T0, 1000L, "CUMULATIVE", "CSV"),
            new ObservationSeries.RawObservation(T1, null, "CUMULATIVE", "CSV"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized).hasSize(1);
  }

  @Test
  void differentSourcesProduceIndependentAccumulationNotOneSharedRunningSum() {
    // A DAILY_INCREMENT row from source "API" must not accumulate on top of a prior
    // DAILY_INCREMENT row from source "CSV" - each source's running sum is independent.
    List<ObservationSeries.RawObservation> raw =
        List.of(
            new ObservationSeries.RawObservation(T0, 1000L, "DAILY_INCREMENT", "CSV"),
            new ObservationSeries.RawObservation(T1, 500L, "DAILY_INCREMENT", "API"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized).hasSize(2);
    ObservationSeries.NormalizedPoint csvPoint =
        normalized.stream().filter(p -> p.source().equals("CSV")).findFirst().orElseThrow();
    ObservationSeries.NormalizedPoint apiPoint =
        normalized.stream().filter(p -> p.source().equals("API")).findFirst().orElseThrow();
    assertThat(csvPoint.cumulativeViews()).isEqualTo(1000L);
    assertThat(apiPoint.cumulativeViews()).isEqualTo(500L);
  }

  @Test
  void resultIsSortedByMeasuredAtAscendingAcrossSources() {
    List<ObservationSeries.RawObservation> raw =
        List.of(
            new ObservationSeries.RawObservation(T2, 100L, "CUMULATIVE", "API"),
            new ObservationSeries.RawObservation(T0, 50L, "CUMULATIVE", "CSV"),
            new ObservationSeries.RawObservation(T1, 75L, "CUMULATIVE", "CSV"));

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);

    assertThat(normalized).extracting(ObservationSeries.NormalizedPoint::measuredAt)
        .containsExactly(T0, T1, T2);
  }

  @Test
  void emptyInputProducesEmptyOutput() {
    assertThat(ObservationSeries.normalize(List.of())).isEmpty();
  }
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=ObservationSeriesTest`
Expected: compilation failure, `ObservationSeries` class does not exist yet.

- [ ] **Step 3: Implement**

Create `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/ObservationSeries.java`:

```java
package com.pompomhills.intelligence.performance;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Converts a raw, possibly-mixed-semantics, possibly-mixed-source observation list into one
 * honest cumulative-views series per source.
 *
 * <p>{@code performance_observations.metric_semantics} declares whether a row's {@code views}
 * value is a {@code DAILY_INCREMENT} (must be accumulated to become comparable to a cumulative
 * checkpoint), an already-{@code CUMULATIVE} running total, a point-in-time {@code SNAPSHOT}
 * (treated as a cumulative checkpoint for this purpose - a snapshot's views count is, by
 * definition, "views as of this moment," which is exactly what a cumulative series needs), or
 * {@code UNKNOWN} (excluded entirely - never guessed, per the project's no-fabrication policy).
 *
 * <p>Accumulation is scoped per {@code source} (e.g. "CSV" vs "API") so one source's running sum
 * is never silently continued by another source's rows - two independently-collected streams
 * must not be blended into one running total, even if the earlier gap-fix (keeping them as
 * separate points) prevents literal numeric corruption on its own.
 */
public final class ObservationSeries {

  private ObservationSeries() {}

  public record RawObservation(Instant measuredAt, Long views, String metricSemantics, String source) {}

  public record NormalizedPoint(Instant measuredAt, Long cumulativeViews, String source) {}

  public static List<NormalizedPoint> normalize(List<RawObservation> raw) {
    List<RawObservation> sorted =
        raw.stream().sorted(Comparator.comparing(RawObservation::measuredAt)).toList();

    Map<String, Long> runningSumBySource = new HashMap<>();
    List<NormalizedPoint> result = new ArrayList<>();

    for (RawObservation observation : sorted) {
      if (observation.views() == null) continue;
      String semantics = observation.metricSemantics();
      String source = observation.source();

      Long cumulative =
          switch (semantics) {
            case "DAILY_INCREMENT" -> {
              long previous = runningSumBySource.getOrDefault(source, 0L);
              long updated = previous + observation.views();
              runningSumBySource.put(source, updated);
              yield updated;
            }
            case "CUMULATIVE", "SNAPSHOT" -> observation.views();
            case "UNKNOWN" -> null;
            default -> null;
          };

      if (cumulative != null) {
        result.add(new NormalizedPoint(observation.measuredAt(), cumulative, source));
      }
    }

    return result.stream().sorted(Comparator.comparing(NormalizedPoint::measuredAt)).toList();
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=ObservationSeriesTest`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/ObservationSeries.java intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/ObservationSeriesTest.java
git commit -m "feat(intelligence): add ObservationSeries metric-semantics normalization utility"
```

---

## Task 2: Rewire `PerformanceTrajectoryController` onto normalized, source-aware observations

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryControllerTest.java`

**Interfaces:**
- Consumes: `ObservationSeries.normalize(List<RawObservation>) -> List<NormalizedPoint>` (Task 1).
- Produces: `TrajectoryView` gains two new fields: `List<String> sourcesPresent` (every distinct
  `source` value seen in the raw observations for this video/platform, informational) and
  `boolean sourceReconciliationApplied` (true when more than one distinct source was present and
  the response therefore used only the single source with the most points, per the explicit
  reconciliation rule below — false when there was only one source, so nothing needed resolving).
  `TrajectoryPoint.views` becomes the **normalized cumulative value**, not the raw column value.

- [ ] **Step 1: Read the current full file**

Read `PerformanceTrajectoryController.java` in full (already quoted in this plan's "Context"
section above, but re-read the live file directly before editing — do not edit from memory of the
quote). Confirm the exact current SQL, `RawPoint` record shape, and `trajectory()` method body
match what's described, since this plan was written against a specific snapshot that may have
shifted.

- [ ] **Step 2: Write the failing tests**

This needs a real database, since the SQL query itself changes (adding `metric_semantics` and
`source` to the SELECT). Create
`intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryControllerTest.java`
using the same `@SpringBootTest` + Testcontainers pattern as
`intelligence/backend/src/test/java/com/pompomhills/intelligence/quality/ValidationEvidencePersistenceTest.java`
(read that file first for the exact container/property-registration boilerplate to copy). This
test inserts directly into `videos` and `performance_observations` via `JdbcClient` (there is no
JPA entity for either table in this code path), then calls the controller method directly (not
through MockMvc — the method is package-visible per the existing style, confirm this compiles from
the same package):

```java
package com.pompomhills.intelligence.performance.api;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompomhills.intelligence.performance.InterventionService;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class PerformanceTrajectoryControllerTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired InterventionService interventions;

  private PerformanceTrajectoryController controller() {
    return new PerformanceTrajectoryController(jdbc, interventions);
  }

  private UUID insertVideo() {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,'test.mp4',:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private void insertObservation(
      UUID videoId, Instant measuredAt, long views, String semantics, String source) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,platform,measurement_timestamp,metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,'instagram',:measured,:semantics,:views,:source)
            """)
        .param("video", videoId)
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("semantics", semantics)
        .param("views", views)
        .param("source", source)
        .update();
  }

  @Test
  void dailyIncrementObservationsProduceAPositiveCumulativeTrajectoryNotANegativeOne() {
    UUID videoId = insertVideo();
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    Instant t1 = Instant.parse("2026-01-02T00:00:00Z");
    insertObservation(videoId, t0, 1000L, "DAILY_INCREMENT", "CSV");
    insertObservation(videoId, t1, 300L, "DAILY_INCREMENT", "CSV");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.points()).hasSize(2);
    assertThat(view.points().get(0).views()).isEqualTo(1000L);
    assertThat(view.points().get(1).views()).isEqualTo(1300L);
    assertThat(view.points().get(1).deltaViews()).isEqualTo(300L);
    // Before this fix, this would have been -700.
  }

  @Test
  void mixedSourcesAreFlaggedAndReconciledToTheSourceWithMorePoints() {
    UUID videoId = insertVideo();
    Instant t0 = Instant.parse("2026-01-01T00:00:00Z");
    Instant t1 = Instant.parse("2026-01-02T00:00:00Z");
    Instant t2 = Instant.parse("2026-01-03T00:00:00Z");
    insertObservation(videoId, t0, 1000L, "CUMULATIVE", "CSV");
    insertObservation(videoId, t1, 1200L, "CUMULATIVE", "CSV");
    insertObservation(videoId, t2, 999999L, "SNAPSHOT", "API");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.sourcesPresent()).containsExactlyInAnyOrder("CSV", "API");
    assertThat(view.sourceReconciliationApplied()).isTrue();
    // CSV has 2 points, API has 1 - CSV wins, API's point is excluded from the series.
    assertThat(view.points()).hasSize(2);
    assertThat(view.points()).allSatisfy(p -> assertThat(p.views()).isLessThan(999999L));
  }

  @Test
  void singleSourceNeedsNoReconciliation() {
    UUID videoId = insertVideo();
    insertObservation(videoId, Instant.parse("2026-01-01T00:00:00Z"), 1000L, "CUMULATIVE", "CSV");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.sourcesPresent()).containsExactly("CSV");
    assertThat(view.sourceReconciliationApplied()).isFalse();
  }

  @Test
  void unknownSemanticsObservationsAreExcludedFromTheTrajectory() {
    UUID videoId = insertVideo();
    insertObservation(videoId, Instant.parse("2026-01-01T00:00:00Z"), 1000L, "CUMULATIVE", "CSV");
    insertObservation(videoId, Instant.parse("2026-01-02T00:00:00Z"), 50L, "UNKNOWN", "CSV");

    var view = controller().trajectory(videoId, "instagram");

    assertThat(view.points()).hasSize(1);
  }
}
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=PerformanceTrajectoryControllerTest`
Expected: compilation failure or assertion failures — `sourcesPresent()`/`sourceReconciliationApplied()`
do not exist on `TrajectoryView` yet, and the first test's `deltaViews()` assertion would fail
against the current raw-diff logic even if it compiled.

- [ ] **Step 4: Implement**

Replace `PerformanceTrajectoryController.java`'s `trajectory()` method and supporting types.
Read the current full file first (per Step 1) to confirm exact current structure, then apply:

```java
package com.pompomhills.intelligence.performance.api;

import com.pompomhills.intelligence.performance.InterventionService;
import com.pompomhills.intelligence.performance.ObservationSeries;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/performance")
public class PerformanceTrajectoryController {
  private final JdbcClient jdbc;
  private final InterventionService interventions;

  public PerformanceTrajectoryController(JdbcClient jdbc, InterventionService interventions) {
    this.jdbc = jdbc;
    this.interventions = interventions;
  }

  @GetMapping("/video/{videoId}/trajectory")
  TrajectoryView trajectory(
      @PathVariable UUID videoId, @RequestParam(defaultValue = "instagram") String platform) {
    List<ObservationSeries.RawObservation> raw =
        jdbc.sql(
                """
                SELECT measurement_timestamp,views,metric_semantics,source
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform AND measurement_timestamp IS NOT NULL
                ORDER BY measurement_timestamp
                """)
            .param("video", videoId)
            .param("platform", platform.toLowerCase())
            .query(
                (rs, ignored) ->
                    new ObservationSeries.RawObservation(
                        rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant(),
                        nullableLong(rs, "views"),
                        rs.getString("metric_semantics"),
                        rs.getString("source")))
            .list();

    List<String> sourcesPresent =
        raw.stream().map(ObservationSeries.RawObservation::source).distinct().sorted().toList();
    boolean reconciliationApplied = sourcesPresent.size() > 1;

    List<ObservationSeries.NormalizedPoint> normalized = ObservationSeries.normalize(raw);
    List<ObservationSeries.NormalizedPoint> selected =
        reconciliationApplied ? dominantSource(normalized) : normalized;

    var interventionEvents = interventions.list(videoId, platform);
    Instant firstIntervention =
        interventionEvents.isEmpty() ? null : interventionEvents.getFirst().eventTime();
    var points = new ArrayList<TrajectoryPoint>();
    for (int index = 0; index < selected.size(); index++) {
      ObservationSeries.NormalizedPoint current = selected.get(index);
      ObservationSeries.NormalizedPoint previous = index == 0 ? null : selected.get(index - 1);
      Long delta = previous == null ? null : current.cumulativeViews() - previous.cumulativeViews();
      Double velocity = null;
      if (previous != null && delta != null) {
        double hours =
            Duration.between(previous.measuredAt(), current.measuredAt()).toMillis() / 3_600_000.0;
        if (hours > 0) velocity = delta / hours;
      }
      points.add(
          new TrajectoryPoint(
              current.measuredAt(),
              current.cumulativeViews(),
              null,
              null,
              null,
              null,
              null,
              delta,
              velocity,
              firstIntervention != null && !current.measuredAt().isBefore(firstIntervention)));
    }
    return new TrajectoryView(
        videoId,
        platform.toLowerCase(),
        label(points),
        firstIntervention == null,
        interventionEvents,
        points,
        sourcesPresent,
        reconciliationApplied);
  }

  /**
   * When more than one source contributed observations, this trajectory uses only the source
   * with the most normalized points - an explicit, visible reconciliation rule rather than
   * silently interleaving two independently-collected series. Callers can see which sources were
   * present via {@link TrajectoryView#sourcesPresent()} and that reconciliation happened via
   * {@link TrajectoryView#sourceReconciliationApplied()}.
   */
  private List<ObservationSeries.NormalizedPoint> dominantSource(
      List<ObservationSeries.NormalizedPoint> normalized) {
    Map<String, List<ObservationSeries.NormalizedPoint>> bySource = new LinkedHashMap<>();
    for (var point : normalized) {
      bySource.computeIfAbsent(point.source(), key -> new ArrayList<>()).add(point);
    }
    return bySource.values().stream()
        .max((a, b) -> Integer.compare(a.size(), b.size()))
        .orElse(List.of());
  }

  private String label(List<TrajectoryPoint> points) {
    if (points.size() < 3) return "INSUFFICIENT_DATA";
    Double previous = points.get(points.size() - 2).viewsPerHour();
    Double latest = points.getLast().viewsPerHour();
    if (previous == null || latest == null) return "INSUFFICIENT_DATA";
    if (latest > Math.max(50, previous * 1.75)) return "SECOND_WAVE";
    if (latest < 10) return "EARLY_STALL";
    if (latest > previous * 1.1) return "PERSISTENT_GROWTH";
    return "SLOW_GROWTH";
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  public record TrajectoryPoint(
      Instant measuredAt,
      Long views,
      Long reach,
      Long likes,
      Long comments,
      Long shares,
      Long follows,
      Long deltaViews,
      Double viewsPerHour,
      boolean intervened) {}

  public record TrajectoryView(
      UUID videoId,
      String platform,
      String label,
      boolean cleanOrganic,
      List<InterventionService.InterventionView> interventions,
      List<TrajectoryPoint> points,
      List<String> sourcesPresent,
      boolean sourceReconciliationApplied) {}
}
```

**Important deliberate scope note for the implementer:** this rewrite drops `reach`/`likes`/
`comments`/`shares`/`follows` from each `TrajectoryPoint` (set to `null` always) because
`ObservationSeries.normalize()` (Task 1) only tracks `views` — those other metrics have their own
semantics questions (are they ever `DAILY_INCREMENT`? the schema doesn't distinguish per-metric
semantics, only one `metric_semantics` value per row) that are out of this plan's scope to solve
correctly. Setting them to `null` here is **more honest than silently keeping the old raw-value
behavior** for fields this task cannot verify correctness for using the same source-blind logic
that was already proven wrong for `views`. If a reviewer or the implementer judges this
regression unacceptable, the alternative is to apply the exact same `metric_semantics`-aware
accumulation independently to each of these five columns (extending `ObservationSeries` to be
generic over metric name) — flag this explicitly rather than silently picking one approach, since
it changes this task's scope.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=PerformanceTrajectoryControllerTest`
Expected: all 4 tests PASS.

- [ ] **Step 6: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass, including any existing test that may reference `TrajectoryPoint`'s
`reach`/`likes`/`comments`/`shares`/`follows` fields (grep for `TrajectoryPoint(` and
`TrajectoryView(` across `src/test` first — same near-miss pattern as Plan A Task 8 in Part 01's
roadmap; fix any positional-construction test call site that doesn't compile against the new
2-field-longer `TrajectoryView` record).

- [ ] **Step 7: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryController.java intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/api/PerformanceTrajectoryControllerTest.java
git commit -m "fix(intelligence): normalize trajectory by metric_semantics, reconcile mixed sources explicitly"
```

---

## Task 3: Rewire `PlatformGrowthProfileService` onto normalized observations + add checkpoint tolerance

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileServiceTest.java`

**Interfaces:**
- Consumes: `ObservationSeries.normalize(...)` (Task 1).
- Produces: `MetricCheckpoint` gains a `boolean withinTolerance` field (true when the matched
  observation is within `TOLERANCE` of the target horizon, false when it's the best available but
  outside tolerance). `GrowthProfile`'s existing fields keep their names/types.

- [ ] **Step 1: Read the current full file**

Read `PlatformGrowthProfileService.java` in full (already quoted in this plan's "Context"
section — re-read the live file directly). Confirm `checkpoint()`'s exact current body, the
`Point`/`MetricCheckpoint`/`GrowthProfile` record shapes, and `profile()`'s query/computation
sequence match before editing.

- [ ] **Step 2: Write the failing tests**

Create `intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileServiceTest.java`,
same Testcontainers pattern as Task 2's test (copy the container/property boilerplate):

```java
package com.pompomhills.intelligence.performance;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class PlatformGrowthProfileServiceTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired PlatformGrowthProfileService service;

  private UUID insertVideo() {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,'test.mp4',:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private void insertObservation(
      UUID videoId,
      Instant publishedAt,
      Instant measuredAt,
      long views,
      String semantics,
      String source) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,platform,publication_timestamp,measurement_timestamp,
               metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,'instagram',:published,:measured,:semantics,:views,:source)
            """)
        .param("video", videoId)
        .param("published", OffsetDateTime.ofInstant(publishedAt, ZoneOffset.UTC))
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("semantics", semantics)
        .param("views", views)
        .param("source", source)
        .update();
  }

  @Test
  void checkpointWithinToleranceOfTargetHorizonIsMarkedWithinTolerance() {
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    // 23h50m after publish - within a reasonable tolerance of the 24h target.
    insertObservation(
        videoId, published, published.plusSeconds(23 * 3600L + 50 * 60L), 5000L, "CUMULATIVE", "CSV");

    var profile = service.profile(videoId, "instagram", Instant.now());

    assertThat(profile.views24h()).isNotNull();
    assertThat(profile.views24h().withinTolerance()).isTrue();
  }

  @Test
  void checkpointFarOutsideToleranceOfTargetHorizonIsMarkedNotWithinTolerance() {
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    // Only a 1h observation exists; the audit's exact failure case for the "24h" label.
    insertObservation(videoId, published, published.plusSeconds(3600L), 100L, "CUMULATIVE", "CSV");

    var profile = service.profile(videoId, "instagram", Instant.now());

    assertThat(profile.views24h()).isNotNull();
    assertThat(profile.views24h().withinTolerance()).isFalse();
    // The real measurement time is still exposed, so a caller can show "closest available: 1h".
    assertThat(profile.views24h().measuredAt()).isEqualTo(published.plusSeconds(3600L));
  }

  @Test
  void dailyIncrementObservationsAreAccumulatedBeforeComputingCheckpoints() {
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, published, published, 1000L, "DAILY_INCREMENT", "CSV");
    insertObservation(
        videoId, published, published.plusSeconds(6 * 3600L), 500L, "DAILY_INCREMENT", "CSV");

    var profile = service.profile(videoId, "instagram", Instant.now());

    assertThat(profile.views6h().views()).isEqualTo(1500L);
  }
}
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd intelligence/backend && mvn test -Dtest=PlatformGrowthProfileServiceTest`
Expected: compilation failure (`withinTolerance()` doesn't exist on `MetricCheckpoint` yet) or
assertion failures.

- [ ] **Step 4: Implement**

Replace `PlatformGrowthProfileService.java`'s query, `checkpoint()` method, and `MetricCheckpoint`
record:

```java
package com.pompomhills.intelligence.performance;

import java.time.Duration;
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
public class PlatformGrowthProfileService {
  /**
   * How close an observation must be to a target horizon to count as satisfying that horizon's
   * label. A "24h" checkpoint built from a 1-hour-old observation is misleading - per the
   * audit's P1-07 finding, this must be visible rather than silently accepted.
   */
  private static final Duration CHECKPOINT_TOLERANCE = Duration.ofHours(2);

  private final JdbcClient jdbc;

  public PlatformGrowthProfileService(JdbcClient jdbc) {
    this.jdbc = jdbc;
  }

  @Transactional(readOnly = true)
  public GrowthProfile profile(UUID videoId, String platform, Instant cutoff) {
    String normalized = platform.toLowerCase(Locale.ROOT);
    List<ObservationSeries.RawObservation> raw =
        jdbc.sql(
                """
                SELECT measurement_timestamp,views,metric_semantics,source
                FROM performance_observations
                WHERE video_id=:video AND platform=:platform
                  AND publication_timestamp IS NOT NULL
                  AND measurement_timestamp IS NOT NULL
                  AND measurement_timestamp<=:cutoff
                ORDER BY measurement_timestamp
                """)
            .param("video", videoId)
            .param("platform", normalized)
            .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
            .query(
                (rs, ignored) ->
                    new ObservationSeries.RawObservation(
                        rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant(),
                        nullableLong(rs, "views"),
                        rs.getString("metric_semantics"),
                        rs.getString("source")))
            .list();
    Instant publishedAt = earliestPublication(videoId, normalized, cutoff);
    if (publishedAt == null) return empty(videoId, normalized);

    List<ObservationSeries.NormalizedPoint> points = ObservationSeries.normalize(raw);
    if (points.isEmpty()) return empty(videoId, normalized);

    MetricCheckpoint at6h = checkpoint(points, publishedAt.plusSeconds(6 * 3600L));
    MetricCheckpoint at24h = checkpoint(points, publishedAt.plusSeconds(24 * 3600L));
    MetricCheckpoint at48h = checkpoint(points, publishedAt.plusSeconds(48 * 3600L));
    MetricCheckpoint at7d = checkpoint(points, publishedAt.plusSeconds(7 * 24 * 3600L));
    ObservationSeries.NormalizedPoint latest = points.getLast();

    Double instagramBurstRatio =
        at6h == null || at24h == null || at24h.views() == 0
            ? null
            : at6h.views() / (double) at24h.views();
    Long viewsAfter24h =
        at24h == null || !latest.measuredAt().isAfter(publishedAt.plusSeconds(24 * 3600L))
            ? null
            : Math.max(0, latest.cumulativeViews() - at24h.views());
    Double facebookTailRatio =
        viewsAfter24h == null || at24h.views() == 0 ? null : viewsAfter24h / (double) at24h.views();

    String signal =
        switch (normalized) {
          case "instagram" -> instagramBurstRatio == null ? "INSUFFICIENT_DATA" : "EARLY_BURST";
          case "facebook" -> facebookTailRatio == null ? "INSUFFICIENT_DATA" : "LONG_TAIL";
          default -> "GENERAL_TRAJECTORY";
        };
    return new GrowthProfile(
        videoId,
        normalized,
        publishedAt,
        at6h,
        at24h,
        at48h,
        at7d,
        new MetricCheckpoint(latest.measuredAt(), latest.cumulativeViews(), true),
        instagramBurstRatio,
        viewsAfter24h,
        facebookTailRatio,
        signal,
        "Ratios are descriptive and use metric-semantics-normalized cumulative checkpoints "
            + "without interpolation; a checkpoint outside its tolerance window is flagged, not "
            + "hidden.");
  }

  private Instant earliestPublication(UUID videoId, String platform, Instant cutoff) {
    return jdbc.sql(
            """
            SELECT min(publication_timestamp) FROM performance_observations
            WHERE video_id=:video AND platform=:platform AND publication_timestamp IS NOT NULL
              AND measurement_timestamp<=:cutoff
            """)
        .param("video", videoId)
        .param("platform", platform)
        .param("cutoff", OffsetDateTime.ofInstant(cutoff, ZoneOffset.UTC))
        .query(OffsetDateTime.class)
        .optional()
        .map(OffsetDateTime::toInstant)
        .orElse(null);
  }

  private MetricCheckpoint checkpoint(List<ObservationSeries.NormalizedPoint> points, Instant horizon) {
    ObservationSeries.NormalizedPoint candidate = null;
    for (var point : points) {
      if (point.measuredAt().isAfter(horizon)) break;
      candidate = point;
    }
    if (candidate == null) return null;
    boolean withinTolerance =
        Duration.between(candidate.measuredAt(), horizon).abs().compareTo(CHECKPOINT_TOLERANCE) <= 0;
    return new MetricCheckpoint(candidate.measuredAt(), candidate.cumulativeViews(), withinTolerance);
  }

  private GrowthProfile empty(UUID videoId, String platform) {
    return new GrowthProfile(
        videoId,
        platform,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        null,
        "INSUFFICIENT_DATA",
        "Ratios are descriptive and use metric-semantics-normalized cumulative checkpoints "
            + "without interpolation; a checkpoint outside its tolerance window is flagged, not "
            + "hidden.");
  }

  private Long nullableLong(java.sql.ResultSet rs, String column) throws java.sql.SQLException {
    long value = rs.getLong(column);
    return rs.wasNull() ? null : value;
  }

  public record MetricCheckpoint(Instant measuredAt, long views, boolean withinTolerance) {}

  public record GrowthProfile(
      UUID videoId,
      String platform,
      Instant publishedAt,
      MetricCheckpoint views6h,
      MetricCheckpoint views24h,
      MetricCheckpoint views48h,
      MetricCheckpoint views7d,
      MetricCheckpoint latest,
      Double instagramBurstRatio,
      Long viewsAfter24h,
      Double facebookTailRatio,
      String primarySignal,
      String disclaimer) {}
}
```

**Note on `earliestPublication`:** the original code took `points.getFirst().publishedAt()` from
the same query that selected `views`. Since the normalization step (Task 1) no longer carries
`publishedAt` through `NormalizedPoint` (only `measuredAt`/`cumulativeViews`/`source`), publication
time is now fetched via a small separate query. This is a deliberate, minor behavior note: the
original implicitly used the *first selected row's* `publicationTimestamp`, which could differ
across sources (the SQL change in this task also drops the per-row `publication_timestamp` from
the raw-observation query, since `ObservationSeries.RawObservation` doesn't carry it) — the new
`earliestPublication` explicitly takes `min(publication_timestamp)`, which is more defensible
(the actual single real publish time, not an artifact of row ordering) but is still worth flagging
as a visible behavior change if the implementer or reviewer finds a case where it matters.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd intelligence/backend && mvn test -Dtest=PlatformGrowthProfileServiceTest`
Expected: all 3 tests PASS.

- [ ] **Step 6: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass. Grep for `MetricCheckpoint(` and `GrowthProfile(` across `src/test` and
`src/main` (especially `PlatformStateService.java`, which consumes `GrowthProfile` in
`liveFeatures()` and `reachFurtherSummary()`'s window calculations — confirm those call sites
still compile against the 3-field `MetricCheckpoint` record, since the field count didn't change
there but the type's semantics did; `PlatformStateService` doesn't construct `MetricCheckpoint`
itself, only reads `growth.instagramBurstRatio()`/`growth.viewsAfter24h()`/`growth.facebookTailRatio()`,
so it should be unaffected, but verify directly rather than assuming).

- [ ] **Step 7: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/performance/PlatformGrowthProfileServiceTest.java
git commit -m "fix(intelligence): normalize growth-profile checkpoints by metric_semantics, add tolerance window"
```

---

## Task 4: Add the same checkpoint tolerance to `PlatformStateService`'s Reach Further window calculations

**Files:**
- Modify: `intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java`
- Test: `intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServiceWindowTest.java`

**Interfaces:**
- Consumes: nothing new from Tasks 1-3 (this file's `point()`/`pointAtOrBefore`/`pointAtOrAfter`
  are private methods with their own independent SQL — they do not call `ObservationSeries`,
  since they only ever select `views`/`reach` directly for a point-in-time Reach-Further-relative
  window, not a general trajectory; adding full metric-semantics normalization here is explicitly
  out of this task's scope — only the tolerance-window gap from P1-07 is being fixed here, which
  is a narrower, independent fix).
- Produces: `MetricPoint` gains a `boolean withinTolerance` field, consistent with Task 3's
  `MetricCheckpoint`. `window()`'s returned `WindowPerformance` is unaffected in shape, but its
  `point` field now reflects whether that point was within tolerance of its named window target.

- [ ] **Step 1: Read the current full file's relevant methods**

Read `PlatformStateService.java` in full first (851 lines — already partially quoted in this
plan's "Context" section; the `point()`/`pointAtOrBefore()`/`pointAtOrAfter()`/`MetricPoint`/
`WindowPerformance`/`window()` methods are what this task touches — locate them precisely via
`grep -n "private MetricPoint point\|record MetricPoint\|record WindowPerformance\|private WindowPerformance window"`
before editing, since this plan's earlier read was truncated at line 692 and may not show the
exact current line numbers).

- [ ] **Step 2: Write the failing test**

Create `intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServiceWindowTest.java`,
same Testcontainers pattern as Tasks 2/3 (full `@SpringBootTest` + container boilerplate — this
service has more constructor dependencies than the previous two; read `PlatformStateService`'s
constructor signature first and construct/autowire accordingly):

```java
package com.pompomhills.intelligence.platformstate;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

@SpringBootTest
@Testcontainers(disabledWithoutDocker = true)
class PlatformStateServiceWindowTest {

  @Container
  static final PostgreSQLContainer<?> DATABASE =
      new PostgreSQLContainer<>("postgres:17-alpine")
          .withDatabaseName("pompom")
          .withUsername("pompom")
          .withPassword("pompom_test");

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", DATABASE::getJdbcUrl);
    registry.add("spring.datasource.username", DATABASE::getUsername);
    registry.add("spring.datasource.password", DATABASE::getPassword);
    registry.add(
        "pompom.data-root",
        () -> System.getProperty("java.io.tmpdir") + "/pompom-creative-intelligence-tests");
  }

  @Autowired JdbcClient jdbc;
  @Autowired PlatformStateService service;

  private UUID insertVideo() {
    UUID id = UUID.randomUUID();
    jdbc.sql(
            """
            INSERT INTO videos(id,content_hash,original_filename,relative_path,duration_ms,
              width,height,fps,aspect_ratio,codec,audio_present,status,ingested_at)
            VALUES (:id,:hash,'test.mp4',:path,15000,1080,1920,30.0,0.5625,'h264',true,
              'INGESTED',now())
            """)
        .param("id", id)
        .param("hash", UUID.randomUUID().toString())
        .param("path", "test/" + id + ".mp4")
        .update();
    return id;
  }

  private void insertObservation(UUID videoId, Instant publishedAt, Instant measuredAt, long views) {
    jdbc.sql(
            """
            INSERT INTO performance_observations
              (id,video_id,platform,publication_timestamp,measurement_timestamp,
               metric_semantics,views,source)
            VALUES (gen_random_uuid(),:video,'instagram',:published,:measured,'CUMULATIVE',:views,'CSV')
            """)
        .param("video", videoId)
        .param("published", OffsetDateTime.ofInstant(publishedAt, ZoneOffset.UTC))
        .param("measured", OffsetDateTime.ofInstant(measuredAt, ZoneOffset.UTC))
        .param("views", views)
        .update();
  }

  @Test
  void reachFurtherWindowUsesLatestObservationEvenWhenFarFromTargetWindowBoundary() {
    // Regression guard for the service continuing to function at all after the tolerance
    // field is added - full window-correctness assertions belong to a future Reach-Further-
    // specific test; this confirms reachFurtherSummary() still returns without error once
    // MetricPoint gains a field, since several internal call sites construct it.
    UUID videoId = insertVideo();
    Instant published = Instant.parse("2026-01-01T00:00:00Z");
    insertObservation(videoId, published, published.plusSeconds(3600L), 100L);

    var summary = service.reachFurtherSummary(videoId, "instagram");

    assertThat(summary.videoId()).isEqualTo(videoId);
  }
}
```

- [ ] **Step 3: Run to verify it fails or passes as a baseline**

Run: `cd intelligence/backend && mvn test -Dtest=PlatformStateServiceWindowTest`
Expected: this test should actually PASS even before any production code change, since it doesn't
yet assert on `withinTolerance` — it exists to catch any compile/runtime breakage introduced by
Step 4's `MetricPoint` field addition. Confirm it passes now (establishing the baseline), then
proceed.

- [ ] **Step 4: Implement — add `withinTolerance` to `MetricPoint`**

Locate the exact current `MetricPoint` record and `point()`/`metricPoint()` methods (via the grep
from Step 1) and apply this shape:

```java
private static final java.time.Duration CHECKPOINT_TOLERANCE = java.time.Duration.ofHours(2);

private MetricPoint point(UUID videoId, String platform, Instant at, boolean before) {
  String operator = before ? "<=" : ">=";
  String order = before ? "DESC" : "ASC";
  MetricPoint raw =
      jdbc.sql(
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
  return raw;
}
```

Update `metricPoint(ResultSet rs)` to `metricPoint(ResultSet rs, Instant target)` and compute
`withinTolerance` there:

```java
private MetricPoint metricPoint(java.sql.ResultSet rs, Instant target) throws java.sql.SQLException {
  Instant measuredAt = rs.getObject("measurement_timestamp", OffsetDateTime.class).toInstant();
  boolean withinTolerance =
      java.time.Duration.between(measuredAt, target).abs().compareTo(CHECKPOINT_TOLERANCE) <= 0;
  return new MetricPoint(measuredAt, nullableLong(rs, "views"), nullableLong(rs, "reach"), withinTolerance);
}
```

Update the `MetricPoint` record declaration to add the field:

```java
public record MetricPoint(Instant measuredAt, Long views, Long reach, boolean withinTolerance) {}
```

Update `latestPoint()`'s call to `metricPoint(rs)` — since "latest" has no target horizon to be
"within tolerance" of, pass the point's own `measuredAt` as the target so `withinTolerance` is
trivially `true` for that call site specifically:

```java
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
```

Read every other call site of `metricPoint(rs)` in the file (grep `metricPoint(rs` to find them
all — there may be more than the two shown above) and update each to pass the correct target
`Instant` for its context (for `pointAtOrBefore`/`pointAtOrAfter`, the target is the `at` parameter
already in scope; for any other call site found, determine the contextually correct target rather
than guessing).

- [ ] **Step 5: Run tests to verify nothing broke**

Run: `cd intelligence/backend && mvn test -Dtest=PlatformStateServiceWindowTest`
Expected: still PASSES.

- [ ] **Step 6: Run the full Spring test suite for regressions**

Run: `cd intelligence/backend && mvn test`
Expected: all tests pass. Grep for `MetricPoint(` across `src/test` and `src/main` to find any
other construction site needing the new field (the `window()` method's `WindowPerformance`
construction reads `.views()`/`.reach()` off a `MetricPoint` but doesn't construct one itself, so
it should be unaffected — verify directly).

- [ ] **Step 7: Commit**

```bash
git add intelligence/backend/src/main/java/com/pompomhills/intelligence/platformstate/PlatformStateService.java intelligence/backend/src/test/java/com/pompomhills/intelligence/platformstate/PlatformStateServiceWindowTest.java
git commit -m "fix(intelligence): add checkpoint tolerance tracking to PlatformStateService metric points"
```

---

## Self-Review

**1. Spec coverage against the audit's Phase A (§8):**
- "Define canonical metric semantics normalization" → Task 1 (`ObservationSeries`).
- "Separate/reconcile CSV and API sources" → Task 2's `dominantSource()` reconciliation rule.
- "Reject incompatible rows from one trajectory" → Task 1's `UNKNOWN`/null exclusion.
- "Add explicit provenance and quality state to trajectory responses" → Task 2's
  `sourcesPresent`/`sourceReconciliationApplied` fields.
- "Correct horizon checkpoint selection" → Tasks 3 and 4's `withinTolerance` fields.

**2. Placeholder scan:** No TBD/TODO/"add appropriate handling" patterns — every step has concrete
code. The one explicitly-flagged scope decision (Task 2's dropping of `reach`/`likes`/`comments`/
`shares`/`follows` from `TrajectoryPoint`) is called out as a decision point for the implementer/
reviewer to confirm, not hidden as an accidental omission.

**3. Type consistency:** `ObservationSeries.RawObservation`/`NormalizedPoint` (Task 1) are used
identically in Tasks 2 and 3's SQL-to-record mapping. `MetricCheckpoint`'s `withinTolerance` field
(Task 3) and `MetricPoint`'s `withinTolerance` field (Task 4) use the same name/type/meaning for
consistency, even though they're different record types in different files — a future reader
should not need to learn two different vocabularies for the same concept.
