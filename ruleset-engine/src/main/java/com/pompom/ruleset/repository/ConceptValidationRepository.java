package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.ConceptValidation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface ConceptValidationRepository extends JpaRepository<ConceptValidation, UUID> {
    
    Optional<ConceptValidation> findByExternalConceptId(String externalConceptId);
    
    List<ConceptValidation> findByApprovedTrue();
    
    List<ConceptValidation> findByApprovedFalse();
    
    @Query("SELECT cv FROM ConceptValidation cv WHERE cv.createdAt >= :since ORDER BY cv.createdAt DESC")
    List<ConceptValidation> findRecentValidations(@Param("since") Instant since);
    
    @Query("SELECT COUNT(cv) FROM ConceptValidation cv WHERE cv.approved = :approved AND cv.createdAt >= :since")
    long countByApprovedSince(@Param("approved") boolean approved, @Param("since") Instant since);
}
