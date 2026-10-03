-- Two independent, additive fixes from the Part 02 audit (video_variants.variant_id already
-- exists for performance_observations/video_publications/platform_content_states since V1; this
-- migration only adds the two columns/tables that are genuinely still missing).

-- Fix 1 (P1-01): content-hash dedup silently discarded a second physical path that happened to
-- have byte-identical content to an already-ingested video. This table lets that second path
-- resolve to the canonical video instead of permanently reporting "Not ingested."
CREATE TABLE video_path_aliases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  relative_path TEXT NOT NULL UNIQUE,
  content_hash VARCHAR(64) NOT NULL,
  discovered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_video_path_aliases_video_id ON video_path_aliases(video_id);

COMMENT ON TABLE video_path_aliases IS
  'Additional physical paths that resolve to the same canonical video by content hash. A path''s presence here (or as videos.relative_path) both count as "ingested" for library listing purposes.';
COMMENT ON COLUMN video_path_aliases.content_hash IS
  'Denormalized copy of the owning video''s content_hash at discovery time, for fast verification without a join.';

-- Fix 2: intervention_events has no variant_id column at all (unlike performance_observations,
-- video_publications, platform_content_states, which have had it since V1). Additive, nullable;
-- the table is append-only (V3__intervention_events_append_only.sql trigger), so existing rows
-- simply get variant_id=NULL and can never be backfilled or mutated afterward - that is expected
-- and correct, not a gap to close later.
ALTER TABLE intervention_events
  ADD COLUMN variant_id UUID REFERENCES video_variants(id) ON DELETE CASCADE;

CREATE INDEX idx_intervention_events_variant
  ON intervention_events(variant_id)
  WHERE variant_id IS NOT NULL;

COMMENT ON COLUMN intervention_events.variant_id IS
  'Optional variant this intervention was observed against. NULL means the intervention is not scoped to a specific variant (legacy rows, or a video with no variants) - matched with IS NOT DISTINCT FROM, never treated as "any variant".';
