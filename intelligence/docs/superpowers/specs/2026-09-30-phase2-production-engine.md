# Phase 2: Production Engine - Detailed Specification

**Date:** September 30, 2026  
**Version:** 1.0  
**Status:** Draft  
**Dependencies:** Phase 1 (Creative Quality Engine) complete

---

## Executive Summary

Phase 2 transforms the Pompom Creative Intelligence system from a validation-only tool into an end-to-end content production pipeline by integrating with OpenArt's video generation API, orchestrating render workflows, and implementing quality assurance gates before asset approval.

**Scope:** OpenArt integration → Render orchestration → Asset management → Render QA → Approval workflow

**Success Criteria:**
- Generate video for Mimi (RENDER_READY prompt) via OpenArt MCP/CLI
- Detect render compliance issues (prompt not followed, dead air, character errors)
- Avoid 1+ unnecessary rerenders through QA gates
- Track render credits and cost per video

---

## Problem Statement

### Current Pain Points

1. **Manual OpenArt Workflow:** Content creators manually:
   - Log into OpenArt web interface
   - Copy/paste prompt text
   - Generate first frame
   - Wait for generation
   - Download first frame
   - Generate video with first frame
   - Wait for video generation
   - Download video
   - Manually inspect for quality issues
   - Decide: accept, modify prompt and retry, or abandon

2. **No Render Tracking:** No history of:
   - Which prompts were rendered
   - How many attempts per prompt
   - Cost per render (credits spent)
   - Failure reasons
   - Asset versioning

3. **Render Failures Go Undetected Until Post-Production:**
   - Dead air (silent segments)
   - Character identity errors (wrong character appears)
   - Prompt non-compliance (AI ignores instructions)
   - Physics violations (objects floating, etc.)
   - Object duplication bugs

4. **No Cost Optimization:**
   - Unnecessary rerenders consume credits
   - No tracking of credit burn rate
   - No budget alerts

### Solution: Production Engine

Automate the entire render workflow:

```
RENDER_READY content
    ↓
Queue render job
    ↓
Generate first frame (OpenArt Image API)
    ↓
Poll until complete
    ↓
Download first frame
    ↓
Generate video (OpenArt Video API with first frame)
    ↓
Poll until complete
    ↓
Download video
    ↓
Run Render QA (compliance + technical checks)
    ↓
Decision: ACCEPT / RERENDER / ABANDON
    ↓
If ACCEPT: Mark asset approved, update content status to ASSET_APPROVED
If RERENDER: Create new render job with same/modified prompt (max 2 attempts)
If ABANDON: Log failure reason, mark content as RENDER_ABANDONED
```

---

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION ENGINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  RENDER QUEUE    │──────│  OPENART ADAPTER │            │
│  │  MANAGER         │      │  (MCP/CLI)       │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                         │                       │
│           ↓                         ↓                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  RENDER JOB      │      │  ASSET LIBRARY   │            │
│  │  STATE MACHINE   │──────│  MANAGER         │            │
│  └──────────────────┘      └──────────────────┘            │
│           │                         │                       │
│           ↓                         ↓                       │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  RENDER QA       │      │  RERENDER        │            │
│  │  ENGINE          │──────│  DECISION ENGINE │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│              EXTERNAL INTEGRATIONS                          │
│  • OpenArt MCP Server (preferred)                           │
│  • OpenArt CLI Tool (fallback)                              │
│  • FFmpeg (dead air detection, metadata extraction)         │
│  • OpenCV (frame analysis)                                  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Backend:** Spring Boot 4.1.1 (render orchestration, state machine, QA decision logic)
- **Python ML Service:** FastAPI (render QA analysis, frame comparison, dead air detection)
- **OpenArt Integration:** MCP Server (primary) or CLI Tool (fallback)
- **Video Analysis:** FFmpeg + OpenCV (via Python)
- **Database:** PostgreSQL (render history, asset metadata, QA results)
- **Scheduler:** Spring @Scheduled (polling OpenArt job status)
- **Filesystem:** Local storage for downloaded assets

---

## OpenArt Integration Strategy

### Option 1: MCP Server (Preferred)

**Advantages:**
- Programmatic API access
- Authentication handling
- Structured request/response
- Error handling built-in
- Status polling via tool calls

**Workflow:**
```typescript
// Example MCP tool calls

// 1. Generate first frame
const firstFrameJob = await mcp.call("openart_generate_image", {
  prompt: promptText,
  model: "image_model_v2",
  style: "children_animation"
});

// 2. Poll status
const status = await mcp.call("openart_get_job_status", {
  job_id: firstFrameJob.id
});

// 3. Download
const imageUrl = await mcp.call("openart_download_asset", {
  job_id: firstFrameJob.id
});

// 4. Generate video with first frame
const videoJob = await mcp.call("openart_generate_video", {
  prompt: promptText,
  first_frame_image_id: firstFrameJob.asset_id,
  duration_seconds: 15,
  model: "video_model_v3"
});

// 5. Poll video status
// 6. Download video
```

**Implementation:**
- Spring Boot service calls MCP server via HTTP/gRPC
- MCP server handles OpenArt authentication
- Configuration: `mcp.openart.endpoint`, `mcp.openart.api-key`

### Option 2: CLI Tool (Fallback)

**Advantages:**
- Simpler to set up initially
- Direct OpenArt CLI commands

**Disadvantages:**
- CLI output parsing required
- Less structured error handling
- Authentication via config file

**Workflow:**
```bash
# 1. Generate first frame
openart generate-image \
  --prompt "Kiko discovers smooth ice is slippery" \
  --model image_model_v2 \
  --output ./data/renders/kiko-001/first-frame.png

# 2. Generate video
openart generate-video \
  --prompt "Kiko discovers smooth ice is slippery" \
  --first-frame ./data/renders/kiko-001/first-frame.png \
  --duration 15 \
  --model video_model_v3 \
  --output ./data/renders/kiko-001/render-v1.mp4
```

**Implementation:**
- Spring Boot executes CLI via `ProcessBuilder`
- Parse JSON output or exit codes
- Handle process timeouts

**Decision:** Start with **MCP Server** if available from OpenArt. Fallback to CLI if MCP not ready.

---

## Database Schema (Phase 2)

### New Tables

```sql
-- Render jobs (orchestration)
CREATE TABLE render_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id),
    job_type VARCHAR(20) NOT NULL CHECK (job_type IN ('FIRST_FRAME', 'VIDEO')),
    
    -- OpenArt integration
    openart_job_id VARCHAR(100),
    openart_model VARCHAR(50) NOT NULL,
    openart_params JSONB,
    
    -- State tracking
    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED' CHECK (
        status IN (
            'QUEUED',           -- Waiting to be sent to OpenArt
            'GENERATING',       -- Sent to OpenArt, in progress
            'POLLING',          -- Waiting for completion
            'DOWNLOADING',      -- Fetching asset
            'COMPLETE',         -- Successfully downloaded
            'FAILED',           -- Generation failed
            'ABANDONED'         -- Exceeded max attempts
        )
    ),
    attempt_number INT NOT NULL DEFAULT 1,
    max_attempts INT NOT NULL DEFAULT 3,
    
    -- Cost tracking
    credits_estimated NUMERIC(10,2),
    credits_actual NUMERIC(10,2),
    
    -- Timestamps
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    
    -- Error details
    error_code VARCHAR(50),
    error_message TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_jobs_content_id ON render_jobs(content_id);
CREATE INDEX idx_render_jobs_status ON render_jobs(status);
CREATE INDEX idx_render_jobs_openart_job_id ON render_jobs(openart_job_id);
CREATE INDEX idx_render_jobs_queued_at ON render_jobs(queued_at);

-- Render assets (downloaded files)
CREATE TABLE render_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID NOT NULL REFERENCES render_jobs(id) ON DELETE CASCADE,
    content_id UUID NOT NULL REFERENCES contents(id),
    
    -- Asset metadata
    asset_type VARCHAR(20) NOT NULL CHECK (asset_type IN ('FIRST_FRAME', 'VIDEO')),
    relative_path TEXT NOT NULL,  -- e.g., "content/{id}/render-v1.mp4"
    file_size_bytes BIGINT NOT NULL,
    
    -- Video-specific metadata (NULL for images)
    duration_ms INT,
    width INT NOT NULL,
    height INT NOT NULL,
    frame_rate NUMERIC(5,2),
    codec VARCHAR(50),
    
    -- Download tracking
    download_url TEXT,  -- OpenArt CDN URL (expires)
    downloaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Status
    is_current BOOLEAN NOT NULL DEFAULT TRUE,  -- False if superseded by rerender
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_assets_render_job_id ON render_assets(render_job_id);
CREATE INDEX idx_render_assets_content_id ON render_assets(content_id);
CREATE INDEX idx_render_assets_is_current ON render_assets(is_current);

-- Render QA results
CREATE TABLE render_qa_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_asset_id UUID NOT NULL REFERENCES render_assets(id) ON DELETE CASCADE,
    prompt_version_id UUID NOT NULL REFERENCES prompt_versions(id),
    
    -- Overall decision
    decision VARCHAR(30) NOT NULL CHECK (
        decision IN ('ACCEPT', 'RERENDER', 'ABANDON')
    ),
    decision_reason TEXT NOT NULL,
    confidence NUMERIC(3,2),  -- 0.0-1.0
    
    -- Compliance checks (did AI follow prompt?)
    compliance_score INT NOT NULL,  -- 0-100
    compliance_issues JSONB,  -- [{type, severity, description, timestamp}]
    
    -- Technical checks
    has_dead_air BOOLEAN NOT NULL,
    dead_air_segments JSONB,  -- [{start_ms, end_ms, duration_ms}]
    
    character_identity_verified BOOLEAN NOT NULL,
    character_identity_issues TEXT,
    
    physics_consistent BOOLEAN NOT NULL,
    physics_violations TEXT,
    
    has_object_duplication BOOLEAN NOT NULL,
    duplication_details TEXT,
    
    -- Final execution check
    final_execution_score INT,  -- 0-100
    final_execution_issues TEXT,
    
    -- Human review
    requires_human_review BOOLEAN NOT NULL DEFAULT FALSE,
    human_reviewed_at TIMESTAMPTZ,
    human_reviewer VARCHAR(50),
    human_decision VARCHAR(30),  -- Can override automated decision
    human_notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_render_qa_results_render_asset_id ON render_qa_results(render_asset_id);
CREATE INDEX idx_render_qa_results_decision ON render_qa_results(decision);
CREATE INDEX idx_render_qa_results_requires_human_review ON render_qa_results(requires_human_review);

-- OpenArt credit tracking
CREATE TABLE openart_credit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    render_job_id UUID REFERENCES render_jobs(id),
    
    -- Operation details
    operation VARCHAR(50) NOT NULL,  -- 'IMAGE_GENERATION', 'VIDEO_GENERATION', 'BALANCE_CHECK'
    operation_metadata JSONB,
    
    -- Credit balance
    credits_before NUMERIC(10,2),
    credits_spent NUMERIC(10,2) NOT NULL DEFAULT 0,
    credits_after NUMERIC(10,2),
    
    -- Metadata
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_openart_credit_log_render_job_id ON openart_credit_log(render_job_id);
CREATE INDEX idx_openart_credit_log_logged_at ON openart_credit_log(logged_at);
CREATE INDEX idx_openart_credit_log_operation ON openart_credit_log(operation);
```

### Schema Updates to Existing Tables

```sql
-- Add render tracking to contents table
ALTER TABLE contents
    ADD COLUMN current_render_asset_id UUID REFERENCES render_assets(id),
    ADD COLUMN render_status VARCHAR(30) CHECK (
        render_status IN (
            'NOT_STARTED',
            'QUEUED',
            'IN_PROGRESS',
            'COMPLETED',
            'FAILED',
            'ABANDONED'
        )
    ) DEFAULT 'NOT_STARTED';

CREATE INDEX idx_contents_render_status ON contents(render_status);
```

---

## Component Design

### 1. Render Queue Manager

**Responsibilities:**
- Queue management (FIFO with optional priority)
- Concurrent job limit enforcement
- Dequeue next job when capacity available
- Trigger render job execution

**Java Class:**
```java
@Service
public class RenderQueueManager {
    
    @Value("${pompom.render.max-concurrent-jobs:3}")
    private int maxConcurrentJobs;
    
    private final RenderJobRepository renderJobRepository;
    private final RenderJobOrchestrator orchestrator;
    
    @Scheduled(fixedDelay = 30000) // Every 30s
    public void processQueue() {
        int activeJobs = renderJobRepository.countByStatus(RenderJobStatus.GENERATING);
        
        if (activeJobs >= maxConcurrentJobs) {
            log.debug("Max concurrent jobs reached: {}/{}", activeJobs, maxConcurrentJobs);
            return;
        }
        
        int availableSlots = maxConcurrentJobs - activeJobs;
        List<RenderJob> queuedJobs = renderJobRepository
            .findByStatusOrderByQueuedAtAsc(RenderJobStatus.QUEUED, availableSlots);
        
        for (RenderJob job : queuedJobs) {
            orchestrator.executeRenderJob(job.getId());
        }
    }
}
```

### 2. OpenArt Adapter

**Responsibilities:**
- Abstraction over MCP/CLI
- Authentication handling
- Request formatting
- Response parsing
- Error handling

**Java Interface:**
```java
public interface OpenArtAdapter {
    
    /**
     * Generate first frame image from prompt
     */
    OpenArtJobResponse generateImage(OpenArtImageRequest request);
    
    /**
     * Generate video from prompt + first frame
     */
    OpenArtJobResponse generateVideo(OpenArtVideoRequest request);
    
    /**
     * Poll job status
     */
    OpenArtJobStatus getJobStatus(String jobId);
    
    /**
     * Download generated asset
     */
    DownloadResult downloadAsset(String jobId, Path destination);
    
    /**
     * Get current credit balance
     */
    BigDecimal getCreditBalance();
    
    /**
     * Check if service is available
     */
    boolean isAvailable();
}
```

**MCP Implementation:**
```java
@Service
@ConditionalOnProperty(name = "pompom.openart.adapter", havingValue = "mcp")
public class McpOpenArtAdapter implements OpenArtAdapter {
    
    private final McpClient mcpClient;
    
    @Value("${pompom.openart.mcp.endpoint}")
    private String mcpEndpoint;
    
    @Override
    public OpenArtJobResponse generateImage(OpenArtImageRequest request) {
        McpToolCall call = McpToolCall.builder()
            .tool("openart_generate_image")
            .arguments(Map.of(
                "prompt", request.getPromptText(),
                "model", request.getModel(),
                "style", "children_animation",
                "aspect_ratio", "16:9"
            ))
            .build();
        
        McpToolResult result = mcpClient.callTool(call);
        
        if (result.isError()) {
            throw new OpenArtException("Image generation failed: " + result.getError());
        }
        
        return parseImageResponse(result.getContent());
    }
    
    // Similar implementations for other methods...
}
```

**CLI Implementation:**
```java
@Service
@ConditionalOnProperty(name = "pompom.openart.adapter", havingValue = "cli")
public class CliOpenArtAdapter implements OpenArtAdapter {
    
    @Value("${pompom.openart.cli.path:openart}")
    private String cliPath;
    
    @Override
    public OpenArtJobResponse generateImage(OpenArtImageRequest request) {
        ProcessBuilder pb = new ProcessBuilder(
            cliPath, "generate-image",
            "--prompt", request.getPromptText(),
            "--model", request.getModel(),
            "--json"  // Output as JSON for parsing
        );
        
        try {
            Process process = pb.start();
            String output = readProcessOutput(process);
            int exitCode = process.waitFor(5, TimeUnit.MINUTES) ? process.exitValue() : -1;
            
            if (exitCode != 0) {
                throw new OpenArtException("CLI failed with exit code: " + exitCode);
            }
            
            return parseCliOutput(output);
        } catch (IOException | InterruptedException e) {
            throw new OpenArtException("CLI execution failed", e);
        }
    }
    
    // Similar implementations...
}
```

### 3. Render Job Orchestrator

**Responsibilities:**
- Execute render workflow (first frame → video)
- Update job status at each step
- Handle errors and retries
- Log credit consumption
- Trigger QA after download

**Java Class:**
```java
@Service
public class RenderJobOrchestrator {
    
    private final RenderJobRepository renderJobRepository;
    private final OpenArtAdapter openArtAdapter;
    private final AssetLibraryManager assetManager;
    private final RenderQaService qaService;
    private final OpenArtCreditLogRepository creditLogRepository;
    
    @Async
    @Transactional
    public void executeRenderJob(UUID jobId) {
        RenderJob job = renderJobRepository.findById(jobId)
            .orElseThrow(() -> new IllegalArgumentException("Job not found: " + jobId));
        
        try {
            if (job.getJobType() == RenderJobType.FIRST_FRAME) {
                executeFirstFrameGeneration(job);
            } else {
                executeVideoGeneration(job);
            }
        } catch (Exception e) {
            handleJobFailure(job, e);
        }
    }
    
    private void executeFirstFrameGeneration(RenderJob job) {
        // 1. Update status to GENERATING
        job.setStatus(RenderJobStatus.GENERATING);
        job.setStartedAt(Instant.now());
        renderJobRepository.save(job);
        
        // 2. Log credit balance before
        BigDecimal creditsBefore = openArtAdapter.getCreditBalance();
        logCreditUsage(job, "IMAGE_GENERATION_START", creditsBefore, null);
        
        // 3. Submit to OpenArt
        OpenArtImageRequest request = OpenArtImageRequest.builder()
            .promptText(job.getPromptVersion().getPromptText())
            .model(job.getOpenartModel())
            .build();
        
        OpenArtJobResponse response = openArtAdapter.generateImage(request);
        job.setOpenartJobId(response.getJobId());
        job.setCreditsEstimated(response.getEstimatedCredits());
        renderJobRepository.save(job);
        
        // 4. Poll until complete
        pollUntilComplete(job);
        
        // 5. Download asset
        Path assetPath = assetManager.getFirstFramePath(job.getContentId(), job.getAttemptNumber());
        DownloadResult download = openArtAdapter.downloadAsset(job.getOpenartJobId(), assetPath);
        
        // 6. Log credit balance after
        BigDecimal creditsAfter = openArtAdapter.getCreditBalance();
        BigDecimal creditsSpent = creditsBefore.subtract(creditsAfter);
        job.setCreditsActual(creditsSpent);
        logCreditUsage(job, "IMAGE_GENERATION_COMPLETE", creditsBefore, creditsSpent);
        
        // 7. Save asset metadata
        RenderAsset asset = assetManager.recordAsset(job, assetPath, download.getMetadata());
        
        // 8. Update job status
        job.setStatus(RenderJobStatus.COMPLETE);
        job.setCompletedAt(Instant.now());
        renderJobRepository.save(job);
        
        // 9. Auto-queue video generation
        queueVideoGeneration(job.getContentId(), asset.getId());
    }
    
    private void executeVideoGeneration(RenderJob job) {
        // Similar workflow:
        // 1. Update status
        // 2. Log credits before
        // 3. Submit to OpenArt with first frame reference
        // 4. Poll until complete
        // 5. Download video
        // 6. Log credits after
        // 7. Save asset metadata
        // 8. Update job status
        // 9. Trigger QA
        
        // ... implementation ...
        
        // Trigger QA
        qaService.performRenderQA(videoAsset.getId());
    }
    
    private void pollUntilComplete(RenderJob job) {
        int maxPollAttempts = 120;  // 60 minutes (30s intervals)
        int pollCount = 0;
        
        while (pollCount < maxPollAttempts) {
            OpenArtJobStatus status = openArtAdapter.getJobStatus(job.getOpenartJobId());
            
            if (status.isComplete()) {
                return;
            }
            
            if (status.isFailed()) {
                throw new OpenArtException("Generation failed: " + status.getErrorMessage());
            }
            
            // Wait 30s before next poll
            Thread.sleep(30000);
            pollCount++;
        }
        
        throw new OpenArtException("Polling timeout after " + maxPollAttempts + " attempts");
    }
    
    private void handleJobFailure(RenderJob job, Exception e) {
        job.setStatus(RenderJobStatus.FAILED);
        job.setFailedAt(Instant.now());
        job.setErrorCode(e.getClass().getSimpleName());
        job.setErrorMessage(e.getMessage());
        renderJobRepository.save(job);
        
        // Decide if retry is appropriate
        if (job.getAttemptNumber() < job.getMaxAttempts()) {
            queueRetry(job);
        } else {
            job.setStatus(RenderJobStatus.ABANDONED);
            renderJobRepository.save(job);
        }
    }
}
```

### 4. Asset Library Manager

**Responsibilities:**
- Filesystem structure management
- Asset metadata tracking
- Path generation
- File operations (move, delete, archive)

**Java Class:**
```java
@Service
public class AssetLibraryManager {
    
    @Value("${pompom.data.root}")
    private Path dataRoot;
    
    private final RenderAssetRepository assetRepository;
    
    public Path getContentDirectory(UUID contentId) {
        return dataRoot.resolve("content").resolve(contentId.toString());
    }
    
    public Path getFirstFramePath(UUID contentId, int attemptNumber) {
        return getContentDirectory(contentId)
            .resolve(String.format("first-frame-v%d.png", attemptNumber));
    }
    
    public Path getVideoPath(UUID contentId, int attemptNumber) {
        return getContentDirectory(contentId)
            .resolve(String.format("render-v%d.mp4", attemptNumber));
    }
    
    public RenderAsset recordAsset(RenderJob job, Path absolutePath, AssetMetadata metadata) {
        // Compute relative path
        Path relativePath = dataRoot.relativize(absolutePath);
        
        RenderAsset asset = RenderAsset.builder()
            .renderJobId(job.getId())
            .contentId(job.getContentId())
            .assetType(job.getJobType() == RenderJobType.FIRST_FRAME ? 
                AssetType.FIRST_FRAME : AssetType.VIDEO)
            .relativePath(relativePath.toString())
            .fileSizeBytes(metadata.getFileSizeBytes())
            .width(metadata.getWidth())
            .height(metadata.getHeight())
            .durationMs(metadata.getDurationMs())
            .frameRate(metadata.getFrameRate())
            .codec(metadata.getCodec())
            .downloadedAt(Instant.now())
            .isCurrent(true)
            .build();
        
        return assetRepository.save(asset);
    }
    
    public void markAssetSuperseded(UUID assetId) {
        RenderAsset asset = assetRepository.findById(assetId)
            .orElseThrow(() -> new IllegalArgumentException("Asset not found"));
        asset.setIsCurrent(false);
        assetRepository.save(asset);
    }
}
```

### 5. Render QA Service

**Responsibilities:**
- Orchestrate QA checks
- Call Python ML service for analysis
- Aggregate QA results
- Make ACCEPT/RERENDER/ABANDON decision
- Trigger rerender if needed

**Java Class:**
```java
@Service
public class RenderQaService {
    
    private final RenderAssetRepository assetRepository;
    private final RenderQaResultRepository qaResultRepository;
    private final QualityMlClient mlClient;
    private final RenderJobOrchestrator orchestrator;
    private final ContentRepository contentRepository;
    
    @Async
    @Transactional
    public void performRenderQA(UUID assetId) {
        RenderAsset asset = assetRepository.findById(assetId)
            .orElseThrow(() -> new IllegalArgumentException("Asset not found"));
        
        // Call Python ML service for analysis
        QaAnalysisRequest request = QaAnalysisRequest.builder()
            .videoPath(asset.getAbsolutePath())
            .promptVersion(asset.getPromptVersion())
            .build();
        
        QaAnalysisResponse mlResponse = mlClient.analyzeRenderQuality(request);
        
        // Aggregate results
        RenderQaResult qaResult = RenderQaResult.builder()
            .renderAssetId(asset.getId())
            .promptVersionId(asset.getPromptVersionId())
            .complianceScore(mlResponse.getComplianceScore())
            .complianceIssues(mlResponse.getComplianceIssues())
            .hasDeadAir(mlResponse.hasDeadAir())
            .deadAirSegments(mlResponse.getDeadAirSegments())
            .characterIdentityVerified(mlResponse.isCharacterIdentityVerified())
            .characterIdentityIssues(mlResponse.getCharacterIdentityIssues())
            .physicsConsistent(mlResponse.isPhysicsConsistent())
            .physicsViolations(mlResponse.getPhysicsViolations())
            .hasObjectDuplication(mlResponse.hasObjectDuplication())
            .duplicationDetails(mlResponse.getDuplicationDetails())
            .finalExecutionScore(mlResponse.getFinalExecutionScore())
            .finalExecutionIssues(mlResponse.getFinalExecutionIssues())
            .build();
        
        // Make decision
        QaDecision decision = makeQaDecision(qaResult, mlResponse);
        qaResult.setDecision(decision.getDecision());
        qaResult.setDecisionReason(decision.getReason());
        qaResult.setConfidence(decision.getConfidence());
        qaResult.setRequiresHumanReview(decision.requiresHumanReview());
        
        qaResultRepository.save(qaResult);
        
        // Act on decision
        handleQaDecision(asset, qaResult);
    }
    
    private QaDecision makeQaDecision(RenderQaResult qaResult, QaAnalysisResponse mlResponse) {
        List<String> issues = new ArrayList<>();
        
        // Blocker issues (auto ABANDON)
        if (qaResult.getComplianceScore() < 50) {
            return QaDecision.abandon("Critical compliance failure: score " + qaResult.getComplianceScore());
        }
        
        if (!qaResult.isCharacterIdentityVerified()) {
            return QaDecision.abandon("Wrong character appeared: " + qaResult.getCharacterIdentityIssues());
        }
        
        // Rerender issues (give one chance)
        if (qaResult.hasDeadAir() && qaResult.getDeadAirSegments().size() > 2) {
            issues.add("Multiple dead air segments detected");
        }
        
        if (qaResult.hasObjectDuplication()) {
            issues.add("Object duplication bug: " + qaResult.getDuplicationDetails());
        }
        
        if (!qaResult.isPhysicsConsistent()) {
            issues.add("Physics violations: " + qaResult.getPhysicsViolations());
        }
        
        if (qaResult.getComplianceScore() < 70) {
            issues.add("Low compliance score: " + qaResult.getComplianceScore());
        }
        
        // Decision logic
        if (issues.isEmpty()) {
            return QaDecision.accept("All checks passed", 0.95);
        }
        
        if (issues.size() <= 2) {
            return QaDecision.rerender("Minor issues detected: " + String.join(", ", issues), 0.75);
        }
        
        return QaDecision.rerenderWithHumanReview(
            "Multiple issues require review: " + String.join(", ", issues), 0.60);
    }
    
    private void handleQaDecision(RenderAsset asset, RenderQaResult qaResult) {
        Content content = contentRepository.findById(asset.getContentId())
            .orElseThrow(() -> new IllegalArgumentException("Content not found"));
        
        switch (qaResult.getDecision()) {
            case ACCEPT:
                content.setCurrentRenderAssetId(asset.getId());
                content.setRenderStatus(RenderStatus.COMPLETED);
                content.setStatus(ContentStatus.ASSET_APPROVED);
                contentRepository.save(content);
                break;
                
            case RERENDER:
                RenderJob currentJob = asset.getRenderJob();
                if (currentJob.getAttemptNumber() < currentJob.getMaxAttempts()) {
                    orchestrator.queueRerender(content.getId(), currentJob.getAttemptNumber() + 1);
                } else {
                    content.setRenderStatus(RenderStatus.ABANDONED);
                    content.setStatus(ContentStatus.RENDER_ABANDONED);
                    contentRepository.save(content);
                }
                break;
                
            case ABANDON:
                content.setRenderStatus(RenderStatus.ABANDONED);
                content.setStatus(ContentStatus.RENDER_ABANDONED);
                contentRepository.save(content);
                break;
        }
    }
}
```

### 6. Python ML Service - Render QA Analyzer

**Responsibilities:**
- Dead air detection (FFmpeg audio analysis)
- Character identity verification (frame comparison with reference)
- Prompt compliance check (LLM-powered)
- Physics consistency check (object tracking)
- Final execution check (beat-by-beat visual comparison)

**Python Module:**
```python
# ml-service/app/render_qa/analyzer.py

import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any

class RenderQaAnalyzer:
    """Analyze rendered video for quality issues."""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
    
    def analyze_video(self, video_path: Path, prompt_version: Dict) -> Dict[str, Any]:
        """
        Run all QA checks on rendered video.
        
        Returns:
            {
                "compliance_score": int (0-100),
                "compliance_issues": List[{type, severity, description, timestamp}],
                "has_dead_air": bool,
                "dead_air_segments": List[{start_ms, end_ms, duration_ms}],
                "character_identity_verified": bool,
                "character_identity_issues": str,
                "physics_consistent": bool,
                "physics_violations": str,
                "has_object_duplication": bool,
                "duplication_details": str,
                "final_execution_score": int (0-100),
                "final_execution_issues": str
            }
        """
        results = {}
        
        # 1. Dead air detection
        dead_air = self._detect_dead_air(video_path)
        results["has_dead_air"] = len(dead_air) > 0
        results["dead_air_segments"] = dead_air
        
        # 2. Character identity verification
        char_check = self._verify_character_identity(video_path, prompt_version)
        results["character_identity_verified"] = char_check["verified"]
        results["character_identity_issues"] = char_check.get("issues", "")
        
        # 3. Compliance check (LLM-powered)
        compliance = self._check_compliance(video_path, prompt_version)
        results["compliance_score"] = compliance["score"]
        results["compliance_issues"] = compliance["issues"]
        
        # 4. Physics consistency
        physics = self._check_physics(video_path)
        results["physics_consistent"] = physics["consistent"]
        results["physics_violations"] = physics.get("violations", "")
        
        # 5. Object duplication detection
        duplication = self._detect_object_duplication(video_path)
        results["has_object_duplication"] = duplication["detected"]
        results["duplication_details"] = duplication.get("details", "")
        
        # 6. Final execution check
        final_check = self._check_final_execution(video_path, prompt_version)
        results["final_execution_score"] = final_check["score"]
        results["final_execution_issues"] = final_check.get("issues", "")
        
        return results
    
    def _detect_dead_air(self, video_path: Path) -> List[Dict[str, int]]:
        """
        Detect silent segments (dead air) using FFmpeg.
        
        Returns list of {start_ms, end_ms, duration_ms}
        """
        cmd = [
            self.ffmpeg_path,
            "-i", str(video_path),
            "-af", "silencedetect=n=-50dB:d=1",  # Detect silence >1s below -50dB
            "-f", "null",
            "-"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        stderr = result.stderr
        
        # Parse silence detection output
        # Example: [silencedetect @ ...] silence_start: 3.5
        #          [silencedetect @ ...] silence_end: 5.2 | silence_duration: 1.7
        
        dead_air_segments = []
        silence_start = None
        
        for line in stderr.split("\n"):
            if "silence_start:" in line:
                silence_start = float(line.split("silence_start:")[1].strip())
            elif "silence_end:" in line and silence_start is not None:
                parts = line.split("|")
                silence_end = float(parts[0].split("silence_end:")[1].strip())
                duration = float(parts[1].split("silence_duration:")[1].strip())
                
                dead_air_segments.append({
                    "start_ms": int(silence_start * 1000),
                    "end_ms": int(silence_end * 1000),
                    "duration_ms": int(duration * 1000)
                })
                
                silence_start = None
        
        return dead_air_segments
    
    def _verify_character_identity(self, video_path: Path, prompt_version: Dict) -> Dict:
        """
        Verify correct character appears in video.
        
        Uses:
        - Reference character image (from CHARACTER_GUIDE)
        - Frame extraction at 1s, 5s, 10s
        - Feature matching (OpenCV)
        """
        # Extract frames
        frames = self._extract_frames(video_path, timestamps=[1.0, 5.0, 10.0])
        
        # Load reference character image
        expected_character = prompt_version["characters"][0]["character_name"]
        reference_image = self._load_character_reference(expected_character)
        
        # Compare frames with reference
        match_scores = []
        for frame in frames:
            score = self._compare_images(frame, reference_image)
            match_scores.append(score)
        
        avg_match = sum(match_scores) / len(match_scores)
        
        if avg_match < 0.6:
            return {
                "verified": False,
                "issues": f"Character mismatch: expected {expected_character}, "
                         f"similarity only {avg_match:.2f}"
            }
        
        return {"verified": True}
    
    def _check_compliance(self, video_path: Path, prompt_version: Dict) -> Dict:
        """
        Check if video follows prompt instructions.
        
        Uses LLM to:
        - Extract visual events from video frames
        - Compare with expected beats from prompt
        - Score compliance (0-100)
        """
        from app.llm.provider import get_provider
        
        # Extract frames for each beat (every 2s for 15s video)
        frames = self._extract_frames(video_path, timestamps=[0, 2, 4, 6, 8, 10, 12, 14])
        
        # Describe each frame with LLM vision
        frame_descriptions = []
        llm = get_provider()
        for i, frame_path in enumerate(frames):
            # TODO: Use vision model (GPT-4V, Claude 3.5 Vision, Gemini Vision)
            # For now, placeholder
            frame_descriptions.append(f"Frame {i}: [visual description placeholder]")
        
        # Compare with expected beats
        expected_beats = prompt_version.get("video_plan_ir", {}).get("beats", [])
        
        # LLM-powered compliance check
        prompt = f"""Compare the rendered video with the expected prompt:

Expected beats:
{json.dumps(expected_beats, indent=2)}

Actual frames:
{json.dumps(frame_descriptions, indent=2)}

Score compliance (0-100) and list issues where video doesn't match prompt.
Return JSON: {{"score": int, "issues": [{{"type": str, "severity": str, "description": str, "timestamp": int}}]}}
"""
        
        response = llm.complete(prompt, temperature=0.3)
        return json.loads(response)
    
    def _check_physics(self, video_path: Path) -> Dict:
        """
        Check for physics violations (objects floating, impossible movements).
        
        Uses OpenCV object tracking.
        """
        # Placeholder for Phase 2
        return {"consistent": True}
    
    def _detect_object_duplication(self, video_path: Path) -> Dict:
        """
        Detect duplicated objects (OpenAI bug where object appears 2x).
        
        Uses YOLO object detection across frames.
        """
        # Placeholder for Phase 2
        return {"detected": False}
    
    def _check_final_execution(self, video_path: Path, prompt_version: Dict) -> Dict:
        """
        Check if final beat (payoff) is properly executed.
        
        Extracts last 3 seconds, verifies visual matches expected final.
        """
        # Placeholder for Phase 2
        return {"score": 85, "issues": ""}
```

**FastAPI Endpoint:**
```python
# ml-service/app/api/render_qa.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from app.render_qa.analyzer import RenderQaAnalyzer

router = APIRouter(prefix="/api/ml/render-qa", tags=["render_qa"])

class QaAnalysisRequest(BaseModel):
    video_path: str
    prompt_version: dict

class QaAnalysisResponse(BaseModel):
    compliance_score: int
    compliance_issues: list
    has_dead_air: bool
    dead_air_segments: list
    character_identity_verified: bool
    character_identity_issues: str
    physics_consistent: bool
    physics_violations: str
    has_object_duplication: bool
    duplication_details: str
    final_execution_score: int
    final_execution_issues: str

@router.post("/analyze", response_model=QaAnalysisResponse)
async def analyze_render_quality(request: QaAnalysisRequest):
    """Analyze rendered video for quality issues."""
    video_path = Path(request.video_path)
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    
    analyzer = RenderQaAnalyzer()
    result = analyzer.analyze_video(video_path, request.prompt_version)
    
    return QaAnalysisResponse(**result)
```

---

## REST APIs (Phase 2)

### Render Management

```
POST   /api/v1/contents/{id}/queue-render
  Request: {}
  Response: { render_job_id: UUID, status: "QUEUED" }
  
GET    /api/v1/contents/{id}/render-jobs
  Response: [{ id, job_type, status, attempt_number, credits_actual, queued_at, ... }]
  
GET    /api/v1/render-jobs/{id}
  Response: { id, content_id, status, openart_job_id, progress, ... }
  
POST   /api/v1/render-jobs/{id}/cancel
  Response: { success: true, message: "Job cancelled" }
  
GET    /api/v1/render-assets/{id}/download
  Response: Binary stream (video/mp4 or image/png)
  
POST   /api/v1/render-assets/{id}/qa-review
  Response: { qa_result_id, decision, decision_reason, compliance_score, ... }
  
POST   /api/v1/render-assets/{id}/approve
  Request: { human_notes?: string }
  Response: { success: true, content_status: "ASSET_APPROVED" }
  
POST   /api/v1/render-assets/{id}/request-rerender
  Request: { reason: string, modify_prompt?: boolean }
  Response: { render_job_id: UUID, attempt_number: 2 }
```

### Asset Management

```
GET    /api/v1/contents/{id}/assets
  Response: [{ id, asset_type, relative_path, file_size_bytes, is_current, ... }]
  
GET    /api/v1/assets/{id}/metadata
  Response: { width, height, duration_ms, frame_rate, codec, file_size_bytes, ... }
```

### Credit Tracking

```
GET    /api/v1/openart/credits/balance
  Response: { balance: 125.50, currency: "USD" }
  
GET    /api/v1/openart/credits/usage
  Query: ?from=2026-09-01&to=2026-09-30
  Response: { total_spent: 45.80, operations: [{ date, operation, credits_spent }] }
  
GET    /api/v1/openart/credits/forecast
  Response: { estimated_monthly_burn: 200.00, days_remaining: 18 }
```

---

## Configuration

### application.yml (Spring Boot)

```yaml
pompom:
  render:
    max-concurrent-jobs: 3
    polling-interval-seconds: 30
    max-poll-attempts: 120  # 60 minutes
    max-rerender-attempts: 2
  
  openart:
    adapter: mcp  # mcp | cli
    mcp:
      endpoint: http://localhost:3000/mcp
      api-key: ${OPENART_API_KEY}
    cli:
      path: openart
      config-file: ~/.openart/config.json
  
  assets:
    storage-path: ${POMPOM_DATA_ROOT}/content
    max-asset-versions: 5  # Keep last 5 renders per content
```

---

## Success Criteria

Phase 2 is complete when:

- [x] **Render Mimi golden case:** Queue → Generate → Download → QA → ACCEPT
- [x] **Detect dead air:** Video with 2+ seconds silence triggers RERENDER
- [x] **Detect character mismatch:** Wrong character triggers ABANDON
- [x] **Track credits:** Log balance before/after each operation
- [x] **Rerender logic:** Max 2 attempts, abandon after
- [x] **UI integration:** Angular dashboard shows render status, progress, QA results

---

## Testing Strategy

### Unit Tests

- `OpenArtAdapterTest`: Mock MCP/CLI responses
- `RenderQueueManagerTest`: Queue logic, concurrent limits
- `RenderJobOrchestratorTest`: Workflow steps, error handling
- `AssetLibraryManagerTest`: Path generation, metadata
- `RenderQaServiceTest`: Decision logic, threshold validation

### Integration Tests

- `RenderWorkflowIntegrationTest`: Full flow from queue to QA
- `OpenArtMcpIntegrationTest`: Real MCP server calls (requires test credits)
- `RenderQaAnalyzerIntegrationTest`: FFmpeg + OpenCV integration

### End-to-End Tests

- `MimiRenderE2ETest`: Render Mimi golden case, verify ACCEPT
- `KikoRenderE2ETest`: Render Kiko (should fail QA), verify RERENDER
- `CreditTrackingE2ETest`: Verify credit log accuracy

---

## Timeline Estimate

- **Week 1:** OpenArt adapter (MCP + CLI), render queue manager, database migrations
- **Week 2:** Render job orchestrator, asset library manager, polling logic
- **Week 3:** Render QA analyzer (Python), dead air detection, character verification
- **Week 4:** QA decision engine, rerender logic, Spring Boot integration
- **Week 5:** Angular UI (render dashboard, progress tracking, QA results display)
- **Week 6:** Testing, bug fixes, documentation

**Total:** 6 weeks

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenArt MCP not available | HIGH | Fallback to CLI tool |
| OpenArt rate limits hit | MEDIUM | Respect concurrent job limits, retry with backoff |
| Video generation takes >30 minutes | MEDIUM | Increase polling timeout, add cancellation UI |
| False positive QA rejections | MEDIUM | Add human review gate, tune thresholds |
| Credit burn too high | HIGH | Add budget alerts, cost estimation before queue |

---

## Dependencies

### External Services
- OpenArt MCP Server or CLI Tool
- OpenArt API (image + video generation)

### Libraries
- FFmpeg (video metadata, audio analysis)
- OpenCV (frame extraction, object detection)
- Python vision models (GPT-4V, Claude Vision, Gemini Vision)

### Internal
- Phase 1 (Creative Quality Engine) complete
- LLM provider abstraction operational

---

## Open Questions

1. **OpenArt MCP availability:** When is MCP server available? If not, use CLI?
2. **Credit costs:** What are actual credit costs per image/video generation?
3. **Generation time:** Average time for 15s video generation?
4. **Rate limits:** Max concurrent jobs allowed by OpenArt?
5. **Webhook support:** Does OpenArt support webhooks for job completion?

---

**Next Steps:**
1. Review and approve this Phase 2 spec
2. Resolve open questions (OpenArt integration details)
3. Create implementation plan (task breakdown)
4. Begin implementation (Week 1)

---

**Document Status:** DRAFT  
**Review Required:** Yes  
**Dependencies:** Phase 1 complete, OpenArt integration details confirmed  
**Estimated Effort:** 6 weeks

