# mentor-worker-benchmark

A fully local benchmark for evaluating whether a **mentor LLM** improves a **worker LLM** on objective coding tasks.

- Inference: [Ollama](https://ollama.com/) (local/free runtime)
- Scoring: objective `pytest` pass/fail only
- Task corpus: versioned/generated `task_pack_v1` (300 tasks)
- Artifacts:
  - `results/results.json`
  - `results/leaderboard.md`
  - `results/schema.md`

## Why this benchmark is harder to game

### Deterministic execution (repro mode)

`--repro` enforces fixed generation parameters and deterministic ordering:

- `temperature=0`
- `top_p=1`
- fixed seeded calls
- fixed max tokens (worker + mentor)
- fixed max turns (`2`)

The run artifact logs environment/provenance for reproducibility:

- Python version/executable
- platform info
- Ollama CLI version
- selected model tags from Ollama
- git commit + dirty state

### Stronger controls and ablations

Run modes:

- `worker_only` (baseline)
- `mentor_worker` (standard mentored loop)
- `mentor_only_suggestion_noise` (dummy mentor control)
- `stronger_worker` (adds larger local worker if available)
- `mentor_swap` (explicit mentor cross-worker matrix mode)

### Mentor anti-cheating guardrails

Mentor outputs are validated and filtered before the worker sees them.
Violations include:

- fenced code blocks (especially long blocks)
- unified diff markers
- file headers
- imports
- function/class definitions

On violation, the original output is blocked and replaced with short natural-language guidance.
Original violating output is logged under `violations` in `results.json` for auditability.

### Patch and runtime safety

- worker patch must be valid unified diff
- patch paths are checked for traversal/unsafe targets
- tests run in isolated temp dirs
- per-task pytest timeout enforced
- test subprocesses run with network disabled

## Task pack

`task_pack_v1` is deterministic and versioned.

- Total: `300` tasks
- Splits:
  - `train`: `200`
  - `dev`: `50`
  - `test`: `50`
- `quick`: `18` balanced eval tasks

Categories:

1. `string_regex_parsing`
2. `ds_algo`
3. `file_io_serialization`
4. `concurrency_basics`
5. `numerical_edge_cases`
6. `multi_file_mini_module`

Regenerate pack:

```bash
python -m mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack --seed 1337
```

## Setup

Python 3.11+ required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.lock
python -m mentor_worker_benchmark setup
```

Default model set:

- `llama3.1:8b`
- `qwen2.5-coder:7b`
- `mistral:7b`
- `phi3:mini`
- `gemma2:9b`

## Reproduce exactly (recommended)

Quick reproducible run:

```bash
python -m mentor_worker_benchmark run \
  --models phi3:mini \
  --task-pack task_pack_v1 \
  --suite quick \
  --repro \
  --seed 1337 \
  --run-modes worker_only,mentor_worker,mentor_only_suggestion_noise \
  --results-path results/results.json
```

Sanity-check all task starters (no model calls):

```bash
python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite all --seed 1337
```

## CLI

```bash
python -m mentor_worker_benchmark setup [--models default|m1,m2] [--skip-pull]
python -m mentor_worker_benchmark run [--suite quick|dev|test|all] [--repro] [--run-modes ...]
python -m mentor_worker_benchmark sanity [--suite quick|dev|test|all]
python -m mentor_worker_benchmark leaderboard --results results/results.json --output results/leaderboard.md
python -m mentor_worker_benchmark compare --before old.json --after new.json
```

## Reporting

`results/leaderboard.md` includes:

- Top mentors by average lift
- Top workers baseline vs mentored vs control
- Per-category breakdown
- Mentor/worker pair matrix with mentor violation rate

`results/schema.md` documents `results.json` fields.

## License

MIT
