package com.pompom.creative.metrics.client;

import com.pompom.creative.metrics.VideoMetrics;
import com.pompom.creative.oauth.PlatformType;
import java.io.IOException;

/** Interface for platform-specific metrics clients. */
public interface PlatformMetricsClient {

  /**
   * Fetch video metrics from platform API.
   *
   * @param platformVideoId Platform-specific video ID
   * @return VideoMetrics with current metrics
   * @throws IOException if API call fails
   */
  VideoMetrics fetchMetrics(String platformVideoId) throws IOException;

  /** Get the platform this client serves. */
  PlatformType getPlatform();
}
