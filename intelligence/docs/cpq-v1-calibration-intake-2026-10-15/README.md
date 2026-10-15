# CPQ V1 offline review preparation

Six exact production prompt copies are prepared in `blind-prompt-drafts/` under neutral local codes. The copies are byte-for-byte identical to their authoritative source files. They contain no added provider identity, canonical grade, view counts, popularity labels, intended quality grade, or human judgments. Source titles that are part of the original prompt remain intact.

These files are **offline drafts**, not imported calibration examples or API-issued reviewer packets. No corpus exists in production. The separate `supervisor-intake-manifest.json` contains provenance and provisional grouping; do not give that manifest to blind quality reviewers. Null production settings and source fields are missing evidence, not defaults.

Before import, establish the exact approved source story/revision and authoritative production settings, obtain independently authenticated source-fidelity evidence, and use the existing calibration APIs. The current fidelity submission API is saved-candidate/comparison-bound; it cannot by itself qualify arbitrary external originals. Do not fabricate a candidate or fidelity record to bridge this gap.

The proposed calibration/held-out groups are review planning only and are not frozen: chair and lamp share a recurrence group; shoe and carrot share a search/reveal group. All revisions of one story or mechanic must stay in the same split. The related carrot alternate and every Mimi original/candidate variant must remain with their respective group if later admitted. Six unreviewed examples cannot justify statistical thresholds or A/A+ grading.

After legitimate import, authenticated reviewers receive packets only through `GET /api/v1/intelligence/workflow/cpq/calibration/examples/{exampleId}/blind-review`. Two distinct qualified human reviewers must assess all six dimensions with exact prompt citations. No review has been submitted by this preparation.
