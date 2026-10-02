package com.pompom.ruleset.engine;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RuleResult {
    private Boolean passed;
    private BigDecimal score;
    private String reason;
    private Map<String, Object> details;
    
    public static RuleResult pass(String reason) {
        return RuleResult.builder()
            .passed(true)
            .score(BigDecimal.valueOf(100.0))
            .reason(reason)
            .build();
    }
    
    public static RuleResult fail(String reason) {
        return RuleResult.builder()
            .passed(false)
            .score(BigDecimal.ZERO)
            .reason(reason)
            .build();
    }
    
    public static RuleResult warn(String reason) {
        return RuleResult.builder()
            .passed(false)
            .score(BigDecimal.valueOf(50.0))
            .reason(reason)
            .build();
    }
    
    public static RuleResult score(boolean passed, double score, String reason) {
        return RuleResult.builder()
            .passed(passed)
            .score(BigDecimal.valueOf(score))
            .reason(reason)
            .build();
    }
}
