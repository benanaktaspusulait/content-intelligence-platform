package com.pompomhills.intelligence.workflow;
import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/v1/intelligence/workflow/cpq/owner-pilot")
public class CpqOwnerPilotController {
 private final CpqOwnerPilotService service;
 public CpqOwnerPilotController(CpqOwnerPilotService service){this.service=service;}
 @GetMapping("/capabilities") public Map<String,Object> capabilities(){return service.capabilities();}
 @GetMapping("/context") public Map<String,Object> context(@RequestParam UUID analysisId,@RequestParam(required=false) UUID comparisonId,@RequestParam(required=false) String candidateId){return service.context(analysisId,comparisonId,candidateId);}
 @PostMapping public Map<String,Object> create(@RequestBody Map<String,Object> b,HttpServletRequest r){return service.create(b,r);}
 @GetMapping("/{id}") public Map<String,Object> view(@PathVariable UUID id,HttpServletRequest r){return service.view(id,r);}
 @PostMapping("/{id}/authorizations") public Map<String,Object> authorize(@PathVariable UUID id,@RequestBody Map<String,Object> b,HttpServletRequest r){return service.authorize(id,b,r);}
 @PostMapping("/{id}/requests/{request}/execute") public Map<String,Object> execute(@PathVariable UUID id,@PathVariable UUID request,HttpServletRequest r){return service.execute(id,request,r);}
 @GetMapping("/{id}/requests/{request}/source-recovery") public Map<String,Object> recoveryPreview(@PathVariable UUID id,@PathVariable UUID request,HttpServletRequest r){return service.recoveryPreview(id,request,r);}
 @PostMapping("/{id}/requests/{request}/recover-source-evidence") public Map<String,Object> recover(@PathVariable UUID id,@PathVariable UUID request,@RequestBody Map<String,Object> b,HttpServletRequest r){return service.recoverSource(id,request,b,r);}
 @PostMapping("/{id}/decisions") public Map<String,Object> decision(@PathVariable UUID id,@RequestBody Map<String,Object> b,HttpServletRequest r){return service.decision(id,b,r);}
}
