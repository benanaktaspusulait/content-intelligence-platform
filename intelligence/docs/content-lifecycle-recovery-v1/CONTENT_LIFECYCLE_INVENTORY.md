# Pompom Content Lifecycle Inventory and Reconciliation

Date: 2026-11-02  
Result: **NEW_PILOT_BLOCKED**  
Scope: configured Pompom Social Reels library plus the existing `intelligence/docs` discovery scope; no unrelated personal files and no external platform access.

## Discovery totals

The configured prompt discovery manifest (`pilot-readiness-v1/local-prompt-inventory.json`) reports 814 matching files, 807 unique file contents, and 7 exact duplicate copies. It is a bounded discovery inventory, not a count of every file in the video library. Its 807 unique items classify as 178 Story, 31 Concept, 92 Video, 9 First frame, and 497 Other. The configured Social Reels scope contributes 705 items (97 Story, 30 Concept, 92 Video, 4 First frame, 482 Other); the docs scope contributes 102 items (81 Story, 1 Concept, 0 Video, 5 First frame, 15 Other).

A separate scoped media scan of the configured Pompom production library found 12,339 files, including 803 video files and 912 PNG files. Hash comparison found 47 groups of byte-identical video files (48 extra copies; 755 distinct video hashes). These are export/file-copy counts, not story counts. The seven exact duplicate prompt-discovery copies and 48 duplicate video copies are different measures and must not be added as duplicate stories.

## Lifecycle evidence

| State/evidence class | Count | Interpretation |
|---|---:|---|
| Tracker rows with at least one platform cell `PUBLISHED` | 119 of 347 | Local tracker assertion only; tracker rows provide no publication ID, URL, or date in the inspected scope. The trackers define `PUBLISHED` as live. |
| Positive `PUBLISHED` platform cells | 237 | Cell count across the same tracker files; not a distinct-content count. |
| Tracker rows without a positive `PUBLISHED` cell | 228 | Unresolved: absence of `PUBLISHED` is not proof of never published. No explicit `NOT PUBLISHED` status was found. |
| Confirmed rendered but unpublished | 0 | No item had both a verified render and explicit evidence of non-publication. A render file alone cannot establish non-publication. |
| Genuinely unused prompt/story items | 0 established | None could be positively reconciled as not rendered and not published with adequate provenance. |
| Unknown/unresolved tracker rows | At least 228 | These are not counted as unused. Additional local prompt/media files cannot be mapped to a complete lifecycle entity set. |
| User-attested published Kiko — Runaway Toothbrush | 1 separate workflow closure | Operator attestation conflicts with its local tracker cells; retained as attested, not represented as platform-verified. |

The inspected local trackers contain 36 tracker files and 347 rows. Grep of the scoped local metadata found no YouTube/Shorts, youtu.be, Instagram Reel, Facebook, or TikTok publication URLs/IDs. Tracker dates are not treated as publication dates. No social APIs or platform scraping were used.

## Provenance and limits

The inventory links source documents and media where exact paths/hashes are available; it does not fabricate missing concept-to-prompt-to-frame-to-render-to-publication edges. `not-generated` folder names, missing MP4s, an image, or a prompt file alone do not establish `PROMPT_READY_NOT_RENDERED`, `CONCEPT_ONLY`, or `NOT_PUBLISHED_CONFIRMED`. Under the requested evidence rules, the largest honest “genuinely unused” count is zero established, not a claim that no unused ideas exist.

Kiko — Runaway Toothbrush was closed at the pilot workflow level as `CLOSED_ALREADY_PUBLISHED` with reason `EXISTING_PUBLISHED_CONTENT_SELECTED_FOR_NEW_PRODUCTION`. Its original prompt, render, tracker, asset bytes, approvals, and historical QA were preserved. The workflow closure and source evidence are recorded in the existing pilot manifest and `data/workflow/production-lifecycle-registry.json`; publication identifier/date remain null because they were not found locally.
