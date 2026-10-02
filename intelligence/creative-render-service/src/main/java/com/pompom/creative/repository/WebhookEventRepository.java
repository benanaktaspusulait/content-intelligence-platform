package com.pompom.creative.repository;

import com.pompom.creative.domain.WebhookEvent;
import com.pompom.creative.oauth.PlatformType;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface WebhookEventRepository extends JpaRepository<WebhookEvent, UUID> {

  List<WebhookEvent> findByIsProcessedFalse();

  List<WebhookEvent> findByIsProcessedFalseAndRetryCountLessThan(int maxRetries);

  List<WebhookEvent> findByPlatform(PlatformType platform);

  List<WebhookEvent> findByPublicationJobId(UUID publicationJobId);

  List<WebhookEvent> findByCreatedAtBefore(Instant before);

  long countByIsProcessedFalse();

  long countByIsProcessedTrue();
}
