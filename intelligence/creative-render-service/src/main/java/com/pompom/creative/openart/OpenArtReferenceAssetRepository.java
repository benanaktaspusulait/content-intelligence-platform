package com.pompom.creative.openart;

import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface OpenArtReferenceAssetRepository
    extends JpaRepository<OpenArtReferenceAsset, UUID> {

  Optional<OpenArtReferenceAsset> findBySourceAndCanonicalKey(
      OpenArtReferenceAsset.ReferenceSource source, String canonicalKey);

  Optional<OpenArtReferenceAsset> findBySourceAndProviderAssetId(
      OpenArtReferenceAsset.ReferenceSource source, String providerAssetId);

  List<OpenArtReferenceAsset> findByCanonicalKeyIgnoreCaseOrderBySourceAsc(String canonicalKey);

  List<OpenArtReferenceAsset> findAllByOrderByCanonicalKeyAscSourceAsc();
}
