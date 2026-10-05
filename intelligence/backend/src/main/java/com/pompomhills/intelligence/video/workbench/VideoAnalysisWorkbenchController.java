package com.pompomhills.intelligence.video.workbench;

import java.util.UUID;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import static com.pompomhills.intelligence.video.workbench.VideoAnalysisWorkbenchDtos.*;

@RestController
@RequestMapping("/api/v1/videos/analysis-workbench")
public class VideoAnalysisWorkbenchController {
  private final VideoAnalysisWorkbenchService service;
  public VideoAnalysisWorkbenchController(VideoAnalysisWorkbenchService service){this.service=service;}
  @GetMapping
  public PageResponse page(@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="25") int size,@RequestParam(required=false) String analysisStatus,@RequestParam(required=false) String triage,@RequestParam(required=false) String publicationState,@RequestParam(required=false) UUID characterId,@RequestParam(required=false) String characterRole,@RequestParam(required=false) String query,@RequestParam(defaultValue="date") String sort,@RequestParam(defaultValue="desc") String direction){return service.page(page,size,analysisStatus,triage,publicationState,characterId,characterRole,query,sort,direction);}
  @PostMapping("/bulk")
  public BulkResponse bulk(@RequestBody BulkRequest request){return service.bulk(request);}
}
