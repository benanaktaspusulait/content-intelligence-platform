# Post-family operasyonel akış — doğrulama ve hazırlık durumu

Çalışma başlangıçta `ef5d231abd6cc85ad0c394b99517cfa2570b3e0f` üzerinden yapıldı. Kullanıcının isteğiyle 2026-10-08 tarihinde tüm kod, test, rapor ve yerel medya kanıtları ana proje dizinindeki `master` çalışma alanına çakışmasız aktarıldı. Ayrı çalışma kopyası kaldırıldı. Aktarım sırasında agent commit oluşturmadı; depodaki başka bir süreç aktarılan dosyaları `b42e7bb` commitine aldı. Önceki Family 10 tamamlamasından PDF düzeni, freeze-validation.json ve FAMILY10_CALIBRATION.md aynen taşındı. Family 1–10 parser/rules/truth/policy/baseline dosyaları değiştirilmedi. Meta/publisher dosyaları ve çalışan 4200/8080/8000 servisleri değiştirilmedi. Commit, ücretli çağrı, yeni medya üretimi ve yayın yapılmadı.

Yerel ekran: http://127.0.0.1:4215/quality/detail?contentId=3&promptVersionId=3 . Backend 8085, ML 8015, ayrı yerel veritabanı `pompom_workflow_local`. Ekran tarihsel profil ile açılır; operatör açıkça **Operasyonel yaratıcı iş akışı v1** seçer.

## Bounded capability audit

| Yetenek | Mevcut yürütme yolu | Eklenen en küçük entegrasyon | Hazırlık / kanıt |
| --- | --- | --- | --- |
| Klasör/prompt/sürüm | ContentWorkspaceController, ContentPromptQueryService, /quality/detail | Aynı detay ekranında opt-in profil; kayıtlı immutable prompt sürümü kullanılır | Gerçek A/B prompt’ları, yerel API + tarayıcı |
| Kaynak kanıtı / IR | Frozen Family 10 general_producibility_evidence | app/workflow/review.py: alıntı, karakter aralığı, kaynak sürümü/hash, yöntem, belirsizlik | Dokuz gerçek kaynak; 7 RISKY / 2 UNKNOWN. Gold etiketleri runtime girdisi değildir |
| Karakter/nesne referansı | MediaContentService ve mevcut karakter kataloğu | Operatör ilişkilendirmesi, gerçek yerel dosya SHA-256, karakter kapsamı, ilk kare ayrı tür | Yerel doğrulama uygulanmış; örneklerde yetkili referans ilişkileri hâlâ eksik |
| İçerik/açılış/süre | Mevcut prompt editörü | ABSURD_PHYSICS / CURIOSITY_ADVENTURE / EDUCATIONAL / MIXED / UNKNOWN; açılış ayrı; süre konseptten | A 15 s, B 25 s. Evrensel komedi/üç deneme/fake-resolution/resolved-ending şartı eklenmedi |
| Model/mod sözleşmesi | Bağlı OpenArt CLI model list/form | Versioned provider-capabilities.json; Mini/2.0/2.5 ayrı tercihler | Gerçek metadata okundu: CLI 0.1.1, 2026-10-08. Üretim çağrısı denenmedi |
| Execution critic | LLMProvider.complete | Yerel kaynak sezgileri; provider-neutral port; DeepSeek metin adaptörü ve bounded OpenAI portu | Stub timeout/bozuk/temelsiz çıktı testleri; varsayılan ücretli endpoint 403. Claude/Gemini için bounded runtime adaptörü yapılandırılmadığında UNKNOWN |
| İlk kare / görsel kapılar | Mevcut FIRST_FRAME ve ValidationEvidenceService | Plan/gerçek kare/gerçek açılış/kapak ayrı; kare yolu/hash kanonik görsel kanıtla eşleşir | İlk kare edinimi ek post-family gate’inden muaf; mevcut gate’ler korunur. Örneklerde görsel PASS yok |
| Final render kabulü | Frozen ValidationEvidencePolicy ve mevcut snapshot/expiry/revalidation/bütçe kontrolleri | PostFamilyAdmissionClient + WorkflowService.admission; yeniden hash/sürüm/model/süre/ayar/kare/segment kontrolü | Yerel olumlu/olumsuz teknik testler. Son video için exact AUTHORIZED ve tüm mevcut kontroller birlikte zorunlu |
| Minimal repair | Mevcut prompt versions | En çok üç yerel yama; korunmuş niyet; tam kaynak alıntısı; Unicode kod noktaları; bir repair + bir verification; DB’de tek başarılı pass | Gerçek prompt üzerinde repair → yeni sürüm kaydı → final review; tekrar 409, paid critic 403 |
| Actual render QA | VideoService, MlVideoClient, mevcut deterministik v5 analiz | Gerçek dosya hash/süre + zamana bağlı plan karşılaştırması; insan incelemesi ayrıca açık onaylanır | Gerçek Luca–Zipo klibi analiz edildi. Semantik hareket/temas/loop sonucu UNKNOWN; seyrek karelerden PASS üretilmedi |
| Yayın/edit ilişkisi | Mevcut video/variant ve import kayıtları | Append-only workflow ledger; lossless ID; tam ID ile tüm ilişki geçmişi; çelişkide AMBIGUOUS | Büyük ID ve ambiguity fixture testleri. Gerçek yayın ID’si örnekte doğrulanmış değil |
| Ölçüm/kohort | PerformanceImportService preview/match/commit | Audience / distribution / outcome ayrı; provenance, pencere, denominator, gerçek süre; configurable near-organic Paid Reach eşiği | Gerçek CSV preview: 1 satır / 0 match / 1 unresolved. Lifetime’dan fixed-horizon veya intentional replay türetilmedi |
| Ders / deney | Mevcut /experiments ve operational ekranlar | Hipotez, sample, model/version/settings/profile/duration/evidence/counterexample; insan onay/red kaydı | Yerel kayıt adapter’i var; otomatik kural değişikliği yok. Gerçek performans sonucu olmadan ders doğrulanmış sayılmaz |

## Model sözleşmesinin somut sınırları

Bağlı image2video formu Mini ve 2.0 için 4–15 s; 2.5 için 4–30 s bildiriyor. Bu bilgi model/moda ve 2026-10-08 metadata snapshot’ına aittir; diğer modlar için destek uydurulmadı. Mini maliyet/çok deneme tercihi, 2.0 açıklanmış kalite gerekçesi, 2.5 uzun süre tercihi ayrı kalır. Açık model seçimi otomatik değiştirilmez.

**2.5 image2video formunda aspectRatio alanı yok.** B’de 25 s için 2.5 önerisi korunur, fakat mevcut 9:16 ayarı bütün sözleşme için UNSUPPORTED olur; desteklenen final render süresi bu yüzden UNKNOWN kalır. İlk kare zorunlu girdisi de eksiktir. Bu durum 15 saniyeye veya başka modele sessizce çevrilmez. Formun bildirmediği oran davranışı ve mevcut worker adapter’inin gerçek sağlayıcı davranışı canlı üretim yapılmadan doğrulanmış sayılmadı. Mevcut kontrollü adapter 480p tek image2video işi yürütür; çok segment ve başka çözünürlük, eşdeğer doğrulanmış adapter olmadan kabul edilmez.

DeepSeek adaptörü bu uygulamada metin portudur; görselleri/klibi incelemiş sayılmaz. Sağlayıcı/model, runtime budget/config ve anahtar gerektirir. `WORKFLOW_PAID_CRITIC_ENABLED` varsayılan false kalır. Timeout/bozuk JSON/temelsiz alıntı/yanlış görsel iddia UNKNOWN olur; genel sezgi sert model kanıtı yerine kullanılamaz. Hiçbir ikinci görüş kanonik render yetkisini tek başına değiştirmez.

## Gerçek örnekler ve belirsizlik

- **A — Luca Sticky Ball:** gerçek üretim prompt’u, 15 s; ABSURD_PHYSICS seçimi, kaynaklı sticky/deformation/contact bulguları. `data/workflow/reports/example-A.json`.
- **B — Luca and Zipo:** gerçek iki karakterli merak/macera prompt’u, 22–25 s kaynak planı. Komedi, üç girişim ve kapalı son zorlaması yok. Tarayıcı AUTO routing CURIOSITY_ADVENTURE ve 2.5 tercihini gösterdi. `example-B.json` ve `operator-curiosity-review.png`.
- **C — Actual clip:** mevcut `08_luca_and_zipo_hd.mp4` yalnızca yerel veri köküne kopyalandı; üretim yapılmadı. SHA-256 `0c38bda790441af44f7f8d901f8ca9bf79cfafcc320a7c01a53baccc3f774f68`. Gerçek deterministik analiz, plan aralıkları ve UNKNOWN semantik sonuç `example-C-actual-clip.json` içinde. Hareket/olay başarısı için gerçek klibin insan/VLM inceleme kanıtı hâlâ gerekli.
- **D — Actual CSV:** `lab/performance_imports/known_observations.csv` gerçek import API’sinde preview edildi; batch `74e9652a-3645-4a88-ac6e-f7f9a40a757d`, hash `7760e207673915d8e8670e05cd09d55349aa016264950366a71a5eac8f7b3179`. Yaklaşık gözlemde doğrulanmış publication ID ve horizon yok. UNMATCHED kaldı; commit veya tahmini video eşleştirmesi yapılmadı. Büyük ID / metrik fixture’ları açıkça sentetiktir. `example-D-import-readiness.json`.
- **Repair boundary:** A’nın yaratıcı çekirdeği korunarak yalnızca watermark yönergesi eşdeğer yerel metinle değiştirildi. Yeni immutable prompt version kaydedildi ve tekrar incelendi; AUTHORIZED üretilmedi. `repair-integration-example.json`.

Üretim kanıtı raporu `family10-source-enrichment.json`: önce tüm dokuz runtime UNKNOWN, sonra kaynak adapter’inde yedi RISKY ve Box Cat / Spot Cat UNKNOWN. Bu runtime sonuçlar manuel Gold etiketleriyle doldurulmadı. Aktör/nesne/held-object kapsamı ve taranmamış bağımlılıklar eksikse omission yokluk sayılmaz; source-bound plan JSON’u da gerçek alıntı ve varlıkları gerektirir. Açık “No lip-sync” zorunlu lip-sync riskine çevrilmez.

Operatör sırası: profil seç → niyeti/referansları/model/süreyi bağla → review → gerekiyorsa tek kaynak yaması → son prompt’u mevcut editöre aktar ve sürüm kaydet → yeni sürümü yeniden review → manuel paket veya mevcut kontrollü kuyruk → gerçek klip QA → doğrulanmış yayın/edit ilişkisi → kaynaklı ölçüm → insan incelemeli ders/deney. Prompt, referans, kaynak planı, süre, model, ayar, segment, niyet veya capability snapshot’ı değişirse binding eskir. İlk kare/QA/performance ayrı aşamalar; izlenme sonucu yaratıcı notu otomatik değiştirmez.

## Ölçülen doğrulama

| Kontrol | Başlangıç | Güncel | Sonuç |
| --- | --- | --- | --- |
| Tam ML pytest | 641 pass | 673 pass | Yeni 32 workflow testi dahil |
| Backend quality/workflow/import odak testleri | — | 64 pass / 0 fail / 0 error | Yeni transport ve admission predicate testleri dahil |
| Render authorization/queue/workflow odak testleri | — | 37 pass | Frozen policy + post-family guard |
| Tam render paketi + son odak testi | 391 test; 1 failure + 11 error | 394 benzersiz test; aynı 1 failure + 11 error | Yeni failing case yok; karşılaştırma raporu saklandı |
| Kalite UI odak testleri | — | 31 pass | Family 9/10 temsil + workflow + Unicode patch |
| Tam frontend paketi | 44 pass / 9 fail | 48 pass / aynı 9 fail | Yeni failing case yok |
| Production frontend build | — | PASS | Mevcut bundle/SCSS budget warning’leri var |
| Ruff / mypy / owned Java format / diff check | — | PASS | Yeni workflow kaynaklarında; baseline dosyaları topluca yeniden biçimlendirilmedi |
| Frozen Golden / aynı pre-batch config | 9 asset / 323 assertion | 9 / 323 | 0 yeni semantic/policy/representation regression; gate PASS |

Tam render paketindeki eski hatalar JSONB string persistence, legacy asset_version migration ve unavailable-plan temporal expectation alanlarında. Bunlar başlangıç commit’inin ayrı checkout’unda aynı isimlerle yeniden görüldü; kapsam dışı render/migration kodu değiştirilmedi. Frontend’in eski dokuz hatası service/video-detail testlerinde; başlangıçla aynı. Golden’ın önceden bilinen beş semantic failure ve review-required kayıtları gizlenmedi; release gate yeni regresyon ölçer.

Ölçüm özetleri `validation-summary.json`, `render-regression-comparison.json`, `frontend-regression-comparison.json` ve `frozen-regression/` altında. Bu sonuçlar live-provider-ready iddiası değildir. Ücretli critic/generation ve paid VLM çalıştırılmadı; gerçek semantik klip doğrulaması, yetkili karakter/kare ilişkileri, final canonical evidence ve gerçek publication/horizon eşleşmesi açık kalan kanıtlardır.

## Tekrarlanabilir yerel kullanım

Kaynaklar `ml-service/app/workflow/`, backend `workflow/`, creative-render `workflow/`, kalite detayındaki `post-family-workflow.component.ts`, mevcut render dashboard ve `V46/V47` additive migration’larındadır. Örnekler için, ML dizininde:

```sh
PYTHONPATH=. .venv/bin/python scripts/run_post_family_examples.py \
  --source-root /Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION \
  --backend-url http://127.0.0.1:8085 \
  --observation-csv /Users/benanaktas/project/video/content-intelligence-platform/lab/performance_imports/known_observations.csv
```

Bu script yalnızca yerel örnek kayıtları/medya kopyaları ve mevcut analiz API’sini kullanır. Paid critic, render provider veya publisher çağırmaz. Ayrı DB’de mevcut metadata/gate’ler korunur; `V46/V47` ortak ortama taşınırken diğer eşzamanlı çalışma migration numaraları normal entegrasyonda uzlaştırılmalıdır.
