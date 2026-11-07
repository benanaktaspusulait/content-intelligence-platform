# Offline pre-render validation — Mimi rising dough ridge

**Result: PRE_RENDER_PASS**

This is a deterministic text-only validation of the final prompt against the requested gates and the accepted architecture in `../REPORT.md`. It does not establish rendered-video quality or model compliance.

## Required outputs

- **Exact source revision:** `../REPORT.md`, section 10, “One revised story architecture (specification only),” including the exact frame-zero description, four beats, 14.5-second revised timing blocks, and rule-consistency proof. The original Phase B response remains separately preserved in the run directory.
- **Duration:** 14.5 seconds target; hard maximum 15.0 seconds.
- **Prompt:** `FINAL_PRODUCTION_PROMPT.md`.
- **First frame:** Mimi is already pressing a horizontal rolling pin onto a chest-high ridge rising directly under its barrel; broad flat dough remains visible on both sides. Both handles, contact, protagonist, goal, and contradiction are called out in the prompt.
- **Final frame:** one tall connected ridge supports the pin above Mimi's comfortable reach; Mimi remains focused on it and does not present to camera.
- **Immutable rule:** only downward rolling-pin pressure causes the dough directly beneath the barrel to rise vertically; the same connected ridge supports the barrel.
- **Continuity:** one Mimi, one location/table, one pin, one dough mass, one connected ridge; visible transitions and contact; fixed camera axis.
- **Negative constraints:** section I of the prompt; no other dough behavior, additional structures, magic, dialogue, extra characters/props, or presenter ending.

## Pre-render QA matrix

| Gate | Result | Evidence / reason |
|---|---|---|
| Opening legibility | PASS | Problem is active at frame zero; no establishing/setup lead-in. |
| Goal clarity | PASS | Flat sheet, braced Mimi, barrel contact, and upward ridge coexist in first frame. |
| Rule immutability | PASS | One explicit trigger, target, direction, and response repeated across all beats. |
| Trigger visibility | PASS | Barrel-to-dough contact required for each rise; lift/reposition shown before next press. |
| Four-beat density | PASS | Continue, crosswise false tamp, reverse roll from far side, final center press; four distinct actions/states. |
| Progress density | PASS | Ridge height, orientation/strategy, travel direction/body position, then reach relationship all change. |
| Payoff predictability | PASS | The rising ridge is foreshadowed, but the specific consequence—pin carried beyond Mimi's reach—is reserved for the final escalation. |
| Payoff strength | PASS | Final press causes the same-rule elevation; clear tool/reach mismatch and focused reaction. |
| Silent view | PASS | Goal, cause, failed attempts, and result are visual; no dialogue or captions required. |
| Camera naturalness | PASS | One stable three-quarter axis, portrait medium/medium-wide; no camera-aware acting. |
| Hand feasibility | PASS WITH RISK | Two hands stay on readable handles, but lifting, crosswise placement, reverse roll, and release need clean staging. No complex finger work. |
| Dough geometry feasibility | PASS WITH RISK | One flat sheet and one connected ridge only; topology stays simple. Height/contact continuity and Beat 3 ridge extension remain the main generation risks. |
| Continuity | PASS | Explicit one character/location/pin/dough/ridge; all movement is visible and contact-driven. |
| Final duration ≤15 s | PASS | Exact blocks total 14.5 seconds, including final 0.7-second hold. |

## Hard-fail audit

| Hard-fail condition | Check |
|---|---|
| Duration exceeds 15 seconds | No — 14.5 seconds. |
| Opening starts before problem | No — the impossible contact is present at frame zero. |
| Rule changes | No — fixed across all four beats. |
| More than one independent dough behavior | No — only local vertical rise under downward barrel contact. |
| Repeated beats without meaningful progress | No — distinct orientation, direction/body position, height, and reach state. |
| Payoff requires a second rule | No — same rise lifts and supports the pin. |
| Rolling-pin contact unclear | No by specification — explicit visible contact for every activation. |
| Multiple walls/box return | No — prohibited, one connected ridge. |
| Front-facing reaction ending | No — Mimi remains focused on the elevated pin. |
| Dialogue required | No — silent visual causality. |
| Geometry continuity is HIGH risk | No at the topology level: only one connected ridge and flat sheet persist, with no topology changes. Residual height/contact continuity and Beat 3 extension are material risks, recorded above; they do not require tracking multiple independent structures. |

## Remaining risks

1. The crosswise tamp can obscure whether the roller touches only the same ridge; keep the entire contact zone visible.
2. Beat 3's reverse roll and continuous ridge extension may be difficult for a video model to preserve. Keep it a single uninterrupted path and do not introduce a second strip or structure.
3. The pin and Mimi's hands must rise with the ridge while maintaining visible physical support; avoid unsupported hovering.
4. Showing the full ridge, Mimi, and flat dough in 9:16 can crowd the frame; keep Mimi large and use a broad but not distant medium-wide composition.
5. The text plan passes offline review only; no render has been made, so visual execution remains unverified.

## Scope and integrity proof

- Provider calls: **0**.
- Render calls: **0**.
- Original Phase B evidence: hashes recorded in `source-evidence-hashes-before.json` and `source-evidence-hashes-after.json`; equality is recorded in `integrity.json`.
- Phase A diversity issue: untouched; no Phase A artifacts were opened or modified for this task.
- Production candidate/story, seed, validators, and source prompts: unchanged.
- No alternate concepts generated.
