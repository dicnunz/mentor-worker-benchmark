# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-03

### Added
- Release methodology and reproducibility documentation:
  - `docs/METHODOLOGY.md`
  - `docs/REPRODUCIBILITY.md`
- Minimal front-page README doc index linking leaderboard, methodology, reproducibility, submission, and pack data-card docs.

### Changed
- Stabilized release metadata at `1.0.0`.
- Multi-seed analysis and reporting are now first-class release methodology:
  - confidence intervals and significance marker,
  - task/test strength gates,
  - official multi-seed protocol and compute budget manifest,
  - pack registry + external pack hashing,
  - Docker sanity path and CI docker sanity job,
  - leaderboard UI v2 artifact flow.

## [0.3.0] - 2026-03-03

### Added
- Added deterministic `analyze` CLI subcommand:
  - `python -m mentor_worker_benchmark analyze --results <path> --out <json>`
  - Computes multi-replicate means, 95% bootstrap CIs, lift CI, and paired bootstrap significance.
  - Emits explicit provenance (`analysis_version`, `ci_method`, `bootstrap_samples`, `bootstrap_seed`).
- Added support for optional `results.replicates` payloads to represent seeded reruns for the same benchmark config.

### Changed
- Submission export now always bundles `analysis.json` alongside `results.json`, `environment.json`, and `submission_manifest.json`.
- Submission verification now:
  - Requires valid `analysis.json` when `results.replicates` contains multiple replicates.
  - Deterministically backfills analysis during verify when a single-replicate archive omits `analysis.json`.
- Community leaderboard normalization now surfaces CI/significance fields per submission:
  - `baseline_mean`, `baseline_ci_low`, `baseline_ci_high`
  - `mentored_mean`, `mentored_ci_low`, `mentored_ci_high`
  - `lift_mean`, `lift_ci_low`, `lift_ci_high`, `lift_significant`
- Legacy `best_worker` Baseline/Mentored/Lift fields are preserved and now mapped to analysis means for backward compatibility.
- Docs leaderboard UI now shows CI tooltips on Baseline/Mentored/Lift and a `sig` marker when lift CI excludes zero.
- Added deterministic analysis and submission verification tests, including a two-replicate fixture.
- Bumped package version to `0.3.0`.

## [0.2.2] - 2026-03-02

### Changed
- Refined leaderboard UI v2 in `docs/index.html` generation: single-table flow with role/pack/suite/search/sort controls, highlight cards, and per-row commit copy action.
- Kept docs generation deterministic with embedded summary JSON and retained fast UI-facing generator test coverage.
- Added fresh dated community submissions and refreshed normalized leaderboard artifacts (`leaderboard/summary.json`, `docs/leaderboard.md`, `docs/index.html`).

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
