package com.pompom.ruleset.api.controller;

import com.pompom.ruleset.api.dto.PerformanceAnalysisRequest;
import com.pompom.ruleset.api.dto.PerformanceAnalysisResponse;
import com.pompom.ruleset.service.PerformanceAnalysisService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/performance")
@RequiredArgsConstructor
@Slf4j
public class PerformanceController {
    
    private final PerformanceAnalysisService analysisService;
    
    @PostMapping("/analyze")
    public ResponseEntity<PerformanceAnalysisResponse> analyzePerformance(
        @Valid @RequestBody PerformanceAnalysisRequest request
    ) {
        log.info("POST /performance/analyze - videoId: {}", request.getExternalVideoId());
        
        PerformanceAnalysisResponse response = analysisService.analyze(request);
        
        return ResponseEntity.ok(response);
    }
}
