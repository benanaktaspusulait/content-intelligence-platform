package com.pompomhills.intelligence.workflow;
import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/v1/intelligence/workflow/cpq/optimization-runs")
public class OptimizationLoopController {
 final OptimizationLoopService service;
 final com.pompomhills.intelligence.content.ContentWorkspaceController versions;
 public OptimizationLoopController(OptimizationLoopService service,com.pompomhills.intelligence.content.ContentWorkspaceController versions){this.service=service;this.versions=versions;}
 @PostMapping("/{id}/accept") public Map<String,Object> accept(@PathVariable UUID id,@RequestBody Map<String,Object> body,HttpServletRequest r){return service.accept(id,body,r,versions);}
 @GetMapping("/capabilities") public Map<String,Object> capabilities(){return service.capabilities();}
 @PostMapping("/preflight") public Map<String,Object> preflight(@RequestBody Map<String,Object> body,HttpServletRequest r){return service.preflight(body,r);}
 @PostMapping public Map<String,Object> start(@RequestBody Map<String,Object> body,HttpServletRequest r){return service.start(body,r);}
 @GetMapping("/latest") public Map<String,Object> latest(@RequestParam UUID analysisId,HttpServletRequest r){return service.latest(analysisId,r);}
 @GetMapping("/{id}") public Map<String,Object> view(@PathVariable UUID id,HttpServletRequest r){return service.view(id,r);}
 @PostMapping("/{id}/stop") public Map<String,Object> stop(@PathVariable UUID id,HttpServletRequest r){return service.stop(id,r);}
 @PostMapping("/{id}/resume") public Map<String,Object> resume(@PathVariable UUID id,HttpServletRequest r){return service.resume(id,r);}
}
