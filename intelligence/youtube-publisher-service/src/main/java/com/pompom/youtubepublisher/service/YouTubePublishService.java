package com.pompom.youtubepublisher.service;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishercontract.PublisherCapability;
import com.pompom.publishersupport.ProviderOperationRecord;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
import com.pompom.youtubepublisher.client.YouTubeDataClient;
import com.pompom.youtubepublisher.security.YouTubeWriteCapabilityGuard;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Duration;
import java.util.HexFormat;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/** Control-plane-facing YouTube operation service with capability-scoped idempotency. */
@Service
public class YouTubePublishService {

  private static final String SAFE_IDENTIFIER_PATTERN = "^[A-Za-z0-9._~-]{1,200}$";
  private static final String SAFE_REQUEST_ID_PATTERN = "^[A-Za-z0-9._~:-]{1,200}$";
  private static final Duration DEFAULT_IN_FLIGHT_CLAIM_STALE_AFTER = Duration.ofMinutes(15);

  private final ProviderOperationRepository operationRepository;
  private final PublisherRequestValidator requestValidator;
  private final YouTubeDataClient client;
  private final YouTubeWriteCapabilityGuard admission;
  private final Clock clock;
  private final Duration inFlightClaimStaleAfter;

  @Autowired
  public YouTubePublishService(
      ProviderOperationRepository operationRepository,
      PublisherRequestValidator requestValidator,
      YouTubeDataClient client,
      YouTubeWriteCapabilityGuard admission) {
    this(
        operationRepository,
        requestValidator,
        client,
        admission,
        Clock.systemUTC(),
        DEFAULT_IN_FLIGHT_CLAIM_STALE_AFTER);
  }

  public YouTubePublishService(
      ProviderOperationRepository operationRepository,
      PublisherRequestValidator requestValidator,
      YouTubeDataClient client,
      YouTubeWriteCapabilityGuard admission,
      Clock clock,
      Duration inFlightClaimStaleAfter) {
    this.operationRepository = operationRepository;
    this.requestValidator = requestValidator;
    this.client = client;
    this.admission = admission;
    this.clock = Objects.requireNonNull(clock, "clock");
    if (inFlightClaimStaleAfter == null
        || inFlightClaimStaleAfter.isZero()
        || inFlightClaimStaleAfter.isNegative()) {
      throw new IllegalArgumentException("in-flight claim stale threshold must be positive");
    }
    this.inFlightClaimStaleAfter = inFlightClaimStaleAfter;
  }

  public PublishResult publish(PublishCommand command, String capability) {
    String normalizedCapability = admission.normalizeCapability(capability);
    if (command == null) {
      throw new IllegalArgumentException("publish command is required");
    }
    requestValidator.validate(command);
    admission.assertProviderConfigured(normalizedCapability, command.platformAccountId(), true);

    PublisherCapability publisherCapability = PublisherCapability.of(normalizedCapability);
    PublishCommand claimedCommand = bindCapability(command, normalizedCapability);
    requestValidator.validate(claimedCommand);

    ProviderOperationRepository.OperationClaim claim;
    try {
      claim = operationRepository.claim(claimedCommand, publisherCapability);
    } catch (IllegalArgumentException failure) {
      if (failure.getMessage() != null
          && failure.getMessage().contains("idempotency key is already bound")) {
        throw new IdempotencyConflictException();
      }
      throw failure;
    }

    Optional<PublishResult> existing = claim.existingResult();
    if (existing.isPresent()) {
      return existing.orElseThrow();
    }
    if (!claim.newOperation()) {
      if (claim.isStale(clock.instant(), inFlightClaimStaleAfter)) {
        PublishResult stale =
            reconciliationRequired(
                null, null, "YouTube publish operation claim is stale; reconciliation is required");
        operationRepository.recordResult(
            publisherCapability, claimedCommand.idempotencyKey(), stale);
        return stale;
      }
      return new PublishResult(
          PublishStatus.ACCEPTED,
          null,
          null,
          null,
          null,
          null,
          "publish operation is in flight",
          false);
    }

    PublishResult result;
    try {
      result = client.publish(claimedCommand);
    } catch (RuntimeException failure) {
      result =
          reconciliationRequired(
              null, null, "YouTube provider operation failed; reconciliation is required");
    }
    if (result == null) {
      result =
          reconciliationRequired(
              null, null, "YouTube provider returned no result; reconciliation is required");
    }
    operationRepository.recordResult(publisherCapability, claimedCommand.idempotencyKey(), result);
    return result;
  }

  /** Reconciles one known YouTube video identity through a read-only status lookup. */
  public PublishResult reconcile(ReconcileCommand command) {
    validateReconcileCommand(command);
    String capability = admission.normalizeCapability(command.capability());
    PublisherCapability publisherCapability = PublisherCapability.of(capability);
    admission.assertProviderConfigured(capability, command.platformAccountId(), false);

    Optional<ProviderOperationRecord> operation =
        operationRepository.findByPublicationAttemptId(
            publisherCapability, command.publicationAttemptId());
    ProviderOperationRecord stored = operation.orElse(null);
    if (stored != null
        && stored.getProviderVideoId() != null
        && !stored.getProviderVideoId().equals(command.providerVideoId())) {
      return reconciliationRequired(
          stored.getProviderVideoId(),
          firstNonBlank(command.providerRequestId(), stored.getProviderRequestId()),
          "YouTube reconciliation identity did not match the stored provider identity");
    }

    PublishResult result;
    try {
      result = client.reconcile(command.providerVideoId());
      if (result == null) {
        result =
            reconciliationRequired(
                command.providerVideoId(),
                command.providerRequestId(),
                "YouTube provider identity could not be reconciled");
      }
    } catch (RuntimeException failure) {
      result =
          reconciliationRequired(
              command.providerVideoId(),
              command.providerRequestId(),
              "YouTube provider identity could not be reconciled");
    }

    if (!command.providerVideoId().equals(result.providerVideoId())
        && (result.status() == PublishStatus.COMPLETED || result.providerVideoId() != null)) {
      result =
          reconciliationRequired(
              command.providerVideoId(),
              firstNonBlank(result.providerRequestId(), command.providerRequestId()),
              "YouTube reconciliation result did not match the requested provider identity");
    }
    recordReconciliationResult(operation, publisherCapability, result);
    return result;
  }

  private void recordReconciliationResult(
      Optional<ProviderOperationRecord> operation,
      PublisherCapability capability,
      PublishResult result) {
    if (operation.isEmpty()) {
      return;
    }
    ProviderOperationRecord record = operation.orElseThrow();
    if (record.getStatus() == PublishStatus.COMPLETED
        || record.getStatus() == PublishStatus.FAILED
        || (record.getStatus() == PublishStatus.RECONCILIATION_REQUIRED
            && result.status() == PublishStatus.RECONCILIATION_REQUIRED)) {
      return;
    }
    operationRepository.recordResult(capability, record.getCommandIdempotencyKey(), result);
  }

  private void validateReconcileCommand(ReconcileCommand command) {
    if (command == null
        || command.publicationAttemptId() == null
        || command.platformAccountId() == null
        || command.platformAccountId().isBlank()) {
      throw new IllegalArgumentException("reconciliation command is invalid");
    }
    admission.normalizeCapability(command.capability());
    validateIdentifier("platformAccountId", command.platformAccountId(), SAFE_IDENTIFIER_PATTERN);
    validateIdentifier("providerVideoId", command.providerVideoId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier(
        "providerRequestId", command.providerRequestId(), SAFE_REQUEST_ID_PATTERN);
  }

  private void validateIdentifier(String fieldName, String value, String pattern) {
    if (value == null || !value.matches(pattern)) {
      throw new IllegalArgumentException(fieldName + " is invalid");
    }
  }

  private void validateOptionalIdentifier(String fieldName, String value, String pattern) {
    if (value != null && !value.isBlank()) {
      validateIdentifier(fieldName, value, pattern);
    }
  }

  private PublishCommand bindCapability(PublishCommand command, String capability) {
    String boundKey = capability + ":" + sha256(capability + "\n" + command.idempotencyKey());
    return new PublishCommand(
        command.publicationJobId(),
        command.publicationAttemptId(),
        boundKey,
        command.platformAccountId(),
        command.assetReference(),
        command.assetSha256(),
        command.title(),
        command.caption(),
        command.hashtags(),
        command.isPrivate(),
        command.providerOptions());
  }

  private String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable", exception);
    }
  }

  private PublishResult reconciliationRequired(
      String providerVideoId, String providerRequestId, String message) {
    return new PublishResult(
        PublishStatus.RECONCILIATION_REQUIRED,
        null,
        providerVideoId,
        null,
        providerRequestId,
        PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
        message,
        true);
  }

  private String firstNonBlank(String first, String second) {
    return first != null && !first.isBlank() ? first : second;
  }

  public record ReconcileCommand(
      @NotNull UUID publicationAttemptId,
      @NotBlank @Pattern(regexp = "^(?i:youtube_shorts)$") String capability,
      @NotBlank @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String platformAccountId,
      @NotBlank @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String providerVideoId,
      @Size(max = 200) @Pattern(regexp = SAFE_REQUEST_ID_PATTERN) String providerRequestId) {}

  public static class IdempotencyConflictException extends IllegalArgumentException {
    public IdempotencyConflictException() {
      super("idempotency key is already bound to a different publish command");
    }
  }
}
