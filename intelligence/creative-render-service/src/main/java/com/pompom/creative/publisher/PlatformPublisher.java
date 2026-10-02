package com.pompom.creative.publisher;

import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;

/** Interface for platform-specific publishers. */
public interface PlatformPublisher {

  /**
   * Publish video to platform.
   *
   * @param request Publish request with video and metadata
   * @return Publish response with post ID and URL
   */
  PublishResponse publish(PublishRequest request);

  /** Get platform name. */
  String getPlatformName();

  /** Check if publisher is configured and ready. */
  boolean isConfigured();
}
