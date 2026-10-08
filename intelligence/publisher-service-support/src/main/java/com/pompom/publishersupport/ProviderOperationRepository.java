package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublisherCapability;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import jakarta.persistence.PersistenceException;
import java.time.Instant;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.hibernate.Session;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

/**
 * Persistence boundary for provider operation state.
 *
 * <p>This repository claims an idempotency key and records a provider result. It never schedules
 * work, invokes a provider, owns a lease, or replaces the render control plane's publication
 * attempt.
 */
@Repository
public class ProviderOperationRepository {

  @PersistenceContext private EntityManager entityManager;

  private final SecretRedactor secretRedactor;
  private final PublisherRequestValidator requestValidator;

  public ProviderOperationRepository() {
    this(new SecretRedactor(), new PublisherRequestValidator());
  }

  ProviderOperationRepository(
      SecretRedactor secretRedactor, PublisherRequestValidator requestValidator) {
    this.secretRedactor = Objects.requireNonNull(secretRedactor, "secretRedactor");
    this.requestValidator = Objects.requireNonNull(requestValidator, "requestValidator");
  }

  /** Atomically claims a command key from the caller's transaction boundary. */
  @Transactional
  public OperationClaim claim(PublishCommand command) {
    return claim(command, PublisherCapability.legacy(), Instant.now());
  }

  @Transactional
  public OperationClaim claim(PublishCommand command, Instant startedAt) {
    return claim(command, PublisherCapability.legacy(), startedAt);
  }

  @Transactional
  public OperationClaim claim(PublishCommand command, PublisherCapability capability) {
    return claim(command, capability, Instant.now());
  }

  @Transactional
  public OperationClaim claim(
      PublishCommand command, PublisherCapability capability, Instant startedAt) {
    requestValidator.validate(command);
    Objects.requireNonNull(capability, "capability");
    Objects.requireNonNull(startedAt, "startedAt");

    Optional<ProviderOperationRecord> existing =
        findByCommandIdempotencyKey(capability, command.idempotencyKey());
    if (existing.isPresent()) {
      return existingClaim(command, existing.get());
    }

    ProviderOperationRecord record =
        ProviderOperationRecord.started(command, capability, startedAt);
    if (isPostgres()) {
      int inserted = insertIfAbsent(record);
      entityManager.clear();
      ProviderOperationRecord stored =
          findByCommandIdempotencyKey(capability, command.idempotencyKey())
              .orElseThrow(
                  () ->
                      new IllegalStateException(
                          "Provider operation disappeared after idempotency claim"));
      if (inserted == 0) {
        return existingClaim(command, stored);
      }
      return new OperationClaim(true, stored);
    }

    try {
      entityManager.persist(record);
      entityManager.flush();
      return new OperationClaim(true, record);
    } catch (PersistenceException exception) {
      // The unique database constraint is the final arbiter under a concurrent first claim.
      entityManager.clear();
      Optional<ProviderOperationRecord> concurrent =
          findByCommandIdempotencyKey(capability, command.idempotencyKey());
      if (concurrent.isPresent()) {
        return existingClaim(command, concurrent.get());
      }
      throw exception;
    }
  }

  @Transactional(readOnly = true)
  public Optional<ProviderOperationRecord> findByCommandIdempotencyKey(
      String commandIdempotencyKey) {
    return findByCommandIdempotencyKey(PublisherCapability.legacy(), commandIdempotencyKey);
  }

  @Transactional(readOnly = true)
  public Optional<ProviderOperationRecord> findByCommandIdempotencyKey(
      PublisherCapability capability, String commandIdempotencyKey) {
    if (capability == null || commandIdempotencyKey == null || commandIdempotencyKey.isBlank()) {
      return Optional.empty();
    }
    return entityManager
        .createQuery(
            "select record from ProviderOperationRecord record "
                + "where record.publisherCapability = :publisherCapability "
                + "and record.commandIdempotencyKey = :commandIdempotencyKey",
            ProviderOperationRecord.class)
        .setParameter("publisherCapability", capability)
        .setParameter("commandIdempotencyKey", commandIdempotencyKey)
        .getResultStream()
        .findFirst();
  }

  @Transactional(readOnly = true)
  public Optional<ProviderOperationRecord> findByPublicationAttemptId(
      PublisherCapability capability, UUID publicationAttemptId) {
    if (capability == null || publicationAttemptId == null) {
      return Optional.empty();
    }
    return entityManager
        .createQuery(
            "select record from ProviderOperationRecord record "
                + "where record.publisherCapability = :publisherCapability "
                + "and record.publicationAttemptId = :publicationAttemptId "
                + "order by record.updatedAt desc",
            ProviderOperationRecord.class)
        .setParameter("publisherCapability", capability)
        .setParameter("publicationAttemptId", publicationAttemptId)
        .setMaxResults(1)
        .getResultStream()
        .findFirst();
  }

  @Transactional(readOnly = true)
  public Optional<PublishResult> findExistingResult(String commandIdempotencyKey) {
    return findExistingResult(PublisherCapability.legacy(), commandIdempotencyKey);
  }

  @Transactional(readOnly = true)
  public Optional<PublishResult> findExistingResult(
      PublisherCapability capability, String commandIdempotencyKey) {
    return findByCommandIdempotencyKey(capability, commandIdempotencyKey)
        .filter(record -> record.getStatus() != null)
        .map(ProviderOperationRecord::toPublishResult);
  }

  /**
   * Stores only the normalized, redacted result fields; raw provider responses never cross here.
   */
  @Transactional
  public ProviderOperationRecord recordResult(String commandIdempotencyKey, PublishResult result) {
    return recordResult(PublisherCapability.legacy(), commandIdempotencyKey, result, Instant.now());
  }

  @Transactional
  public ProviderOperationRecord recordResult(
      String commandIdempotencyKey, PublishResult result, Instant completedAt) {
    return recordResult(PublisherCapability.legacy(), commandIdempotencyKey, result, completedAt);
  }

  @Transactional
  public ProviderOperationRecord recordResult(
      PublisherCapability capability, String commandIdempotencyKey, PublishResult result) {
    return recordResult(capability, commandIdempotencyKey, result, Instant.now());
  }

  @Transactional
  public ProviderOperationRecord recordResult(
      PublisherCapability capability,
      String commandIdempotencyKey,
      PublishResult result,
      Instant completedAt) {
    Objects.requireNonNull(capability, "capability");
    Objects.requireNonNull(commandIdempotencyKey, "commandIdempotencyKey");
    Objects.requireNonNull(result, "result");
    Objects.requireNonNull(completedAt, "completedAt");
    ProviderOperationRecord record =
        findByCommandIdempotencyKey(capability, commandIdempotencyKey)
            .orElseThrow(
                () ->
                    new IllegalArgumentException(
                        "No provider operation claimed for command idempotency key"));
    record.apply(result, completedAt, secretRedactor);
    entityManager.flush();
    return record;
  }

  private OperationClaim existingClaim(
      PublishCommand command, ProviderOperationRecord existingOperation) {
    if (!PublisherCommandFingerprint.sha256(command)
        .equals(existingOperation.getCommandFingerprint())) {
      throw new IllegalArgumentException(
          "idempotency key is already bound to a different publish command");
    }
    return new OperationClaim(false, existingOperation);
  }

  private int insertIfAbsent(ProviderOperationRecord record) {
    Instant now = Instant.now();
    return entityManager
        .createNativeQuery(
            "INSERT INTO publisher_support.provider_operation_records ("
                + "id, publication_job_id, publication_attempt_id, command_idempotency_key, "
                + "publisher_capability, command_fingerprint, started_at, reconciliation_required, "
                + "created_at, updated_at, entity_version) "
                + "VALUES (:id, :publicationJobId, :publicationAttemptId, "
                + ":commandIdempotencyKey, :publisherCapability, :commandFingerprint, :startedAt, "
                + "FALSE, :createdAt, :updatedAt, 0) "
                + "ON CONFLICT (publisher_capability, command_idempotency_key) DO NOTHING")
        .setParameter("id", UUID.randomUUID())
        .setParameter("publicationJobId", record.getPublicationJobId())
        .setParameter("publicationAttemptId", record.getPublicationAttemptId())
        .setParameter("commandIdempotencyKey", record.getCommandIdempotencyKey())
        .setParameter("publisherCapability", record.getPublisherCapability().wireValue())
        .setParameter("commandFingerprint", record.getCommandFingerprint())
        .setParameter("startedAt", record.getStartedAt())
        .setParameter("createdAt", now)
        .setParameter("updatedAt", now)
        .executeUpdate();
  }

  private boolean isPostgres() {
    try {
      return entityManager
          .unwrap(Session.class)
          .doReturningWork(
              connection ->
                  connection.getMetaData().getDatabaseProductName().contains("PostgreSQL"));
    } catch (RuntimeException exception) {
      return false;
    }
  }

  public record OperationClaim(boolean newOperation, ProviderOperationRecord operation) {
    public OperationClaim {
      Objects.requireNonNull(operation, "operation");
    }

    public Optional<PublishResult> existingResult() {
      return newOperation || operation.getStatus() == null
          ? Optional.empty()
          : Optional.of(operation.toPublishResult());
    }
  }
}
