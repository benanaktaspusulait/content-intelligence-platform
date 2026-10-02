package com.pompom.creative.monitoring;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

/** Custom metrics service for Prometheus monitoring. */
@Service
@RequiredArgsConstructor
public class MetricsService {

  private final MeterRegistry meterRegistry;

  public void recordRenderJobCreated(String jobType) {
    Counter.builder("pompom.render.jobs.created")
        .tag("type", jobType)
        .register(meterRegistry)
        .increment();
  }

  public void recordRenderJobCompleted(String jobType, String status) {
    Counter.builder("pompom.render.jobs.completed")
        .tag("type", jobType)
        .tag("status", status)
        .register(meterRegistry)
        .increment();
  }

  public void recordPublicationCreated(String platform) {
    Counter.builder("pompom.publications.created")
        .tag("platform", platform)
        .register(meterRegistry)
        .increment();
  }

  public void recordPublicationCompleted(String platform, String status) {
    Counter.builder("pompom.publications.completed")
        .tag("platform", platform)
        .tag("status", status)
        .register(meterRegistry)
        .increment();
  }

  public Timer.Sample startTimer() {
    return Timer.start(meterRegistry);
  }

  public void recordRenderDuration(Timer.Sample sample) {
    sample.stop(
        Timer.builder("pompom.render.duration")
            .description("Render job duration")
            .register(meterRegistry));
  }
}
