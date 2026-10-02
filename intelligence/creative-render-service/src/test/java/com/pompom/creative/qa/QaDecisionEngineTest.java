package com.pompom.creative.qa;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.creative.domain.*;
import com.pompom.creative.repository.RenderQaResultRepository;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class QaDecisionEngineTest {

  @Mock private RenderQaResultRepository qaResultRepo;

  private ObjectMapper objectMapper;
  private QaDecisionEngine decisionEngine;

  @BeforeEach
  void setUp() {
    objectMapper = new ObjectMapper();
    decisionEngine = new QaDecisionEngine(qaResultRepo, objectMapper);
  }

  @Test
  void makeDecision_allChecksPass_acceptsAsset() {
    // Given: Asset with perfect QA results
    RenderAsset asset = createAsset(1);
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(false)
            .characterIdentityVerified(true)
            .confidence(0.95)
            .complianceScore(100)
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    QaDecisionEngine.QaDecision decision = decisionEngine.makeDecision(asset, qaResult);

    // Then
    assertThat(decision.decision()).isEqualTo(RenderQaResult.QaDecision.ACCEPT);
    assertThat(decision.requiresHumanReview()).isFalse();
    assertThat(decision.reason()).contains("All QA checks passed");

    verify(qaResultRepo).save(any(RenderQaResult.class));
  }

  @Test
  void makeDecision_characterMismatch_abandonsImmediately() {
    // Given: Asset with character mismatch
    RenderAsset asset = createAsset(1);
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(false)
            .characterIdentityVerified(false)
            .confidence(0.3)
            .characterIdentityIssues("Wrong character detected")
            .complianceScore(50)
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    QaDecisionEngine.QaDecision decision = decisionEngine.makeDecision(asset, qaResult);

    // Then
    assertThat(decision.decision()).isEqualTo(RenderQaResult.QaDecision.ABANDON);
    assertThat(decision.requiresHumanReview()).isTrue();
    assertThat(decision.reason()).contains("Character identity verification failed");
  }

  @Test
  void makeDecision_deadAirFirstAttempt_rerender() {
    // Given: Asset with dead air, first attempt
    RenderAsset asset = createAsset(1);
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(true)
            .deadAirDurationMs(3000)
            .characterIdentityVerified(true)
            .confidence(0.9)
            .complianceScore(70)
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    QaDecisionEngine.QaDecision decision = decisionEngine.makeDecision(asset, qaResult);

    // Then
    assertThat(decision.decision()).isEqualTo(RenderQaResult.QaDecision.RERENDER);
    assertThat(decision.requiresHumanReview()).isFalse();
    assertThat(decision.reason()).contains("Dead air detected");
    assertThat(decision.reason()).contains("3000ms");
  }

  @Test
  void makeDecision_deadAirMaxAttempts_abandon() {
    // Given: Asset with dead air after max attempts
    RenderAsset asset = createAsset(2); // Attempt 2
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(true)
            .deadAirDurationMs(2500)
            .characterIdentityVerified(true)
            .confidence(0.9)
            .complianceScore(70)
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    QaDecisionEngine.QaDecision decision = decisionEngine.makeDecision(asset, qaResult);

    // Then
    assertThat(decision.decision()).isEqualTo(RenderQaResult.QaDecision.ABANDON);
    assertThat(decision.requiresHumanReview()).isTrue();
    assertThat(decision.reason()).contains("Dead air persists after");
  }

  @Test
  void makeDecision_lowComplianceFirstAttempt_rerender() {
    // Given: Asset with low compliance, first attempt
    RenderAsset asset = createAsset(1);
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(false)
            .characterIdentityVerified(true)
            .confidence(0.85)
            .complianceScore(65) // Below threshold of 70
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    QaDecisionEngine.QaDecision decision = decisionEngine.makeDecision(asset, qaResult);

    // Then
    assertThat(decision.decision()).isEqualTo(RenderQaResult.QaDecision.RERENDER);
    assertThat(decision.requiresHumanReview()).isFalse();
    assertThat(decision.reason()).contains("Compliance score below threshold");
  }

  @Test
  void makeDecision_lowComplianceMaxAttempts_abandon() {
    // Given: Asset with low compliance after max attempts
    RenderAsset asset = createAsset(2);
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(false)
            .characterIdentityVerified(true)
            .confidence(0.85)
            .complianceScore(65)
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    QaDecisionEngine.QaDecision decision = decisionEngine.makeDecision(asset, qaResult);

    // Then
    assertThat(decision.decision()).isEqualTo(RenderQaResult.QaDecision.ABANDON);
    assertThat(decision.requiresHumanReview()).isTrue();
    assertThat(decision.reason()).contains("Compliance score remains low");
  }

  @Test
  void makeDecision_savesQaResultEntity() {
    // Given
    RenderAsset asset = createAsset(1);
    QaAnalysisResult qaResult =
        QaAnalysisResult.builder()
            .hasDeadAir(true)
            .deadAirSegments(
                List.of(
                    QaAnalysisResult.DeadAirSegment.builder()
                        .startMs(1000)
                        .endMs(3000)
                        .duration(2.0)
                        .build()))
            .deadAirDurationMs(2000)
            .characterIdentityVerified(true)
            .confidence(0.9)
            .complianceScore(70)
            .build();

    when(qaResultRepo.save(any())).thenAnswer(i -> i.getArgument(0));

    // When
    decisionEngine.makeDecision(asset, qaResult);

    // Then: Verify saved entity
    ArgumentCaptor<RenderQaResult> captor = ArgumentCaptor.forClass(RenderQaResult.class);
    verify(qaResultRepo).save(captor.capture());

    RenderQaResult saved = captor.getValue();
    assertThat(saved.getRenderAsset()).isEqualTo(asset);
    assertThat(saved.getDecision()).isEqualTo(RenderQaResult.QaDecision.RERENDER);
    assertThat(saved.getComplianceScore()).isEqualTo(70);
    assertThat(saved.getHasDeadAir()).isTrue();
    assertThat(saved.getCharacterIdentityVerified()).isTrue();
    assertThat(saved.getDeadAirSegments()).isNotNull();
    assertThat(saved.getComplianceIssues()).isNotNull();
  }

  // Helper method to create test asset
  private RenderAsset createAsset(int attemptNumber) {
    RenderJob job =
        RenderJob.builder()
            .id(UUID.randomUUID())
            .contentId(1L)
            .promptVersionId(1L)
            .contentTitleSnapshot("Kiko Episode")
            .promptVersionNumberSnapshot(1)
            .attemptNumber(attemptNumber)
            .build();

    return RenderAsset.builder()
        .id(UUID.randomUUID())
        .renderJob(job)
        .contentId(1L)
        .assetType(RenderAsset.AssetType.VIDEO)
        .relativePath("content/1/render-v1.mp4")
        .build();
  }
}
