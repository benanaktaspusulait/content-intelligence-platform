package com.pompom.creative.repository;

import com.pompom.creative.domain.PublicationAnalytics;
import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

@Repository
public interface PublicationAnalyticsRepository extends JpaRepository<PublicationAnalytics, UUID> {

  Optional<PublicationAnalytics> findByPublicationJobId(UUID publicationJobId);

  List<PublicationAnalytics> findByPlatform(PlatformType platform);

  List<PublicationAnalytics> findByFetchedAtBefore(Instant before);

  @Query("SELECT SUM(a.views) FROM PublicationAnalytics a WHERE a.platform = :platform")
  Long sumViewsByPlatform(PlatformType platform);

  @Query("SELECT SUM(a.views) FROM PublicationAnalytics a")
  Long sumTotalViews();

  @Query("SELECT AVG(a.engagementRate) FROM PublicationAnalytics a WHERE a.platform = :platform")
  Double avgEngagementRateByPlatform(PlatformType platform);

  @Query("SELECT a FROM PublicationAnalytics a ORDER BY a.views DESC")
  List<PublicationAnalytics> findTopByViews(org.springframework.data.domain.Pageable pageable);

  @Query("SELECT a FROM PublicationAnalytics a ORDER BY a.engagementRate DESC")
  List<PublicationAnalytics> findTopByEngagement(org.springframework.data.domain.Pageable pageable);
}
