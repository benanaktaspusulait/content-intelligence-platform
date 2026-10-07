# Mimi vs. the Sneaky Door — Compact Generation Card

## Final Target

- 15 seconds total: 3 × 5-second clips
- 1080×1920, 9:16 vertical, 24 fps
- Location: canonical Kiko's Home front porch
- Style: warm, rounded, matte Pompom Hills preschool animation
- Language: English only
- OpenArt music: OFF

## Attachments

- Mimi: `01-CHARACTERS/drawings/mimi.png`
- Kiko: `01-CHARACTERS/drawings/kiko.png`
- World: `POMPOM_HILLS_PRODUCTION/02_WORLDS/KIKOS_HOME/01_HERO_VIEW/hero-view.png`
- Separate Negative Prompt: `mimi-sneaky-door-negative-prompt.txt`

## Render Order

### 1. Build `@image1`

Use `start-and-loop-frame-prompts.md`. Approve Mimi identity, vertical door staging, safe movement space and exact Kiko's Home identity.

### 2. Render Shot 01

Use `mimi-sneaky-door-shot-01-openart.md` with `@image1`.

Action: door closes → Mimi “Huh?” → strong pull → smaller tug → puzzled stable end.

Export the unmodified final frame as `@image2`. Reject it if Mimi, door, world, colour or camera drifted.

### 3. Render Shot 02

Use `mimi-sneaky-door-shot-02-openart.md` with `@image2`.

Action: two real steps away → door opens once → Mimi turns → door closes once → clever realization.

Export the unmodified final frame as `@image3`. Reject it if the chain degraded.

### 4. Build Optional `@image4`

Use the loop-wipe section in `start-and-loop-frame-prompts.md`. It must match the exact door material and warm exposure.

### 5. Render Shot 03

Use `mimi-sneaky-door-shot-03-openart.md` with `@image3`; add `@image4` as final-frame anchor if supported.

Action: two fake steps → spring-back and “Got you!” → Kiko visible doorway entrance and “Surprise!” → controlled door-to-lens wipe.

### 6. Assemble

Concatenate Shot 01 → Shot 02 → Shot 03 with direct cuts only. No dissolve, crossfade, title card, moral card or speed effect. Keep exactly 360 final frames. The last door-surface frame is a visual loop bridge into the opening; it is not a frame-identical seamless loop.

## Non-Negotiable Locks

- Kiko is not visible in Shots 01–02.
- The canonical front door is the only environment object allowed to move.
- Mimi never leaves the visible safe area or enters the door swing path.
- Dialogue is exact and appears once per listed line.
- Use manually selected approved saved Mimi and Kiko voices.
- No generated music, narration, extra dialogue or readable text.
- No darkening, HDR, saturation, gloss, sharpening or world-layout drift.
