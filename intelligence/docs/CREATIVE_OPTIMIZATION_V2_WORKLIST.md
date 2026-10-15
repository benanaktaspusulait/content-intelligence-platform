# Creative Optimization Engine V2 — İş Listesi

Durum: **TAMAMLANDI — CREATIVE_OPTIMIZATION_V2_READY**. Gerçek frontend/backend/ML hattında, izole veritabanı ve mock sağlayıcıyla maddi sahneleme değişikliği gösterildi. Gerçek sağlayıcı ve görsel/izleyici faydası doğrulanmış değildir.

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

- [x] Gerçek Mimi girdileriyle tam prodüksiyon promptu içeren anlamlı önce/sonra fixture'ı oluştur.
- [x] Maddi iyileştirme, kozmetik değişim, keyfî zaman bölme, yürütme regresyonu, hikâye sapması, faydası doğrulanmamış geçerli aday ve KEEP_ORIGINAL durumlarını test et.
- [x] Mock sağlayıcıyla gerçek dispatch → teşhis/plan → prompt → source/canonical → eleştiri → comparison hattını uçtan uca çalıştır.
- [x] Tek aday/sıfır aday, bütçe/idempotency/recovery, mevcut adaylar ve prompt sürümü değişmezliği regresyonlarını çalıştır.
- [x] İlgili ML, backend ve frontend regresyonlarını çalıştır; sonuçları sayıları ve sınırlarıyla kaydet.

## 5. Dağıtım ve kapanış

- [x] deploy.sh ile etkilenen servisleri dağıt; image/health/sürüm eşleşmesini doğrula.
- [x] Dağıtılmış frontend/backend ile izole mock uçtan uca kabulünü yap; gerçek sağlayıcı kapalı kalsın.
- [x] Tarayıcıda gerçek iyileştirme kanıtı ve canonical skor ayrımını, onaysız prompt yaratılmadığını doğrula.
- [x] Tarihî kayıtlar/hikâye/Prompt 10/Step 6 governance/F8 değişmezliğini doğrula.
- [x] 16 başlıklı son raporu, somut Mimi önce/sonrasını ve sonraki tek ücretli deneme için açık yetki + pozitif sınırlı bütçe gereksinimini yaz.
- [x] Kanıta göre CREATIVE_OPTIMIZATION_V2_READY veya CREATIVE_OPTIMIZATION_V2_INCOMPLETE durumunu ver.

## Çalışma günlüğü

- 2026-10-15: Kullanıcı isteği okundu; bu liste uygulamaya başlamadan oluşturuldu. Önce mevcut hat ve gerçek kayıtlar inceleniyor.

- Kök neden denetimi: `output/verification/creative-optimization-v2/root-cause-audit.md`. Gerçek kaynak ve provenance salt okunur alındı. V2 uygulaması mevcut rol içinde ilerliyor.

- V2 çekirdeği ve nitel karşılaştırma eklendi. 115 odaklı ML testi ve 99 frontend testi geçti. İzole canlı hat A için maddi değişiklik / B için regresyon tespit etti; son imaj ve metrik doğrulaması sürüyor.

- Sonuç: 176 ML + 99 frontend + 47 backend + 27 queue testi geçti; 3 isteğe bağlı backend testi atlandı. İzole gerçek HTTP kabulü ve tarayıcıda önce/sonra, A/B navigasyonu ve B regresyon engeli doğrulandı. Üretimde 69 eski kayıt, Prompt 10, 1.11 skorları korundu. Mühendislik önerisi KEEP_ORIGINAL; canlı legacy ekranın mevcut REVIEW_MATERIAL_CANDIDATE / kanıtlanmamış fayda etiketi değiştirilmedi.
- Ayrıntılı 16 bölümlü rapor: `output/verification/creative-optimization-v2/report.md`; makine sonucu: `result.json`. Gerçek çağrı, otomatik onay, üretim prompt sürümü, render ve commit/push yok.

- Canlı son kontrolde bağlam farkı kaydedildi: mevcut legacy UI KEEP_ORIGINAL yerine REVIEW_MATERIAL_CANDIDATE gösteriyor; bu önceki adaylarda kanıtlanmış fayda veya onay anlamına gelmiyor. Tarihî değerlendirme değiştirilmedi; ayrım raporda açıklandı.

## Ek kabul — tanıma ve üretim kanıtlarını ayır

- [x] Hazır plan fixture'larının yalnız değerlendirme/integrasyon kanıtı olduğunu açıkça işaretle.
- [x] Hazır cevap almayan, çalışma anındaki teşhis ve hedeflerden plan kuran reaktif test double ile üretim hattını doğrula.
- [x] Hedef değişimi, kaynak değişimi ve desteklenmeyen hedef için karşı-olgusal testleri çalıştır; cevap tekrarını dışla.
- [x] İki yetenek için ayrı kanıt ve gerçek model etkinliği için UNVERIFIED durumunu raporla. Ücret/onay sınırlarını koru.

- Ek kabul sonucu: hazır cevapla değerlendirme ve girdiye tepki veren sınırlı yeniden yapılandırma ayrı belgelendi. 5 yeni + 15 mevcut = 20 odaklı test geçti. Gerçek modelin yaratıcı etkinliği UNVERIFIED; READY yalnız uygulama hazırlığıdır. `output/verification/creative-optimization-v2/generation-vs-recognition.md`.

## Model katkısını artırma — model-authored-production-v1

- [x] Gerçek sağlayıcı yanıtındaki dar seçim alanını ve şablon derleyicisini incele.
- [x] Mevcut V2'ye kaynak referanslı model-yazarlı prodüksiyon şeması ekle; eski kayıtların yorumunu koru.
- [x] Uzamsal ilişki, koreografi, sonuç, durum geçişi, zaman sunumu, kompozisyon ve üretici kısıtlarını doğrula ve metni koruyarak derle.
- [x] Maddi değişiklik, kaynak dışı değişiklik, kozmetik genişleme ve üretim riski kontrollerini uygula.
- [x] Açık şablon fallback'i ile model/sunucu/kaynak kökenini ayır; sessiz fallback yapma.
- [x] Kaydedilmiş Mimi girdileri ve mock yanıtlarla temas + 2→4→8 çoklu-beat örneği ve olumsuz durumları test et.
- [x] Canonical/source/critic/risk ve tarihî gerçek yanıt uyumluluğunu doğrula; tam önce/sonra raporunu yaz.
- [x] Etkilenen servisleri dağıtıp salt okunur sözleşme/tarihî kayıt kontrolünü tamamla; gerçek çağrı yapma.

- Kapanış: 25 model-yazarlı sözleşme testi dahil 221 ML, 47 backend ve 70 frontend testi geçti; 3 backend testi koşullu olarak atlandı. Sözleşme ve kaynak/derleyici/model kökeni doğrulandı. Gerçek yaratıcı etkinlik UNVERIFIED. Tam örnek ve kanıt: `output/verification/creative-v2-model-authored/MODEL_AUTHORED_ACCEPTANCE_REPORT.md`. Çoklu-beat mock örneğinde canonical 88.40625/B değişmedi; execution critic uyarıları nedeniyle KEEP_ORIGINAL/onay kapalı. Gerçek sağlayıcı çağrısı yok.

## Gerçek yanıt sonrası sözleşme ve yaratıcı nitelik düzeltmesi — v2

- [x] Gerçek ikinci çağrının özgün yanıtını değişmez regresyon fixture'ı olarak kullan; teknik ve yaratıcı sonuçları ayır.
- [x] Kaynak beat aralığı tekrarını, yeni alt zamanlamayı, süre değişikliğini ve desteksiz zaman iddiasını ayır.
- [x] Yeni isteklerde kaynak kimliklerini enum ve beat bazlı makine sözleşmesiyle sınırla; gerçek kaynak anılışlarını generik olarak çıkar.
- [x] Değişmeyen anlatı/ayarları doldurtmayan, tek güçlü fiziksel müdahaleyi isteyen talimatları sürümle.
- [x] Maddi fark değerlendirmesini teknik geçerlilikten ayır; gerçek A/B'yi kozmetik başarıya yükseltme.
- [x] Ücretsiz deterministik/mock testler, kaynak/canonical/critic/F8 regresyonları ve eski sürüm uyumluluğunu doğrula.
- [x] Tam rapor ve sonraki tek deney önerisini hazırla; ücretli deney yapma.

- Sonuç: model-authored-production-v2 dağıtıldı. 244 ML / 47 backend / 70 frontend testi geçti; 3 koşullu backend testi atlandı. Özgün A/B zamanları kabul ediliyor; kaynak kimlikleri hâlâ geçersiz ve yaratıcı farkları VALID_BUT_EQUIVALENT, öneri KEEP_ORIGINAL. 75 tarihî kayıt değişmedi, yeni ücretli çağrı yok. Sonraki öneri A; yeni yetki gerektirir. Rapor: `output/verification/creative-v2-contract-repair-v2/REAL_MODEL_FAILURE_REPAIR_REPORT.md`.
