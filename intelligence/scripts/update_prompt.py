#!/usr/bin/env python3
"""Update the saved production prompt with corrected text."""
import json
import subprocess

# The corrected prompt text
corrected_prompt = """TITLE / FORMAT
Mimi Sticky / 15s Video

VISUAL STYLE
Bright and colorful animation with a playful tone.

CHARACTER / CONTINUITY
Mimi, an anthropomorphic bunny, interacts with sticky notes in a humorous and chaotic manner.

TIMED SHOT PLAN
0-2s: Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger [close-up on Mimi's hand] Mimi is in front of a toy cabinet, looking determined -> the note sticks to Mimi, not the cabinet
2-5s: Mimi tries to peel the stuck note away with her other hand; the note splits into two [medium shot of Mimi struggling] Mimi pulls at the note -> one note sticks to each hand
5-10s: Mimi continues to pull; each pull doubles the number of sticky notes [wide shot showing Mimi covered in notes] notes multiply from two to four to eight as she pulls, progressively covering her arms, legs and face -> Mimi is overwhelmed by notes
10-12s: Mimi sees herself in a mirror and screams [close-up on Mimi's shocked face] Mimi is startled by her reflection completely covered in notes -> Mimi is startled
12-15s: Mimi sneezes and the sticky notes fly off [medium shot of notes flying] notes scatter and stick to the cabinet -> Mimi breathes a sigh of relief but the cabinet remains messy

AUDIO
Playful background music with sound effects for sneezing and notes sticking.

NEGATIVE CONSTRAINTS
No dark themes or violence.

FINAL CUT
Mimi is relieved but the cabinet remains visibly messy.

CHARACTER IDENTITY LOCK
Mimi is the established anthropomorphic bunny character. Preserve that identity; do not render a human or invent unverified visual details. No approved visual reference is currently bound, so appearance details remain unverified.

PRODUCTION SETTINGS
Aspect ratio: 9:16. Target generator: SEEDANCE_2_0_MINI. Content profile: AUTO."""

# Read the current payload
result = subprocess.run(
    ["docker", "exec", "intelligence-postgres-1", "psql", "-U", "pompom", "-d", "pompom", "-t", "-A",
     "-c", "SELECT payload::text FROM post_family_workflow_events WHERE id='1bbde0d2-efc2-46b8-920c-9f55e910ef59';"],
    capture_output=True, text=True, cwd="/Users/benanaktas/project/video/content-intelligence-platform/intelligence"
)

payload = json.loads(result.stdout.strip())
print("=== ORIGINAL PROMPT (first 200 chars) ===")
print(payload['result']['prompt'][:200])
print()

# Store the original prompt for audit
original_prompt = payload['result']['prompt']

# Update the prompt
payload['result']['prompt'] = corrected_prompt

# Mark the productionPlan as stale since it was derived from the original prompt
# We set a flag to indicate the prompt text has been manually edited
if 'productionPlan' in payload['result']:
    payload['result']['productionPlan']['promptTextEdited'] = True
    payload['result']['productionPlan']['evidenceLimitations'] = (
        payload['result']['productionPlan'].get('evidenceLimitations', []) +
        ["Prompt text manually edited after generation; structured productionPlan is STALE and does not reflect the current prompt text. Re-run analysis after editing."]
    )

# Update the database
new_payload_json = json.dumps(payload)
# Use psql with a file to avoid escaping issues
import tempfile
import os

with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    f.write(new_payload_json)
    tmpfile = f.name

try:
    result = subprocess.run(
        ["docker", "exec", "-i", "intelligence-postgres-1", "psql", "-U", "pompom", "-d", "pompom", "-t", "-A",
         "-c", f"UPDATE post_family_workflow_events SET payload = (SELECT jsonb FROM jsonb_in((SELECT '{tmpfile}'::text::regclass::text)), updated_at = NOW() WHERE id='1bbde0d2-efc2-46b8-920c-9f55e910ef59';"],
        capture_output=True, text=True,
        cwd="/Users/benanaktas/project/video/content-intelligence-platform/intelligence"
    )
    print("UPDATE result:", result.stdout, result.stderr)
finally:
    os.unlink(tmpfile)

# Simpler approach: use Python's json and psql copy
print("\n=== Using simpler UPDATE approach ===")

# Encode the payload as a JSON string for SQL
payload_escaped = new_payload_json.replace("'", "''")

sql = f"UPDATE post_family_workflow_events SET payload = '{payload_escaped}'::jsonb, updated_at = NOW() WHERE id='1bbde0d2-efc2-46b8-920c-9f55e910ef59';"

result = subprocess.run(
    ["docker", "exec", "intelligence-postgres-1", "psql", "-U", "pompom", "-d", "pompom", "-c", sql],
    capture_output=True, text=True,
    cwd="/Users/benanaktas/project/video/content-intelligence-platform/intelligence"
)

print("SQL result:", result.stdout)
if result.stderr:
    print("SQL stderr:", result.stderr)

# Verify the update
result = subprocess.run(
    ["docker", "exec", "intelligence-postgres-1", "psql", "-U", "pompom", "-d", "pompom", "-t", "-A",
     "-c", "SELECT payload->'result'->'prompt' FROM post_family_workflow_events WHERE id='1bbde0d2-efc2-46b8-920c-9f55e910ef59';"],
    capture_output=True, text=True,
    cwd="/Users/benanaktas/project/video/content-intelligence-platform/intelligence"
)

updated_prompt = json.loads(result.stdout.strip())
print("\n=== UPDATED PROMPT (first 200 chars) ===")
print(updated_prompt[:200])
print("\n=== VERIFICATION ===")
print("Original had 'sticky note note':", "sticky note note" in original_prompt)
print("Updated has 'sticky note note':", "sticky note note" in corrected_prompt)
print("Updated has 'each pull doubles':", "each pull doubles" in corrected_prompt)
print("Updated has 'cabinet remains messy':", "cabinet remains messy" in corrected_prompt)
print("Updated has 'note sticks to Mimi, not the cabinet':", "note sticks to Mimi, not the cabinet" in corrected_prompt)
