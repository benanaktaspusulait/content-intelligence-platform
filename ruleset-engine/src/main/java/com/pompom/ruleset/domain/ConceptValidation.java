package com.pompom.ruleset.domain;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Concept validation result entity.
 * Stores the outcome of pre-render validation.
 */
@Entity
@Table(name = "concept_validations")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptValidation {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @Column(name = "external_concept_id", length = 255)
    private String externalConceptId; // Reference to Creative Intelligence system
    
    @Column(name = "concept_text", columnDefinition = "TEXT", nullable = false)
    private String conceptText;
    
    @Column(name = "approved", nullable = false)
    private Boolean approved;
    
    @Column(name = "overall_score", precision = 5, scale = 2)
    private BigDecimal overallScore; // 0-100
    
    @Enumerated(EnumType.STRING)
    @Column(name = "intent", length = 50)
    private ContentIntent intent;
    
    @OneToMany(mappedBy = "validation", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<RuleEvaluation> ruleEvaluations = new ArrayList<>();
    
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();
    
    public enum ContentIntent {
        GROWTH,       // Maximize reach, replay
        EDUCATIONAL,  // Learning, follower trust
        EXPERIMENT,   // Test new format
        STOCK         // Content library
    }
    
    /**
     * Add a rule evaluation result.
     */
    public void addRuleEvaluation(RuleEvaluation evaluation) {
        ruleEvaluations.add(evaluation);
        evaluation.setValidation(this);
    }
    
    /**
     * Check if any critical rules failed.
     */
    public boolean hasCriticalFailures() {
        return ruleEvaluations.stream()
            .anyMatch(eval -> eval.getRule().getSeverity() == Rule.RuleSeverity.CRITICAL 
                && !eval.getPassed());
    }
}
