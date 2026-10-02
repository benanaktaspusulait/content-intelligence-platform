from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import load_settings
from .characters import add_character, assign as assign_character, list_characters, pair_statistics, statistics_by_platform
from .dashboard import Dashboard
from .database import Database
from .fingerprints import build as build_fingerprint
from .fingerprints import build_all as build_all_fingerprints
from .fix_engine import create_candidate
from .learning import create_challenger, models as list_models
from .pipeline import Pipeline
from .prediction import audit as audit_prediction
from .prediction import backtest, create_prediction, lock_prediction, record_human_prediction, reliability, research_questions
from .rescue import RescuePipeline
from .rescue_edit import comparison as rescue_comparison
from .rescue_edit import create_rescue_candidate
from .research import update_findings
from .spreadsheet_ingest import import_path, resolve_row, unresolved
from .test_planner import create_experiment, list_experiments, plan as create_test_plan
from .trajectory import rebuild as rebuild_trajectories


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="pompom", description="Local-first Pompom creative video review")
    root.add_argument("--config", help="Path to config.toml")
    root.add_argument("--verbose", action="store_true")
    commands = root.add_subparsers(dest="command", required=True)
    analyse = commands.add_parser("analyse", help="Analyse a file or directory")
    analyse.add_argument("target", nargs="?", help="Defaults to configured input_dir")
    analyse.add_argument("--force", action="store_true")
    analyse.add_argument("--limit", type=int)
    rescue = commands.add_parser("rescue", help="Analyse each video's own creative engine and edit-order opportunities")
    rescue.add_argument("target", nargs="?", help="Defaults to configured input_dir")
    rescue.add_argument("--force", action="store_true")
    rescue.add_argument("--limit", type=int)
    commands.add_parser("dashboard", help="Start local review dashboard")
    commands.add_parser("report", help="Print series-level descriptive report")
    daily = commands.add_parser("daily", help="Print a small human-review queue")
    daily.add_argument("--limit", type=int, default=12)
    fix = commands.add_parser("fix", help="Render a non-destructive safe edit candidate")
    fix.add_argument("video_id")
    rescue_fix = commands.add_parser("rescue-fix", help="Render and re-analyse a Stock Creative Rescue A/B candidate")
    rescue_fix.add_argument("video_id")
    rescue_fix.add_argument("--variant", choices=("minimal", "cold_open"), required=True)
    reanalyse = commands.add_parser("reanalyse", help="Force re-analysis")
    reanalyse.add_argument("video_id")
    fingerprint = commands.add_parser("fingerprint", help="Build versioned creative fingerprints")
    fingerprint.add_argument("video_id", nargs="?")
    fingerprint.add_argument("--all", action="store_true")
    fingerprint.add_argument("--force", action="store_true")
    importer = commands.add_parser("import-performance", help="Preview or import CSV, TSV, or XLSX performance exports")
    importer.add_argument("source")
    importer.add_argument("--preview", action="store_true")
    importer.add_argument("--platform", choices=("instagram", "facebook", "tiktok", "manual"))
    importer.add_argument("--timezone", default="Europe/London")
    commands.add_parser("unresolved-imports", help="List performance rows needing a video match")
    resolver = commands.add_parser("resolve-import", help="Resolve an imported row to a video")
    resolver.add_argument("raw_row_id", type=int)
    resolver.add_argument("video_id")
    resolver.add_argument("--note", default="human resolution")
    reconcile = commands.add_parser("reconcile", help="Human resolution alias for an imported row")
    reconcile.add_argument("raw_row_id", type=int)
    reconcile.add_argument("video_id")
    reconcile.add_argument("--note", default="human reconciliation")
    commands.add_parser("rebuild-trajectories", help="Rebuild checkpoint trajectories from normalised observations")
    predict = commands.add_parser("predict", help="Create a platform-specific forecast")
    predict.add_argument("video_id")
    predict.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    predict.add_argument("--planned-publish-time")
    predict.add_argument("--mode", default="PRE_PUBLISH", choices=("PRE_PUBLISH", "EARLY_LIVE"))
    predict.add_argument("--knowledge-cutoff")
    predict.add_argument("--lock", action="store_true")
    locker = commands.add_parser("lock-prediction", help="Permanently lock a forecast")
    locker.add_argument("prediction_id", type=int)
    locker.add_argument("--note", default="confirmed for publication")
    auditor = commands.add_parser("evaluate-prediction", help="Compare a locked forecast with observed checkpoints")
    auditor.add_argument("prediction_id", type=int)
    reliability_parser = commands.add_parser("reliability", help="Report forecast calibration and error")
    reliability_parser.add_argument("--platform", choices=("instagram", "facebook", "tiktok"))
    backtester = commands.add_parser("backtest", help="Run expanding-window historical baseline evaluation")
    backtester.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    backtester.add_argument("--horizon", type=int, default=1440)
    human = commands.add_parser("human-predict", help="Lock a human forecast before revealing model output")
    human.add_argument("video_id")
    human.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    human.add_argument("--horizon", type=int, default=1440)
    human.add_argument("--expected", type=float)
    human.add_argument("--band", choices=("LOW", "PARTIAL", "MEANINGFUL", "STRONG", "PERSISTENT", "BREAKOUT"))
    human.add_argument("--rationale")
    commands.add_parser("research-questions", help="Summarise current reliability research questions")
    update_research = commands.add_parser("update-research", help="Write evidence-thresholded observational findings")
    update_research.add_argument("--minimum-sample", type=int, default=8)
    learner = commands.add_parser("learn", help="Create a reproducible challenger model snapshot")
    learner.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    learner.add_argument("--as-of")
    commands.add_parser("models", help="List champion and challenger models")
    planner = commands.add_parser("test-plan", help="Build an exploit/adjacent/explore publishing plan")
    planner.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    planner.add_argument("--limit", type=int, default=10)
    character_add = commands.add_parser("character-add", help="Add a character to the registry")
    character_add.add_argument("name")
    character_add.add_argument("--status", default="NEW", choices=("ESTABLISHED", "LIMITED_DATA", "NEW", "UNTESTED"))
    character_add.add_argument("--notes")
    character_assign = commands.add_parser("character-assign", help="Assign an explicit character role to a video")
    character_assign.add_argument("video_id")
    character_assign.add_argument("character")
    character_assign.add_argument("--role", default="UNKNOWN", choices=("PROTAGONIST", "HELPER", "RIVAL", "OBSERVER", "COMEDIC_TARGET", "TEACHER", "UNKNOWN"))
    character_assign.add_argument("--primary", action="store_true")
    character_stats = commands.add_parser("character-stats", help="Show raw and small-sample-adjusted character evidence")
    character_stats.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    commands.add_parser("characters", help="List character registry")
    experiment_create = commands.add_parser("experiment-create", help="Register an experiment hypothesis")
    experiment_create.add_argument("name")
    experiment_create.add_argument("--platform", required=True, choices=("instagram", "facebook", "tiktok"))
    experiment_create.add_argument("--hypothesis", required=True)
    experiment_create.add_argument("--design", default="MATCHED_CROSS_VIDEO", choices=("DIRECT_AB", "MATCHED_CROSS_VIDEO", "OBSERVATIONAL"))
    experiment_create.add_argument("--metric", default="views")
    experiment_create.add_argument("--horizon", type=int, default=1440)
    commands.add_parser("experiments", help="List registered experiments")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = load_settings(args.config)
    database = Database(settings.database, settings.project_dir / "migrations")
    pipeline = Pipeline(settings, database)
    rescue_pipeline = RescuePipeline(settings, database)
    if args.command == "analyse":
        target = Path(args.target).expanduser().resolve() if args.target else settings.input_dir
        if settings.input_dir != target and settings.input_dir not in target.parents:
            print(f"Refusing out-of-scope target: {target}\nAllowed root: {settings.input_dir}", file=sys.stderr)
            return 2
        completed, skipped, failed = pipeline.analyse_batch(target, args.force, args.limit)
        print(f"completed={completed} skipped={skipped} failed={failed}")
        return 1 if failed else 0
    if args.command == "rescue":
        target = Path(args.target).expanduser().resolve() if args.target else settings.input_dir
        if settings.input_dir != target and settings.input_dir not in target.parents:
            print(f"Refusing out-of-scope target: {target}\nAllowed root: {settings.input_dir}", file=sys.stderr)
            return 2
        completed, skipped, failed = rescue_pipeline.analyse_batch(target, args.force, args.limit)
        print(f"completed={completed} skipped={skipped} failed={failed}")
        return 1 if failed else 0
    if args.command == "dashboard":
        Dashboard(settings, database).serve()
        return 0
    if args.command == "report":
        rows = database.series_summary()
        print("Series | Videos | Median DNA | Median Hook | Median Action | Good/Winner | Observed median reach/views")
        for row in rows:
            print(f"{row['series']} | {row['video_count']} | {row['median_action_dna']} | {row['median_hook']} | {row['median_action']} | {row['strong_count']} | {row['observed_median_performance'] or '-'}")
        return 0
    if args.command == "daily":
        rows = database.list_videos()
        unreviewed = [row for row in rows if not row.get("confirmed_classification") and not row.get("override_classification")]
        queue = sorted(unreviewed, key=lambda row: (-float(row["action_dna"]), row["filename"]))[: args.limit]
        headings = {"WINNER CANDIDATE": "BEST PRIME-SLOT CANDIDATE", "GOOD": "GOOD NORMAL-SLOT CANDIDATES", "AVERAGE/FIXABLE": "FIX-FIRST CANDIDATES", "BAD": "LOW-VALUE NIGHT TEST CANDIDATES"}
        for category in ("WINNER CANDIDATE", "GOOD", "AVERAGE/FIXABLE", "BAD"):
            print(f"\n{headings[category]}")
            for row in queue:
                if row["classification"] == category:
                    print(f"- {row['id']} {row['series']} / {row['filename']} (DNA {row['action_dna']})")
        return 0
    if args.command == "fix":
        original = database.detail(args.video_id)
        if not original:
            print("Unknown video ID", file=sys.stderr)
            return 2
        output = create_candidate(database, settings.data_dir, args.video_id)
        fixed = pipeline.analyse_one(output, force=True)
        comparison = {
            "original_video_id": args.video_id,
            "candidate_video_id": fixed.video_id,
            "classification": [original["classification"], fixed.classification],
            "creative_structure_match": [original["action_dna"], fixed.creative_structure_match],
            "hook_score": [original["analysis"]["scores"]["first_frame_hook"], fixed.scores["first_frame_hook"]],
            "dead_time_seconds": [sum(item["end"] - item["start"] for item in original["analysis"]["dead_time"]), sum(item.end - item.start for item in fixed.dead_time)],
            "duration": [original["duration"], fixed.metadata.duration],
            "trade_off": "Numeric changes are supporting evidence only; human review must confirm continuity and story clarity.",
        }
        (output.parent / "comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
        database.record_edit(args.video_id, int(original["analysis_id"]), output, "REANALYSED", comparison)
        print(output)
        print(json.dumps(comparison, indent=2))
        return 0
    if args.command == "rescue-fix":
        original = database.detail(args.video_id)
        if not original:
            print("Unknown video ID", file=sys.stderr)
            return 2
        output = create_rescue_candidate(database, settings.data_dir, args.video_id, args.variant)
        fixed = rescue_pipeline.analyse_one(output, force=True)
        candidate = database.detail(fixed.video_id)
        if not candidate:
            raise RuntimeError("Candidate re-analysis was not persisted")
        result = rescue_comparison(original, candidate, args.variant)
        (output.parent / f"comparison_{args.variant}.json").write_text(json.dumps(result, indent=2) + "\n")
        database.record_rescue_edit(args.video_id, args.variant, output, result)
        print(output)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "reanalyse":
        detail = database.detail(args.video_id)
        if not detail:
            print("Unknown video ID", file=sys.stderr)
            return 2
        result = pipeline.analyse_one(Path(detail["path"]), force=True)
        print(f"{result.classification} DNA={result.creative_structure_match}")
        return 0
    if args.command == "fingerprint":
        if not args.all and not args.video_id:
            print("Provide VIDEO_ID or --all", file=sys.stderr)
            return 2
        result = build_all_fingerprints(database, args.force) if args.all else build_fingerprint(database, args.video_id, args.force)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "import-performance":
        try:
            result = import_path(database, Path(args.source), args.platform, args.timezone, args.preview)
        except (ValueError, OSError) as error:
            print(str(error), file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command == "unresolved-imports":
        print(json.dumps(unresolved(database), indent=2, ensure_ascii=False))
        return 0
    if args.command in {"resolve-import", "reconcile"}:
        resolve_row(database, args.raw_row_id, args.video_id, args.note)
        print("resolved")
        return 0
    if args.command == "rebuild-trajectories":
        print(json.dumps(rebuild_trajectories(database), indent=2))
        return 0
    if args.command == "predict":
        result = create_prediction(database, args.video_id, args.platform, args.planned_publish_time, args.mode, args.knowledge_cutoff, args.lock)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "lock-prediction":
        lock_prediction(database, args.prediction_id, args.note)
        print(f"prediction {args.prediction_id} locked")
        return 0
    if args.command == "evaluate-prediction":
        print(json.dumps(audit_prediction(database, args.prediction_id), indent=2))
        return 0
    if args.command == "reliability":
        print(json.dumps(reliability(database, args.platform), indent=2))
        return 0
    if args.command == "backtest":
        print(json.dumps(backtest(database, args.platform, args.horizon), indent=2))
        return 0
    if args.command == "human-predict":
        print(record_human_prediction(database, args.video_id, args.platform, args.horizon, args.expected, args.band, args.rationale))
        return 0
    if args.command == "research-questions":
        print(json.dumps(research_questions(database), indent=2))
        return 0
    if args.command == "update-research":
        print(json.dumps(update_findings(database, settings.project_dir / "RESEARCH_FINDINGS.md", args.minimum_sample), indent=2))
        return 0
    if args.command == "learn":
        print(json.dumps(create_challenger(database, args.platform, args.as_of), indent=2))
        return 0
    if args.command == "models":
        print(json.dumps(list_models(database), indent=2))
        return 0
    if args.command == "test-plan":
        print(json.dumps(create_test_plan(database, args.platform, args.limit), indent=2))
        return 0
    if args.command == "character-add":
        print(add_character(database, args.name, args.status, args.notes))
        return 0
    if args.command == "character-assign":
        assign_character(database, args.video_id, args.character, args.role, args.primary)
        print("assigned")
        return 0
    if args.command == "character-stats":
        print(json.dumps({"characters": statistics_by_platform(database, args.platform), "pairs": pair_statistics(database, args.platform)}, indent=2))
        return 0
    if args.command == "characters":
        print(json.dumps(list_characters(database), indent=2))
        return 0
    if args.command == "experiment-create":
        print(create_experiment(database, args.name, args.platform, args.hypothesis, args.design, args.metric, args.horizon))
        return 0
    if args.command == "experiments":
        print(json.dumps(list_experiments(database), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
