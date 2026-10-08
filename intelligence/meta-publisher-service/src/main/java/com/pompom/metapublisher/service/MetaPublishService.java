package com.pompom.metapublisher.service;

import com.pompom.metapublisher.facebook.FacebookReelsClient;
import com.pompom.metapublisher.instagram.InstagramReelsClient;
import com.pompom.publishercontract.PublishCommand;
import com.pompom.publishercontract.PublishErrorClass;
import com.pompom.publishercontract.PublishResult;
import com.pompom.publishercontract.PublishStatus;
import com.pompom.publishersupport.ProviderOperationRepository;
import com.pompom.publishersupport.PublisherRequestValidator;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class MetaPublishService {

  private final ProviderOperationRepository operationRepository;
  private final PublisherRequestValidator requestValidator;
  private final FacebookReelsClient facebookClient;
  private final InstagramReelsClient instagramClient;

  public MetaPublishService(
      ProviderOperationRepository operationRepository,
      PublisherRequestValidator requestValidator,
      FacebookReelsClient facebookClient,
      InstagramReelsClient instagramClient) {
    this.operationRepository = operationRepository;
    this.requestValidator = requestValidator;
    this.facebookClient = facebookClient;
    this.instagramClient = instagramClient;
  }

  public PublishResult publish(PublishCommand command, String capability) {
    String normalizedCapability = normalizeCapability(capability);
    PublishCommand normalizedCommand = normalizeCommand(command, normalizedCapability);
    PublishCommand claimedCommand = bindCapability(normalizedCommand, normalizedCapability);
    requestValidator.validate(claimedCommand);

    ProviderOperationRepository.OperationClaim claim;
    try {
      claim = operationRepository.claim(claimedCommand);
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
    operationRepository.recordResult(claimedCommand.idempotencyKey(), result);
    return result;
  }

  public PublishResult reconcile(ReconcileCommand command) {
    if (command == null
        || command.publicationAttemptId() == null
        || command.platformAccountId() == null
        || command.platformAccountId().isBlank()) {
      throw new IllegalArgumentException("reconciliation command is invalid");
    }
    String capability = normalizeCapability(command.capability());
    String providerIdentity = firstNonBlank(command.providerVideoId(), command.providerPostId());
    if (providerIdentity == null) {
      throw new IllegalArgumentException("provider identity is required");
    }
    try {
      PublishResult result =
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
      return result == null
          ? reconciliationRequired(
              command.providerPostId(),
              command.providerVideoId(),
              command.providerRequestId(),
              "provider identity could not be reconciled")
          : result;
    } catch (RuntimeException failure) {
      return reconciliationRequired(
          command.providerPostId(),
          command.providerVideoId(),
          command.providerRequestId(),
          "provider identity could not be reconciled");
    }
  }

  private PublishCommand normalizeCommand(PublishCommand command, String capability) {
    if (command == null) {
      throw new IllegalArgumentException("publish command is required");
    }
    if (!"instagram_reels".equals(capability)
        || command.caption() == null
        || command.caption().length() <= InstagramReelsClient.CAPTION_LIMIT) {
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
    String normalized = capability == null ? "" : capability.trim().toLowerCase(Locale.ROOT);
    if (!"facebook_reels".equals(normalized) && !"instagram_reels".equals(normalized)) {
      throw new IllegalArgumentException("unsupported publisher capability");
    }
    return normalized;
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
      @NotBlank String capability,
      @NotBlank String platformAccountId,
      String providerPostId,
      String providerVideoId,
      String providerRequestId) {
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
