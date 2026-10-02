# Video Analysis

Spring validates a relative path inside `POMPOM_DATA_ROOT`; Python performs computation. Supported originals are MP4, MOV, and M4V.

The v1 pipeline uses ffprobe for metadata and SHA-256, samples the opening densely, samples approximately once per second, and samples the final two seconds every 250 ms. OpenCV measures frame differences, motion density, static ranges, black frames, opening/final motion, and first/last similarity. A timestamped contact sheet is written under `data/storyboards/`.

Every fingerprint feature contains `value`, `confidence`, `evidence`, and `timestampRanges`. Semantic features receive an explicit low-confidence neutral prior when no VLM is configured. This prevents motion heuristics from masquerading as story understanding.

The Action DNA score is a creative-structure match, not a viral probability. Original media is never modified.
