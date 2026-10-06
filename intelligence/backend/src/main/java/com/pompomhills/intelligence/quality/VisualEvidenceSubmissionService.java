package com.pompomhills.intelligence.quality;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.VisualEvidenceDtos.VisualEvidenceRequest;
import com.pompomhills.intelligence.quality.VisualEvidenceDtos.VisualEvidenceResponse;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class VisualEvidenceSubmissionService {
  private static final Pattern SHA256 = Pattern.compile("^[0-9a-f]{64}$");
  private static final java.util.Set<String> GATES = java.util.Set.of("FIRST_FRAME", "SILHOUETTE");
  private static final java.util.Set<String> STATUSES = java.util.Set.of("PASS", "FAIL", "PENDING", "UNKNOWN");

  private final QualityValidationRepository validations;
  private final ValidationVisualEvidenceRepository evidence;
  private final ObjectMapper objectMapper;
  private final IntelligenceQualityValidationService revalidation;

  public VisualEvidenceSubmissionService(
      QualityValidationRepository validations,
      ValidationVisualEvidenceRepository evidence,
      ObjectMapper objectMapper) {
    this(validations, evidence, objectMapper, null);
  }

  @Autowired
  public VisualEvidenceSubmissionService(
      QualityValidationRepository validations,
      ValidationVisualEvidenceRepository evidence,
      ObjectMapper objectMapper,
      IntelligenceQualityValidationService revalidation) {
    this.validations = validations;
    this.evidence = evidence;
    this.objectMapper = objectMapper;
    this.revalidation = revalidation;
  }

  @Transactional
  public VisualEvidenceResponse submit(long validationRecordId, VisualEvidenceRequest request) {
    QualityValidationEntity validation =
        validations.findById(validationRecordId)
            .orElseThrow(() -> new ValidationEvidenceNotFoundException(validationRecordId));
    validateRequest(validation, request);

    var replay = evidence.findBySubmissionKey(request.submissionKey());
    if (replay.isPresent()) {
      ValidationVisualEvidenceEntity existing = replay.get();
      if (!sameSubmission(existing, validationRecordId, request)) {
        throw new VisualEvidenceConflictException("submissionKey was already used for a different payload");
      }
      return response(validation, existing, false);
    }

    ValidationVisualEvidenceEntity row = new ValidationVisualEvidenceEntity();
    row.setValidationRecordId(validationRecordId);
    row.setContentId(request.contentId());
    row.setPromptVersionId(request.promptVersionId());
    row.setPromptSha256(request.promptSha256());
    row.setVisualGate(request.gate());
    row.setStatus(request.status());
    row.setEvidenceSetId(request.evidenceSetId());
    row.setRenderJobId(request.renderJobId());
    row.setRenderAssetId(request.renderAssetId());
    row.setAssetType(request.assetType());
    row.setAssetRelativePath(request.assetRelativePath());
    row.setAssetSha256(request.assetSha256());
    row.setProvenanceJson(writeJson(request.provenance()));
    row.setReason(request.reason().trim());
    row.setVerificationId(request.verificationId());
    row.setVerifiedAt(request.verifiedAt());
    row.setSubmissionKey(request.submissionKey());
    row.setSubmittedAt(Instant.now());
    ValidationVisualEvidenceEntity saved = evidence.saveAndFlush(row);
    Map<String, Object> visual = ValidationVisualEvidenceProjection.project(latest(validation.getId()));
    if (revalidation != null && Boolean.TRUE.equals(visual.get("finalVideoEligible"))) {
      revalidation.revalidateWithVisualEvidence(validation, visual);
    }
    return response(validation, saved, true);
  }

  private void validateRequest(QualityValidationEntity validation, VisualEvidenceRequest request) {
    if (request == null || request.contentId() == null || request.promptVersionId() == null
        || request.promptSha256() == null || !SHA256.matcher(request.promptSha256()).matches()) {
      throw new VisualEvidenceInvalidException("content identity and lowercase prompt SHA-256 are required");
    }
    if (!Objects.equals(validation.getContentId(), request.contentId())
        || !Objects.equals(validation.getPromptVersionId(), request.promptVersionId())
        || !Objects.equals(validation.getPromptSha256(), request.promptSha256())) {
      throw new VisualEvidenceConflictException("visual evidence does not match the validation prompt snapshot");
    }
    if (request.gate() == null || !GATES.contains(request.gate())
        || request.status() == null || !STATUSES.contains(request.status())) {
      throw new VisualEvidenceInvalidException("gate and status must use the visual evidence vocabulary");
    }
    if (request.submissionKey() == null || request.submissionKey().isBlank()
        || request.reason() == null || request.reason().isBlank()) {
      throw new VisualEvidenceInvalidException("submissionKey and reason are required");
    }
    if (request.assetRelativePath() != null
        && (request.assetRelativePath().startsWith("/") || request.assetRelativePath().contains(".."))) {
      throw new VisualEvidenceInvalidException("assetRelativePath must be a relative, traversal-free path");
    }
    if ("PASS".equals(request.status()) || "FAIL".equals(request.status())) {
      if (request.evidenceSetId() == null || request.renderJobId() == null || request.renderAssetId() == null
          || !"FIRST_FRAME".equals(request.assetType()) || request.assetSha256() == null
          || !SHA256.matcher(request.assetSha256()).matches() || request.provenance() == null
          || request.provenance().isEmpty() || request.verificationId() == null
          || request.verificationId().isBlank() || request.verifiedAt() == null) {
        throw new VisualEvidenceInvalidException("verified visual results require complete asset and verifier provenance");
      }
    }
    if ("PASS".equals(request.status()) && request.gate().equals("SILHOUETTE")) {
      var latest = latest(validation.getId());
      ValidationVisualEvidenceEntity first = latest.stream()
          .filter(row -> "FIRST_FRAME".equals(row.getVisualGate()) && "PASS".equals(row.getStatus()))
          .reduce((a, b) -> b).orElse(null);
      if (first != null && (!Objects.equals(first.getEvidenceSetId(), request.evidenceSetId())
          || !Objects.equals(first.getRenderAssetId(), request.renderAssetId())
          || !Objects.equals(first.getAssetSha256(), request.assetSha256()))) {
        throw new VisualEvidenceConflictException("both visual gates must use the same first-frame asset identity");
      }
    }
  }

  private boolean sameSubmission(ValidationVisualEvidenceEntity row, long validationId, VisualEvidenceRequest request) {
    return row.getValidationRecordId().equals(validationId)
        && Objects.equals(row.getVisualGate(), request.gate())
        && Objects.equals(row.getStatus(), request.status())
        && Objects.equals(row.getEvidenceSetId(), request.evidenceSetId())
        && Objects.equals(row.getRenderAssetId(), request.renderAssetId())
        && Objects.equals(row.getAssetSha256(), request.assetSha256());
  }

  private List<ValidationVisualEvidenceEntity> latest(long validationId) {
    return evidence.findByValidationRecordIdOrderBySubmittedAtAscIdAsc(validationId);
  }

  private VisualEvidenceResponse response(
      QualityValidationEntity validation, ValidationVisualEvidenceEntity row, boolean created) {
    List<ValidationVisualEvidenceEntity> rows = latest(validation.getId());
    Map<String, Object> visual = ValidationVisualEvidenceProjection.project(rows);
    boolean promptEligible = promptStageEligible(validation);
    boolean finalEligible = ValidationVisualEvidenceProjection.finalVideoEligible(rows);
    return new VisualEvidenceResponse(validation.getId(), row.getId(), row.getVisualGate(), row.getStatus(), promptEligible, finalEligible, visual, created);
  }

  private boolean promptStageEligible(QualityValidationEntity validation) {
    QualityReportDto report = QualityReportSnapshots.fromJson(validation.getReportJson());
    if (report == null || report.preRenderAssessment() == null) return false;
    Object stage = report.preRenderAssessment().get("prompt_stage");
    Object authorization = report.preRenderAssessment().get("render_authorization");
    return "READY_FOR_FIRST_FRAME".equals(stage)
        && authorization instanceof Map<?, ?> map
        && !"BLOCKED_CREATIVE_FAILURE".equals(map.get("status"));
  }

  private String writeJson(Map<String, Object> provenance) {
    try {
      return objectMapper.writeValueAsString(provenance == null ? Map.of() : provenance);
    } catch (JsonProcessingException error) {
      throw new VisualEvidenceInvalidException("visual evidence provenance is not valid JSON");
    }
  }
}
