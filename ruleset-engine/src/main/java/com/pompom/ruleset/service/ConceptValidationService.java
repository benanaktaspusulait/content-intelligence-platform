package com.pompom.ruleset.service;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.domain.ConceptValidation;
import com.pompom.ruleset.domain.Rule;
import com.pompom.ruleset.domain.RuleEvaluation;
import com.pompom.ruleset.engine.CodeEvaluator;
import com.pompom.ruleset.engine.LlmEvaluator;
import com.pompom.ruleset.engine.RuleResult;
import com.pompom.ruleset.repository.ConceptValidationRepository;
import com.pompom.ruleset.repository.RuleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
@RequiredArgsConstructor
public class ConceptValidationService {
    
    private final RuleRepository ruleRepository;
    private final ConceptValidationRepository validationRepository;
    private final CodeEvaluator codeEvaluator;
    private final LlmEvaluator llmEvaluator;
    
    @Transactional
    public ConceptValidationResponse validate(ConceptValidationRequest request) {
        log.info("Validating concept: {}", request.getExternalConceptId());
        
        List<Rule> rules = ruleRepository.findByActiveTrue();
        log.debug("Loaded {} active rules", rules.size());
        
        ConceptValidation validation = ConceptValidation.builder()
            .externalConceptId(request.getExternalConceptId())
            .conceptText(request.getConceptText())
            .intent(request.getIntent())
            .build();
        
        List<RuleEvaluation> evaluations = new ArrayList<>();
        for (Rule rule : rules) {
            RuleResult result = evaluateRule(rule, request);
            
            RuleEvaluation evaluation = RuleEvaluation.builder()
                .rule(rule)
                .passed(result.getPassed())
                .score(result.getScore())
                .reason(result.getReason())
                .details(result.getDetails())
                .build();
            
            validation.addRuleEvaluation(evaluation);
            evaluations.add(evaluation);
        }
        
        BigDecimal overallScore = calculateOverallScore(evaluations);
        validation.setOverallScore(overallScore);
        
        boolean approved = !validation.hasCriticalFailures() && 
                          overallScore.compareTo(BigDecimal.valueOf(60.0)) >= 0;
        validation.setApproved(approved);
        
        validationRepository.save(validation);
        
        return buildResponse(validation);
    }
    
    private RuleResult evaluateRule(Rule rule, ConceptValidationRequest request) {
        try {
            RuleResult result = null;
            
            if (rule.getEvaluationType() == Rule.EvaluationType.CODE) {
                result = codeEvaluator.evaluate(rule, request);
            } else if (rule.getEvaluationType() == Rule.EvaluationType.LLM) {
                result = llmEvaluator.evaluate(rule, request);
            } else if (rule.getEvaluationType() == Rule.EvaluationType.HYBRID) {
                RuleResult codeResult = codeEvaluator.evaluate(rule, request);
                RuleResult llmResult = llmEvaluator.evaluate(rule, request);
                result = combineResults(codeResult, llmResult);
            }
            
            return result != null ? result : RuleResult.pass("No evaluator");
        } catch (Exception e) {
            log.error("Rule evaluation failed for {}", rule.getRuleCode(), e);
            return RuleResult.fail("Evaluation error: " + e.getMessage());
        }
    }
    
    private RuleResult combineResults(RuleResult code, RuleResult llm) {
        boolean passed = code.getPassed() && llm.getPassed();
        BigDecimal avgScore = code.getScore().add(llm.getScore())
            .divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP);
        String reason = "Code: " + code.getReason() + " | LLM: " + llm.getReason();
        
        return RuleResult.builder()
            .passed(passed)
            .score(avgScore)
            .reason(reason)
            .build();
    }
    
    private BigDecimal calculateOverallScore(List<RuleEvaluation> evaluations) {
        if (evaluations.isEmpty()) {
            return BigDecimal.ZERO;
        }
        
        BigDecimal totalScore = evaluations.stream()
            .map(RuleEvaluation::getScore)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        return totalScore.divide(
            BigDecimal.valueOf(evaluations.size()),
            2,
            RoundingMode.HALF_UP
        );
    }
    
    private ConceptValidationResponse buildResponse(ConceptValidation validation) {
        List<ConceptValidationResponse.RuleResultDto> ruleResults = validation.getRuleEvaluations().stream()
            .map(eval -> ConceptValidationResponse.RuleResultDto.builder()
                .ruleCode(eval.getRule().getRuleCode())
                .ruleName(eval.getRule().getName())
                .passed(eval.getPassed())
                .score(eval.getScore())
                .reason(eval.getReason())
                .severity(eval.getRule().getSeverity().toString())
                .build())
            .collect(Collectors.toList());
        
        List<String> criticalIssues = validation.getRuleEvaluations().stream()
            .filter(RuleEvaluation::isCriticalFailure)
            .map(eval -> eval.getRule().getName() + ": " + eval.getReason())
            .collect(Collectors.toList());
        
        List<String> warnings = validation.getRuleEvaluations().stream()
            .filter(RuleEvaluation::isWarning)
            .map(eval -> eval.getRule().getName() + ": " + eval.getReason())
            .collect(Collectors.toList());
        
        return ConceptValidationResponse.builder()
            .validationId(validation.getId())
            .approved(validation.getApproved())
            .overallScore(validation.getOverallScore())
            .ruleResults(ruleResults)
            .criticalIssues(criticalIssues)
            .warnings(warnings)
            .recommendations(generateRecommendations(validation))
            .build();
    }
    
    private List<String> generateRecommendations(ConceptValidation validation) {
        List<String> recommendations = new ArrayList<>();
        
        validation.getRuleEvaluations().stream()
            .filter(eval -> eval.getRule().getRuleCode().equals("LOOPABILITY_001_LOOP_STRUCTURE"))
            .filter(eval -> eval.getScore() != null && eval.getScore().compareTo(BigDecimal.valueOf(80)) >= 0)
            .findFirst()
            .ifPresent(eval -> recommendations.add("Strong loopability potential - consider hard cut ending"));
        
        return recommendations;
    }
}
