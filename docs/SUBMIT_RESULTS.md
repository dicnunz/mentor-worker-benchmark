# Submitting Benchmark Results

This project accepts reproducible result bundles so runs can be compared on a shared leaderboard.

## 1. Choose the right run type

From repo root:

```bash
./scripts/run_local_verification.sh
```

Use that first for local release-health verification on this machine.
It is not an official suite. It exports a verified `community (not official)` bundle under `submissions/` and is the sanctioned first check before heavier publication runs.

For official/public leaderboard artifacts, use:

```bash
./scripts/run_official_quick.sh
```

or:

```bash
./scripts/run_official_dev.sh
```

Use `TASK_SUITE=dev50 ./scripts/run_official_dev_v1.sh` if you want explicit headline-suite control (`dev`, `dev50`, or `test`).

Both scripts:
- run the benchmark with standardized config (`task_pack_v2`, fixed suite/profile script defaults),
- export a submission zip,
- verify that zip locally,
- mark the submission as `official`.

Official quick default profile (`./scripts/run_official_quick.sh`):
- `--run-modes worker_only,mentor_worker`
- `--repro`
- `--max-turns 3`
- `--model-timeout 180`
- `--test-timeout 8`
- `--worker-num-predict 512`
- `--mentor-num-predict 256`

Official protocol (`v0.3.0`):
- Headline suites (`dev`/`dev50`/`test`) run 3 seeds: `1337,2026,9001`.
- Official zip filenames include protocol + seeds (for example `protocol-v0.3.0_seeds-1337-2026-9001`).
- Results include `run_group_id`, `replicates`, and a `compute_budget` manifest.

Official interpretation policy:
- `dev`/`dev50`/`test` official runs are headline baseline runs.
- `dev10`/`quick` official runs are sanity checks (harness health and error-rate visibility).
- The official headline scripts remain scientifically valid but are not the practical default local gate on this 16 GB MacBook Air.

Environment variables:
- `PYTHON_BIN` (default: `python3`)
- `MWB_MODELS` (default: `default`)
- `RESULTS_PATH` (optional override)
- `SUBMISSION_PATH` (optional override)

## 2. Manual export / verify (optional)

```bash
python -m mentor_worker_benchmark export \
  --results results/results.json \
  --out submissions/my_run.zip

python -m mentor_worker_benchmark verify \
  --submission submissions/my_run.zip
```

Submission zip contents:
- `results.json`
- `environment.json`
- `analysis.json` (deterministic task-family CI/significance analysis)
- `submission_manifest.json` (commit, task-pack version, CLI command, protocol metadata, compute budget)

By default, manual exports are labeled `community (not official)`.
Only maintainers should use `--official` for standardized official runs.

## 3. Open a submission issue

Use the **Benchmark Result Submission** issue template and attach/link your `.zip`.

Include:
- task pack and suite,
- models used,
- commit hash,
- CLI command,
- verification output.

## Maintainer verification

Maintainers can run local verification:

```bash
python -m mentor_worker_benchmark verify --submission submissions/<name>.zip
```

Or use GitHub Actions manual workflow: **Verify Submission Bundle** (`workflow_dispatch`) with either:
- `submission_url` (public zip URL), or
- `submission_path` (path in repo).

For submission PRs, CI also runs **Submissions PR Check** to:
- verify changed bundles,
- regenerate normalized leaderboard artifacts,
- refresh `docs/index.html` and `docs/leaderboard.md`.

Tracked historical/public bundles may live under `submissions/archive/...`; the leaderboard refresh scans `submissions/` recursively and ignores local scratch names such as `submissions/local_*` and `submissions/tmp_*`.
