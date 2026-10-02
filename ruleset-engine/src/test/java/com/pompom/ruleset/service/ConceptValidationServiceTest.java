package com.pompom.ruleset.service;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.domain.ConceptValidation;
import com.pompom.ruleset.domain.Rule;
import com.pompom.ruleset.repository.RuleRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Transactional
class ConceptValidationServiceTest {
    
    @Autowired
    private ConceptValidationService validationService;
    
    @Autowired
    private RuleRepository ruleRepository;
    
    @BeforeEach
    void setup() {
        // Clear existing rules
        ruleRepository.deleteAll();
        
        // Insert test rule
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .name("Immediate Anomaly")
            .category(Rule.RuleCategory.CONCEPT)
            .severity(Rule.RuleSeverity.CRITICAL)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .evidenceLevel(Rule.EvidenceLevel.SUPPORTED)
            .active(true)
            .build();
        ruleRepository.save(rule);
    }
    
    @Test
    void testValidationPass() {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .externalConceptId("test-001")
            .conceptText("Giant spoon that grows with every pour")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        ConceptValidationResponse response = validationService.validate(request);
        
        assertNotNull(response.getValidationId());
        assertTrue(response.getApproved());
        assertNotNull(response.getOverallScore());
        assertTrue(response.getOverallScore().doubleValue() >= 60.0);
        assertFalse(response.getRuleResults().isEmpty());
    }
    
    @Test
    void testValidationFail() {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .externalConceptId("test-002")
            .conceptText("Door that won't open when pushed")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        ConceptValidationResponse response = validationService.validate(request);
        
        assertNotNull(response.getValidationId());
        assertFalse(response.getApproved());
        assertFalse(response.getCriticalIssues().isEmpty());
    }
    
    @Test
    void testValidationWithMultipleRules() {
        // Add second rule
        Rule rule2 = Rule.builder()
            .ruleCode("BEAT_003_STORY_DETACHED_GAP")
            .name("Story Detached Gap")
            .category(Rule.RuleCategory.BEAT)
            .severity(Rule.RuleSeverity.CRITICAL)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .evidenceLevel(Rule.EvidenceLevel.SUPPORTED)
            .active(true)
            .build();
        ruleRepository.save(rule2);
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Giant spoon. Cut to landscape. Back to spoon.")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        ConceptValidationResponse response = validationService.validate(request);
        
        assertEquals(2, response.getRuleResults().size());
        assertTrue(response.getCriticalIssues().size() >= 1);
    }
}
