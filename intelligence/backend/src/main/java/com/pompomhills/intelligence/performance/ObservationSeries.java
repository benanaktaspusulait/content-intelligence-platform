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
