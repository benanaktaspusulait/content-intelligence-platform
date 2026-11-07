# Mimi Canonical Reference — Human Review Package

**Review decision required:** approve or reject the existing canonical source for production reference use. No status was changed in this task.

## Recommended candidate

Recommend review of the registered full character sheet at:

`/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/mimi.png`

It is the only existing registered Mimi character sheet. The image visibly depicts the light-blue rabbit, floppy blue ears with pink inner ears, green eyes, pink nose, white belly/tail and yellow shirt. These match [`01-CHARACTERS/02-mimi.md`](/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/02-mimi.md). Character ID from the existing character registry/provenance is `00000000-0000-0000-0000-000000000003`; the seeded character row status is `UNTESTED`, which is separate from reference approval. `mimi-reference-owner-review.png` is a byte-identical copy of the canonical PNG, not a separate candidate. The project environment asset registry is environment-only; it has no row that approves this character image.

- Dimensions / format: 1536×1024, RGB PNG, 1,904,791 bytes
- SHA-256: `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57`
- Approval: `UNREVIEWED`; prior provenance records `canonicalApproval: NOT_APPROVED`
- Successful use: no successful reference-conditioned generation is evidenced. The failed V1 render explicitly sent `referenceImages: []` and used text2video; it generated a human child. The canonical image was only the source for the crop below.

![Canonical Mimi sheet](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/pilot-readiness-v1/v2-unblock-review/mimi-canonical-source.png)

## Existing derivative (not approved)

[`mimi-reference-clean-crop-owner-review.png`](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/pilot-readiness-v1/v2-unblock-review/mimi-owner-review-crop.png) is a pixel crop of the canonical sheet (249×394; SHA-256 `80e0579ac5979be010da5c7250debbe9e74e84b37661d7a2213f24e055e49f14`). Its provenance says `UNAPPROVED_DERIVATIVE_OWNER_REVIEW_ONLY`, with owner review required. It is not approved for production. If the owner prefers this single-character crop, it needs its own explicit approval and hash-bound record; approval of the source must not silently approve the derivative.

The other local Mimi images found are story or generated scene outputs, not registered character identity references. They must not be substituted for the canonical sheet.

## Why owner approval is still required

The source file and character canon agree visually, but the project provenance explicitly marks the source unreviewed and not approved. The character row's `UNTESTED` status is not image approval. The [environment Asset Registry](/Users/benanaktas/project/video/yuvarlak-dunya/00-CORE/ASSET_REGISTRY.md) is not a character-reference approval registry. Presence, visual plausibility, or a successful file hash check cannot replace an owner decision.

## Auditable approval procedure using existing project API

Use the authenticated local project application and the existing character-reference lifecycle. First inspect the workspace candidate:

```http
GET /api/v1/characters/00000000-0000-0000-0000-000000000003/workspace-references
```

It should list `library/01-CHARACTERS/drawings/mimi.png` as `UNREVIEWED`. To place this exact file into the existing review queue (still no provider call):

```http
POST /api/v1/characters/00000000-0000-0000-0000-000000000003/workspace-references/import
Content-Type: application/json

{"relativePath":"library/01-CHARACTERS/drawings/mimi.png"}
```

The endpoint creates a `PENDING_REVIEW` record and returns its reference ID and SHA-256. A human reviewer should open the returned preview, compare it against the character canon and the attached sheet, and decide whether the exact image is fit for identity conditioning. Only the reviewer should approve or reject it. To approve, use the returned reference ID and an attributable reviewer name:

```http
POST /api/v1/characters/00000000-0000-0000-0000-000000000003/references/{referenceId}/approve
Content-Type: application/json

{"reviewer":"<reviewer name>"}
```

The existing approval endpoint verifies that the stored image hash is unchanged and records reviewer and timestamp. The approval endpoint was **not** called here. Do not run a render unless an explicit `APPROVED` record is visible for the exact hash.
