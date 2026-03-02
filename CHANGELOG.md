# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.1] - 2026-03-02

### Changed
- Fixed README/doc inaccuracies: `task_pack_v2` quick split is `30` tasks, and CLI suite examples now include `dev10`.
- Clarified official baseline policy:
  - headline official numbers come from `dev`/`dev50`/`test`
  - official `dev10`/`quick` runs are sanity checks only.
- Improved community leaderboard normalization for legacy bundles missing newer summary fields.
  - Backfills `total_passes`, per-mode pass counts, model-call errors/timeouts from raw `results.runs` when available.
  - Emits explicit `metrics_source` metadata in normalized submission JSON.
  - Adds official-role labeling (`headline` vs `sanity`) and updates docs rendering accordingly.
- Added regression tests for leaderboard legacy backfill and official-role classification.
- Bumped package version to `0.2.1`.

## [0.1.0] - 2026-03-01

### Added
- Local Ollama integration for mentor/worker chat loops and setup checks.
- Objective coding benchmark harness with patch application and pytest scoring.
- `task_pack_v1` deterministic corpus (300 tasks) with `train/dev/test` and `quick` split.
- Benchmark run modes:
  - `worker_only`
  - `mentor_worker`
  - `mentor_only_suggestion_noise`
  - `stronger_worker`
  - `mentor_swap`
- Reproducibility mode (`--repro`) with fixed generation settings and deterministic ordering.
- Mentor constraint enforcement with violation detection, blocking, and logging.
- Patch safety checks and isolated test execution with per-task timeout.
- Result artifacts:
  - `results/results.json`
  - `results/leaderboard.md`
  - `results/schema.md`
- CLI commands:
  - `setup`
  - `run`
  - `sanity`
  - `leaderboard`
  - `compare`
- CI workflow for tests, task-pack metadata/schema validation, and sanity subset checks.
- Leaderboard publishing utility (`scripts/publish_leaderboard.py`) that also writes `docs/index.html` for GitHub Pages.
- Project quality and community files:
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - GitHub release notes template config.
