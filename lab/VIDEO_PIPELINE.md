# Video Pipeline

1. Recursively discover MP4/MOV/MKV/WebM inside the configured root.
2. Hash content and collect FFprobe metadata.
3. Sample frame zero, each 0.25s in the first 3s, every 1s through the middle, and each 0.25s
   in the final 2s.
4. Save evidence frames and a timestamped storyboard without source upscaling.
5. Measure frame difference, optical-flow motion, brightness, entropy, black frames, static
   intervals, scene changes, opening onset, and final-to-first similarity.
6. Detect local audio silence with FFmpeg; transcription is intentionally optional.
7. Add semantic evidence when a local VLM is explicitly configured.
8. Score with rubric gates, create reports, and persist an immutable source reference.
9. Safe fix operations only trim existing footage and write a candidate to a separate tree.

