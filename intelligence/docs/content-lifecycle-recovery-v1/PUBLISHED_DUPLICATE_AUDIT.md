# Published and Duplicate Audit

Date: 2026-11-02. Local evidence only; no external platform calls.

## Exact duplicate measures

- Prompt-source exact-content copies excluded by the existing inventory: **7** (814 discovered files → 807 unique contents).
- Identical video-file copies: **48 extra copies across 47 hash groups**; **755 distinct video hashes** among 803 video files.
- Exact duplicate story/production identities positively confirmed: **0 from the complete local provenance available here**. The file-copy counts above do not imply story equivalence.
- `EXACT_DUPLICATE_OF_PUBLISHED` rows in the new-candidate screen: **0 established**. Candidate lifecycle is unresolved, so this does not mean clear.

## Candidate comparison

| Candidate | Existing evidence | Classification | Decision |
|---|---|---|---|
| Kiko — Upside-Down / Sunny Umbrella | Candidate proposes an open/closed umbrella linked to abrupt sun/rain changes. Existing `Whats_Wrong_Season_2/04_kiko_umbrella_open_closed` tracker says Meta `PUBLISHED`, TikTok `PUBLISHED`, YouTube `READY`; its metadata describes Kiko’s umbrella repeatedly opening and closing. A different archived Kiko umbrella video/prompt also exists. | `HIGH_SIMILARITY_REVIEW` | Exclude. The shared object alone is insufficient for equivalence; shared umbrella-state/phenomenon motif plus known published item requires comparison/review. Candidate-specific lifecycle is also unknown. |
| Luca — Shadow Takes a Shortcut | Archive has a generated MP4, prompt and social copy for `Luca vs. the Cheating Shadow`. Social copy explicitly says Luca races his shadow and it repeatedly finds a shortcut to arrive first. Proposed plan has Luca circle a tree while the shadow shortcuts across the trunk and remains ahead; exact same protagonist, race/catch-up goal, shadow shortcut, repeated losing progression and payoff. No local publication tracker row for the archived item was found. | `HIGH_SIMILARITY_REVIEW`; probable story-equivalent pending publication reconciliation | Exclude. Evidence supports strong structural overlap, but archive placement and an MP4 do not prove publication. Do not call it `STORY_EQUIVALENT_TO_PUBLISHED` until the archived item's publication status and structured shape comparison are established. |
| Mimi — Rainbow on Her Hand | No exact or close published rainbow-hand item found in scoped tracker/metadata search. Candidate is under `not-generated`; its lifecycle cannot be positively verified. | `INSUFFICIENT_EVIDENCE` | Exclude. “No match found” is not proof of unused, and no approved first-frame image exists. |

## Lifecycle reference examples

- `01_runaway_toothbrush` has local original prompt and MP4 with exact hashes. The tracker row is `MISSING_METADATA | MISSING_METADATA | READY`, conflicting with the user instruction that the video was published. Workflow is closed as already published based on the user attestation; platform/date remain unverified.
- `04_kiko_umbrella_open_closed` has local tracker `PUBLISHED` cells for Meta and TikTok. This is tracker-asserted publication evidence, not a locally available post ID/date.
- `Luca_vs._the_Cheating_Shadow` has a prompt, social copy and MP4, but no publication confirmation located. Classified `UNKNOWN`, not published and not unused.

The existing Creative Shape/Historical Territory implementations were not given complete canonical structured story fields for these candidates and archive controls. Their output is therefore `INSUFFICIENT_EVIDENCE`; no new similarity engine or title-based duplicate assertion was introduced.
