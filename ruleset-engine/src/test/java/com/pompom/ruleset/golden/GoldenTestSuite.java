package com.pompom.ruleset.golden;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.domain.GoldenTestCase;
import com.pompom.ruleset.domain.Rule;
import com.pompom.ruleset.repository.GoldenTestCaseRepository;
import com.pompom.ruleset.repository.RuleRepository;
import com.pompom.ruleset.service.ConceptValidationService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Slf4j
@Transactional
public class GoldenTestSuite {
    
    @Autowired
    private GoldenTestCaseRepository goldenRepo;
    
    @Autowired
    private ConceptValidationService validationService;
    
    @Autowired
    private RuleRepository ruleRepository;
    
    @BeforeEach
    void setupRules() {
        // Ensure test rules exist
        ruleRepository.deleteAll();
        
        Rule rule1 = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .name("Immediate Anomaly")
            .category(Rule.RuleCategory.CONCEPT)
            .severity(Rule.RuleSeverity.CRITICAL)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .evidenceLevel(Rule.EvidenceLevel.SUPPORTED)
            .active(true)
            .build();
        
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
        
        ruleRepository.saveAll(List.of(rule1, rule2));
    }
    
    @Test
    public void testAllGoldenCases() {
        List<GoldenTestCase> goldenCases = goldenRepo.findAll();
        
        if (goldenCases.isEmpty()) {
            log.warn("No golden test cases found in database. Ensure migrations ran.");
            return;
        }
        
        log.info("Running golden test suite with {} cases", goldenCases.size());
        
        List<String> failures = new ArrayList<>();
        
        for (GoldenTestCase testCase : goldenCases) {
            log.info("Testing golden case: {}", testCase.getTestName());
            
            ConceptValidationRequest request = ConceptValidationRequest.builder()
                .conceptText(testCase.getConceptText())
                .intent(testCase.getIntent())
                .build();
            
            ConceptValidationResponse response = validationService.validate(request);
            
            // Check approval expectation
            if (!testCase.getExpectedApproved().equals(response.getApproved())) {
                failures.add(testCase.getTestName() + ": Expected approved=" + 
                    testCase.getExpectedApproved() + " but got " + response.getApproved());
            }
            
            // Check score range
            if (testCase.getExpectedMinScore() != null) {
                if (response.getOverallScore().compareTo(testCase.getExpectedMinScore()) < 0) {
                    failures.add(testCase.getTestName() + ": Score " + response.getOverallScore() +
                        " below minimum " + testCase.getExpectedMinScore());
                }
            }
            
            if (testCase.getExpectedMaxScore() != null) {
                if (response.getOverallScore().compareTo(testCase.getExpectedMaxScore()) > 0) {
                    failures.add(testCase.getTestName() + ": Score " + response.getOverallScore() +
                        " above maximum " + testCase.getExpectedMaxScore());
                }
            }
        }
        
        if (!failures.isEmpty()) {
            fail("Golden test suite failures:\n" + String.join("\n", failures));
        }
        
        log.info("✅ Golden test suite PASSED: {} cases", goldenCases.size());
    }
    
    @Test
    public void testPositiveGoldenCases() {
        List<GoldenTestCase> positiveCases = goldenRepo.findByCategory(GoldenTestCase.TestCategory.POSITIVE);
        
        for (GoldenTestCase testCase : positiveCases) {
            ConceptValidationRequest request = ConceptValidationRequest.builder()
                .conceptText(testCase.getConceptText())
                .intent(testCase.getIntent())
                .build();
            
            ConceptValidationResponse response = validationService.validate(request);
            
            assertTrue(response.getApproved(), 
                "Positive case '" + testCase.getTestName() + "' should be approved");
        }
    }
    
    @Test
    public void testNegativeGoldenCases() {
        List<GoldenTestCase> negativeCases = goldenRepo.findByCategory(GoldenTestCase.TestCategory.NEGATIVE);
        
        for (GoldenTestCase testCase : negativeCases) {
            ConceptValidationRequest request = ConceptValidationRequest.builder()
                .conceptText(testCase.getConceptText())
                .intent(testCase.getIntent())
                .build();
            
            ConceptValidationResponse response = validationService.validate(request);
            
            assertFalse(response.getApproved(), 
                "Negative case '" + testCase.getTestName() + "' should be rejected");
            assertFalse(response.getCriticalIssues().isEmpty(),
                "Negative case should have critical issues");
        }
    }
}
