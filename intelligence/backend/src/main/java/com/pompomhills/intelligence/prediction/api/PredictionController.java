package com.pompomhills.intelligence.prediction.api;

import com.pompomhills.intelligence.prediction.PredictionService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/predictions")
public class PredictionController {
  private final PredictionService service;

  public PredictionController(PredictionService service) {
    this.service = service;
  }

  @PostMapping
  public PredictionService.PredictionView generate(@Valid @RequestBody GeneratePrediction request) {
    return service.generate(request.videoId(), request.platform().toLowerCase());
  }

  @PostMapping("/live")
  public PredictionService.PredictionView generateLive(
      @Valid @RequestBody GenerateLivePrediction request) {
    return service.generateLive(
        request.videoId(), request.platform().toLowerCase(), request.knowledgeCutoff());
  }

  @PostMapping("/{id}/lock")
  public PredictionService.PredictionView lock(
      @PathVariable UUID id, @RequestBody(required = false) LockPrediction request) {
    return service.lock(id, request == null ? "confirmed for publication" : request.reason());
  }

  @GetMapping
  public List<PredictionService.PredictionView> list() {
    return service.list();
  }

  @PostMapping("/{id}/evaluate")
  public PredictionService.PredictionView evaluate(
      @PathVariable UUID id, @Valid @RequestBody EvaluatePrediction request) {
    return service.evaluate(id, request.horizonMinutes(), request.actualValue());
  }

  @GetMapping("/video/{videoId}")
  public List<PredictionService.PredictionView> history(@PathVariable UUID videoId) {
    return service.history(videoId);
  }

  public record GeneratePrediction(UUID videoId, @NotBlank String platform) {}

  public record GenerateLivePrediction(
      UUID videoId, @NotBlank String platform, java.time.Instant knowledgeCutoff) {}

  public record LockPrediction(String reason) {}

  public record EvaluatePrediction(int horizonMinutes, double actualValue) {}
}
