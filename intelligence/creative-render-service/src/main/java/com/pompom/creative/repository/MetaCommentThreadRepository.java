package com.pompom.creative.repository;

import com.pompom.creative.domain.MetaCommentThread;
import com.pompom.creative.oauth.PlatformType;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MetaCommentThreadRepository extends JpaRepository<MetaCommentThread, UUID> {
  Optional<MetaCommentThread> findByPlatformAndExternalThreadKey(
      PlatformType platform, String externalThreadKey);
}
