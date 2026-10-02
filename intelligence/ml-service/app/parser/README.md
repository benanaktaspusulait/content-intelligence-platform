# Prompt Parser

Converts freeform text prompts into structured Video Plan IR.

## Usage

```python
from app.parser.prompt_parser import parse_prompt

with open("prompt.txt", "r") as f:
    prompt_text = f.read()

result = parse_prompt(prompt_text)

video_plan_ir = result["videoPlanIR"]
parser_metadata = result["parserMetadata"]

print(f"Confidence: {parser_metadata['confidence']}")
print(f"Warnings: {len(parser_metadata['warnings'])}")
print(f"Beats extracted: {len(video_plan_ir['beats'])}")
```

## Parser Strategy

### 1. Metadata Extraction
- Title (from `TITLE:` or pattern matching)
- Duration (from `15-second` or default 15.0)
- Format (from `9:16` or `vertical`)
- Series type (from keywords: opposites, what's wrong, etc.)

### 2. Character & Setting Extraction
- Primary character (from `MAIN CHARACTER:` or name detection)
- Secondary characters
- Location (from `SETTING:` or `LOCATION:`)
- Main props (from `MAIN OBJECTS:` section)

### 3. Learning Objective (if applicable)
- Core concepts (from `CORE ENGLISH:` section)
- Pedagogical goal
- Sound-off readability flag

### 4. Timeline Beat Parsing
**Most complex step.** Looks for timestamp patterns like:
```
0.0-1.0 SEC — HOOK
Description here

1.0-3.0 SEC — ACTION
More description
```

For each beat, extracts:
- Start/end times
- Action description
- Visual state (inferred)
- Consequence
- Intensity (keyword-based estimation)
- Motion amount
- Dialogue (if quoted)

### 5. Beat Enrichment
After initial parsing, enriches beats with:
- `isNewConsequence`: Compare to all previous beats
- `similarToBeats`: List beat IDs with >70% similarity
- `consequenceType`: new / repeat / continuation / escalation
- `cycleGroup`: Detect repeated action cycles (future enhancement)

### 6. Hook & Payoff Identification
- Hook: First beat + mid-action check
- Final payoff: Last beat + repeat-of-opening check

### 7. AI Producibility Assessment
Scans for risk keywords:
- hand-object → precision risk
- morph/transform → morphing risk
- liquid/water → physics risk

Complexity:
- 0-1 risk factors: low/medium
- 2 risk factors: high
- 3+ risk factors: very_high

## Parser Metadata

```json
{
  "confidence": 0.85,
  "ambiguities": [
    "Core mechanic not explicitly stated"
  ],
  "assumptions": [
    "Duration not explicit, using default: 15.0s"
  ],
  "warnings": [
    "Primary character not clearly identified"
  ]
}
```

**Confidence calculation:**
- Starts at 1.0
- -0.10 per warning
- -0.05 per ambiguity
- -0.03 per assumption

## Limitations

### Current Version (v1.0)

1. **No LLM integration yet**
   - Uses regex + keyword matching
   - Cannot handle complex natural language variations
   - May miss implicit information

2. **Simple similarity detection**
   - Word overlap only (Jaccard)
   - Should use embeddings for better accuracy

3. **Intensity estimation is heuristic**
   - Keyword-based (sudden, quick → high; gentle, slow → low)
   - No context understanding

4. **Cycle detection not implemented**
   - `cycleGroup` field exists but not populated
   - Requires sequence pattern matching

5. **Visual state normalization is simplistic**
   - Just uses action text
   - Doesn't understand semantic equivalence
   - "slides on floor" ≠ "glides on surface" (but should be same state)

### Future Enhancements

**Phase 2: LLM-Assisted Parsing**
- Use GPT-4/Claude to extract structured data
- Better action/consequence separation
- Semantic similarity for visual states
- Automatic cycle detection

**Phase 3: Learning from Corrections**
- Store human-corrected IRs
- Fine-tune extraction patterns
- Build domain-specific entity recognizer

**Phase 4: Multi-modal**
- Parse video previews to validate IR
- Use frame analysis to verify beat timings
- Detect actual visual state transitions

## Testing

```bash
cd ml-service
python -m pytest tests/parser/
```

See `tests/parser/test_prompt_parser.py` for examples.

## Integration

Parser is called by FastAPI endpoint:

```
POST /api/v1/parse-prompt
Content-Type: application/json

{
  "promptText": "..."
}

Response:
{
  "videoPlanIR": {...},
  "parserMetadata": {...}
}
```

Then flows to rule engine for validation.
