package com.pompom.creative.queue;

import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderJob;
import com.pompom.creative.contract.CreativeProductionContractService;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.contract.PromptConstraintCompiler;
import com.pompom.creative.evidence.IntelligenceValidationEvidenceClient;
import com.pompom.creative.evidence.ValidationEvidenceDto;
import com.pompom.creative.intelligence.ContentPromptSnapshot;
import com.pompom.creative.intelligence.IntelligenceContentClient;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.service.BudgetAlertService;
import com.pompom.creative.service.CreditTrackingService;
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
  private final IntelligenceContentClient contentClient;
  private final ValidationEvidencePolicy policy;
  private final RequestFingerprint fingerprints;
  private final CreditTrackingService creditTrackingService;
  private final BudgetAlertService budgetAlertService;
  private final CreativeProductionContractService contractService;
  private final TransactionTemplate newTransaction;

  public RenderJobQueueService(
      RenderJobRepository repository,
      RenderAttemptRepository attemptRepository,
      IntelligenceValidationEvidenceClient evidenceClient,
      IntelligenceContentClient contentClient,
      ValidationEvidencePolicy policy,
      RequestFingerprint fingerprints,
      CreditTrackingService creditTrackingService,
      BudgetAlertService budgetAlertService,
      CreativeProductionContractService contractService,
      PlatformTransactionManager transactionManager) {
    this.repository = repository;
    this.attemptRepository = attemptRepository;
    this.evidenceClient = evidenceClient;
    this.contentClient = contentClient;
    this.policy = policy;
    this.fingerprints = fingerprints;
    this.creditTrackingService = creditTrackingService;
    this.budgetAlertService = budgetAlertService;
    this.contractService = contractService;
    // Each create attempt runs in its own, explicitly-started transaction (rather than relying
    // on @Transactional, which would not create a new transaction boundary on a self-invoked
    // method anyway) so that a losing concurrent insert's aborted transaction is fully isolated:
    // the subsequent replay re-read runs in a separate transaction, never the poisoned one.
    this.newTransaction = new TransactionTemplate(transactionManager);
  }

  /** Compatibility constructor for focused unit tests and legacy callers. */
  public RenderJobQueueService(
      RenderJobRepository repository,
      RenderAttemptRepository attemptRepository,
      IntelligenceValidationEvidenceClient evidenceClient,
      IntelligenceContentClient contentClient,
      ValidationEvidencePolicy policy,
      RequestFingerprint fingerprints,
      CreditTrackingService creditTrackingService,
      BudgetAlertService budgetAlertService,
      PlatformTransactionManager transactionManager) {
    this(
        repository,
        attemptRepository,
        evidenceClient,
        contentClient,
        policy,
        fingerprints,
        creditTrackingService,
        budgetAlertService,
        new CreativeProductionContractService(new ObjectMapper(), new PromptConstraintCompiler()),
        transactionManager);
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
    ContentPromptSnapshot prompt =
        contentClient.fetch(request.contentId(), request.promptVersionId());
    if (prompt.contentId() != evidence.contentId()
        || prompt.promptVersionId() != evidence.promptVersionId()
        || !prompt.promptSha256().equals(evidence.promptSha256())) {
      throw new ValidationEvidenceRejectedException(
          "PROMPT_SNAPSHOT_MISMATCH",
          "Canonical prompt snapshot does not match the render-authorizing evidence");
    }
    if (!"RENDER_READY".equals(prompt.contentStatus())) {
      throw new ValidationEvidenceRejectedException(
          "CONTENT_NOT_RENDER_READY", "Content is not in the RENDER_READY state");
    }
    if (prompt.promptText() == null || prompt.promptText().isBlank()) {
      throw new ValidationEvidenceRejectedException(
          "PROMPT_TEXT_EMPTY", "Canonical approved prompt text is empty");
    }
    CreativeProductionContractService.ContractCompilation contract =
        contractService.compile(prompt, evidence.deterministicRulesetVersion());
    if ("INCOMPLETE".equals(contract.contract().status())
        || "SERVICE_ERROR".equals(contract.contract().status())) {
      throw new ValidationEvidenceRejectedException(
          "CREATIVE_CONTRACT_INCOMPLETE",
          "Validated prompt cannot produce a complete creative production contract: "
              + contract.contract().errors());
    }
    budgetAlertService.checkBudgetBeforeRender();
    if (!creditTrackingService.canAffordRender(request.jobType())) {
      throw new IllegalStateException("Insufficient render budget");
    }
    java.math.BigDecimal estimatedCredits =
        creditTrackingService.getEstimatedCost(request.jobType());

    RenderJob job =
        RenderJob.builder()
            .contentId(evidence.contentId())
            .promptVersionId(evidence.promptVersionId())
            .contentTitleSnapshot(prompt.contentTitle())
            .promptVersionNumberSnapshot(prompt.promptVersionNumber())
            .promptSha256(prompt.promptSha256())
            .promptTextSnapshot(prompt.promptText())
            .generationPromptSnapshot(contract.generationPromptSnapshot())
            .creativeContractVersion(contract.contract().contractVersion())
            .creativeContractStatus(contract.contract().status())
            .creativeContractSnapshot(contract.contractJson())
            .compiledGenerationConstraints(contract.constraintsJson())
            .constraintCompilerVersion(contract.constraints().compilerVersion())
            .compiledConstraintsSha256(contract.constraintsSha256())
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
            .openartParams(toJson(request.openartParams()))
            .creditsEstimated(estimatedCredits)
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

  private String toJson(java.util.Map<String, Object> parameters) {
    try {
      return new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(parameters);
    } catch (com.fasterxml.jackson.core.JsonProcessingException error) {
      throw new IllegalArgumentException("Provider parameters are not serializable", error);
    }
  }
}
