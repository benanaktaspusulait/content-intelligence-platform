-- Carries the variant resolved during import preview/commit through to the written observation.
-- Additive, nullable: existing import_rows predate variant resolution and have no variant to
-- backfill.
ALTER TABLE import_rows
  ADD COLUMN matched_variant_id UUID REFERENCES video_variants(id);

COMMENT ON COLUMN import_rows.matched_variant_id IS
  'Variant resolved from an explicit variantid/variant_id import column, scoped to matched_video_id. NULL when no variant column was present or it did not resolve to a variant of the matched video.';
