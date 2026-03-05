# Methodology

## Benchmark Question

Primary question:

> Given the same task and worker model, does adding a mentor that can only provide natural-language guidance increase task pass rate relative to worker-only execution?

## Threat Model and Scoring

- The worker is the only actor allowed to emit code changes.
- The mentor is constrained to high-level natural language guidance; code-like output is blocked/sanitized and logged as a violation.
- The worker output must be a unified diff patch applied inside an isolated task workspace.
- The worker sees the task prompt, local workspace snapshot, failing `pytest` output, and test files.
- No internet access is allowed during execution.
- Task outcome is objective: the bundled `pytest` suite is the evaluation oracle.

Construct note:

- This benchmark measures deterministic, test-driven repair ability under a visible local test oracle.

Scored modes include:

- `worker_only` (baseline)
- `mentor_worker` (treatment)
- `mentor_only_suggestion_noise` (control)

For a fixed configuration, pass rate is:

- `pass_rate(mode) = passed_tasks / total_tasks`

Improvement ("lift") is:

- `lift = pass_rate(mentor_worker) - pass_rate(worker_only)`

Positive lift means mentorship improved pass rate for the same worker setup.

## Protocols

### Suites

Supported suites:

- `quick`, `dev10`, `dev50`, `dev`, `test`, `all`

Official headline suites are `dev`, `dev50`, and `test`.  
Official sanity suites are `quick` and `dev10` (harness-health checks, not headline claims).

### Multi-Seed Protocol

Official headline protocol uses deterministic seeds:

- `1337`, `2026`, `9001`

Each seed is a replicate under one deterministic run group id.

### Confidence Intervals and Significance

Analysis (`python -m mentor_worker_benchmark analyze`) reports:

- Per-group replicate pass rates
- Mean pass rates across replicates
- 95% bootstrap confidence intervals
- Lift confidence interval and a `lift_significant` flag

Current CI method label:

- `bootstrap_percentile_95_task_family_within_replicate_pooled`

Paired significance method label:

- `paired_bootstrap_over_task_families`

Bootstrap is deterministic; seed provenance is stored (`bootstrap_samples`, `bootstrap_seed`, per-group derived seeds).
When exact duplicate task families exist in the source corpus, resampling is performed at the task-family level rather than the raw task row level to avoid inflated effective sample size.

### Determinism Guarantees

Given identical inputs (task pack contents, config, seeds, code revision), the benchmark aims to produce identical outputs by:

- deterministic task ordering and seed handling,
- reproducibility mode (`--repro`) with fixed generation settings,
- deterministic replicate grouping and analysis seeding,
- explicit environment/protocol metadata capture in results and exported bundles.

## Failure Accounting and Interpretation

Results include explicit failure accounting:

- total failed runs,
- model-call errors and timeouts by mode,
- total model-call errors/timeouts.

Failures and timeouts count as non-passing outcomes.  
Interpretation should always include both pass-rate/lift and failure diagnostics; a high error/timeout regime can make comparisons less informative even when aggregate pass-rate differences appear large.

Compute budget metadata is recorded per run/export:

- `max_turns`
- `timeout_seconds`
- `total_model_calls_attempted`
- `total_tokens_estimate` (or `"unavailable"`)
- `total_wall_time_seconds`

## Test Strength Gates

Task-pack validation computes per-task strength indicators:

- assertion count (AST heuristic),
- edge-case keyword coverage,
- multi-file interaction signal,
- negative-test presence.

A 0-100 strength score is produced and included in validation reports.

Validation also runs a deterministic counterexample mutation gate:

- run tests on starter code,
- apply a deterministic wrong patch to likely target logic,
- require tests to fail on that wrong patch in strict mode.

Strict validation policies enforce:

- bounded low-strength fraction,
- bounded mutation-skip fraction,
- mutation-not-caught failures (with explicit allowlist support for grandfathered tasks).

What these gates do not guarantee:

- They are not full mutation testing.
- They reduce obvious weak-test/trivial-task failure modes but do not prove exhaustive behavioral coverage.

## Pack Registry, External Packs, and Contamination

For `task_pack_v2`, the active release pack contains `473` exact-family-independent tasks selected from a `652`-task generated source corpus. The source corpus audit detected `38` exact duplicate families; split hardening removes those duplicates from the active evaluation corpus by keeping one representative per exact family.

Built-in packs are declared in `mentor_worker_benchmark/packs/registry.json` with data-card fields (license, intended use, limitations, contamination risks, recommendations).

Pack selection supports:

- registry ids via `--task-pack <id>`
- backward-compatible legacy module aliases
- external packs via `--task-pack-path /path/to/pack`

External packs must:

- pass the same validation gates,
- declare a license in `metadata.json`,
- produce a deterministic pack hash (SHA256 over manifest + task files).

Pack hash is recorded in results/exports for reproducibility and dispute resolution.

Contamination remains a limitation:

- task generation is synthetic, but overlap with pretraining patterns cannot be fully excluded;
- claims should be bounded to measured benchmark behavior and not over-generalized to all software engineering tasks.
- the task corpus, tests, and exported submission bundles are open, so leaderboard-specific overfitting is possible and headline numbers should not be interpreted as hidden-holdout estimates.
