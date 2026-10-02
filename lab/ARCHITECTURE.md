# Architecture

`CLI -> Pipeline -> FFprobe/OpenCV/Audio -> VisionAnalyzer -> Scoring -> Reports + SQLite`

The dashboard reads the same SQLite library and serves source video with byte ranges. Stable
IDs are the first 16 characters of SHA-256 content hashes. Analysis caching is keyed by video,
software version, and rubric version. Providers implement `VisionAnalyzer`; local heuristics
always work, while the local VLM is optional and falls back visibly on failure.

The app is dependency-light by design: Python standard library handles CLI, HTTP, JSON,
SQLite, migrations, and networking; FFmpeg and OpenCV handle media evidence. The server binds
to `127.0.0.1` by default.

`RescuePipeline` reuses the same deterministic evidence but applies a separate prompt,
classification, report, review record, and edit history. This prevents Action DNA from
silently becoming a universal creative rule.
