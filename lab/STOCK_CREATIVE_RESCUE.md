# Stock Creative Rescue

Prompt version: `stock-creative-rescue-v1`

This is a second analysis mode. It does not replace Pompom Action DNA and does not force every
video into the physical-anomaly family. It first asks what this specific video makes the viewer
feel or want to see next.

## Creative Engines

Physical problem, visual anomaly, mystery, reveal, character comedy, chase/movement,
transformation, impossible scale, emotional/cute moment, visual search/puzzle,
repetition/escalation, narrative continuation, educational discovery, spectacle, or a
human-labelled alternative.

Without a local VLM or human review, the engine remains explicitly unverified. Motion alone
cannot identify comedy, emotion, character goals, or reveal logic.

## Workflow

1. Review the entire sampled storyboard.
2. Identify the creative engine and complete: “The viewer keeps watching because ...”.
3. Find strongest movement, visual, surprise, reaction, anomaly, emotional frame, and final.
4. Score the first 0.8 seconds against the strongest available moment.
5. Build a 1.5-second beat map and mark passive/repeated intervals.
6. Review the final three seconds, CTA interruption, dead tail, and loop.
7. Preserve alternative promising patterns rather than imitating an existing winner.
8. Prefer existing footage. New footage is proposed only when a semantic provider can specify
   one continuity-safe missing shot.

## Rescue Classes

- `A — PRIME / PUBLISH AS-IS`: preserve the cut; do not edit for activity's sake.
- `B — STRONG BUT SMALL FIX`: trim, opening, CTA, ending, or loop adjustment only.
- `C — RESCUEABLE`: good idea currently wasted by setup/order/dead time; restructure existing footage.
- `D — LOW-VALUE TEST`: not justified for a prime slot in its current form.
- `E — DO NOT PUBLISH YET`: fundamental story, identity, animation, or creative-engine failure.

Observed platform performance is separate from creative scores and outranks speculative
assumptions. It does not prove causality and never becomes a predicted view count.

## A/B Edits

- `minimal`: safe start/end trims from explicit evidence.
- `cold_open`: 0.15-0.80 seconds copied from the strongest existing event, followed by a hard
  cut to the original sequence. It is marked as a semantic risk unless a local VLM verifies
  that the reveal is not spoiled.

Every candidate is written under `.lab_data/output/rescue_candidates/`, then passed through
both the base analysis and Rescue analysis. Originals are never overwritten.
