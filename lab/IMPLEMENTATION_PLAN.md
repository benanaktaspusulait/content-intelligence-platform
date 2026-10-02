# Pompom Creative Lab - Implementation Plan

## Scope

This installation is intentionally bound to the parent `new14092026` media tree. It never
modifies source media. Generated evidence, reports, database state, and edit candidates live
under `Pompom_Creative_Lab/.lab_data/`.

## Phases

1. Environment: verify Python, FFmpeg/ffprobe, OpenCV, Pillow, and local AI availability.
2. Foundation: typed configuration/models, logging, deterministic IDs, SQLite migrations.
3. Video pipeline: metadata, configurable frame sampling, storyboard, motion/change metrics,
   black/fade/static detection, and audio silence/loudness evidence.
4. Analysis: provider abstraction, honest local heuristics, optional OpenAI/Ollama-compatible
   local VLM, evidence-first Pompom Action DNA scoring, fatal-problem classification.
5. Fix engine: validated, non-destructive trims/cuts/end-card removal and candidate re-analysis.
6. Workflow: recursive/resumable batch analysis, daily queue, CSV performance import, series
   aggregates, Markdown/JSON reports.
7. Dashboard: local library, filters/sorts, video detail, timeline, evidence, review overrides,
   notes, fix approval/rejection, and performance entry.
8. Validation: unit and integration tests including duplicates, Unicode paths, missing tools,
   short/landscape/no-audio/corrupt inputs, provider outages, and fix-plan validation.
9. Creative research: maintain Stock Creative Rescue as a separate mode, preserve alternative
   engines, and compare minimal vs cold-open candidates using observed platform data.

## Explicit Boundaries

- The Action DNA score is a creative-structure match, never a view prediction.
- Performance is stored separately and correlations are descriptive only.
- Without a semantic model, goal/rule/continuity claims are conservative and low-confidence.
- No generative frames, destructive overwrites, network calls, or automatic publishing.
