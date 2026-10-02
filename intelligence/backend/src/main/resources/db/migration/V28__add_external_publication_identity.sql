ALTER TABLE video_publications
  ADD COLUMN platform_content_id TEXT,
  ADD COLUMN platform_url TEXT;

CREATE UNIQUE INDEX uq_video_publications_platform_content_id
  ON video_publications(platform, platform_content_id)
  WHERE platform_content_id IS NOT NULL;

COMMENT ON COLUMN video_publications.platform_content_id IS
  'External platform post, reel, or video identifier. Registration does not publish content.';
COMMENT ON COLUMN video_publications.platform_url IS
  'Canonical URL of the already-published external platform content.';
