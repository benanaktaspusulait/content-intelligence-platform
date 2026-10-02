# Pompom Meta Publisher - Entegrasyon Rehberi

Bu rehber, Pompom Meta Publisher'ı mevcut video üretim pipeline'ınıza nasıl entegre edeceğinizi gösterir.

## İçindekiler

1. [Üretim Pipeline Entegrasyonu](#üretim-pipeline-entegrasyonu)
2. [Pompom Creative Intelligence Entegrasyonu](#pompom-creative-intelligence-entegrasyonu)
3. [Otomatik Yayın Workflow'u](#otomatik-yayın-workflowu)
4. [CI/CD Entegrasyonu](#cicd-entegrasyonu)

---

## Üretim Pipeline Entegrasyonu

### Video Render Sonrası Otomatik Yayın

Video render'ı tamamlandıktan sonra otomatik yayın için:

```python
# render_and_publish.py

from pathlib import Path
from pompom_meta_publisher.publishing import publish_to_meta

def render_video(episode_data):
    """Video render logic'iniz"""
    # ... render işlemleri ...
    return Path("output/final-reel.mp4")

def publish_video(video_path: Path, episode_data: dict):
    """Render sonrası otomatik yayın"""
    
    # Caption oluştur
    caption = f"""{episode_data['title']} {episode_data['emoji']}

{episode_data['description']}

{' '.join(episode_data['hashtags'])}
"""
    
    # Content ID oluştur
    content_id = f"{episode_data['series']}-{episode_data['episode']}"
    
    # Yayınla
    report = publish_to_meta(
        video_path=video_path,
        caption=caption,
        content_id=content_id,
    )
    
    return report

# Ana workflow
episode = {
    "series": "can-you-find-it",
    "episode": "001",
    "title": "Lucas's Lost Treasure",
    "emoji": "🔍✨",
    "description": "Can you find Lucas's lost treasure?",
    "hashtags": ["#PompomHills", "#KidsLearning"],
}

video_path = render_video(episode)
report = publish_video(video_path, episode)

if report.ok:
    print(f"✅ Published to {len(report.published)} platforms")
else:
    print(f"❌ Failed: {report.failures}")
```

---

## Pompom Creative Intelligence Entegrasyonu

### Backend REST API Integration

Pompom Creative Intelligence backend'ine Meta publishing endpoint'i ekleyin:

```java
// MetaPublishingController.java

@RestController
@RequestMapping("/api/meta")
public class MetaPublishingController {
    
    @PostMapping("/publish")
    public ResponseEntity<PublishResponse> publishToMeta(
            @RequestBody PublishRequest request) {
        
        // Python publisher'ı çağır
        ProcessBuilder pb = new ProcessBuilder(
            "python3",
            "../pompom-meta-publisher/publish_pompom_reel.py",
            "--video", request.getVideoPath(),
            "--caption", request.getCaption(),
            "--content-id", request.getContentId(),
            "--live"
        );
        
        Process process = pb.start();
        int exitCode = process.waitFor();
        
        if (exitCode == 0) {
            return ResponseEntity.ok(new PublishResponse("SUCCESS"));
        } else {
            return ResponseEntity.status(500)
                .body(new PublishResponse("FAILED"));
        }
    }
    
    @GetMapping("/history")
    public ResponseEntity<List<PublicationRecord>> getHistory() {
        // SQLite ledger'dan geçmişi oku
        // ...
    }
}
```

### Angular Frontend Integration

```typescript
// meta-publishing.service.ts

@Injectable({
  providedIn: 'root'
})
export class MetaPublishingService {
  private apiUrl = '/api/meta';

  constructor(private http: HttpClient) {}

  publishVideo(videoPath: string, caption: string, contentId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/publish`, {
      videoPath,
      caption,
      contentId
    });
  }

  getPublishingHistory(): Observable<PublicationRecord[]> {
    return this.http.get<PublicationRecord[]>(`${this.apiUrl}/history`);
  }

  checkConfiguration(): Observable<ConfigStatus> {
    return this.http.get<ConfigStatus>(`${this.apiUrl}/config/check`);
  }
}
```

```typescript
// video-detail.component.ts

export class VideoDetailComponent {
  
  publishToMeta() {
    this.metaService.publishVideo(
      this.video.path,
      this.video.caption,
      this.video.contentId
    ).subscribe({
      next: (response) => {
        this.notificationService.success('Published to Meta!');
        this.loadPublishingHistory();
      },
      error: (error) => {
        this.notificationService.error('Publishing failed: ' + error.message);
      }
    });
  }
}
```

---

## Otomatik Yayın Workflow'u

### Cron Job ile Günlük Yayın

```bash
# /etc/cron.d/pompom-publisher

# Her gün saat 10:00'da yeni videoları yayınla
0 10 * * * cd /path/to/pompom-meta-publisher && ./scripts/auto_publish_new_videos.sh --search-dir ../new-videos --live >> /var/log/pompom-publisher.log 2>&1
```

### Watchdog ile Klasör İzleme

```python
# watch_and_publish.py

import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pompom_meta_publisher.publishing import publish_to_meta

class VideoHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('final.mp4'):
            print(f"New video detected: {event.src_path}")
            
            # 5 saniye bekle (render tamamlansın)
            time.sleep(5)
            
            # Auto-publish
            video_path = Path(event.src_path)
            content_id = video_path.parent.name.lower().replace(' ', '-')
            
            report = publish_to_meta(
                video_path=video_path,
                caption="New Pompom Hills content! 🌟",
                content_id=content_id,
            )
            
            if report.ok:
                print(f"✅ Auto-published: {content_id}")
            else:
                print(f"❌ Auto-publish failed: {content_id}")

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(VideoHandler(), path='../new-videos', recursive=True)
    observer.start()
    
    print("👀 Watching for new videos...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
```

---

## CI/CD Entegrasyonu

### GitHub Actions Workflow

```yaml
# .github/workflows/publish-to-meta.yml

name: Publish to Meta

on:
  push:
    paths:
      - 'videos/ready-to-publish/**'
  workflow_dispatch:
    inputs:
      video_path:
        description: 'Video path to publish'
        required: true
      caption:
        description: 'Caption'
        required: true
      content_id:
        description: 'Content ID'
        required: true

jobs:
  publish:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd pompom-meta-publisher
          pip install -e ".[s3]"
      
      - name: Configure Meta credentials
        env:
          META_PAGE_ID: ${{ secrets.META_PAGE_ID }}
          META_INSTAGRAM_ACCOUNT_ID: ${{ secrets.META_INSTAGRAM_ACCOUNT_ID }}
          META_PAGE_ACCESS_TOKEN: ${{ secrets.META_PAGE_ACCESS_TOKEN }}
          META_S3_BUCKET: ${{ secrets.META_S3_BUCKET }}
          META_S3_ACCESS_KEY_ID: ${{ secrets.META_S3_ACCESS_KEY_ID }}
          META_S3_SECRET_ACCESS_KEY: ${{ secrets.META_S3_SECRET_ACCESS_KEY }}
        run: |
          cat > pompom-meta-publisher/.env << EOF
          META_PAGE_ID=${META_PAGE_ID}
          META_INSTAGRAM_ACCOUNT_ID=${META_INSTAGRAM_ACCOUNT_ID}
          META_PAGE_ACCESS_TOKEN=${META_PAGE_ACCESS_TOKEN}
          META_ENABLE_FACEBOOK=true
          META_ENABLE_INSTAGRAM=true
          META_DRY_RUN=false
          META_STORAGE_BACKEND=s3
          META_S3_BUCKET=${META_S3_BUCKET}
          META_S3_ACCESS_KEY_ID=${META_S3_ACCESS_KEY_ID}
          META_S3_SECRET_ACCESS_KEY=${META_S3_SECRET_ACCESS_KEY}
          EOF
      
      - name: Publish videos
        run: |
          cd pompom-meta-publisher
          python3 scripts/auto_publish_new_videos.sh \
            --search-dir ../videos/ready-to-publish \
            --live
      
      - name: Upload publish log
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: publish-log
          path: pompom-meta-publisher/data/publish_log.db
```

### GitLab CI/CD

```yaml
# .gitlab-ci.yml

stages:
  - test
  - publish

test-config:
  stage: test
  script:
    - cd pompom-meta-publisher
    - pip install -e .
    - python test_config.py
  only:
    - merge_requests

publish-to-meta:
  stage: publish
  script:
    - cd pompom-meta-publisher
    - pip install -e ".[s3]"
    - python batch_publish.py --json ../videos-to-publish.json --live
  only:
    - main
  when: manual
```

---

## Webhook Integration

Meta yayın durumunu webhook ile takip edin:

```python
# webhook_server.py

from flask import Flask, request, jsonify
from pompom_meta_publisher.publishing import PublishLedger

app = Flask(__name__)
ledger = PublishLedger()

@app.route('/webhook/meta/status', methods=['POST'])
def meta_status_webhook():
    """Meta'dan gelen status update'leri"""
    data = request.json
    
    # Update ledger with new status
    content_id = data.get('content_id')
    platform = data.get('platform')
    status = data.get('status')
    
    if status == 'published':
        ledger.record(
            content_id=content_id,
            platform=platform,
            status='SUCCESS',
            media_id=data.get('media_id'),
            permalink=data.get('permalink')
        )
    
    # Notify other systems
    notify_slack(f"✅ {content_id} published to {platform}")
    
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

---

## Best Practices

### 1. Error Handling

```python
from pompom_meta_publisher.publishing import publish_to_meta
from pompom_meta_publisher.publishing.errors import (
    MetaApiError,
    MetaAuthenticationError,
    MetaRateLimitError,
)

try:
    report = publish_to_meta(...)
    report.raise_for_status()
except MetaAuthenticationError:
    # Token yenilenme gerek
    refresh_token()
    retry_publish()
except MetaRateLimitError:
    # Rate limit - bekle ve tekrar dene
    time.sleep(300)
    retry_publish()
except MetaApiError as e:
    # Diğer API hataları
    log_error(e)
    notify_admin(e)
```

### 2. Monitoring

```python
# monitoring.py

import logging
from prometheus_client import Counter, Histogram

publish_total = Counter('pompom_publish_total', 'Total publishes', ['platform', 'status'])
publish_duration = Histogram('pompom_publish_duration_seconds', 'Publish duration')

@publish_duration.time()
def monitored_publish(video_path, caption, content_id):
    report = publish_to_meta(video_path, caption, content_id)
    
    for result in report.results.values():
        publish_total.labels(
            platform=result.platform,
            status=result.status
        ).inc()
    
    return report
```

### 3. Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def publish_with_retry(video_path, caption, content_id):
    report = publish_to_meta(video_path, caption, content_id)
    if not report.ok:
        raise Exception(f"Publishing failed: {report.failures}")
    return report
```

---

## Support

Entegrasyon konusunda sorularınız için:
- Documentation: [README.md](README.md)
- Examples: [EXAMPLE_USAGE.md](EXAMPLE_USAGE.md)
- Quick Start: [QUICKSTART.md](QUICKSTART.md)
