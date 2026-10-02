package com.pompom.ruleset.api.dto;

import com.pompom.ruleset.domain.PerformanceScore;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceAnalysisResponse {
    
    private UUID performanceId;
    
    private BigDecimal overallQuality;
    
    private PerformanceScore.PerformanceClassification classification;
    
    private String wavePattern;
    
    private Map<String, BigDecimal> dimensionScores;
    
    private DerivedMetricsDto derivedMetrics;
    
    private List<String> insights;
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DerivedMetricsDto {
        private BigDecimal avgWatchRatio;
        private BigDecimal entryProxy;
        private BigDecimal viewsPerViewer;
        private BigDecimal endRetentionRate;
    }
}
