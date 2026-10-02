package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.GoldenTestCase;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface GoldenTestCaseRepository extends JpaRepository<GoldenTestCase, UUID> {
    
    Optional<GoldenTestCase> findByTestName(String testName);
    
    List<GoldenTestCase> findByCategory(GoldenTestCase.TestCategory category);
}
