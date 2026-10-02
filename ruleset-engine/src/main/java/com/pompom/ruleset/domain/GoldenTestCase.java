package com.pompom.ruleset.domain;

import io.hypersistence.utils.hibernate.type.json.JsonBinaryType;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.Type;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Golden test case entity.
 * Regression prevention dataset with expected outcomes.
 */
@Entity
@Table(name = "golden_test_cases")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class GoldenTestCase {
    
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;
    
    @Column(name = "test_name", unique = true, nullable = false, length = 255)
    private String testName;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "category", nullable = false, length = 30)
    private TestCategory category;
    
    @Column(name = "concept_text", columnDefinition = "TEXT", nullable = false)
    private String conceptText;
    
    @Enumerated(EnumType.STRING)
    @Column(name = "intent", length = 50)
    private ConceptValidation.ContentIntent intent;
    
    // Expected validation outcome
    @Column(name = "expected_approved", nullable = false)
    private Boolean expectedApproved;
    
    @Column(name = "expected_min_score", precision = 5, scale = 2)
    private BigDecimal expectedMinScore;
    
    @Column(name = "expected_max_score", precision = 5, scale = 2)
    private BigDecimal expectedMaxScore;
    
    @Type(JsonBinaryType.class)
    @Column(name = "expected_passing_rules", columnDefinition = "jsonb")
    private List<String> expectedPassingRules;
    
    @Type(JsonBinaryType.class)
    @Column(name = "expected_failing_rules", columnDefinition = "jsonb")
    private List<String> expectedFailingRules;
    
    @Column(name = "notes", columnDefinition = "TEXT")
    private String notes;
    
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();
    
    public enum TestCategory {
        POSITIVE,  // Should pass validation
        NEGATIVE   // Should fail validation
    }
}
