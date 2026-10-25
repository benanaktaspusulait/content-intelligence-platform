#!/usr/bin/env python3
"""Network-denied stored-response replay. No provider or generation options."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))


def offline_guard(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen"):
        raise RuntimeError("Evidence replay forbids provider/network/process access")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic-evidence-adapter-version", choices=["v1"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for key in tuple(os.environ):
        if key.endswith(("_API_KEY", "_API_TOKEN")):
            os.environ.pop(key)
    sys.addaudithook(offline_guard)
    os.environ.setdefault("POMPOM_DATA_ROOT", str(ROOT / "data"))
    from app.workflow.semantic_evidence_replay import replay_experiment

    output = args.output
    output.mkdir(parents=True, exist_ok=False)
    report = replay_experiment(
        {"semanticEvidenceAdapterVersion": args.semantic_evidence_adapter_version}
    )
    with (output / "analysis.json").open("x") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    proof = {
        "providerCalls": 0,
        "networkDeniedByAuditHook": True,
        "credentialEnvironmentStripped": True,
        "subprocessDenied": True,
        "analysisSha256": hashlib.sha256(
            (output / "analysis.json").read_bytes()
        ).hexdigest(),
    }
    with (output / "offline-execution-proof.json").open("x") as f:
        json.dump(proof, f, indent=2)
        f.write("\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ("candidates", "excludedRawEntries", "pipelineEvidence")
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
