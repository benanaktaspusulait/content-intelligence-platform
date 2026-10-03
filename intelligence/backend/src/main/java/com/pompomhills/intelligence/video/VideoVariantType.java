package com.pompomhills.intelligence.video;

/**
 * Mirrors the {@code video_variants.variant_type} CHECK constraint in
 * {@code V1__initial_schema.sql} exactly - these six values are a database-enforced closed set,
 * not just a Java-side convenience. Do not add a seventh value here without a new migration
 * widening the CHECK constraint first.
 */
public enum VideoVariantType {
  ORIGINAL,
  HOOK_COLD_OPEN,
  TRIMMED,
  NO_CTA,
  LOOP_CUT,
  CUSTOM_EDIT
}
