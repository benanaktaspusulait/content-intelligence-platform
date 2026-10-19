package com.pompom.creative.service;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.pompom.creative.domain.QaHumanReview;
import com.pompom.creative.postrender.PostRenderEvaluationRepository;
import com.pompom.creative.postrender.VideoQcGateTest;
import com.pompom.creative.repository.*;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class QaHumanReviewAuthorityTest {
  @Test void ownerCanApproveAnUnavailableReviewThroughExistingAuditedDecisionService() {
    var repository = mock(PostRenderEvaluationRepository.class);
    var audit = mock(QaHumanReviewRepository.class);
    var service = new QaHumanReviewService(mock(RenderQaResultRepository.class), audit,
        mock(RenderAttemptRepository.class), mock(RenderJobRepository.class), repository, mock(CreditTrackingService.class));
    var id = UUID.randomUUID();
    var evaluation = VideoQcGateTest.evaluation("NOT_EVALUATED", false, "TECHNICAL_QC_PASS");
    when(repository.findById(id)).thenReturn(Optional.of(evaluation));
    service.decidePostRender(id, QaHumanReview.Decision.APPROVED, "owner", "Explicit owner choice despite unavailable creative review");
    assertThat(evaluation.getHumanDecision()).isEqualTo("APPROVED");
    assertThat(evaluation.getHumanReviewer()).isEqualTo("owner");
    assertThat(evaluation.getHumanReviewedAt()).isNotNull();
    verify(audit).save(any(QaHumanReview.class));
  }

  @Test void ownerApprovalCannotOverrideCorruptMedia() {
    var repository = mock(PostRenderEvaluationRepository.class);
    var audit = mock(QaHumanReviewRepository.class);
    var service = new QaHumanReviewService(mock(RenderQaResultRepository.class), audit,
        mock(RenderAttemptRepository.class), mock(RenderJobRepository.class), repository, mock(CreditTrackingService.class));
    var id = UUID.randomUUID();
    var evaluation = VideoQcGateTest.evaluation("PUBLISH", false, "TECHNICAL_QC_FAIL");
    when(repository.findById(id)).thenReturn(Optional.of(evaluation));
    assertThatThrownBy(() -> service.decidePostRender(id, QaHumanReview.Decision.APPROVED, "owner", "choice"))
        .isInstanceOf(IllegalStateException.class);
    verify(audit, never()).save(any());
  }
}
