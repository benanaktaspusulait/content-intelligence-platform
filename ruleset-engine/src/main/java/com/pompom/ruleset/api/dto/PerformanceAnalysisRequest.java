package com.pompom.ruleset.api.dto;

import com.pompom.ruleset.domain.ConceptValidation;
import com.pompom.ruleset.domain.PerformanceScore;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceAnalysisRequest {
    
    @NotBlank(message = "External video ID is required")
    private String externalVideoId;
    
    @NotNull(message = "Platform is required")
    private PerformanceScore.Platform platform;
    
    private ConceptValidation.ContentIntent intent;
    
    @NotNull(message = "Duration is required")
    private BigDecimal durationSeconds;
    
    private Instant publishedAt;
    
    @NotNull(message = "Metrics are required")
    private MetricsDto metrics;
    
    private Integer timeSincePublishHours;
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MetricsDto {
        private Long views;
        private Long likes;
        private Long comments;
        private Long shares;
        private Long saves;
        private Long reach;
        private Long impressions;
        private BigDecimal avgWatchTimeSeconds;
        private BigDecimal completionRate;
        private Long threeSecondViews;
        private Long uniqueViewers;
        private Map<String, BigDecimal> countryDistribution;
    }
}
