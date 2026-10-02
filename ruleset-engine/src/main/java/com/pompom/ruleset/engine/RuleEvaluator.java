package com.pompom.ruleset.engine;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.Rule;

public interface RuleEvaluator {
    
    /**
     * Evaluate a rule against a concept.
     * 
     * @param rule The rule to evaluate
     * @param request The concept validation request
     * @return RuleResult with pass/fail and reasoning
     */
    RuleResult evaluate(Rule rule, ConceptValidationRequest request);
    
    /**
     * Check if this evaluator supports the given rule.
     */
    boolean supports(Rule rule);
}
