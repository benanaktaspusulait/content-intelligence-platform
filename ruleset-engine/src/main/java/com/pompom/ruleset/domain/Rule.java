package com.pompom.ruleset.domain;

import io.hypersistence.utils.hibernate.type.json.JsonBinaryType;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.Type;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

/**
 * Rule definition entity.
 * Represents a single validation or performance rule.
 */
@Entity
@Table(name = "rules")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Rule {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @Column(name = "rule_code", unique = true, nullable = false, length = 50)
    private String ruleCode;
    
    @Column(name = "name", nullable = false)
    private String name;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "category", nullable = false, length = 30)
    private RuleCategory category;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "severity", nullable = false, length = 20)
    private RuleSeverity severity;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "evaluation_type", nullable = false, length = 20)
    private EvaluationType evaluationType;
    
    @Column(name = "description", columnDefinition = "TEXT")
    private String description;
    
    @Type(JsonBinaryType.class)
    @Column(name = "yaml_definition", columnDefinition = "jsonb", nullable = false)
    private Map<String, Object> yamlDefinition;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "evidence_level", nullable = false, length = 30)
    private EvidenceLevel evidenceLevel;
    
    @Column(name = "active", nullable = false)
    private Boolean active = true;
    
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();
    
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();
    
    @PreUpdate
    public void preUpdate() {
        this.updatedAt = Instant.now();
    }
    
    public enum RuleCategory {
        CONCEPT,
        BEAT,
        MOTION,
        STORY,
        FINAL,
        PROMPT,
        PLATFORM,
        PERFORMANCE
    }
    
    public enum RuleSeverity {
        CRITICAL,  // Fail = reject concept
        HIGH,      // Fail = strong warning
        MEDIUM,    // Fail = warning
        LOW,       // Fail = info
        INFO       // Informational only
    }
    
    public enum EvaluationType {
        CODE,    // Java evaluator
        LLM,     // OpenAI evaluation
        HYBRID   // Both code + LLM
    }
    
    public enum EvidenceLevel {
        THEORETICAL,         // Hypothesis, not tested
        OBSERVED,            // Seen in 1-3 examples
        SUPPORTED,           // Consistent across 4-10 examples
        STRONGLY_SUPPORTED   // Validated in 10+ examples
    }
}
