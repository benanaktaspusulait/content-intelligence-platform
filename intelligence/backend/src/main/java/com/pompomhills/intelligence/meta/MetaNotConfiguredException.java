package com.pompomhills.intelligence.meta;

/** Raised when a Meta read-only operation is requested but the integration is not configured. */
final class MetaNotConfiguredException extends RuntimeException {
  MetaNotConfiguredException() {
    super("Meta read-only analytics is not configured.");
  }
}
