package com.pompomhills.intelligence.character.api;

import com.pompomhills.intelligence.character.CharacterService;
import com.pompomhills.intelligence.character.CharacterService.VideoCharacterInput;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/videos/{videoId}/characters")
public class VideoCharactersController {
  private final CharacterService service;

  public VideoCharactersController(CharacterService service) {
    this.service = service;
  }

  @PutMapping
  @ResponseStatus(HttpStatus.NO_CONTENT)
  public void replace(@PathVariable UUID videoId, @Valid @RequestBody ReplaceCharacters request) {
    service.replaceForVideo(
        videoId,
        request.characters().stream()
            .map(item -> new VideoCharacterInput(item.characterId(), item.participation(), item.role()))
            .toList());
  }

  public record ReplaceCharacters(@NotNull @Valid List<Item> characters) {}

  public record Item(@NotNull UUID characterId, @NotBlank String participation, @NotBlank String role) {}
}
