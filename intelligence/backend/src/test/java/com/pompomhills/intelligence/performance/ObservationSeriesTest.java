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
