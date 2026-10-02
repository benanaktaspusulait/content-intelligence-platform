package com.pompom.ruleset.api.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptValidationResponse {
    
    private UUID validationId;
    
    private Boolean approved;
    
    private BigDecimal overallScore;
    
    private List<RuleResultDto> ruleResults;
    
    private List<String> recommendations;
    
    private List<String> criticalIssues;
    
    private List<String> warnings;
    
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RuleResultDto {
        private String ruleCode;
        private String ruleName;
        private Boolean passed;
        private BigDecimal score;
        private String reason;
        private String severity;
    }
}
