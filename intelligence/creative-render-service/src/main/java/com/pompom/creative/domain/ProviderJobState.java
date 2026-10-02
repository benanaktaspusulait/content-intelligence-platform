package com.pompom.creative.domain;

/**
 * Provider (OpenArt) job state as reported by a status poll. {@code UNKNOWN} covers malformed or
 * unrecognized provider responses and must never be treated as success - only {@code SUCCEEDED} may
 * transition an attempt to {@link RenderExecutionStage#DOWNLOADING}.
 */
public enum ProviderJobState {
  QUEUED,
  RUNNING,
  SUCCEEDED,
  FAILED,
  CANCELLED,
  UNKNOWN
}
