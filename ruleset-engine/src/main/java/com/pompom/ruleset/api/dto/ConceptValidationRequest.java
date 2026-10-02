package com.pompom.ruleset.api.dto;

import com.pompom.ruleset.domain.ConceptValidation;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ConceptValidationRequest {
    
    private String externalConceptId;
    
    @NotBlank(message = "Concept text is required")
    private String conceptText;
    
    private ConceptValidation.ContentIntent intent;
    
    private BigDecimal estimatedDuration;
    
    private List<String> characters;
    
    private String location;
}
