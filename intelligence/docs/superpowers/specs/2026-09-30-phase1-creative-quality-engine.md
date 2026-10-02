# Phase 1: Creative Quality Engine - Detailed Specification

**Date:** September 30, 2026  
**Version:** 1.0  
**Status:** Draft  
**Parent:** Master Architecture v1.0

---

## Goal

Build a prompt validation system that catches Opa, Arda, and Kiko failures **before** spending render credits.

**Success Criteria:**
- ✅ Kiko "Slippery/Rough" → BLOCKED (static state dominance 42%)
- ✅ Opa "Old/New" → BLOCKED (repetitive action)
- ✅ Arda "Sharp/Blunt" → BLOCKED (cycle repetition)
- ✅ Mimi "Clean/Dirty" → RENDER_READY (score >92, zero blockers)

**Target Timeline:** 2-3 weeks

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CREATIVE QUALITY ENGINE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FRONTEND (Angular 21)                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │ Prompt Create │→│ Validation    │→│ Fix Loop      │  │
│  │ - Concept     │  │ Results       │  │ - Export      │  │
│  │ - Full Prompt │  │ - Timeline    │  │ - Import      │  │
│  └───────────────┘  │ - Scores      │  │ - Regression  │  │
│                     │ - Evidence    │  └───────────────┘  │
│                     └───────────────┘                      │
│                            │                               │
├────────────────────────────┼───────────────────────────────┤
│  BACKEND (Spring Boot)     │                               │
│  ┌────────────────────────┼──────────────────────┐        │
│  │ Content Domain         │   Validation Domain  │        │
│  │ - ContentEntity        │   - ValidationRun    │        │
│  │ - PromptVersion        │   - FailedRule       │        │
│  │ - ConceptValidation    │   - RenderGate       │        │
│  └────────────────────────┴──────────────────────┘        │
│              │                      │                      │
│              └──────────┬───────────┘                      │
│                         │                                  │
│  ┌─────────────────────┴────────────────────┐             │
│  │         LLM Provider Abstraction          │             │
│  │  OpenAI │ Claude │ Gemini │ Ollama        │             │
│  └─────────────────────┬────────────────────┘             │
│                        │                                   │
├────────────────────────┼───────────────────────────────────┤
│  ML SERVICE (FastAPI)  │                                   │
│  ┌────────────────────┼───────────────────────┐           │
│  │  LLM Parser        │   Rule Engine          │           │
│  │  - Prompt → IR     │   - 11 Families        │           │
│  │  - Beat Extract    │   - Evidence Extract   │           │
│  │  - Confidence      │   - Weighted Scoring   │           │
│  └────────────────────┴───────────────────────┘           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  STORAGE                                                    │
│  PostgreSQL          Local Filesystem        YAML Rules    │
│  - contents          - prompt-v*.txt         - families/   │
│  - prompt_versions   - validation-*.json     - criteria/   │
│  - validation_runs   - reference/            - thresholds/ │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Content Domain (Backend)

**ContentEntity** - Root aggregate for entire content lifecycle

```java
@Entity
@Table(name = "contents")
public class ContentEntity {
    @Id
    private UUID id;
    
    private String title;
    
    @ManyToOne
    private CharacterEntity character;
    
    @Enumerated(EnumType.STRING)
    private SeriesType seriesType;
    
    private Integer targetDurationSeconds;
    
    @Convert(converter = StringArrayConverter.class)
    private List<String> targetPlatforms;
    
    @Convert(converter = StringArrayConverter.class)
    private List<String> learningWords;
    
    private String creativeEngine;
    
    @Enumerated(EnumType.STRING)
    private ContentStatus status;
    
    private Integer currentPromptVersion;
    
    @Version
    private Long entityVersion;
    
    private Instant createdAt;
    private Instant updatedAt;
}

enum SeriesType {
    OPPOSITES,
    WHATS_WRONG,
    DISCOVERY,
    FEELINGS,
    MUSIC,
    STORIES,
    SOCIAL_REEL
}

enum ContentStatus {
    IDEA,
    CONCEPT_REVIEW,
    CONCEPT_REJECTED,
    PROMPT_DRAFT,
    VALIDATING,
    BLOCKED,
    NEEDS_FIX,
    RENDER_READY,
    RENDER_QUEUED,
    RENDERING,
    RENDER_COMPLETE,
    RENDER_QA,
    ASSET_APPROVED,
    ARCHIVED
}
```

**PromptVersionEntity** - Immutable prompt versions

```java
@Entity
@Table(name = "prompt_versions")
public class PromptVersionEntity {
    @Id
    private UUID id;
    
    @ManyToOne
    private ContentEntity content;
    
    private Integer versionNumber;
    
    @Column(columnDefinition = "TEXT")
    private String promptText;
    
    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "JSONB")
    private VideoPlanIR videoPlanIr;
    
    private Double parserConfidence;
    
    @Convert(converter = StringArrayConverter.class)
    private List<String> parserWarnings;
    
    @Convert(converter = StringArrayConverter.class)
    private List<String> parserAmbiguities;
    
    @Enumerated(EnumType.STRING)
    private CreatedBy createdBy;
    
    private Instant createdAt;
}

enum CreatedBy {
    USER,
    AI_FIX
}
```

**VideoPlanIR** - Java representation of parsed prompt structure

```java
public record VideoPlanIR(
    Metadata metadata,
    Characters characters,
    Setting setting,
    LearningObjective learningObjective,
    CoreMechanic coreMechanic,
    Hook hook,
    List<Beat> beats,
    FinalPayoff finalPayoff,
    Producibility producibility
) {
    public record Metadata(
        String title,
        int duration,
        String format,
        String seriesType,
        Instant createdAt,
        int version,
        String previousVersionId
    ) {}
    
    public record Beat(
        String id,
        double startTime,
        double endTime,
        double duration,
        String action,
        String actionType,
        String visualState,
        String visualStateId,
        String consequence,
        String consequenceType,
        int intensity,
        String motionAmount,
        Dialogue dialogue,
        double readabilityDuration,
        boolean isReadable,
        boolean isNewConsequence,
        List<String> similarToBeats,
        String cycleGroup
    ) {}
    
    // ... other nested records
}
```

**Services:**

```java
@Service
public class ContentService {
    public ContentEntity createContent(CreateContentRequest request);
    public PromptVersionEntity createPromptVersion(UUID contentId, String promptText, CreatedBy createdBy);
    public ContentEntity getContent(UUID id);
    public Page<ContentEntity> listContents(ContentFilter filter, Pageable pageable);
    public void updateStatus(UUID contentId, ContentStatus newStatus);
    public List<PromptVersionEntity> getVersionHistory(UUID contentId);
    public PromptVersionEntity getVersion(UUID contentId, int versionNumber);
}

@Service
public class ConceptValidationService {
    public ConceptValidationResult validateConcept(UUID contentId, String conceptText);
    public List<ConceptValidationEntity> getConceptHistory(UUID contentId);
}
```

**Controllers:**

```java
@RestController
@RequestMapping("/api/v1/contents")
public class ContentController {
    
    @PostMapping
    public ResponseEntity<ContentResponse> createContent(@RequestBody CreateContentRequest request);
    
    @GetMapping("/{id}")
    public ResponseEntity<ContentDetailResponse> getContent(@PathVariable UUID id);
    
    @GetMapping
    public ResponseEntity<Page<ContentSummaryResponse>> listContents(
        @RequestParam(required = false) ContentStatus status,
        @RequestParam(required = false) UUID characterId,
        @RequestParam(required = false) SeriesType seriesType,
        Pageable pageable
    );
    
    @PostMapping("/{id}/concept-validate")
    public ResponseEntity<ConceptValidationResponse> validateConcept(
        @PathVariable UUID id,
        @RequestBody ConceptValidationRequest request
    );
    
    @PostMapping("/{id}/prompt-versions")
    public ResponseEntity<PromptVersionResponse> createPromptVersion(
        @PathVariable UUID id,
        @RequestBody CreatePromptVersionRequest request
    );
    
    @GetMapping("/{id}/prompt-versions")
    public ResponseEntity<List<PromptVersionResponse>> getVersionHistory(@PathVariable UUID id);
    
    @GetMapping("/{id}/prompt-versions/{versionNumber}")
    public ResponseEntity<PromptVersionDetailResponse> getVersion(
        @PathVariable UUID id,
        @PathVariable int versionNumber
    );
}
```

---

### 2. Validation Domain (Backend)

**ValidationRunEntity** - Results of quality validation

```java
@Entity
@Table(name = "validation_runs")
public class ValidationRunEntity {
    @Id
    private UUID id;
    
    @ManyToOne
    private PromptVersionEntity promptVersion;
    
    private String rulesetVersion;
    
    private Double overallScore;
    
    @Enumerated(EnumType.STRING)
    private ValidationStatus status;
    
    private Integer blockerCount;
    private Integer criticalCount;
    private Integer warningCount;
    
    @Type(JsonBinaryType.class)
    @Column(columnDefinition = "JSONB")
    private Map<String, Double> familyScores;
    
    private Long executionTimeMs;
    
    private Instant createdAt;
    
    @OneToMany(mappedBy = "validationRun", cascade = CascadeType.ALL)
    private List<FailedRuleEntity> failedRules;
}

enum ValidationStatus {
    PASS,
    NEEDS_REVISION,
    BLOCKED
}
```

**FailedRuleEntity** - Individual rule violations with evidence

```java
@Entity
@Table(name = "failed_rules")
public class FailedRuleEntity {
    @Id
    private UUID id;
    
    @ManyToOne
    private ValidationRunEntity validationRun;
    
    private String family;
    private String ruleId;
    
    @Enumerated(EnumType.STRING)
    private RuleSeverity severity;
    
    @Column(columnDefinition = "TEXT")
    private String actualValue;
    
    @Column(columnDefinition = "TEXT")
    private String requiredValue;
    
    @Column(columnDefinition = "TEXT")
    private String evidence;
    
    @Column(columnDefinition = "TEXT")
    private String recommendation;
}

enum RuleSeverity {
    BLOCKER,
    CRITICAL,
    WARNING
}
```

**Services:**

```java
@Service
public class ValidationService {
    
    public ValidationRunEntity validatePrompt(UUID promptVersionId) {
        // 1. Load prompt version
        // 2. If no IR, parse it first
        // 3. Call ML service for quality validation
        // 4. Save ValidationRunEntity + FailedRuleEntity
        // 5. Update content status
        // 6. Return validation results
    }
    
    public List<ValidationRunEntity> getValidationHistory(UUID contentId);
    
    public ValidationRunEntity getLatestValidation(UUID promptVersionId);
    
    public RegressionReport detectRegression(UUID oldVersionId, UUID newVersionId);
}

@Service
public class RenderGateService {
    
    public RenderReadinessDecision evaluateReadiness(UUID promptVersionId) {
        ValidationRunEntity latest = validationService.getLatestValidation(promptVersionId);
        
        boolean isReady = 
            latest.getBlockerCount() == 0 &&
            latest.getCriticalCount() == 0 &&
            latest.getOverallScore() >= 92.0 &&
            latest.getFamilyScores().get("conceptStrength") >= 85.0 &&
            latest.getFamilyScores().get("hookStrength") >= 85.0 &&
            latest.getFamilyScores().get("visualNovelty") >= 82.0 &&
            latest.getFamilyScores().get("progression") >= 85.0 &&
            latest.getFamilyScores().get("aiProducibility") >= 80.0 &&
            latest.getFamilyScores().get("readability") >= 85.0 &&
            latest.getFamilyScores().get("finalPayoff") >= 82.0;
        
        return new RenderReadinessDecision(isReady, generateReasoning(latest));
    }
    
    public void markRenderReady(UUID contentId, String approvedBy);
    
    public HumanOverrideEntity createOverride(UUID promptVersionId, String ruleId, String reason, String by);
}
```

**Controllers:**

```java
@RestController
@RequestMapping("/api/v1")
public class ValidationController {
    
    @PostMapping("/contents/{id}/validate")
    public ResponseEntity<ValidationResultResponse> validatePrompt(
        @PathVariable UUID id,
        @RequestParam(required = false) Integer versionNumber
    );
    
    @GetMapping("/contents/{id}/validation-history")
    public ResponseEntity<List<ValidationResultResponse>> getValidationHistory(@PathVariable UUID id);
    
    @PostMapping("/contents/{id}/check-render-readiness")
    public ResponseEntity<RenderReadinessResponse> checkRenderReadiness(@PathVariable UUID id);
    
    @PostMapping("/contents/{id}/mark-render-ready")
    public ResponseEntity<Void> markRenderReady(
        @PathVariable UUID id,
        @RequestBody MarkRenderReadyRequest request
    );
    
    @PostMapping("/contents/{id}/override-rule")
    public ResponseEntity<HumanOverrideResponse> overrideRule(
        @PathVariable UUID id,
        @RequestBody RuleOverrideRequest request
    );
    
    @GetMapping("/prompt-versions/{versionId}/compare/{otherVersionId}")
    public ResponseEntity<VersionComparisonResponse> compareVersions(
        @PathVariable UUID versionId,
        @PathVariable UUID otherVersionId
    );
}
```

---

### 3. LLM Provider Abstraction (Backend)

**Interface:**

```java
public interface LlmProvider {
    String getName();
    boolean isAvailable();
    LlmResponse complete(LlmRequest request);
    int estimateTokens(String text);
    double estimateCost(int tokens);
}

public record LlmRequest(
    String systemPrompt,
    String userPrompt,
    double temperature,
    int maxTokens,
    String responseFormat
) {}

public record LlmResponse(
    String content,
    int tokensUsed,
    long responseTimeMs,
    double cost
) {}
```

**Implementations:**

```java
@Component
@ConditionalOnProperty(name = "llm.provider", havingValue = "openai")
public class OpenAiProvider implements LlmProvider {
    
    @Value("${llm.openai.api-key}")
    private String apiKey;
    
    @Value("${llm.openai.model}")
    private String model;
    
    private final RestTemplate restTemplate;
    
    @Override
    public LlmResponse complete(LlmRequest request) {
        // Call OpenAI API
        // Parse response
        // Track tokens and cost
        // Handle errors (rate limits, timeouts)
    }
}

// Similar implementations for Claude, Gemini, Ollama
```

**Configuration:**

```yaml
llm:
  provider: ${LLM_PROVIDER:openai}
  openai:
    api-key: ${OPENAI_API_KEY:}
    model: ${OPENAI_MODEL:gpt-4o}
    timeout: 30s
  claude:
    api-key: ${CLAUDE_API_KEY:}
    model: claude-3-5-sonnet-20241022
  gemini:
    api-key: ${GEMINI_API_KEY:}
    model: gemini-2.0-flash-exp
  ollama:
    base-url: ${OLLAMA_BASE_URL:http://localhost:11434}
    model: qwen2.5:7b
```

---

### 4. Prompt Parser (ML Service - FastAPI)

**Parser Service:**

```python
class PromptParser:
    def __init__(self, llm_client: LlmClient):
        self.llm_client = llm_client
        self.system_prompt = self._load_system_prompt()
    
    def parse(self, prompt_text: str, character: str, duration: int) -> ParseResult:
        """
        Convert prompt text → VideoPlanIR using LLM
        
        Returns:
            ParseResult with IR, confidence, warnings, ambiguities
        """
        user_prompt = self._build_user_prompt(prompt_text, character, duration)
        
        response = self.llm_client.complete(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,  # Low temperature for structured output
            response_format="json"
        )
        
        ir = self._extract_json(response.content)
        confidence = self._calculate_confidence(ir, response)
        warnings = self._detect_warnings(ir)
        ambiguities = self._detect_ambiguities(ir, prompt_text)
        
        return ParseResult(
            video_plan_ir=ir,
            confidence=confidence,
            warnings=warnings,
            ambiguities=ambiguities
        )
    
    def _load_system_prompt(self) -> str:
        """Load from ml-service/prompts/parser-system.txt"""
        # Include:
        # - VideoPlanIR schema definition
        # - Beat extraction guidelines
        # - Intensity estimation rules
        # - Visual state normalization
        # - Example good/bad IRs
    
    def _calculate_confidence(self, ir: dict, response: LlmResponse) -> float:
        """
        Calculate parser confidence 0.0-1.0
        
        Factors:
        - Beat count (4-10 is ideal)
        - Beat continuity (no gaps)
        - Sum(beat durations) == target duration
        - All required fields present
        - LLM response coherence
        """
```

**API Endpoint:**

```python
@router.post("/api/ml/parse-prompt")
async def parse_prompt(request: ParsePromptRequest) -> ParsePromptResponse:
    """
    Parse prompt text into VideoPlanIR structure
    
    Input:
        prompt_text: str
        character_name: str
        target_duration: int
        series_type: str
    
    Output:
        video_plan_ir: dict
        confidence: float (0.0-1.0)
        warnings: list[str]
        ambiguities: list[str]
    """
    parser = PromptParser(llm_client)
    result = parser.parse(
        prompt_text=request.prompt_text,
        character=request.character_name,
        duration=request.target_duration
    )
    
    return ParsePromptResponse(
        video_plan_ir=result.video_plan_ir,
        confidence=result.confidence,
        warnings=result.warnings,
        ambiguities=result.ambiguities
    )
```

---

### 5. Rule Engine (ML Service - FastAPI)

**Rule YAML Structure:**

```yaml
# ml-service/rules/visual_novelty.yaml
family: visual_novelty
weight: 0.14
minimum_threshold: 80

criteria:
  - name: distinct_consequence_count
    description: "Number of materially different visual consequences"
    measurement: "Count beats where isNewConsequence == true"
    pass_threshold: 5
    operator: ">="
    weight: 0.35
    severity_on_fail: BLOCKER
    
  - name: static_state_duration
    description: "No single visual state dominates"
    measurement: "Max % duration of any visualStateId"
    pass_threshold: 30
    operator: "<="
    weight: 0.25
    severity_on_fail: CRITICAL
    
  - name: novelty_timeline_distribution
    description: "New consequences spread across timeline"
    measurement: "Longest gap without new consequence"
    pass_threshold: 4.5
    operator: "<="
    unit: "seconds"
    weight: 0.20
    severity_on_fail: WARNING
    
  - name: action_repetition_frequency
    description: "Same action doesn't repeat 3+ times"
    measurement: "Count of most frequent action"
    pass_threshold: 2
    operator: "<="
    weight: 0.20
    severity_on_fail: CRITICAL

scoring:
  excellent: [90, 100]
  good: [80, 89]
  acceptable: [70, 79]
  weak: [60, 69]
  failing: [0, 59]
```

**Rule Engine:**

```python
class RuleEngine:
    def __init__(self, ruleset_version: str = "1.0"):
        self.ruleset = self._load_ruleset(ruleset_version)
        self.evaluators = {
            "concept_strength": ConceptStrengthEvaluator(),
            "hook_strength": HookStrengthEvaluator(),
            "visual_novelty": VisualNoveltyEvaluator(),
            "progression": ProgressionEvaluator(),
            "escalation": EscalationEvaluator(),
            "motion_quality": MotionQualityEvaluator(),
            "readability": ReadabilityEvaluator(),
            "ai_producibility": AiProducibilityEvaluator(),
            "consistency": ConsistencyEvaluator(),
            "final_payoff": FinalPayoffEvaluator(),
            "render_risk": RenderRiskEvaluator()
        }
    
    def evaluate(self, video_plan_ir: dict) -> ValidationResult:
        """
        Evaluate IR against all 11 rule families
        
        Returns:
            overall_score: float
            status: str (PASS/NEEDS_REVISION/BLOCKED)
            family_scores: dict[str, float]
            failed_rules: list[FailedRule]
            blocker_count, critical_count, warning_count: int
        """
        family_results = {}
        all_failed_rules = []
        
        for family_name, evaluator in self.evaluators.items():
            family_def = self.ruleset.families[family_name]
            result = evaluator.evaluate(video_plan_ir, family_def)
            
            family_results[family_name] = result.score
            all_failed_rules.extend(result.failed_criteria)
        
        overall_score = self._calculate_weighted_score(family_results)
        status = self._determine_status(overall_score, all_failed_rules)
        
        return ValidationResult(
            overall_score=overall_score,
            status=status,
            family_scores=family_results,
            failed_rules=all_failed_rules,
            blocker_count=self._count_severity(all_failed_rules, "BLOCKER"),
            critical_count=self._count_severity(all_failed_rules, "CRITICAL"),
            warning_count=self._count_severity(all_failed_rules, "WARNING")
        )
```

**Family Evaluator Example:**

```python
class VisualNoveltyEvaluator(BaseFamilyEvaluator):
    def evaluate(self, ir: dict, family_def: RuleFamily) -> FamilyResult:
        scores = {}
        failed = []
        
        # Criterion 1: distinct_consequence_count
        new_consequence_count = sum(
            1 for beat in ir['beats'] if beat.get('isNewConsequence', False)
        )
        criterion = family_def.get_criterion('distinct_consequence_count')
        if new_consequence_count < criterion.pass_threshold:
            failed.append(FailedRule(
                family="visual_novelty",
                rule_id="distinct_consequence_count",
                severity=criterion.severity_on_fail,
                actual_value=str(new_consequence_count),
                required_value=f">= {criterion.pass_threshold}",
                evidence=f"Only {new_consequence_count} distinct consequences detected.",
                recommendation="Add more consequences to reach minimum of {criterion.pass_threshold}."
            ))
            scores['distinct_consequence_count'] = 0
        else:
            scores['distinct_consequence_count'] = 100
        
        # Criterion 2: static_state_duration
        state_durations = self._group_by_visual_state(ir['beats'])
        max_state_pct = max(
            (duration / ir['metadata']['duration']) * 100
            for duration in state_durations.values()
        )
        criterion = family_def.get_criterion('static_state_duration')
        if max_state_pct > criterion.pass_threshold:
            longest_state = max(state_durations, key=state_durations.get)
            failed.append(FailedRule(
                family="visual_novelty",
                rule_id="static_state_duration",
                severity=criterion.severity_on_fail,
                actual_value=f"{max_state_pct:.1f}%",
                required_value=f"<= {criterion.pass_threshold}%",
                evidence=f"Visual state '{longest_state}' occupies {max_state_pct:.1f}% of video.",
                recommendation=f"Reduce '{longest_state}' duration or introduce new consequences."
            ))
            scores['static_state_duration'] = 0
        else:
            scores['static_state_duration'] = 100
        
        # ... evaluate remaining 2 criteria
        
        family_score = self._weighted_average(scores, family_def.criteria)
        
        return FamilyResult(
            score=family_score,
            failed_criteria=failed
        )
```

**API Endpoint:**

```python
@router.post("/api/ml/validate-quality")
async def validate_quality(request: ValidateQualityRequest) -> ValidationResultResponse:
    """
    Evaluate VideoPlanIR against current ruleset
    
    Input:
        video_plan_ir: dict
        ruleset_version: str (default "1.0")
    
    Output:
        overall_score: float
        status: str
        family_scores: dict[str, float]
        failed_rules: list[FailedRule]
        blocker_count, critical_count, warning_count: int
    """
    engine = RuleEngine(ruleset_version=request.ruleset_version)
    result = engine.evaluate(request.video_plan_ir)
    
    return ValidationResultResponse(
        overall_score=result.overall_score,
        status=result.status,
        family_scores=result.family_scores,
        failed_rules=result.failed_rules,
        blocker_count=result.blocker_count,
        critical_count=result.critical_count,
        warning_count=result.warning_count
    )
```

---

### 6. Concept Validator (ML Service - FastAPI)

```python
class ConceptValidator:
    def __init__(self, llm_client: LlmClient):
        self.llm_client = llm_client
        self.system_prompt = self._load_system_prompt()
    
    def validate(self, concept_text: str, character: str, duration: int) -> ConceptValidationResult:
        """
        Validate concept (idea-only) before full prompt
        
        Checks:
        - Can generate 4+ visual consequences?
        - 15-second capacity?
        - Single dominant mechanic?
        - AI-producible?
        - Too simple or too complex?
        """
        user_prompt = f"""
        Concept: {concept_text}
        Character: {character}
        Duration: {duration} seconds
        
        Evaluate if this concept can sustain {duration} seconds of engaging content.
        Return JSON:
        {{
          "is_passing": bool,
          "failure_reasons": list[str],
          "recommendations": list[str],
          "confidence": float
        }}
        """
        
        response = self.llm_client.complete(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            response_format="json"
        )
        
        result = json.loads(response.content)
        return ConceptValidationResult(**result)

@router.post("/api/ml/validate-concept")
async def validate_concept(request: ConceptRequest) -> ConceptResponse:
    validator = ConceptValidator(llm_client)
    result = validator.validate(
        concept_text=request.concept_text,
        character=request.character_name,
        duration=request.target_duration
    )
    return ConceptResponse(**result.dict())
```

---

### 7. Frontend (Angular 21)

**Prompt Create Component:**

```typescript
// prompts/prompt-create/prompt-create.component.ts
@Component({
  selector: 'app-prompt-create',
  standalone: true,
  template: `
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
      <mat-form-field>
        <input matInput formControlName="title" placeholder="Title" />
      </mat-form-field>
      
      <mat-form-field>
        <mat-select formControlName="characterId" placeholder="Character">
          <mat-option *ngFor="let char of characters$ | async" [value]="char.id">
            {{ char.name }}
          </mat-option>
        </mat-select>
      </mat-form-field>
      
      <mat-form-field>
        <mat-select formControlName="seriesType" placeholder="Series Type">
          <mat-option value="OPPOSITES">Opposites</mat-option>
          <mat-option value="WHATS_WRONG">What's Wrong?</mat-option>
          <!-- ... -->
        </mat-select>
      </mat-form-field>
      
      <mat-form-field>
        <textarea matInput formControlName="conceptText" 
                  placeholder="Concept (brief idea)" rows="3"></textarea>
      </mat-form-field>
      
      <button mat-raised-button type="button" 
              (click)="validateConcept()" 
              [disabled]="!form.value.conceptText">
        Validate Concept
      </button>
      
      <mat-form-field *ngIf="conceptPassed">
        <textarea matInput formControlName="promptText" 
                  placeholder="Full Prompt" rows="15"></textarea>
      </mat-form-field>
      
      <div class="actions">
        <button mat-raised-button type="submit">Save Draft</button>
        <button mat-raised-button color="primary" 
                (click)="validatePrompt()" 
                [disabled]="!form.value.promptText">
          Validate Prompt
        </button>
      </div>
    </form>
  `
})
export class PromptCreateComponent {
  form = this.fb.group({
    title: ['', Validators.required],
    characterId: ['', Validators.required],
    seriesType: ['', Validators.required],
    targetDuration: [15, Validators.required],
    conceptText: [''],
    promptText: ['']
  });
  
  conceptPassed = false;
  
  async validateConcept() {
    const result = await this.conceptService.validate(
      this.form.value.conceptText!
    );
    
    if (result.isPassing) {
      this.conceptPassed = true;
      this.snackBar.open('Concept is strong! You can write the full prompt.', 'OK');
    } else {
      this.dialog.open(ConceptFailureDialog, {
        data: result
      });
    }
  }
  
  async validatePrompt() {
    const content = await this.contentService.create(this.form.value);
    const validation = await this.validationService.validate(content.id);
    
    this.router.navigate(['/contents', content.id, 'validation']);
  }
}
```

**Validation Results Component:**

```typescript
// validation/validation-results/validation-results.component.ts
@Component({
  selector: 'app-validation-results',
  standalone: true,
  template: `
    <div class="header">
      <h2>{{ content.title }} (V{{ promptVersion.versionNumber }})</h2>
      <mat-chip [color]="statusColor">{{ validation.status }}</mat-chip>
      <div class="score">{{ validation.overallScore }} / 100</div>
    </div>
    
    <mat-card>
      <mat-card-header>
        <mat-card-title>Overall Quality</mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <mat-progress-bar mode="determinate" 
                          [value]="validation.overallScore"></mat-progress-bar>
        <div class="severity-counts">
          <span class="blocker">Blockers: {{ validation.blockerCount }}</span>
          <span class="critical">Critical: {{ validation.criticalCount }}</span>
          <span class="warning">Warnings: {{ validation.warningCount }}</span>
        </div>
      </mat-card-content>
    </mat-card>
    
    <app-family-scorecard [familyScores]="validation.familyScores"></app-family-scorecard>
    
    <app-beat-timeline [videoPlanIr]="promptVersion.videoPlanIr"></app-beat-timeline>
    
    <app-failed-rules-table [failedRules]="validation.failedRules"></app-failed-rules-table>
    
    <div class="actions">
      <button mat-raised-button (click)="exportForFix()">Export for ChatGPT</button>
      <button mat-raised-button (click)="importFixed()">Import Fixed</button>
      <button mat-raised-button color="primary" 
              *ngIf="renderReadiness.isReady"
              (click)="markRenderReady()">
        Mark Render Ready
      </button>
    </div>
  `
})
export class ValidationResultsComponent {
  content!: ContentEntity;
  promptVersion!: PromptVersionEntity;
  validation!: ValidationRunEntity;
  renderReadiness!: RenderReadinessDecision;
  
  ngOnInit() {
    this.loadData();
  }
  
  exportForFix() {
    const report = this.fixLoopService.generateReport(this.validation);
    navigator.clipboard.writeText(report);
    this.snackBar.open('Report copied to clipboard!', 'OK');
  }
  
  async importFixed() {
    const dialog = this.dialog.open(ImportFixedDialog);
    const fixedPrompt = await dialog.afterClosed().toPromise();
    
    if (fixedPrompt) {
      const newVersion = await this.contentService.createVersion(
        this.content.id,
        fixedPrompt,
        'AI_FIX'
      );
      
      const newValidation = await this.validationService.validate(newVersion.id);
      
      const regression = await this.validationService.compareVersions(
        this.promptVersion.id,
        newVersion.id
      );
      
      this.router.navigate(['/contents', this.content.id, 'versions', 'compare'], {
        queryParams: {
          v1: this.promptVersion.versionNumber,
          v2: newVersion.versionNumber
        }
      });
    }
  }
}
```

**Beat Timeline Component:**

```typescript
// validation/beat-timeline/beat-timeline.component.ts
@Component({
  selector: 'app-beat-timeline',
  standalone: true,
  template: `
    <svg [attr.width]="width" [attr.height]="height">
      <!-- Time axis -->
      <line [attr.x1]="margin" [attr.y1]="timelineY" 
            [attr.x2]="width - margin" [attr.y2]="timelineY" 
            stroke="#ccc" />
      
      <!-- Beat blocks -->
      <g *ngFor="let beat of beats">
        <rect [attr.x]="getBeatX(beat)" 
              [attr.y]="beatY" 
              [attr.width]="getBeatWidth(beat)" 
              [attr.height]="beatHeight"
              [attr.fill]="getBeatColor(beat)"
              (mouseover)="showTooltip(beat)"
              (click)="selectBeat(beat)">
        </rect>
      </g>
      
      <!-- Intensity curve -->
      <polyline [attr.points]="intensityCurve" 
                fill="none" 
                stroke="#ff6b6b" 
                stroke-width="2" />
    </svg>
    
    <div *ngIf="selectedBeat" class="beat-details">
      <h4>Beat {{ selectedBeat.id }}</h4>
      <p><strong>Time:</strong> {{ selectedBeat.startTime }}s - {{ selectedBeat.endTime }}s</p>
      <p><strong>Action:</strong> {{ selectedBeat.action }}</p>
      <p><strong>Consequence:</strong> {{ selectedBeat.consequence }}</p>
      <p><strong>Intensity:</strong> {{ selectedBeat.intensity }}/10</p>
      <mat-chip [color]="consequenceTypeColor(selectedBeat)">
        {{ selectedBeat.consequenceType }}
      </mat-chip>
    </div>
  `
})
export class BeatTimelineComponent {
  @Input() videoPlanIr!: VideoPlanIR;
  
  width = 800;
  height = 200;
  margin = 40;
  
  get beats() {
    return this.videoPlanIr.beats;
  }
  
  getBeatX(beat: Beat): number {
    const duration = this.videoPlanIr.metadata.duration;
    const timelineWidth = this.width - 2 * this.margin;
    return this.margin + (beat.startTime / duration) * timelineWidth;
  }
  
  getBeatWidth(beat: Beat): number {
    const duration = this.videoPlanIr.metadata.duration;
    const timelineWidth = this.width - 2 * this.margin;
    return (beat.duration / duration) * timelineWidth;
  }
  
  getBeatColor(beat: Beat): string {
    switch (beat.consequenceType) {
      case 'new': return '#4caf50';
      case 'continuation': return '#ffc107';
      case 'repeat': return '#f44336';
      case 'escalation': return '#2196f3';
      default: return '#9e9e9e';
    }
  }
  
  get intensityCurve(): string {
    const duration = this.videoPlanIr.metadata.duration;
    const timelineWidth = this.width - 2 * this.margin;
    const maxIntensity = 10;
    
    return this.beats.map(beat => {
      const x = this.margin + (beat.startTime / duration) * timelineWidth;
      const y = this.height - this.margin - (beat.intensity / maxIntensity) * 100;
      return `${x},${y}`;
    }).join(' ');
  }
}
```

---

## Database Schema

**Flyway Migrations:**

```sql
-- V7__phase1_content_domain.sql
CREATE TABLE contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    character_id UUID REFERENCES characters(id),
    series_type VARCHAR(50) NOT NULL,
    target_duration_seconds INT NOT NULL DEFAULT 15,
    target_platforms TEXT[] NOT NULL DEFAULT ARRAY['ALL'],
    learning_words TEXT[],
    creative_engine VARCHAR(200),
    status VARCHAR(50) NOT NULL DEFAULT 'IDEA',
    current_prompt_version INT DEFAULT 0,
    entity_version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_series_type CHECK (series_type IN ('OPPOSITES', 'WHATS_WRONG', 'DISCOVERY', 'FEELINGS', 'MUSIC', 'STORIES', 'SOCIAL_REEL')),
    CONSTRAINT chk_status CHECK (status IN ('IDEA', 'CONCEPT_REVIEW', 'CONCEPT_REJECTED', 'PROMPT_DRAFT', 'VALIDATING', 'BLOCKED', 'NEEDS_FIX', 'RENDER_READY', 'RENDER_QUEUED', 'RENDERING', 'RENDER_COMPLETE', 'RENDER_QA', 'ASSET_APPROVED', 'ARCHIVED'))
);

CREATE INDEX idx_contents_status ON contents(status);
CREATE INDEX idx_contents_character ON contents(character_id);
CREATE INDEX idx_contents_series_type ON contents(series_type);

CREATE TABLE prompt_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    prompt_text TEXT NOT NULL,
    video_plan_ir JSONB,
    parser_confidence NUMERIC(3,2),
    parser_warnings TEXT[],
    parser_ambiguities TEXT[],
    created_by VARCHAR(50) NOT NULL DEFAULT 'USER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_created_by CHECK (created_by IN ('USER', 'AI_FIX')),
    CONSTRAINT chk_confidence CHECK (parser_confidence IS NULL OR (parser_confidence >= 0 AND parser_confidence <= 1)),
    UNIQUE(content_id, version_number)
);

CREATE INDEX idx_prompt_versions_content ON prompt_versions(content_id);

CREATE TABLE concept_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    concept_text TEXT NOT NULL,
    is_passing BOOLEAN NOT NULL,
    failure_reasons TEXT[],
    recommendations TEXT[],
    confidence_score NUMERIC(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_concept_validations_content ON concept_validations(content_id);

-- V8__phase1_validation_domain.sql
CREATE TABLE validation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
    ruleset_version VARCHAR(10) NOT NULL DEFAULT '1.0',
    overall_score NUMERIC(5,2) NOT NULL,
    status VARCHAR(30) NOT NULL,
    blocker_count INT NOT NULL DEFAULT 0,
    critical_count INT NOT NULL DEFAULT 0,
    warning_count INT NOT NULL DEFAULT 0,
    family_scores JSONB NOT NULL,
    execution_time_ms BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_score CHECK (overall_score >= 0 AND overall_score <= 100),
    CONSTRAINT chk_status CHECK (status IN ('PASS', 'NEEDS_REVISION', 'BLOCKED'))
);

CREATE INDEX idx_validation_runs_prompt_version ON validation_runs(prompt_version_id);
CREATE INDEX idx_validation_runs_status ON validation_runs(status);

CREATE TABLE failed_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    validation_run_id UUID NOT NULL REFERENCES validation_runs(id) ON DELETE CASCADE,
    family VARCHAR(50) NOT NULL,
    rule_id VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    actual_value TEXT,
    required_value TEXT,
    evidence TEXT NOT NULL,
    recommendation TEXT,
    
    CONSTRAINT chk_severity CHECK (severity IN ('BLOCKER', 'CRITICAL', 'WARNING'))
);

CREATE INDEX idx_failed_rules_validation_run ON failed_rules(validation_run_id);
CREATE INDEX idx_failed_rules_severity ON failed_rules(severity);

CREATE TABLE human_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id),
    validation_run_id UUID REFERENCES validation_runs(id),
    overridden_rule_id VARCHAR(50) NOT NULL,
    original_severity VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    overridden_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_human_overrides_prompt_version ON human_overrides(prompt_version_id);

-- V9__phase1_reference_library.sql
CREATE TABLE reference_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
    reference_type VARCHAR(20) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    expected_status VARCHAR(30) NOT NULL,
    tags TEXT[],
    added_by VARCHAR(50) NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    CONSTRAINT chk_reference_type CHECK (reference_type IN ('POSITIVE', 'NEGATIVE')),
    CONSTRAINT chk_category CHECK (category IN ('WINNER', 'STATIC_STATE', 'REPETITION', 'CYCLE_REPETITION', 'WEAK_FINAL', 'WEAK_HOOK', 'INSUFFICIENT_CONSEQUENCES', 'AI_PRODUCIBILITY_ISSUE'))
);

CREATE INDEX idx_reference_prompts_type ON reference_prompts(reference_type);
CREATE INDEX idx_reference_prompts_category ON reference_prompts(category);

CREATE TABLE ruleset_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(10) NOT NULL UNIQUE,
    description TEXT,
    rules_definition TEXT NOT NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deprecated_at TIMESTAMPTZ
);
```

---

## Testing Strategy

### Unit Tests
- ✅ Each rule family evaluator (11 tests)
- ✅ LLM provider implementations (mock API responses)
- ✅ State machine transitions
- ✅ Version comparison logic

### Integration Tests
- ✅ End-to-end: Create content → Validate → Fix → Revalidate
- ✅ Parser: Known prompts → Expected IR
- ✅ Rule engine: Known IR → Expected validation results

### Golden Tests
- ✅ Mimi Clean/Dirty → RENDER_READY (score >92)
- ✅ Kiko Slippery/Rough → BLOCKED (static state)
- ✅ Opa Old/New → BLOCKED (repetition)
- ✅ Arda Sharp/Blunt → BLOCKED (cycle)

### Regression Tests
- ✅ Rule changes → Re-run all reference prompts
- ✅ Assert expected status unchanged

---

## Deployment

### Local Development

```bash
# Terminal 1: PostgreSQL
docker compose up postgres

# Terminal 2: ML Service
cd ml-service
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8001

# Terminal 3: Backend
cd backend
mvn spring-boot:run -Dspring-boot.run.profiles=local

# Terminal 4: Frontend
cd frontend
npm install
npm start
```

### Environment Variables

```bash
# .env
DB_URL=jdbc:postgresql://localhost:5432/pompom
DB_USERNAME=pompom
DB_PASSWORD=pompom_local

LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
GEMINI_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434

ML_SERVICE_URL=http://localhost:8001
POMPOM_DATA_ROOT=../data
```

---

## Success Criteria (Phase 1)

Before declaring Phase 1 complete:

- [ ] ✅ Can create content with metadata
- [ ] ✅ Concept validation catches insufficient consequences
- [ ] ✅ LLM parser converts Mimi prompt → IR (confidence >0.7)
- [ ] ✅ Rule engine evaluates all 11 families
- [ ] ✅ Kiko prompt → BLOCKED (static state 42% + insufficient consequences)
- [ ] ✅ Opa prompt → BLOCKED (repetitive action)
- [ ] ✅ Arda prompt → BLOCKED (cycle repetition)
- [ ] ✅ Mimi prompt → RENDER_READY (score 94, zero blockers)
- [ ] ✅ Version diff shows score changes
- [ ] ✅ Regression detection flags score drops
- [ ] ✅ Export report → Import fixed → New version created
- [ ] ✅ Render gate blocks prompts with blockers
- [ ] ✅ Manual override creates audit record
- [ ] ✅ Reference library has 4 golden cases
- [ ] ✅ Golden tests pass

**Target:** 2-3 weeks from start to completion

---

## Next Steps After Phase 1

1. **Phase 2 Spec:** Production Engine (OpenArt, render, QA)
2. **Phase 3 Spec:** Distribution Engine (TikTok, YouTube, Meta)
3. **Phase 4 Spec:** Learning Engine (metrics, correlations, rule mining)

---

**Document Status:** DRAFT  
**Review Required:** Yes  
**Dependencies:** Master Architecture v1.0  
**Implementation:** Not Started
