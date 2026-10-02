# Pompom Creative Intelligence - Development Roadmap

**Version:** 1.0  
**Last Updated:** September 30, 2026  
**Status:** Phase 1 Complete → Phase 2-4 Planned

---

## Vision

Transform Pompom Creative Intelligence from a validation-only tool into a **closed-loop AI content production system** that learns from every video and continuously improves its creative rules.

**Complete System Flow:**
```
Idea → Validation → Render → QA → Publish → Metrics → Learning → Better Rules → Better Next Video
```

---

## Phase Overview

| Phase | Name | Status | Duration | Dependencies |
|-------|------|--------|----------|--------------|
| **Phase 1** | Creative Quality Engine | ✅ **COMPLETE** | 6 weeks | None |
| **Phase 2** | Production Engine | 📋 Planned | 6 weeks | Phase 1 |
| **Phase 3** | Distribution Engine | 📋 Planned | 6 weeks | Phase 2 |
| **Phase 4** | Learning Engine | 📋 Planned | 6 weeks | Phase 3 |

**Total Timeline:** 24 weeks (~6 months) for complete system

---

## Phase 1: Creative Quality Engine ✅

**Status:** **COMPLETE** (September 14, 2026)  
**Spec:** `docs/superpowers/specs/2026-09-30-phase1-creative-quality-engine.md`

### Delivered

✅ **Prompt Parser**
- Regex-based markdown extraction
- Beat parsing with 85-95% confidence
- VideoPlanIR intermediate representation

✅ **Rule Engine**
- 11 quality families (concept, hook, novelty, progression, etc.)
- 10 critical rules implemented
- 4 severity levels (BLOCKER/CRITICAL/WARNING/PASS)
- YAML rule definitions

✅ **Quality Scorer**
- 0-100 scoring scale
- Weighted family scores
- RENDER_READY (≥92) / NEEDS_REVISION / BLOCKED status

✅ **Auto-Fix Loop**
- Rule-specific transformations
- 5 iteration maximum
- Regression prevention
- Improvement tracking

✅ **Spring Boot REST API**
- 7 endpoints (validate, compare versions, batch)
- PostgreSQL persistence (V6 migration)
- JPA entities and repositories

✅ **Angular UI**
- Quality dashboard with score card
- Beat timeline visualization
- Priority fixes list
- Family scores chart

✅ **Integration Tests**
- 5/5 tests passing
- 3 golden test cases (Kiko, Opa, Arda)
- 100% known failure detection

### New Additions (September 30, 2026)

🆕 **Database V7-V9 Migrations** (commit 4a36b0cc)
- `contents` table (root aggregate)
- `prompt_versions` table (version tracking)
- `validation_runs` table (validation history)
- `failed_rules` table (rule violations)
- `reference_prompts` table + 4 golden test seeds

### Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Failed cases detected | 3/3 (100%) | ✅ 3/3 |
| Validation time | <5s | ✅ <50ms |
| Auto-fix improvement | +15pts | ✅ 60→75 typical |
| Integration tests | 5/5 pass | ✅ 5/5 |

---

## Phase 2: Production Engine 📋

**Status:** Planned  
**Spec:** `docs/superpowers/specs/2026-09-30-phase2-production-engine.md`  
**Duration:** 6 weeks  
**Dependencies:** Phase 1 complete

### Scope

**Goal:** Automate OpenArt render workflow from RENDER_READY prompt to approved asset

**Key Components:**

1. **OpenArt Adapter**
   - MCP Server integration (preferred)
   - CLI Tool fallback
   - Authentication handling
   - Image + video generation

2. **Render Queue Manager**
   - FIFO queue with priority
   - Concurrent job limits (3-5)
   - Polling orchestration

3. **Render Job State Machine**
   - QUEUED → GENERATING → POLLING → DOWNLOADING → COMPLETE
   - Error handling and retries (max 3 attempts)
   - Credit tracking

4. **Asset Library Manager**
   - Local filesystem structure
   - Asset metadata (resolution, duration, codec)
   - Version management (first-frame-v1.png, render-v2.mp4)

5. **Render QA Engine (Python)**
   - Dead air detection (FFmpeg)
   - Character identity verification (OpenCV)
   - Prompt compliance check (LLM vision)
   - Physics consistency check
   - Object duplication detection

6. **Rerender Decision Engine**
   - ACCEPT / RERENDER / ABANDON logic
   - Max 2 rerender attempts
   - Human review gate for edge cases

### Success Criteria

- [ ] Generate Mimi video via OpenArt MCP/CLI
- [ ] Detect dead air (>2s silence) → trigger RERENDER
- [ ] Detect character mismatch → ABANDON
- [ ] Track credit usage per render
- [ ] Avoid 1+ unnecessary rerenders through QA

### Technical Decisions Needed

1. **OpenArt Integration:** MCP Server available? If not, use CLI Tool
2. **Credit Costs:** Actual costs per image/video generation?
3. **Generation Time:** Average time for 15s video?
4. **Rate Limits:** Max concurrent jobs allowed by OpenArt?

### Timeline

| Week | Deliverable |
|------|-------------|
| 1 | OpenArt adapter, render queue, database migrations |
| 2 | Render job orchestrator, polling logic |
| 3 | Python QA analyzer (dead air, character verification) |
| 4 | QA decision engine, rerender logic |
| 5 | Angular UI (render dashboard, progress tracking) |
| 6 | Testing, bug fixes, documentation |

---

## Phase 3: Distribution Engine 📋

**Status:** Planned  
**Spec:** `docs/superpowers/specs/2026-09-30-phase3-distribution-engine.md`  
**Duration:** 6 weeks  
**Dependencies:** Phase 2 complete

### Scope

**Goal:** Multi-platform publishing with one click (TikTok, YouTube, Meta)

**Key Components:**

1. **Platform Adapter Pattern**
   - `TikTokPublisher` (Content Posting API)
   - `YouTubeShortsPublisher` (Data API v3)
   - `MetaFacebookPublisher` (Graph API)
   - `MetaInstagramPublisher` (Reels API)

2. **OAuth & Credentials Manager**
   - Multi-platform OAuth 2.0 flow
   - Token refresh automation
   - Encrypted credential storage (OS Keychain)

3. **Social Metadata Generator**
   - Platform-specific caption templates
   - LLM-powered caption generation
   - Hashtag optimization
   - Learning word integration

4. **Publishing Scheduler**
   - Calendar view UI (Angular)
   - Drag-and-drop scheduling
   - Conflict detection (same character same day)
   - Platform prime time recommendations

5. **Publication State Tracker**
   - Platform-specific state machines
   - Webhook handlers (where supported)
   - Polling for status updates
   - Retry logic (max 3 attempts)

### Success Criteria

- [ ] Connect TikTok account via OAuth
- [ ] Generate caption for Mimi (LLM-powered)
- [ ] Publish Mimi to TikTok with one click
- [ ] Schedule 10 videos in calendar
- [ ] Publish to YouTube Shorts
- [ ] Track publication status (PROCESSING → PUBLISHED)

### Technical Decisions Needed

1. **Platform Developer Accounts:** TikTok, YouTube, Meta API credentials
2. **Credential Storage:** Use macOS Keychain or alternative?
3. **Scheduling:** Auto-publish at scheduled time or manual approval?

### Timeline

| Week | Deliverable |
|------|-------------|
| 1 | OAuth infrastructure, credential encryption |
| 2 | TikTok publisher implementation |
| 3 | YouTube publisher implementation |
| 4 | Meta publishers (Facebook + Instagram) |
| 5 | Caption generator, scheduling system |
| 6 | Calendar UI, webhook handlers, testing |

---

## Phase 4: Learning Engine 📋

**Status:** Planned  
**Spec:** `docs/superpowers/specs/2026-09-30-phase4-learning-engine.md`  
**Duration:** 6 weeks  
**Dependencies:** Phase 3 complete

### Scope

**Goal:** Close the loop - learn from performance data and improve creative rules

**Key Components:**

1. **Metrics Collector**
   - Scheduled collection (T+30m, T+1h, T+6h, T+24h, T+7d, T+30d)
   - Platform API integration (TikTok, YouTube, Meta Analytics)
   - Manual entry UI (fallback)

2. **Trajectory Analyzer**
   - Time-series analysis (velocity, acceleration)
   - Wave detection (primary, secondary, tertiary)
   - Plateau/decay detection
   - Tail strength assessment

3. **Performance Classifier**
   - 10 classification categories:
     - EARLY_REJECTION, WEAK, MEDIUM, STRONG_START
     - BREAKOUT, DELAYED_BREAKOUT, MULTI_WAVE
     - PERSISTENT_WINNER, LONG_TAIL, EVERGREEN_BREAKOUT
   - Confidence scoring

4. **Benchmark Engine**
   - Winner catalog (top performers per character)
   - Similarity matching
   - Trajectory comparison

5. **Correlation Analyzer**
   - Statistical analysis (Pearson correlation, p-values)
   - Quality scores ↔ performance metrics
   - Effect size calculation

6. **Rule Mining Engine**
   - Pattern detection across winners/losers
   - Hypothesis generation
   - Evidence collection (sample size >20)
   - Confidence scoring

7. **Rule Approval Workflow (Angular)**
   - Human review queue
   - Evidence visualization
   - Approve/Reject/Modify
   - A/B test suggestions
   - Ruleset version activation

### Success Criteria

- [ ] Collect metrics for 50+ published videos
- [ ] Classify 10+ videos (WINNER/MEDIUM/WEAK)
- [ ] Detect 3+ significant correlations (p<0.05)
- [ ] Generate 5+ rule candidates with evidence
- [ ] Approve and activate 1+ new rule
- [ ] Track rule evidence levels (THEORETICAL → SUPPORTED)

### Example Rule Candidates

1. **CONSEQUENCE_COUNT_ENHANCED:** Videos with 5+ consequences perform 2x better
2. **HOOK_INTENSITY_THRESHOLD:** Hook intensity >7 correlates with 40% higher completion rate
3. **BEAT_PACING_VARIANCE:** Beat duration variance <3s improves retention
4. **FINAL_EXECUTION_SCORE:** Final execution score >85 predicts strong long-tail
5. **NOVELTY_SCORE_THRESHOLD:** Novelty score >0.7 correlates with breakout performance

### Timeline

| Week | Deliverable |
|------|-------------|
| 1 | Metrics collector, platform adapters |
| 2 | Trajectory analyzer, classification logic |
| 3 | Correlation analyzer, statistical tests |
| 4 | Rule mining engine, pattern detection |
| 5 | Human approval UI, review workflow |
| 6 | Integration testing, rule activation, evidence tracking |

---

## Technology Stack

### Backend
- **Language:** Java 21
- **Framework:** Spring Boot 4.1.1
- **Database:** PostgreSQL 17
- **Migrations:** Flyway
- **Scheduler:** Spring @Scheduled

### ML Services
- **Language:** Python 3.11
- **Framework:** FastAPI
- **LLM:** OpenAI GPT-4o (primary), Claude/Gemini/Ollama (alternatives)
- **Video Analysis:** FFmpeg, OpenCV
- **Statistics:** scipy, statsmodels, numpy

### Frontend
- **Framework:** Angular 21
- **Language:** TypeScript
- **Styling:** SCSS
- **Charting:** Chart.js, D3.js

### Infrastructure
- **Containerization:** Docker Compose
- **Secrets:** OS Keychain (macOS) or environment variables
- **Storage:** Local filesystem + PostgreSQL

---

## Risk Assessment

### High Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenArt MCP not available | Blocks Phase 2 | Fallback to CLI Tool |
| Platform API rate limits | Slows Phase 3 | Respect limits, queue management |
| Insufficient video sample | Blocks Phase 4 | Start with manual metric entry, expand gradually |

### Medium Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| OAuth token management complexity | Auth failures | Use proven libraries, automated refresh |
| False positive QA rejections | Wasted credits | Human review gate, tune thresholds |
| Rule candidate low confidence | Delays Phase 4 | Lower sample size threshold, qualitative analysis |

---

## Success Metrics (Overall)

### Phase 1 (Complete)
- ✅ 3/3 known failures detected pre-render
- ✅ <50ms validation time
- ✅ 60→75 typical auto-fix improvement

### Phase 2 (Target)
- [ ] Render 20+ videos via OpenArt
- [ ] QA catches 5+ compliance issues
- [ ] Avoid 10+ unnecessary rerenders
- [ ] Track $500+ credit savings

### Phase 3 (Target)
- [ ] Publish 50+ videos to TikTok
- [ ] Publish 50+ videos to YouTube
- [ ] Schedule 100+ videos in calendar
- [ ] OAuth uptime >99%

### Phase 4 (Target)
- [ ] Collect metrics for 200+ videos
- [ ] Identify 10+ significant correlations
- [ ] Generate 20+ rule candidates
- [ ] Activate 5+ new rules
- [ ] Improve validation accuracy from 95% to 98%

---

## Next Steps

### Immediate (Week 1)

1. ✅ Review and approve Master Architecture
2. ✅ Review and approve Phase 1 spec (already implemented)
3. ✅ Create V7-V9 database migrations (commit 4a36b0cc)
4. → **Review and approve Phase 2 spec**
5. → **Resolve OpenArt integration questions**
6. → **Create Phase 2 implementation plan**

### Short-term (Weeks 2-7)

1. Implement Phase 2 (Production Engine)
2. Test with Mimi golden case
3. Deploy Phase 2 to production
4. Begin collecting render data

### Medium-term (Weeks 8-13)

1. Implement Phase 3 (Distribution Engine)
2. Connect platform accounts
3. Publish first batch of videos
4. Monitor publication success rates

### Long-term (Weeks 14-19)

1. Implement Phase 4 (Learning Engine)
2. Collect 50+ video metrics
3. Generate first rule candidates
4. Approve and activate new rules

### Future Enhancements

- **LLM Parser Enhancement:** Replace regex with GPT-4V for semantic understanding
- **Real-time Metrics:** Webhook integration for instant performance updates
- **Multi-language Support:** Turkish, Spanish, French content
- **Platform Expansion:** Instagram Stories, Snapchat Spotlight
- **Advanced Analytics:** Predictive modeling (score → expected views)
- **Automated A/B Testing:** Test rule variants automatically

---

## Budget Estimate

### Development Time

| Phase | Weeks | Team | Cost Estimate |
|-------|-------|------|---------------|
| Phase 1 | 6 (complete) | 1 dev | - |
| Phase 2 | 6 | 1 dev | - |
| Phase 3 | 6 | 1 dev | - |
| Phase 4 | 6 | 1 dev | - |
| **Total** | **24 weeks** | **1 dev** | - |

### Operational Costs (Monthly Estimates)

| Service | Cost | Phase |
|---------|------|-------|
| OpenAI API (GPT-4o) | $100-200 | Phase 1-4 |
| OpenArt Credits | $200-500 | Phase 2+ |
| Platform API fees | $0 (free tiers) | Phase 3+ |
| Infrastructure (cloud) | $50-100 | Phase 2+ (if deployed) |
| **Total Monthly** | **$350-800** | **All phases** |

---

## Approval Checklist

- [x] Phase 1 spec approved
- [x] Phase 1 implemented and tested
- [x] V7-V9 migrations created
- [ ] Phase 2 spec reviewed
- [ ] OpenArt integration strategy confirmed
- [ ] Phase 2 implementation plan created
- [ ] Phase 3 spec reviewed
- [ ] Platform API credentials obtained
- [ ] Phase 4 spec reviewed
- [ ] Sample size target confirmed (50+ videos)

---

## Document Status

**Status:** ACTIVE ROADMAP  
**Version:** 1.0  
**Last Updated:** September 30, 2026  
**Next Review:** After Phase 2 completion

---

**Questions or feedback?** Contact: [Project Lead]

