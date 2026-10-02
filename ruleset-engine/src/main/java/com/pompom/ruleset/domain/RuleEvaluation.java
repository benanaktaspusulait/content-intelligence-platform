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
 * Individual rule evaluation result.
 * Links a validation to a specific rule with pass/fail outcome.
 */
@Entity
@Table(name = "rule_evaluations")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RuleEvaluation {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "validation_id", nullable = false)
    @ToString.Exclude
    private ConceptValidation validation;
    
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "rule_id", nullable = false)
    private Rule rule;
    
    @Column(name = "passed", nullable = false)
    private Boolean passed;
    
    @Column(name = "score", precision = 5, scale = 2)
    private BigDecimal score; // 0-100
    
    @Column(name = "reason", columnDefinition = "TEXT")
    private String reason;
    
    @Type(JsonBinaryType.class)
    @Column(name = "details", columnDefinition = "jsonb")
    private Map<String, Object> details;
    
    @Column(name = "evaluated_at", nullable = false)
    private Instant evaluatedAt = Instant.now();
    
    /**
     * Check if this is a critical failure.
     */
    public boolean isCriticalFailure() {
        return !passed && rule.getSeverity() == Rule.RuleSeverity.CRITICAL;
    }
    
    /**
     * Check if this is a warning.
     */
    public boolean isWarning() {
        return !passed && 
            (rule.getSeverity() == Rule.RuleSeverity.HIGH || 
             rule.getSeverity() == Rule.RuleSeverity.MEDIUM);
    }
}
