# Pompom Creative Lab

Local-first creative experimentation and learning system for videos under `new14092026`.
It does not modify source media. Creative quality, observed platform performance, and learned
test opportunity remain separate. Forecasts are uncertainty-aware historical estimates, and
pre-publish forecasts become database-enforced immutable evidence when locked.

The dashboard has three complementary areas:

- **Action DNA:** checks similarity to the proven anomaly/goal/struggle/escalation structure.
- **Stock Creative Rescue:** finds the video's own mechanism and tests whether edit order,
  opening, pacing, or ending is wasting it. It does not force all stock into one format.
- **Experiment Lab:** imports recurring performance files, rebuilds trajectories, audits
  predictions, tracks experiments/models, and exposes character coverage gaps.

## First Run

```bash
cd "/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Pompom_Creative_Lab"
chmod +x pompom
./pompom analyse "../What’s Wrong? uploaded" --limit 1
./pompom dashboard
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

The current machine already has the required FFmpeg, OpenCV, NumPy, and Pillow tools. For a
fresh machine, use Python 3.11+ and install the project:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
```

## Commands

```bash
./pompom analyse                       # full configured new14092026 tree
./pompom analyse "../Absurd_Moments"   # one series
./pompom analyse /absolute/video.mp4   # one in-scope video
./pompom rescue                        # full Stock Creative Rescue pass
./pompom rescue "../Absurd_Moments"    # Rescue pass for one series
./pompom daily --limit 12
./pompom report
./pompom dashboard
./pompom fix VIDEO_ID
./pompom rescue-fix VIDEO_ID --variant minimal
./pompom rescue-fix VIDEO_ID --variant cold_open
./pompom reanalyse VIDEO_ID
./pompom import-performance metrics.csv
./pompom import-performance meta.xlsx --preview --platform instagram
./pompom unresolved-imports
./pompom reconcile RAW_ROW_ID VIDEO_ID
./pompom rebuild-trajectories
./pompom fingerprint --all
./pompom test-plan --platform instagram
./pompom predict VIDEO_ID --platform instagram --lock
./pompom evaluate-prediction PREDICTION_ID
./pompom reliability --platform instagram
./pompom backtest --platform instagram --horizon 1440
./pompom human-predict VIDEO_ID --platform instagram --band STRONG
./pompom character-assign VIDEO_ID Kiko --role PROTAGONIST --primary
./pompom character-stats --platform instagram
./pompom learn --platform instagram
./pompom update-research
```

Use `--force` only when a current analysis should be replaced. One corrupt video is logged
and skipped without aborting the batch.

## Output

All generated state is under `.lab_data/`:

- `library.sqlite3`: versioned library and human decisions
- `output/analyses/<video-id>/analysis.json`
- `output/analyses/<video-id>/report.md`
- `output/analyses/<video-id>/storyboard.jpg`
- `output/analyses/<video-id>/timeline.json`
- `output/analyses/<video-id>/fix_plan.json`
- `output/edited_candidates/<video-id>/`: never-overwritten source derivatives
- `output/rescue/<video-id>/rescue_report.md`
- `output/rescue_candidates/<video-id>/`: original/minimal vs cold-open A/B candidates
- immutable raw import rows, normalised observations, trajectories, dataset snapshots,
  model versions, predictions, and audits in `library.sqlite3`
- `RESEARCH_FINDINGS.md`: evidence-thresholded observational findings

## Daily Learning Loop

1. Analyse stock and build fingerprints.
2. Create a test plan and optional blind human forecast.
3. Generate and lock platform-specific pre-publish forecasts.
4. Publish, then import checkpoint exports with `--preview` first.
5. Review unresolved matches and conflicts. Imports automatically rebuild trajectories and
   audit eligible locked forecasts; they never auto-train or auto-promote a model.
6. Create a challenger explicitly with `pompom learn`, backtest it, and promote only after
   justified validation.

CSV, TSV, XLSX, and JSON are supported. Legacy binary `.xls` files are preserved but must be
converted to XLSX or CSV. The account timezone defaults to `Europe/London` with DST handling.

## Confidence

Default analysis uses local frame/motion/audio evidence. It intentionally marks semantic
fields such as character goal, physical rule, and anatomy continuity as lower confidence.
Configure a local VLM for stronger semantic evidence; external network use remains off.
