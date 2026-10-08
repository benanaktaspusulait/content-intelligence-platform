package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.pompom.publishercontract.PublishCommand;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class PublisherRequestValidatorTest {

  private final PublisherRequestValidator validator = new PublisherRequestValidator();

  @Test
  void acceptsAnImmutableCommandAtSharedTitleAndCaptionBounds() {
    PublishCommand command =
        command(
            "idempotency-key",
            "t".repeat(PublisherRequestValidator.MAX_TITLE_LENGTH),
            "c".repeat(PublisherRequestValidator.MAX_CAPTION_LENGTH));

    assertThatCode(() -> validator.validate(command)).doesNotThrowAnyException();
  }

  @Test
  void rejectsMissingIdentityAssetReferenceOrAssetHash() {
    PublishCommand command =
        new PublishCommand(
            null, null, " ", " ", " ", "not-a-sha", null, null, null, false, Map.of());

    assertThatThrownBy(() -> validator.validate(command))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("publicationJobId")
        .hasMessageContaining("assetSha256");
  }

  @Test
  void acceptsTwoThousandTwoHundredEmojiCodePointsAtTheCaptionBound() {
    assertThatCode(() -> validator.validate(command("emoji-caption", "title", "😀".repeat(2200))))
        .doesNotThrowAnyException();
  }

  @Test
  void rejectsTitleAndCaptionBeyondProviderNeutralStorageBounds() {
    assertThatThrownBy(
            () ->
                validator.validate(
                    command(
                        "key-title",
                        "t".repeat(PublisherRequestValidator.MAX_TITLE_LENGTH + 1),
                        "caption")))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("title");

    assertThatThrownBy(
            () ->
                validator.validate(
                    command(
                        "key-caption",
                        "title",
                        "c".repeat(PublisherRequestValidator.MAX_CAPTION_LENGTH + 1))))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("caption");
  }

  @Test
  void delegatesProviderOptionAllowlistToThePublisherContract() {
    assertThatThrownBy(
            () ->
                validator.validate(
                    new PublishCommand(
                        UUID.randomUUID(),
                        UUID.randomUUID(),
                        "idempotency-key",
                        "account-id",
                        "asset-reference",
                        "a".repeat(64),
                        "title",
                        "caption",
                        List.of(),
                        false,
                        Map.of("access_token", "must-not-cross-boundary"))))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("providerOptions");
  }

  @Test
  void rejectsCommandIdempotencyKeysThatExceedThePersistedColumnBound() {
    assertThatThrownBy(
            () ->
                validator.validate(
                    command(
                        "k".repeat(PublisherRequestValidator.MAX_KEY_LENGTH + 1),
                        "title",
                        "caption")))
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("idempotencyKey");
  }

  private PublishCommand command(String idempotencyKey, String title, String caption) {
    return new PublishCommand(
        UUID.randomUUID(),
        UUID.randomUUID(),
        idempotencyKey,
        "account-id",
        "immutable-asset-reference",
        "a".repeat(64),
        title,
        caption,
        List.of("shorts"),
        false,
        Map.of("privacy", "private"));
  }
}
