package com.pompomhills.intelligence.quality;

import com.pompomhills.intelligence.quality.VisualEvidenceDtos.VisualEvidenceRequest;
import com.pompomhills.intelligence.quality.VisualEvidenceDtos.VisualEvidenceResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/** Internal append-only submission boundary for explicit first-frame visual verification. */
@RestController
@RequestMapping("/api/v1/internal/validation-evidence")
public class VisualEvidenceController {
  private final VisualEvidenceSubmissionService service;

  public VisualEvidenceController(VisualEvidenceSubmissionService service) {
    this.service = service;
  }

  @PostMapping("/{validationRecordId}/visual")
  public ResponseEntity<VisualEvidenceResponse> submit(
      @PathVariable long validationRecordId, @RequestBody VisualEvidenceRequest request) {
    try {
      VisualEvidenceResponse response = service.submit(validationRecordId, request);
      return ResponseEntity.status(response.created() ? HttpStatus.CREATED : HttpStatus.OK).body(response);
    } catch (ValidationEvidenceNotFoundException error) {
      throw new org.springframework.web.server.ResponseStatusException(HttpStatus.NOT_FOUND, error.getMessage(), error);
    } catch (VisualEvidenceConflictException error) {
      throw new org.springframework.web.server.ResponseStatusException(HttpStatus.CONFLICT, error.getMessage(), error);
    } catch (VisualEvidenceInvalidException error) {
      throw new org.springframework.web.server.ResponseStatusException(HttpStatus.UNPROCESSABLE_ENTITY, error.getMessage(), error);
    }
  }
}
