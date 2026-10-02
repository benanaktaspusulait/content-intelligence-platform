# Phase 3: Distribution Engine - Detailed Specification

**Date:** September 30, 2026  
**Version:** 1.0  
**Status:** Draft  
**Dependencies:** Phase 2 (Production Engine) complete

---

## Executive Summary

Phase 3 transforms approved render assets into published social media content across TikTok, YouTube, and Meta platforms with automated caption generation, scheduling, OAuth handling, and publication state tracking.

**Scope:** Multi-platform publishing → OAuth management → Caption generation → Scheduling → State tracking

**Success Criteria:**
- Publish to TikTok with one click (OAuth + upload)
- Publish to YouTube Shorts with one click
- Generate platform-optimized captions automatically
- Schedule 10+ videos in publishing calendar
- Track publication status across all platforms

---

## Architecture

### Platform Adapter Pattern

```java
interface PlatformPublisher {
    // Authentication
    AuthenticationStatus authenticate(OAuthCredentials creds);
    void refreshAccessToken();
    
    // Content validation
    ValidationResult validateContent(Content content, PublishParams params);
    
    // Publishing
    PublishResult publish(Content content, SocialMetadata metadata, PublishParams params);
    PublishStatus getStatus(String platformContentId);
    
    // Capabilities
    boolean supportsScheduling();
    boolean supportsWebhooks();
    List<String> getRequiredPermissions();
    Map<String, Object> getPlatformLimits();  // file size, duration, etc.
}
```

**Implementations:**
1. `TikTokPublisher` - TikTok Content Posting API
2. `YouTubeShortsPublisher` - YouTube Data API v3
3. `MetaFacebookPublisher` - Meta Graph API
4. `MetaInstagramPublisher` - Meta Graph API (Reels)

---

## Database Schema (Phase 3)

```sql
-- Platform credentials (encrypted at rest)
CREATE TABLE platform_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(30) NOT NULL CHECK (platform IN ('TIKTOK', 'YOUTUBE', 'FACEBOOK', 'INSTAGRAM')),
    account_name VARCHAR(100) NOT NULL,
    account_identifier VARCHAR(200),  -- Platform-specific user ID
    
    -- OAuth tokens (encrypted)
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    
    -- Permissions
    granted_permissions VARCHAR[],
    required_permissions VARCHAR[],
    permissions_complete BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE' CHECK (
        status IN ('ACTIVE', 'EXPIRED', 'REVOKED', 'PENDING_REFRESH')
    ),
    
    -- Metadata
    linked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    last_refresh_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1,
    
    UNIQUE(platform, account_name)
);

-- Social metadata (platform-specific captions, titles, tags)
CREATE TABLE social_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id),
    platform VARCHAR(30) NOT NULL,
    version_number INT NOT NULL DEFAULT 1,
    
    -- Caption and title
    caption TEXT,
    title VARCHAR(200),
    description TEXT,
    
    -- Hashtags and tags
    hashtags VARCHAR[],
    learning_words_tagged VARCHAR[],
    
    -- Platform-specific metadata
    tiktok_settings JSONB,  -- {privacy_level, duet_enabled, comment_enabled, stitch_enabled}
    youtube_settings JSONB,  -- {category_id, tags[], default_language, privacy_status}
    facebook_settings JSONB,  -- {targeting, published, scheduled_publish_time}
    instagram_settings JSONB,  -- {caption_entities, location_id, share_to_feed}
    
    -- Generation metadata
    generated_by VARCHAR(50),  -- USER/AI/TEMPLATE
    template_id UUID,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50),
    entity_version INT NOT NULL DEFAULT 1,
    
    UNIQUE(content_id, platform, version_number)
);

-- Publication records (per platform)
CREATE TABLE publication_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id),
    render_asset_id UUID NOT NULL REFERENCES render_assets(id),
    social_metadata_id UUID NOT NULL REFERENCES social_metadata(id),
    platform_credential_id UUID NOT NULL REFERENCES platform_credentials(id),
    
    -- Platform details
    platform VARCHAR(30) NOT NULL,
    platform_content_id VARCHAR(200),  -- TikTok video ID, YouTube video ID, etc.
    platform_url TEXT,
    
    -- Publishing
    scheduled_for TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    
    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (
        status IN (
            'DRAFT',           -- Not yet scheduled
            'SCHEDULED',       -- Scheduled for future
            'PUBLISHING',      -- Upload in progress
            'PROCESSING',      -- Platform processing (e.g., YouTube)
            'PUBLISHED',       -- Live on platform
            'FAILED',          -- Upload/publish failed
            'DELETED',         -- Deleted from platform
            'REJECTED'         -- Platform rejected content
        )
    ),
    
    -- Error tracking
    error_code VARCHAR(50),
    error_message TEXT,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    last_retry_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_publication_records_content_id ON publication_records(content_id);
CREATE INDEX idx_publication_records_platform ON publication_records(platform);
CREATE INDEX idx_publication_records_status ON publication_records(status);
CREATE INDEX idx_publication_records_scheduled_for ON publication_records(scheduled_for);

-- Publishing schedule (calendar view)
CREATE TABLE publishing_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID NOT NULL REFERENCES contents(id),
    publication_record_id UUID REFERENCES publication_records(id),
    
    -- Schedule details
    platform VARCHAR(30) NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    time_slot_reason TEXT,  -- "Instagram prime time 7-9pm", "Avoid same-day Kiko content"
    
    -- Status
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (
        status IN ('PENDING', 'CONFIRMED', 'PUBLISHED', 'CANCELLED', 'MISSED')
    ),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(50),
    cancelled_at TIMESTAMPTZ,
    cancelled_reason TEXT,
    entity_version INT NOT NULL DEFAULT 1
);

CREATE INDEX idx_publishing_schedule_scheduled_time ON publishing_schedule(scheduled_time);
CREATE INDEX idx_publishing_schedule_platform ON publishing_schedule(platform);
CREATE INDEX idx_publishing_schedule_status ON publishing_schedule(status);

-- Platform webhook events (for status updates)
CREATE TABLE platform_webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_record_id UUID REFERENCES publication_records(id),
    
    -- Event details
    platform VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    platform_content_id VARCHAR(200),
    
    -- Payload
    raw_payload JSONB NOT NULL,
    parsed_data JSONB,
    
    -- Processing
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ,
    processing_error TEXT,
    
    -- Metadata
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_ip VARCHAR(50)
);

CREATE INDEX idx_platform_webhook_events_platform ON platform_webhook_events(platform);
CREATE INDEX idx_platform_webhook_events_processed ON platform_webhook_events(processed);
CREATE INDEX idx_platform_webhook_events_received_at ON platform_webhook_events(received_at);
```

---

## Platform-Specific Implementation Details

### 1. TikTok Publisher

**API:** TikTok Content Posting API v2  
**OAuth:** OAuth 2.0 with refresh tokens  
**Required Scopes:** `video.upload`, `video.publish`

**Key Features:**
- Direct video upload (multipart/form-data)
- Privacy settings (public/friends/private)
- Duet/Stitch/Comment settings
- Hashtag support (max 100 chars)
- No scheduling support (publish immediately or via TikTok Creator Portal)

**Upload Flow:**
```
1. Initiate upload session → Get upload_url + upload_id
2. Upload video bytes to upload_url (chunk upload for large files)
3. Publish video with metadata (caption, settings) + upload_id
4. Poll status until PUBLISHED
```

**Implementation Notes:**
- Video requirements: 540x960 min, 9:16 aspect ratio preferred, max 10GB
- Caption max length: 2200 chars (UTF-8)
- Hashtags count toward caption limit
- No direct scheduling - can save as draft for manual publish

### 2. YouTube Shorts Publisher

**API:** YouTube Data API v3  
**OAuth:** OAuth 2.0 with refresh tokens  
**Required Scopes:** `youtube.upload`, `youtube.force-ssl`

**Key Features:**
- Resumable upload protocol
- Shorts categorization (#Shorts in title/description)
- Scheduling support
- Category selection
- Privacy status (public/unlisted/private)

**Upload Flow:**
```
1. Create resumable upload session → Get upload_url
2. Upload video chunks to upload_url
3. Set video metadata (snippet, status)
4. Mark as Shorts (#Shorts in title, vertical video detected automatically)
5. Poll processing status until ready
```

**Implementation Notes:**
- Video requirements: 9:16 aspect ratio, <60s duration for Shorts
- Title max: 100 chars
- Description max: 5000 chars
- Tags max: 500 chars total, 30 chars per tag
- Automatic category: "Entertainment" or "Education" based on content

### 3. Meta Facebook Publisher

**API:** Graph API v18.0  
**OAuth:** OAuth 2.0 with long-lived tokens  
**Required Scopes:** `pages_manage_posts`, `pages_read_engagement`, `publish_video`

**Key Features:**
- Page video upload
- Scheduling support
- Targeting options (age, location)
- Crossposting to Instagram (if linked)
- Video captions (SRT upload)

**Upload Flow:**
```
1. Initiate resumable upload → Get upload_session_id
2. Upload video chunks
3. Finish upload with metadata (description, published, scheduled_publish_time)
4. Poll status until READY
5. Create video post with upload_session_id
```

**Implementation Notes:**
- Video requirements: min 600x600, max 10GB
- Description max: 63,206 chars
- Can schedule up to 75 days in advance
- Requires Page access token (not personal profile)

### 4. Meta Instagram Publisher

**API:** Instagram Graph API  
**OAuth:** OAuth 2.0 (requires Facebook Page connection)  
**Required Scopes:** `instagram_content_publish`, `pages_read_engagement`

**Key Features:**
- Reels upload (9:16 vertical video)
- Caption with hashtags
- Location tagging
- Share to Feed option
- Cover frame selection

**Upload Flow:**
```
1. Create media container → Upload video to container_id
2. Wait for container status = FINISHED
3. Publish media container (ig_user_id + container_id)
4. Poll until PUBLISHED
```

**Implementation Notes:**
- Reels requirements: 9:16 aspect ratio, 3-90s duration, <1GB
- Caption max: 2200 chars
- Max 30 hashtags
- No direct scheduling (use Creator Studio)

---

## OAuth Workflow

### Authorization Flow

```
User clicks "Connect TikTok"
    ↓
Frontend redirects to /api/v1/platforms/tiktok/auth/initiate
    ↓
Backend generates OAuth URL with state param (CSRF protection)
    ↓
Frontend redirects to TikTok OAuth page
    ↓
User authorizes app
    ↓
TikTok redirects to /api/v1/platforms/tiktok/auth/callback?code=...&state=...
    ↓
Backend exchanges code for access_token + refresh_token
    ↓
Backend stores encrypted tokens in platform_credentials
    ↓
Backend redirects frontend to success page
```

### Token Refresh

```
Spring @Scheduled task runs daily
    ↓
Check all credentials with token_expires_at < NOW + 7 days
    ↓
Call platform OAuth refresh endpoint with refresh_token
    ↓
Update encrypted_access_token + token_expires_at
    ↓
Log refresh event
```

### Credential Encryption

**Use OS Keychain (macOS):**
```java
@Service
public class CredentialEncryptionService {
    
    public String encrypt(String plaintext) {
        // Use macOS Keychain via JNA
        KeychainPasswordItem item = Keychain.addGenericPassword(
            "PompomCreativeIntelligence",
            "platform_token_" + UUID.randomUUID(),
            plaintext.getBytes()
        );
        return item.getItemId();  // Store reference ID in DB
    }
    
    public String decrypt(String keychainRef) {
        byte[] data = Keychain.findGenericPassword("PompomCreativeIntelligence", keychainRef);
        return new String(data);
    }
}
```

---

## Caption Generation

### Template System

```yaml
# data/caption-templates/tiktok/episode-templates.yaml

episode_default:
  template: |
    {character_name} discovers {core_concept}! 🎉
    
    {learning_moment}
    
    #LearnWithPompom #{character_name} #{learning_word_1} #{learning_word_2}
  
  variables:
    character_name: Required
    core_concept: Required
    learning_moment: Required
    learning_word_1: Optional
    learning_word_2: Optional

kiko_curiosity:
  template: |
    Curious Kiko explores {discovery}! 🤔✨
    
    Watch as Kiko learns about {concept} through playful discovery.
    
    #CuriousKiko #DiscoverWithKiko #{learning_word}
```

### AI Generation

```python
# ml-service/app/caption/generator.py

from app.llm.provider import get_provider

CAPTION_GENERATION_PROMPT = """Generate a social media caption for a children's educational video.

Video details:
- Character: {character_name}
- Title: {title}
- Core concept: {core_concept}
- Learning words: {learning_words}
- Duration: {duration}s
- Platform: {platform}

Platform requirements:
{platform_requirements}

Style guidelines:
- Age-appropriate (2-4 years)
- Warm, encouraging tone
- Include 3-5 relevant hashtags
- Emphasize learning moment
- Keep concise ({max_length} char limit)

Output format:
{{
  "caption": "...",
  "hashtags": ["...", "..."],
  "title": "..." (for YouTube)
}}
"""

class CaptionGenerator:
    def generate_caption(
        self,
        content: dict,
        platform: str,
        style: str = "default"
    ) -> dict:
        llm = get_provider()
        
        platform_reqs = self._get_platform_requirements(platform)
        
        prompt = CAPTION_GENERATION_PROMPT.format(
            character_name=content["character_name"],
            title=content["title"],
            core_concept=content["core_concept"],
            learning_words=", ".join(content["learning_words"]),
            duration=content["duration"],
            platform=platform,
            platform_requirements=platform_reqs,
            max_length=self._get_max_length(platform)
        )
        
        response = llm.complete(prompt, temperature=0.8)
        return json.loads(response)
```

---

## Publishing Scheduler

### Calendar View UI (Angular)

```typescript
interface ScheduleSlot {
  date: Date;
  platform: Platform;
  contentId?: string;
  status: 'AVAILABLE' | 'SCHEDULED' | 'PUBLISHED';
  reason?: string;
}

class PublishingCalendarComponent {
  // Weekly calendar view
  weeks: ScheduleSlot[][];
  
  // Drag-and-drop scheduling
  onDropContent(content: Content, slot: ScheduleSlot) {
    // Check conflicts (same character same day)
    const conflicts = this.checkConflicts(content, slot);
    
    if (conflicts.length > 0) {
      this.showConflictDialog(conflicts);
    } else {
      this.schedulePublication(content, slot);
    }
  }
  
  // Smart scheduling rules
  checkConflicts(content: Content, slot: ScheduleSlot): Conflict[] {
    const conflicts = [];
    
    // Rule 1: No same character same day same platform
    const sameDay = this.getScheduledForDay(slot.date, slot.platform);
    const sameChar = sameDay.filter(s => s.character === content.character);
    if (sameChar.length > 0) {
      conflicts.push({
        type: 'SAME_CHARACTER_SAME_DAY',
        message: `${content.character} already scheduled for ${slot.platform} on this day`
      });
    }
    
    // Rule 2: Respect platform prime times
    const hour = slot.date.getHours();
    const primeTime = this.getPrimeTime(slot.platform);
    if (hour < primeTime.start || hour > primeTime.end) {
      conflicts.push({
        type: 'SUBOPTIMAL_TIME',
        severity: 'WARNING',
        message: `${slot.platform} prime time is ${primeTime.start}-${primeTime.end}`
      });
    }
    
    return conflicts;
  }
}
```

### Scheduled Publishing Task

```java
@Service
public class ScheduledPublishingService {
    
    @Scheduled(fixedDelay = 60000)  // Every 1 minute
    public void publishScheduledContent() {
        Instant now = Instant.now();
        Instant window = now.plusMinutes(5);  // 5-minute window
        
        List<PublishingSchedule> due = scheduleRepository
            .findByStatusAndScheduledTimeBetween(
                ScheduleStatus.CONFIRMED,
                now,
                window
            );
        
        for (PublishingSchedule schedule : due) {
            try {
                publishContent(schedule);
            } catch (Exception e) {
                handlePublishFailure(schedule, e);
            }
        }
    }
    
    private void publishContent(PublishingSchedule schedule) {
        Content content = contentRepository.findById(schedule.getContentId()).orElseThrow();
        SocialMetadata metadata = socialMetadataRepository
            .findByContentIdAndPlatform(content.getId(), schedule.getPlatform())
            .orElseThrow();
        
        PlatformPublisher publisher = platformPublisherFactory.getPublisher(schedule.getPlatform());
        
        PublishParams params = PublishParams.builder()
            .scheduledTime(schedule.getScheduledTime())
            .build();
        
        PublishResult result = publisher.publish(content, metadata, params);
        
        // Create publication record
        PublicationRecord record = PublicationRecord.builder()
            .contentId(content.getId())
            .renderAssetId(content.getCurrentRenderAssetId())
            .socialMetadataId(metadata.getId())
            .platform(schedule.getPlatform())
            .platformContentId(result.getContentId())
            .platformUrl(result.getUrl())
            .status(PublicationStatus.PROCESSING)
            .publishedAt(Instant.now())
            .build();
        
        publicationRecordRepository.save(record);
        
        // Update schedule
        schedule.setStatus(ScheduleStatus.PUBLISHED);
        schedule.setPublicationRecordId(record.getId());
        scheduleRepository.save(schedule);
    }
}
```

---

## REST APIs (Phase 3)

### OAuth & Credentials

```
GET    /api/v1/platforms
  Response: [{ platform, supported, required_scopes, features }]

POST   /api/v1/platforms/{platform}/auth/initiate
  Response: { oauth_url, state }

GET    /api/v1/platforms/{platform}/auth/callback
  Query: code, state
  Response: Redirect to frontend success page

POST   /api/v1/platforms/{platform}/auth/refresh
  Response: { success, new_expiry }

DELETE /api/v1/platforms/{platform}/auth/revoke
  Response: { success }

GET    /api/v1/platforms/{platform}/credentials
  Response: { account_name, permissions, status, expires_at }
```

### Social Metadata

```
POST   /api/v1/contents/{id}/social-metadata
  Request: { platform, caption?, title?, hashtags[], settings }
  Response: { id, version_number }

GET    /api/v1/contents/{id}/social-metadata
  Query: platform?
  Response: [{ id, platform, version, caption, hashtags, ... }]

POST   /api/v1/contents/{id}/generate-caption
  Request: { platform, style?, template_id? }
  Response: { caption, title, hashtags, confidence }

PUT    /api/v1/social-metadata/{id}
  Request: { caption?, title?, hashtags? }
  Response: { updated_fields }
```

### Publishing

```
POST   /api/v1/contents/{id}/publish-now
  Request: { platform, social_metadata_id }
  Response: { publication_record_id, status }

POST   /api/v1/contents/{id}/schedule-publish
  Request: { platform, social_metadata_id, scheduled_time }
  Response: { schedule_id, publication_record_id }

GET    /api/v1/publications
  Query: platform?, status?, from_date?, to_date?
  Response: [{ id, content, platform, status, published_at, url }]

GET    /api/v1/publications/{id}
  Response: { id, content, platform, status, platform_url, metrics_link }

POST   /api/v1/publications/{id}/cancel
  Response: { success }

DELETE /api/v1/publications/{id}
  Request: { delete_from_platform: boolean }
  Response: { success, platform_deleted }
```

### Calendar

```
GET    /api/v1/publishing-calendar
  Query: from_date, to_date, platform?
  Response: [{ date, platform, slots: [{ content?, status, reason? }] }]

POST   /api/v1/publishing-calendar/bulk-schedule
  Request: [{ content_id, platform, scheduled_time }]
  Response: { scheduled_count, conflicts: [...] }

DELETE /api/v1/publishing-calendar/{schedule_id}
  Request: { reason }
  Response: { success }
```

### Webhooks

```
POST   /api/v1/webhooks/tiktok
  (Platform-initiated, validates signature)

POST   /api/v1/webhooks/youtube
  (Platform-initiated, validates token)

POST   /api/v1/webhooks/meta
  (Platform-initiated, validates app secret)
```

---

## Success Criteria

- [x] Connect TikTok account via OAuth
- [x] Generate caption for Mimi content (LLM-powered)
- [x] Publish Mimi to TikTok (upload + status tracking)
- [x] Schedule 10 videos in calendar
- [x] Publish to YouTube Shorts
- [x] Handle OAuth token refresh automatically
- [x] Track publication status (PROCESSING → PUBLISHED)

---

## Timeline Estimate

- **Week 1:** Database schema, OAuth infrastructure, credential encryption
- **Week 2:** TikTok publisher implementation + testing
- **Week 3:** YouTube publisher implementation + testing
- **Week 4:** Meta (Facebook/Instagram) publisher implementation
- **Week 5:** Caption generator (templates + LLM), scheduling system
- **Week 6:** Calendar UI, webhook handlers, integration testing

**Total:** 6 weeks

---

## Dependencies

- Phase 2 (Production Engine) complete
- Platform API credentials (TikTok, YouTube, Meta developer accounts)
- OS Keychain access for credential encryption

---

**Document Status:** DRAFT  
**Review Required:** Yes  
**Estimated Effort:** 6 weeks

