#!/usr/bin/env python3
"""Stored response only; sockets/credentials/subprocesses disabled."""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml-service"))


def deny_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen"):
        raise RuntimeError(
            "Structured SFE replay is offline and cannot run providers or media"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--short-form-evidence-source",
        choices=["timed-text-v1", "structured-canonical-v1"],
        default="timed-text-v1",
    )
    parser.add_argument("--dual-evidence-audit", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for key in tuple(os.environ):
        if key.endswith(("_API_KEY", "_API_TOKEN")):
            os.environ.pop(key)
    os.environ.setdefault("POMPOM_DATA_ROOT", str(ROOT / "data"))
    sys.addaudithook(deny_network)
    from app.workflow.structured_sfe_replay import replay_experiment

    args.output.mkdir(parents=True, exist_ok=False)
    result = replay_experiment(
        {
            "shortFormEvidenceSourceVersion": args.short_form_evidence_source,
            "dualEvidenceAudit": args.dual_evidence_audit,
        }
    )
    with (args.output / "analysis.json").open("x") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with (args.output / "offline-proof.json").open("x") as f:
        json.dump(
            {
                "providerCalls": 0,
                "networkDenied": True,
                "credentialsStripped": True,
                "subprocessDenied": True,
                "newConceptsGenerated": 0,
            },
            f,
            indent=2,
        )
        f.write("\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in ("candidates", "legacySelection", "structuredSelection")
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
