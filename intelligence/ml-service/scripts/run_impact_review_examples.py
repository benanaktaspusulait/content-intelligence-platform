"""Read real sources and already-inspected local frames; no paid calls or media generation.

The observed notes below are an operator's static-frame inspection, not a VLM/clip
validation result. Audience counts are written only after the blind review is fixed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def post(base, route, value):
    request = urllib.request.Request(
        base + route, data=json.dumps(value).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8085")
    parser.add_argument("--inspected-frames", required=True)
    args = parser.parse_args()
    source = Path(args.source_root) / "09_SOCIAL_REELS/new14092026"
    folders = {
        "Noah / Walking Shoes": ("Absurd_Moments/05_noah_walking_shoes", 89000),
        "Upside-Down Chair": ("What’s Wrong? uploaded/1-The Upside-Down Chair", 64000),
        "Missing Shoe": ("english learning uploaded/3-“Where is it?” — Luca’s Missing Shoe", 45000),
        "Tiny Door": ("What’s Wrong? uploaded/4-The Tiny Door", 61000),
        "Kiko / Soap": ("chaplin_set/09_kiko_vs_soap", None),
        "Luca & Zipo": ("classic story-1/08_luca_and_zipo", None),
    }
    dest = ROOT / "data/workflow/reports/impact-amendment"
    dest.mkdir(parents=True, exist_ok=True)
    availability = []
    for name, (directory, _) in folders.items():
        folder = source / directory
        paths = (
            sorted(
                p
                for p in folder.iterdir()
                if p.is_file() and (p.suffix == ".mp4" or "prompt" in p.name.lower())
            )
            if folder.is_dir()
            else []
        )
        availability.append(
            {
                "target": name,
                "artifacts": [
                    {"path": str(p), "sha256": digest(p), "bytes": p.stat().st_size} for p in paths
                ],
                "reviewStatus": "TARGET_AVAILABLE_NOT_AUTOMATICALLY_REVIEWED" if paths else "UNAVAILABLE",
            }
        )
    (dest / "source-availability.json").write_text(json.dumps(availability, ensure_ascii=False, indent=2))
    actual_prompt = ROOT / "data/library/workflow-examples/B/01_video_prompt.txt"
    text = actual_prompt.read_text()

    def claim(quote, **fields):
        start = text.index(quote)
        return dict(sourceSpan=[start, start + len(quote)], sourceQuote=quote, **fields)

    options = {
        "profile": "post-family-v1",
        "contentProfile": "CURIOSITY_ADVENTURE",
        "openingStrategy": "CURIOSITY_DISCOVERY",
        "desiredDuration": 25,
        "generator": "SEEDANCE_2_5",
        "settings": {"mode": "image2video", "resolution": "480p", "aspectRatio": "9:16"},
        "references": [],
        "protectedIntent": [],
        "intentRequirements": [
            claim(
                "They hug. Zipo floats upward. Luca waves.",
                id="farewell",
                level="ESSENTIAL",
                eventIds=["source_4"],
                rationale="Yakınlık ve ayrılık deneyiminin planlanan merkezi olayı",
            )
        ],
        "creativeEvidence": [
            claim(
                "Luca looks through toy binoculars at stars.\nA beam sweeps across grass.",
                dimension="OPENING",
                assessment="READABLE_EARLY_DEVELOPMENT",
                visualFocus="READABLE",
                promise="CONCRETE",
                causeAtFrameZero="UNEXPLAINED",
                rationale=(
                    "Yıldızlara bakan çocuğun dikkatini çeken ışın, kim geliyor sorusu"
                    "nu planlıyor; ilk kare tam mekanizmayı açıklamak zorunda değil."
                ),
            ),
            claim(
                'Zipo becomes sad.\nLuca: "They found you?"\nZipo: "Blip."\nLuca: "I\'ll miss you."',
                dimension="PROGRESSION",
                assessment="DEVELOPING",
                mechanisms=["EMOTIONAL", "RELATIONAL"],
                rationale=(
                    "Tanışma ve birlikte keşiften ayrılık kaygısına geçiş, izleme dene"
                    "yimini daha fazla fiziksel karmaşa gerektirmeden değiştiriyor."
                ),
            ),
            claim(
                (
                    "Luca enters room sadly.\nA small glowing stone sits on desk.\nIt li"
                    'ghts up.\nZipo voice: "Blip blop, Luca!"\nLuca beams.'
                ),
                dimension="ENDING",
                assessment="DELIVERS_PROMISE",
                functions=["EMOTIONAL_SATISFACTION", "REVEAL", "CALLBACK"],
                rationale=(
                    "Planın masa taşı ve tanıdık ses dönüşü ayrılığı yeniden çerçeveli"
                    "yor; gerçek ses/video karşılığı ayrıca doğrulanmalı."
                ),
            ),
        ],
    }
    review = post(
        args.backend_url,
        "/api/v1/intelligence/workflow/review",
        {"contentId": 3, "promptVersionId": 3, "options": options},
    )
    if review["finalPrompt"] != text:
        raise ValueError("Stored prompt differs from actual source; stop example")
    (dest / "prompt-review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2))
    video_path = "library/workflow-examples/B/08_luca_and_zipo_hd.mp4"
    # These images have been inspected by the operator. They support poses/shot
    # sequence only; motion/contact/voice evidence is deliberately not claimed.
    defect = {
        "type": "SHOT_ORDER_VARIATION",
        "start": 9.9,
        "end": 10.8,
        "durationSeconds": 0.9,
        "recurrence": 1,
        "eventId": "source_4",
        "affectedEntity": "Luca and Zipo",
        "rawSeverity": "PLAN_ORDER_MISMATCH",
        "observed": (
            "8 fps örneklerinde yükselmiş Zipo pozu yaklaşık 10.0 s civarında,"
            " sarılma pozu yaklaşık 10.375 s civarında görülüyor."
        ),
        "inferred": (
            "Planlanan sarılma → yükselme sırası kurguda değişmiş görünüyor; b"
            "u tek başına vedalaşmanın okunabilirliğini yok etmiyor."
        ),
        "uncertainty": "Yaklaşık 0.125 s örnekleme aralığı; sürekli hareket, tam temas ve ses doğrulanmadı.",
        "impact": "LOCAL_TOLERABLE",
        "confidence": "MEDIUM",
        "requiresMotion": False,
        "evidenceBasis": "DENSE_LOCAL_FRAMES",
        "reference": f"{video_path}#t=9.9,10.8",
    }
    observation = {
        "coverage": [0, 15.104],
        "events": [],
        "defects": [defect],
        "experience": {
            "openingFrame": {
                "value": "READABLE",
                "start": 0,
                "end": 0,
                "observed": "Gerçek videonun sıfırıncı karesinde dürbünlü çocuğun yakın planı okunuyor.",
                "inferred": "İlk kare odağı okunabilir; "
                "gelişen görsel vaat için sonraki hareket ayrıca incelenmeli.",
                "uncertainty": "Tek kare, hareket/nedensellik/ses "
                "veya kanonik görsel kabul kapısı kanıtı değildir.",
                "requiresMotion": False,
                "confidence": "MEDIUM",
                "evidenceBasis": "DENSE_LOCAL_FRAMES",
                "reference": f"{video_path}#t=0,0",
            }
        },
    }
    qa = post(
        args.backend_url,
        f"/api/v1/intelligence/workflow/records/{review['recordId']}/qa",
        {
            "relativePath": video_path,
            "humanReviewed": False,
            "stillsReviewed": True,
            "observation": observation,
        },
    )
    (dest / "actual-video-review.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2))
    frames = Path(args.inspected_frames)
    for name in ["contact-01.jpg", "contact-02.jpg", "transition-8.5-11.5.jpg", "actual-frame-zero.png"]:
        shutil.copy2(frames / name, dest / name)
    notes = {
        "sourcePromptHash": digest(actual_prompt),
        "videoHash": digest(ROOT / "data" / video_path),
        "videoDurationSeconds": 15.104,
        "sourcePromptPlanSeconds": [22, 25],
        "frameEvidenceMethod": "LOCAL_FFMPEG_STATIC_FRAME_INSPECTION",
        "actualFrameZero": {
            "timestampSeconds": 0,
            "sha256": digest(dest / "actual-frame-zero.png"),
            "canonicalVisualGate": False,
        },
        "sampling": [
            {"interval": [0, 15.104], "fps": 2, "uncertaintySeconds": 0.25},
            {"interval": [8.5, 11.5], "fps": 8, "uncertaintySeconds": 0.125},
        ],
        "observed": [
            {
                "interval": [0, 2.5],
                "description": (
                    "Başlangıçta dürbünlü çocuk, ardından ışın ve tek gözlü yeşil varlık kareleri görülüyor."
                ),
            },
            {"interval": [5.5, 7.5], "description": "Uğurböceği ve bisküvi ile karşılaşma görüntüleri."},
            {"interval": [9.9, 11.5], "description": defect["observed"]},
            {"interval": [13, 14.5], "description": "Masa üzerinde mavi taş ve çocuğun yakın yüz planı."},
        ],
        "inferred": [
            (
                "Keşif → yakınlaşma → ayrılık → taş görüntüsü planın ilişkisel/duy"
                "gusal niyetine aday karşılıklar sunuyor."
            )
        ],
        "notEstablished": [
            "Actual voice or transcript",
            "Precise contact or continuous animation",
            "Official-reference identity match",
            "Measured audience response",
        ],
        "editorialDecision": qa["editorialRecommendation"],
        "planFidelity": qa["planFidelity"],
        "viewerFacingUsability": qa["viewerFacingUsability"],
    }
    (dest / "video-inspection-notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2))
    # Fix review first; user-reported approximations are context, not evaluator input.
    outcomes = [
        {
            "target": name,
            "reportedApproximateViews": views,
            "basis": "USER_REPORTED_APPROXIMATE" if views is not None else "NO_AUDIENCE_EVIDENCE",
            "fixedHorizon": "UNKNOWN",
            "verifiedPublicationId": None,
            "usedInEvaluator": False,
        }
        for name, (_, views) in folders.items()
    ]
    (dest / "outcome-context-only.json").write_text(json.dumps(outcomes, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            {
                "promptReviewId": review["recordId"],
                "actualReviewId": qa["recordId"],
                "actualDecision": qa["editorialRecommendation"],
                "defectSeverity": qa["findings"][0]["severity"],
            }
        )
    )


if __name__ == "__main__":
    main()
