package com.pompomhills.intelligence.character;

import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CharacterRepository extends JpaRepository<CharacterEntity, UUID> {
  boolean existsByNameIgnoreCase(String name);
}
