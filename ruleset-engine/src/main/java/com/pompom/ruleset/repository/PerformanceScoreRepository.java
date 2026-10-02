package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.PerformanceScore;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface PerformanceScoreRepository extends JpaRepository<PerformanceScore, UUID> {
    
    Optional<PerformanceScore> findByExternalVideoId(String externalVideoId);
    
    List<PerformanceScore> findByPlatform(PerformanceScore.Platform platform);
    
    @Query("SELECT ps FROM PerformanceScore ps WHERE ps.classification = :classification ORDER BY ps.overallQuality DESC")
    List<PerformanceScore> findByClassification(@Param("classification") PerformanceScore.PerformanceClassification classification);
}
