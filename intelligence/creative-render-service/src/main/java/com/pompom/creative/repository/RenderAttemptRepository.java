package com.pompom.creative.repository;

import com.pompom.creative.domain.RenderAttempt;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface RenderAttemptRepository extends JpaRepository<RenderAttempt, UUID> {

  List<RenderAttempt> findByRenderJobIdOrderByAttemptNumberAsc(UUID renderJobId);

  Optional<RenderAttempt> findTopByRenderJobIdOrderByAttemptNumberDesc(UUID renderJobId);
}
