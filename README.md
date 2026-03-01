# mentor-worker-benchmark

`mentor-worker-benchmark` is a fully local benchmark for measuring whether a **mentor LLM** improves a **worker LLM** on objective coding tasks.

- Inference is local via [Ollama](https://ollama.com/) (no paid APIs required).
- Scoring is objective: generated patches are applied, then `pytest` decides pass/fail.
- Outputs are reproducible artifacts (`results.json`, markdown leaderboard, optional static docs page).

## Motivation

Many “AI collaboration” evaluations are hard to verify and easy to game. This project tests a narrower, auditable question:

> When a mentor can only send natural-language guidance, does the worker solve more tasks than the worker alone?

The benchmark includes controls and ablations (baseline worker-only and dummy-mentor control), plus guardrails against mentor cheating and unsafe patches.

## What It Measures (And What It Doesn’t)

What it measures:
- Task success rate on objective Python microtasks with unit tests.
- Mentorship lift: mentored pass rate minus worker-only baseline.
- Control performance with non-informative mentor advice.
- Mentor constraint violation rate.

What it does not measure:
- Open-ended coding quality beyond test coverage.
- Subjective style or readability judgments.
- Real-world long-horizon software engineering workflows.

## Task Pack and Splits

`task_pack_v1` contains 300 deterministic tasks across 6 categories:

1. `string_regex_parsing`
2. `ds_algo`
3. `file_io_serialization`
4. `concurrency_basics`
5. `numerical_edge_cases`
6. `multi_file_mini_module`

Splits:
- `train`: 200
- `dev`: 50
- `test`: 50
- `quick`: 18 balanced eval tasks

Default benchmark behavior runs `dev+test` unless overridden.

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
  --task-pack task_pack_v1 \
  --suite quick \
  --models phi3:mini \
  --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise \
  --repro \
  --seed 1337 \
  --results-path results/results.json
```

`--repro` fixes key generation/runtime settings (temperature, top_p, seeds, max tokens, max turns).

## Sanity Check (No Model Calls)

Validate task harness and starters without Ollama:

```bash
python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite quick --seed 1337
python -m mentor_worker_benchmark.tasks.task_pack_v1.validate
```

## CLI

```bash
python -m mentor_worker_benchmark setup [--models default|m1,m2] [--skip-pull]
python -m mentor_worker_benchmark run [--task-pack task_pack_v1] [--suite quick|dev|test|all] [--repro]
python -m mentor_worker_benchmark sanity [--task-pack task_pack_v1] [--suite quick|dev|test|all]
python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md
python -m mentor_worker_benchmark compare --before before.json --after after.json
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
- `results/leaderboard.md`
- `docs/index.html` (optional GitHub Pages view)

## Lightweight Leaderboard Publishing

Generate markdown + static HTML:

```bash
python scripts/publish_leaderboard.py \
  --results results/results.json \
  --markdown-out results/leaderboard.md \
  --html-out docs/index.html
```

Enable GitHub Pages (repo settings):
1. Open **Settings → Pages**.
2. Set **Source** to “Deploy from a branch”.
3. Select `main` branch and `/docs` folder.
4. Save. GitHub publishes `docs/index.html`.

## Methodology Guardrails

- Mentor can only send natural-language guidance; code-like mentor output is blocked/sanitized and logged.
- Worker must return a unified diff patch; patch format and paths are validated.
- Patch application forbids traversal outside the task workspace.
- Tests run in isolated temp directories with per-task timeout and network disabled.
- Run metadata logs environment and provenance (Python, platform, Ollama version/model tags, git commit hash).

## Adding or Updating Tasks

See [CONTRIBUTING.md](CONTRIBUTING.md) for task authoring standards, split rules, and validation commands.

## License

MIT ([LICENSE](LICENSE))
