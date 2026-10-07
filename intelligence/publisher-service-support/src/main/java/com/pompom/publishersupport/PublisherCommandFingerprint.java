package com.pompom.publishersupport;

import com.pompom.publishercontract.PublishCommand;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * Computes a stable, non-secret identity for a publish command independent of its idempotency key.
 */
public final class PublisherCommandFingerprint {

  private PublisherCommandFingerprint() {}

  public static String sha256(PublishCommand command) {
    Objects.requireNonNull(command, "command");
    String canonical =
        String.join(
            "\n",
            field(command.publicationJobId().toString()),
            field(command.publicationAttemptId().toString()),
            field(command.platformAccountId()),
            field(command.assetReference()),
            field(command.assetSha256()),
            field(command.title()),
            field(command.caption()),
            field(String.join("\u001f", command.hashtags())),
            field(Boolean.toString(command.isPrivate())),
            field(
                command.providerOptions().entrySet().stream()
                    .sorted(Map.Entry.comparingByKey())
                    .map(entry -> field(entry.getKey()) + field(entry.getValue()))
                    .collect(Collectors.joining("\u001e"))));
    try {
      return HexFormat.of()
          .formatHex(
              MessageDigest.getInstance("SHA-256")
                  .digest(canonical.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 is unavailable", exception);
    }
  }

  private static String field(String value) {
    return value == null ? "-1:" : value.length() + ":" + value;
  }
}
