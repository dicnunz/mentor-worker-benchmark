# Submitting Benchmark Results

This project accepts reproducible result bundles so runs can be compared on a shared leaderboard.

## 1. Run an official suite

From repo root:

```bash
./scripts/run_official_quick.sh
```

or:

```bash
./scripts/run_official_dev.sh
```

Both scripts:
- run the benchmark with standardized config (`task_pack_v2`, fixed suite/profile script defaults),
- export a submission zip,
- verify that zip locally,
- mark the submission as `official`.

Official protocol (`v0.3.0`):
- Headline suites (`dev`/`dev50`/`test`) run 3 seeds: `1337,2026,9001`.
- Official zip filenames include protocol + seeds (for example `protocol-v0.3.0_seeds-1337-2026-9001`).
- Results include `run_group_id`, `replicates`, and a `compute_budget` manifest.

Official interpretation policy:
- `dev`/`dev50`/`test` official runs are headline baseline runs.
- `dev10`/`quick` official runs are sanity checks (harness health and error-rate visibility).

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
- `analysis.json` (deterministic CI/significance analysis)
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
