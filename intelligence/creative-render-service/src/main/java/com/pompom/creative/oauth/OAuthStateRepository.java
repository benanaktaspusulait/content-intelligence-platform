package com.pompom.creative.oauth;

import java.time.Instant;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OAuthStateRepository extends JpaRepository<OAuthState, String> {

  @Modifying
  @Query(
      "UPDATE OAuthState s SET s.consumedAt = :consumedAt "
          + "WHERE s.stateHash = :stateHash AND s.consumedAt IS NULL AND s.expiresAt > :consumedAt")
  int consume(@Param("stateHash") String stateHash, @Param("consumedAt") Instant consumedAt);

  void deleteByExpiresAtBefore(Instant cutoff);
}
