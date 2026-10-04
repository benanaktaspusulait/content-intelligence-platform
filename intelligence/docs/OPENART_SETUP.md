# OpenArt Integration Setup

This document describes how to set up the real OpenArt adapter for production use.

## Overview

The system supports two OpenArt adapters:
- **Mock Adapter** (default): For development and testing, no external dependencies
- **Real Adapter**: Production adapter using OpenArt CLI tool

## Prerequisites

### 1. OpenArt CLI Installation

The real adapter requires OpenArt CLI tool to be installed and accessible in PATH.

**Installation** (example - adjust based on actual OpenArt CLI):

```bash
# Via npm (if OpenArt CLI is distributed as npm package)
npm install -g @openart/cli

# Or via pip (if Python-based)
pip install openart-cli

# Or download binary from OpenArt website
curl -L https://openart.ai/cli/download | bash
```

**Verify installation:**

```bash
openart --version
# Should output: OpenArt CLI v1.2.3 (or similar)
```

### 2. OpenArt API Key

Obtain an API key from OpenArt:
1. Sign up at https://openart.ai
2. Navigate to API settings
3. Generate a new API key
4. Save the key securely

## Configuration

### Environment Variables

Set these environment variables before starting the application:

```bash
# Enable real OpenArt adapter
export OPENART_ENABLED=true

# Disable mock adapter
export OPENART_MOCK_ENABLED=false

# OpenArt API key (required for real adapter)
export OPENART_API_KEY=your_api_key_here

# Optional: Custom CLI path (if not in PATH)
export OPENART_CLI_PATH=/usr/local/bin/openart

# Optional: CLI timeout in seconds (default: 300)
export OPENART_CLI_TIMEOUT=600

# Optional: Monthly budget in credits (default: 1000)
export OPENART_MONTHLY_BUDGET=5000
```

### Application Properties

Alternatively, configure in `application.yml` or `application-prod.yml`:

```yaml
pompom:
  openart:
    enabled: true
    mock:
      enabled: false
    api-key: ${OPENART_API_KEY}
    cli:
      path: openart
      timeout-seconds: 300
    budget:
      monthly: 1000
      warning-threshold: 0.2
      alert:
        enabled: true
        webhook-url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
        email: alerts@yourcompany.com
    cost:
      first-frame: 10   # Credits per first-frame generation
      video: 100         # Credits per video generation
```

## CLI Command Reference

The real adapter expects OpenArt CLI to support these commands:

### Image Generation
```bash
openart generate-image \
  --prompt "A happy orange ball character playing" \
  --model "stable-diffusion-xl" \
  --style "cinematic" \
  --aspect-ratio "16:9" \
  --api-key <KEY> \
  --output-format json
```

**Expected JSON output:**
```json
{
  "job_id": "img-abc123",
  "status": "QUEUED",
  "estimated_credits": 2.5
}
```

### Video Generation
```bash
openart generate-video \
  --prompt "Orange ball rolling down a hill" \
  --first-frame <IMAGE_ID> \
  --duration 15 \
  --model "runway-gen2" \
  --api-key <KEY> \
  --output-format json
```

**Expected JSON output:**
```json
{
  "job_id": "vid-xyz789",
  "status": "QUEUED",
  "estimated_credits": 15.0
}
```

### Job Status Check
```bash
openart status \
  --job-id <JOB_ID> \
  --api-key <KEY> \
  --output-format json
```

**Expected JSON output:**
```json
{
  "job_id": "vid-xyz789",
  "status": "COMPLETE",
  "progress_percent": 100
}
```

Or if failed:
```json
{
  "job_id": "vid-xyz789",
  "status": "FAILED",
  "progress_percent": 50,
  "error": "Insufficient credits"
}
```

### Asset Download
```bash
openart download \
  --job-id <JOB_ID> \
  --output /path/to/output.mp4 \
  --api-key <KEY> \
  --output-format json
```

**Expected JSON output:**
```json
{
  "width": 1920,
  "height": 1080,
  "duration_ms": 15000,
  "codec": "h264"
}
```

### Credit Balance
```bash
openart credits \
  --api-key <KEY> \
  --output-format json
```

**Expected JSON output:**
```json
{
  "balance": 950.5
}
```

## Testing the Integration

### 1. Test CLI Availability

```bash
curl http://localhost:8080/api/v1/health
# Should show openart.available: true
```

### 2. Check Credit Balance

```bash
curl http://localhost:8080/api/v1/budget/status
```

**Expected response:**
```json
{
  "budgetLimit": 1000,
  "usedCredits": 0,
  "remainingCredits": 1000,
  "remainingPercent": 100.0,
  "level": "HEALTHY",
  "totalJobs": 0
}
```

### 3. Queue a Test Job

```bash
curl -X POST http://localhost:8080/api/v1/render-jobs \
  -H "Content-Type: application/json" \
  -d '{
    "contentId": 1,
    "promptVersionId": 1,
    "jobType": "FIRST_FRAME"
  }'
```

**Expected response:**
```json
{
  "jobId": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 4. Monitor Job Progress

```bash
curl http://localhost:8080/api/v1/render-jobs/550e8400-e29b-41d4-a716-446655440000
```

## Troubleshooting

### CLI Not Found
**Error:** `OpenArt CLI is not available`

**Solution:**
1. Verify CLI is installed: `which openart`
2. Add to PATH if needed: `export PATH=$PATH:/path/to/openart`
3. Or set explicit path: `OPENART_CLI_PATH=/full/path/to/openart`

### API Key Invalid
**Error:** `Command failed with exit code 1: Unauthorized`

**Solution:**
1. Verify API key is correct
2. Check key has not expired
3. Ensure key has sufficient permissions

### Timeout
**Error:** `Command timed out after 300 seconds`

**Solution:**
1. Increase timeout: `OPENART_CLI_TIMEOUT=600`
2. Check network connectivity
3. Verify OpenArt service status

### Insufficient Credits
**Error:** `Monthly budget exhausted`

**Solution:**
1. Check budget status: `GET /api/v1/budget/status`
2. Increase monthly budget: `OPENART_MONTHLY_BUDGET=5000`
3. Wait for next billing cycle

## Production Checklist

- [ ] OpenArt CLI installed and accessible
- [ ] Valid API key configured
- [ ] Budget limits set appropriately
- [ ] Alert webhooks/emails configured
- [ ] Test render job completed successfully
- [ ] Monitoring/logging configured
- [ ] Backup strategy for generated assets
- [ ] Credit usage tracking dashboard

## CLI Command Customization

If the actual OpenArt CLI uses different command syntax, update the command builders in:
`backend/src/main/java/com/pompom/creative/openart/CliRealOpenArtAdapter.java`

Methods to customize:
- `buildImageGenerateCommand()`
- `buildVideoGenerateCommand()`
- `buildStatusCommand()`
- `buildDownloadCommand()`
- `buildCreditsCommand()`

## Support

For OpenArt CLI issues, consult:
- OpenArt CLI documentation: https://docs.openart.ai/cli
- OpenArt support: support@openart.ai
- OpenArt community forum: https://forum.openart.ai

For Pompom CI integration issues, contact the development team.
