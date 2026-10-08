package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import com.pompom.publishercontract.PublishCommand;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PublisherCommandFingerprintTest {

  private static final UUID JOB_ID = UUID.fromString("11111111-1111-1111-1111-111111111111");
  private static final UUID ATTEMPT_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");

  @Test
  void changesWhenEachCommandIdentityFieldChanges() {
    PublishCommand base =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private"));

    assertDifferent(
        base,
        command(
            UUID.fromString("33333333-3333-3333-3333-333333333333"),
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            UUID.fromString("44444444-4444-4444-4444-444444444444"),
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "other-account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "other-asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        commandWithHash(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "b".repeat(64),
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "other-title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "other-caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("long-form"),
            false,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            true,
            Map.of("privacy", "private")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "public")));
    assertDifferent(
        base,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy_level", "private")));
  }

  @Test
  void distinguishesHashtagListBoundariesAndEmptyElements() {
    PublishCommand empty =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of(),
            false,
            Map.of());
    PublishCommand emptyElement =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of(""),
            false,
            Map.of());
    PublishCommand delimiterInsideElement =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("a\u001fb"),
            false,
            Map.of());
    PublishCommand separateElements =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("a", "b"),
            false,
            Map.of());

    assertDifferent(empty, emptyElement);
    assertDifferent(delimiterInsideElement, separateElements);
  }

  @Test
  void canonicalizesProviderOptionMapOrderButBindsKeysAndValues() {
    Map<String, String> firstOrder = new LinkedHashMap<>();
    firstOrder.put("privacy", "private");
    firstOrder.put("category_id", "one");
    Map<String, String> secondOrder = new LinkedHashMap<>();
    secondOrder.put("category_id", "one");
    secondOrder.put("privacy", "private");

    PublishCommand first =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of(),
            false,
            firstOrder);
    PublishCommand second =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of(),
            false,
            secondOrder);

    assertThat(PublisherCommandFingerprint.sha256(first))
        .isEqualTo(PublisherCommandFingerprint.sha256(second));
    assertDifferent(
        first,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of(),
            false,
            Map.of("privacy", "public", "category_id", "one")));
    assertDifferent(
        first,
        command(
            JOB_ID,
            ATTEMPT_ID,
            "key",
            "account",
            "asset",
            "title",
            "caption",
            List.of(),
            false,
            Map.of("privacy_level", "private", "category_id", "one")));
  }

  @Test
  void excludesTheLookupIdempotencyKeyFromTheCommandProjection() {
    PublishCommand first =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "first-key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private"));
    PublishCommand second =
        command(
            JOB_ID,
            ATTEMPT_ID,
            "second-key",
            "account",
            "asset",
            "title",
            "caption",
            List.of("shorts"),
            false,
            Map.of("privacy", "private"));

    assertThat(PublisherCommandFingerprint.sha256(first))
        .isEqualTo(PublisherCommandFingerprint.sha256(second));
  }

  private void assertDifferent(PublishCommand first, PublishCommand second) {
    assertThat(PublisherCommandFingerprint.sha256(first))
        .as("fingerprints must differ for distinct command projections")
        .isNotEqualTo(PublisherCommandFingerprint.sha256(second));
  }

  private PublishCommand command(
      UUID jobId,
      UUID attemptId,
      String idempotencyKey,
      String account,
      String asset,
      String title,
      String caption,
      List<String> hashtags,
      boolean isPrivate,
      Map<String, String> providerOptions) {
    return commandWithHash(
        jobId,
        attemptId,
        idempotencyKey,
        account,
        asset,
        "a".repeat(64),
        title,
        caption,
        hashtags,
        isPrivate,
        providerOptions);
  }

  private PublishCommand commandWithHash(
      UUID jobId,
      UUID attemptId,
      String idempotencyKey,
      String account,
      String asset,
      String assetSha256,
      String title,
      String caption,
      List<String> hashtags,
      boolean isPrivate,
      Map<String, String> providerOptions) {
    return new PublishCommand(
        jobId,
        attemptId,
        idempotencyKey,
        account,
        asset,
        assetSha256,
        title,
        caption,
        hashtags,
        isPrivate,
        providerOptions);
  }
}
