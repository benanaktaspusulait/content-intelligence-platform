# Local Development

Requirements: Java 21, Maven 3.9+, Node 22.12+, npm, Python 3.12+, FFmpeg/ffprobe, and Docker Desktop.

Full stack:

```bash
cp .env.example .env
docker compose up --build
```

Native services:

```bash
docker compose up -d postgres
cd ml-service && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload
cd ../backend && mvn spring-boot:run -Dspring-boot.run.profiles=local
cd ../frontend && npm ci && npm start
```

Place test media under `data/videos/original/` and ingest paths relative to `data/`. Never point the data root at an unrestricted filesystem location.
