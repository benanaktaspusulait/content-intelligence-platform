package com.pompomhills.intelligence.workflow;
import java.util.*;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/v1/intelligence/workflow/cpq/draft-review")
public class CpqDraftReviewController {
 final CpqDraftReviewService service;
 public CpqDraftReviewController(CpqDraftReviewService service){this.service=service;}
 @GetMapping("/preflight") public Map<String,Object> preflight(HttpServletRequest r){return service.preflight(r);}
 @PostMapping public Map<String,Object> create(@RequestBody Map<String,Object> body,HttpServletRequest r){return service.create(body,r);}
 @GetMapping("/{id}") public Map<String,Object> view(@PathVariable UUID id,HttpServletRequest r){return service.view(id,r);}
 @PostMapping("/{id}/authorizations") public Map<String,Object> authorize(@PathVariable UUID id,@RequestBody Map<String,Object> body,HttpServletRequest r){return service.authorize(id,body,r);}
 @PostMapping("/{id}/requests/{request}/execute") public Map<String,Object> execute(@PathVariable UUID id,@PathVariable UUID request,HttpServletRequest r){return service.execute(id,request,r);}
}
