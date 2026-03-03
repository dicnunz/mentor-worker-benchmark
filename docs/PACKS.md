# Task Packs: Data Card + Submission Guide

This benchmark supports:

- built-in packs resolved through `mentor_worker_benchmark/packs/registry.json`
- external packs loaded with `--task-pack-path /path/to/pack`

Default built-in packs are unchanged. External packs must pass the same validation gates before selection.

## Registry Data Card Fields

Each registry entry should include:

- `pack_id`
- `version`
- `task_count`
- `splits`
- `categories`
- `generator_commit`
- `license`
- `intended_use`
- `limitations`
- `contamination_risks`
- `evaluation_recommendations`

## External Pack Directory Layout

Expected minimum layout:

```text
my_pack/
  metadata.json
  tasks/
    <task_id>/
      prompt.md
      src/
        __init__.py
        solution.py
      tests/
        test_solution.py
```

`metadata.json` must include the standard task-pack fields (`pack_name`, `pack_version`, `counts`, `categories`, `tasks`) and a non-empty `license`.

## Safety + Reproducibility Rules

When loading `--task-pack-path`:

- pack metadata/tasks are validated with the same task-pack validation gates.
- task paths must stay inside the pack root (no traversal/out-of-root paths).
- a deterministic pack hash is computed as SHA256 over:
  - `metadata.json` bytes
  - all task file contents listed under task paths

The pack hash is recorded into run results and exported submission manifests.

## Data Card Template

Use this template when proposing a new pack for registry inclusion:

```md
# <pack_id> Data Card

- Version:
- License:
- Generator commit:
- Task count:
- Splits: train/dev/test/quick
- Categories:

## Intended Use

## Limitations

## Contamination Risks

## Evaluation Recommendations
```

## Submission Guidance

1. Validate pack metadata/tasks locally.
2. Run benchmark with either:
   - `--task-pack <registered_pack_id>`, or
   - `--task-pack-path /abs/path/to/pack`.
3. Export results with `python -m mentor_worker_benchmark export ...`.
4. Include pack data card details with the submission (license and intended use are required).
