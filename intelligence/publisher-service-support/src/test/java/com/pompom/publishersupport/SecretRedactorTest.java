package com.pompom.publishersupport;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.Map;
import org.junit.jupiter.api.Test;

class SecretRedactorTest {

  private final SecretRedactor redactor = new SecretRedactor();

  @Test
  void redactsKnownSecretsBearerValuesAndCredentialAssignments() {
    String text =
        "Authorization: Bearer bearer-secret access_token=access-secret "
            + "client_secret=client-secret";

    String redacted = redactor.redact(text, "bearer-secret", "access-secret", "client-secret");

    assertThat(redacted)
        .doesNotContain("bearer-secret", "access-secret", "client-secret")
        .contains("Bearer [REDACTED]")
        .contains("access_token=[REDACTED]")
        .contains("client_secret=[REDACTED]");
  }

  @Test
  void redactsSensitiveMapFieldsAndBoundsControlCharacters() {
    String longMessage = "safe\nmessage\t" + "x".repeat(SecretRedactor.MAX_LENGTH + 20);

    Map<String, String> redacted =
        redactor.redactFields(
            Map.of(
                "access_token", "token-value",
                "message", longMessage,
                "status", "accepted"));

    assertThat(redacted.get("access_token")).isEqualTo("[REDACTED]");
    assertThat(redacted.get("message"))
        .doesNotContain("\n", "\t")
        .hasSize(SecretRedactor.MAX_LENGTH);
    assertThat(redacted.get("status")).isEqualTo("accepted");
  }

  @Test
  void leavesNullAndBlankMessagesWithoutInventingProviderContent() {
    assertThat(redactor.redact(null)).isNull();
    assertThat(redactor.redact("   ")).isEqualTo("   ");
  }

  @Test
  void redactsDigestParametersAfterTheFirstDelimiter() {
    String redacted =
        redactor.redact("Authorization: Digest username=user, response=digest-secret-value");

    assertThat(redacted).doesNotContain("digest-secret-value").contains("Digest [REDACTED]");
  }
}
