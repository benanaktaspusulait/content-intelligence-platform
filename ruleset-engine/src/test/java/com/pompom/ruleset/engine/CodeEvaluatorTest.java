package com.pompom.ruleset.engine;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.ConceptValidation;
import com.pompom.ruleset.domain.Rule;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class CodeEvaluatorTest {
    
    @Autowired
    private CodeEvaluator codeEvaluator;
    
    @Test
    void testImmediateAnomalyPass() {
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .name("Immediate Anomaly")
            .category(Rule.RuleCategory.CONCEPT)
            .severity(Rule.RuleSeverity.CRITICAL)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .evidenceLevel(Rule.EvidenceLevel.SUPPORTED)
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Giant spoon that gets bigger with every pour")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        RuleResult result = codeEvaluator.evaluate(rule, request);
        
        assertTrue(result.getPassed());
        assertNotNull(result.getReason());
        assertTrue(result.getReason().toLowerCase().contains("immediate"));
    }
    
    @Test
    void testImmediateAnomalyFail() {
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Door that eventually opens after pushing")
            .build();
        
        RuleResult result = codeEvaluator.evaluate(rule, request);
        
        assertFalse(result.getPassed());
        assertTrue(result.getReason().contains("No immediate visual anomaly"));
    }
    
    @Test
    void testStoryDetachedGapFail() {
        Rule rule = Rule.builder()
            .ruleCode("BEAT_003_STORY_DETACHED_GAP")
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Characters push door. Cut to scenic landscape for 2 seconds. Back to door.")
            .build();
        
        RuleResult result = codeEvaluator.evaluate(rule, request);
        
        assertFalse(result.getPassed());
        assertTrue(result.getReason().contains("detached"));
    }
    
    @Test
    void testMeaningfulMotionPass() {
        Rule rule = Rule.builder()
            .ruleCode("MOTION_001_MEANINGFUL_MOTION")
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Giant spoon grows. Character tries to lift. Struggles. Final: gives up.")
            .build();
        
        RuleResult result = codeEvaluator.evaluate(rule, request);
        
        assertTrue(result.getPassed());
    }
}
