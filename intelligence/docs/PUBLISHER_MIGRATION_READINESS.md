# Publisher migration status

The publisher migration is complete for the Java service boundary. Runtime publication is owned by the internal Java publisher services and render-service internal clients:

- `meta-publisher-service`: Facebook Page Reels and Instagram Professional Reels.
- `tiktok-publisher-service`: TikTok chunked upload and reconciliation.
- `youtube-publisher-service`: YouTube Shorts OAuth refresh and resumable upload.

All internal requests use the provider-neutral `publisher-contract` payload. Provider credentials stay inside the target service; render-service sends publication identity, asset reference/hash, metadata, capability and idempotency data. Publisher services are internal-only Compose services with health checks and fail-closed write flags.

The former standalone Python publisher package, SQLite ledgers, Python dependencies, command-line batch scripts and historical integration instructions were removed after Java contract/parity tests and render-service routing tests passed. No runtime path imports or executes the removed Python publisher code.

Publishing remains disabled by default. Enabling a provider requires its server-side write flag, internal caller token and provider credentials; no browser route receives those secrets. Live publishing and live provider calls were not used for this migration verification.
