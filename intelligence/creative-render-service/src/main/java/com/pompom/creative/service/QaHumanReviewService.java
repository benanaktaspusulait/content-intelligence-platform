package com.pompom.creative.service;

import com.pompom.creative.domain.QaHumanReview;
import com.pompom.creative.domain.RenderQaResult;
import com.pompom.creative.repository.QaHumanReviewRepository;
import com.pompom.creative.repository.RenderAttemptRepository;
import com.pompom.creative.repository.RenderJobRepository;
import com.pompom.creative.repository.RenderQaResultRepository;
import com.pompom.creative.postrender.PostRenderEvaluation;
import com.pompom.creative.postrender.PostRenderEvaluationRepository;
import com.pompom.creative.domain.RenderAttempt;
import com.pompom.creative.domain.RenderExecutionStage;
import com.pompom.creative.domain.RenderJob;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Applies and audits human decisions required by the post-render QA gate. */
@Service
@RequiredArgsConstructor
public class QaHumanReviewService {

  private final RenderQaResultRepository qaResultRepository;
  private final QaHumanReviewRepository reviewRepository;
  private final RenderAttemptRepository renderAttemptRepository;
  private final RenderJobRepository renderJobRepository;
  private final PostRenderEvaluationRepository postRenderEvaluationRepository;

  @Transactional(readOnly = true)
  public List<RenderQaResult> pendingReviews() {
    return qaResultRepository.findByRequiresHumanReviewTrueAndHumanReviewedAtIsNullOrderByCreatedAtAsc();
  }

  @Transactional(readOnly = true)
  public List<PostRenderEvaluation> pendingPostRenderEvaluations() {
    return postRenderEvaluationRepository.findByHumanReviewRequiredTrueAndHumanReviewedAtIsNullOrderByCreatedAtAsc();
  }

  @Transactional
  public QaHumanReview decide(
      UUID qaResultId, QaHumanReview.Decision decision, String reviewer, String notes) {
    if (reviewer == null || reviewer.isBlank()) {
      throw new IllegalArgumentException("reviewer is required");
    }
    RenderQaResult qa =
        qaResultRepository
            .findById(qaResultId)
            .orElseThrow(() -> new IllegalArgumentException("QA result not found"));
    if (!Boolean.TRUE.equals(qa.getRequiresHumanReview())) {
      throw new IllegalStateException("This QA result does not require human review");
    }
    if (qa.getHumanReviewedAt() != null) {
      throw new IllegalStateException("This QA result has already been reviewed");
    }

    qa.setHumanReviewedAt(Instant.now());
    qa.setHumanReviewer(reviewer.trim());
    qa.setHumanDecision(decision.name());
    qa.setHumanNotes(notes);
    qa.setDecision(
        switch (decision) {
          case APPROVED -> RenderQaResult.QaDecision.ACCEPT;
          case REJECTED -> RenderQaResult.QaDecision.ABANDON;
          case RERENDER_REQUESTED -> RenderQaResult.QaDecision.RERENDER;
        });
    qaResultRepository.save(qa);

    if (decision == QaHumanReview.Decision.RERENDER_REQUESTED) {
      queueRerender(qa);
    }

    return reviewRepository.save(
        QaHumanReview.builder()
            .renderQaResult(qa)
            .decision(decision)
            .reviewer(reviewer.trim())
            .notes(notes)
            .build());
  }

  @Transactional(readOnly = true)
  public List<QaHumanReview> history(UUID qaResultId) {
    return reviewRepository.findByRenderQaResultIdOrderByCreatedAtDesc(qaResultId);
  }

  @Transactional
  public QaHumanReview decidePostRender(
      UUID evaluationId, QaHumanReview.Decision decision, String reviewer, String notes) {
    if (reviewer == null || reviewer.isBlank()) throw new IllegalArgumentException("reviewer is required");
    PostRenderEvaluation evaluation = postRenderEvaluationRepository.findById(evaluationId)
        .orElseThrow(() -> new IllegalArgumentException("Post-render evaluation not found"));
    evaluation.recordHumanDecision(reviewer.trim(), decision.name(), notes);
    postRenderEvaluationRepository.save(evaluation);
    if (decision == QaHumanReview.Decision.RERENDER_REQUESTED) queueRerender(evaluation.getRenderAsset().getRenderJob());
    return reviewRepository.save(QaHumanReview.builder()
        .postRenderEvaluation(evaluation)
        .decision(decision)
        .reviewer(reviewer.trim())
        .notes(notes)
        .build());
  }

  @Transactional(readOnly = true)
  public List<QaHumanReview> postRenderHistory(UUID evaluationId) {
    return reviewRepository.findByPostRenderEvaluationIdOrderByCreatedAtDesc(evaluationId);
  }

  private void queueRerender(RenderQaResult qa) {
    queueRerender(qa.getRenderAsset().getRenderJob());
  }

  private void queueRerender(RenderJob job) {
    if (job.getStatus() != RenderJob.RenderJobStatus.ABANDONED
        && job.getStatus() != RenderJob.RenderJobStatus.COMPLETE) {
      throw new IllegalStateException("Render job is not in a rerenderable terminal state");
    }
    var attempts = renderAttemptRepository.findByRenderJobIdOrderByAttemptNumberAsc(job.getId());
    if (attempts.size() >= job.getMaxAttempts()) {
      throw new IllegalStateException("Render job has reached its maximum attempts");
    }
    RenderAttempt latest = attempts.get(attempts.size() - 1);
    latest.setStage(RenderExecutionStage.RETRY_WAIT);
    latest.setCompletedAt(Instant.now());
    latest.setLeaseOwner(null);
    latest.setLeaseExpiresAt(null);
    renderAttemptRepository.save(latest);
    renderAttemptRepository.save(
        RenderAttempt.builder()
            .renderJobId(job.getId())
            .attemptNumber(latest.getAttemptNumber() + 1)
            .stage(RenderExecutionStage.QUEUED)
            .pollCount(0)
            .eligibleAt(Instant.now())
            .build());
    job.setStatus(RenderJob.RenderJobStatus.QUEUED);
    job.setErrorCode(null);
    job.setErrorMessage(null);
    job.setFailedAt(null);
    renderJobRepository.save(job);
  }
}
