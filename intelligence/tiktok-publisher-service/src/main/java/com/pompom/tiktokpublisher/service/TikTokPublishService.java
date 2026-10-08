package com.pompom.tiktokpublisher.service;

import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishercontract.PublisherCapability;
import com.pompom.publishersupport.ProviderOperationRecord;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
import com.pompom.tiktokpublisher.client.TikTokContentClient;
import com.pompom.tiktokpublisher.security.TikTokWriteCapabilityGuard;
import jakarta.validation.constraints.AssertTrue;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Optional;
import java.util.UUID;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

/** Control-plane-facing TikTok operation service with capability-scoped idempotency. */
@Service
public class TikTokPublishService {

  private static final String SAFE_IDENTIFIER_PATTERN = "^[A-Za-z0-9._~-]{1,200}$";
  private static final String SAFE_REQUEST_ID_PATTERN = "^[A-Za-z0-9._~:-]{1,200}$";

  private final ProviderOperationRepository operationRepository;
  private final PublisherRequestValidator requestValidator;
  private final TikTokContentClient client;
  private final TikTokWriteCapabilityGuard admission;

  @Autowired
  public TikTokPublishService(
      ProviderOperationRepository operationRepository,
      PublisherRequestValidator requestValidator,
      TikTokContentClient client,
      TikTokWriteCapabilityGuard admission) {
    this.operationRepository = operationRepository;
    this.requestValidator = requestValidator;
    this.client = client;
    this.admission = admission;
  }

  public PublishResult publish(PublishCommand command, String capability) {
    String normalizedCapability = admission.normalizeCapability(capability);
    PublishCommand normalizedCommand = normalizeCommand(command);
    requestValidator.validate(normalizedCommand);
    admission.assertProviderConfigured(
        normalizedCapability, normalizedCommand.platformAccountId(), true);

    PublisherCapability publisherCapability = PublisherCapability.of(normalizedCapability);
    PublishCommand claimedCommand = bindCapability(normalizedCommand, normalizedCapability);
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
              null, null, "TikTok provider operation failed; reconciliation is required");
    }
    if (result == null) {
      result =
          reconciliationRequired(
              null, null, "TikTok provider returned no result; reconciliation is required");
    }
    operationRepository.recordResult(publisherCapability, claimedCommand.idempotencyKey(), result);
    return result;
  }

  /** Reconciles one known TikTok publish ID through status fetch only. */
  public PublishResult reconcile(ReconcileCommand command) {
    validateReconcileCommand(command);
    String capability = admission.normalizeCapability(command.capability());
    PublisherCapability publisherCapability = PublisherCapability.of(capability);
    admission.assertProviderConfigured(capability, command.platformAccountId(), false);

    String publishId = firstNonBlank(command.providerPostId(), command.providerVideoId());
    Optional<ProviderOperationRecord> operation =
        operationRepository.findByPublicationAttemptId(
            publisherCapability, command.publicationAttemptId());

    PublishResult result;
    try {
      result = client.reconcile(publishId);
      if (result == null) {
        result =
            reconciliationRequired(
                publishId,
                command.providerRequestId(),
                "TikTok provider identity could not be reconciled");
      }
    } catch (RuntimeException failure) {
      result =
          reconciliationRequired(
              publishId,
              command.providerRequestId(),
              "TikTok provider identity could not be reconciled");
    }

    if (result.status() == PublishStatus.COMPLETED && !matchesRequestedIdentity(command, result)) {
      result =
          reconciliationRequired(
              publishId,
              result.providerRequestId(),
              "TikTok publication evidence did not match the requested identity");
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
        || record.getStatus() == PublishStatus.FAILED) {
      return;
    }
    operationRepository.recordResult(capability, record.getCommandIdempotencyKey(), result);
  }

  private boolean matchesRequestedIdentity(ReconcileCommand command, PublishResult result) {
    return matches(command.providerPostId(), result.providerPostId())
        || matches(command.providerVideoId(), result.providerPostId())
        || matches(command.providerPostId(), result.providerVideoId())
        || matches(command.providerVideoId(), result.providerVideoId());
  }

  private boolean matches(String requested, String returned) {
    return requested != null && !requested.isBlank() && requested.equals(returned);
  }

  private PublishCommand normalizeCommand(PublishCommand command) {
    if (command == null) {
      throw new IllegalArgumentException("publish command is required");
    }
    String caption = TikTokContentClient.truncateCaption(command.caption());
    if (java.util.Objects.equals(caption, command.caption())) {
      return command;
    }
    return new PublishCommand(
        command.publicationJobId(),
        command.publicationAttemptId(),
        command.idempotencyKey(),
        command.platformAccountId(),
        command.assetReference(),
        command.assetSha256(),
        command.title(),
        caption,
        command.hashtags(),
        command.isPrivate(),
        command.providerOptions());
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

  private void validateReconcileCommand(ReconcileCommand command) {
    if (command == null
        || command.publicationAttemptId() == null
        || command.platformAccountId() == null
        || command.platformAccountId().isBlank()) {
      throw new IllegalArgumentException("reconciliation command is invalid");
    }
    admission.normalizeCapability(command.capability());
    validateIdentifier("platformAccountId", command.platformAccountId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier("providerPostId", command.providerPostId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier(
        "providerVideoId", command.providerVideoId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier(
        "providerRequestId", command.providerRequestId(), SAFE_REQUEST_ID_PATTERN);
    if (firstNonBlank(command.providerPostId(), command.providerVideoId()) == null) {
      throw new IllegalArgumentException("provider identity is required");
    }
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

  private PublishResult reconciliationRequired(
      String providerPostId, String providerRequestId, String message) {
    return new PublishResult(
        PublishStatus.RECONCILIATION_REQUIRED,
        providerPostId,
        null,
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
      @NotBlank @Pattern(regexp = "^(?i:tiktok_video)$") String capability,
      @NotBlank @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String platformAccountId,
      @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String providerPostId,
      @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String providerVideoId,
      @Size(max = 200) @Pattern(regexp = SAFE_REQUEST_ID_PATTERN) String providerRequestId) {

    @AssertTrue(message = "provider identity is required") public boolean hasProviderIdentity() {
      return (providerPostId != null && !providerPostId.isBlank())
          || (providerVideoId != null && !providerVideoId.isBlank());
    }
  }

  public static class IdempotencyConflictException extends IllegalArgumentException {
    public IdempotencyConflictException() {
      super("idempotency key is already bound to a different publish command");
    }
  }
}
