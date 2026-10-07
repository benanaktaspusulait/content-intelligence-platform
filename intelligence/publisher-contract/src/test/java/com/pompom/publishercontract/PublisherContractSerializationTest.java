package com.pompom.publishercontract;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PublisherContractSerializationTest {
  private final ObjectMapper objectMapper = new ObjectMapper();
  private final Validator validator = Validation.buildDefaultValidatorFactory().getValidator();

  @Test
  void serializesAndRoundTripsCompleteCommandFieldSet() throws Exception {
    UUID publicationJobId = UUID.fromString("11111111-1111-1111-1111-111111111111");
    UUID publicationAttemptId = UUID.fromString("22222222-2222-2222-2222-222222222222");
    List<String> hashtags = new ArrayList<>(List.of("reels", "shorts"));
    Map<String, String> providerOptions = new HashMap<>(Map.of("privacy", "private"));

    PublishCommand command =
        new PublishCommand(
            publicationJobId,
            publicationAttemptId,
            "job-1-attempt-1",
            "account-42",
            "assets/video.mp4",
            "a".repeat(64),
            "A title",
            "A caption",
            hashtags,
            true,
            providerOptions);

    hashtags.add("mutated-after-construction");
    providerOptions.put("mutated", "after-construction");

    JsonNode json = objectMapper.readTree(objectMapper.writeValueAsString(command));

    assertThat(json.fieldNames())
        .toIterable()
        .containsExactlyInAnyOrder(
            "publicationJobId",
            "publicationAttemptId",
            "idempotencyKey",
            "platformAccountId",
            "assetReference",
            "assetSha256",
            "title",
            "caption",
            "hashtags",
            "isPrivate",
            "providerOptions");
    assertThat(json.get("publicationJobId").asText()).isEqualTo(publicationJobId.toString());
    assertThat(json.get("publicationAttemptId").asText())
        .isEqualTo(publicationAttemptId.toString());
    assertThat(json.get("idempotencyKey").asText()).isEqualTo("job-1-attempt-1");
    assertThat(json.get("platformAccountId").asText()).isEqualTo("account-42");
    assertThat(json.get("assetReference").asText()).isEqualTo("assets/video.mp4");
    assertThat(json.get("assetSha256").asText()).isEqualTo("a".repeat(64));
    assertThat(json.get("title").asText()).isEqualTo("A title");
    assertThat(json.get("caption").asText()).isEqualTo("A caption");
    assertThat(List.of(json.get("hashtags").get(0).asText(), json.get("hashtags").get(1).asText()))
        .containsExactly("reels", "shorts");
    assertThat(json.get("isPrivate").asBoolean()).isTrue();
    assertThat(json.get("providerOptions").get("privacy").asText()).isEqualTo("private");
    assertThat(json.has("accessToken")).isFalse();
    assertThat(json.has("refreshToken")).isFalse();
    assertThat(json.has("credentials")).isFalse();
    assertThat(json.has("token")).isFalse();

    assertThat(objectMapper.readValue(json.toString(), PublishCommand.class)).isEqualTo(command);
    assertThat(command.hashtags()).containsExactly("reels", "shorts");
    assertThat(command.providerOptions()).containsEntry("privacy", "private");
    assertThatThrownBy(() -> command.hashtags().add("not-allowed"))
        .isInstanceOf(UnsupportedOperationException.class);
    assertThatThrownBy(() -> command.providerOptions().put("not-allowed", "value"))
        .isInstanceOf(UnsupportedOperationException.class);
  }

  @Test
  void normalizesNullCollectionsAndValidatesRequiredCommandIdentity() {
    PublishCommand normalized =
        new PublishCommand(
            UUID.randomUUID(),
            UUID.randomUUID(),
            "idempotency-key",
            "account-id",
            "asset-reference",
            "a".repeat(64),
            null,
            null,
            null,
            false,
            null);

    assertThat(normalized.hashtags()).isEmpty();
    assertThat(normalized.providerOptions()).isEmpty();
    assertThat(validator.validate(normalized)).isEmpty();

    PublishCommand invalid =
        new PublishCommand(null, null, " ", " ", " ", null, null, null, null, false, null);

    assertThat(validator.validate(invalid))
        .extracting(violation -> violation.getPropertyPath().toString())
        .containsExactlyInAnyOrder(
            "publicationJobId",
            "publicationAttemptId",
            "idempotencyKey",
            "platformAccountId",
            "assetReference",
            "assetSha256");
  }

  @Test
  void validatesAssetSha256AsExactly64HexCharactersAtTheBoundary() {
    for (String invalidHash :
        List.of("a".repeat(63), "a".repeat(65), "g".repeat(64), "a".repeat(63) + "G")) {
      PublishCommand invalid = commandWithOptions(invalidHash, Map.of());

      assertThat(validator.validate(invalid))
          .as("invalid assetSha256: %s", invalidHash)
          .extracting(violation -> violation.getPropertyPath().toString())
          .contains("assetSha256");
    }

    assertThat(validator.validate(commandWithOptions("0123456789abcdef".repeat(4), Map.of())))
        .isEmpty();
  }

  @Test
  void acceptsOnlyDocumentedNonSecretProviderOptions() {
    Map<String, String> documentedOptions =
        Map.ofEntries(
            Map.entry("privacy", "private"),
            Map.entry("privacy_level", "SELF_ONLY"),
            Map.entry("privacy_status", "private"),
            Map.entry("category_id", "22"),
            Map.entry("default_language", "en"),
            Map.entry("made_for_kids", "false"),
            Map.entry("disable_duet", "false"),
            Map.entry("disable_comment", "false"),
            Map.entry("disable_stitch", "false"),
            Map.entry("duet_enabled", "false"),
            Map.entry("comment_enabled", "false"),
            Map.entry("stitch_enabled", "false"),
            Map.entry("video_cover_timestamp_ms", "1000"),
            Map.entry("tags", "shorts,reels"),
            Map.entry("targeting", "public"),
            Map.entry("published", "true"),
            Map.entry("scheduled_publish_time", "2026-10-07T12:00:00Z"),
            Map.entry("caption_entities", "[]"),
            Map.entry("location_id", "location-42"),
            Map.entry("share_to_feed", "true"));

    assertThat(commandWithOptions("a".repeat(64), documentedOptions).providerOptions())
        .containsExactlyInAnyOrderEntriesOf(documentedOptions);
  }

  @Test
  void rejectsUnknownAndCredentialLikeProviderOptionKeysIncludingBypasses() {
    for (String rejectedKey :
        List.of(
            "arbitrary",
            "provider_specific_setting",
            "api_key",
            "auth",
            "authorization",
            "client_secret",
            "access_token",
            "refresh-token",
            "mytokenconfig",
            "secret_value",
            "password")) {
      assertThatThrownBy(
              () ->
                  commandWithOptions(
                      "a".repeat(64), Map.of(rejectedKey, "must-not-cross-boundary")))
          .as("rejected provider option key: %s", rejectedKey)
          .isInstanceOf(IllegalArgumentException.class);
    }
  }

  @Test
  void serializesAndRoundTripsCompleteResultFieldSet() throws Exception {
    PublishResult result =
        new PublishResult(
            PublishStatus.FAILED,
            "provider-post-1",
            "provider-video-1",
            "https://provider.example/post-1",
            "provider-request-1",
            PublishErrorClass.PROVIDER_REJECTED.wireValue(),
            "Provider rejected the publication",
            false);

    JsonNode json = objectMapper.readTree(objectMapper.writeValueAsString(result));

    assertThat(json.fieldNames())
        .toIterable()
        .containsExactlyInAnyOrder(
            "status",
            "providerPostId",
            "providerVideoId",
            "permalink",
            "providerRequestId",
            "errorClass",
            "message",
            "reconciliationRequired");
    assertThat(json.get("status").asText()).isEqualTo("failed");
    assertThat(json.get("providerPostId").asText()).isEqualTo("provider-post-1");
    assertThat(json.get("providerVideoId").asText()).isEqualTo("provider-video-1");
    assertThat(json.get("permalink").asText()).isEqualTo("https://provider.example/post-1");
    assertThat(json.get("providerRequestId").asText()).isEqualTo("provider-request-1");
    assertThat(json.get("errorClass").asText()).isEqualTo("provider_rejected");
    assertThat(json.get("message").asText()).isEqualTo("Provider rejected the publication");
    assertThat(json.get("reconciliationRequired").asBoolean()).isFalse();
    assertThat(objectMapper.readValue(json.toString(), PublishResult.class)).isEqualTo(result);
  }

  @Test
  void roundTripsEveryPublishLifecycleStatusWithCoherentErrorAndReconciliationFields()
      throws Exception {
    for (PublishStatus status : PublishStatus.values()) {
      PublishResult result = validResultFor(status);
      String json = objectMapper.writeValueAsString(result);

      assertThat(objectMapper.readValue(json, PublishResult.class)).isEqualTo(result);
    }
  }

  @Test
  void rejectsContradictoryPublishLifecycleCombinations() {
    assertInvalidLifecycle(PublishStatus.ACCEPTED, PublishErrorClass.TRANSIENT.wireValue(), false);
    assertInvalidLifecycle(PublishStatus.ACCEPTED, null, true);

    assertInvalidLifecycle(PublishStatus.COMPLETED, PublishErrorClass.TRANSIENT.wireValue(), false);
    assertInvalidLifecycle(PublishStatus.COMPLETED, null, true);

    assertInvalidLifecycle(PublishStatus.FAILED, null, false);
    assertInvalidLifecycle(
        PublishStatus.FAILED, PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(), false);
    assertInvalidLifecycle(PublishStatus.FAILED, PublishErrorClass.TRANSIENT.wireValue(), true);

    assertInvalidLifecycle(PublishStatus.RECONCILIATION_REQUIRED, null, true);
    assertInvalidLifecycle(
        PublishStatus.RECONCILIATION_REQUIRED, PublishErrorClass.TRANSIENT.wireValue(), false);
    assertInvalidLifecycle(
        PublishStatus.RECONCILIATION_REQUIRED,
        PublishErrorClass.PROVIDER_REJECTED.wireValue(),
        true);
    assertInvalidLifecycle(
        PublishStatus.RECONCILIATION_REQUIRED,
        PublishErrorClass.RECONCILIATION_REQUIRED.wireValue(),
        false);
  }

  @Test
  void rejectsUnnormalizedErrorClassValues() {
    assertThatThrownBy(
            () ->
                new PublishResult(
                    PublishStatus.FAILED,
                    null,
                    null,
                    null,
                    null,
                    "provider_specific_raw_error",
                    "message",
                    false))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("error class");
  }

  @Test
  void serializesAndDeserializesEveryEnumWireValue() throws Exception {
    for (PublishStatus status : PublishStatus.values()) {
      assertThat(objectMapper.writeValueAsString(status)).isEqualTo('"' + status.wireValue() + '"');
      assertThat(objectMapper.readValue('"' + status.wireValue() + '"', PublishStatus.class))
          .isEqualTo(status);
    }
    for (PublishErrorClass errorClass : PublishErrorClass.values()) {
      assertThat(objectMapper.writeValueAsString(errorClass))
          .isEqualTo('"' + errorClass.wireValue() + '"');
      assertThat(
              objectMapper.readValue('"' + errorClass.wireValue() + '"', PublishErrorClass.class))
          .isEqualTo(errorClass);
    }
    for (PublisherCapability capability : PublisherCapability.values()) {
      assertThat(objectMapper.writeValueAsString(capability))
          .isEqualTo('"' + capability.wireValue() + '"');
      assertThat(
              objectMapper.readValue('"' + capability.wireValue() + '"', PublisherCapability.class))
          .isEqualTo(capability);
    }
  }

  @Test
  void rejectsUnknownEnumWireValuesAtJsonBoundary() {
    assertUnknownEnum(PublishStatus.class);
    assertUnknownEnum(PublishErrorClass.class);
    assertUnknownEnum(PublisherCapability.class);
  }

  private void assertUnknownEnum(Class<?> enumType) {
    assertThatThrownBy(() -> objectMapper.readValue("\"not-a-wire-value\"", enumType))
        .isInstanceOf(JsonProcessingException.class);
  }

  private void assertInvalidLifecycle(
      PublishStatus status, String errorClass, boolean reconciliationRequired) {
    assertThatThrownBy(
            () ->
                new PublishResult(
                    status,
                    null,
                    null,
                    null,
                    null,
                    errorClass,
                    "lifecycle test",
                    reconciliationRequired))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("lifecycle");
  }

  private PublishResult validResultFor(PublishStatus status) {
    return switch (status) {
      case ACCEPTED ->
          new PublishResult(
              status, null, null, null, "provider-request-accepted", null, "Accepted", false);
      case COMPLETED ->
          new PublishResult(
              status,
              "provider-post-completed",
              "provider-video-completed",
              "https://provider.example/completed",
              "provider-request-completed",
              null,
              "Completed",
              false);
      case FAILED ->
          new PublishResult(
              status,
              null,
              null,
              null,
              "provider-request-failed",
              PublishErrorClass.PROVIDER_REJECTED.wireValue(),
              "Failed",
              false);
      case RECONCILIATION_REQUIRED ->
          new PublishResult(
              status,
              null,
              null,
              null,
              "provider-request-uncertain",
              PublishErrorClass.TRANSIENT.wireValue(),
              "Reconciliation required",
              true);
    };
  }

  private PublishCommand commandWithOptions(String assetSha256, Map<String, String> options) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        "idempotency-key",
        "account-id",
        "asset-reference",
        assetSha256,
        "title",
        "caption",
        List.of("shorts"),
        false,
        options);
  }
}
