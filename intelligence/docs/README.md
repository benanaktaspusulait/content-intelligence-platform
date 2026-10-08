# Pompom Creative Intelligence System

AI-powered creative intelligence platform for video content creation, optimization, and distribution across social media platforms (TikTok, YouTube Shorts, Instagram Reels).

## 2026-10-08 operational audit

Current runtime/UI evidence and remaining work are in [Pompom end-to-end audit](POMPOM_END_TO_END_AUDIT.md) and [prioritized backlog](POMPOM_END_TO_END_BACKLOG.md). Feature checkmarks below are historical context; they are not journey-level verification. No backlog implementation was performed in this audit.

## Features

### Phase 1: Foundation & Core Domain ✅
- Content management with prompt versioning
- Render job orchestration
- Asset library management
- Database schema with Flyway migrations

### Phase 2: Render Pipeline ✅
- OpenArt API integration (video generation)
- Credit tracking and budget alerts
- QA service with decision engine
- Golden test framework

### Phase 3: OAuth & Publishing ✅
- OAuth2 flows (TikTok, YouTube, Instagram)
- Multi-platform publishers
- Publication state tracking
- Credential management with encryption
- Scheduled publishing
- AI-powered caption generation
- Webhook system for platform callbacks
- Publication history export (CSV/JSON)

### Phase 4: Learning Engine ✅
- Scheduled metrics collection (T+30m, 1h, 6h, 24h, 7d, 30d)
- Performance classification (10 categories)
- Trajectory analysis (9 shapes, velocity/acceleration)
- Correlation analysis (Pearson r)
- Rule mining (IF-THEN patterns)
- Winner catalog & benchmarking (4 tiers)

### Phase 5: Real Platform Integration ✅
- TikTok Content Posting API & Research API
- YouTube Data API v3 & Analytics
- Instagram Graph API (requires an externally hosted public media URL)
- Real API metrics collection with mock fallback

### Phase 6: Real-time Features ✅
- WebSocket infrastructure (STOMP, /ws endpoint)
- Real-time render progress streaming
- Live metrics updates
- Email notifications (HTML templates)
- In-app notification system
- SSE endpoints (/notifications, /metrics, /heartbeat)

### Phase 7: Advanced Analytics ✅
- Predictive performance scoring (pre-publish)
- Success probability & viral potential
- A/B testing framework with statistical analysis
- Optimal publish time recommendations
- Content improvement recommendations
- Anomaly detection (Z-score)
- Trend analysis (moving averages)

### Phase 8: Production Readiness ✅
- Prometheus metrics integration
- Rate limiting (100 req/min)
- Structured logging (Logstash)
- Custom health checks (disk space)
- Response compression
- Caching configuration

## Tech Stack

**Backend:**
- Java 21
- Spring Boot 4.1.1
- Spring Data JPA
- Spring WebSocket
- PostgreSQL with Flyway
- Micrometer + Prometheus

**Key Libraries:**
- Lombok (boilerplate reduction)
- Jackson (JSON processing)
- JavaMailSender (email)
- SockJS (WebSocket fallback)
- Apache POI (Excel export)
- Apache Commons CSV

## Quick Start

### Prerequisites
- Java 21+
- PostgreSQL 15+
- Maven 3.9+
- Platform API credentials (TikTok/YouTube/Instagram)

### Setup

1. **Clone repository**
```bash
git clone <repository-url>
cd Pompom_Creative_Intelligence/backend
```

2. **Configure database**
```bash
createdb pompom
```

3. **Set environment variables**
```bash
export DB_URL=jdbc:postgresql://localhost:5432/pompom
export DB_USERNAME=pompom
export DB_PASSWORD=your_password

# Platform OAuth
export TIKTOK_CLIENT_ID=your_client_id
export TIKTOK_CLIENT_SECRET=your_secret
export YOUTUBE_CLIENT_ID=your_client_id
export YOUTUBE_CLIENT_SECRET=your_secret
export INSTAGRAM_APP_ID=your_app_id
export INSTAGRAM_APP_SECRET=your_secret

# Security
export ENCRYPTION_KEY=$(openssl rand -base64 32)

# Email (optional)
export MAIL_HOST=smtp.gmail.com
export MAIL_USERNAME=your_email
export MAIL_PASSWORD=your_password
export EMAIL_NOTIFICATIONS_ENABLED=true

# OpenArt (optional)
export OPENART_API_KEY=your_api_key
export OPENART_ENABLED=true
```

4. **Build and run**
```bash
mvn clean install
mvn spring-boot:run
```

5. **Access application**
- API: http://localhost:8080
- Swagger UI: http://localhost:8080/swagger-ui.html
- Health: http://localhost:8080/actuator/health
- Metrics: http://localhost:8080/actuator/prometheus

## API Endpoints

### Render Jobs
- `POST /api/v1/render/queue` - Queue render job
- `GET /api/v1/render/{jobId}` - Get job status
- `GET /api/v1/render/jobs` - List all jobs

### Publications
- `POST /api/v1/publish` - Publish to platform
- `GET /api/v1/publish/{jobId}` - Get publication status
- `GET /api/v1/publish/scheduled` - List scheduled publications

### Metrics
- `POST /api/v1/metrics/schedule/{jobId}` - Schedule metrics collection
- `GET /api/v1/metrics/timeline/{jobId}` - Get metrics timeline
- `POST /api/v1/metrics/manual` - Manual metrics entry

### Analytics
- `POST /api/v1/analytics/predict` - Predict performance
- `POST /api/v1/analytics/ab-test` - Create A/B test
- `GET /api/v1/analytics/recommendations` - Get recommendations
- `GET /api/v1/analytics/trends` - Analyze trends

### WebSocket
- Connect: `ws://localhost:8080/ws`
- Topics:
  - `/topic/render/progress` - Render updates
  - `/topic/metrics/updates` - Metrics updates
  - `/topic/notifications` - Notifications

### SSE
- `GET /api/v1/sse/notifications` - Stream notifications
- `GET /api/v1/sse/metrics/{jobId}` - Stream metrics
- `GET /api/v1/sse/heartbeat` - Keepalive

## Database Schema

**24 migrations** (V1-V24):
- Contents, prompt versions
- Render jobs, assets, QA results
- Golden tests, reference prompts
- Platform credentials (encrypted)
- Publication jobs
- Scheduled publications
- Publication analytics
- Webhooks, webhook deliveries
- Video metrics, collection jobs
- Performance classifications
- Trajectory analyses
- Correlation analyses
- Rule candidates
- Winner entries
- Notifications
- Performance predictions
- A/B tests

## Configuration

Key configuration files:
- `application.yml` - Main configuration
- `application-local.yml` - Local development
- `application-docker.yml` - Docker deployment
- `logback-spring.xml` - Logging configuration

## Monitoring

**Prometheus Metrics:**
- `pompom.render.jobs.created` - Render jobs created (by type)
- `pompom.render.jobs.completed` - Render jobs completed (by type, status)
- `pompom.render.duration` - Render duration histogram
- `pompom.publications.created` - Publications created (by platform)
- `pompom.publications.completed` - Publications completed (by platform, status)

**Health Checks:**
- Database connectivity
- Disk space monitoring
- Custom health indicators

## Development

### Running tests
```bash
mvn test
```

### Code formatting
```bash
mvn spotless:apply
```

### Database migrations
```bash
mvn flyway:migrate
mvn flyway:info
```

## Production Deployment

### Docker
```bash
docker build -t pompom-creative:latest .
docker run -p 8080:8080 \
  -e DB_URL=... \
  pompom-creative:latest
```

### Kubernetes
See `k8s/` directory for manifests.

### Environment Variables
All sensitive configuration via environment variables (12-factor app).

## Security

- ✅ OAuth2 token encryption (AES-256)
- ✅ Rate limiting (100 req/min)
- ✅ Webhook signature verification
- ✅ SQL injection prevention (JPA)
- ✅ CORS configuration
- ✅ HTTPS recommended for production

## Performance

- ✅ Database connection pooling
- ✅ Response compression (gzip)
- ✅ Async task execution
- ✅ Caching support
- ✅ Scheduled batch processing

## License

Proprietary - Pompom Hills Production

## Support

For issues and questions, contact: admin@pompomhills.com

---

**Version:** 1.0.0  
**Last Updated:** September 2026  
**Status:** Production Ready ✅
