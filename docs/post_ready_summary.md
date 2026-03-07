# Post-Ready Benchmark Snapshot

Generated from `leaderboard/summary.json`: `2026-03-07T16:23:17+00:00`

Verified submissions: `9` total (`4` official, `5` community).

## What This Measures

- `mentor-worker-benchmark` measures whether a mentor model improves a worker model on deterministic local Python repair tasks scored by bundled `pytest` tests.
- The key outputs are worker-only baseline pass rate, mentored pass rate, paired lift, and model-call reliability (errors/timeouts).

## Current Snapshot

- Top baseline: `20.00%` from `official_dev10_signal_qwen25coder7b_phi3mini_2026-03-06` (dev10, worker `qwen2.5-coder:7b`, errors `0`, timeouts `0`).
- Best mentor lift: `+3.33%` from `community_quick_signal_qwen25coder7b_llama318b_2026-03-03` (quick, worker `qwen2.5-coder:7b`, mentor `llama3.1:8b`, baseline `16.67%`, mentored `20.00%`).
- Most reliable run: `official_dev50_signal_qwen_llama` (dev50, `100` total runs, errors `0`, timeouts `0`, worker `qwen2.5-coder:7b`).

## Headline Official Baseline

- Current headline official row: `official_dev50_signal_qwen_llama` (dev50, baseline `0.00%`, mentored `0.00%`, lift `+0.00%`).

## Honest Limitation

- Local `quick` and `dev10` health verification is useful for checking benchmark behavior and low-error execution on this machine, but it is not the same thing as a full headline publication run on `dev`, `dev50`, or `test`.

