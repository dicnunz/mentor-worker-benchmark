# Reproducibility

This document lists the exact commands used to reproduce benchmark checks and artifacts.

Operational policy for this machine:
- `./scripts/run_local_verification.sh` is the sanctioned local release-health path.
- Full leaderboard/publication reproduction remains available, but it is not the practical default local gate on this 16 GB MacBook Air.

`task_pack_v2` reproducibility note:

- Active release pack: `473` exact-family-independent tasks.
- Audited source corpus: `652` generated tasks.
- The provenance `--fail-on-overlap` check fails on active exact-family leakage, not on softer near-similarity clusters.

## Choose The Right Path

Use:
- `./scripts/run_local_verification.sh` for the fastest trustworthy local gate and a verified community bundle
- `./scripts/run_official_quick.sh` for an official sanity artifact
- `./scripts/run_official_dev.sh` or `TASK_SUITE=dev50 ./scripts/run_official_dev_v1.sh` for headline multi-seed official baselines
- `./scripts/reproduce_leaderboard.sh` to rebuild the tracked public artifact set end to end

## Local Operational Verification

Recommended first step on this machine:

```bash
./scripts/run_local_verification.sh
```

Default local verification profile:
- `task_pack_v2`
- `suite=dev10`
- `seed=1337`
- `worker=phi3:mini`
- `mentor=phi3:mini`
- `run-modes=worker_only,mentor_worker`

This path performs, in order:
1. backend stability preflight
2. single-seed benchmark run
3. integrity audit
4. community bundle export
5. bundle verification

It is intended for local release-health verification only, not for headline publication.

Artifacts emitted by the script:
- preflight JSON
- results JSON
- checkpoint JSONL
- run log
- verified community submission zip

### Resume semantics

Resume source of truth:
- `<results-stem>.checkpoint.jsonl` for single-seed progress
- `<results-stem>.seed-<seed>.json` for completed per-seed artifacts

Resumable unit:
- `(seed, mode, task_id, worker_model, mentor_model)`

Changing suite, seed, models, run modes, or benchmark revision requires a new `--results-path`, because checkpoint metadata must match exactly.
Checkpoint metadata includes the benchmark git commit and task-pack metadata; resume is for interrupted reruns of the same effective benchmark, not for carrying work across code revisions.
When a run is resumed, `benchmark_wall_time_seconds` reflects accumulated completed run time, while `checkpointing.session_wall_time_seconds` reflects only the current invocation.

Not resumable until completion:
- final merged multi-seed `results.json`
- exported submission bundles
- derived leaderboard markdown/html

## Full Leaderboard Reproduction

This is the full reproducibility/publishing pipeline, not the recommended first local check on this machine.

Run the full reproducibility pipeline:

```bash
./scripts/reproduce_leaderboard.sh
```

This command performs all required steps in order:

1. Installs pinned Python dependencies into `.venv`.
2. Verifies/pulls required Ollama models.
3. Runs the canonical quick benchmark protocol.
4. Rebuilds leaderboard artifacts with strict submission verification.
5. Audits the resulting benchmark artifact integrity.

Useful environment overrides:

- `PYTHON_BIN` (bootstrap Python, default: `python3`)
- `VENV_DIR` (default: `.venv`)
- `RESULTS_PATH` (default: `results/reproducible_quick_protocol-v0.3.0_results.json`)
- `RUN_LOG_PATH`
- `SUBMISSION_PATH`
- `SEEDS` (default: `1337`)
- `CANONICAL_WORKER_MODELS` (default: `phi3:mini,qwen2.5-coder:7b`)
- `CANONICAL_MENTOR_MODELS` (default: `llama3.1:8b,mistral:7b`)

## Python Command

Use the virtualenv interpreter when available:

```bash
PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN="python"; fi
```

All commands below assume `"$PYTHON_BIN"` is set.

## Local Sanity, Validation, and Provenance

Sanity (no model calls):

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite quick --seed 1337
"$PYTHON_BIN" -m mentor_worker_benchmark sanity --task-pack task_pack_v2 --suite quick --seed 1337
```

Task-pack validation reports (with strict strength gates):

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark.tasks.task_pack_v1.validate --strict
"$PYTHON_BIN" -m mentor_worker_benchmark.tasks.task_pack_v2.validate --strict
```

Pack provenance (v2):

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark provenance --task-pack task_pack_v2 --fail-on-overlap
```

## Docker Sanity

Containerized sanity check (no Ollama required):

```bash
make docker-sanity
# or:
./scripts/docker_sanity.sh
```

Default container command:

```bash
python -m mentor_worker_benchmark sanity --task-pack task_pack_v2 --suite quick --seed 1337
```

## Official Headline Runs (Multi-Seed)

### Scripted protocol runs

`dev` headline:

```bash
./scripts/run_official_dev.sh
```

`dev` / `dev50` / `test` headline with explicit suite control:

```bash
TASK_SUITE=dev50 ./scripts/run_official_dev_v1.sh
```

`quick` sanity defaults (official sanity artifact, still heavier than local verification):

```bash
./scripts/run_official_quick.sh
```

Quick profile defaults:

- `--run-modes worker_only,mentor_worker`
- `--repro`
- `--max-turns 3`
- `--model-timeout 180`
- `--test-timeout 8`
- `--worker-num-predict 512`
- `--mentor-num-predict 256`

Default headline seeds are:

- `1337,2026,9001`

### Manual run + export + verify

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite dev50 \
  --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise \
  --repro \
  --model-timeout 180 \
  --test-timeout 8 \
  --seeds 1337,2026,9001 \
  --results-path results/official_dev50_results.json
```

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark export \
  --results results/official_dev50_results.json \
  --out submissions/official_dev50_protocol-v0.3.0_seeds-1337-2026-9001.zip \
  --official
```

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark verify \
  --submission submissions/official_dev50_protocol-v0.3.0_seeds-1337-2026-9001.zip
```

## Deterministic Leaderboard/Docs Regeneration

Run the strict leaderboard build twice: the first pass regenerates artifacts, the second proves there is no drift when the tracked archive is unchanged.
The scan is recursive under `submissions/`, including `submissions/archive/...`, and ignores local scratch names such as `submissions/local_*` and `submissions/tmp_*`.

```bash
"$PYTHON_BIN" scripts/build_community_leaderboard.py --strict
"$PYTHON_BIN" scripts/build_community_leaderboard.py --strict
```

Then confirm no artifact drift:

```bash
git status --short
```

Expected: clean working tree after the second strict run when the tracked submission archive is unchanged.

## Verify a Submission Bundle

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark verify --submission submissions/<bundle>.zip
```

For multi-replicate bundles, `analysis.json` is required; for single-replicate bundles, verification can deterministically backfill analysis if absent.
