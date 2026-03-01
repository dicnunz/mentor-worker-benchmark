import json
import zipfile
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.submission import export_submission_bundle, verify_submission_bundle


def _sample_results_payload() -> dict[str, object]:
    return {
        "generated_at": "2026-03-01T00:00:00+00:00",
        "config": {
            "models": ["phi3:mini"],
            "worker_models": ["phi3:mini"],
            "run_modes": ["worker_only"],
            "repro_mode": True,
            "max_turns": 2,
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "worker_num_predict": 640,
                "mentor_num_predict": 220,
                "seed": 1337,
            },
            "task_pack": "task_pack_v2",
            "suite": "quick",
            "selector_source": "suite",
            "task_selector": None,
            "task_count": 1,
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
            "total_runs": 1,
            "runs_by_mode": {"worker_only": 1},
            "benchmark_wall_time_seconds": 1.0,
            "violation_count": 0,
        },
        "runs": [
            {
                "mode": "worker_only",
                "task_id": "v1_string_regex_parsing_000",
                "worker_model": "phi3:mini",
                "mentor_model": None,
                "pass": False,
                "turns_used": 1,
                "wall_time_seconds": 0.12,
                "total_tokens_estimate": 42,
                "mentor_turn_count": 0,
                "mentor_violation_count": 0,
                "log": {},
            }
        ],
        "violations": [],
        "aggregates": {
            "task_count": 1,
            "tasks": ["v1_string_regex_parsing_000"],
            "baseline_by_worker": {"phi3:mini": 0.0},
            "control_by_worker": {"phi3:mini": 0.0},
            "mentor_worker_pairs": [],
            "best_mentors": [],
            "best_workers": [
                {
                    "worker_model": "phi3:mini",
                    "baseline_pass_rate": 0.0,
                    "mentored_pass_rate": 0.0,
                    "control_pass_rate": 0.0,
                    "delta": 0.0,
                }
            ],
            "category_breakdown": [],
        },
    }


def test_export_and_verify_submission_round_trip(tmp_path: Path) -> None:
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "submission.zip"
    results_path.write_text(json.dumps(_sample_results_payload(), indent=2), encoding="utf-8")

    manifest = export_submission_bundle(
        results_path=results_path,
        out_path=out_path,
        cli_command="python -m mentor_worker_benchmark run --suite quick --repro",
    )
    assert out_path.exists()
    assert manifest["task_pack"] == "task_pack_v2"
    assert manifest["official_submission"] is False

    report = verify_submission_bundle(out_path)
    assert report["ok"], report["errors"]


def test_export_supports_official_submission_flag(tmp_path: Path) -> None:
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "official_submission.zip"
    results_path.write_text(json.dumps(_sample_results_payload(), indent=2), encoding="utf-8")

    manifest = export_submission_bundle(
        results_path=results_path,
        out_path=out_path,
        official_submission=True,
    )
    assert manifest["official_submission"] is True

    report = verify_submission_bundle(out_path)
    assert report["ok"], report["errors"]
    assert report["details"]["official_submission"] is True


def test_verify_rejects_manifest_with_missing_commit(tmp_path: Path) -> None:
    payload: dict[str, Any] = _sample_results_payload()
    environment = dict(payload["environment"])
    environment["git"] = {"commit": "de5a929", "dirty": False}
    payload["environment"] = environment

    out_path = tmp_path / "invalid_submission.zip"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload, indent=2))
        archive.writestr("environment.json", json.dumps(payload["environment"], indent=2))
        archive.writestr(
            "submission_manifest.json",
            json.dumps(
                {
                    "bundle_version": "1",
                    "task_pack": "task_pack_v2",
                    "task_pack_version": "2.0.0",
                    "git_commit_hash": "",
                    "cli_command": "",
                },
                indent=2,
            ),
        )

    report = verify_submission_bundle(out_path)
    assert not report["ok"]
    joined = "\n".join(report["errors"])
    assert "git_commit_hash cannot be empty" in joined
    assert "cli_command cannot be empty" in joined
