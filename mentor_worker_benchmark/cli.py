from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mentor_worker_benchmark.ollama_client import OllamaClient
from mentor_worker_benchmark.runner import (
    BenchmarkConfig,
    DEFAULT_MODELS,
    DEFAULT_RUN_MODES,
    REPRO_MAX_TURNS,
    compare_results,
    render_compare_report,
    run_benchmark,
    run_sanity_check,
    write_leaderboard,
)
from mentor_worker_benchmark.submission import (
    export_submission_bundle,
    render_verification_report,
    verify_submission_bundle,
)
from mentor_worker_benchmark.tasks.task_pack_v1.curate import CurationConfig, run_curation
from mentor_worker_benchmark.tasks.task_pack_v2.provenance import (
    DEFAULT_MAX_CLUSTERS,
    DEFAULT_SIMILARITY_THRESHOLD,
    write_provenance_artifacts,
)


def _parse_models(raw: str) -> list[str]:
    if raw.strip().lower() == "default":
        return list(DEFAULT_MODELS)
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise ValueError("No models provided. Use comma-separated model names or `default`.")
    return models


def _parse_run_modes(raw: str) -> tuple[str, ...]:
    if not raw.strip():
        return tuple(DEFAULT_RUN_MODES)
    if raw.strip().lower() == "default":
        return tuple(DEFAULT_RUN_MODES)

    entries = [token.strip() for token in raw.split(",") if token.strip()]
    if not entries:
        return tuple(DEFAULT_RUN_MODES)
    return tuple(entries)


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
    run_modes = _parse_run_modes(args.run_modes)

    if args.max_turns < 1:
        print("--max-turns must be >= 1")
        return 1
    if args.tasks and args.suite:
        print("--tasks provided; ignoring --suite for task selection.")
    if args.repro and args.max_turns != REPRO_MAX_TURNS:
        print(f"Repro mode enabled: overriding max turns to fixed value {REPRO_MAX_TURNS}.")

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
        run_modes=run_modes,
        repro_mode=args.repro,
        stronger_worker_model=args.stronger_worker_model,
    )

    try:
        results = run_benchmark(config, client=client)
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1

    print(f"Completed {results['summary']['total_runs']} runs.")
    print("Runs by mode:")
    for mode, count in sorted(results["summary"]["runs_by_mode"].items()):
        print(f"- {mode}: {count}")
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


def cmd_compare(args: argparse.Namespace) -> int:
    before_path = Path(args.before)
    after_path = Path(args.after)
    if not before_path.exists():
        print(f"Before results file not found: {before_path}")
        return 1
    if not after_path.exists():
        print(f"After results file not found: {after_path}")
        return 1

    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))

    comparison = compare_results(before, after)
    report = render_compare_report(comparison)
    print(report)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    try:
        manifest = export_submission_bundle(
            results_path=Path(args.results),
            out_path=Path(args.out),
            cli_command=args.command,
            official_submission=args.official,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Submission bundle written: {args.out}")
    print(f"Task pack: {manifest['task_pack']} ({manifest['task_pack_version']})")
    print(f"Commit: {manifest['git_commit_hash']}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    report = verify_submission_bundle(Path(args.submission))
    print(render_verification_report(report))
    return 0 if report.get("ok") else 1


def cmd_curate(args: argparse.Namespace) -> int:
    config = CurationConfig(
        task_pack=args.task_pack,
        seed=args.seed,
        similarity_threshold=args.similarity_threshold,
        triviality_sample_size=args.triviality_sample_size,
        full_triviality_model_check=args.full_triviality_model_check,
        max_replacement_attempts=args.max_replacement_attempts,
        results_dir=Path(args.results_dir),
        worker_num_predict=args.worker_num_predict,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
    )

    try:
        payload = run_curation(config)
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 1

    print(
        f"Curation finished: replaced {payload['replacements']['count']} tasks. "
        f"Duplicate clusters {payload['duplicates']['cluster_count_before']} -> "
        f"{payload['duplicates']['cluster_count_after']}."
    )
    print(f"Report JSON: {config.results_dir / 'curation_report.json'}")
    print(f"Report Markdown: {config.results_dir / 'curation_report.md'}")
    return 0


def cmd_provenance(args: argparse.Namespace) -> int:
    if args.task_pack != "task_pack_v2":
        print("`provenance` currently supports only --task-pack task_pack_v2.")
        return 1

    try:
        payload = write_provenance_artifacts(
            seed=args.seed,
            similarity_threshold=args.similarity_threshold,
            max_clusters=args.max_clusters,
        )
    except RuntimeError as exc:
        print(str(exc))
        return 1

    similarity = payload["checks"]["similarity_scan"]
    originality = payload["checks"]["originality_scan"]
    print(
        f"Provenance updated for {payload['pack_name']} "
        f"(clusters={similarity['cluster_count']}, flagged_files={originality['flagged_files_count']})."
    )
    print("Artifacts:")
    print("- mentor_worker_benchmark/tasks/task_pack_v2/provenance.json")
    print("- mentor_worker_benchmark/tasks/task_pack_v2/PROVENANCE.md")

    if args.fail_on_overlap and int(similarity["cluster_count"]) > 0:
        print("Overlap clusters detected and --fail-on-overlap set.")
        return 1
    if int(originality["flagged_files_count"]) > 0:
        print("Originality marker scan found potential external references.")
        return 1
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

    run = subparsers.add_parser("run", help="Run benchmark suites and ablations.")
    run.add_argument("--models", default="default", help="Comma-separated model list or `default`.")
    run.add_argument("--max-turns", type=int, default=4)
    run.add_argument("--task-pack", default="task_pack_v2")
    run.add_argument("--suite", choices=["quick", "dev", "test", "all"], default=None)
    run.add_argument(
        "--tasks",
        default=None,
        help="Legacy explicit selector: all, quick, or comma-separated task ids. Overrides --suite.",
    )
    run.add_argument("--seed", type=int, default=1337)
    run.add_argument("--repro", action="store_true", help="Enable deterministic reproducibility mode.")
    run.add_argument(
        "--run-modes",
        default="default",
        help=(
            "Comma-separated run modes. "
            "Allowed: worker_only,mentor_worker,mentor_only_suggestion_noise,stronger_worker,mentor_swap"
        ),
    )
    run.add_argument(
        "--stronger-worker-model",
        default=None,
        help="Optional explicit stronger worker model to use when run mode includes stronger_worker.",
    )
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
    sanity.add_argument("--task-pack", default="task_pack_v2")
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

    compare = subparsers.add_parser("compare", help="Compare two results JSON files and report deltas.")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.set_defaults(func=cmd_compare)

    export = subparsers.add_parser("export", help="Export a standardized submission zip from results.json.")
    export.add_argument("--results", default="results/results.json")
    export.add_argument("--out", required=True)
    export.add_argument("--command", default=None, help="Optional explicit CLI command used for the run.")
    export.add_argument(
        "--official",
        action="store_true",
        help="Mark bundle as official (maintainer-approved standardized run).",
    )
    export.set_defaults(func=cmd_export)

    verify = subparsers.add_parser("verify", help="Verify a standardized submission zip.")
    verify.add_argument("--submission", required=True)
    verify.set_defaults(func=cmd_verify)

    curate = subparsers.add_parser(
        "curate",
        help="Run task-pack quality gates, regenerate flagged tasks, and emit curation reports.",
    )
    curate.add_argument("--task-pack", default="task_pack_v1")
    curate.add_argument("--seed", type=int, default=1337)
    curate.add_argument("--similarity-threshold", type=float, default=0.92)
    curate.add_argument("--triviality-sample-size", type=int, default=72)
    curate.add_argument("--full-triviality-model-check", action="store_true")
    curate.add_argument("--max-replacement-attempts", type=int, default=10)
    curate.add_argument("--worker-num-predict", type=int, default=220)
    curate.add_argument("--ollama-timeout-seconds", type=int, default=60)
    curate.add_argument("--results-dir", default="results")
    curate.set_defaults(func=cmd_curate)

    provenance = subparsers.add_parser(
        "provenance",
        help="Generate task_pack_v2 provenance manifest and overlap/originality checks.",
    )
    provenance.add_argument("--task-pack", default="task_pack_v2")
    provenance.add_argument("--seed", type=int, default=None)
    provenance.add_argument("--similarity-threshold", type=float, default=DEFAULT_SIMILARITY_THRESHOLD)
    provenance.add_argument("--max-clusters", type=int, default=DEFAULT_MAX_CLUSTERS)
    provenance.add_argument("--fail-on-overlap", action="store_true")
    provenance.set_defaults(func=cmd_provenance)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    exit_code = args.func(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main(sys.argv[1:])
