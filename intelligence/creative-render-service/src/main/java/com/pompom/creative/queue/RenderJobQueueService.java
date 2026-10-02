package com.pompom.creative.queue;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import java.time.Instant;
import java.util.Optional;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Implements the idempotent render queue gate: fetches validation evidence, enforces every {@link
 * ValidationEvidencePolicy} predicate, and either replays an existing job for a reused {@code
 * Idempotency-Key} or atomically creates a new one with the accepted evidence copied in.
 *
 * <p>A rejected request (policy failure, missing/incomplete evidence) must create zero rows -
 * {@link #queue} fetches evidence and validates it before ever constructing a {@link RenderJob}.
 */
@Service
public class RenderJobQueueService {

  private final RenderJobRepository repository;
  private final RenderAttemptRepository attemptRepository;
  private final IntelligenceValidationEvidenceClient evidenceClient;
  private final ValidationEvidencePolicy policy;
  private final RequestFingerprint fingerprints;
  private final TransactionTemplate newTransaction;

  public RenderJobQueueService(
      RenderJobRepository repository,
      RenderAttemptRepository attemptRepository,
      IntelligenceValidationEvidenceClient evidenceClient,
      ValidationEvidencePolicy policy,
      RequestFingerprint fingerprints,
      PlatformTransactionManager transactionManager) {
    this.repository = repository;
    this.attemptRepository = attemptRepository;
    this.evidenceClient = evidenceClient;
    this.policy = policy;
    this.fingerprints = fingerprints;
    // Each create attempt runs in its own, explicitly-started transaction (rather than relying
    // on @Transactional, which would not create a new transaction boundary on a self-invoked
    // method anyway) so that a losing concurrent insert's aborted transaction is fully isolated:
    // the subsequent replay re-read runs in a separate transaction, never the poisoned one.
    this.newTransaction = new TransactionTemplate(transactionManager);
  }

  public QueueRenderJobResponse queue(String idempotencyKey, QueueRenderJobRequest request) {
    String fingerprint = fingerprints.sha256(request);

    Optional<RenderJob> existing = repository.findByIdempotencyKey(idempotencyKey);
    if (existing.isPresent()) {
      return replay(existing.get(), fingerprint, idempotencyKey);
    }

    try {
      return createAfterEvidenceValidation(idempotencyKey, fingerprint, request);
    } catch (DataIntegrityViolationException raceOnUniqueKey) {
      // Another concurrent request won the race to insert this idempotency key first. The
      // create attempt's own transaction (see @Transactional below) has already rolled back, so
      // this re-read runs in a fresh transaction/connection rather than the poisoned one -
      // PostgreSQL aborts an entire transaction after any failed statement within it, so the
      // re-read could never succeed inside the same transaction that saw the conflict.
      RenderJob winner =
          repository.findByIdempotencyKey(idempotencyKey).orElseThrow(() -> raceOnUniqueKey);
      return replay(winner, fingerprint, idempotencyKey);
    }
  }

  private QueueRenderJobResponse replay(
      RenderJob existing, String fingerprint, String idempotencyKey) {
    if (!existing.getRequestFingerprint().equals(fingerprint)) {
      throw new IdempotencyKeyConflictException(idempotencyKey);
    }
    return new QueueRenderJobResponse(existing.getId(), true);
  }

  private QueueRenderJobResponse createAfterEvidenceValidation(
      String idempotencyKey, String fingerprint, QueueRenderJobRequest request) {
    // Evidence fetch and policy validation happen before the transaction opens: a rejection here
    // must create zero rows and never even starts a database transaction.
    ValidationEvidenceDto evidence = evidenceClient.getEvidence(request.validationRecordId());
    policy.validate(request, evidence, Instant.now());

    RenderJob job =
        RenderJob.builder()
            .contentId(evidence.contentId())
            .promptVersionId(evidence.promptVersionId())
            .contentTitleSnapshot(String.valueOf(evidence.contentId()))
            .promptVersionNumberSnapshot(0)
            .promptSha256(evidence.promptSha256())
            .promptTextSnapshot("")
            .validationRecordId(evidence.validationRecordId())
            .evidenceDeterministicRulesetVersion(evidence.deterministicRulesetVersion())
            .evidenceSemanticProvider(evidence.semanticProvider())
            .evidenceSemanticModelVersion(evidence.semanticModelVersion())
            .evidenceProducibilityValidatorVersion(evidence.producibilityValidatorVersion())
            .evidenceIndependentRevalidationId(evidence.independentRevalidationId())
            .evidenceIndependentlyRevalidatedAt(evidence.independentlyRevalidatedAt())
            .evidenceValidatedAt(evidence.validatedAt())
            .idempotencyKey(idempotencyKey)
            .requestFingerprint(fingerprint)
            .jobType(request.jobType())
            .openartModel(request.openartModel())
            .build();

    // Runs in its own, explicitly-scoped transaction (started here, not via @Transactional on a
    // self-invoked method) so that a losing concurrent insert's constraint violation - and the
    // transaction abort PostgreSQL applies to every statement after it - stays fully contained
    // to this one attempt and never poisons the connection the caller re-reads with afterward.
    //
    // The first durable RenderAttempt row is created in the same transaction as the job: without
    // it, a job could be persisted with nothing for a worker to ever claim.
    RenderJob saved =
        newTransaction.execute(
            status -> {
              RenderJob savedJob = repository.save(job);
              attemptRepository.save(RenderAttempt.firstAttemptFor(savedJob.getId()));
              return savedJob;
            });
    return new QueueRenderJobResponse(saved.getId(), false);
  }
}
