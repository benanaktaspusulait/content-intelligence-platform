package com.pompomhills.intelligence.workflow;

import java.util.*;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/intelligence/workflow/idea-drafts")
public class IdeaDraftController {
  private final IdeaDraftService service;
  public IdeaDraftController(IdeaDraftService service){this.service=service;}
  @GetMapping public List<Map<String,Object>> list(){return service.list();}
  @GetMapping("/{id}") public Map<String,Object> get(@PathVariable UUID id,@RequestParam String workspacePath){return service.get(id,workspacePath);}
  @PostMapping public Map<String,Object> save(@RequestBody Map<String,Object> request){return service.save(request);}
  @PostMapping("/{id}/continue") public Map<String,Object> proceed(@PathVariable UUID id,@RequestBody Map<String,Object> request){return service.continueDraft(id,request);}
}
