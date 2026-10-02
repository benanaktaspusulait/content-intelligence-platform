# Pompom Meta Publisher - Hızlı Başlangıç

## 🚀 5 Dakikada Başla

### 1. Kurulum

```bash
cd pompom-meta-publisher

# Virtual environment oluştur ve paketi kur
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Konfigürasyon

```bash
# .env dosyası oluştur
cp .env.example .env

# Meta token'larını .env'ye ekle
nano .env
```

**Minimum .env:**
```bash
META_PAGE_ID=your-page-id
META_INSTAGRAM_ACCOUNT_ID=your-instagram-id
META_PAGE_ACCESS_TOKEN=your-token

META_ENABLE_FACEBOOK=true
META_ENABLE_INSTAGRAM=true
META_DRY_RUN=false

# Instagram için storage gerekli
META_STORAGE_BACKEND=s3
META_S3_BUCKET=pompom-reels
META_S3_ENDPOINT_URL=https://your-endpoint.com
META_S3_PUBLIC_BASE_URL=https://cdn.pompomhills.com
META_S3_ACCESS_KEY_ID=your-key
META_S3_SECRET_ACCESS_KEY=your-secret
```

### 3. Test Et

```bash
# Konfigürasyonu kontrol et
python publish_pompom_reel.py --check

# Dry run yap
python publish_pompom_reel.py \
    --video output/test.mp4 \
    --caption "Test reel 🎬" \
    --content-id test-001 \
    --dry-run
```

### 4. Yayınla

```bash
# Gerçek yayın
python publish_pompom_reel.py \
    --video output/final-reel.mp4 \
    --caption "Amazing Pompom Hills content! 🌟" \
    --content-id pompom-001 \
    --live
```

## 📋 Sık Kullanılan Komutlar

```bash
# Konfigürasyon kontrolü
python publish_pompom_reel.py --check

# Sadece Facebook
python publish_pompom_reel.py --video video.mp4 --caption "Text" --content-id id-001 --platform facebook --live

# Sadece Instagram
python publish_pompom_reel.py --video video.mp4 --caption "Text" --content-id id-001 --platform instagram --live

# Caption dosyadan oku
python publish_pompom_reel.py --video video.mp4 --caption-file caption.txt --content-id id-001 --live

# Yayın geçmişi
python publish_pompom_reel.py --history

# Tekrar yayınla (force)
python publish_pompom_reel.py --video video.mp4 --caption "Text" --content-id id-001 --force --live
```

## 🔑 Token Alma

### Facebook Page Access Token

1. [Meta Developers](https://developers.facebook.com) → Uygulamanı seç
2. Tools → Graph API Explorer
3. User Token seç → Permissions ekle:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_show_list`
   - `instagram_basic`
   - `instagram_content_publish`
4. Generate Access Token
5. Long-lived token'a çevir:
   ```bash
   curl "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN"
   ```
6. Page Access Token al:
   ```bash
   curl "https://graph.facebook.com/v21.0/PAGE_ID?fields=access_token&access_token=LONG_LIVED_USER_TOKEN"
   ```

## 📊 Çıktı Örneği

```
──────────────────────────────────────────────────────────────────────
  Content    : lucas-treasure-001
  Video      : output/final.mp4
  Hosted URL : https://cdn.pompomhills.com/reels/lucas-treasure-xxx.mp4
  facebook  : SUCCESS  (id=123456789012345_98765)
              https://www.facebook.com/reel/123456789012345
  instagram : SUCCESS  (id=18012345678901234)
              https://www.instagram.com/reel/AbCdEfGhIjK/
──────────────────────────────────────────────────────────────────────
```

## 🎯 Python API

```python
from pompom_meta_publisher.publishing import publish_to_meta

report = publish_to_meta(
    video_path="output/reel.mp4",
    caption="Amazing content! 🌟",
    content_id="pompom-001",
)

if report.ok:
    print("✓ Published!")
    for r in report.published:
        print(f"  {r.platform}: {r.permalink}")
```

## 🆘 Yardım

```bash
python publish_pompom_reel.py --help
```

Detaylı örnekler için: [EXAMPLE_USAGE.md](EXAMPLE_USAGE.md)
