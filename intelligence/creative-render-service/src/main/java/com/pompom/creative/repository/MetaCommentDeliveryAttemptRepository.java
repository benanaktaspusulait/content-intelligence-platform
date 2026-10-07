package com.pompom.creative.repository;

import com.pompom.creative.domain.MetaCommentDeliveryAttempt;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface MetaCommentDeliveryAttemptRepository
    extends JpaRepository<MetaCommentDeliveryAttempt, UUID> {}
