package com.pompomhills.intelligence.character;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.jdbc.core.simple.JdbcClient;

class CharacterWorkspaceReferenceTest {
  @Test
  void discoversExistingMatchingArtworkWithoutWritesAndRejectsOtherCharacter(@TempDir Path root) throws Exception {
    UUID id = UUID.randomUUID();
    var characters = mock(CharacterRepository.class);
    when(characters.findById(id)).thenReturn(Optional.of(new CharacterEntity(id, "Mimi", CharacterStatus.ESTABLISHED, "")));
    var jdbc = mock(JdbcClient.class);
    var service = new CharacterReferenceService(jdbc, characters, root.toString());
    Path folder = Files.createDirectories(root.resolve("library/01-CHARACTERS/drawings"));
    var image = new java.awt.image.BufferedImage(90,160,java.awt.image.BufferedImage.TYPE_INT_RGB);
    javax.imageio.ImageIO.write(image, "png", folder.resolve("mimi.png").toFile());
    javax.imageio.ImageIO.write(image, "png", folder.resolve("mimo.png").toFile());
    assertThat(service.workspaceReferences(id)).hasSize(1);
    assertThat(service.workspaceReferences(id).getFirst()).containsEntry("status", "UNREVIEWED");
    assertThat(service.workspaceImage(id, "library/01-CHARACTERS/drawings/mimi.png")).isEqualTo(folder.resolve("mimi.png"));
    assertThatThrownBy(() -> service.workspaceImage(id, "library/01-CHARACTERS/drawings/mimo.png")).hasMessageContaining("this character");
    assertThatThrownBy(() -> service.workspaceImage(id, "../outside.png")).hasMessageContaining("this character");
    verifyNoInteractions(jdbc);
  }
}
