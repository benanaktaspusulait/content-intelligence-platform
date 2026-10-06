package com.pompomhills.intelligence.quality;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompomhills.intelligence.quality.VisualEvidenceDtos.VisualEvidenceRequest;
import com.pompomhills.intelligence.quality.VisualEvidenceDtos.VisualEvidenceResponse;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class VisualEvidenceSubmissionServiceTest {
  private QualityValidationRepository validations;
  private ValidationVisualEvidenceRepository evidence;
  private VisualEvidenceSubmissionService service;
  private QualityValidationEntity parent;
  private final List<ValidationVisualEvidenceEntity> rows = new ArrayList<>();

  @BeforeEach
  void setUp() {
    validations = mock(QualityValidationRepository.class);
    evidence = mock(ValidationVisualEvidenceRepository.class);
    service = new VisualEvidenceSubmissionService(validations, evidence, new ObjectMapper());
    parent = new QualityValidationEntity();
    parent.setId(42L);
    parent.setContentId(10L);
    parent.setPromptVersionId(11L);
    parent.setPromptSha256("a".repeat(64));
    parent.setReportJson("{\"preRenderAssessment\":{\"prompt_stage\":\"READY_FOR_FIRST_FRAME\",\"render_authorization\":{\"status\":\"BLOCKED_PENDING_EVIDENCE\"}}}");
    when(validations.findById(42L)).thenReturn(Optional.of(parent));
    when(evidence.findBySubmissionKey(any())).thenReturn(Optional.empty());
    when(evidence.findByValidationRecordIdOrderBySubmittedAtAscIdAsc(42L)).thenAnswer(ignored -> rows);
    when(evidence.saveAndFlush(any())).thenAnswer(invocation -> {
      ValidationVisualEvidenceEntity row = invocation.getArgument(0);
      row.setId((long) rows.size() + 1);
      rows.add(row);
      return row;
    });
  }

  @Test
  void appendsBothVisualGateResultsAndOnlyThenProjectsFinalVideoEligibility() {
    UUID evidenceSet = UUID.randomUUID();
    UUID job = UUID.randomUUID();
    UUID asset = UUID.randomUUID();
    String assetSha = "b".repeat(64);

    VisualEvidenceResponse first = service.submit(42L, request("FIRST_FRAME", evidenceSet, job, asset, assetSha, "first"));
    assertThat(first.firstFrameEligible()).isTrue();
    assertThat(first.finalVideoEligible()).isFalse();

    VisualEvidenceResponse silhouette = service.submit(42L, request("SILHOUETTE", evidenceSet, job, asset, assetSha, "silhouette"));
    assertThat(silhouette.finalVideoEligible()).isTrue();
    assertThat(rows).hasSize(2);
    verify(validations, never()).save(any());
    verify(validations, never()).saveAndFlush(any());
  }

  @Test
  void latestFailSupersedesEarlierPassAndNeverAuthorizesVideo() {
    UUID evidenceSet = UUID.randomUUID();
    UUID job = UUID.randomUUID();
    UUID asset = UUID.randomUUID();
    String sha = "b".repeat(64);
    service.submit(42L, request("FIRST_FRAME", evidenceSet, job, asset, sha, "pass"));
    service.submit(42L, request("SILHOUETTE", evidenceSet, job, asset, sha, "pass2"));
    VisualEvidenceRequest fail = new VisualEvidenceRequest(10L, 11L, "a".repeat(64), "FIRST_FRAME", "FAIL", evidenceSet, job, asset, "FIRST_FRAME", "content/first-frame.png", sha, Map.of("kind", "HUMAN_VERIFICATION"), "failed", "review-3", Instant.now(), "submission-3");
    VisualEvidenceResponse response = service.submit(42L, fail);
    assertThat(response.finalVideoEligible()).isFalse();
  }

  private VisualEvidenceRequest request(String gate, UUID evidenceSet, UUID job, UUID asset, String sha, String key) {
    return new VisualEvidenceRequest(10L, 11L, "a".repeat(64), gate, "PASS", evidenceSet, job, asset, "FIRST_FRAME", "content/first-frame.png", sha, Map.of("kind", "HUMAN_VERIFICATION"), "verified", "review-" + key, Instant.now(), key);
  }
}
