package com.pompom.creative.domain;

import java.util.EnumSet;
import java.util.Set;

/**
 * Persisted execution stage of a {@link RenderAttempt}. A worker claiming an attempt executes
 * exactly the stage the attempt is currently in and persists the next stage before releasing the
 * lease - never more than one stage per claim.
 */
public enum RenderExecutionStage {
  QUEUED,
  SUBMITTING,
  PROVIDER_QUEUED,
  POLLING,
  DOWNLOADING,
  POST_RENDER_QA,
  RETRY_WAIT,
  COMPLETE,
  FAILED,
  ABANDONED,
  NEEDS_HUMAN_REVIEW;

  /**
   * Stages an attempt row never transitions out of once reached, and so can never be claim-eligible
   * again. {@code RETRY_WAIT} is included even though it is not a terminal *outcome* for the job (a
   * rerender always inserts a new attempt row to carry the job forward) - it is a dead end for this
   * specific row, and {@code RenderAttemptOrchestrator.processAttempt} has no stage handler for it.
   *
   * <p>{@code SUBMITTING} is included because it is an externally-visible uncertainty boundary: once
   * the intent is committed, automatic resubmission could duplicate a provider generation. It must be
   * reconciled by an operator rather than claimed again automatically.
   *
   * <p>This is the single source of truth for claim-unclaimability: {@code
   * JdbcRenderAttemptClaimRepository} builds its SQL exclusion list from this set rather than
   * maintaining a separate hand-written list, so the two can never drift out of sync.
   */
  private static final Set<RenderExecutionStage> UNCLAIMABLE =
      EnumSet.of(
          SUBMITTING, COMPLETE, FAILED, ABANDONED, NEEDS_HUMAN_REVIEW, RETRY_WAIT);

  public boolean isUnclaimable() {
    return UNCLAIMABLE.contains(this);
  }

  public static Set<RenderExecutionStage> unclaimableStages() {
    return EnumSet.copyOf(UNCLAIMABLE);
  }
}
