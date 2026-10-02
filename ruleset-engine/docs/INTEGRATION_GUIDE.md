# Integration Guide: Creative Intelligence ↔ Ruleset Engine

## Architecture

Creative Intelligence Backend calls Ruleset Engine via REST API.

```
Creative Intelligence (Spring Boot :8080)
   ↓ HTTP REST
Ruleset Engine (Spring Boot :8081)
```

## Use Case 1: Pre-Render Validation

**When:** Before submitting video render job to OpenArt

**Workflow:**
1. User creates content with concept text
2. Creative Intelligence calls `POST /api/ruleset/v1/validate/concept`
3. If `approved=false`, reject concept and show reasons
4. If `approved=true`, proceed to render

**Java Client Example:**

```java
@Service
public class RulesetClient {
    
    private final WebClient webClient;
    
    public RulesetClient(@Value("${ruleset.engine.url}") String baseUrl) {
        this.webClient = WebClient.builder()
            .baseUrl(baseUrl)
            .build();
    }
    
    public ConceptValidationResponse validateConcept(String conceptText, ContentIntent intent) {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .externalConceptId(UUID.randomUUID().toString())
            .conceptText(conceptText)
            .intent(intent)
            .build();
        
        return webClient.post()
            .uri("/validate/concept")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(ConceptValidationResponse.class)
            .block();
    }
}
```

**Usage in Content Workflow:**

```java
@Service
public class ContentService {
    
    private final RulesetClient rulesetClient;
    private final RenderJobService renderJobService;
    
    public void submitForRender(Content content, String conceptText) {
        // Validate concept first
        ConceptValidationResponse validation = rulesetClient.validateConcept(
            conceptText,
            ContentIntent.GROWTH
        );
        
        if (!validation.getApproved()) {
            throw new ConceptRejectionException(
                "Concept failed validation: " + 
                String.join(", ", validation.getCriticalIssues())
            );
        }
        
        // Log warnings if any
        if (!validation.getWarnings().isEmpty()) {
            log.warn("Concept has warnings: {}", validation.getWarnings());
        }
        
        // Proceed to render
        renderJobService.createJob(content);
    }
}
```

## Use Case 2: Post-Publish Analysis

**When:** After metrics are collected from platform APIs

**Workflow:**
1. Video is published to social platform
2. Metrics collector fetches performance data (T+1h, T+24h, T+7d)
3. Creative Intelligence calls `POST /api/ruleset/v1/performance/analyze`
4. Store performance classification for reporting

**Java Client Example:**

```java
public void analyzeVideoPerformance(PublicationJob job, VideoMetrics metrics) {
    PerformanceAnalysisRequest request = PerformanceAnalysisRequest.builder()
        .externalVideoId(job.getId().toString())
        .platform(mapPlatform(job.getPlatform()))
        .intent(ContentIntent.GROWTH)
        .durationSeconds(BigDecimal.valueOf(15.0))
        .metrics(PerformanceAnalysisRequest.MetricsDto.builder()
            .views(metrics.getViews())
            .likes(metrics.getLikes())
            .reach(metrics.getReach())
            .avgWatchTimeSeconds(metrics.getAvgWatchTimeSeconds())
            .threeSecondViews(calculateThreeSecViews(metrics))
            .uniqueViewers(estimateUniqueViewers(metrics))
            .build())
        .timeSincePublishHours(calculateHoursSincePublish(job))
        .build();
    
    PerformanceAnalysisResponse analysis = rulesetClient.analyzePerformance(request);
    
    // Store classification
    job.setPerformanceClassification(analysis.getClassification().toString());
    publicationJobRepository.save(job);
    
    // Log insights
    log.info("Performance insights for {}: {}", job.getId(), analysis.getInsights());
}
```

## Configuration

**Creative Intelligence `application.yml`:**

```yaml
ruleset:
  engine:
    url: ${RULESET_ENGINE_URL:http://localhost:8081/api/ruleset/v1}
    timeout-seconds: 30
```

**Ruleset Engine `application.yml`:**

```yaml
server:
  port: 8081
```

## Deployment

Both services can run independently:

**Development:**
```bash
# Terminal 1: Ruleset Engine
cd pompom-ruleset-engine
./mvnw spring-boot:run

# Terminal 2: Creative Intelligence
cd ../Pompom_Creative_Intelligence/backend
./mvnw spring-boot:run
```

**Production:**
- Deploy as separate containers/pods
- Use service discovery or hardcoded URLs
- Ensure network connectivity between services

## Error Handling

```java
try {
    ConceptValidationResponse validation = rulesetClient.validateConcept(concept, intent);
    // ...
} catch (WebClientResponseException e) {
    if (e.getStatusCode() == HttpStatus.SERVICE_UNAVAILABLE) {
        // Ruleset engine is down - decide: fail safe or fail open?
        log.error("Ruleset engine unavailable, allowing concept through");
        // proceed without validation (fail-open strategy)
    } else {
        throw new RulesetValidationException("Validation failed", e);
    }
}
```

## Monitoring

Both services expose `/actuator/health`:

```bash
curl http://localhost:8081/actuator/health
```

Track these metrics:
- Validation request rate
- Validation approval rate
- Performance analysis request rate
- API latency (p50, p95, p99)
