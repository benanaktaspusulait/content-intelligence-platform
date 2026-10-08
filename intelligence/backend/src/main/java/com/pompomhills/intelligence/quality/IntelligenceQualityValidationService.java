package com.pompomhills.intelligence.quality;

import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.content.ContentPromptSnapshot;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Backs the public {@code POST /api/v1/intelligence/quality/validate} endpoint.
 *
 * <p>Every persisted record gets a {@code validatedAt} timestamp, linked or not. When the request
 * links to a real content/prompt version, the ML service is called with the stored immutable prompt
 * text (never the request body's text - the request body is only used for standalone, permanently
 * non-renderable validations), and the persisted record is additionally populated with the evidence
 * fields {@link ValidationEvidenceService} requires, including an {@code expiresAt} one freshness
 * TTL after {@code validatedAt} so evidence cannot authorize render indefinitely. Deterministic
 * ruleset, semantic provider/model and producibility-validator provenance are copied from the ML
 * response. A linked validation that is initially render-ready is validated a second time and the
 * two executions are persisted as separate rows before the primary row can reference the
 * independent run.
 */
@Service
public class IntelligenceQualityValidationService {

  private static final Logger log =
      LoggerFactory.getLogger(IntelligenceQualityValidationService.class);

  private final QualityMlClient mlClient;
  private final QualityValidationRepository repository;
  private final ContentPromptQueryService contentPrompts;
  private final Duration evidenceFreshnessTtl;

  public IntelligenceQualityValidationService(
      QualityMlClient mlClient,
      QualityValidationRepository repository,
      ContentPromptQueryService contentPrompts,
      @Value("${pompom.quality.evidence-freshness-ttl:PT24H}") Duration evidenceFreshnessTtl) {
    this.mlClient = mlClient;
    this.repository = repository;
    this.contentPrompts = contentPrompts;
    this.evidenceFreshnessTtl = evidenceFreshnessTtl;
  }

  @Transactional
  public IntelligenceValidateResponse validateAndPersistEvidence(
      IntelligenceValidateRequest request) {
    boolean linked = request.contentId() != null && request.promptVersionId() != null;

    if (!linked) {
      requireValidStandalonePrompt(request.prompt());
    }

    ContentPromptSnapshot snapshot =
        linked ? contentPrompts.load(request.contentId(), request.promptVersionId()) : null;

    String promptToValidate = linked ? snapshot.promptText() : request.prompt();

    log.info(
        "Validating {} prompt with ruleset version: {}",
        linked ? "linked" : "standalone",
        request.rulesetVersion());

    QualityReportDto report = mlClient.validatePrompt(promptToValidate, request.rulesetVersion());
    Instant validatedAt = Instant.now();
    QualityValidationEntity entity =
        buildEntity(promptToValidate, snapshot, report, validatedAt, UUID.randomUUID());

    if (snapshot != null && "RENDER_READY".equals(report.status())) {
      QualityReportDto independentReport =
          mlClient.validatePrompt(promptToValidate, report.rulesetVersion());
      Instant independentlyValidatedAt = Instant.now();
      UUID independentRunId = UUID.randomUUID();
      QualityValidationEntity independent =
          buildEntity(
              promptToValidate,
              snapshot,
              independentReport,
              independentlyValidatedAt,
              independentRunId);
      repository.saveAndFlush(independent);

      if (sameAuthorizationDecision(report, independentReport)) {
        entity.setIndependentRevalidationId(independentRunId);
        entity.setIndependentlyRevalidatedAt(independentlyValidatedAt);
      }
    }

    QualityValidationEntity saved = repository.save(entity);

    log.info(
        "Validation complete: score={}, status={}, id={}, linked={}",
        report.overallScore(),
        report.status(),
        saved.getId(),
        linked);

    return new IntelligenceValidateResponse(saved.getId(), report);
  }

  @Transactional
  public IntelligenceValidateResponse validateWorkflowProfile(
      java.util.Map<String, Object> review) {
    var snapshot =
        contentPrompts.load(
            ((Number) review.get("contentId")).longValue(),
            ((Number) review.get("promptVersionId")).longValue());
    @SuppressWarnings("unchecked")
    var bound = (java.util.Map<String, Object>) review.get("boundRequest");
    if (!snapshot.promptText().equals(bound.get("prompt")))
      throw new IllegalArgumentException("Review source is stale");
    var report = mlClient.validatePromptForWorkflow(snapshot.promptText(), "latest", null, bound);
    var entity =
        buildEntity(snapshot.promptText(), snapshot, report, Instant.now(), UUID.randomUUID());
    if ("RENDER_READY".equals(report.status())) {
      String base = report.rulesetVersion().split("\\+", 2)[0];
      var independentReport =
          mlClient.validatePromptForWorkflow(snapshot.promptText(), base, null, bound);
      var independent =
          buildEntity(
              snapshot.promptText(), snapshot, independentReport, Instant.now(), UUID.randomUUID());
      repository.saveAndFlush(independent);
      if (sameAuthorizationDecision(report, independentReport)) {
        entity.setIndependentRevalidationId(independent.getValidationRunId());
        entity.setIndependentlyRevalidatedAt(independent.getValidatedAt());
      }
    }
    var saved = repository.save(entity);
    return new IntelligenceValidateResponse(saved.getId(), report);
  }

  @SuppressWarnings("unchecked")
  private java.util.Map<String, Object> profileContext(QualityValidationEntity entity) {
    var assessment = QualityReportSnapshots.preRenderAssessment(entity.getReportJson());
    if (assessment == null
        || !(assessment.get("canonicalProfileAdmission") instanceof java.util.Map<?, ?> projection))
      return null;
    return projection.get("boundRequest") instanceof java.util.Map<?, ?> context
        ? (java.util.Map<String, Object>) context
        : null;
  }

  private QualityReportDto validateVisual(
      QualityValidationEntity parent, java.util.Map<String, Object> visualEvidence) {
    var context = profileContext(parent);
    return context == null
        ? mlClient.validatePrompt(
            parent.getPromptText(), parent.getRulesetVersion(), visualEvidence)
        : mlClient.validatePromptForWorkflow(
            parent.getPromptText(),
            parent.getRulesetVersion().split("\\+", 2)[0],
            visualEvidence,
            context);
  }

  private QualityValidationEntity buildEntity(
      String prompt,
      ContentPromptSnapshot snapshot,
      QualityReportDto report,
      Instant validatedAt,
      UUID validationRunId) {
    QualityValidationEntity entity = new QualityValidationEntity();
    entity.setValidationRunId(validationRunId);
    entity.setPromptText(prompt);
    entity.setRulesetVersion(report.rulesetVersion());
    entity.setOverallScore(report.overallScore());
    entity.setStatus(report.status());
    entity.setBlockerCount(report.blockerCount());
    entity.setCriticalCount(report.criticalCount());
    entity.setWarningCount(report.warningCount());
    entity.setValidatedAt(validatedAt);
    entity.setReportJson(QualityReportSnapshots.toJson(report));
    entity.setPromptFingerprint(QualityReportSnapshots.fingerprint(prompt));

    if (snapshot != null) {
      entity.setExpiresAt(validatedAt.plus(evidenceFreshnessTtl));
      entity.setContentId(snapshot.contentId());
      entity.setPromptVersionId(snapshot.promptVersionId());
      entity.setPromptSha256(snapshot.promptSha256());
      entity.setDeterministicRulesetVersion(report.rulesetVersion());
      QualityProvenanceDto provenance = report.provenance();
      if (provenance != null) {
        entity.setSemanticProvider(provenance.semanticProvider());
        entity.setSemanticModelVersion(provenance.semanticModelVersion());
        // producibilityValidatorVersion is deliberately NOT populated here. There is no
        // independent "producibility validator" runtime: AI producibility validation is a
        // family of ordinary deterministic rules in the versioned ruleset, already fully
        // identified by deterministicRulesetVersion above. Writing a value here (even the ML
        // response's own producibilityValidatorVersion, which is itself a fabricated static
        // config string, not real provenance) would make this evidence record claim a kind of
        // verification that never happened. See ValidationEvidenceService/ValidationEvidencePolicy,
        // which no longer require this field, and PART_01_COMPLETION_ROADMAP.md's Plan C1.
      }
    }
    return entity;
  }

  private boolean sameAuthorizationDecision(
      QualityReportDto primary, QualityReportDto independent) {
    if (!"RENDER_READY".equals(independent.status())) {
      return false;
    }
    if (!primary.rulesetVersion().equals(independent.rulesetVersion())) {
      return false;
    }
    QualityProvenanceDto first = primary.provenance();
    QualityProvenanceDto second = independent.provenance();
    return first != null
        && second != null
        && "PRE_RENDER".equals(first.evaluationStage())
        && first.equals(second);
  }

  /**
   * Enforces the length requirement that used to live on {@link IntelligenceValidateRequest} as a
   * declarative constraint. Only applies to standalone (unlinked) requests, since a linked request
   * never uses this field at all.
   */
  private void requireValidStandalonePrompt(String prompt) {
    if (prompt == null || prompt.isBlank()) {
      throw new IllegalArgumentException("Prompt text cannot be blank");
    }
    int length = prompt.length();
    if (length < 100 || length > 10000) {
      throw new IllegalArgumentException("Prompt must be between 100-10000 characters");
    }
  }

  /**
   * Explicitly revalidates a linked prompt after both visual gates have supplied evidence.
   * The original report_json snapshot is never rewritten; the two new validation rows preserve
   * the visual-evidence revalidation and its independent run as immutable history.
   */
  @Transactional
  public void revalidateWithVisualEvidence(
      QualityValidationEntity parent, java.util.Map<String, Object> visualEvidence) {
    if (parent.getContentId() == null || parent.getPromptVersionId() == null) return;
    ContentPromptSnapshot snapshot =
        contentPrompts.load(parent.getContentId(), parent.getPromptVersionId());
    QualityReportDto first = validateVisual(parent, visualEvidence);
    Instant firstAt = Instant.now();
    UUID firstRunId = UUID.randomUUID();
    QualityValidationEntity firstEntity =
        buildEntity(parent.getPromptText(), snapshot, first, firstAt, firstRunId);
    repository.saveAndFlush(firstEntity);
    if (!"RENDER_READY".equals(first.status())) return;

    QualityReportDto independent = validateVisual(parent, visualEvidence);
    Instant independentAt = Instant.now();
    UUID independentRunId = UUID.randomUUID();
    QualityValidationEntity independentEntity =
        buildEntity(parent.getPromptText(), snapshot, independent, independentAt, independentRunId);
    repository.saveAndFlush(independentEntity);
    if (sameAuthorizationDecision(first, independent)) {
      parent.setIndependentRevalidationId(independentRunId);
      parent.setIndependentlyRevalidatedAt(independentAt);
      repository.save(parent);
    }
  }
}
