package com.pompom.creative.websocket.dto;

import java.time.Instant;
import java.util.UUID;
import lombok.Builder;
import lombok.Data;

/** WebSocket event for render job progress updates. */
@Data
@Builder
public class RenderProgressEvent {

  /** Event type. */
  private EventType type;

  /** Render job ID. */
  private UUID jobId;

  /** Job status (PENDING, RUNNING, COMPLETED, FAILED). */
  private String status;

  /** Progress percentage (0-100). */
  private Integer progressPercent;

  /** Current step description. */
  private String currentStep;

  /** Estimated time remaining in seconds. */
  private Integer estimatedSecondsRemaining;

  /** Credits used so far. */
  private Integer creditsUsed;

  /** Error message (if failed). */
  private String errorMessage;

  /** Event timestamp. */
  @Builder.Default private Instant timestamp = Instant.now();

  public enum EventType {
    JOB_STARTED,
    PROGRESS_UPDATE,
    STEP_COMPLETED,
    JOB_COMPLETED,
    JOB_FAILED,
    CREDIT_UPDATE
  }
}
