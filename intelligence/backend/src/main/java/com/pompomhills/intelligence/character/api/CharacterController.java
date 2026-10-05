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

  public CharacterController(CharacterService service, com.pompomhills.intelligence.character.VideoCharacterAssociationService associations) {
    this.service = service;
    this.associations = associations;
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
}
