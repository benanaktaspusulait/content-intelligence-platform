import argparse
import csv
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

import yaml

from app.workflow.review import review_prompt

parser = argparse.ArgumentParser(
    description="Run no-credit operational examples against an isolated local backend"
)
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--backend-url", default="http://127.0.0.1:8085")
parser.add_argument("--observation-csv", type=Path)
args = parser.parse_args()
data = Path(__file__).resolve().parents[2] / "data"
out = data / "workflow/reports"
out.mkdir(parents=True, exist_ok=True)
source = args.source_root / "09_SOCIAL_REELS/new14092026"


def post(path, value):
    body = json.dumps(value).encode()
    req = urllib.request.Request(
        args.backend_url + "/api/v1/intelligence/" + path,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def write(name, value):
    (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


caps = json.loads((data / "workflow/provider-capabilities.json").read_text())["models"]
enriched = []
manifest = yaml.safe_load((data / "golden/pompom-golden-v1/manifest.yaml").read_text())
for asset in manifest["assets"]:
    prompt = (data / "golden/pompom-golden-v1" / asset["promptFile"]).read_text()
    r = review_prompt(
        {
            "profile": "post-family-v1",
            "prompt": prompt,
            "sourceId": asset["sourceLocation"],
            "sourceVersion": asset["promptHash"],
            "settings": {},
        },
        caps,
    )
    enriched.append(
        {
            "goldenId": asset["goldenId"],
            "beforeRuntimeStatus": "UNKNOWN",
            "afterRuntimeStatus": r["generalProducibility"]["status"],
            "productionEvidence": r["productionEvidence"],
            "bindingHash": r["bindingHash"],
        }
    )
write(
    "family10-source-enrichment.json",
    {"method": "Source prompts only; no manual Gold labels loaded", "assets": enriched},
)
for key, folder, profile in [
    ("A", "Absurd_Moments/01_luca_sticky_ball", "ABSURD_PHYSICS"),
    ("B", "classic story-1/08_luca_and_zipo", "CURIOSITY_ADVENTURE"),
]:
    src = source / folder
    dest = data / "library/workflow-examples" / key
    dest.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.suffix == ".mp4" or p.name in ["01_video_prompt.txt", "00_title.txt"]:
            shutil.copy2(p, dest / p.name)
    prompt = (src / "01_video_prompt.txt").read_text()
    with urllib.request.urlopen(args.backend_url + "/api/v1/intelligence/contents") as response:
        existing = json.load(response)
    content = next(
        (item for item in existing if item["title"] == f"Workflow example {key} · " + src.name), None
    )
    if content is None:
        content = post(
            "contents",
            {
                "title": f"Workflow example {key} · " + src.name,
                "type": "REEL",
                "description": "Real existing source; isolated local validation, no generation",
            },
        )
    with urllib.request.urlopen(
        args.backend_url + f"/api/v1/intelligence/contents/{content['id']}/prompt-versions"
    ) as response:
        stored_versions = json.load(response)
    version = next((v for v in stored_versions if v.get("rawText") == prompt), None)
    if version is None:
        version = post(f"contents/{content['id']}/prompt-versions", {"rawText": prompt, "parsedIr": "{}"})
    review = post(
        "workflow/review",
        {
            "contentId": content["id"],
            "promptVersionId": version["id"],
            "sourcePath": str(src / "01_video_prompt.txt"),
            "options": {
                "profile": "post-family-v1",
                "contentProfile": profile,
                "generator": "AUTO",
                "settings": {"mode": "image2video", "aspectRatio": "9:16"},
                "references": [],
            },
        },
    )
    write("example-" + key + ".json", review)
    print(
        key,
        "content",
        content["id"],
        "version",
        version["id"],
        "review",
        review["recordId"],
        "beats",
        len(review["productionEvidence"]["videoPlanIR"]["beats"]),
        review["generation"]["desiredDuration"],
    )
    if key == "B":
        clip = next(dest.glob("*.mp4"))
        relative = str(clip.relative_to(data))
        qa = post(
            f"workflow/records/{review['recordId']}/qa",
            {"relativePath": relative, "observation": {"coverage": [], "events": []}},
        )
        write(
            "example-C-actual-clip.json",
            {
                "sourcePath": str(src / clip.name),
                "sourceSha256": hashlib.sha256(clip.read_bytes()).hexdigest(),
                "qa": qa,
            },
        )
        print("C", qa["status"], qa.get("assetHash"))
actual = args.observation_csv
if actual and actual.exists():
    rows = list(csv.DictReader(actual.open()))
    write(
        "example-D-import-readiness.json",
        {
            "sourcePath": str(actual),
            "sourceHash": hashlib.sha256(actual.read_bytes()).hexdigest(),
            "rows": rows,
            "status": "UNMATCHED",
            "reason": "Approximate contextual observations lack verified platform publication IDs "
            "and fixed observation windows; no video or cohort match inferred.",
            "syntheticTechnicalCoverage": "test_post_family_feedback.py preserves 20-digit IDs; "
            "fixtures are not real performance evidence.",
        },
    )
