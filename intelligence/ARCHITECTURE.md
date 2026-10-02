# Architecture

```text
Angular 21
   |
REST /api/v1
   |
Spring Boot 4.1.1 -- PostgreSQL 17
   |                         |
versioned REST              local filesystem
   |                         |
FastAPI computation service + FFmpeg/OpenCV/scikit-learn
```

Spring owns workflow, transactions, imports, experiments, locks, audit events, and model metadata. Python is stateless computation except for versioned model artifacts. PostgreSQL is authoritative; videos and artifacts stay on disk. No Kafka, Redis, Kubernetes, or Elasticsearch is used.

Locked predictions are immutable in both service logic and a PostgreSQL trigger. Raw imports are append-only. Creative score, observed performance, and learned opportunity remain separate.

