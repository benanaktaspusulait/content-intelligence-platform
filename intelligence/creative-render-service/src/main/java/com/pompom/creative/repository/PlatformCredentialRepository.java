package com.pompom.creative.repository;

import com.pompom.creative.domain.PlatformCredential;
import com.pompom.creative.oauth.PlatformType;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface PlatformCredentialRepository extends JpaRepository<PlatformCredential, UUID> {

  Optional<PlatformCredential> findByPlatform(PlatformType platform);

  Optional<PlatformCredential> findByPlatformAndIsActiveTrue(PlatformType platform);

  List<PlatformCredential> findByIsActiveTrue();

  boolean existsByPlatformAndIsActiveTrue(PlatformType platform);
}
