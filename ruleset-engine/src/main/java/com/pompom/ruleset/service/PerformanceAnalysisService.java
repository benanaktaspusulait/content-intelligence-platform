package com.pompom.ruleset.service;

import com.pompom.ruleset.api.dto.PerformanceAnalysisRequest;
import com.pompom.ruleset.api.dto.PerformanceAnalysisResponse;
import com.pompom.ruleset.domain.PerformanceScore;
import com.pompom.ruleset.repository.PerformanceScoreRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@Slf4j
@RequiredArgsConstructor
public class PerformanceAnalysisService {
    
    private final PerformanceScoreRepository scoreRepository;
    
    @Transactional
    public PerformanceAnalysisResponse analyze(PerformanceAnalysisRequest request) {
        log.info("Analyzing performance for video: {}", request.getExternalVideoId());
        
        BigDecimal avgWatchRatio = calculateAvgWatchRatio(
            request.getMetrics().getAvgWatchTimeSeconds(),
            request.getDurationSeconds()
        );
        
        BigDecimal entryProxy = calculateEntryProxy(
            request.getMetrics().getThreeSecondViews(),
            request.getMetrics().getReach()
        );
        
        BigDecimal viewsPerViewer = calculateViewsPerViewer(
            request.getMetrics().getViews(),
            request.getMetrics().getUniqueViewers()
        );
        
        PerformanceScore score = PerformanceScore.builder()
            .externalVideoId(request.getExternalVideoId())
            .platform(request.getPlatform())
            .intent(request.getIntent())
            .views(request.getMetrics().getViews())
            .likes(request.getMetrics().getLikes())
            .comments(request.getMetrics().getComments())
            .shares(request.getMetrics().getShares())
            .saves(request.getMetrics().getSaves())
            .reach(request.getMetrics().getReach())
            .impressions(request.getMetrics().getImpressions())
            .avgWatchSeconds(request.getMetrics().getAvgWatchTimeSeconds())
            .durationSeconds(request.getDurationSeconds())
            .completionRate(request.getMetrics().getCompletionRate())
            .threeSecondViews(request.getMetrics().getThreeSecondViews())
            .uniqueViewers(request.getMetrics().getUniqueViewers())
            .avgWatchRatio(avgWatchRatio)
            .entryProxy(entryProxy)
            .viewsPerViewer(viewsPerViewer)
            .endRetentionRate(request.getMetrics().getCompletionRate())
            .collectedAt(java.time.Instant.now())
            .timeSincePublishHours(request.getTimeSincePublishHours())
            .build();
        
        calculateDimensionScores(score, avgWatchRatio, entryProxy, viewsPerViewer);
        classifyPerformance(score, request.getPlatform());
        
        scoreRepository.save(score);
        
        return buildPerformanceResponse(score);
    }
    
    private BigDecimal calculateAvgWatchRatio(BigDecimal avgWatch, BigDecimal duration) {
        if (duration == null || duration.compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }
        return avgWatch.divide(duration, 4, RoundingMode.HALF_UP);
    }
    
    private BigDecimal calculateEntryProxy(Long threeSecViews, Long reach) {
        if (reach == null || reach == 0) {
            return BigDecimal.ZERO;
        }
        return BigDecimal.valueOf(threeSecViews)
            .divide(BigDecimal.valueOf(reach), 4, RoundingMode.HALF_UP);
    }
    
    private BigDecimal calculateViewsPerViewer(Long views, Long uniqueViewers) {
        if (uniqueViewers == null || uniqueViewers == 0) {
            return BigDecimal.ONE;
        }
        return BigDecimal.valueOf(views)
            .divide(BigDecimal.valueOf(uniqueViewers), 2, RoundingMode.HALF_UP);
    }
    
    private void calculateDimensionScores(PerformanceScore score, 
                                          BigDecimal avgWatchRatio,
                                          BigDecimal entryProxy,
                                          BigDecimal viewsPerViewer) {
        BigDecimal hookStrength = entryProxy.compareTo(BigDecimal.valueOf(0.75)) >= 0 ?
            BigDecimal.valueOf(90.0) : BigDecimal.valueOf(60.0);
        score.setHookStrength(hookStrength);
        
        BigDecimal loopability = (avgWatchRatio.compareTo(BigDecimal.ONE) >= 0 &&
                                  viewsPerViewer.compareTo(BigDecimal.valueOf(2.0)) >= 0) ?
            BigDecimal.valueOf(85.0) : BigDecimal.valueOf(50.0);
        score.setLoopabilityScore(loopability);
        
        score.setProgressionScore(BigDecimal.valueOf(70.0));
        score.setAttemptDiversityScore(BigDecimal.valueOf(70.0));
        score.setFinalPayoff(BigDecimal.valueOf(70.0));
        
        BigDecimal overall = hookStrength.add(loopability)
            .divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP);
        score.setOverallQuality(overall);
    }
    
    private void classifyPerformance(PerformanceScore score, PerformanceScore.Platform platform) {
        BigDecimal entryProxy = score.getEntryProxy();
        
        if (platform == PerformanceScore.Platform.META_FACEBOOK) {
            if (entryProxy.compareTo(BigDecimal.valueOf(0.80)) >= 0) {
                score.setClassification(PerformanceScore.PerformanceClassification.STRONG);
            } else if (entryProxy.compareTo(BigDecimal.valueOf(0.75)) >= 0) {
                score.setClassification(PerformanceScore.PerformanceClassification.VIABLE);
            } else {
                score.setClassification(PerformanceScore.PerformanceClassification.WEAK);
            }
        } else {
            score.setClassification(PerformanceScore.PerformanceClassification.VIABLE);
        }
    }
    
    private PerformanceAnalysisResponse buildPerformanceResponse(PerformanceScore score) {
        Map<String, BigDecimal> dimensions = new HashMap<>();
        dimensions.put("hookStrength", score.getHookStrength());
        dimensions.put("progressionScore", score.getProgressionScore());
        dimensions.put("attemptDiversityScore", score.getAttemptDiversityScore());
        dimensions.put("finalPayoff", score.getFinalPayoff());
        dimensions.put("loopabilityScore", score.getLoopabilityScore());
        
        PerformanceAnalysisResponse.DerivedMetricsDto derived = 
            PerformanceAnalysisResponse.DerivedMetricsDto.builder()
                .avgWatchRatio(score.getAvgWatchRatio())
                .entryProxy(score.getEntryProxy())
                .viewsPerViewer(score.getViewsPerViewer())
                .endRetentionRate(score.getEndRetentionRate())
                .build();
        
        List<String> insights = generateInsights(score);
        
        return PerformanceAnalysisResponse.builder()
            .performanceId(score.getId())
            .overallQuality(score.getOverallQuality())
            .classification(score.getClassification())
            .wavePattern(score.getWavePattern())
            .dimensionScores(dimensions)
            .derivedMetrics(derived)
            .insights(insights)
            .build();
    }
    
    private List<String> generateInsights(PerformanceScore score) {
        List<String> insights = new ArrayList<>();
        
        if (score.getAvgWatchRatio().compareTo(BigDecimal.ONE) > 0) {
            insights.add("Exceptional loopability: avg watch > duration suggests replay");
        }
        
        if (score.getEntryProxy().compareTo(BigDecimal.valueOf(0.75)) >= 0) {
            insights.add("Strong entry proxy - hook works immediately");
        }
        
        if (score.getViewsPerViewer().compareTo(BigDecimal.valueOf(2.0)) >= 0) {
            insights.add("High views/viewer ratio indicates replay behavior");
        }
        
        return insights;
    }
}
