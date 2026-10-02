package com.pompom.ruleset.api.controller;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.service.ConceptValidationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/validate")
@RequiredArgsConstructor
@Slf4j
public class ValidationController {
    
    private final ConceptValidationService validationService;
    
    @PostMapping("/concept")
    public ResponseEntity<ConceptValidationResponse> validateConcept(
        @Valid @RequestBody ConceptValidationRequest request
    ) {
        log.info("POST /validate/concept - externalId: {}", request.getExternalConceptId());
        
        ConceptValidationResponse response = validationService.validate(request);
        
        return ResponseEntity.ok(response);
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<ConceptValidationResponse> getValidation(
        @PathVariable UUID id
    ) {
        log.info("GET /validate/{}", id);
        return ResponseEntity.notFound().build();
    }
}
