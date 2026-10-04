package com.pompom.creative.publisher;

import com.pompom.creative.publisher.dto.PublishRequest;
import com.pompom.creative.publisher.dto.PublishResponse;
import java.util.Optional;

/** Interface for platform-specific publishers. */
public interface PlatformPublisher {

  /**
   * Publish video to platform.
   *
   * @param request Publish request with video and metadata
   * @return Publish response with post ID and URL
   */
  PublishResponse publish(PublishRequest request);

  /** Reconcile a possibly completed remote submission without creating a new post. */
  default Optional<PublishResponse> reconcile(
      PublishRequest request, String platformPostId, String platformVideoId) {
    return Optional.empty();
  }

  /** Get platform name. */
  String getPlatformName();

  /** Check if publisher is configured and ready. */
  boolean isConfigured();
}
