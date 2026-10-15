# Creative Optimization Engine V2 — İş Listesi

Durum: UYGULAMA SÜRÜYOR. READY kabulü yalnız gerçek uygulama hattında anlamlı yeniden yapılandırma gösterildikten sonra verilecek.

## Korunacak sınırlar

Content 10 / immutable Prompt ID 10 (v1), onaylı hikâye, Ruleset 1.11 ve tüm tarihî kayıtlar korunacak. Canonical skor ile yaratıcı iyileştirme ayrı tutulacak. Gerçek/ücretli sağlayıcı çağrısı, otomatik retry/onay, prompt sürümü oluşturma, görsel/video üretimi, yayın, doğrudan production DB yazımı ve commit/push yapılmayacak. Canlı mock doğrulaması production kayıtlarını değiştirmeyen izole test altyapısında yapılacak.

## 1. Kök neden ve mevcut mimari

- [x] PROMPT_OPTIMIZATION ve BUILD_PROMPT talimatlarını, dispatch/bütçe/idempotency/persistence sözleşmelerini incele.
- [x] Plan-first, Video Plan IR, kaynak sadakati, materiality, risk, comparison ve Step 6 akışını izle.
- [x] Yüzeysel adayların nedenlerini dosya/satır kanıtlarıyla yaz; tekrar kullanılacak bileşenleri belirle.
- [x] Gerçek kayıtlı Prompt 10, onaylı hikâye, güncel ayarlar ve analiz girdilerini salt okunur yükle; başlangıç bütünlük kanıtını kaydet.

## 2. Yaratıcı teşhis ve yeniden yapılandırma

- [x] Korumalı hikâye / düzenlenebilir prodüksiyon katmanlarını açık sözleşmeye ayır.
- [x] Altı boyutlu, sürümlü nitel yaratıcı değerlendirme modelini tanımla; açılış stratejisini dikkate al.
- [x] Beat/zaman, tam kaynak, somut fırsat, değişiklik, gözlenebilir sonuç, risk, güven ve kanıt sınıfı içeren teşhisi mevcut hatta ekle.
- [x] Teşhis → hedef → eylem/sonuç planı → sadakat → tam prompt sırasını uygula.
- [x] Tek savunulabilir aday veya NO_JUSTIFIED_IMPROVEMENT sonucuna izin ver; iki aday zorunluluğunu uçtan uca kaldır.
- [x] Hikâye değişikliği gerektiren önerileri STORY_CHANGE_REQUIRES_APPROVAL olarak ayır.

## 3. Eleştiri, karşılaştırma ve metrikler

- [x] Kozmetik kamera/adjektif değişimi ve aynı eylemin zamanlara bölünmesini yetersiz say.
- [x] Kaynaklı sahneleme, mekânsal ilişki, koreografi, sonuç ve durum değişimlerini karşılaştır; benzerlik oranını tek karar ölçütü yapma.
- [x] Teşhisle ilişkilendirilmiş sınırlı eleştiri/düzeltme geri bildirimi ekle; ek ücretli çağrı için ayrı yetki şartını koru.
- [x] Önce/sonra tam alıntı, gözlenebilir fark, gerekçe, hikâye dayanağı, risk ve belirsizlik içeren değişiklik kanıtını ekle.
- [x] Canonical değerlendirmeden ayrı nitel sonuçları ve KEEP_ORIGINAL kararını koru.
- [x] Minimal Step 6 görünümü ile yeni kanıtı göster; otomatik seçim/onay yapma.
- [x] Material başarı, eşdeğer ret, sadakat/risk/canonical regresyonu, operatör tercihi ve maliyet/boşa çağrı metriklerinin veri sözleşmesini ekle; eksik veriyi sıfır sayma.

## 4. Deterministik ve gerçek hat kabulü

- [ ] Gerçek Mimi girdileriyle tam prodüksiyon promptu içeren anlamlı önce/sonra fixture'ı oluştur.
- [ ] Maddi iyileştirme, kozmetik değişim, keyfî zaman bölme, yürütme regresyonu, hikâye sapması, faydası doğrulanmamış geçerli aday ve KEEP_ORIGINAL durumlarını test et.
- [ ] Mock sağlayıcıyla gerçek dispatch → teşhis/plan → prompt → source/canonical → eleştiri → comparison hattını uçtan uca çalıştır.
- [ ] Tek aday/sıfır aday, bütçe/idempotency/recovery, mevcut adaylar ve prompt sürümü değişmezliği regresyonlarını çalıştır.
- [ ] İlgili ML, backend ve frontend regresyonlarını çalıştır; sonuçları sayıları ve sınırlarıyla kaydet.

## 5. Dağıtım ve kapanış

- [ ] deploy.sh ile etkilenen servisleri dağıt; image/health/sürüm eşleşmesini doğrula.
- [ ] Dağıtılmış frontend/backend ile izole mock uçtan uca kabulünü yap; gerçek sağlayıcı kapalı kalsın.
- [ ] Tarayıcıda gerçek iyileştirme kanıtı ve canonical skor ayrımını, onaysız prompt yaratılmadığını doğrula.
- [ ] Tarihî kayıtlar/hikâye/Prompt 10/Step 6 governance/F8 değişmezliğini doğrula.
- [ ] 16 başlıklı son raporu, somut Mimi önce/sonrasını ve sonraki tek ücretli deneme için açık yetki + pozitif sınırlı bütçe gereksinimini yaz.
- [ ] Kanıta göre CREATIVE_OPTIMIZATION_V2_READY veya CREATIVE_OPTIMIZATION_V2_INCOMPLETE durumunu ver.

## Çalışma günlüğü

- 2026-10-15: Kullanıcı isteği okundu; bu liste uygulamaya başlamadan oluşturuldu. Önce mevcut hat ve gerçek kayıtlar inceleniyor.

- Kök neden denetimi: `output/verification/creative-optimization-v2/root-cause-audit.md`. Gerçek kaynak ve provenance salt okunur alındı. V2 uygulaması mevcut rol içinde ilerliyor.

- V2 çekirdeği ve nitel karşılaştırma eklendi. 115 odaklı ML testi ve 99 frontend testi geçti. İzole canlı hat A için maddi değişiklik / B için regresyon tespit etti; son imaj ve metrik doğrulaması sürüyor.
