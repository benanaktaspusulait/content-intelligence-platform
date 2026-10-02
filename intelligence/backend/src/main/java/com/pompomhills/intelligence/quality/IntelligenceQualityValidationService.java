package com.pompomhills.intelligence.quality;

import com.pompomhills.intelligence.content.ContentPromptQueryService;
import com.pompomhills.intelligence.content.ContentPromptSnapshot;
import java.time.Duration;
import java.time.Instant;
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
 * ruleset version is recorded directly; semantic/producibility/independent- revalidation identity
 * are left absent here because the ML service does not yet produce them - a later slice populates
 * those fields, and until then {@link ValidationEvidenceService} ensures such a record can never
 * read back as RENDER_READY.
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

    QualityValidationEntity entity = new QualityValidationEntity();
    entity.setPromptText(promptToValidate);
    entity.setRulesetVersion(report.rulesetVersion());
    entity.setOverallScore(report.overallScore());
    entity.setStatus(report.status());
    entity.setBlockerCount(report.blockerCount());
    entity.setCriticalCount(report.criticalCount());
    entity.setWarningCount(report.warningCount());
    entity.setValidatedAt(validatedAt);

    if (snapshot != null) {
      entity.setExpiresAt(validatedAt.plus(evidenceFreshnessTtl));
      entity.setContentId(snapshot.contentId());
      entity.setPromptVersionId(snapshot.promptVersionId());
      entity.setPromptSha256(snapshot.promptSha256());
      entity.setDeterministicRulesetVersion(report.rulesetVersion());
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
}
