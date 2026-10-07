package com.pompom.publishersupport;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Redacts credential-shaped values before provider text is logged or persisted. */
public final class SecretRedactor {

  public static final int MAX_LENGTH = 300;
  public static final String REDACTED = "[REDACTED]";

  private static final Pattern AUTHORIZATION_ASSIGNMENT =
      Pattern.compile(
          "(?i)([\\\"']?\\bauthorization\\b[\\\"']?\\s*[:=]\\s*)(?:(bearer|basic|token)\\s+"
              + "[^\\s,;&}]+|(digest)\\s+[^}\\r\\n]+|[^}\\r\\n]+)");
  private static final Pattern BEARER_VALUE = Pattern.compile("(?i)\\bbearer\\s+[^\\s,;&}]+");
  private static final Pattern BARE_TOKEN_VALUE =
      Pattern.compile("(?i)\\btoken\\s+[A-Za-z0-9._~+/=-]{16,}");
  private static final Pattern SENSITIVE_ASSIGNMENT =
      Pattern.compile(
          "(?i)([\\\"']?\\b(?:access[_-]?(?:token|key)|refresh[_-]?token|token|"
              + "api[_-]?(?:key|secret)|oauth[_-]?(?:secret|token)|client[_-]?(?:secret|token)|"
              + "appsecret[_-]?proof|private[_-]?key|jwt|password|secret|credential)[\\\"']?"
              + "\\s*[:=]\\s*)(\\\"[^\\\"]*\\\"|'[^']*'|[^\\s,;&}]+)");
  private static final Pattern CONTROL_CHARACTERS = Pattern.compile("[\\p{Cntrl}]+");

  /** Redacts known secret values and generic credential-shaped material. */
  public String redact(String value, String... knownSecrets) {
    if (value == null || value.isBlank()) {
      return value;
    }

    String redacted = value;
    if (knownSecrets != null) {
      for (String knownSecret : knownSecrets) {
        if (knownSecret != null && !knownSecret.isBlank()) {
          redacted = redacted.replace(knownSecret, REDACTED);
        }
      }
    }
    redacted = replaceAuthorizationAssignments(redacted);
    redacted = BEARER_VALUE.matcher(redacted).replaceAll("Bearer " + REDACTED);
    redacted = BARE_TOKEN_VALUE.matcher(redacted).replaceAll("Token " + REDACTED);
    redacted = replaceSensitiveAssignments(redacted);
    redacted = CONTROL_CHARACTERS.matcher(redacted).replaceAll(" ").trim();
    if (redacted.length() > MAX_LENGTH) {
      return redacted.substring(0, MAX_LENGTH);
    }
    return redacted;
  }

  /** Alias used when sanitizing a provider-controlled response body or error message. */
  public String redactProviderResponse(String response, String... knownSecrets) {
    return redact(response, knownSecrets);
  }

  /** Redacts sensitive fields and sanitizes all other field values. */
  public Map<String, String> redactFields(Map<String, String> fields) {
    if (fields == null || fields.isEmpty()) {
      return Map.of();
    }

    Map<String, String> redacted = new LinkedHashMap<>();
    fields.forEach(
        (key, value) -> redacted.put(key, isSensitiveKey(key) ? REDACTED : redact(value)));
    return Map.copyOf(redacted);
  }

  private String replaceAuthorizationAssignments(String value) {
    Matcher matcher = AUTHORIZATION_ASSIGNMENT.matcher(value);
    StringBuffer result = new StringBuffer();
    while (matcher.find()) {
      String scheme = matcher.group(2) != null ? matcher.group(2) : matcher.group(3);
      String replacement =
          matcher.group(1) + (scheme == null ? "" : capitalize(scheme) + " ") + REDACTED;
      matcher.appendReplacement(result, Matcher.quoteReplacement(replacement));
    }
    matcher.appendTail(result);
    return result.toString();
  }

  private String replaceSensitiveAssignments(String value) {
    Matcher matcher = SENSITIVE_ASSIGNMENT.matcher(value);
    StringBuffer result = new StringBuffer();
    while (matcher.find()) {
      matcher.appendReplacement(result, Matcher.quoteReplacement(matcher.group(1) + REDACTED));
    }
    matcher.appendTail(result);
    return result.toString();
  }

  private String capitalize(String value) {
    return value.substring(0, 1).toUpperCase(Locale.ROOT)
        + value.substring(1).toLowerCase(Locale.ROOT);
  }

  private boolean isSensitiveKey(String key) {
    if (key == null) {
      return false;
    }
    String normalized = key.replaceAll("[^A-Za-z0-9]", "").toLowerCase(Locale.ROOT);
    return normalized.contains("token")
        || normalized.contains("secret")
        || normalized.contains("password")
        || normalized.contains("credential")
        || normalized.contains("authorization")
        || normalized.contains("apikey")
        || normalized.contains("accesskey")
        || normalized.contains("privatekey")
        || normalized.contains("oauth")
        || normalized.equals("jwt");
  }
}
