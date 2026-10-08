package com.pompom.metapublisher.service;

import com.pompom.metapublisher.facebook.FacebookReelsClient;
import com.pompom.metapublisher.instagram.InstagramReelsClient;
import com.pompom.metapublisher.security.MetaWriteCapabilityGuard;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishercontract.PublisherCapability;
import com.pompom.publishersupport.ProviderOperationRecord;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
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

@Service
public class MetaPublishService {

  private static final String SAFE_IDENTIFIER_PATTERN = "^[A-Za-z0-9._~-]{1,200}$";
  private static final String SAFE_REQUEST_ID_PATTERN = "^[A-Za-z0-9._~:-]{1,200}$";

  private final ProviderOperationRepository operationRepository;
  private final PublisherRequestValidator requestValidator;
  private final FacebookReelsClient facebookClient;
  private final InstagramReelsClient instagramClient;
  private final MetaWriteCapabilityGuard admission;

  @Autowired
  public MetaPublishService(
      ProviderOperationRepository operationRepository,
      PublisherRequestValidator requestValidator,
      FacebookReelsClient facebookClient,
      InstagramReelsClient instagramClient,
      MetaWriteCapabilityGuard admission) {
    this.operationRepository = operationRepository;
    this.requestValidator = requestValidator;
    this.facebookClient = facebookClient;
    this.instagramClient = instagramClient;
    this.admission = admission;
  }

  public PublishResult publish(PublishCommand command, String capability) {
    String normalizedCapability = normalizeCapability(capability);
    PublisherCapability publisherCapability = PublisherCapability.of(normalizedCapability);
    PublishCommand normalizedCommand = normalizeCommand(command, normalizedCapability);
    requestValidator.validate(normalizedCommand);
    admission.assertProviderConfigured(
        normalizedCapability, normalizedCommand.platformAccountId(), true);

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
      result =
          switch (normalizedCapability) {
            case "facebook_reels" -> facebookClient.publish(claimedCommand);
            case "instagram_reels" -> instagramClient.publish(claimedCommand);
            default -> throw new IllegalArgumentException("unsupported publisher capability");
          };
    } catch (RuntimeException failure) {
      result =
          new PublishResult(
              PublishStatus.RECONCILIATION_REQUIRED,
              null,
              null,
              null,
              null,
              PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
              "Meta provider operation failed; reconciliation is required",
              true);
    }
    if (result == null) {
      result =
          new PublishResult(
              PublishStatus.RECONCILIATION_REQUIRED,
              null,
              null,
              null,
              null,
              PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
              "Meta provider returned no result; reconciliation is required",
              true);
    }
    operationRepository.recordResult(publisherCapability, claimedCommand.idempotencyKey(), result);
    return result;
  }

  public PublishResult reconcile(ReconcileCommand command) {
    validateReconcileCommand(command);
    String capability = normalizeCapability(command.capability());
    PublisherCapability publisherCapability = PublisherCapability.of(capability);
    admission.assertProviderConfigured(capability, command.platformAccountId(), false);

    Optional<ProviderOperationRecord> operation =
        operationRepository.findByPublicationAttemptId(
            publisherCapability, command.publicationAttemptId());
    PublishResult result;
    try {
      result =
          switch (capability) {
            case "facebook_reels" ->
                facebookClient.reconcile(
                    command.platformAccountId(),
                    command.providerPostId(),
                    command.providerVideoId());
            case "instagram_reels" ->
                instagramClient.reconcile(
                    command.platformAccountId(),
                    command.providerPostId(),
                    command.providerVideoId());
            default -> throw new IllegalArgumentException("unsupported publisher capability");
          };
      if (result == null) {
        result =
            reconciliationRequired(
                command.providerPostId(),
                command.providerVideoId(),
                command.providerRequestId(),
                "provider identity could not be reconciled");
      }
    } catch (RuntimeException failure) {
      result =
          reconciliationRequired(
              command.providerPostId(),
              command.providerVideoId(),
              command.providerRequestId(),
              "provider identity could not be reconciled");
    }

    if (result.status() == PublishStatus.COMPLETED && !matchesRequestedIdentity(command, result)) {
      result =
          reconciliationRequired(
              command.providerPostId(),
              command.providerVideoId(),
              result.providerRequestId(),
              "provider publication evidence did not match the requested identity");
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
        || matches(command.providerVideoId(), result.providerVideoId());
  }

  private boolean matches(String requested, String returned) {
    return requested != null && !requested.isBlank() && requested.equals(returned);
  }

  private PublishCommand normalizeCommand(PublishCommand command, String capability) {
    if (command == null) {
      throw new IllegalArgumentException("publish command is required");
    }
    if (!"instagram_reels".equals(capability)
        || command.caption() == null
        || command.caption().codePointCount(0, command.caption().length())
            <= InstagramReelsClient.CAPTION_LIMIT) {
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
        InstagramReelsClient.truncateCaption(command.caption()),
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

  private String normalizeCapability(String capability) {
    return admission.normalizeCapability(capability);
  }

  private void validateReconcileCommand(ReconcileCommand command) {
    if (command == null
        || command.publicationAttemptId() == null
        || command.platformAccountId() == null
        || command.platformAccountId().isBlank()) {
      throw new IllegalArgumentException("reconciliation command is invalid");
    }
    normalizeCapability(command.capability());
    validateIdentifier("platformAccountId", command.platformAccountId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier("providerPostId", command.providerPostId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier(
        "providerVideoId", command.providerVideoId(), SAFE_IDENTIFIER_PATTERN);
    validateOptionalIdentifier(
        "providerRequestId", command.providerRequestId(), SAFE_REQUEST_ID_PATTERN);
    if (firstNonBlank(command.providerVideoId(), command.providerPostId()) == null) {
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
      String providerPostId, String providerVideoId, String providerRequestId, String message) {
    return new PublishResult(
        PublishStatus.RECONCILIATION_REQUIRED,
        providerPostId,
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
      @NotBlank @Pattern(regexp = "^(?i:facebook_reels|instagram_reels)$") String capability,
      @NotBlank @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String platformAccountId,
      @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String providerPostId,
      @Size(max = 200) @Pattern(regexp = SAFE_IDENTIFIER_PATTERN) String providerVideoId,
      @Size(max = 200) @Pattern(regexp = SAFE_REQUEST_ID_PATTERN) String providerRequestId) {
    @jakarta.validation.constraints.AssertTrue(message = "provider identity is required") public boolean hasProviderIdentity() {
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
