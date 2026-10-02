package com.pompom.ruleset.domain;

import io.hypersistence.utils.hibernate.type.json.JsonBinaryType;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.Type;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Performance score entity.
 * Stores post-publish performance analysis results.
 */
@Entity
@Table(name = "performance_scores")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PerformanceScore {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @Column(name = "external_video_id", nullable = false, length = 255)
    private String externalVideoId; // Reference to Creative Intelligence video
    
    @Enumerated(EnumType.STRING)
    @Column(name = "platform", nullable = false, length = 20)
    private Platform platform;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "intent", length = 50)
    private ConceptValidation.ContentIntent intent;
    
    // Raw metrics
    @Column(name = "views")
    private Long views;
    
    @Column(name = "likes")
    private Long likes;
    
    @Column(name = "comments")
    private Long comments;
    
    @Column(name = "shares")
    private Long shares;
    
    @Column(name = "saves")
    private Long saves;
    
    @Column(name = "reach")
    private Long reach;
    
    @Column(name = "impressions")
    private Long impressions;
    
    @Column(name = "avg_watch_seconds", precision = 6, scale = 2)
    private BigDecimal avgWatchSeconds;
    
    @Column(name = "duration_seconds", precision = 6, scale = 2)
    private BigDecimal durationSeconds;
    
    @Column(name = "completion_rate", precision = 5, scale = 2)
    private BigDecimal completionRate;
    
    @Column(name = "three_second_views")
    private Long threeSecondViews;
    
    @Column(name = "unique_viewers")
    private Long uniqueViewers;
    
    // Derived metrics
    @Column(name = "avg_watch_ratio", precision = 5, scale = 4)
    private BigDecimal avgWatchRatio; // avgWatch / duration
    
    @Column(name = "entry_proxy", precision = 5, scale = 4)
    private BigDecimal entryProxy; // 3secViews / reach
    
    @Column(name = "views_per_viewer", precision = 5, scale = 2)
    private BigDecimal viewsPerViewer; // views / uniqueViewers
    
    @Column(name = "end_retention_rate", precision = 5, scale = 2)
    private BigDecimal endRetentionRate;
    
    // Dimension scores (0-100)
    @Column(name = "hook_strength", precision = 5, scale = 2)
    private BigDecimal hookStrength;
    
    @Column(name = "progression_score", precision = 5, scale = 2)
    private BigDecimal progressionScore;
    
    @Column(name = "attempt_diversity_score", precision = 5, scale = 2)
    private BigDecimal attemptDiversityScore;
    
    @Column(name = "educational_clarity", precision = 5, scale = 2)
    private BigDecimal educationalClarity;
    
    @Column(name = "final_payoff", precision = 5, scale = 2)
    private BigDecimal finalPayoff;
    
    @Column(name = "loopability_score", precision = 5, scale = 2)
    private BigDecimal loopabilityScore;
    
    // Overall
    @Column(name = "overall_quality", precision = 5, scale = 2)
    private BigDecimal overallQuality;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "classification", length = 30)
    private PerformanceClassification classification;
    
    @Column(name = "wave_pattern", length = 50)
    private String wavePattern;
    
    // Geography data
    @Type(JsonBinaryType.class)
    @Column(name = "country_distribution", columnDefinition = "jsonb")
    private Map<String, BigDecimal> countryDistribution;
    
    // Collection metadata
    @Column(name = "collected_at", nullable = false)
    private Instant collectedAt;
    
    @Column(name = "time_since_publish_hours")
    private Integer timeSincePublishHours;
    
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();
    
    public enum Platform {
        META_FACEBOOK,
        META_INSTAGRAM,
        TIKTOK,
        YOUTUBE_SHORTS
    }
    
    public enum PerformanceClassification {
        WEAK,
        VIABLE,
        STRONG,
        EXCEPTIONAL
    }
}
