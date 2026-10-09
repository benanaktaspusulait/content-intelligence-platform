package com.pompom.creative.visual;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface VisualReferencePlanRepository extends JpaRepository<VisualReferencePlan, UUID> {
  Optional<VisualReferencePlan> findByRenderJobId(UUID renderJobId);
}
