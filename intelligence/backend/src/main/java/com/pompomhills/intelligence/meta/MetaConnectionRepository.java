package com.pompomhills.intelligence.meta;

import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MetaConnectionRepository extends JpaRepository<MetaConnectionEntity, UUID> {
  Optional<MetaConnectionEntity> findByIdAndOwnerKey(UUID id, String ownerKey);

  Optional<MetaConnectionEntity>
      findByOwnerKeyAndProviderUserIdAndFacebookPageIdAndInstagramAccountId(
          String ownerKey,
          String providerUserId,
          String facebookPageId,
          String instagramAccountId);

  Optional<MetaConnectionEntity> findByOwnerKeyAndFacebookPageId(
      String ownerKey, String facebookPageId);

  Optional<MetaConnectionEntity> findTopByOwnerKeyOrderByUpdatedAtDesc(String ownerKey);

}
