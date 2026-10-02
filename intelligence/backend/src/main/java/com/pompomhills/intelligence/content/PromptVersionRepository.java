package com.pompomhills.intelligence.content;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PromptVersionRepository extends JpaRepository<PromptVersionEntity, Long> {
  Optional<PromptVersionEntity> findByIdAndContentId(Long id, Long contentId);
}
