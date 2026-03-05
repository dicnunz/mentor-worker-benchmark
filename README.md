# mentor-worker-benchmark

[![CI](https://github.com/dicnunz/mentor-worker-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/dicnunz/mentor-worker-benchmark/actions/workflows/ci.yml)
[![GitHub Pages](https://img.shields.io/website?down_color=lightgrey&down_message=down&label=pages&up_color=brightgreen&up_message=live&url=https%3A%2F%2Fdicnunz.github.io%2Fmentor-worker-benchmark%2F)](https://dicnunz.github.io/mentor-worker-benchmark/)

`mentor-worker-benchmark` is a fully local benchmark for measuring whether a **mentor LLM** improves a **worker LLM** on deterministic, objectively scored coding tasks.

Core docs:
- [Live Leaderboard](https://dicnunz.github.io/mentor-worker-benchmark/)
- [Methodology](docs/METHODOLOGY.md)
- [Reproducibility](docs/reproducibility.md)
- [Submit Results](docs/SUBMIT_RESULTS.md)
- [Pack Data Cards](docs/PACKS.md)

- Inference is local via [Ollama](https://ollama.com/) (no paid APIs required).
- Scoring is objective: generated patches are applied, then `pytest` decides pass/fail.
- Outputs are reproducible artifacts (`results.json`, markdown leaderboard, optional static docs page).

## Motivation

Many “AI collaboration” evaluations are hard to verify and easy to game. This project tests a narrower, auditable question:

> When a mentor can only send natural-language guidance, does the worker solve more tasks than the worker alone?

The benchmark includes controls and ablations (baseline worker-only and dummy-mentor control), plus guardrails against mentor cheating and unsafe patches.

## Benchmark Construct

- The worker sees the task prompt, a workspace snapshot, failing `pytest` output, and test files.
- The benchmark therefore measures **test-driven repair ability**, not blind synthesis from a hidden oracle.
- Tasks are deterministic local Python repair tasks.
- No internet access is allowed or required during execution.
- The evaluation oracle is the local `pytest` suite bundled with each task.

## What It Measures (And What It Doesn’t)

What it measures:
- Task success rate on deterministic Python repair tasks scored by unit tests.
- Mentorship lift: mentored pass rate minus worker-only baseline.
- Control performance with non-informative mentor advice.
- Mentor constraint violation rate.

What it does not measure:
- Open-ended coding quality beyond test coverage.
- Subjective style or readability judgments.
- Real-world long-horizon software engineering workflows.

Open-benchmark limitation:
- The task corpus, tests, and submission bundles are public, so leaderboard overfitting is possible. Treat leaderboard results as transparent benchmark behavior on an open corpus, not as performance on a hidden holdout.

## Task Pack and Splits

Default pack: `task_pack_v2` (mini-repo realism).

`task_pack_v2` contains `473` active deterministic tasks after exact-family deduplication for split independence.

Source provenance:
- `652` source tasks were generated and audited.
- `38` exact duplicate families were detected in the source corpus.
- The active release keeps one representative per exact family.

Categories:

1. `string_regex_parsing`
2. `ds_algo`
3. `file_io_serialization`
4. `concurrency_basics`
5. `numerical_edge_cases`
6. `multi_file_mini_module`
7. `mini_repo_bugfix`
8. `mini_repo_feature`
9. `mini_repo_cli`
10. `mini_repo_tool_sim`

Splits:
- `train`: 265
- `dev`: 104
- `test`: 104
- `quick`: 30 curated eval tasks (balanced fast profile)

Default benchmark behavior runs `dev+test` unless overridden.
`task_pack_v1` is still available via `--task-pack task_pack_v1`.

Why v2 is more realistic:
- Tasks include multi-module interactions and integration-style failures.
- CLI behavior and tool-output parsing patterns mimic real local workflows.
- Worker context now includes a concise file tree plus size-limited file excerpts.

## Install

Python 3.11+ is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.lock
```

## Local Setup (Ollama)

```bash
python -m mentor_worker_benchmark setup
```

Default models (pulled if missing):
- `llama3.1:8b`
- `qwen2.5-coder:7b`
- `mistral:7b`
- `phi3:mini`
- `gemma2:9b`

If Ollama is installed but not running, start it with the desktop app or:

```bash
ollama serve
```

## Reproducible Run (Recommended)

Run quick suite in reproducibility mode:

```bash
python -m mentor_worker_benchmark run \
  --task-pack task_pack_v2 \
  --suite quick \
  --models phi3:mini \
  --run-modes worker_only,mentor_worker \
  --repro \
  --max-turns 3 \
  --timeout 180 \
  --worker-num-predict 512 \
  --mentor-num-predict 256 \
  --seed 1337 \
  --results-path results/results.json
```

`--repro` fixes key generation/runtime settings (temperature, top_p, seeds, max tokens, max turns).

## Run With OpenAI SOTA Models

You can run remote models by switching provider(s) from the default `ollama` to `openai`.

Requirements:
- Set `OPENAI_API_KEY` in your environment.
- Pick explicit model names (for example `gpt-5`, `gpt-5-mini`, `o4-mini`) using role flags.

Examples:

```bash
# Use OpenAI for both mentor and worker.
python -m mentor_worker_benchmark run \
  --provider openai \
  --mentor-model gpt-5 \
  --worker-model gpt-5-mini \
  --suite quick \
  --run-modes worker_only,mentor_worker \
  --repro \
  --max-turns 3 \
  --timeout 180 \
  --worker-num-predict 512 \
  --mentor-num-predict 256
```

```bash
# Hybrid run: local worker via Ollama, remote mentor via OpenAI.
python -m mentor_worker_benchmark run \
  --provider ollama \
  --mentor-provider openai \
  --worker-provider ollama \
  --mentor-model gpt-5 \
  --worker-model phi3:mini \
  --suite quick \
  --run-modes worker_only,mentor_worker \
  --repro \
  --max-turns 3 \
  --timeout 180 \
  --worker-num-predict 512 \
  --mentor-num-predict 256
```

```bash
# Optional reasoning hint for supported OpenAI models.
python -m mentor_worker_benchmark run \
  --provider openai \
  --mentor-model gpt-5 \
  --worker-model gpt-5-mini \
  --reasoning-level medium
```

Warning:
- OpenAI runs are not free. You are responsible for API cost and rate limits.
- Large suites can trigger throttling; start with `--suite quick` and the reproducible quick profile shown above.

## Official Suites

Standardized scripts (macOS/Linux):

```bash
./scripts/run_official_quick.sh
./scripts/run_official_dev.sh
./scripts/run_official_dev_v1.sh
```

`run_official_dev_v1.sh` accepts `TASK_SUITE=dev|dev50|test` (default `dev50`).

Each script runs a fixed-suite benchmark configuration, exports a submission bundle, and verifies it.
Headline policy:
- Headline official baseline numbers come from `dev`/`dev50`/`test` suites.
- Official `dev10`/`quick` runs are sanity checks for harness health and error-rate visibility, not headline performance claims.
- Headline suites run three deterministic seeds by default: `1337`, `2026`, `9001`.

## How To Interpret Headline Numbers

- Headline `Baseline`, `Mentored`, and `Lift` are multi-seed means (not single-point pass rates).
- Confidence intervals are 95% bootstrap CIs computed deterministically from task-family outcomes.
- A `sig` lift marker means the 95% lift CI excludes `0`.
- Sanity suites (`quick`/`dev10`) remain harness-health checks, not headline claims.

## Sanity Check (No Model Calls)

Validate task harness and starters without Ollama:

```bash
python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite quick --seed 1337
python -m mentor_worker_benchmark sanity --task-pack task_pack_v2 --suite quick --seed 1337
python -m mentor_worker_benchmark.tasks.task_pack_v1.validate
python -m mentor_worker_benchmark.tasks.task_pack_v2.validate
python -m mentor_worker_benchmark provenance --task-pack task_pack_v2
```

## CLI

```bash
python -m mentor_worker_benchmark setup [--models default|m1,m2] [--skip-pull]
python -m mentor_worker_benchmark run [--task-pack task_pack_v2|task_pack_v1] [--suite quick|dev10|dev50|dev|test|all] [--seed 1337|--seeds 1337,2026,9001] [--repro] [--debug]
python -m mentor_worker_benchmark run --task-pack-path /abs/path/to/pack --suite dev
python -m mentor_worker_benchmark sanity [--task-pack task_pack_v2|task_pack_v1] [--suite quick|dev10|dev50|dev|test|all]
python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md
python -m mentor_worker_benchmark compare --before before.json --after after.json
python -m mentor_worker_benchmark analyze --results results/results.json --out results/analysis.json
python -m mentor_worker_benchmark export --results results/results.json --out submissions/<name>.zip [--official]
python -m mentor_worker_benchmark verify --submission submissions/<name>.zip
python -m mentor_worker_benchmark curate --task-pack task_pack_v1 --seed 1337
python -m mentor_worker_benchmark provenance --task-pack task_pack_v2 [--fail-on-overlap]
```

Convenience:

```bash
make setup
make quick
```

## Example Leaderboard Snippet

```md
## Best Mentors
| Mentor | Avg Lift | Mentored Pass Rate | Violation Rate |
| --- | --- | --- | --- |
| phi3:mini | 0.00% | 0.00% | 0.00% |

## Best Workers
| Worker | Baseline | Mentored | Control | Lift |
| --- | --- | --- | --- | --- |
| phi3:mini | 0.00% | 0.00% | 0.00% | 0.00% |
```

Generated files:
- `results/results.json`
- `results/analysis.json` (from `analyze`, or bundled automatically during `export`)
- `results/leaderboard.md`
- `docs/index.html` (optional GitHub Pages view)

## How To Submit Results

1. Run an official suite (`./scripts/run_official_quick.sh` or `./scripts/run_official_dev.sh`).
2. If needed, manually export:

```bash
python -m mentor_worker_benchmark export \
  --results results/results.json \
  --out submissions/my_run.zip
```

3. Verify your bundle:

```bash
python -m mentor_worker_benchmark verify --submission submissions/my_run.zip
```

4. Open a submission issue and attach/link the zip.

Submission details and maintainer verification flow are documented in `docs/SUBMIT_RESULTS.md`.
Pack registry/data-card guidance is documented in `docs/PACKS.md`.

## Community Leaderboard Automation

Repository structure:
- `submissions/`: tracked submission bundles (`.zip`).
- `leaderboard/submissions/`: normalized per-submission JSON extracted from verified bundles.
- `leaderboard/summary.json`: aggregated view used by docs.

Automation:
- PRs touching `submissions/` trigger `.github/workflows/submissions-pr.yml`.
- CI verifies each changed submission zip.
- CI regenerates `leaderboard/summary.json`, `docs/leaderboard.md`, and `docs/index.html`.
- For same-repo PRs, CI auto-commits refreshed artifacts back to the PR branch.

`docs/index.html` now includes:
- headline official baselines plus official sanity runs,
- pack filter (`task_pack_v1` / `task_pack_v2`),
- suite filter (`quick` / `dev10` / `dev50` / `dev` / `test`),
- explicit `community (not official)` labeling.

## Official Baselines

Merged official baseline submissions:
- [official_dev_v1_m3air_2026-03-01.zip](submissions/official_dev_v1_m3air_2026-03-01.zip) (dev50 headline baseline)
- [official_dev_sanity_2026-03-01.zip](submissions/official_dev_sanity_2026-03-01.zip) (`dev10` sanity run; harness-health only, not headline)
- [official_quick_m3air_2026-03-01.zip](submissions/official_quick_m3air_2026-03-01.zip) (from [PR #1](https://github.com/dicnunz/mentor-worker-benchmark/pull/1))
- [official_quick_expanded_m3air_2026-03-01.zip](submissions/official_quick_expanded_m3air_2026-03-01.zip) (from [PR #2](https://github.com/dicnunz/mentor-worker-benchmark/pull/2))

## Lightweight Leaderboard Publishing

Generate markdown + static HTML:

```bash
python scripts/publish_leaderboard.py \
  --results results/results.json \
  --markdown-out results/leaderboard.md \
  --html-out docs/single_run.html
```

Enable GitHub Pages (repo settings):
1. Open **Settings → Pages**.
2. Set **Source** to “Deploy from a branch”.
3. Select `main` branch and `/docs` folder.
4. Save. GitHub publishes `docs/index.html` (community leaderboard).

Regenerate community artifacts from tracked `submissions/*.zip`:

```bash
python scripts/build_community_leaderboard.py --strict
```

## Methodology Guardrails

- Mentor can only send natural-language guidance; code-like mentor output is blocked/sanitized and logged.
- Worker must return a unified diff patch; patch format and paths are validated.
- Patch application forbids traversal outside the task workspace.
- Tests run in isolated temp directories with per-task timeout and network disabled.
- Run metadata logs environment and provenance (Python, platform, Ollama version/model tags, git commit hash).

## Compute Budget

Each run writes a `compute_budget` manifest in `results.json` and in exported `submission_manifest.json`:

- `max_turns`
- `timeout_seconds`
- `total_model_calls_attempted`
- `total_tokens_estimate` (or explicit `"unavailable"`)
- `total_wall_time_seconds`

## Test Strength Gates

Task-pack validation now includes deterministic test-strength gates to make results harder to game:

- Static test strength heuristics per task:
  - assertion count (AST-based),
  - edge-case keyword coverage,
  - negative-test presence (e.g., exception expectations),
  - multi-file interaction signal from test/source imports.
- Counterexample mutation harness:
  - runs tests on the starter task workspace,
  - applies a deterministic wrong patch to the likely target module/function,
  - verifies tests fail on the wrong patch.
- Strict mode (`--strict`) fails validation when:
  - too many tasks are mutation-skipped,
  - non-allowlisted tasks do not fail under the wrong patch,
  - low-strength scores exceed conservative policy thresholds.

Allowlists live in each pack (`strength_allowlist.json`) to explicitly grandfather legacy tasks while keeping strict checks transparent.

What this does **not** guarantee:
- It is not a full mutation-testing framework and does not prove complete behavioral coverage.
- It reduces obvious weak-test/trivial-task failure modes but cannot eliminate every possible benchmark gaming path.

## Provenance & Limitations

`task_pack_v2` includes generated provenance artifacts:
- `mentor_worker_benchmark/tasks/task_pack_v2/provenance.json`
- `mentor_worker_benchmark/tasks/task_pack_v2/PROVENANCE.md`

They are generated by in-repo scripts and include:
- Generator version, git commit hash, and seed.
- A contamination-risk checklist with explicit did/did-not-do statements.
- Intra-pack overlap scan (hashed token/char n-gram cosine on prompt+tests).
- Originality marker scan for obvious external-source references in task files.

Regenerate and re-check:

```bash
python -m mentor_worker_benchmark provenance --task-pack task_pack_v2
```

No-overclaim policy:
- See `docs/benchmark_policy.md` for allowed/disallowed claims and responsible citation guidance.
- We intentionally do **not** claim zero contamination risk; models may have seen similar patterns during pretraining.

## Cite / Reference

Use this short reference when citing the benchmark:

```text
dicnunz. mentor-worker-benchmark: Local benchmark for mentor-worker LLM collaboration on objective coding tasks. GitHub repository, 2026. https://github.com/dicnunz/mentor-worker-benchmark
```

BibTeX:

```bibtex
@misc{dicnunz_mentor_worker_benchmark_2026,
  author = {dicnunz},
  title = {mentor-worker-benchmark: Local benchmark for mentor-worker LLM collaboration on objective coding tasks},
  year = {2026},
  howpublished = {\url{https://github.com/dicnunz/mentor-worker-benchmark}},
  note = {Accessed: 2026-03-01}
}
```

## Quality Gates

`task_pack_v1` includes an automated curation pipeline used to keep the base 300-task corpus credible before composing v2.

Run:

```bash
python -m mentor_worker_benchmark curate --task-pack task_pack_v1 --seed 1337
```

What `curate` does:
- Detects near-duplicates using hashed token/character n-gram cosine similarity.
- Flags trivial tasks (low test depth, short starter code, and phi3 one-turn pass checks).
- Flags ambiguity (missing explicit prompt I/O examples, weak edge-case/invalid-input test coverage).
- Rebalances difficulty to target distribution (`easy 35%`, `medium 45%`, `hard 20%`) with DEV calibration.
- Runs DEV one-turn worker-only calibration on `phi3:mini` and `qwen2.5-coder:7b` before/after.
- Regenerates flagged tasks deterministically while preserving category/split and exact split counts.

Curation artifacts:
- `results/curation_report.json`
- `results/curation_report.md`

## Adding or Updating Tasks

See [CONTRIBUTING.md](CONTRIBUTING.md) for task authoring standards, split rules, and validation commands.

## License

MIT ([LICENSE](LICENSE))

All benchmark task content under `mentor_worker_benchmark/tasks/task_pack_v1` and
`mentor_worker_benchmark/tasks/task_pack_v2` is synthetic in-repo content and is MIT-licensed as part of this repository.
