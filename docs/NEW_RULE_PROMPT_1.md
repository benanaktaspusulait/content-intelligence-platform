Evet. Hatta bunu tek “soft guideline” değil, **render öncesi BLOCKER seviyesinde rule** yapmalıyız. Kumbara ve Dönen Masa tam olarak bu boşluktan geçti.

Ben bunu tek başlık altında ama üç kontrolle tanımlardım:

### `INSTANT_VISUAL_ABSURDITY_GATE` — BLOCKER

**Amaç:** Video başlamadan, yalnızca first-frame screenshot’a bakıldığında fiziksel anormallik anlaşılabiliyor mu?

```text
RULE: INSTANT_VISUAL_ABSURDITY_GATE
SEVERITY: BLOCKER

A concept MUST NOT proceed to prompt generation/render unless the
first frame communicates a physically impossible or clearly wrong
situation without requiring temporal history, counting, comparison,
audio, text, or prior knowledge of the concept.

PASS only if ALL conditions are true:

1. STATIC_WRONGNESS
   The first frame looks physically wrong as a still image.

2. NO_HISTORY_REQUIRED
   The viewer does not need to know what happened before this frame
   to understand that something is wrong.

3. NO_MICRO_COMPARISON
   The viewer does not need to:
   - count objects,
   - compare before/after states,
   - track a marker,
   - inspect small positional changes,
   - compare object position against background geometry.

4. LARGE_VISUAL_SIGNAL
   The anomaly occupies a meaningful part of the frame and remains
   readable on a small phone screen.

5. CHARACTER_ALREADY_ENGAGED
   The main character is already physically reacting to or fighting
   the impossible event in frame zero, not merely observing it.

IF ANY CONDITION FAILS:
BLOCK concept before render.
Do not attempt to repair a fundamentally weak hook with a longer prompt.
```

Buna bir de çok önemli bir **automatic fail** bölümü koyarım:

```text
AUTO-FAIL PATTERNS:

- "You have to see the previous movement to understand it."
- "You need to count 1 vs 3 objects."
- "You need to notice that this marker did not rotate."
- "You need to compare table legs with the rug."
- "It looks normal until animation starts."
- "The anomaly is only audible."
- "The character is simply surprised / looking."
```

Bu rule ile bizim örnekler çok net ayrılıyor:

| Concept | Gate |
|---|---|
| Crocodile, ağzından toplar taşmış | **PASS** |
| Sticky Ball uzamış halde | **PASS** |
| Impossible Faucet, su yanlış yönde | **PASS** |
| Dev Balloon | **PASS** |
| Kumbara 1→3 coin | **FAIL** — counting/history |
| Table-Turning Ball | **FAIL** — marker/background comparison |
| Push-Back Box | **RISK/FAIL** — önceki push bilinmeden return anlaşılmıyor |

Ama bence bunun yanına ikinci bir BLOCKER daha koymalıyız:

```text
RULE: ENGINE_SILHOUETTE_DUPLICATE
SEVERITY: BLOCKER / CRITICAL

Reject or heavily demote a concept if its visible progression and final
screen silhouette are substantially similar to an existing winner,
even when the underlying mathematical rule is different.
```

Örneğin:

> Crocodile = source ejects many objects → screen fills  
> Hiccup Box = source ejects many objects → screen fills  
> Piggy Bank = source ejects many objects → screen fills

Matematik farklı olsa bile **izleyici açısından aynı visual engine family**.

En önemli değişiklik şu olur:

> Artık `good rule + good escalation = render` demiyoruz.

Yeni sıra:

> **FIRST-FRAME GATE → SILHOUETTE DUPLICATE GATE → RULE QUALITY → ESCALATION → AI PRODUCIBILITY → RENDER**

Ve first-frame gate **ilk sırada**. Orada fail olan konseptin geri kalanına bakmaya bile gerek yok.

Bence bu iki rule'u Prompt Validation Engine'e doğrudan **BLOCKER** olarak eklemeliyiz.