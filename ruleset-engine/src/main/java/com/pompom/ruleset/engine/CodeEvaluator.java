package com.pompom.ruleset.engine;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.Rule;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class CodeEvaluator implements RuleEvaluator {
    
    @Override
    public RuleResult evaluate(Rule rule, ConceptValidationRequest request) {
        log.debug("Evaluating rule {} with CODE evaluator", rule.getRuleCode());
        
        return switch (rule.getRuleCode()) {
            case "CONCEPT_001_IMMEDIATE_ANOMALY" -> evaluateImmediateAnomaly(request);
            case "BEAT_003_STORY_DETACHED_GAP" -> evaluateStoryDetachedGap(request);
            case "MOTION_001_MEANINGFUL_MOTION" -> evaluateMeaningfulMotion(request);
            case "PROMPT_001_OVER_CONSTRAINT" -> evaluateOverConstraint(request);
            default -> {
                log.warn("No CODE evaluator for rule {}", rule.getRuleCode());
                yield RuleResult.pass("No code evaluator implemented");
            }
        };
    }
    
    @Override
    public boolean supports(Rule rule) {
        return rule.getEvaluationType() == Rule.EvaluationType.CODE ||
               rule.getEvaluationType() == Rule.EvaluationType.HYBRID;
    }
    
    private RuleResult evaluateImmediateAnomaly(ConceptValidationRequest request) {
        String concept = request.getConceptText().toLowerCase();
        
        boolean hasVisualAnomaly = 
            concept.contains("giant") || concept.contains("huge") ||
            concept.contains("tiny") || concept.contains("upside down") ||
            concept.contains("floating") || concept.contains("upward") ||
            concept.contains("dirty") || concept.contains("clean") ||
            concept.contains("reversed") || concept.contains("backward");
        
        boolean mightBeSubtle =
            concept.contains("slowly") || concept.contains("gradually") ||
            concept.contains("eventually") || concept.contains("later");
        
        if (!hasVisualAnomaly) {
            return RuleResult.fail("No immediate visual anomaly detected in concept");
        }
        
        if (mightBeSubtle) {
            return RuleResult.warn("Anomaly may be gradual rather than immediate");
        }
        
        return RuleResult.pass("Visual anomaly is immediate");
    }
    
    private RuleResult evaluateStoryDetachedGap(ConceptValidationRequest request) {
        String concept = request.getConceptText().toLowerCase();
        
        boolean hasDetachedScenery =
            (concept.contains("landscape") || concept.contains("scenery") || 
             concept.contains("pan to") || concept.contains("cut to")) &&
            !concept.contains("relevant") && !concept.contains("related");
        
        boolean hasUnrelatedInsert =
            concept.contains("meanwhile") || concept.contains("elsewhere") ||
            concept.contains("unrelated");
        
        if (hasDetachedScenery || hasUnrelatedInsert) {
            return RuleResult.fail("Concept includes story-detached elements");
        }
        
        return RuleResult.pass("All elements are story-relevant");
    }
    
    private RuleResult evaluateMeaningfulMotion(ConceptValidationRequest request) {
        String concept = request.getConceptText().toLowerCase();
        
        boolean hasLongPauses =
            concept.contains("long pause") || concept.contains("wait") ||
            concept.contains("static for") || concept.contains("freeze");
        
        boolean hasEducationalPause =
            concept.contains("reads") || concept.contains("learning") ||
            concept.contains("educational moment");
        
        boolean hasFakeWinPause =
            concept.contains("realizes") || concept.contains("fake win") ||
            concept.contains("brief celebration");
        
        if (hasLongPauses && !hasEducationalPause && !hasFakeWinPause) {
            return RuleResult.warn("Concept may include unmotivated static moments");
        }
        
        return RuleResult.pass("Motion/progression pacing is appropriate");
    }
    
    private RuleResult evaluateOverConstraint(ConceptValidationRequest request) {
        return RuleResult.pass("Over-constraint check requires prompt text");
    }
}
