# Phase 2: Production Engine - Implementation Plan (Part 2: QA and UI)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Python QA analyzer, decision engine, and Angular UI to complete Phase 2 Production Engine.

**Architecture:** Spring Boot orchestrates → Python ML service performs QA (FFmpeg dead air, OpenCV character verification) → Decision engine decides ACCEPT/RERENDER/ABANDON → Angular UI displays progress.

**Part 1 Foundation (Complete):**
- ✅ Database schema (V10-V11)
- ✅ JPA entities (RenderJob, RenderAsset, RenderQaResult)
- ✅ OpenArt mock adapter
- ✅ Render job orchestration
- ✅ Asset library management
- ✅ Integration test

**Part 2 Scope (This Plan):**
1. Python FastAPI QA analyzer endpoints
2. QA decision engine (Spring Boot)
3. Enhanced orchestrator (triggers QA after download)
4. Angular render dashboard UI

## Global Constraints

- **Python:** 3.11 minimum, FastAPI, FFmpeg, OpenCV
- **Spring Boot:** 4.1.1, Java 21
- **Angular:** 21
- **No real credits:** Use mock adapter for Part 2
- **TDD:** Write test first, verify fail, implement, verify pass, commit
- **No Placeholders:** Every step has complete code

---

## Task 1: Python QA Analyzer - Dead Air Detection

**Files:**
- Create: `ml-service/app/qa/__init__.py`
- Create: `ml-service/app/qa/dead_air_analyzer.py`
- Create: `ml-service/tests/test_dead_air_analyzer.py`
- Modify: `ml-service/app/main.py` (add QA endpoints)

**Requirements:**
- Use FFmpeg to extract audio
- Detect silence segments (>2s)
- Return list of dead air segments with timestamps
- FastAPI endpoint: `POST /api/v1/qa/dead-air`

**Implementation:**

```python
# ml-service/app/qa/dead_air_analyzer.py
import subprocess
import json
from pathlib import Path
from typing import List, Dict

class DeadAirAnalyzer:
    def __init__(self, silence_threshold_db: int = -50, min_silence_duration: float = 2.0):
        self.silence_threshold_db = silence_threshold_db
        self.min_silence_duration = min_silence_duration
    
    def analyze(self, video_path: Path) -> Dict:
        """Detect dead air (silence) segments in video."""
        segments = self._detect_silence(video_path)
        
        has_dead_air = len(segments) > 0
        total_dead_air_duration = sum(seg['duration'] for seg in segments)
        
        return {
            'has_dead_air': has_dead_air,
            'dead_air_segments': segments,
            'total_dead_air_duration_ms': int(total_dead_air_duration * 1000),
            'segment_count': len(segments)
        }
    
    def _detect_silence(self, video_path: Path) -> List[Dict]:
        """Use FFmpeg silencedetect filter to find silence."""
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', f'silencedetect=noise={self.silence_threshold_db}dB:d={self.min_silence_duration}',
            '-f', 'null',
            '-'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse FFmpeg output for silence segments
        segments = []
        lines = result.stderr.split('\n')
        
        silence_start = None
        for line in lines:
            if 'silence_start:' in line:
                silence_start = float(line.split('silence_start:')[1].strip())
            elif 'silence_end:' in line and silence_start is not None:
                silence_end = float(line.split('silence_end:')[1].split('|')[0].strip())
                duration = silence_end - silence_start
                
                segments.append({
                    'start_ms': int(silence_start * 1000),
                    'end_ms': int(silence_end * 1000),
                    'duration': duration
                })
                
                silence_start = None
        
        return segments
```

```python
# ml-service/app/main.py (add endpoint)
from app.qa.dead_air_analyzer import DeadAirAnalyzer

dead_air_analyzer = DeadAirAnalyzer()

@app.post("/api/v1/qa/dead-air")
async def analyze_dead_air(request: DeadAirRequest):
    """Analyze video for dead air (silence segments)."""
    video_path = Path(request.video_path)
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    result = dead_air_analyzer.analyze(video_path)
    
    return DeadAirResponse(**result)
```

---

## Task 2: Python QA Analyzer - Character Identity Verification

**Files:**
- Create: `ml-service/app/qa/character_verifier.py`
- Create: `ml-service/tests/test_character_verifier.py`
- Modify: `ml-service/app/main.py` (add endpoint)

**Requirements:**
- Use OpenAI GPT-4V to verify character identity
- Compare first frame against character reference
- Return verification result + issues
- FastAPI endpoint: `POST /api/v1/qa/character-identity`

**Implementation:**

```python
# ml-service/app/qa/character_verifier.py
import base64
from pathlib import Path
from typing import Dict
from app.llm.llm_provider import get_provider

class CharacterVerifier:
    def __init__(self):
        self.llm = get_provider('openai')
    
    def verify(self, video_path: Path, expected_character: str, reference_image_path: Path = None) -> Dict:
        """Verify character identity using vision LLM."""
        # Extract first frame
        first_frame_path = self._extract_first_frame(video_path)
        
        # Encode image
        with open(first_frame_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode()
        
        # Build prompt
        prompt = f"""You are verifying character identity in a children's video.

Expected character: {expected_character}

Analyze the image and determine:
1. Is {expected_character} present in the image?
2. Is {expected_character} the main focus?
3. Are there any visual inconsistencies (wrong colors, proportions, style)?

Respond in JSON format:
{{
  "character_verified": true/false,
  "confidence": 0.0-1.0,
  "issues": ["list of any issues found"],
  "reasoning": "brief explanation"
}}
"""
        
        response = self.llm.complete(prompt, image=image_data)
        
        # Parse JSON response
        import json
        result = json.loads(response)
        
        return {
            'character_identity_verified': result['character_verified'],
            'confidence': result['confidence'],
            'character_identity_issues': ', '.join(result['issues']) if result['issues'] else None,
            'reasoning': result['reasoning']
        }
    
    def _extract_first_frame(self, video_path: Path) -> Path:
        """Extract first frame using FFmpeg."""
        import subprocess
        
        output_path = video_path.parent / f"{video_path.stem}_frame.png"
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vframes', '1',
            '-f', 'image2',
            str(output_path)
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        return output_path
```

---

## Task 3: QA Decision Engine (Spring Boot)

**Files:**
- Create: `backend/src/main/java/com/pompom/creative/service/QaDecisionEngine.java`
- Create: `backend/src/test/java/com/pompom/creative/service/QaDecisionEngineTest.java`

**Requirements:**
- Consume QA results from Python service
- Apply decision logic: ACCEPT / RERENDER / ABANDON
- Create RenderQaResult entity
- Return decision + reasoning

**Decision Rules:**
- Dead air (>2s): RERENDER (if attempts < 2), else ABANDON
- Character mismatch: ABANDON immediately
- Compliance score <70: RERENDER
- All pass: ACCEPT

```java
@Service
@Slf4j
@RequiredArgsConstructor
public class QaDecisionEngine {
    
    private final RenderQaResultRepository qaResultRepo;
    
    @Transactional
    public QaDecision makeDecision(RenderAsset asset, QaAnalysisResult qaResult) {
        log.info("Making QA decision for asset: {}", asset.getId());
        
        // Analyze results
        boolean hasDeadAir = qaResult.hasDeadAir();
        boolean characterVerified = qaResult.isCharacterIdentityVerified();
        int complianceScore = qaResult.getComplianceScore();
        
        RenderQaResult.QaDecision decision;
        String reason;
        
        // Decision logic
        if (!characterVerified) {
            decision = RenderQaResult.QaDecision.ABANDON;
            reason = "Character identity verification failed";
        } else if (hasDeadAir && asset.getRenderJob().getAttemptNumber() < 2) {
            decision = RenderQaResult.QaDecision.RERENDER;
            reason = "Dead air detected (" + qaResult.getDeadAirDurationMs() + "ms)";
        } else if (hasDeadAir) {
            decision = RenderQaResult.QaDecision.ABANDON;
            reason = "Dead air persists after max attempts";
        } else if (complianceScore < 70) {
            decision = RenderQaResult.QaDecision.RERENDER;
            reason = "Compliance score below threshold: " + complianceScore;
        } else {
            decision = RenderQaResult.QaDecision.ACCEPT;
            reason = "All QA checks passed";
        }
        
        // Create QA result entity
        RenderQaResult qaResultEntity = RenderQaResult.builder()
            .renderAsset(asset)
            .promptVersion(asset.getRenderJob().getPromptVersion())
            .decision(decision)
            .decisionReason(reason)
            .confidence(BigDecimal.valueOf(qaResult.getConfidence()))
            .complianceScore(complianceScore)
            .hasDeadAir(hasDeadAir)
            .deadAirSegments(qaResult.getDeadAirSegmentsJson())
            .characterIdentityVerified(characterVerified)
            .characterIdentityIssues(qaResult.getCharacterIdentityIssues())
            .physicsConsistent(true) // Placeholder for Part 3
            .hasObjectDuplication(false) // Placeholder for Part 3
            .requiresHumanReview(decision == RenderQaResult.QaDecision.ABANDON)
            .build();
        
        qaResultRepo.save(qaResultEntity);
        
        log.info("QA decision: {} - {}", decision, reason);
        
        return new QaDecision(decision, reason);
    }
}
```

---

## Task 4: Enhanced Orchestrator (Trigger QA)

**Files:**
- Modify: `backend/src/main/java/com/pompom/creative/service/RenderJobOrchestrator.java`
- Modify: `backend/src/test/java/com/pompom/creative/service/RenderJobOrchestratorTest.java`

**Requirements:**
- After asset download, call Python QA service
- Call QA decision engine
- If RERENDER: increment attempt, requeue job
- If ABANDON: mark job ABANDONED
- If ACCEPT: mark job COMPLETE

```java
// Add to RenderJobOrchestrator.executeRenderJob()

// After: RenderAsset asset = assetLibraryManager.recordAsset(job, downloadResult);

// Run QA analysis
QaAnalysisResult qaResult = qaService.analyzeAsset(asset);

// Make decision
QaDecision decision = qaDecisionEngine.makeDecision(asset, qaResult);

if (decision.getDecision() == RenderQaResult.QaDecision.RERENDER) {
    // Requeue job
    job.setAttemptNumber(job.getAttemptNumber() + 1);
    job.setStatus(RenderJob.RenderJobStatus.QUEUED);
    renderJobRepo.save(job);
    
    log.info("Job {} queued for rerender (attempt {})", jobId, job.getAttemptNumber());
    
    // Re-execute
    executeRenderJob(jobId);
    return;
}

if (decision.getDecision() == RenderQaResult.QaDecision.ABANDON) {
    job.setStatus(RenderJob.RenderJobStatus.ABANDONED);
    renderJobRepo.save(job);
    log.warn("Job {} abandoned: {}", jobId, decision.getReason());
    return;
}

// ACCEPT - mark complete (already done below)
```

---

## Task 5: Python QA Service Client (Spring Boot)

**Files:**
- Create: `backend/src/main/java/com/pompom/creative/qa/QaService.java`
- Create: `backend/src/main/java/com/pompom/creative/qa/QaAnalysisResult.java`
- Create: `backend/src/test/java/com/pompom/creative/qa/QaServiceTest.java`

**Requirements:**
- RestClient to call Python FastAPI
- Call /api/v1/qa/dead-air
- Call /api/v1/qa/character-identity
- Aggregate results into QaAnalysisResult

```java
@Service
@Slf4j
public class QaService {
    
    private final RestClient restClient;
    
    @Value("${pompom.qa.service.url:http://localhost:8001}")
    private String qaServiceUrl;
    
    public QaService(RestClient.Builder restClientBuilder) {
        this.restClient = restClientBuilder.baseUrl(qaServiceUrl).build();
    }
    
    public QaAnalysisResult analyzeAsset(RenderAsset asset) {
        Path assetPath = getAssetPath(asset);
        
        // Dead air analysis
        DeadAirResponse deadAir = restClient.post()
            .uri("/api/v1/qa/dead-air")
            .body(new DeadAirRequest(assetPath.toString()))
            .retrieve()
            .body(DeadAirResponse.class);
        
        // Character verification
        CharacterIdentityResponse characterIdentity = restClient.post()
            .uri("/api/v1/qa/character-identity")
            .body(new CharacterIdentityRequest(
                assetPath.toString(),
                extractCharacterName(asset)
            ))
            .retrieve()
            .body(CharacterIdentityResponse.class);
        
        // Aggregate results
        return QaAnalysisResult.builder()
            .hasDeadAir(deadAir.hasDeadAir())
            .deadAirSegments(deadAir.deadAirSegments())
            .deadAirDurationMs(deadAir.totalDeadAirDurationMs())
            .characterIdentityVerified(characterIdentity.characterVerified())
            .characterIdentityIssues(characterIdentity.issues())
            .confidence(characterIdentity.confidence())
            .complianceScore(calculateComplianceScore(deadAir, characterIdentity))
            .build();
    }
    
    private int calculateComplianceScore(DeadAirResponse deadAir, CharacterIdentityResponse character) {
        int score = 100;
        
        if (deadAir.hasDeadAir()) {
            score -= 30;
        }
        
        if (!character.characterVerified()) {
            score -= 50;
        }
        
        return Math.max(0, score);
    }
}
```

---

## Task 6: Angular Render Dashboard

**Files:**
- Create: `frontend/src/app/render/render-dashboard/render-dashboard.component.ts`
- Create: `frontend/src/app/render/render-dashboard/render-dashboard.component.html`
- Create: `frontend/src/app/render/render-dashboard/render-dashboard.component.scss`
- Create: `frontend/src/app/render/render.service.ts`
- Create: `frontend/src/app/render/models/render-job.model.ts`

**Requirements:**
- Display list of render jobs with status
- Show progress for IN_PROGRESS jobs
- Display QA results for completed jobs
- Action buttons: Queue New, View Asset, Rerun QA

```typescript
// frontend/src/app/render/render-dashboard/render-dashboard.component.ts
@Component({
  selector: 'app-render-dashboard',
  templateUrl: './render-dashboard.component.html',
  styleUrls: ['./render-dashboard.component.scss']
})
export class RenderDashboardComponent implements OnInit {
  renderJobs: RenderJob[] = [];
  loading = false;
  
  constructor(private renderService: RenderService) {}
  
  ngOnInit() {
    this.loadRenderJobs();
    
    // Poll for updates every 5 seconds
    interval(5000).subscribe(() => {
      this.loadRenderJobs();
    });
  }
  
  loadRenderJobs() {
    this.loading = true;
    this.renderService.getRenderJobs().subscribe({
      next: (jobs) => {
        this.renderJobs = jobs;
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load render jobs', err);
        this.loading = false;
      }
    });
  }
  
  queueNewRenderJob() {
    // Navigate to content selection
    this.router.navigate(['/render/queue']);
  }
  
  viewAsset(job: RenderJob) {
    // Open asset viewer
    window.open(job.assetUrl, '_blank');
  }
  
  getStatusClass(status: string): string {
    const statusMap = {
      'QUEUED': 'status-queued',
      'GENERATING': 'status-generating',
      'POLLING': 'status-polling',
      'DOWNLOADING': 'status-downloading',
      'COMPLETE': 'status-complete',
      'FAILED': 'status-failed',
      'ABANDONED': 'status-abandoned'
    };
    return statusMap[status] || 'status-unknown';
  }
}
```

```html
<!-- frontend/src/app/render/render-dashboard/render-dashboard.component.html -->
<div class="render-dashboard">
  <div class="dashboard-header">
    <h1>Render Dashboard</h1>
    <button mat-raised-button color="primary" (click)="queueNewRenderJob()">
      <mat-icon>add</mat-icon>
      Queue New Render
    </button>
  </div>
  
  <div class="dashboard-stats">
    <mat-card>
      <mat-card-content>
        <div class="stat">
          <span class="stat-value">{{ renderJobs.length }}</span>
          <span class="stat-label">Total Jobs</span>
        </div>
      </mat-card-content>
    </mat-card>
    
    <mat-card>
      <mat-card-content>
        <div class="stat">
          <span class="stat-value">{{ getJobsByStatus('QUEUED').length }}</span>
          <span class="stat-label">Queued</span>
        </div>
      </mat-card-content>
    </mat-card>
    
    <mat-card>
      <mat-card-content>
        <div class="stat">
          <span class="stat-value">{{ getJobsByStatus('COMPLETE').length }}</span>
          <span class="stat-label">Complete</span>
        </div>
      </mat-card-content>
    </mat-card>
  </div>
  
  <mat-card class="jobs-table-card">
    <mat-card-content>
      <table mat-table [dataSource]="renderJobs" class="jobs-table">
        
        <ng-container matColumnDef="content">
          <th mat-header-cell *matHeaderCellDef>Content</th>
          <td mat-cell *matCellDef="let job">{{ job.contentTitle }}</td>
        </ng-container>
        
        <ng-container matColumnDef="jobType">
          <th mat-header-cell *matHeaderCellDef>Type</th>
          <td mat-cell *matCellDef="let job">
            <span class="job-type-badge">{{ job.jobType }}</span>
          </td>
        </ng-container>
        
        <ng-container matColumnDef="status">
          <th mat-header-cell *matHeaderCellDef>Status</th>
          <td mat-cell *matCellDef="let job">
            <span [class]="'status-badge ' + getStatusClass(job.status)">
              {{ job.status }}
            </span>
          </td>
        </ng-container>
        
        <ng-container matColumnDef="progress">
          <th mat-header-cell *matHeaderCellDef>Progress</th>
          <td mat-cell *matCellDef="let job">
            <mat-progress-bar 
              *ngIf="job.status === 'GENERATING' || job.status === 'POLLING'"
              mode="indeterminate">
            </mat-progress-bar>
            <span *ngIf="job.status === 'COMPLETE'">100%</span>
          </td>
        </ng-container>
        
        <ng-container matColumnDef="qaDecision">
          <th mat-header-cell *matHeaderCellDef>QA Decision</th>
          <td mat-cell *matCellDef="let job">
            <span *ngIf="job.qaDecision" 
                  [class]="'qa-decision-badge qa-' + job.qaDecision.toLowerCase()">
              {{ job.qaDecision }}
            </span>
          </td>
        </ng-container>
        
        <ng-container matColumnDef="actions">
          <th mat-header-cell *matHeaderCellDef>Actions</th>
          <td mat-cell *matCellDef="let job">
            <button mat-icon-button (click)="viewAsset(job)" 
                    *ngIf="job.assetUrl"
                    matTooltip="View Asset">
              <mat-icon>visibility</mat-icon>
            </button>
          </td>
        </ng-container>
        
        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
      </table>
    </mat-card-content>
  </mat-card>
</div>
```

---

## Part 2 Complete

**Delivered:**
✅ Python QA analyzer (dead air, character verification)
✅ QA decision engine (ACCEPT/RERENDER/ABANDON)
✅ Enhanced orchestrator (triggers QA)
✅ Angular render dashboard UI

**Next:** Phase 3 (Distribution Engine) or Phase 4 (Learning Engine)

---

**Total Tasks:** 6  
**Estimated Duration:** 2-3 weeks  
**Tech Stack:** Spring Boot 4.1.1, Python 3.11, FastAPI, Angular 21, FFmpeg, OpenCV

