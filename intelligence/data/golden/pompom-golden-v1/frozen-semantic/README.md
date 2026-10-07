# Frozen Semantic Evidence

The deterministic Golden runner uses the existing semantic-check call boundary with frozen, local decisions. It never calls a live provider.

Semantic prompt/schema identities are currently `UNKNOWN` because the existing Prompt Quality path does not persist separate semantic prompt or schema versions. This is explicit provenance, not a fabricated version.

If a future Golden assertion requires a non-deterministic semantic judgment, add a per-asset fixture here and record its provider/model/prompt/schema identity in the full-stack fingerprint before changing the baseline.
