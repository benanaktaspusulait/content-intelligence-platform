package com.pompomhills.intelligence.meta;

import java.util.regex.Pattern;

/** Redacts provider credential material and bounds provider-controlled error text. */
final class MetaErrorSanitizer {
  static final int MAX_LENGTH = 300;

  private static final Pattern BEARER_VALUE =
      Pattern.compile("(?i)\\bbearer\\s+[^\\s,;&]+", Pattern.CASE_INSENSITIVE);
  private static final Pattern CREDENTIAL_VALUE =
      Pattern.compile(
          "(?i)\\b(access[_-]?token|appsecret[_-]?proof|token)\\s*[:=]\\s*[^\\s,;&]+",
          Pattern.CASE_INSENSITIVE);
  private static final Pattern CONTROL_CHARACTERS = Pattern.compile("[\\p{Cntrl}]+");

  private MetaErrorSanitizer() {}

  static String sanitize(String reason, String fallback, String... knownCredentials) {
    if (reason == null || reason.isBlank()) {
      return fallback;
    }

    String sanitized = reason;
    if (knownCredentials != null) {
      for (String credential : knownCredentials) {
        if (credential != null && !credential.isBlank()) {
          sanitized = sanitized.replace(credential, "[REDACTED]");
        }
      }
    }
    sanitized = BEARER_VALUE.matcher(sanitized).replaceAll("Bearer [REDACTED]");
    sanitized = CREDENTIAL_VALUE.matcher(sanitized).replaceAll("$1=[REDACTED]");
    sanitized = CONTROL_CHARACTERS.matcher(sanitized).replaceAll(" ").trim();
    if (sanitized.isBlank()) {
      return fallback;
    }
    return sanitized.length() <= MAX_LENGTH
        ? sanitized
        : sanitized.substring(0, MAX_LENGTH);
  }

  static String sanitizeOrNull(String reason, String... knownCredentials) {
    if (reason == null || reason.isBlank()) {
      return null;
    }
    return sanitize(reason, "The Meta provider validation failed.", knownCredentials);
  }
}
