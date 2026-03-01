from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.runner import (
    BenchmarkConfig,
    DEFAULT_MODELS,
    run_benchmark,
    run_sanity_check,
    write_leaderboard,
)


def _parse_models(raw: str) -> list[str]:
    if raw.strip().lower() == "default":
        return list(DEFAULT_MODELS)
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise ValueError("No models provided. Use comma-separated model names or `default`.")
    return models


def cmd_setup(args: argparse.Namespace) -> int:
    models = _parse_models(args.models)
    client = OllamaClient()

    status = client.ensure_server_running(auto_start=True)
    print(status.message)
    if not status.reachable:
        return 1

    if args.skip_pull:
        print("Skipping model pulls (--skip-pull).")
        return 0

    print(f"Ensuring {len(models)} model(s) are available locally...")
    try:
        pulled = client.ensure_models(models)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    if pulled:
        print("Pulled models:")
        for model in pulled:
            print(f"- {model}")
    else:
        print("All requested models are already present.")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    models = _parse_models(args.models)
    if args.max_turns < 1:
        print("--max-turns must be >= 1")
        return 1
    if args.tasks and args.suite:
        print("--tasks provided; ignoring --suite for task selection.")

    client = OllamaClient(timeout_seconds=args.timeout)
    status = client.ensure_server_running(auto_start=False)
    if not status.reachable:
        print(status.message)
        print("Run `python -m mentor_worker_benchmark setup` first.")
        return 1

    if not args.skip_model_check:
        local_models = client.list_local_models()
        missing = [model for model in models if model not in local_models]
        if missing:
            print("Missing models: " + ", ".join(missing))
            print("Run `python -m mentor_worker_benchmark setup` to pull them.")
            return 1

    config = BenchmarkConfig(
        models=models,
        max_turns=args.max_turns,
        task_pack=args.task_pack,
        suite=args.suite,
        task_selector=args.tasks,
        seed=args.seed,
        results_path=Path(args.results_path),
    )

    try:
        results = run_benchmark(config, client=client)
    except ValueError as exc:
        print(str(exc))
        return 1

    print(f"Completed {results['summary']['total_runs']} runs.")
    print(f"Results JSON: {config.results_path}")
    print(f"Leaderboard: {config.results_path.parent / 'leaderboard.md'}")
    return 0


def cmd_sanity(args: argparse.Namespace) -> int:
    if args.tasks and args.suite:
        print("--tasks provided; ignoring --suite for task selection.")
    try:
        summary = run_sanity_check(
            task_pack=args.task_pack,
            suite=args.suite,
            task_selector=args.tasks,
            seed=args.seed,
        )
    except ValueError as exc:
        print(str(exc))
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(
        f"Sanity checked {summary['task_count']} tasks from `{summary['task_pack']}` "
        f"(suite={summary['suite']})."
    )
    print(
        f"Expected failures: {summary['expected_failures']}, "
        f"unexpected passes: {summary['unexpected_passes']}, "
        f"broken harness tasks: {summary['broken_tasks']}"
    )
    print(f"Wall time: {summary['wall_time_seconds']}s")
    return 0 if summary["unexpected_passes"] == 0 and summary["broken_tasks"] == 0 else 1


def cmd_leaderboard(args: argparse.Namespace) -> int:
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        return 1

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    output = Path(args.output)
    write_leaderboard(payload, output)
    print(f"Leaderboard written to: {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mentor-worker-benchmark",
        description="Benchmark local mentor/worker LLM collaboration over objective coding tasks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Verify Ollama and pull required models.")
    setup.add_argument("--models", default="default", help="Comma-separated model list or `default`.")
    setup.add_argument("--skip-pull", action="store_true", help="Skip `ollama pull` checks.")
    setup.set_defaults(func=cmd_setup)

    run = subparsers.add_parser("run", help="Run baseline and mentored benchmark suites.")
    run.add_argument("--models", default="default", help="Comma-separated model list or `default`.")
    run.add_argument("--max-turns", type=int, default=4)
    run.add_argument("--task-pack", default="task_pack_v1")
    run.add_argument("--suite", choices=["quick", "dev", "test", "all"], default=None)
    run.add_argument(
        "--tasks",
        default=None,
        help="Legacy explicit selector: all, quick, or comma-separated task ids. Overrides --suite.",
    )
    run.add_argument("--seed", type=int, default=1337)
    run.add_argument("--results-path", default="results/results.json")
    run.add_argument("--timeout", type=int, default=180)
    run.add_argument(
        "--skip-model-check",
        action="store_true",
        help="Skip local model presence check (advanced).",
    )
    run.set_defaults(func=cmd_run)

    sanity = subparsers.add_parser(
        "sanity",
        help="Run pytest sanity checks on task starters (no model interaction).",
    )
    sanity.add_argument("--task-pack", default="task_pack_v1")
    sanity.add_argument("--suite", choices=["quick", "dev", "test", "all"], default="all")
    sanity.add_argument(
        "--tasks",
        default=None,
        help="Legacy explicit selector: all, quick, or comma-separated task ids. Overrides --suite.",
    )
    sanity.add_argument("--seed", type=int, default=1337)
    sanity.set_defaults(func=cmd_sanity)

    leaderboard = subparsers.add_parser("leaderboard", help="Render leaderboard markdown from JSON results.")
    leaderboard.add_argument("--results", default="results/results.json")
    leaderboard.add_argument("--output", default="results/leaderboard.md")
    leaderboard.set_defaults(func=cmd_leaderboard)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = args.func(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])
