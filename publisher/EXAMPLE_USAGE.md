# Pompom Meta Publisher - Kullanım Örnekleri

## Kurulum

```bash
cd pompom-meta-publisher

# Virtual environment oluştur
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Paketi kur
pip install -e .

# S3 storage kullanacaksan
pip install boto3
```

## Konfigürasyon

```bash
# .env dosyası oluştur
cp .env.example .env

# .env dosyasını düzenle ve tokenlarını ekle
nano .env
```

`.env` örneği:

```bash
# Meta API Credentials
META_PAGE_ID=123456789012345
META_INSTAGRAM_ACCOUNT_ID=987654321098765
META_PAGE_ACCESS_TOKEN=your-long-lived-page-access-token-here

# Platforms
META_ENABLE_FACEBOOK=true
META_ENABLE_INSTAGRAM=true

# Safety - Test için true, gerçek yayın için false
META_DRY_RUN=false

# Storage (Instagram için gerekli)
META_STORAGE_BACKEND=s3
META_S3_BUCKET=pompom-reels
META_S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com
META_S3_PUBLIC_BASE_URL=https://cdn.pompomhills.com
META_S3_ACCESS_KEY_ID=your-access-key
META_S3_SECRET_ACCESS_KEY=your-secret-key
META_S3_REGION=auto
```

## Kullanım Örnekleri

### 1. Konfigürasyonu Kontrol Et

```bash
python publish_pompom_reel.py --check
```

Çıktı:
```json
{
  "api_version": "v26.0",
  "dry_run": false,
  "facebook": {
    "enabled": true,
    "configured": true,
    "page_id": "123456789012345",
    "page_name": "Pompom Hills",
    "reachable": true
  },
  "instagram": {
    "enabled": true,
    "configured": true,
    "account_id": "987654321098765",
    "username": "pompom.hills",
    "reachable": true,
    "publishing_limit": {
      "config": {"quota_total": 50},
      "quota_usage": 12
    }
  },
  "storage": {
    "backend": "s3",
    "can_host": true
  }
}
```

### 2. Dry Run (Test)

```bash
python publish_pompom_reel.py \
    --video ../Can\ You\ Find\ It?/01_lucas_lost_treasure/output/final.mp4 \
    --caption "Can you find Lucas's lost treasure? 🔍✨ #PompomHills #KidsEducation" \
    --content-id lucas-treasure-001 \
    --dry-run
```

### 3. Gerçek Yayın (Facebook + Instagram)

```bash
python publish_pompom_reel.py \
    --video ../Can\ You\ Find\ It?/01_lucas_lost_treasure/output/final.mp4 \
    --caption "Can you find Lucas's lost treasure? 🔍✨ #PompomHills #KidsEducation" \
    --content-id lucas-treasure-001 \
    --live
```

### 4. Sadece Facebook'a Yayınla

```bash
python publish_pompom_reel.py \
    --video output/kiko-morning.mp4 \
    --caption "Good morning with Kiko! ☀️" \
    --content-id kiko-morning-001 \
    --platform facebook \
    --live
```

### 5. Sadece Instagram'a Yayınla

```bash
python publish_pompom_reel.py \
    --video output/mimi-feelings.mp4 \
    --caption "Mimi learns about feelings 💕" \
    --content-id mimi-feelings-001 \
    --platform instagram \
    --live
```

### 6. Caption'ı Dosyadan Oku (Markdown)

`metadata/social.md`:
```markdown
# Social Media Content

## Instagram Caption

Watch Kiko discover the magic of nature! 🌿✨

In this episode, Kiko explores the forest and learns about different plants.
Perfect for curious little minds! 

#PompomHills #KidsLearning #NatureExploration #EducationalContent
#PreschoolFun #ToddlerActivities
```

Kullanım:
```bash
python publish_pompom_reel.py \
    --video output/kiko-nature.mp4 \
    --caption-file metadata/social.md \
    --caption-section "Instagram Caption" \
    --content-id kiko-nature-001 \
    --live
```

### 7. Caption'ı Text Dosyasından Oku

`metadata/caption.txt`:
```
Opa tells a wonderful story! 📖✨

Join Opa under the big tree as he shares tales of adventure and wisdom.

#PompomHills #Storytime #KidsStories
```

Kullanım:
```bash
python publish_pompom_reel.py \
    --video output/opa-story.mp4 \
    --caption-file metadata/caption.txt \
    --content-id opa-story-001 \
    --live
```

### 8. Zaten Yayınlanmış Videoyu Tekrar Yayınla (Force)

```bash
python publish_pompom_reel.py \
    --video output/kiko-discovery.mp4 \
    --caption "Updated caption with new hashtags! 🌟" \
    --content-id kiko-discovery-001 \
    --force \
    --live
```

### 9. Pre-hosted URL Kullan (Storage Backend Skip)

```bash
python publish_pompom_reel.py \
    --video output/reel.mp4 \
    --video-url https://cdn.pompomhills.com/reels/special-reel.mp4 \
    --caption "Special reel! 🎉" \
    --content-id special-reel-001 \
    --live
```

### 10. Yayın Geçmişini Gör

```bash
python publish_pompom_reel.py --history
```

Çıktı:
```
────────────────────────────────────────────────────────────────────────────────────────────────
  content_id                platform   status             media_id               published_at
────────────────────────────────────────────────────────────────────────────────────────────────
  kiko-discovery-001        instagram  SUCCESS            18012345678901234      2026-09-30T15:23:45+00:00
  kiko-discovery-001        facebook   SUCCESS            123456789012345_98765  2026-09-30T15:23:12+00:00
  lucas-treasure-001        instagram  SUCCESS            18012345678901235      2026-09-30T14:45:30+00:00
  lucas-treasure-001        facebook   SUCCESS            123456789012345_98766  2026-09-30T14:45:10+00:00
────────────────────────────────────────────────────────────────────────────────────────────────
```

## Python API Kullanımı

```python
from pathlib import Path
from pompom_meta_publisher.publishing import publish_to_meta

# Basit kullanım
report = publish_to_meta(
    video_path=Path("output/final-reel.mp4"),
    caption="Watch Kiko discover something amazing! 🌟",
    content_id="kiko-discovery-001",
)

# Sonuçları kontrol et
if report.ok:
    print("✓ Published successfully!")
    for result in report.published:
        print(f"  {result.platform}: {result.permalink}")
else:
    print("✗ Publishing failed:")
    for failure in report.failures:
        print(f"  {failure.platform}: {failure.detail}")

# Exception fırlat istersen
try:
    report.raise_for_status()
except Exception as e:
    print(f"Error: {e}")
```

## Toplu Yayın Örneği

`batch_publish.py`:
```python
#!/usr/bin/env python3
from pathlib import Path
from pompom_meta_publisher.publishing import publish_to_meta

# Yayınlanacak videolar
videos = [
    {
        "video": "Can You Find It?/01_lucas_lost_treasure/output/final.mp4",
        "caption": "Can you find Lucas's lost treasure? 🔍✨",
        "content_id": "lucas-treasure-001",
    },
    {
        "video": "Can You Find It?/02_mimis_missing_carrot/output/final.mp4",
        "caption": "Where did Mimi's carrot go? 🥕",
        "content_id": "mimi-carrot-001",
    },
    {
        "video": "Can You Find It?/03_opas_missing_glasses/output/final.mp4",
        "caption": "Help Opa find his glasses! 👓",
        "content_id": "opa-glasses-001",
    },
]

for item in videos:
    print(f"\n📤 Publishing: {item['content_id']}")
    
    try:
        report = publish_to_meta(
            video_path=Path(item["video"]),
            caption=item["caption"],
            content_id=item["content_id"],
        )
        
        if report.ok:
            print(f"✓ Success!")
            for result in report.published:
                print(f"  {result.platform}: {result.media_id}")
        else:
            print(f"✗ Failed:")
            for failure in report.failures:
                print(f"  {failure.platform}: {failure.detail}")
    
    except Exception as e:
        print(f"✗ Error: {e}")
        continue
```

Çalıştır:
```bash
python batch_publish.py
```

## Sorun Giderme

### "Instagram skipped: no public URL"
- `META_STORAGE_BACKEND` ayarını kontrol et (Instagram için HTTPS URL gerekli)
- S3/R2 bucket ayarlarını kontrol et

### "Token is invalid or expired"
- Meta Developer Console'dan yeni token al
- Long-lived Page Access Token kullandığından emin ol

### "Video processing timeout"
- `META_POLL_TIMEOUT` değerini artır (varsayılan: 300 saniye)
- Video dosya boyutunu kontrol et (çok büyükse optimize et)

### "Facebook works but Instagram fails"
- `META_INSTAGRAM_ACCOUNT_ID` doğru mu kontrol et
- Instagram hesabı Professional/Business account mı kontrol et
- Instagram hesabı Facebook Page'e bağlı mı kontrol et

## Notlar

- **Duplicate Protection**: Aynı `content_id` ile iki kez yayın yapamazsın (--force kullanmadıkça)
- **Caption Limit**: Instagram 2200 karakter limiti var, otomatik kısaltılır
- **Dry Run**: Production'a geçmeden önce mutlaka test et
- **Ledger**: Tüm yayınlar `data/publish_log.db` SQLite veritabanında saklanır
- **Tokens**: Token'lar log'lara yazılmaz (otomatik scrubbing)
