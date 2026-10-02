package com.pompomhills.intelligence.meta;

/**
 * Raised when the Meta OAuth authorization-code/token exchange or follow-up verification calls
 * fail. The message is a fixed, generic string; it never includes tokens, secrets, or raw Graph
 * error payloads.
 */
final class MetaOAuthException extends RuntimeException {
  MetaOAuthException(String message) {
    super(message);
  }
}
