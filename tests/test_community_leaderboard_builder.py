from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.submission import export_submission_bundle


def _load_builder_module() -> Any:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "build_community_leaderboard.py"
    spec = importlib.util.spec_from_file_location("build_community_leaderboard", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _base_results_payload(*, suite: str) -> dict[str, Any]:
    return {
        "generated_at": "2026-03-01T00:00:00+00:00",
        "config": {
            "models": ["qwen2.5-coder:7b", "llama3.1:8b"],
            "worker_models": ["qwen2.5-coder:7b"],
            "run_modes": ["worker_only", "mentor_worker"],
            "repro_mode": True,
            "max_turns": 2,
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "worker_num_predict": 220,
                "mentor_num_predict": 120,
                "seed": 1337,
            },
            "task_pack": "task_pack_v2",
            "suite": suite,
            "selector_source": "suite",
            "task_selector": None,
            "task_count": 2,
            "stronger_worker_included": None,
            "stronger_worker_status": None,
        },
        "environment": {
            "benchmark_version": "0.1.0",
            "python": {"version": "3.11.0", "implementation": "CPython", "executable": "python"},
            "platform": {
                "platform": "macOS",
                "system": "Darwin",
                "release": "23.0",
                "machine": "arm64",
            },
            "ollama": {"base_url": "http://localhost:11434", "cli_version": "0.0.0", "model_tags": []},
            "git": {"commit": "de5a929", "dirty": False},
        },
        "summary": {
            "total_runs": 2,
            "runs_by_mode": {"worker_only": 1, "mentor_worker": 1},
            "benchmark_wall_time_seconds": 1.5,
            "violation_count": 0,
        },
        "runs": [
            {
                "mode": "worker_only",
                "task_id": "v2_string_regex_parsing_000",
                "worker_model": "qwen2.5-coder:7b",
                "mentor_model": None,
                "pass": True,
                "turns_used": 1,
                "wall_time_seconds": 0.5,
                "total_tokens_estimate": 120,
                "mentor_turn_count": 0,
                "mentor_violation_count": 0,
                "log": {},
            },
            {
                "mode": "mentor_worker",
                "task_id": "v2_ds_algo_001",
                "worker_model": "qwen2.5-coder:7b",
                "mentor_model": "llama3.1:8b",
                "pass": False,
                "turns_used": 1,
                "wall_time_seconds": 1.0,
                "total_tokens_estimate": 240,
                "mentor_turn_count": 1,
                "mentor_violation_count": 0,
                "log": {
                    "turns": [
                        {
                            "worker_error": "request timed out after 20s",
                            "mentor_error": "",
                        }
                    ]
                },
            },
        ],
        "violations": [],
        "aggregates": {
            "task_count": 2,
            "tasks": ["v2_string_regex_parsing_000", "v2_ds_algo_001"],
            "baseline_by_worker": {"qwen2.5-coder:7b": 0.5},
            "control_by_worker": {"qwen2.5-coder:7b": 0.0},
            "mentor_worker_pairs": [],
            "best_mentors": [],
            "best_workers": [
                {
                    "worker_model": "qwen2.5-coder:7b",
                    "baseline_pass_rate": 0.5,
                    "mentored_pass_rate": 0.0,
                    "control_pass_rate": 0.0,
                    "delta": -0.5,
                }
            ],
            "category_breakdown": [],
        },
    }


def _two_replicates_payload() -> dict[str, Any]:
    fixture = Path(__file__).resolve().parent / "fixtures" / "results_two_replicates.json"
    return json.loads(fixture.read_text(encoding="utf-8"))


def _fake_git_head(monkeypatch: Any) -> str:
    export_commit = "1234567890abcdef1234567890abcdef12345678"

    def _fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert args and list(args[0]) == ["git", "rev-parse", "HEAD"]
        return subprocess.CompletedProcess(
            args=list(args[0]),
            returncode=0,
            stdout=f"{export_commit}\n",
            stderr="",
        )

    monkeypatch.setattr("mentor_worker_benchmark.submission.subprocess.run", _fake_run)
    return export_commit


def test_legacy_summary_metrics_are_backfilled_from_runs(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    builder = _load_builder_module()
    payload = _base_results_payload(suite="dev10")
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "official_dev10.zip"
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    commit = _fake_git_head(monkeypatch)

    export_submission_bundle(results_path=results_path, out_path=out_path, official_submission=True)
    normalized = builder._normalize_submission(out_path)

    assert normalized["git_commit_hash"] == commit
    assert normalized["total_runs"] == 2
    assert normalized["total_passes"] == 1
    assert normalized["passes_by_mode"] == {"worker_only": 1, "mentor_worker": 0}
    assert normalized["model_call_errors_by_mode"] == {"worker_only": 0, "mentor_worker": 1}
    assert normalized["model_call_timeouts_by_mode"] == {"worker_only": 0, "mentor_worker": 1}
    assert normalized["total_model_call_errors"] == 1
    assert normalized["total_model_call_timeouts"] == 1
    assert normalized["metrics_source"]["total_passes"] == "runs_backfill"
    assert normalized["metrics_source"]["model_call_errors_by_mode"] == "runs_backfill"
    assert normalized["official_role"] == "sanity"
    assert normalized["protocol_version"] == "v0.3.0"
    assert normalized["seeds_count"] == 1
    assert isinstance(normalized["time_total_s"], float)


def test_official_role_classification_for_headline_and_sanity(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    builder = _load_builder_module()
    _fake_git_head(monkeypatch)

    headline_results = tmp_path / "headline_results.json"
    headline_zip = tmp_path / "official_dev50.zip"
    headline_payload = _base_results_payload(suite="dev50")
    headline_results.write_text(json.dumps(headline_payload, indent=2), encoding="utf-8")
    export_submission_bundle(results_path=headline_results, out_path=headline_zip, official_submission=True)

    sanity_results = tmp_path / "sanity_results.json"
    sanity_zip = tmp_path / "official_quick.zip"
    sanity_payload = _base_results_payload(suite="quick")
    sanity_results.write_text(json.dumps(sanity_payload, indent=2), encoding="utf-8")
    export_submission_bundle(results_path=sanity_results, out_path=sanity_zip, official_submission=True)

    headline_normalized = builder._normalize_submission(headline_zip)
    sanity_normalized = builder._normalize_submission(sanity_zip)

    assert headline_normalized["official_role"] == "headline"
    assert sanity_normalized["official_role"] == "sanity"


def test_normalize_submission_surfaces_analysis_means_cis_and_significance(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    builder = _load_builder_module()
    _fake_git_head(monkeypatch)

    results_path = tmp_path / "multi_results.json"
    out_path = tmp_path / "multi_submission.zip"
    results_path.write_text(json.dumps(_two_replicates_payload(), indent=2), encoding="utf-8")
    export_submission_bundle(results_path=results_path, out_path=out_path, official_submission=True)

    normalized = builder._normalize_submission(out_path)
    assert normalized["baseline_mean"] == 0.25
    assert normalized["mentored_mean"] == 0.75
    assert normalized["lift_mean"] == 0.5
    assert normalized["baseline_ci_low"] <= normalized["baseline_ci_high"]
    assert normalized["mentored_ci_low"] <= normalized["mentored_ci_high"]
    assert normalized["lift_ci_low"] <= normalized["lift_ci_high"]
    assert isinstance(normalized["lift_significant"], bool)
    assert normalized["best_worker"]["baseline_pass_rate"] == normalized["baseline_mean"]
    assert normalized["best_worker"]["mentored_pass_rate"] == normalized["mentored_mean"]
    assert normalized["best_worker"]["lift"] == normalized["lift_mean"]
    assert normalized["protocol_version"] == "v0.3.0"
    assert normalized["seeds_count"] == 2
    assert normalized["protocol_seeds"] == [1337, 2026]


def test_rendered_index_contains_tabs_single_table_headers_and_embedded_summary_json(tmp_path: Path) -> None:
    builder = _load_builder_module()
    output_path = tmp_path / "index.html"
    summary = {
        "generated_at": "2026-03-01T00:00:00+00:00",
        "submission_count": 1,
        "official_count": 1,
        "community_count": 0,
        "entries": [
            {
                "submission_id": "official_dev_v1_m3air_2026-03-01",
                "task_pack": "task_pack_v2",
                "suite": "dev50",
                "official_submission": True,
                "best_worker": {
                    "worker_model": "qwen2.5-coder:7b",
                    "baseline_pass_rate": 0.1,
                    "mentored_pass_rate": 0.2,
                    "lift": 0.1,
                },
                "total_model_call_errors": 3,
                "total_model_call_timeouts": 1,
                "git_commit_hash": "1234567890abcdef1234567890abcdef12345678",
                "generated_at": "2026-03-01T00:00:00+00:00",
            }
        ],
    }

    builder._render_index_html(summary, output_path)
    rendered = output_path.read_text(encoding="utf-8")

    assert '<script id="summary-json" type="application/json">' in rendered
    assert ">Headline<" in rendered
    assert ">Sanity<" in rendered
    assert ">Community<" in rendered
    assert ">All<" in rendered
    assert rendered.count("<table>") == 1

    match = re.search(r"<thead>\s*<tr>(.*?)</tr>\s*</thead>", rendered, flags=re.S)
    assert match is not None
    headers = re.findall(r"<th[^>]*>(.*?)</th>", match.group(1))
    assert headers == [
        "Submission",
        "Role",
        "Pack",
        "Suite",
        "Top Worker",
        "Baseline",
        "Mentored",
        "Lift",
        "Errors",
        "Timeouts",
        "Commit",
    ]
    assert "sig-marker" in rendered
    assert "95% CI" in rendered
