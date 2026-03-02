# Benchmark Claim Policy

This policy defines how to communicate `mentor-worker-benchmark` results without overclaiming.

## Scope

The benchmark measures local mentor/worker LLM behavior on synthetic, objective Python tasks scored by `pytest`.

It does not measure broad software engineering ability, product quality, or real-world deployment readiness.

## Allowed Claims

- "Model X achieved Y% pass rate on this benchmark configuration."
- "Mentor A improved Worker B by Z points over the worker-only baseline in this run."
- "In this offline setup, mentor guidance was associated with positive/negative lift."
- "Results are reproducible with the same task pack, seed, models, and repro settings."

## Disallowed Claims

- "State of the art."
- "General intelligence improvement."
- "Model X is best overall at coding."
- "Zero contamination risk."
- Any claim that extends these results to unrelated domains without new evidence.

## Responsible Reporting

- Always include:
  - task pack (`task_pack_v1` or `task_pack_v2`)
  - split/suite (`quick`, `dev10`, `dev50`, `dev`, `test`, `all`)
  - seed and repro mode status
  - run modes included (worker-only, mentor-worker, control)
  - model tags exactly as pulled from Ollama
- Report both baseline and mentored outcomes, plus lift and mentor violation rate.
- Cite contamination limitations from `task_pack_v2/PROVENANCE.md`.
- Prefer comparisons within the same environment and same commit hash.

## Official Baseline Policy

- Headline official baseline numbers should come from `dev`, `dev50`, or `test` suites.
- Official `dev10` and `quick` runs are sanity/harness-health checks.
- Do not present `dev10`/`quick` official runs as headline performance claims.

## Citation Template

Use language like:

> On commit `<hash>`, using `task_pack_v2` (`<suite>`, seed `<seed>`, repro mode `<on/off>`), Worker `<worker>` achieved `<baseline>%` in worker-only mode and `<mentored>%` with Mentor `<mentor>` (`lift <delta>%`, control `<control>%`).
