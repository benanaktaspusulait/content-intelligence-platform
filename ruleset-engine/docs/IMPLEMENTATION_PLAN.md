# Pompom Ruleset Engine v1.0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build standalone microservice for creative concept validation, performance analysis, and learning-based rule evolution

**Architecture:** Spring Boot 3.2+ REST API with PostgreSQL, OpenAI integration, YAML-based rule engine

**Tech Stack:** Java 21, Spring Boot, PostgreSQL 15+, Liquibase, OpenAI API, JUnit 5, Testcontainers

## Global Constraints

- Java 21 minimum
- Spring Boot 3.2+ (not 4.x from Creative Intelligence backend)
- PostgreSQL 15+ with JSONB support required
- OpenAI API key required (env variable)
- Rule auto-activation MUST be disabled (human approval required)
- Golden test suite MUST pass before any rule change is merged
- All timestamps UTC
- API versioning: `/api/ruleset/v1`

---

## Task 1: Database Schema and Migrations

**Files:**
- Create: `src/main/resources/db/changelog/db.changelog-master.xml`
- Create: `src/main/resources/db/changelog/001-initial-schema.sql`
- Create: `src/main/resources/db/changelog/002-golden-test-data.sql`

**Interfaces:**
- Produces: Complete database schema for all domain entities

- [ ] **Step 1: Create Liquibase master changelog**

Create `src/main/resources/db/changelog/db.changelog-master.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
    http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.20.xsd">

    <include file="db/changelog/001-initial-schema.sql"/>
    <include file="db/changelog/002-golden-test-data.sql"/>
</databaseChangeLog>
```

- [ ] **Step 2: Create initial schema migration**

Create `src/main/resources/db/changelog/001-initial-schema.sql`:

```sql
--liquibase formatted sql

--changeset pompom:1
CREATE TABLE rules (
    id UUID PRIMARY KEY,
    rule_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    evaluation_type VARCHAR(20) NOT NULL,
    description TEXT,
    yaml_definition JSONB NOT NULL,
    evidence_level VARCHAR(30) NOT NULL,
    active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_rules_active ON rules(active) WHERE active = true;
CREATE INDEX idx_rules_category ON rules(category);

--changeset pompom:2
CREATE TABLE concept_validations (
    id UUID PRIMARY KEY,
    external_concept_id VARCHAR(255),
    concept_text TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    overall_score DECIMAL(5,2),
    intent VARCHAR(50),
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cv_external_id ON concept_validations(external_concept_id);
CREATE INDEX idx_cv_approved ON concept_validations(approved);
CREATE INDEX idx_cv_created_at ON concept_validations(created_at DESC);

--changeset pompom:3
CREATE TABLE rule_evaluations (
    id UUID PRIMARY KEY,
    validation_id UUID NOT NULL REFERENCES concept_validations(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES rules(id),
    passed BOOLEAN NOT NULL,
    score DECIMAL(5,2),
    reason TEXT,
    details JSONB,
    evaluated_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_re_validation ON rule_evaluations(validation_id);
CREATE INDEX idx_re_rule ON rule_evaluations(rule_id);
CREATE INDEX idx_re_passed ON rule_evaluations(passed);

--changeset pompom:4
CREATE TABLE performance_scores (
    id UUID PRIMARY KEY,
    external_video_id VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    intent VARCHAR(50),
    views BIGINT,
    likes BIGINT,
    comments BIGINT,
    shares BIGINT,
    saves BIGINT,
    reach BIGINT,
    impressions BIGINT,
    avg_watch_seconds DECIMAL(6,2),
    duration_seconds DECIMAL(6,2),
    completion_rate DECIMAL(5,2),
    three_second_views BIGINT,
    unique_viewers BIGINT,
    avg_watch_ratio DECIMAL(5,4),
    entry_proxy DECIMAL(5,4),
    views_per_viewer DECIMAL(5,2),
    end_retention_rate DECIMAL(5,2),
    hook_strength DECIMAL(5,2),
    progression_score DECIMAL(5,2),
    attempt_diversity_score DECIMAL(5,2),
    educational_clarity DECIMAL(5,2),
    final_payoff DECIMAL(5,2),
    loopability_score DECIMAL(5,2),
    overall_quality DECIMAL(5,2),
    classification VARCHAR(30),
    wave_pattern VARCHAR(50),
    country_distribution JSONB,
    collected_at TIMESTAMP NOT NULL,
    time_since_publish_hours INTEGER,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_ps_external_video ON performance_scores(external_video_id);
CREATE INDEX idx_ps_platform ON performance_scores(platform);
CREATE INDEX idx_ps_classification ON performance_scores(classification);
CREATE INDEX idx_ps_collected_at ON performance_scores(collected_at DESC);

--changeset pompom:5
CREATE TABLE candidate_rules (
    id UUID PRIMARY KEY,
    rule_code VARCHAR(50),
    name VARCHAR(255),
    category VARCHAR(30),
    description TEXT,
    correlation_metric VARCHAR(100),
    correlation_coefficient DECIMAL(5,4),
    p_value DECIMAL(10,8),
    sample_size INTEGER,
    example_video_ids JSONB,
    status VARCHAR(30) NOT NULL,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_cr_status ON candidate_rules(status);
CREATE INDEX idx_cr_created_at ON candidate_rules(created_at DESC);

--changeset pompom:6
CREATE TABLE rule_evidence (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL REFERENCES rules(id),
    evidence_type VARCHAR(50) NOT NULL,
    video_id VARCHAR(255),
    metric_name VARCHAR(100),
    metric_value DECIMAL(10,4),
    notes TEXT,
    recorded_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_re_rule ON rule_evidence(rule_id);
CREATE INDEX idx_re_evidence_type ON rule_evidence(evidence_type);

--changeset pompom:7
CREATE TABLE golden_test_cases (
    id UUID PRIMARY KEY,
    test_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(30) NOT NULL,
    concept_text TEXT NOT NULL,
    intent VARCHAR(50),
    expected_approved BOOLEAN NOT NULL,
    expected_min_score DECIMAL(5,2),
    expected_max_score DECIMAL(5,2),
    expected_passing_rules JSONB,
    expected_failing_rules JSONB,
    notes TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_gtc_category ON golden_test_cases(category);
```

- [ ] **Step 3: Verify schema compiles**

Run:
```bash
./mvnw liquibase:update
```

Expected: Database schema created successfully

- [ ] **Step 4: Commit**

```bash
git add src/main/resources/db/changelog/
git commit -m "feat: add database schema for ruleset engine"
```

---

## Task 2: Repository Layer

**Files:**
- Create: `src/main/java/com/pompom/ruleset/repository/RuleRepository.java`
- Create: `src/main/java/com/pompom/ruleset/repository/ConceptValidationRepository.java`
- Create: `src/main/java/com/pompom/ruleset/repository/RuleEvaluationRepository.java`
- Create: `src/main/java/com/pompom/ruleset/repository/PerformanceScoreRepository.java`
- Create: `src/main/java/com/pompom/ruleset/repository/CandidateRuleRepository.java`
- Create: `src/main/java/com/pompom/ruleset/repository/GoldenTestCaseRepository.java`

**Interfaces:**
- Consumes: Domain entities from Task 1
- Produces: JPA repositories with custom queries

- [ ] **Step 1: Create RuleRepository**

```java
package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.Rule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface RuleRepository extends JpaRepository<Rule, UUID> {
    
    Optional<Rule> findByRuleCode(String ruleCode);
    
    @Query("SELECT r FROM Rule r WHERE r.active = true AND r.category = :category ORDER BY r.severity")
    List<Rule> findActiveByCategory(@Param("category") Rule.RuleCategory category);
    
    @Query("SELECT r FROM Rule r WHERE r.active = true AND r.severity IN :severities")
    List<Rule> findActiveBySeverities(@Param("severities") List<Rule.RuleSeverity> severities);
    
    List<Rule> findByActiveTrue();
}
```

- [ ] **Step 2: Create ConceptValidationRepository**

```java
package com.pompom.ruleset.repository;

import com.pompom.ruleset.domain.ConceptValidation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ConceptValidationRepository extends JpaRepository<ConceptValidation, UUID> {
    
    Optional<ConceptValidation> findByExternalConceptId(String externalConceptId);
    
    List<ConceptValidation> findByApprovedTrue();
    
    List<ConceptValidation> findByApprovedFalse();
    
    @Query("SELECT cv FROM ConceptValidation cv WHERE cv.createdAt >= :since ORDER BY cv.createdAt DESC")
    List<ConceptValidation> findRecentValidations(Instant since);
    
    @Query("SELECT COUNT(cv) FROM ConceptValidation cv WHERE cv.approved = :approved AND cv.createdAt >= :since")
    long countByApprovedSince(boolean approved, Instant since);
}
```

- [ ] **Step 3: Create remaining repositories**

Create similar repository interfaces for:
- `RuleEvaluationRepository`
- `PerformanceScoreRepository`
- `CandidateRuleRepository`
- `GoldenTestCaseRepository`

- [ ] **Step 4: Write repository integration test**

Create `src/test/java/com/pompom/ruleset/repository/RuleRepositoryTest.java`:

```java
@SpringBootTest
@Testcontainers
class RuleRepositoryTest {
    
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:15")
        .withDatabaseName("test")
        .withUsername("test")
        .withPassword("test");
    
    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }
    
    @Autowired
    private RuleRepository ruleRepository;
    
    @Test
    void testSaveAndFindRule() {
        Rule rule = Rule.builder()
            .ruleCode("TEST_001")
            .name("Test Rule")
            .category(Rule.RuleCategory.CONCEPT)
            .severity(Rule.RuleSeverity.HIGH)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of("key", "value"))
            .evidenceLevel(Rule.EvidenceLevel.THEORETICAL)
            .active(true)
            .build();
        
        Rule saved = ruleRepository.save(rule);
        
        Optional<Rule> found = ruleRepository.findByRuleCode("TEST_001");
        assertTrue(found.isPresent());
        assertEquals("Test Rule", found.get().getName());
    }
}
```

- [ ] **Step 5: Run test**

```bash
./mvnw test -Dtest=RuleRepositoryTest
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/main/java/com/pompom/ruleset/repository/
git add src/test/java/com/pompom/ruleset/repository/
git commit -m "feat: add JPA repositories for ruleset entities"
```

---

## Task 3: Rule Evaluation Engine - Core

**Files:**
- Create: `src/main/java/com/pompom/ruleset/engine/RuleEvaluator.java`
- Create: `src/main/java/com/pompom/ruleset/engine/CodeEvaluator.java`
- Create: `src/main/java/com/pompom/ruleset/engine/LlmEvaluator.java`
- Create: `src/main/java/com/pompom/ruleset/engine/RuleResult.java`

**Interfaces:**
- Consumes: Rule entity, ConceptValidationRequest
- Produces: RuleResult with pass/fail and score

- [ ] **Step 1: Create RuleResult value object**

```java
package com.pompom.ruleset.engine;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RuleResult {
    private Boolean passed;
    private BigDecimal score;
    private String reason;
    private Map<String, Object> details;
    
    public static RuleResult pass(String reason) {
        return RuleResult.builder()
            .passed(true)
            .score(BigDecimal.valueOf(100.0))
            .reason(reason)
            .build();
    }
    
    public static RuleResult fail(String reason) {
        return RuleResult.builder()
            .passed(false)
            .score(BigDecimal.ZERO)
            .reason(reason)
            .build();
    }
    
    public static RuleResult warn(String reason) {
        return RuleResult.builder()
            .passed(false)
            .score(BigDecimal.valueOf(50.0))
            .reason(reason)
            .build();
    }
    
    public static RuleResult score(boolean passed, double score, String reason) {
        return RuleResult.builder()
            .passed(passed)
            .score(BigDecimal.valueOf(score))
            .reason(reason)
            .build();
    }
}
```

- [ ] **Step 2: Create RuleEvaluator interface**

```java
package com.pompom.ruleset.engine;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.Rule;

public interface RuleEvaluator {
    
    /**
     * Evaluate a rule against a concept.
     * 
     * @param rule The rule to evaluate
     * @param request The concept validation request
     * @return RuleResult with pass/fail and reasoning
     */
    RuleResult evaluate(Rule rule, ConceptValidationRequest request);
    
    /**
     * Check if this evaluator supports the given rule.
     */
    boolean supports(Rule rule);
}
```

- [ ] **Step 3: Create CodeEvaluator stub**

```java
package com.pompom.ruleset.engine;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.Rule;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class CodeEvaluator implements RuleEvaluator {
    
    @Override
    public RuleResult evaluate(Rule rule, ConceptValidationRequest request) {
        log.debug("Evaluating rule {} with CODE evaluator", rule.getRuleCode());
        
        // Dispatch to specific rule implementation
        return switch (rule.getRuleCode()) {
            case "CONCEPT_001_IMMEDIATE_ANOMALY" -> evaluateImmediateAnomaly(rule, request);
            case "BEAT_003_STORY_DETACHED_GAP" -> evaluateStoryDetachedGap(rule, request);
            case "MOTION_001_MEANINGFUL_MOTION" -> evaluateMeaningfulMotion(rule, request);
            case "PROMPT_001_OVER_CONSTRAINT" -> evaluateOverConstraint(rule, request);
            default -> {
                log.warn("No CODE evaluator for rule {}", rule.getRuleCode());
                yield RuleResult.pass("No code evaluator implemented");
            }
        };
    }
    
    @Override
    public boolean supports(Rule rule) {
        return rule.getEvaluationType() == Rule.EvaluationType.CODE ||
               rule.getEvaluationType() == Rule.EvaluationType.HYBRID;
    }
    
    private RuleResult evaluateImmediateAnomaly(Rule rule, ConceptValidationRequest request) {
        String concept = request.getConceptText().toLowerCase();
        
        // Positive signals
        boolean hasVisualAnomaly = 
            concept.contains("giant") || concept.contains("huge") ||
            concept.contains("tiny") || concept.contains("upside down") ||
            concept.contains("floating") || concept.contains("upward") ||
            concept.contains("dirty") || concept.contains("clean") ||
            concept.contains("reversed") || concept.contains("backward");
        
        // Negative signals
        boolean mightBeSubtle =
            concept.contains("slowly") || concept.contains("gradually") ||
            concept.contains("eventually") || concept.contains("later");
        
        if (!hasVisualAnomaly) {
            return RuleResult.fail("No immediate visual anomaly detected in concept");
        }
        
        if (mightBeSubtle) {
            return RuleResult.warn("Anomaly may be gradual rather than immediate");
        }
        
        return RuleResult.pass("Visual anomaly is immediate");
    }
    
    private RuleResult evaluateStoryDetachedGap(Rule rule, ConceptValidationRequest request) {
        String concept = request.getConceptText().toLowerCase();
        
        boolean hasDetachedScenery =
            (concept.contains("landscape") || concept.contains("scenery") || 
             concept.contains("pan to") || concept.contains("cut to")) &&
            !concept.contains("relevant") && !concept.contains("related");
        
        boolean hasUnrelatedInsert =
            concept.contains("meanwhile") || concept.contains("elsewhere") ||
            concept.contains("unrelated");
        
        if (hasDetachedScenery || hasUnrelatedInsert) {
            return RuleResult.fail("Concept includes story-detached elements");
        }
        
        return RuleResult.pass("All elements are story-relevant");
    }
    
    private RuleResult evaluateMeaningfulMotion(Rule rule, ConceptValidationRequest request) {
        String concept = request.getConceptText().toLowerCase();
        
        boolean hasLongPauses =
            concept.contains("long pause") || concept.contains("wait") ||
            concept.contains("static for") || concept.contains("freeze");
        
        boolean hasEducationalPause =
            concept.contains("reads") || concept.contains("learning") ||
            concept.contains("educational moment");
        
        boolean hasFakeWinPause =
            concept.contains("realizes") || concept.contains("fake win") ||
            concept.contains("brief celebration");
        
        if (hasLongPauses && !hasEducationalPause && !hasFakeWinPause) {
            return RuleResult.warn("Concept may include unmotivated static moments");
        }
        
        return RuleResult.pass("Motion/progression pacing is appropriate");
    }
    
    private RuleResult evaluateOverConstraint(Rule rule, ConceptValidationRequest request) {
        // This would evaluate prompt text, not concept text
        // For now, stub pass
        return RuleResult.pass("Over-constraint check requires prompt text");
    }
}
```

- [ ] **Step 4: Write test for CodeEvaluator**

```java
@SpringBootTest
class CodeEvaluatorTest {
    
    @Autowired
    private CodeEvaluator codeEvaluator;
    
    @Test
    void testImmediateAnomalyPass() {
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .evaluationType(Rule.EvaluationType.CODE)
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Giant spoon that gets bigger with every pour")
            .build();
        
        RuleResult result = codeEvaluator.evaluate(rule, request);
        
        assertTrue(result.getPassed());
        assertThat(result.getReason()).contains("immediate");
    }
    
    @Test
    void testImmediateAnomalyFail() {
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .evaluationType(Rule.EvaluationType.CODE)
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Door that eventually opens after pushing")
            .build();
        
        RuleResult result = codeEvaluator.evaluate(rule, request);
        
        assertFalse(result.getPassed());
    }
}
```

- [ ] **Step 5: Run test**

```bash
./mvnw test -Dtest=CodeEvaluatorTest
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/main/java/com/pompom/ruleset/engine/
git add src/test/java/com/pompom/ruleset/engine/
git commit -m "feat: implement code-based rule evaluation engine"
```

---

## Task 4: LLM Integration

**Files:**
- Create: `src/main/java/com/pompom/ruleset/engine/LlmEvaluator.java`
- Create: `src/main/java/com/pompom/ruleset/config/OpenAiConfig.java`
- Test: `src/test/java/com/pompom/ruleset/engine/LlmEvaluatorTest.java`

**Interfaces:**
- Consumes: Rule with LLM prompt template, ConceptValidationRequest
- Produces: RuleResult from OpenAI analysis

- [ ] **Step 1: Create OpenAI configuration**

```java
package com.pompom.ruleset.config;

import com.theokanning.openai.service.OpenAiService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;

@Configuration
public class OpenAiConfig {
    
    @Value("${openai.api-key}")
    private String apiKey;
    
    @Value("${openai.timeout-seconds:30}")
    private int timeoutSeconds;
    
    @Bean
    public OpenAiService openAiService() {
        return new OpenAiService(apiKey, Duration.ofSeconds(timeoutSeconds));
    }
}
```

- [ ] **Step 2: Implement LlmEvaluator**

```java
package com.pompom.ruleset.engine;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.domain.Rule;
import com.theokanning.openai.completion.chat.ChatCompletionRequest;
import com.theokanning.openai.completion.chat.ChatMessage;
import com.theokanning.openai.service.OpenAiService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
@RequiredArgsConstructor
public class LlmEvaluator implements RuleEvaluator {
    
    private final OpenAiService openAiService;
    private final ObjectMapper objectMapper;
    
    @Value("${openai.model:gpt-4-turbo-preview}")
    private String model;
    
    @Value("${openai.temperature:0.3}")
    private double temperature;
    
    @Value("${openai.max-tokens:1000}")
    private int maxTokens;
    
    @Override
    public RuleResult evaluate(Rule rule, ConceptValidationRequest request) {
        log.debug("Evaluating rule {} with LLM evaluator", rule.getRuleCode());
        
        try {
            String prompt = buildPrompt(rule, request);
            String response = callOpenAi(prompt);
            return parseResponse(response);
        } catch (Exception e) {
            log.error("LLM evaluation failed for rule {}", rule.getRuleCode(), e);
            return RuleResult.warn("LLM evaluation failed: " + e.getMessage());
        }
    }
    
    @Override
    public boolean supports(Rule rule) {
        return rule.getEvaluationType() == Rule.EvaluationType.LLM ||
               rule.getEvaluationType() == Rule.EvaluationType.HYBRID;
    }
    
    private String buildPrompt(Rule rule, ConceptValidationRequest request) {
        Map<String, Object> yamlDef = rule.getYamlDefinition();
        String promptTemplate = (String) yamlDef.get("prompt");
        
        if (promptTemplate == null) {
            throw new IllegalArgumentException("Rule " + rule.getRuleCode() + " has no prompt template");
        }
        
        // Simple template substitution
        return promptTemplate
            .replace("{{conceptText}}", request.getConceptText())
            .replace("{{intent}}", request.getIntent() != null ? request.getIntent().toString() : "UNKNOWN");
    }
    
    private String callOpenAi(String prompt) {
        ChatCompletionRequest completionRequest = ChatCompletionRequest.builder()
            .model(model)
            .temperature(temperature)
            .maxTokens(maxTokens)
            .messages(List.of(
                new ChatMessage("system", "You are a creative concept evaluator for short-form video content. Respond ONLY with valid JSON."),
                new ChatMessage("user", prompt)
            ))
            .build();
        
        return openAiService.createChatCompletion(completionRequest)
            .getChoices()
            .get(0)
            .getMessage()
            .getContent();
    }
    
    private RuleResult parseResponse(String response) throws Exception {
        // Extract JSON from response (may be wrapped in markdown)
        String json = response;
        if (response.contains("```json")) {
            json = response.substring(
                response.indexOf("```json") + 7,
                response.lastIndexOf("```")
            ).trim();
        } else if (response.contains("```")) {
            json = response.substring(
                response.indexOf("```") + 3,
                response.lastIndexOf("```")
            ).trim();
        }
        
        JsonNode node = objectMapper.readTree(json);
        
        double score = node.has("score") ? node.get("score").asDouble() : 0.0;
        String reason = node.has("reason") ? node.get("reason").asText() : "No reason provided";
        
        boolean passed = score >= 70.0;
        
        return RuleResult.builder()
            .passed(passed)
            .score(BigDecimal.valueOf(score))
            .reason(reason)
            .details(objectMapper.convertValue(node, Map.class))
            .build();
    }
}
```

- [ ] **Step 3: Write LLM test (with mock)**

```java
@SpringBootTest
class LlmEvaluatorTest {
    
    @MockBean
    private OpenAiService openAiService;
    
    @Autowired
    private LlmEvaluator llmEvaluator;
    
    @Test
    void testLlmEvaluationPass() {
        // Mock OpenAI response
        ChatCompletionResult mockResult = new ChatCompletionResult();
        ChatCompletionChoice choice = new ChatCompletionChoice();
        ChatMessage message = new ChatMessage();
        message.setContent("{\"score\": 85.0, \"reason\": \"Strong immediate anomaly\"}");
        choice.setMessage(message);
        mockResult.setChoices(List.of(choice));
        
        when(openAiService.createChatCompletion(any())).thenReturn(mockResult);
        
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_002_ONE_DOMINANT_MECHANIC")
            .evaluationType(Rule.EvaluationType.LLM)
            .yamlDefinition(Map.of("prompt", "Evaluate: {{conceptText}}"))
            .build();
        
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .conceptText("Giant spoon grows with each pour")
            .build();
        
        RuleResult result = llmEvaluator.evaluate(rule, request);
        
        assertTrue(result.getPassed());
        assertEquals(85.0, result.getScore().doubleValue(), 0.1);
    }
}
```

- [ ] **Step 4: Run test**

```bash
./mvnw test -Dtest=LlmEvaluatorTest
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/pompom/ruleset/engine/LlmEvaluator.java
git add src/main/java/com/pompom/ruleset/config/OpenAiConfig.java
git add src/test/java/com/pompom/ruleset/engine/LlmEvaluatorTest.java
git commit -m "feat: implement LLM-based rule evaluation with OpenAI"
```

---

## Task 5: Concept Validation Service

**Files:**
- Create: `src/main/java/com/pompom/ruleset/service/ConceptValidationService.java`
- Test: `src/test/java/com/pompom/ruleset/service/ConceptValidationServiceTest.java`

**Interfaces:**
- Consumes: ConceptValidationRequest, RuleEvaluator implementations
- Produces: ConceptValidationResponse with all rule results

- [ ] **Step 1: Implement ConceptValidationService**

```java
package com.pompom.ruleset.service;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.domain.ConceptValidation;
import com.pompom.ruleset.domain.Rule;
import com.pompom.ruleset.domain.RuleEvaluation;
import com.pompom.ruleset.engine.CodeEvaluator;
import com.pompom.ruleset.engine.LlmEvaluator;
import com.pompom.ruleset.engine.RuleResult;
import com.pompom.ruleset.repository.ConceptValidationRepository;
import com.pompom.ruleset.repository.RuleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
@RequiredArgsConstructor
public class ConceptValidationService {
    
    private final RuleRepository ruleRepository;
    private final ConceptValidationRepository validationRepository;
    private final CodeEvaluator codeEvaluator;
    private final LlmEvaluator llmEvaluator;
    
    @Transactional
    public ConceptValidationResponse validate(ConceptValidationRequest request) {
        log.info("Validating concept: {}", request.getExternalConceptId());
        
        // Load active rules
        List<Rule> rules = ruleRepository.findByActiveTrue();
        log.debug("Loaded {} active rules", rules.size());
        
        // Create validation entity
        ConceptValidation validation = ConceptValidation.builder()
            .externalConceptId(request.getExternalConceptId())
            .conceptText(request.getConceptText())
            .intent(request.getIntent())
            .build();
        
        // Evaluate each rule
        List<RuleEvaluation> evaluations = new ArrayList<>();
        for (Rule rule : rules) {
            RuleResult result = evaluateRule(rule, request);
            
            RuleEvaluation evaluation = RuleEvaluation.builder()
                .rule(rule)
                .passed(result.getPassed())
                .score(result.getScore())
                .reason(result.getReason())
                .details(result.getDetails())
                .build();
            
            validation.addRuleEvaluation(evaluation);
            evaluations.add(evaluation);
        }
        
        // Calculate overall score
        BigDecimal overallScore = calculateOverallScore(evaluations);
        validation.setOverallScore(overallScore);
        
        // Determine approval
        boolean approved = !validation.hasCriticalFailures() && 
                          overallScore.compareTo(BigDecimal.valueOf(60.0)) >= 0;
        validation.setApproved(approved);
        
        // Save
        validationRepository.save(validation);
        
        // Build response
        return buildResponse(validation);
    }
    
    private RuleResult evaluateRule(Rule rule, ConceptValidationRequest request) {
        try {
            RuleResult result = null;
            
            if (rule.getEvaluationType() == Rule.EvaluationType.CODE) {
                result = codeEvaluator.evaluate(rule, request);
            } else if (rule.getEvaluationType() == Rule.EvaluationType.LLM) {
                result = llmEvaluator.evaluate(rule, request);
            } else if (rule.getEvaluationType() == Rule.EvaluationType.HYBRID) {
                // Run both, combine results
                RuleResult codeResult = codeEvaluator.evaluate(rule, request);
                RuleResult llmResult = llmEvaluator.evaluate(rule, request);
                result = combineResults(codeResult, llmResult);
            }
            
            return result != null ? result : RuleResult.pass("No evaluator");
        } catch (Exception e) {
            log.error("Rule evaluation failed for {}", rule.getRuleCode(), e);
            return RuleResult.fail("Evaluation error: " + e.getMessage());
        }
    }
    
    private RuleResult combineResults(RuleResult code, RuleResult llm) {
        // Both must pass for HYBRID
        boolean passed = code.getPassed() && llm.getPassed();
        BigDecimal avgScore = code.getScore().add(llm.getScore())
            .divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP);
        String reason = "Code: " + code.getReason() + " | LLM: " + llm.getReason();
        
        return RuleResult.builder()
            .passed(passed)
            .score(avgScore)
            .reason(reason)
            .build();
    }
    
    private BigDecimal calculateOverallScore(List<RuleEvaluation> evaluations) {
        if (evaluations.isEmpty()) {
            return BigDecimal.ZERO;
        }
        
        BigDecimal totalScore = evaluations.stream()
            .map(RuleEvaluation::getScore)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        return totalScore.divide(
            BigDecimal.valueOf(evaluations.size()),
            2,
            RoundingMode.HALF_UP
        );
    }
    
    private ConceptValidationResponse buildResponse(ConceptValidation validation) {
        List<ConceptValidationResponse.RuleResultDto> ruleResults = validation.getRuleEvaluations().stream()
            .map(eval -> ConceptValidationResponse.RuleResultDto.builder()
                .ruleCode(eval.getRule().getRuleCode())
                .ruleName(eval.getRule().getName())
                .passed(eval.getPassed())
                .score(eval.getScore())
                .reason(eval.getReason())
                .severity(eval.getRule().getSeverity().toString())
                .build())
            .collect(Collectors.toList());
        
        List<String> criticalIssues = validation.getRuleEvaluations().stream()
            .filter(RuleEvaluation::isCriticalFailure)
            .map(eval -> eval.getRule().getName() + ": " + eval.getReason())
            .collect(Collectors.toList());
        
        List<String> warnings = validation.getRuleEvaluations().stream()
            .filter(RuleEvaluation::isWarning)
            .map(eval -> eval.getRule().getName() + ": " + eval.getReason())
            .collect(Collectors.toList());
        
        return ConceptValidationResponse.builder()
            .validationId(validation.getId())
            .approved(validation.getApproved())
            .overallScore(validation.getOverallScore())
            .ruleResults(ruleResults)
            .criticalIssues(criticalIssues)
            .warnings(warnings)
            .recommendations(generateRecommendations(validation))
            .build();
    }
    
    private List<String> generateRecommendations(ConceptValidation validation) {
        List<String> recommendations = new ArrayList<>();
        
        // Check loopability
        validation.getRuleEvaluations().stream()
            .filter(eval -> eval.getRule().getRuleCode().equals("LOOPABILITY_001_LOOP_STRUCTURE"))
            .filter(eval -> eval.getScore() != null && eval.getScore().compareTo(BigDecimal.valueOf(80)) >= 0)
            .findFirst()
            .ifPresent(eval -> recommendations.add("Strong loopability potential - consider hard cut ending"));
        
        return recommendations;
    }
}
```

- [ ] **Step 2: Write service test**

```java
@SpringBootTest
@Transactional
class ConceptValidationServiceTest {
    
    @Autowired
    private ConceptValidationService validationService;
    
    @Autowired
    private RuleRepository ruleRepository;
    
    @MockBean
    private LlmEvaluator llmEvaluator;
    
    @BeforeEach
    void setup() {
        // Insert test rule
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .name("Immediate Anomaly")
            .category(Rule.RuleCategory.CONCEPT)
            .severity(Rule.RuleSeverity.CRITICAL)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .evidenceLevel(Rule.EvidenceLevel.SUPPORTED)
            .active(true)
            .build();
        ruleRepository.save(rule);
    }
    
    @Test
    void testValidationPass() {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .externalConceptId("test-001")
            .conceptText("Giant spoon that grows with every pour")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        ConceptValidationResponse response = validationService.validate(request);
        
        assertNotNull(response.getValidationId());
        assertTrue(response.getApproved());
        assertTrue(response.getOverallScore().compareTo(BigDecimal.valueOf(60)) >= 0);
    }
    
    @Test
    void testValidationFail() {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .externalConceptId("test-002")
            .conceptText("Door that won't open when pushed")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        ConceptValidationResponse response = validationService.validate(request);
        
        assertNotNull(response.getValidationId());
        assertFalse(response.getApproved());
        assertFalse(response.getCriticalIssues().isEmpty());
    }
}
```

- [ ] **Step 3: Run test**

```bash
./mvnw test -Dtest=ConceptValidationServiceTest
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/pompom/ruleset/service/ConceptValidationService.java
git add src/test/java/com/pompom/ruleset/service/ConceptValidationServiceTest.java
git commit -m "feat: implement concept validation service with rule evaluation"
```

---

## Task 6: REST API Controllers

**Files:**
- Create: `src/main/java/com/pompom/ruleset/api/controller/ValidationController.java`
- Create: `src/main/java/com/pompom/ruleset/api/controller/PerformanceController.java`
- Test: `src/test/java/com/pompom/ruleset/api/controller/ValidationControllerTest.java`

**Interfaces:**
- Consumes: HTTP requests with DTOs
- Produces: HTTP responses with validation/performance results

- [ ] **Step 1: Create ValidationController**

```java
package com.pompom.ruleset.api.controller;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.service.ConceptValidationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/validate")
@RequiredArgsConstructor
@Slf4j
public class ValidationController {
    
    private final ConceptValidationService validationService;
    
    @PostMapping("/concept")
    public ResponseEntity<ConceptValidationResponse> validateConcept(
        @Valid @RequestBody ConceptValidationRequest request
    ) {
        log.info("POST /validate/concept - externalId: {}", request.getExternalConceptId());
        
        ConceptValidationResponse response = validationService.validate(request);
        
        return ResponseEntity.ok(response);
    }
    
    @GetMapping("/{id}")
    public ResponseEntity<ConceptValidationResponse> getValidation(
        @PathVariable UUID id
    ) {
        log.info("GET /validate/{}", id);
        
        // TODO: implement get by ID
        return ResponseEntity.notFound().build();
    }
}
```

- [ ] **Step 2: Write controller test**

```java
@SpringBootTest
@AutoConfigureMockMvc
class ValidationControllerTest {
    
    @Autowired
    private MockMvc mockMvc;
    
    @Autowired
    private ObjectMapper objectMapper;
    
    @Autowired
    private RuleRepository ruleRepository;
    
    @BeforeEach
    void setup() {
        Rule rule = Rule.builder()
            .ruleCode("CONCEPT_001_IMMEDIATE_ANOMALY")
            .name("Immediate Anomaly")
            .category(Rule.RuleCategory.CONCEPT)
            .severity(Rule.RuleSeverity.CRITICAL)
            .evaluationType(Rule.EvaluationType.CODE)
            .yamlDefinition(Map.of())
            .evidenceLevel(Rule.EvidenceLevel.SUPPORTED)
            .active(true)
            .build();
        ruleRepository.save(rule);
    }
    
    @Test
    void testValidateConceptEndpoint() throws Exception {
        ConceptValidationRequest request = ConceptValidationRequest.builder()
            .externalConceptId("api-test-001")
            .conceptText("Giant spoon grows with every pour")
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .build();
        
        mockMvc.perform(post("/validate/concept")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.validationId").exists())
            .andExpect(jsonPath("$.approved").isBoolean())
            .andExpect(jsonPath("$.overallScore").isNumber())
            .andExpect(jsonPath("$.ruleResults").isArray());
    }
}
```

- [ ] **Step 3: Run test**

```bash
./mvnw test -Dtest=ValidationControllerTest
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/main/java/com/pompom/ruleset/api/controller/
git add src/test/java/com/pompom/ruleset/api/controller/
git commit -m "feat: add REST API controllers for validation"
```

---

## Task 7: Golden Test Suite Implementation

**Files:**
- Create: `src/test/java/com/pompom/ruleset/golden/GoldenTestSuite.java`
- Create: `src/main/resources/db/changelog/002-golden-test-data.sql`

**Interfaces:**
- Consumes: GoldenTestCase entities
- Produces: Pass/fail regression test results

- [ ] **Step 1: Create golden test data migration**

Create `src/main/resources/db/changelog/002-golden-test-data.sql`:

```sql
--liquibase formatted sql

--changeset pompom:golden-positive-001
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_min_score, expected_failing_rules, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_POS_001_GIANT_SPOON',
    'POSITIVE',
    'Giant spoon that gets bigger with every pour. Kiko pours water, spoon grows. Adds ingredient, spoon grows more. Stirs, spoon is now huge. Tries to drink, spoon too big for mouth. Final: spoon fills entire kitchen.',
    'GROWTH',
    true,
    85.0,
    NULL,
    'THE canonical winner. If this fails, something is very wrong.',
    NOW()
);

--changeset pompom:golden-negative-001
INSERT INTO golden_test_cases (id, test_name, category, concept_text, intent, expected_approved, expected_max_score, expected_failing_rules, notes, created_at)
VALUES (
    gen_random_uuid(),
    'GOLDEN_NEG_001_DOOR_PUSH',
    'NEGATIVE',
    'Characters try to open a stuck door. Kiko pushes door, doesn''t open. Kiko pushes harder. Mimi joins, both push. Arda joins, all three push. Cut to scenic landscape for 2 seconds. Back to door, everyone pushing. Door finally opens.',
    'GROWTH',
    false,
    50.0,
    '["CONCEPT_001_IMMEDIATE_ANOMALY", "BEAT_002_ACTIVITY_NOT_PROGRESSION", "BEAT_003_STORY_DETACHED_GAP"]'::jsonb,
    'Canonical failure: no immediate anomaly, activity not progression, detached scenic insert.',
    NOW()
);

-- Add more golden cases...
```

- [ ] **Step 2: Implement GoldenTestSuite**

```java
package com.pompom.ruleset.golden;

import com.pompom.ruleset.api.dto.ConceptValidationRequest;
import com.pompom.ruleset.api.dto.ConceptValidationResponse;
import com.pompom.ruleset.domain.GoldenTestCase;
import com.pompom.ruleset.repository.GoldenTestCaseRepository;
import com.pompom.ruleset.service.ConceptValidationService;
import lombok.extern.slf4j.Slf4j;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@Slf4j
public class GoldenTestSuite {
    
    @Autowired
    private GoldenTestCaseRepository goldenRepo;
    
    @Autowired
    private ConceptValidationService validationService;
    
    @Test
    public void testAllGoldenCases() {
        List<GoldenTestCase> goldenCases = goldenRepo.findAll();
        
        assertTrue(goldenCases.size() >= 2, "Golden test suite must have at least 2 cases");
        
        List<String> failures = new ArrayList<>();
        
        for (GoldenTestCase testCase : goldenCases) {
            log.info("Testing golden case: {}", testCase.getTestName());
            
            ConceptValidationRequest request = ConceptValidationRequest.builder()
                .conceptText(testCase.getConceptText())
                .intent(testCase.getIntent())
                .build();
            
            ConceptValidationResponse response = validationService.validate(request);
            
            // Check approval expectation
            if (!testCase.getExpectedApproved().equals(response.getApproved())) {
                failures.add(testCase.getTestName() + ": Expected approved=" + 
                    testCase.getExpectedApproved() + " but got " + response.getApproved());
            }
            
            // Check score range
            if (testCase.getExpectedMinScore() != null) {
                if (response.getOverallScore().compareTo(testCase.getExpectedMinScore()) < 0) {
                    failures.add(testCase.getTestName() + ": Score " + response.getOverallScore() +
                        " below minimum " + testCase.getExpectedMinScore());
                }
            }
            
            if (testCase.getExpectedMaxScore() != null) {
                if (response.getOverallScore().compareTo(testCase.getExpectedMaxScore()) > 0) {
                    failures.add(testCase.getTestName() + ": Score " + response.getOverallScore() +
                        " above maximum " + testCase.getExpectedMaxScore());
                }
            }
        }
        
        if (!failures.isEmpty()) {
            fail("Golden test suite failures:\n" + String.join("\n", failures));
        }
        
        log.info("Golden test suite PASSED: {} cases", goldenCases.size());
    }
}
```

- [ ] **Step 3: Run golden test suite**

```bash
./mvnw test -Dtest=GoldenTestSuite
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/test/java/com/pompom/ruleset/golden/
git add src/main/resources/db/changelog/002-golden-test-data.sql
git commit -m "feat: implement golden test suite for regression prevention"
```

---

## Task 8: Performance Analysis Service (Stub)

**Files:**
- Create: `src/main/java/com/pompom/ruleset/service/PerformanceAnalysisService.java`
- Create: `src/main/java/com/pompom/ruleset/api/controller/PerformanceController.java`

**Interfaces:**
- Consumes: PerformanceAnalysisRequest with metrics
- Produces: PerformanceScore with dimension scores and classification

- [ ] **Step 1: Implement PerformanceAnalysisService stub**

```java
package com.pompom.ruleset.service;

import com.pompom.ruleset.api.dto.PerformanceAnalysisRequest;
import com.pompom.ruleset.api.dto.PerformanceAnalysisResponse;
import com.pompom.ruleset.domain.PerformanceScore;
import com.pompom.ruleset.repository.PerformanceScoreRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
@Slf4j
@RequiredArgsConstructor
public class PerformanceAnalysisService {
    
    private final PerformanceScoreRepository scoreRepository;
    
    @Transactional
    public PerformanceAnalysisResponse analyze(PerformanceAnalysisRequest request) {
        log.info("Analyzing performance for video: {}", request.getExternalVideoId());
        
        // Calculate derived metrics
        BigDecimal avgWatchRatio = calculateAvgWatchRatio(
            request.getMetrics().getAvgWatchTimeSeconds(),
            request.getDurationSeconds()
        );
        
        BigDecimal entryProxy = calculateEntryProxy(
            request.getMetrics().getThreeSecondViews(),
            request.getMetrics().getReach()
        );
        
        BigDecimal viewsPerViewer = calculateViewsPerViewer(
            request.getMetrics().getViews(),
            request.getMetrics().getUniqueViewers()
        );
        
        // Build performance score entity
        PerformanceScore score = PerformanceScore.builder()
            .externalVideoId(request.getExternalVideoId())
            .platform(request.getPlatform())
            .intent(request.getIntent())
            .views(request.getMetrics().getViews())
            .likes(request.getMetrics().getLikes())
            .comments(request.getMetrics().getComments())
            .shares(request.getMetrics().getShares())
            .saves(request.getMetrics().getSaves())
            .reach(request.getMetrics().getReach())
            .impressions(request.getMetrics().getImpressions())
            .avgWatchSeconds(request.getMetrics().getAvgWatchTimeSeconds())
            .durationSeconds(request.getDurationSeconds())
            .completionRate(request.getMetrics().getCompletionRate())
            .threeSecondViews(request.getMetrics().getThreeSecondViews())
            .uniqueViewers(request.getMetrics().getUniqueViewers())
            .avgWatchRatio(avgWatchRatio)
            .entryProxy(entryProxy)
            .viewsPerViewer(viewsPerViewer)
            .endRetentionRate(request.getMetrics().getCompletionRate())
            .collectedAt(java.time.Instant.now())
            .timeSincePublishHours(request.getTimeSincePublishHours())
            .build();
        
        // Calculate dimension scores (stub - will be implemented in next phase)
        calculateDimensionScores(score, avgWatchRatio, entryProxy, viewsPerViewer);
        
        // Classify performance
        classifyPerformance(score, request.getPlatform());
        
        // Save
        scoreRepository.save(score);
        
        // Build response
        return buildPerformanceResponse(score);
    }
    
    private BigDecimal calculateAvgWatchRatio(BigDecimal avgWatch, BigDecimal duration) {
        if (duration == null || duration.compareTo(BigDecimal.ZERO) == 0) {
            return BigDecimal.ZERO;
        }
        return avgWatch.divide(duration, 4, RoundingMode.HALF_UP);
    }
    
    private BigDecimal calculateEntryProxy(Long threeSecViews, Long reach) {
        if (reach == null || reach == 0) {
            return BigDecimal.ZERO;
        }
        return BigDecimal.valueOf(threeSecViews)
            .divide(BigDecimal.valueOf(reach), 4, RoundingMode.HALF_UP);
    }
    
    private BigDecimal calculateViewsPerViewer(Long views, Long uniqueViewers) {
        if (uniqueViewers == null || uniqueViewers == 0) {
            return BigDecimal.ONE;
        }
        return BigDecimal.valueOf(views)
            .divide(BigDecimal.valueOf(uniqueViewers), 2, RoundingMode.HALF_UP);
    }
    
    private void calculateDimensionScores(PerformanceScore score, 
                                          BigDecimal avgWatchRatio,
                                          BigDecimal entryProxy,
                                          BigDecimal viewsPerViewer) {
        // Stub implementation - basic heuristics
        
        // Hook strength from entry proxy
        BigDecimal hookStrength = entryProxy.compareTo(BigDecimal.valueOf(0.75)) >= 0 ?
            BigDecimal.valueOf(90.0) : BigDecimal.valueOf(60.0);
        score.setHookStrength(hookStrength);
        
        // Loopability from avgWatchRatio and viewsPerViewer
        BigDecimal loopability = (avgWatchRatio.compareTo(BigDecimal.ONE) >= 0 &&
                                  viewsPerViewer.compareTo(BigDecimal.valueOf(2.0)) >= 0) ?
            BigDecimal.valueOf(85.0) : BigDecimal.valueOf(50.0);
        score.setLoopabilityScore(loopability);
        
        // Other dimensions - stub values
        score.setProgressionScore(BigDecimal.valueOf(70.0));
        score.setAttemptDiversityScore(BigDecimal.valueOf(70.0));
        score.setFinalPayoff(BigDecimal.valueOf(70.0));
        
        // Overall quality
        BigDecimal overall = hookStrength.add(loopability)
            .divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP);
        score.setOverallQuality(overall);
    }
    
    private void classifyPerformance(PerformanceScore score, PerformanceScore.Platform platform) {
        BigDecimal entryProxy = score.getEntryProxy();
        
        if (platform == PerformanceScore.Platform.META_FACEBOOK) {
            if (entryProxy.compareTo(BigDecimal.valueOf(0.80)) >= 0) {
                score.setClassification(PerformanceScore.PerformanceClassification.STRONG);
            } else if (entryProxy.compareTo(BigDecimal.valueOf(0.75)) >= 0) {
                score.setClassification(PerformanceScore.PerformanceClassification.VIABLE);
            } else {
                score.setClassification(PerformanceScore.PerformanceClassification.WEAK);
            }
        } else {
            score.setClassification(PerformanceScore.PerformanceClassification.VIABLE);
        }
    }
    
    private PerformanceAnalysisResponse buildPerformanceResponse(PerformanceScore score) {
        Map<String, BigDecimal> dimensions = new HashMap<>();
        dimensions.put("hookStrength", score.getHookStrength());
        dimensions.put("progressionScore", score.getProgressionScore());
        dimensions.put("attemptDiversityScore", score.getAttemptDiversityScore());
        dimensions.put("finalPayoff", score.getFinalPayoff());
        dimensions.put("loopabilityScore", score.getLoopabilityScore());
        
        PerformanceAnalysisResponse.DerivedMetricsDto derived = 
            PerformanceAnalysisResponse.DerivedMetricsDto.builder()
                .avgWatchRatio(score.getAvgWatchRatio())
                .entryProxy(score.getEntryProxy())
                .viewsPerViewer(score.getViewsPerViewer())
                .endRetentionRate(score.getEndRetentionRate())
                .build();
        
        List<String> insights = generateInsights(score);
        
        return PerformanceAnalysisResponse.builder()
            .performanceId(score.getId())
            .overallQuality(score.getOverallQuality())
            .classification(score.getClassification())
            .wavePattern(score.getWavePattern())
            .dimensionScores(dimensions)
            .derivedMetrics(derived)
            .insights(insights)
            .build();
    }
    
    private List<String> generateInsights(PerformanceScore score) {
        List<String> insights = new ArrayList<>();
        
        if (score.getAvgWatchRatio().compareTo(BigDecimal.ONE) > 0) {
            insights.add("Exceptional loopability: avg watch > duration suggests replay");
        }
        
        if (score.getEntryProxy().compareTo(BigDecimal.valueOf(0.75)) >= 0) {
            insights.add("Strong entry proxy - hook works immediately");
        }
        
        if (score.getViewsPerViewer().compareTo(BigDecimal.valueOf(2.0)) >= 0) {
            insights.add("High views/viewer ratio indicates replay behavior");
        }
        
        return insights;
    }
}
```

- [ ] **Step 2: Create PerformanceController**

```java
package com.pompom.ruleset.api.controller;

import com.pompom.ruleset.api.dto.PerformanceAnalysisRequest;
import com.pompom.ruleset.api.dto.PerformanceAnalysisResponse;
import com.pompom.ruleset.service.PerformanceAnalysisService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/performance")
@RequiredArgsConstructor
@Slf4j
public class PerformanceController {
    
    private final PerformanceAnalysisService analysisService;
    
    @PostMapping("/analyze")
    public ResponseEntity<PerformanceAnalysisResponse> analyzePerformance(
        @Valid @RequestBody PerformanceAnalysisRequest request
    ) {
        log.info("POST /performance/analyze - videoId: {}", request.getExternalVideoId());
        
        PerformanceAnalysisResponse response = analysisService.analyze(request);
        
        return ResponseEntity.ok(response);
    }
}
```

- [ ] **Step 3: Write basic test**

```java
@SpringBootTest
class PerformanceAnalysisServiceTest {
    
    @Autowired
    private PerformanceAnalysisService analysisService;
    
    @Test
    void testBasicAnalysis() {
        PerformanceAnalysisRequest request = PerformanceAnalysisRequest.builder()
            .externalVideoId("perf-test-001")
            .platform(PerformanceScore.Platform.META_FACEBOOK)
            .intent(ConceptValidation.ContentIntent.GROWTH)
            .durationSeconds(BigDecimal.valueOf(15.0))
            .metrics(PerformanceAnalysisRequest.MetricsDto.builder()
                .views(25000L)
                .reach(31000L)
                .threeSecondViews(24500L)
                .avgWatchTimeSeconds(BigDecimal.valueOf(16.8))
                .uniqueViewers(8500L)
                .build())
            .timeSincePublishHours(48)
            .build();
        
        PerformanceAnalysisResponse response = analysisService.analyze(request);
        
        assertNotNull(response.getPerformanceId());
        assertNotNull(response.getClassification());
        assertTrue(response.getDerivedMetrics().getAvgWatchRatio().compareTo(BigDecimal.ONE) > 0);
    }
}
```

- [ ] **Step 4: Run test**

```bash
./mvnw test -Dtest=PerformanceAnalysisServiceTest
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/main/java/com/pompom/ruleset/service/PerformanceAnalysisService.java
git add src/main/java/com/pompom/ruleset/api/controller/PerformanceController.java
git add src/test/java/com/pompom/ruleset/service/PerformanceAnalysisServiceTest.java
git commit -m "feat: implement performance analysis service with basic metrics"
```

---

## Task 9: Integration with Creative Intelligence Backend

**Files:**
- Create: `docs/INTEGRATION_GUIDE.md`
- Create: Example client code snippet

**Interfaces:**
- Documents REST API integration patterns
- Provides example Java HTTP client code

- [ ] **Step 1: Create integration guide**

Create `docs/INTEGRATION_GUIDE.md`:

```markdown
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
```

- [ ] **Step 2: Commit documentation**

```bash
git add docs/INTEGRATION_GUIDE.md
git commit -m "docs: add integration guide for Creative Intelligence backend"
```

---

## Task 10: Documentation and README

**Files:**
- Update: `README.md`
- Update: `docs/ARCHITECTURE.md`
- Create: `docs/QUICKSTART.md`

**Interfaces:**
- Provides complete project documentation
- Enables new developers to onboard quickly

- [ ] **Step 1: Update main README**

Update `README.md` with deployment instructions, API examples, and links to other docs.

- [ ] **Step 2: Create QUICKSTART.md**

```markdown
# Quick Start

## Prerequisites

- Java 21+
- PostgreSQL 15+
- OpenAI API key

## Setup

1. **Clone repository**

```bash
git clone <repo-url>
cd pompom-ruleset-engine
```

2. **Configure environment**

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. **Start PostgreSQL**

```bash
docker run -d \
  --name ruleset-postgres \
  -e POSTGRES_DB=pompom_ruleset \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgres:15
```

4. **Run migrations**

```bash
./mvnw liquibase:update
```

5. **Start application**

```bash
./mvnw spring-boot:run
```

6. **Test API**

```bash
curl -X POST http://localhost:8081/validate/concept \
  -H "Content-Type: application/json" \
  -d '{
    "conceptText": "Giant spoon that grows with every pour",
    "intent": "GROWTH"
  }'
```

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Read [RULE_DEFINITIONS.md](RULE_DEFINITIONS.md) for all rules
- Read [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) to connect with Creative Intelligence
```

- [ ] **Step 3: Commit**

```bash
git add README.md docs/QUICKSTART.md
git commit -m "docs: complete project documentation"
```

---

## Final Verification

- [ ] **Run all tests**

```bash
./mvnw clean test
```

Expected: All tests PASS

- [ ] **Run golden test suite**

```bash
./mvnw test -Dtest=GoldenTestSuite
```

Expected: Golden suite PASS

- [ ] **Start application**

```bash
./mvnw spring-boot:run
```

Expected: Application starts, no errors

- [ ] **Smoke test API**

```bash
curl -X POST http://localhost:8081/validate/concept \
  -H "Content-Type: application/json" \
  -d '{"conceptText": "Test concept", "intent": "GROWTH"}'
```

Expected: HTTP 200, JSON response

- [ ] **Check actuator health**

```bash
curl http://localhost:8081/actuator/health
```

Expected: `{"status":"UP"}`

---

## Implementation Complete

At this point, you have:

✅ Complete database schema with migrations
✅ Domain model for all entities
✅ Repository layer with JPA
✅ Rule evaluation engine (code + LLM)
✅ Concept validation service
✅ Performance analysis service (basic)
✅ REST API controllers
✅ Golden test suite for regression prevention
✅ Integration documentation
✅ Complete project documentation

**Next Phase (Future):**
- Implement all 22 rules from RULE_DEFINITIONS.md
- Build learning engine for correlation detection
- Add wave detection logic
- Implement candidate rule workflow
- Build admin UI for rule management

---

## Execution Options

**Option 1: Subagent-Driven (recommended)**
Use `superpowers:subagent-driven-development` to dispatch fresh subagent per task with review between tasks.

**Option 2: Inline Execution**
Use `superpowers:executing-plans` to execute tasks in current session with batch checkpoints.
