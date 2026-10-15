# Adaptive Creative Optimization V3 — İş Listesi

> CPQ V1 implementation addition (2026-10-15): the separate approved-for-implementation contract and calibration/fidelity tooling are tracked in [CPQ V1 implementation report](CREATIVE_PROMPT_QUALITY_V1_IMPLEMENTATION_REPORT.md). CPQ grading remains inactive; this does not change V3 canonical feasibility or authorize any provider dispatch.

## CPQ V1 integration follow-up

- [x] Finalize architecture direction as approved for implementation while preserving activation gates.
- [x] Implement versioned six-dimension pre-render text evidence preview without uncalibrated grades.
- [x] Implement authenticated exact-binding fidelity review and UNKNOWN consumer fallback.
- [x] Implement corpus import, blinded reviewer judgments, structural readiness and held-out diagnostic calibration preview.
- [x] Keep source fidelity, canonical evaluation, CPQ preview and F8/render readiness separate in Step 6.
- [x] Make Step 6 assessment creation explicit; loading saved optimization state does not create CPQ records.
- [x] Report CPQ opportunity, canonical A attainability and inactive quality target separately in V3 preflight.
- [ ] Complete relevant full regression suites without host resource exhaustion.
- [ ] Deploy via `intelligence/scripts/deploy.sh` and verify runtime artifacts.
- [ ] Verify deployed Step 6 CPQ panel and authenticated reviewer capability in a real browser.
- [ ] Populate authorized independent calibration corpus, held-out validation, legitimate B-to-A golden acceptance and formal activation record before enabling grades.

Durum: ADAPTIVE_CREATIVE_OPTIMIZATION_V3_INCOMPLETE. Uygulama ve güvenli durdurma dağıtıldı; tam ürün akışında bağımsız kanıtla nitelendirilmiş B→A golden kabulü açık. Sistem doğruluğu ile gerçek modelin yaratıcı etkinliği ayrı raporlanacak. Bu görev hiçbir gerçek DeepSeek/OpenAI üretim çağrısına izin vermez.

Hedef: Mevcut V2 akışını kullanarak A/A+ hedefine yönelmek; B sonucunu tamamlanmış optimizasyon saymamak. Kanıtlanamayan veya korunan hikâyeyle ulaşılamayan hedef için çağrı yapmadan açık engel döndürmek. Kanonik değerlendirme, skorlar, eşikler ve geçmiş kayıtlar değişmeyecek.

## Faz 1 — Not tanımı ve ulaşılabilirlik denetimi (routing değişmeden önce)

- [x] Ruleset 1.11 gerçek not eşiklerini, A+ varlığını ve skor toplama formülünü koddan çıkar; render kuyruğunun 92 eşiğinden ayır.
- [x] Güncel Mimi analizi, Prompt 10/v1, onaylı hikâye ve üretim ayarlarını salt okunur yükle; bütünlük kanıtlarını kaydet.
- [x] Her puan kaybını kural, ağırlık/katkı, dayanak ve onarım türüyle eşleştir: TEXT_REPAIRABLE / CREATIVE_RECONSTRUCTION_REPAIRABLE / EVIDENCE_REQUIRED / GOVERNED_POLICY_DECISION_REQUIRED / PROTECTED_STORY_CONFLICT / EVALUATOR_DEFECT / NOT_CURRENTLY_ATTAINABLE.
- [x] İki gerçek deneme içeren korunan hikâyeye üçüncü olay eklemeden, mevcut kanıtla desteklenen üst sınırı hesapla; ATTEMPT_001 istisnasının kanonik FAIL/skoru değiştirmediğini doğrula.
- [x] A'nın render öncesi ulaşılabilirliğini ve hangi ek kanıtların gerektiğini kısa raporla. Gerekirse ayrı kalite rubriği için yalnız yönetilen ADR öner; yeni not icat etme.
- [x] Faz 1 raporunu tamamladıktan sonra routing uygulamasına geç.

## Faz 2 — Mevcut sözleşme onarımlarını koru ve doğrula

- [x] Önceki görevin model-authored-production-v2 zaman/kaynak kimliği düzeltmelerini incele; tekrar uygulama veya geriye dönük anlam değişikliği yapma.
- [x] İkinci gerçek OpenAI yanıtının değişmez fixture'ını yeniden oynat; teknik geçerlilik, kaynak sadakati, yaratıcı maddilik, risk ve kanonik uygunluğu ayrı göster.
- [x] Yeni alt zamanlama, olay sırası, süre değişikliği, geçersiz kimlik ve kozmetik paragraf negatif testlerini koru.
- [x] Tam özgün bağlam + yalnız teşhisle gerekçelenen prodüksiyon müdahaleleri sözleşmesini ve bağımlı beat değişikliği gerekçelerini doğrula.

## Faz 3 — Sağlayıcı bağımsız üretim ve yetenek profilleri

- [x] Mevcut OpenAI/DeepSeek adaptörlerini, rol yapılandırmasını ve maliyet ön kontrolünü incele; aynı akışı genişlet.
- [x] Güncel resmî OpenAI/DeepSeek belgelerinden model kimlikleri, uç noktalar, JSON/JSON Schema, bağlam/çıktı limitleri, fiyat, reasoning davranışı ve kullanım ömrünü doğrula.
- [x] DeepSeek birincil / OpenAI yükseltme için ayrı, açık model/yetenek profilleri ve sağlayıcıya özgü serileştirme uygula; model adı varsayma veya sessiz fallback yapma.
- [x] JSON Schema desteklenmeyen profilde sağlayıcı uyumlu JSON sözleşmesini aynı deterministik kaynak doğrulamasına bağla.
- [x] Ham yanıt, kullanım, model/sağlayıcı ve kaynak/model/derleyici kökenini normal kalıcı kanıt akışında koru.

## Faz 4 — Sınırlı adaptif yönlendirme ve yetkilendirme

- [x] DEEPSEEK_ONLY, OPENAI_ONLY, ADAPTIVE modlarını mevcut Step 6 komutuna ekle.
- [x] Üretim öncesi hedef ulaşılabilirlik kontrolünü zorunlu kıl; kanıt/hikâye engelinde gereksiz çağrıları durdur.
- [x] ADAPTIVE için DeepSeek → doğrulama → kalite/kanonik karar → gerekçeli koşullu OpenAI yükseltmesi uygula.
- [x] A yeterliyse dur; B iyileşme / eşdeğer / regresyon / teknik sözleşme hatası / ulaşılamaz hedef durumlarını ayır.
- [x] Sağlayıcı/model, istek sayısı, toplam bütçe, token, tur ve gecikme limitlerini açık operatör onayına bağla; ikinci sağlayıcı onayı yoksa gönderme.
- [x] Normal kalıcı rezervasyon, idempotency, append-only audit ve belirsiz gönderimde tekrar yasağını iki aşamada uygula.
- [x] Yükseltme brief'ine özgün kaynak, korunacak doğrulanmış değişiklikler, gerçek açıklar ve başarısızlık kanıtını koy; reddedilmiş metni tercih edilen cevap yapma.

## Faz 5 — Kalite, hedef uygunluğu ve ürün akışı

- [x] Mevcut altı yaratıcı kalite boyutunda kaynak destekli fark / doğrulanmamış hipotez / değişim yok / regresyon / eksik kanıt ayrımını uygula.
- [x] Aynı ruleset/hikâye/ayar bağında Original–DeepSeek–OpenAI karşılaştır; en yüksek skor/uzunluk/yenilik otomatik tercih olmasın.
- [ ] A/A+ uygunluğunu gerçek not sözleşmesi, yeterli uygulanabilir kanıt ve regresyon yokluğu ile sınırla; A+ yoksa kullanma. Politika uygulandı; üreticinin UNKNOWN çıktısından bağımsız PASS kanıtına gerçek ürün bağı henüz tamamlanmadığı için tam kabul açık.
- [x] BEST AVAILABLE DRAFT ile TARGET-QUALIFIED FINAL CANDIDATE ayrımını ve istenen açık workflow durumlarını mevcut arayüze ekle.
- [x] B iyileşmesini ilerleme olarak kaydet; hedefe erişildi/success diye sunma. Seçim/onay/yeni prompt sürümü yalnız açık operatör kararıyla olsun.
- [ ] Gerçek ve mock kanıtları ayıran kısa olay/metrik sözleşmesini ekle; yeni büyük dashboard kurma. Sözleşme ve çalışma raporu eklendi; bağımsız değerlendirme/operatör kabul kanıtının tam raporlama projeksiyonu açık.

## Faz 6 — Kabul testleri, dağıtım ve kapanış

- [ ] Gerçek Mimi ve mevcut onaylı golden girdilerle, no-egress mock ortamında 20 kabul durumunu test et: B→A yolu, DeepSeek A'da durma, B/eşdeğer/regresyon yükseltmesi, ortak sözleşme hatasında durma, OpenAI A, her iki B, kanıt/hikâye engeli, eksik izin, bütçe, tekrar, kısmi hata, kimlik/zamanlama, tarihî replay, eşit skorlu maddi fark, bütünlük.
- [x] Negatif güvenlik/onay kapsamı ve ücret idempotency testlerini ekle; mock A fixture'larını gerçek yaratıcı yetenek kanıtı diye sunma.
- [x] ML/backend/frontend ile bütçe, governance, F8 ve render kuyruğu ilgili regresyonlarını çalıştır.
- [x] Etkilenen servisleri deploy.sh ile dağıt; imaj/kaynak sürümünü ve gerçek uygulama arayüzünü doğrula.
- [x] Sağlayıcı taklitleri ve disposable veritabanıyla dış ağa çıkışsız uçtan uca uygulama kabulünü çalıştır; üretim kayıtlarına yazma.
- [x] Üretim geçmişi, Prompt 10/v1, hikâye, Ruleset 1.7–1.11, önceki sağlayıcı yanıtları, governance ve F8 bütünlüğünü doğrula.
- [x] ADAPTIVE_CREATIVE_OPTIMIZATION_V3_REPORT.md dosyasını 20 rapor maddesiyle tamamla; READY veya INCOMPLETE sonucunu kanıta göre ver.

## Çalışma günlüğü

- İş listesi oluşturuldu. İlk adım: not sözleşmesi ve Mimi için savunulabilir üst sınır denetimi. Routing koduna henüz dokunulmadı.

- Faz 1 tamamlandı: A >=92, A+ yok; mevcut kanıt/korunan kaynak altında iyimser koşullu tavan 89.3125/B. Ayrıntı: ADAPTIVE_CREATIVE_OPTIMIZATION_V3_GRADE_AUDIT.md. Routing henüz değiştirilmedi.

- Faz 2: önceki 48 sözleşme testi geçti; gerçek A/B yanıtlarında 2/4 hatalı kimlik ayrı teşhis edildi, doğru kaynak zaman pencereleri korunuyor.
- Faz 3–5: mevcut V2 üzerinde yapılandırılan sağlayıcı adaptörü, bağlı bütçe/yetki, kalıcı V3 koşullu yönlendirme, altı boyut, A uygunluğu ve taslak/nihai ayrımı uygulandı. Kabul testleri ve dağıtım sürüyor.

- Sonuç: 269 ML, 56 backend, 72 frontend ve 44 render admission testi geçti; backend 3 koşullu eski test atlandı (geçti sayılmadı).
- Dağıtılmış ve izole gerçek Mimi akışı: TARGET_BLOCKED_BY_STORY_CONSTRAINT, 88.40625/B, koşullu tavan 89.3125; gerçek sağlayıcı çağrısı 0, üretim yazması 0, 75 tarihî kayıt değişmedi.
- Açık kabul: kontrollü A/B karar oracle testleri gerçek, onaylı golden girdiyle tam ürün B→A kabulünün yerine sayılmadı. Kaynak sadakati UNKNOWN → bağımsız PASS bağı ve bu kanıtı tüketen tam A senaryosu gerekiyor. İnaktif ADR önerisi eklendi; not veya tarihî kayıt değiştirilmedi.
