# Post-family operasyonel akış — güncel hazırlık durumu

Güncelleme: 9 Ekim 2026. Kod ana proje dizinindeki `master` üzerinde. Bu düzeltmeler için yeni worktree oluşturulmadı. Güncel kabul sınırları [durum raporunda](../POMPOM_FIX_PROGRESS.md), dağıtım ve canlı test sonuçları [deploy kanıtlarında](../fix-evidence/live-2026-10-09/README.md).

## Çalışan ortam

Mevcut Docker ortamı güncellendi: arayüz http://localhost:4200, backend 8080, ML 8000. Backend, ML, render ve PostgreSQL sağlıklı; arayüz HTTP ve tarayıcı kontrollerini geçti. Veritabanı V55'e yükseltildi, mevcut kayıt sayıları korundu. Önceki 4215/8085/8015 adresleri izole fixture ortamına aittir; deploy edilen uygulamanın adresi değildir.

Prompt detay ekranında operatör **Operasyonel yaratıcı iş akışı v1** profilini açıkça seçer. Family 1–10 sözleşmeleri ayrı kalır. Kesin kaynak/sürüm/hash, eksik kanıtın UNKNOWN kalması ve ayrı üretim yetkilendirmesi korunur.

## Canlı metin rolleri

Kullanıcı ücretli testlere sonradan açıkça izin verdi. STORY, DeepSeek `deepseek-flash` ile; BUILD_PROMPT ve MINIMAL_REPAIR, OpenAI `gpt-4o-mini-2024-07-18` ile sınırlandırılmış gerçek çağrıları geçti. Minimal düzeltmede görülen JSON biçim sorunu düzeltildi ve regresyon testi eklendi. Üç rolün sunucu model/fiyat ayarları yapılandırıldı; çağrı başına açık maliyet tavanı gerekir. Anahtarlar Git dışında özel `.env` dosyalarında kalır.

Bu testler metin taşıma ve çıktı sözleşmesini doğrular. Üretilen hikâye/prompt/yama NOT_VALIDATED kalır; bağımsız inceleme ve üretim yetkilendirmesinin yerini almaz. Genel readiness yanıtındaki `liveVerified: false`, özel canlı kanıtların burada kayıtlı olduğu gerçeğiyle karıştırılmamalıdır.

## Açık kabul sınırları

- Daha geniş B14 vision/critic/gerçek üretilmiş video kabulü tamamlanmadı.
- OpenArt mock durumda; semantik video çağrıları ve yayın anahtarları kapalı. Bu doğrulamada medya üretilmedi ve yayın yapılmadı.
- B17'nin sentetik eğitim → terfi → tahmin → rollback zinciri doğrulandı. Gerçek üretim modeli için doğrulanmış, olgunlaşmış veri gerekir; üretim model kaydı hâlâ boş.
- Kaynak kanıtı eksik eski medya için kesin lineage veya görsel PASS uydurulmaz. Audience/platform nedenselliği sentetik fixture'lardan çıkarılmaz.

Orijinal kabul ölçütleri [iş listesinde](../POMPOM_END_TO_END_BACKLOG.md), tarihsel ana çalışma alanı aktarım kanıtı [master-transfer.json](../../data/workflow/reports/master-transfer.json) dosyasındadır.
