package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Converter;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/** Durable provider-side operation state, deliberately separate from control-plane attempts. */
@Entity
@Table(
    name = "provider_operation_records",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_provider_operation_command_idempotency_key",
            columnNames = "command_idempotency_key"))
public class ProviderOperationRecord {

  public static final int MAX_IDENTIFIER_LENGTH = 200;

  @Id
  @GeneratedValue(strategy = GenerationType.UUID)
  private UUID id;

  @Column(name = "publication_job_id", nullable = false, updatable = false)
  private UUID publicationJobId;

  @Column(name = "publication_attempt_id", nullable = false, updatable = false)
  private UUID publicationAttemptId;

  @Column(name = "command_idempotency_key", nullable = false, updatable = false, length = 200)
  private String commandIdempotencyKey;

  @Column(name = "command_fingerprint", nullable = false, updatable = false, length = 64)
  private String commandFingerprint;

  @Column(name = "provider_request_id", length = 200)
  private String providerRequestId;

  @Column(name = "status", length = 40)
  @Convert(converter = PublishStatusConverter.class)
  private PublishStatus status;

  @Column(name = "provider_post_id", length = 200)
  private String providerPostId;

  @Column(name = "provider_video_id", length = 200)
  private String providerVideoId;

  @Column(name = "permalink", columnDefinition = "TEXT")
  private String permalink;

  @Column(name = "error_class", length = 50)
  @Convert(converter = PublishErrorClassConverter.class)
  private PublishErrorClass errorClass;

  @Column(name = "message", columnDefinition = "TEXT")
  private String message;

  @Column(name = "started_at", nullable = false)
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Column(name = "reconciliation_required", nullable = false)
  private boolean reconciliationRequired;

  @Column(name = "created_at", nullable = false, updatable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Version
  @Column(name = "entity_version", nullable = false)
  private Integer entityVersion;

  protected ProviderOperationRecord() {}

  static ProviderOperationRecord started(PublishCommand command, Instant startedAt) {
    ProviderOperationRecord record = new ProviderOperationRecord();
    record.publicationJobId = command.publicationJobId();
    record.publicationAttemptId = command.publicationAttemptId();
    record.commandIdempotencyKey = command.idempotencyKey();
    record.commandFingerprint = PublisherCommandFingerprint.sha256(command);
    record.startedAt = startedAt;
    record.reconciliationRequired = false;
    return record;
  }

  void apply(PublishResult result, Instant completedAt, SecretRedactor redactor) {
    Objects.requireNonNull(result, "result");
    Objects.requireNonNull(result.status(), "publish result status is required");
    validateIdentifiers(result);

    if (status != null) {
      PublishResult existingResult = toPublishResult();
      if (existingResult.equals(result)) {
        return;
      }
      if (lifecycleRank(result.status()) <= lifecycleRank(status)) {
        throw new IllegalStateException(
            "provider operation has a terminal or non-advancing result and cannot be overwritten");
      }
    }

    status = result.status();
    providerPostId = result.providerPostId();
    providerVideoId = result.providerVideoId();
    permalink = result.permalink();
    providerRequestId = result.providerRequestId();
    errorClass =
        result.errorClass() == null ? null : PublishErrorClass.fromWireValue(result.errorClass());
    message = redactor.redactProviderResponse(result.message());
    reconciliationRequired = result.reconciliationRequired();
    this.completedAt = completedAt;
  }

  private int lifecycleRank(PublishStatus lifecycleStatus) {
    return switch (lifecycleStatus) {
      case ACCEPTED -> 1;
      case RECONCILIATION_REQUIRED -> 2;
      case COMPLETED, FAILED -> 3;
    };
  }

  private void validateIdentifiers(PublishResult result) {
    validateIdentifier("providerRequestId", result.providerRequestId());
    validateIdentifier("providerPostId", result.providerPostId());
    validateIdentifier("providerVideoId", result.providerVideoId());
  }

  private void validateIdentifier(String fieldName, String value) {
    if (value != null && value.length() > MAX_IDENTIFIER_LENGTH) {
      throw new IllegalArgumentException(
          fieldName + " exceeds the persisted maximum of " + MAX_IDENTIFIER_LENGTH + " characters");
    }
  }

  public PublishResult toPublishResult() {
    if (status == null) {
      throw new IllegalStateException("provider operation has no provider result yet");
    }
    return new PublishResult(
        status,
        providerPostId,
        providerVideoId,
        permalink,
        providerRequestId,
        errorClass == null ? null : errorClass.wireValue(),
        message,
        reconciliationRequired);
  }

  @PrePersist
  void prePersist() {
    Instant now = Instant.now();
    if (createdAt == null) {
      createdAt = now;
    }
    if (updatedAt == null) {
      updatedAt = now;
    }
  }

  @PreUpdate
  void preUpdate() {
    updatedAt = Instant.now();
  }

  public UUID getId() {
    return id;
  }

  public UUID getPublicationJobId() {
    return publicationJobId;
  }

  public UUID getPublicationAttemptId() {
    return publicationAttemptId;
  }

  public String getCommandIdempotencyKey() {
    return commandIdempotencyKey;
  }

  public String getCommandFingerprint() {
    return commandFingerprint;
  }

  public String getProviderRequestId() {
    return providerRequestId;
  }

  public PublishStatus getStatus() {
    return status;
  }

  public PublishErrorClass getErrorClass() {
    return errorClass;
  }

  public String getProviderPostId() {
    return providerPostId;
  }

  public String getProviderVideoId() {
    return providerVideoId;
  }

  public String getPermalink() {
    return permalink;
  }

  public String getMessage() {
    return message;
  }

  public Instant getStartedAt() {
    return startedAt;
  }

  public Instant getCompletedAt() {
    return completedAt;
  }

  public boolean isReconciliationRequired() {
    return reconciliationRequired;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public Instant getUpdatedAt() {
    return updatedAt;
  }

  public Integer getEntityVersion() {
    return entityVersion;
  }

  @Converter
  public static class PublishStatusConverter implements AttributeConverter<PublishStatus, String> {
    @Override
    public String convertToDatabaseColumn(PublishStatus status) {
      return status == null ? null : status.wireValue();
    }

    @Override
    public PublishStatus convertToEntityAttribute(String value) {
      return value == null ? null : PublishStatus.fromWireValue(value);
    }
  }

  @Converter
  public static class PublishErrorClassConverter
      implements AttributeConverter<PublishErrorClass, String> {
    @Override
    public String convertToDatabaseColumn(PublishErrorClass errorClass) {
      return errorClass == null ? null : errorClass.wireValue();
    }

    @Override
    public PublishErrorClass convertToEntityAttribute(String value) {
      return value == null ? null : PublishErrorClass.fromWireValue(value);
    }
  }
}
