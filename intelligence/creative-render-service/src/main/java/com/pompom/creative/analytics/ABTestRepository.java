package com.pompom.creative.analytics;

import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface ABTestRepository extends JpaRepository<ABTest, UUID> {

  List<ABTest> findByStatusOrderByCreatedAtDesc(ABTest.TestStatus status);

  List<ABTest> findAllByOrderByCreatedAtDesc();
}
