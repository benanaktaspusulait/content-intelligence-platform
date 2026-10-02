package com.pompom.creative.domain;

/** Publication job status enum. Represents the state machine for social media publishing. */
public enum PublicationStatus {
  QUEUED, // Job created, waiting to start
  UPLOADING, // Video upload in progress
  PROCESSING, // Platform is processing the video
  PUBLISHED, // Successfully published
  FAILED, // Upload or publish failed
  CANCELLED // Job cancelled by user
}
