# Implementation Plan

## Environment Decision

- Java 21.0.7 and Maven 3.9.9 are available.
- Spring Boot 4.1.1 is the selected stable release.
- Node 22.22.0 is compatible with Angular 21, not Angular 22's current minimum patch; Angular 21.2 is pinned.
- Docker Desktop exists but may not be running. Native builds remain possible.
- FFmpeg 8.1 and ffprobe are available. Apple M1 Pro GPU is visible; no GPU is required.

## Delivery Phases

1. Monorepo, ADRs, Compose, health endpoints.
2. Flyway schema and Video/Character/Prediction domain.
3. FastAPI metadata, frame, fingerprint, baseline prediction contracts.
4. Angular operational shell and core pages.
5. Performance import, matching, trajectory, audit.
6. Jobs, experiments, planner, model registry, research queue.
7. Non-destructive fix candidates and broader E2E coverage.

Each phase must pass formatting, compile/type checks, unit tests, contract tests, and relevant integration tests before promotion.

