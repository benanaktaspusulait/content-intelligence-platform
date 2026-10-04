# Uçtan Uca İçerik İncelemesi - Parça 01

## Prompt Quality Engine ve Render Yetkilendirme Akışı

**İnceleme tarihi:** 2026-10-03  
**Kapsam:** Prompt metninin parse edilmesinden kalite kararına, kararın saklanmasından render kuyruğuna izin verilmesine kadar olan akış.  
**Yöntem:** Kaynak kod ve mevcut dokümanların içerik/bağlantı incelemesi. Bu çalışma kapsamında test çalıştırılmadı.

---

## 1. Bu Parçada Gerçekte Ne Var?

### Python ML servisi

- Serbest metin prompt'u `Video Plan IR` yapısına çeviren regex/heuristic parser.
- Dört sürümlü kural seti: `1.0`, `1.1`, `1.2`, `1.3`.
- Güncel `1.3` setinde 34 kural ve bu 34 kuralın tamamı için kayıtlı evaluator.
- Deterministic kontroller:
  - consequence sayısı ve yoğunluğu,
  - static-state dominance,
  - tekrar/cycle tespiti,
  - attempt sayısı ve verb-root tekrarı,
  - payoff zamanı ve salience,
  - prop/risk/üretilebilirlik kontrolleri.
- LLM-semantic kontroller:
  - attempt stratejilerinin gerçekten farklı olması,
  - twist'in ana fizik kuralına bağlı olması,
  - doğal karakter hedefi,
  - kuralın izleyici tarafından öğrenilebilir olması,
  - açılış probleminin anlaşılması,
  - karakter performansının okunabilirliği,
  - generation-executable attempt kontrolü.
- Family score, overall score ve `RENDER_READY / NEEDS_REVISION / BLOCKED / SERVICE_ERROR` kararı.
- Prompt sürümü karşılaştırma ve regression checker.
- Template tabanlı auto-fix döngüsü.
- FFmpeg tabanlı dead-air analizi.
- Karakter kimliği/continuity için tasarlanmış post-render QA sınıfı.

### Spring Boot tarafı

- Python servisine bağlanan `QualityMlClient`.
- İki ayrı doğrulama yolu:
  - `/api/quality/validate`: ad hoc/keşif amaçlı, render yetkilendirmez.
  - `/api/v1/intelligence/quality/validate`: content ve prompt version ile ilişkili kanıt üretme yolu.
- `quality_validations` tablosuna validation geçmişi yazılması.
- Prompt SHA-256, ruleset sürümü ve freshness TTL içeren immutable evidence modeli.
- Render servisinin okuyacağı internal evidence endpoint'i.
- Eksik kanıtta fail-closed davranan render gate.

### Angular tarafı

- Prompt girişi, score, failed rules, priority fixes, family scores ve timeline gösteren eski bir `QualityValidatorComponent` var.
- Ancak bu component aktif route tablosuna bağlı değil; çalışan uygulamada erişilebilir bir kalite ekranı değil.

---

## 2. Mevcut Gerçek Akış

1. Spring client, ruleset belirtilmezse Python servisine `latest` gönderiyor.
2. Python parser prompt'u `Video Plan IR` biçimine çeviriyor.
3. Güncel akışta Ruleset `1.3` seçiliyor ve 34 evaluator çalıştırılıyor.
4. Deterministic ve semantic kontrollerden family score ve genel durum üretiliyor.
5. Linked validation endpoint'i content/prompt kimliğini ve prompt hash'ini kaydediyor.
6. Fakat semantic provider/model, producibility validator version ve independent revalidation alanları doldurulmuyor.
7. Evidence servisi bu alanları zorunlu tuttuğu için kaydı `RENDER_READY` olsa bile `NEEDS_REVISION` durumuna indiriyor.
8. Creative render service bu eksik kanıtı kabul etmiyor ve render kuyruğuna izin vermiyor.

**Sonuç:** Kalite değerlendirmesi mevcut; güvenli render kapısı da mevcut. Fakat ikisinin arasındaki production authorization zinciri tamamlanmadığı için sistem bugün uçtan uca render yetkilendiremez.

---

## 3. Tamamlanmış ve Sağlam Bölümler

### 3.1 Kural kataloğu ile evaluator eşleşmesi tamam

Ruleset `1.3` içindeki 34 rule ID'nin tamamı `RuleEngine.evaluators` içinde kayıtlı. Kayıtsız evaluator oluşursa sistem sessizce PASS vermiyor; `SERVICE_ERROR` ile fail-closed davranıyor.

Kaynaklar:

- `intelligence/data/rules/RULESET_1.3.yaml:54-775`
- `intelligence/ml-service/app/rules/rule_engine.py:103-139`
- `intelligence/ml-service/app/rules/rule_engine.py:155-188`

### 3.2 Ruleset sürümleme altyapısı gerçek

Ruleset kataloglama, belirli sürümü yükleme, latest çözümleme ve iki sürümü karşılaştırma kodu var. Spring client normal kullanımda `latest` gönderiyor; dolayısıyla güncel sistem doğrudan `1.0`a takılı kalmıyor.

Kaynaklar:

- `intelligence/ml-service/app/rules/rule_versioning.py:93-243`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityMlClient.java:43-56`

### 3.3 Regression checker ve immutable evidence fikri doğru kurulmuş

Auto-fix sonrası yeniden değerlendirme ve regression kararı var. Render gate ayrıca veritabanındaki `status` değerine körü körüne güvenmiyor; gerekli kanıt alanlarını yeniden kontrol ediyor. Şu an tamamlanmamış olsa da güvenlik yaklaşımı doğru: eksik kanıt render izni üretmiyor.

Kaynaklar:

- `intelligence/ml-service/app/autofix/iteration_loop.py:177-310`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/ValidationEvidenceService.java:41-133`
- `intelligence/creative-render-service/src/main/java/com/pompom/creative/queue/ValidationEvidencePolicy.java`

---

## 4. Kritik Eksikler ve Yanlış Bağlantılar

## P0 - Render authorization zinciri hiçbir kaydı RENDER_READY yapamıyor

Linked validation servisi şu alanları dolduruyor:

- content ID,
- prompt version ID,
- prompt SHA-256,
- deterministic ruleset version,
- validation/freshness zamanı.

Ancak aşağıdaki zorunlu alanları doldurmuyor:

- `semanticProvider`,
- `semanticModelVersion`,
- `producibilityValidatorVersion`,
- `independentRevalidationId`,
- `independentlyRevalidatedAt`.

Evidence servisi bunlardan biri eksikse sonucu kesin olarak `NEEDS_REVISION` yapıyor. Kod yorumları da bu parçanın “later slice” olduğunu açıkça söylüyor.

Etkisi:

- Kalite motoru 100 puan ve `RENDER_READY` döndürse bile render kapısı açılmaz.
- UI/API'de başarılı görünen bir validation üretim hattında kullanılamaz.
- Render dashboard'un gerçek quality gate ile tamamlandığı söylenemez.

Kaynaklar:

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/IntelligenceQualityValidationService.java:13-25`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/IntelligenceQualityValidationService.java:68-90`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/ValidationEvidenceService.java:105-133`

## P0 - Character continuity “vision” kontrolü görüntüyü modele göndermiyor

`CharacterVerifier`, videodan kare çıkarıp base64 görüntüyü provider'a iletiyor. Fakat OpenAI, Claude, Gemini ve Ollama provider'larının tamamı `image` parametresini bilerek siliyor. Yani LLM yalnızca “Expected character: Kiko” gibi metni görüyor; gerçek kareyi görmüyor.

Ayrıca canonical reference image sadece dosyanın varlığı açısından kontrol ediliyor; modele veya karşılaştırmaya hiç katılmıyor.

Etkisi:

- `CONSISTENCY_002` gerçekte karakter continuity doğrulamıyor.
- LLM, görmediği frame hakkında JSON karar üretmeye zorlanıyor.
- Post-render kalite raporu yanlış PASS veya FAIL üretebilir.

Kaynaklar:

- `intelligence/ml-service/app/qa/character_verifier.py:23-69`
- `intelligence/ml-service/app/qa/character_verifier.py:76-149`
- `intelligence/ml-service/app/llm/openai_provider.py:18-24`
- `intelligence/ml-service/app/llm/claude_provider.py:18-23`
- `intelligence/ml-service/app/llm/gemini_provider.py:18-23`
- `intelligence/ml-service/app/llm/ollama_provider.py:16-21`
- `intelligence/ml-service/app/rules/rule_engine.py:1352-1420`

## P0 - SERVICE_ERROR veritabanına yazılamıyor

Python quality engine `SERVICE_ERROR` durumunu resmi bir overall status olarak üretiyor. Java enum'u da bunu kabul ediyor. Fakat `quality_validations.status` check constraint'i yalnızca şu üç değere izin veriyor:

- `RENDER_READY`,
- `NEEDS_REVISION`,
- `BLOCKED`.

Sonraki migration bu constraint'i güncellemiyor.

Etkisi:

- Semantic provider eksik olduğunda veya evaluator fail-closed çalıştığında Python 200 response içinde `SERVICE_ERROR` döndürebilir.
- Spring bu sonucu saklamaya çalışınca PostgreSQL insert/update constraint hatası verir.
- Kullanıcı asıl semantic servis problemini değil, persistence hatasını görür; validation kaydı da oluşmaz.

Kaynaklar:

- `intelligence/ml-service/app/quality/contracts.py:56-62`
- `intelligence/ml-service/app/rules/rule_engine.py:217-225`
- `intelligence/backend/src/main/resources/db/migration/V6__quality_validations.sql:17-23`
- `intelligence/backend/src/main/resources/db/migration/V30__add_immutable_validation_evidence.sql:1-33`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/ValidationDecisionStatus.java:10-15`

## P1 - Parser bazı kritik kalite sinyallerini ölçmek yerine olumlu varsayıyor

Parser şu değerleri doğrudan olumlu default ile üretiyor:

- `hook.startsAt = 0.0`,
- `hook.visualStrength = 4`,
- `hook.soundOffClear = true`,
- `coreMechanic.consistency = consistent`,
- `coreMechanic.mechanicCount = 1`,
- beat consequence = description'ın ilk 150 karakteri,
- visual state = action metninin normalize edilmiş hâli.

Timeline bulunamazsa fallback parser gerçek beat üretmiyor; boş liste döndürüyor. Secondary character çıkarımı da her zaman `None`.

Etkisi:

- HOOK_002, HOOK_003 ve CONSISTENCY_001 gerçek kanıttan çok parser varsayımını ölçebilir.
- Aynı görsel state farklı cümlelerle yazıldığında `BEAT_004` bunu farklı state sanabilir.
- Çok karakterli prompt'lar IR içinde doğru temsil edilmez.
- Prompt `[ATTEMPT: VERB]` marker'ı kullanmıyorsa parser hiçbir attempt'i attempt olarak tanımaz; güncel attempt kuralları format bağımlı biçimde BLOCKED sonucu üretir.

Kaynaklar:

- `intelligence/ml-service/app/parser/prompt_parser.py:230-257`
- `intelligence/ml-service/app/parser/prompt_parser.py:325-352`
- `intelligence/ml-service/app/parser/prompt_parser.py:399-423`
- `intelligence/ml-service/app/parser/prompt_parser.py:425-506`
- `intelligence/ml-service/app/parser/prompt_parser.py:575-594`

## P1 - Semantic provider çalışma zamanı hataları tam olarak fail-closed normalize edilmiyor

Semantic check fonksiyonları provider oluşturulurken meydana gelen `ValueError`ı `SemanticCheckServiceError`a çeviriyor. Fakat gerçek `llm.complete()` çağrısındaki timeout, HTTP, network veya SDK hataları çevrilmiyor. Evaluator'lar yalnızca `SemanticCheckServiceError` yakalıyor.

Etkisi:

- Credential eksikliği kontrollü `SERVICE_ERROR` üretirken, ağ/SDK arızası tüm `/validate` isteğini 500 ile düşürebilir.
- Aynı operasyonel problem farklı hata yolları üretir.

Kaynaklar:

- `intelligence/ml-service/app/llm/semantic_checks.py:66-73`
- `intelligence/ml-service/app/llm/semantic_checks.py:111-128`
- `intelligence/ml-service/app/llm/semantic_checks.py:271-304`
- `intelligence/ml-service/app/rules/rule_engine.py:1255-1266`

## P1 - API, SERVICE_ERROR ve UNKNOWN ayrıntılarını response'tan kaybediyor

Canonical report içinde `service_errors`, `unknown_rules` ve `not_applicable_rules` ayrı tutuluyor. Ancak HTTP response modeli bunlar için alan içermiyor. `failed_rules` yalnızca gerçek `FAIL` outcome'larını içeriyor.

Etkisi:

- Response `status = SERVICE_ERROR` olabilir ama `failedRules` boş görünebilir.
- `CONSISTENCY_002` pre-render aşamada `UNKNOWN` üretir; kullanıcı bunun çalışmadığını/ertelendiğini göremez.
- UI problemi açıklamak yerine yalnızca genel status gösterir.

Kaynaklar:

- `intelligence/ml-service/app/quality/contracts.py:175-231`
- `intelligence/ml-service/app/api/quality.py:130-142`
- `intelligence/ml-service/app/api/quality.py:479-558`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityReportDto.java:21-32`

## P1 - Auto-fix “sonraki fix'i dene” demesine rağmen aynı fix'i tekrar seçiyor

Top priority fix uygulanamazsa kod “Try next fix” yorumuna rağmen outer iteration'a `continue` ediyor. Current report değişmediği için sonraki turda yine aynı `priority_fixes[0]` seçiliyor.

Bu özellikle önemlidir çünkü:

- `CONCEPT_006` bilinçli olarak `REPLACE_CONCEPT` ve patch fixer tarafından uygulanamaz.
- Bu blocker listenin başındaysa döngü ikinci düzeltmeye hiç geçmeden aynı başarısız fix'i iteration limiti kadar tekrar eder.
- 34 kuraldan yalnızca 11'i fixer registry'sinde; bunlardan `REPETITION_003` ve `PROGRESSION_005` de içeride açıkça tam uygulanmamış durumda.

Kaynaklar:

- `intelligence/ml-service/app/autofix/iteration_loop.py:154-175`
- `intelligence/ml-service/app/autofix/prompt_fixer.py:43-56`
- `intelligence/ml-service/app/autofix/prompt_fixer.py:74-109`
- `intelligence/ml-service/app/autofix/prompt_fixer.py:379-396`
- `intelligence/ml-service/app/autofix/prompt_fixer.py:460-475`

## P1 - Güncel rule'lar için öneri metinleri eksik

Quality scorer'ın recommendation map'i yalnızca ilk 10 rule'u kapsıyor. Ruleset `1.1-1.3` ile gelen 24 yeni rule başarısız olduğunda priority fix oluşuyor ama `recommendation` çoğu durumda boş string oluyor.

Etkisi:

- UI'da “Fix:” başlığı var fakat altında uygulanabilir öneri olmayabilir.
- Auto-fix desteklenmeyen yeni rule'larda kullanıcıya manuel çözüm de sunulmuyor.

Kaynaklar:

- `intelligence/ml-service/app/scoring/quality_scorer.py:180-225`
- `intelligence/ml-service/app/scoring/quality_scorer.py:249-272`
- `intelligence/frontend/src/app/pages/quality-validator/quality-validator.component.html:114-121`

## P1 - Quality UI kodu var ama aktif uygulamada yok

`QualityValidatorComponent` eksiksiz sayılabilecek bir eski ekran olarak mevcut. Ancak `app.routes.ts` içinde route'u yok ve başka bir component tarafından import edilmiyor.

Etkisi:

- Kullanıcı aktif Angular uygulamasından prompt quality motoruna erişemez.
- Backend/Python özelliği görünür ürün akışına dönüşmemiştir.
- Component'in çağırdığı endpoint ad hoc endpoint'tir; render-authorizing endpoint değildir.

Kaynaklar:

- `intelligence/frontend/src/app/pages/quality-validator/quality-validator.component.ts:76-166`
- `intelligence/frontend/src/app/app.routes.ts:1-36`
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/quality/QualityValidationController.java:11-45`

## P1 - Yeni quality family'leri scorer görünümünde tam entegre değil

Rule engine `character_performance` ve `generation_executability` family'lerini sırasıyla `0.05` ve `0.09` ile overall score'a dahil ediyor. `QualityScorer.FAMILY_WEIGHTS` ve radar listesi ise eski 11 family'de kalmış durumda.

Etkisi:

- Overall score ile enhanced breakdown'daki weighted contribution aynı ağırlık modelini anlatmıyor.
- `generation_executability` breakdown'da default `0.05` alırken gerçek overall hesapta `0.09` kullanılıyor.
- Radar/özet görünümleri güncel rule modelini eksik temsil ediyor.

Kaynaklar:

- `intelligence/ml-service/app/rules/rule_engine.py:289-322`
- `intelligence/ml-service/app/scoring/quality_scorer.py:57-70`
- `intelligence/ml-service/app/scoring/quality_scorer.py:371-395`

## P2 - Hesaplanan zengin raporun önemli kısmı API'den çıkmıyor

`EnhancedQualityReport` şu alanları hesaplıyor:

- parser confidence/assumptions/warnings,
- score breakdowns,
- family radar,
- top strengths,
- top weaknesses.

`QualityReportResponse` bunları taşımıyor. Özellikle parser confidence'ın kaybolması, heuristic parser'ın belirsiz sonuçlarının kesin sonuç gibi görünmesine yol açıyor.

Kaynaklar:

- `intelligence/ml-service/app/quality/contracts.py:304-328`
- `intelligence/ml-service/app/scoring/quality_scorer.py:81-117`
- `intelligence/ml-service/app/api/quality.py:130-142`

## P2 - Feedback/learning modülleri ana akışa bağlı değil

Feedback collector, performance analyzer ve rule learner sınıfları mevcut. Fakat API, scheduler, persistence veya validation workflow tarafından kullanılmıyorlar. `FeedbackCollector` in-memory çalışıyor; modül içindeki bazı rule-effectiveness analizleri de placeholder seviyesinde.

Etkisi:

- “Gerçek performanstan öğrenen quality rules” özelliği kod tabanında taslak olarak var, çalışan döngü değil.
- Dokümanlardaki feedback loop anlatımı mevcut production davranışını yansıtmıyor.

Kaynaklar:

- `intelligence/ml-service/app/feedback/feedback_collector.py`
- `intelligence/ml-service/app/feedback/performance_analyzer.py:226-242`
- `intelligence/ml-service/app/feedback/rule_learner.py`

## P2 - Dokümantasyon güncel sistemle ciddi biçimde drift etmiş

`PROJECT_COMPLETE.md`, sistemi v1.0 / 10 rule / 11 family / production-ready olarak tanımlıyor. Gerçek kod Ruleset `1.3`, 34 rule ve 13 family içeriyor; aynı zamanda render authorization, vision input ve UI bağlantısı eksik.

`README.md` de birçok fazı eksiksiz tamamlanmış gösterirken aktif route tablosunda bazı ekranlar placeholder, quality ekranı ise tamamen route dışı.

Etkisi:

- Yeni geliştirme yapan kişi yanlış mimari ve yanlış tamamlanma seviyesiyle işe başlar.
- “Production ready” ifadesi gerçek uçtan uca davranışla uyuşmaz.

Kaynaklar:

- `intelligence/PROJECT_COMPLETE.md:1-20`
- `intelligence/PROJECT_COMPLETE.md:24-43`
- `intelligence/PROJECT_COMPLETE.md:413-425`
- `intelligence/README.md:5-66`

---

## 5. Bu Parçanın Olgunluk Değerlendirmesi

| Katman | Durum | Not |
|---|---|---|
| Rule catalog/versioning | Güçlü | 1.0-1.3 sürümlü, 34 rule/evaluator eşleşmiş |
| Deterministic rule engine | Büyük ölçüde mevcut | Parser'ın ürettiği sinyal kalitesine fazla bağımlı |
| Semantic rule engine | Mevcut ama operasyonel eksikliğe açık | Provider provenance ve hata normalizasyonu eksik |
| Scoring/reporting | Çalışır çekirdek | API contract ve family diagnostics güncel değil |
| Auto-fix | Prototip | Kapsam dar, iteration seçim hatası var |
| Character continuity QA | İşlevsel değil | Görüntü provider'a ulaşmıyor |
| Spring persistence | Mevcut | SERVICE_ERROR constraint uyumsuzluğu var |
| Render authorization | Güvenli ama tamamlanmamış | Fail-closed; hiçbir validation tam kanıt üretemiyor |
| Angular quality UI | Orphaned | Kod var, aktif route ve ürün akışı yok |
| Feedback learning | Taslak | Ana sisteme bağlı değil |

**Genel karar:** Bu bölüm “production-ready uçtan uca quality gate” değildir. Güçlü bir kural motoru ve doğru fail-closed temel vardır; fakat şu an en doğru tanım **gelişmiş quality-analysis çekirdeği + tamamlanmamış production authorization entegrasyonu** olur.

---

## 6. Önerilen Tamamlama Sırası

1. Render-authorizing validation için semantic/producibility provenance ve independent revalidation zincirini tamamla.
2. `SERVICE_ERROR` DB constraint ve API observability modelini düzelt.
3. Vision provider'larda gerçek image payload desteğini ve reference-image karşılaştırmasını ekle.
4. Parser'ı varsayılan PASS üreten alanlardan çıkar; ölçülemeyen alanları `unknown/evidence_missing` olarak taşı.
5. Auto-fix'in aynı uygulanamaz fix'te dönmesini engelle ve 1.1-1.3 recommendation kapsamını tamamla.
6. Quality ekranını güncel uygulama route'una, render-authorizing endpoint ayrımını açıkça koruyarak bağla.
7. Scorer/family şemalarını 13 family ile tek kaynağa indir.
8. Feedback modüllerini gerçek persistence ve performance observation akışına bağla veya ürün kapsamı dışında olduğunu açıkça işaretle.

---

## 7. Sonraki İnceleme Parçası

Bir sonraki mantıklı parça: **Video Library ve Video Detail veri akışı**.

Bu parçada şu zincir incelenmeli:

`mounted folders -> media discovery -> video grouping/versioning -> detail API -> gerçek video playback -> teknik metadata -> performance observations -> Meta/TikTok/YouTube metrikleri`.

Bu seçim, kalite motorundan sonra kullanıcı tarafından aktif kullanılan ana ürün yüzeyinin gerçekten hangi veriyi gösterdiğini ve hangi alanların hâlâ placeholder olduğunu ortaya çıkarır.
