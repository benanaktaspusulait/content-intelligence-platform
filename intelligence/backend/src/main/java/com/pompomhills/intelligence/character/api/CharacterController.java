package com.pompomhills.intelligence.character.api;

import com.pompomhills.intelligence.character.CharacterService;
import com.pompomhills.intelligence.character.CharacterStatus;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/characters")
public class CharacterController {
  private final CharacterService service;
  private final com.pompomhills.intelligence.character.VideoCharacterAssociationService associations;
  private final com.pompomhills.intelligence.character.CharacterReferenceService references;

  public CharacterController(CharacterService service, com.pompomhills.intelligence.character.VideoCharacterAssociationService associations,
      com.pompomhills.intelligence.character.CharacterReferenceService references) {
    this.service = service;
    this.associations = associations;
    this.references = references;
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public CharacterService.CharacterView create(@Valid @RequestBody CreateCharacter request) {
    return service.create(request.name(), request.status(), request.notes());
  }

  @GetMapping
  public List<CharacterService.CharacterView> list() {
    return service.list();
  }

  @GetMapping("/coverage")
  public List<CharacterService.CharacterCoverageView> coverage() {
    return service.coverage();
  }

  @GetMapping("/{characterId}/references")
  public List<java.util.Map<String, Object>> references(@PathVariable UUID characterId) {
    return references.list(characterId).stream().map(row -> {
      java.util.Map<String, Object> result = new java.util.LinkedHashMap<>(row);
      result.put("previewUrl", "/api/v1/characters/" + characterId + "/references/" + row.get("id") + "/image");
      return result;
    }).toList();
  }

  @GetMapping("/{characterId}/references/{referenceId}/image")
  public org.springframework.http.ResponseEntity<org.springframework.core.io.Resource> referenceImage(
      @PathVariable UUID characterId, @PathVariable UUID referenceId) {
    java.nio.file.Path path = references.imagePath(characterId, referenceId);
    var resource = new org.springframework.core.io.FileSystemResource(path);
    var media = org.springframework.http.MediaTypeFactory.getMediaType(resource)
        .orElse(org.springframework.http.MediaType.APPLICATION_OCTET_STREAM);
    return org.springframework.http.ResponseEntity.ok().contentType(media)
        .header(org.springframework.http.HttpHeaders.CACHE_CONTROL, "private, no-store")
        .body(resource);
  }

  @PostMapping(value = "/{characterId}/references", consumes = org.springframework.http.MediaType.MULTIPART_FORM_DATA_VALUE)
  @ResponseStatus(HttpStatus.CREATED)
  public java.util.Map<String, Object> uploadReference(@PathVariable UUID characterId,
      @RequestPart("file") org.springframework.web.multipart.MultipartFile file,
      @RequestParam(defaultValue = "") String description) {
    return references.upload(characterId, file, description);
  }

  @PostMapping("/{characterId}/references/{referenceId}/approve")
  public java.util.Map<String, Object> approveReference(@PathVariable UUID characterId,
      @PathVariable UUID referenceId, @Valid @RequestBody ApproveReference request) {
    return references.approve(characterId, referenceId, request.reviewer());
  }

  @PostMapping("/{characterId}/videos/{videoId}")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  public void assign(
      @PathVariable UUID characterId,
      @PathVariable UUID videoId,
      @Valid @RequestBody AssignCharacter request) {
    service.assign(
        videoId,
        characterId,
        request.participation(),
        request.role(),
        request.screenTimeRatio(),
        request.actionShare(),
        request.speakingShare());
  }

  @PostMapping("/associations/backfill")
  public com.pompomhills.intelligence.character.VideoCharacterAssociationService.BackfillReport backfill(
      @RequestParam(defaultValue = "MISSING_ONLY") String mode,
      @RequestParam(defaultValue = "true") boolean dryRun) {
    return associations.backfill(com.pompomhills.intelligence.character.VideoCharacterAssociationService.Mode.valueOf(mode), dryRun);
  }

  public record CreateCharacter(
      @NotBlank String name, @NotNull CharacterStatus status, String notes) {}

  public record AssignCharacter(
      @NotBlank String participation,
      @NotBlank String role,
      Double screenTimeRatio,
      Double actionShare,
      Double speakingShare) {}

  public record ApproveReference(@NotBlank String reviewer) {}
}
