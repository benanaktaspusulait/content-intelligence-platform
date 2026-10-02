# Testing

Run all local quality gates with `./scripts/verify.sh`.

- Java: Spotless, Spring context, Flyway, and PostgreSQL Testcontainers. Integration tests cover immutable locked predictions and raw-to-normalized imports.
- Python: Ruff, mypy, and pytest for health, prediction cold-start behavior, and path validation.
- Angular: production build and Vitest component tests.

Docker Compose is the cross-service smoke test. Verify backend, Python, and frontend health, then inspect `/v3/api-docs`. Contract DTOs carry `contractVersion`; incompatible changes require a new version rather than silent field reuse.
