# First real-provider acceptance — pre-dispatch gate

Primary result: **REAL_MODEL_TEST_NOT_AUTHORIZED** (awaiting fresh explicit approval, not an implementation failure).

No paid inference was dispatched. One authenticated GET of model metadata returned HTTP 200 for `gpt-4o-mini-2024-07-18`. This checks credential/model-read access, not inference quota, successful inference or creative effectiveness. No credentials or authorization headers were saved.

## Reviewed proposal

- Official application command: `POST /api/v1/intelligence/workflow/records/f0d36feb-ee0f-4da8-ae21-2071a3ddea18/creative-optimization`.
- Provider: OpenAI direct; no custom API base or mock route.
- Exact configured model: `gpt-4o-mini-2024-07-18`; enabled, real-looking credential present.
- Selected immutable source: Content 10, Prompt ID 10/version 1; score 88.40625/B; canonical Ruleset 1.11.
- Prompt SHA-256: `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`.
- Approved-story SHA-256: `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`.
- Actual latest saved analysis and immutable prompt, approved-story provenance and current settings were loaded through read-only application GETs and checked for agreement.
- Profile ABSURD_PHYSICS, Seedance 2.0 Mini, 15s, 9:16, opening strategy AUTO, settings record `2d90c69b-bcec-4871-9c4e-7e029906c974`.
- Current V2 request/schema/system were assembled using deployed application code without calling a provider. No candidate fixture or prepared winning answer is supplied.
- Schema `creative_reconstruction_v2`: strict object/required fields and supported composition checked locally. The exact model's Structured Outputs compatibility is documented, but live schema acceptance remains untested until an authorized inference.

## Tokens and cost

Configured rates match the official model page: USD 0.15 per million input tokens and USD 0.60 per million output tokens. Maximum completion is **4,000 tokens**. The model context window is 128,000 tokens. The application does **not** configure a separate hard input-token parameter; its input gate is **24,000 UTF-8 payload bytes**. These are not interchangeable units.

Planned payload is 13,126 bytes, schema 1,717 bytes and system instructions 2,213 bytes: total 17,056 byte-based input budget units. The application's conservative byte-based cost estimate is `(17,056 × 0.15 + 4,000 × 0.60) / 1,000,000` = **USD 0.0049584**. This is an application estimate, not an exact token count or a guaranteed invoice. Provider-reported usage must determine the final calculated cost after an authorized call. No token usage exists yet.

Proposed operator ceiling is **USD 0.20 for exactly one inference request**. It is not granted by the supplied task. The future command retains normal application budget reservation, idempotency, durable provider evidence and no automatic retry. The saved pending request has `operatorAuthorized: false` and has not been sent.

## Model lifecycle caveat

Official documentation currently labels this exact model snapshot deprecated. Model metadata access returned 200; this is not treated as proof of successful inference availability. No replacement/fallback model was selected. If an authorized request fails, retain the failure and do not make a second call.

## Pending evidence

Model decision/structured response, compiler contribution, full new candidate, per-beat changes, canonical/source outcomes, real tokens/cost and product-value assessment do not exist yet. The exact original prompt and current source context are saved in `verified-source-context.json` and `prompt-versions.json`. Final recommendation remains KEEP_ORIGINAL. No prompt version, story change, candidate approval, ATTEMPT exception, visual generation, render or publication was performed. No direct production SQL modification or commit/push was performed.

The user attachment section 2 explicitly says: “STOP BEFORE DISPATCH until the operator explicitly authorizes the positive budget and one provider call.” This report records the gate rather than treating the task itself as spending permission.

## Official documentation checked

- [Exact model family, snapshot, pricing, context and Structured Outputs](https://developers.openai.com/api/docs/models/gpt-4o-mini)
- [Structured Outputs model/schema compatibility](https://developers.openai.com/api/docs/guides/structured-outputs)
