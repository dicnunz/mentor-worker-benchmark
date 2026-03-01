# Contributing to mentor-worker-benchmark

Thanks for contributing. This project is benchmark infrastructure, so reproducibility and auditability are the top priorities.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.lock
```

## Local Validation Before PR

Run all of these before opening a PR:

```bash
python -m pytest tests -q
python -m mentor_worker_benchmark.tasks.task_pack_v1.validate
python -m mentor_worker_benchmark sanity --task-pack task_pack_v1 --suite quick --seed 1337
python -m mentor_worker_benchmark curate --task-pack task_pack_v1 --seed 1337
```

## Task Pack Contribution Rules

All benchmark tasks must remain objective and fast.

Task requirements:
- `prompt.md` with clear requirements and examples.
- starter implementation under `src/` that is incomplete or intentionally buggy.
- `pytest` tests under `tests/` with edge cases and deterministic expectations.

Task quality requirements:
- No subjective judging.
- No network dependency.
- Avoid flaky timing assumptions.
- Keep per-task runtime short.

Split policy for `task_pack_v1`:
- `train`: 200
- `dev`: 50
- `test`: 50
- `quick`: 18 balanced tasks across categories

If you edit generator logic or task definitions:

```bash
python -m mentor_worker_benchmark.tasks.task_pack_v1.generate_task_pack --seed 1337
python -m mentor_worker_benchmark.tasks.task_pack_v1.validate
```

## Benchmark Methodology Constraints

- Keep mentor-only guidance enforcement intact.
- Keep worker patch format enforcement (unified diff only).
- Keep patch safety checks (no path traversal/out-of-tree writes).
- Keep isolated test execution behavior.

Changes that weaken these constraints will not be accepted.

## Pull Request Checklist

- Add/update tests for any behavior change.
- Update docs (`README.md`, `results/schema.md`, etc.) when output formats or commands change.
- Keep CLI backward-compatible unless a breaking change is intentional and documented.
- Include a concise summary of methodological impact in the PR description.
