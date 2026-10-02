# Local AI Setup

Local semantic vision is optional. Start any OpenAI-compatible vision endpoint, then set:

```bash
export VISION_PROVIDER=local_vlm
export VISION_BASE_URL=http://127.0.0.1:11434/v1
export VISION_MODEL=your-local-vision-model
./pompom analyse ../Absurd_Moments --force --limit 1
```

Ollama is installed on this machine, but no model is hardcoded or downloaded automatically.
The endpoint receives timestamped local evidence frames only when explicitly enabled. If it
is offline or returns invalid JSON, analysis continues with local heuristics and records the
provider error. External uploads are off by default.

