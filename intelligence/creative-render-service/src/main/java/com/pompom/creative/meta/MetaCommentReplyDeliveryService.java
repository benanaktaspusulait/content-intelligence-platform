package com.pompom.creative.meta;

import com.pompom.creative.domain.MetaCommentDeliveryAttempt;
import com.pompom.creative.domain.MetaCommentReply;
import com.pompom.creative.oauth.MetaCommentReplyGuard;
import com.pompom.creative.oauth.PlatformType;
import com.pompom.creative.repository.MetaCommentDeliveryAttemptRepository;
import com.pompom.creative.repository.MetaCommentReplyRepository;
import java.net.SocketTimeoutException;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeoutException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientResponseException;

/** Durable, human-approved public comment reply orchestration. */
@Service
public class MetaCommentReplyDeliveryService {

  private final MetaCommentReplyRepository replyRepository;
  private final MetaCommentDeliveryAttemptRepository attemptRepository;
  private final Map<PlatformType, MetaCommentReplyPort> ports;
  private final MetaCommentReplyGuard guard;
  private final TransactionTemplate transactionTemplate;

  @Autowired
  public MetaCommentReplyDeliveryService(
      MetaCommentReplyRepository replyRepository,
      MetaCommentDeliveryAttemptRepository attemptRepository,
      List<MetaCommentReplyPort> ports,
      MetaCommentReplyGuard guard,
      TransactionTemplate transactionTemplate) {
    this(
        replyRepository,
        attemptRepository,
        ports.stream()
            .collect(java.util.stream.Collectors.toMap(MetaCommentReplyPort::platform, p -> p)),
        guard,
        transactionTemplate);
  }

  MetaCommentReplyDeliveryService(
      MetaCommentReplyRepository replyRepository,
      MetaCommentDeliveryAttemptRepository attemptRepository,
      Map<PlatformType, MetaCommentReplyPort> ports,
      MetaCommentReplyGuard guard) {
    this(replyRepository, attemptRepository, ports, guard, null);
  }

  MetaCommentReplyDeliveryService(
      MetaCommentReplyRepository replyRepository,
      MetaCommentDeliveryAttemptRepository attemptRepository,
      Map<PlatformType, MetaCommentReplyPort> ports,
      MetaCommentReplyGuard guard,
      TransactionTemplate transactionTemplate) {
    this.replyRepository = replyRepository;
    this.attemptRepository = attemptRepository;
    this.ports = ports;
    this.guard = guard;
    this.transactionTemplate = transactionTemplate;
  }

  public MetaCommentReply send(UUID replyId) {
    DeliveryClaim claim = claim(replyId);
    if (!claim.providerCallRequired()) {
      return claim.reply();
    }

    MetaCommentReply reply = claim.reply();
    MetaCommentDeliveryAttempt attempt = claim.attempt();
    MetaCommentReplyPort port = ports.get(claim.platform());
    if (port == null) {
      reply.markFailed("No provider reply adapter configured for " + claim.platform(), false);
      attempt.setStatus(MetaCommentDeliveryAttempt.Status.FAILED);
      attempt.setErrorMessage(reply.getErrorMessage());
      attempt.setCompletedAt(Instant.now());
      complete(claim);
      return reply;
    }

    try {
      MetaCommentReplyPort.SendResult result = port.sendApprovedReply(reply);
      if (result == null || !result.success()) {
        String message = result == null ? "Provider returned no reply result" : result.message();
        reply.markFailed(message, true);
        attempt.setStatus(MetaCommentDeliveryAttempt.Status.RETRYABLE);
        attempt.setErrorMessage(message);
      } else {
        reply.markSent(result.providerReplyId());
        attempt.setStatus(MetaCommentDeliveryAttempt.Status.SENT);
        attempt.setProviderRequestId(result.providerReplyId());
      }
    } catch (Exception error) {
      String message =
          error.getMessage() == null ? error.getClass().getSimpleName() : error.getMessage();
      if (isAmbiguous(error)) {
        reply.markAmbiguous(message);
        attempt.setStatus(MetaCommentDeliveryAttempt.Status.RECONCILIATION_REQUIRED);
      } else {
        reply.markFailed(message, true);
        attempt.setStatus(MetaCommentDeliveryAttempt.Status.RETRYABLE);
      }
      attempt.setErrorMessage(message);
    }
    attempt.setCompletedAt(Instant.now());
    complete(claim);
    return reply;
  }

  private DeliveryClaim claim(UUID replyId) {
    if (transactionTemplate == null) {
      return claimInTransaction(replyId);
    }
    return transactionTemplate.execute(status -> claimInTransaction(replyId));
  }

  private DeliveryClaim claimInTransaction(UUID replyId) {
    MetaCommentReply reply = findReply(replyId);
    if (reply.getStatus() == MetaCommentReply.Status.SENT
        || reply.getStatus() == MetaCommentReply.Status.RECONCILIATION_REQUIRED) {
      return DeliveryClaim.noProviderCall(reply);
    }
    if (reply.getStatus() != MetaCommentReply.Status.APPROVED) {
      throw new IllegalStateException("Reply requires human approval before provider send");
    }
    PlatformType platform = reply.getComment().getThread().getPlatform();
    guard.assertAllowed(platform);

    MetaCommentDeliveryAttempt latest =
        attemptRepository.findTopByReplyIdOrderByAttemptNumberDesc(replyId).orElse(null);
    if (latest != null
        && (latest.getStatus() == MetaCommentDeliveryAttempt.Status.SUBMITTING
            || latest.getStatus() == MetaCommentDeliveryAttempt.Status.RECONCILIATION_REQUIRED)) {
      String reconciliationMessage = "A previous provider attempt requires reconciliation";
      latest.setStatus(MetaCommentDeliveryAttempt.Status.RECONCILIATION_REQUIRED);
      latest.setErrorMessage(reconciliationMessage);
      latest.setCompletedAt(Instant.now());
      attemptRepository.save(latest);
      reply.markAmbiguous(reconciliationMessage);
      replyRepository.save(reply);
      return DeliveryClaim.noProviderCall(reply);
    }

    int attemptNumber = latest == null ? 1 : latest.getAttemptNumber() + 1;
    MetaCommentDeliveryAttempt attempt =
        MetaCommentDeliveryAttempt.builder()
            .reply(reply)
            .attemptNumber(attemptNumber)
            .status(MetaCommentDeliveryAttempt.Status.SUBMITTING)
            .build();
    attemptRepository.save(attempt);
    return new DeliveryClaim(reply, platform, attempt, true);
  }

  private void complete(DeliveryClaim claim) {
    if (transactionTemplate == null) {
      completeInTransaction(claim);
      return;
    }
    transactionTemplate.executeWithoutResult(status -> completeInTransaction(claim));
  }

  private void completeInTransaction(DeliveryClaim claim) {
    attemptRepository.save(claim.attempt());
    replyRepository.save(claim.reply());
  }

  private boolean isAmbiguous(Exception error) {
    Throwable current = error;
    while (current != null) {
      if (current instanceof ResourceAccessException) {
        return true;
      }
      if (current instanceof RestClientResponseException response
          && response.getStatusCode().value() >= 500) {
        return true;
      }
      if (current instanceof SocketTimeoutException
          || current instanceof TimeoutException
          || current instanceof java.io.InterruptedIOException) {
        return true;
      }
      current = current.getCause();
    }
    return false;
  }

  private MetaCommentReply findReply(UUID replyId) {
    return replyRepository
        .findByIdForUpdate(replyId)
        .orElseThrow(() -> new IllegalArgumentException("Comment reply not found"));
  }

  private record DeliveryClaim(
      MetaCommentReply reply,
      PlatformType platform,
      MetaCommentDeliveryAttempt attempt,
      boolean providerCallRequired) {
    private static DeliveryClaim noProviderCall(MetaCommentReply reply) {
      return new DeliveryClaim(reply, null, null, false);
    }
  }
}
