# Quick Start

## Prerequisites

- Java 21+
- PostgreSQL 15+
- OpenAI API key
- Maven 3.8+

## Setup

### 1. Clone and Configure

```bash
cd /path/to/Pompom_Ruleset_Engine
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Start PostgreSQL

**Option A: Docker**
```bash
docker-compose up postgres -d
```

**Option B: Local PostgreSQL**
```bash
createdb pompom_ruleset
```

### 3. Run Database Migrations

```bash
./mvnw liquibase:update
```

Expected output:
```
[INFO] Successfully released change log lock
[INFO] BUILD SUCCESS
```

### 4. Start Application

```bash
./mvnw spring-boot:run
```

Expected output:
```
Started RulesetEngineApplication in X.XXX seconds
```

### 5. Verify Health

```bash
curl http://localhost:8081/actuator/health
```

Expected: `{"status":"UP"}`

## Test API

### Validate a Concept (Positive Example)

```bash
curl -X POST http://localhost:8081/validate/concept \
  -H "Content-Type: application/json" \
  -d '{
    "conceptText": "Giant spoon that grows with every pour. Kiko pours water, spoon grows. Final: spoon fills entire kitchen.",
    "intent": "GROWTH"
  }'
```

Expected: `{"approved": true, "overallScore": 100.0, ...}`

### Validate a Concept (Negative Example)

```bash
curl -X POST http://localhost:8081/validate/concept \
  -H "Content-Type: application/json" \
  -d '{
    "conceptText": "Door that eventually opens after pushing",
    "intent": "GROWTH"
  }'
```

Expected: `{"approved": false, "criticalIssues": [...], ...}`

### Analyze Performance

```bash
curl -X POST http://localhost:8081/performance/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "externalVideoId": "test-001",
    "platform": "META_FACEBOOK",
    "durationSeconds": 15.0,
    "metrics": {
      "views": 25000,
      "reach": 31000,
      "threeSecondViews": 24500,
      "avgWatchTimeSeconds": 16.8,
      "uniqueViewers": 8500
    },
    "timeSincePublishHours": 48
  }'
```

Expected: `{"classification": "STRONG", "overallQuality": 87.5, ...}`

## Next Steps

- **Seed Rules:** Insert initial rule definitions into `rules` table
- **Run Tests:** `./mvnw test`
- **Read Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **Review Rules:** [RULE_DEFINITIONS.md](RULE_DEFINITIONS.md)
- **Integration:** [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

## Troubleshooting

### Database Connection Error

```
Error: Connection to localhost:5432 refused
```

**Solution:** Ensure PostgreSQL is running:
```bash
docker-compose up postgres -d
# or
pg_ctl status
```

### OpenAI API Error

```
Error: Invalid API key
```

**Solution:** Check `.env` file has valid `OPENAI_API_KEY`

### Port Already in Use

```
Error: Port 8081 is already in use
```

**Solution:** Change port in `application.yml`:
```yaml
server:
  port: 8082
```

## Development Mode

**Auto-reload on file changes:**

```bash
./mvnw spring-boot:run -Dspring-boot.run.fork=false
```

**Run with debug logging:**

```bash
./mvnw spring-boot:run -Dspring-boot.run.arguments=--logging.level.com.pompom.ruleset=DEBUG
```

## Production Deployment

**Build JAR:**

```bash
./mvnw clean package -DskipTests
```

**Run JAR:**

```bash
java -jar target/ruleset-engine-1.0.0-SNAPSHOT.jar
```

**Docker:**

```bash
docker-compose up -d
```
