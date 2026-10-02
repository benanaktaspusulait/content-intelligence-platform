package com.pompom.creative.websocket.dto;

import com.pompom.creative.oauth.PlatformType;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;
import lombok.Builder;
import lombok.Data;

/** WebSocket event for metrics collection updates. */
@Data
@Builder
public class MetricsUpdateEvent {

  /** Event type. */
  private EventType type;

  /** Publication job ID. */
  private UUID publicationJobId;

  /** Platform. */
  private PlatformType platform;

  /** Platform video ID. */
  private String platformVideoId;

  /** Collection point (T+30M, T+1H, etc.). */
  private String collectionPoint;

  /** Current views. */
  private Long views;

  /** Current likes. */
  private Long likes;

  /** Current comments. */
  private Long comments;

  /** Current shares. */
  private Long shares;

  /** Engagement rate percentage. */
  private BigDecimal engagementRate;

  /** Virality score. */
  private BigDecimal viralityScore;

  /** Performance category (if classified). */
  private String performanceCategory;

  /** Trajectory shape (if analyzed). */
  private String trajectoryShape;

  /** Event timestamp. */
  @Builder.Default private Instant timestamp = Instant.now();

  public enum EventType {
    METRICS_COLLECTED,
    PERFORMANCE_CLASSIFIED,
    TRAJECTORY_ANALYZED,
    MILESTONE_REACHED
  }
}
