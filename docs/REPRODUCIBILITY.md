# Reproducibility

This document lists the exact commands used to reproduce benchmark checks and artifacts.

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

`quick` sanity defaults (reliable local profile):

```bash
./scripts/run_official_quick.sh
```

Quick profile defaults:

- `--run-modes worker_only,mentor_worker`
- `--repro`
- `--max-turns 3`
- `--timeout 180`
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

Regenerate from tracked submissions:

```bash
"$PYTHON_BIN" scripts/build_community_leaderboard.py --strict
"$PYTHON_BIN" scripts/build_community_leaderboard.py --strict
```

Then confirm no artifact drift:

```bash
git status --short
```

Expected: clean working tree after the second strict run.

## Verify a Submission Bundle

```bash
"$PYTHON_BIN" -m mentor_worker_benchmark verify --submission submissions/<bundle>.zip
```

For multi-replicate bundles, `analysis.json` is required; for single-replicate bundles, verification can deterministically backfill analysis if absent.
