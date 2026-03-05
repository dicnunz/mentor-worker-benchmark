import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.analysis import generate_analysis_payload
from mentor_worker_benchmark.submission import (
    export_submission_bundle,
    resolve_task_pack_version,
    verify_submission_bundle,
)


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
            "python": {
                "version": "3.11.0",
                "implementation": "CPython",
                "executable": "python",
                "pip_freeze_sha256": "a" * 64,
                "pip_freeze_line_count": 123,
            },
            "platform": {
                "platform": "macOS",
                "system": "Darwin",
                "release": "23.0",
                "machine": "arm64",
            },
            "ollama": {"base_url": "http://localhost:11434", "cli_version": "0.0.0", "model_tags": []},
            "git": {"commit": "de5a929", "dirty": False},
            "task_pack": {
                "id": "task_pack_v2",
                "version": "2.1.0",
                "source": "registry",
                "hash": "b" * 64,
                "manifest_path": "mentor_worker_benchmark/tasks/task_pack_v2/metadata.json",
            },
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
    assert manifest["pip_freeze_sha256"] == "a" * 64
    with zipfile.ZipFile(out_path, "r") as archive:
        assert "analysis.json" in archive.namelist()

    report = verify_submission_bundle(out_path)
    assert report["ok"], report["errors"]
    assert report["details"]["pip_freeze_sha256"] == "a" * 64


def test_export_supports_official_submission_flag(tmp_path: Path) -> None:
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "official_quick_protocol-v0.3.0_seeds-1337.zip"
    results_path.write_text(json.dumps(_sample_results_payload(), indent=2), encoding="utf-8")

    manifest = export_submission_bundle(
        results_path=results_path,
        out_path=out_path,
        official_submission=True,
    )
    assert manifest["official_submission"] is True
    assert manifest["protocol_version"] == "v0.3.0"
    assert manifest["protocol_seeds"] == [1337]

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
                    "task_pack_version": "2.1.0",
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


def test_export_uses_git_rev_parse_head_for_manifest_and_environment(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    results_path = tmp_path / "results.json"
    out_path = tmp_path / "submission.zip"
    results_path.write_text(json.dumps(_sample_results_payload(), indent=2), encoding="utf-8")

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

    manifest = export_submission_bundle(
        results_path=results_path,
        out_path=out_path,
    )
    assert manifest["git_commit_hash"] == export_commit

    with zipfile.ZipFile(out_path, "r") as archive:
        bundled_results = json.loads(archive.read("results.json").decode("utf-8"))
        bundled_environment = json.loads(archive.read("environment.json").decode("utf-8"))
        bundled_manifest = json.loads(archive.read("submission_manifest.json").decode("utf-8"))

    assert bundled_manifest["git_commit_hash"] == export_commit
    assert bundled_environment["git"]["commit"] == export_commit
    assert bundled_results["environment"]["git"]["commit"] == export_commit


def test_verify_requires_analysis_for_multi_replicate_results(tmp_path: Path) -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "results_two_replicates.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))

    out_path = tmp_path / "missing_analysis_multi.zip"
    task_pack_version = resolve_task_pack_version("task_pack_v2") or "2.1.0"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload, indent=2))
        archive.writestr("environment.json", json.dumps(payload["environment"], indent=2))
        archive.writestr(
            "submission_manifest.json",
            json.dumps(
                {
                    "bundle_version": "1",
                    "task_pack": "task_pack_v2",
                    "task_pack_version": task_pack_version,
                    "git_commit_hash": "de5a929",
                    "cli_command": "python -m mentor_worker_benchmark run --suite quick",
                },
                indent=2,
            ),
        )

    report = verify_submission_bundle(out_path)
    assert not report["ok"]
    assert any("analysis.json is required for multi-replicate" in item for item in report["errors"])


def test_verify_backfills_analysis_for_single_replicate_when_missing(tmp_path: Path) -> None:
    payload = _sample_results_payload()
    out_path = tmp_path / "missing_analysis_single.zip"
    task_pack_version = resolve_task_pack_version("task_pack_v2") or "2.1.0"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload, indent=2))
        archive.writestr("environment.json", json.dumps(payload["environment"], indent=2))
        archive.writestr(
            "submission_manifest.json",
            json.dumps(
                {
                    "bundle_version": "1",
                    "task_pack": "task_pack_v2",
                    "task_pack_version": task_pack_version,
                    "git_commit_hash": "de5a929",
                    "cli_command": "python -m mentor_worker_benchmark run --suite quick --repro",
                },
                indent=2,
            ),
        )

    report = verify_submission_bundle(out_path)
    assert report["ok"], report["errors"]
    assert report["details"]["analysis_source"] == "generated_single_replicate"


def test_verify_rejects_new_official_headline_bundle_without_required_multiseed(
    tmp_path: Path,
) -> None:
    payload = _sample_results_payload()
    payload["config"]["suite"] = "dev50"
    out_path = tmp_path / "official_dev50_protocol-v0.3.0_seeds-1337.zip"
    task_pack_version = resolve_task_pack_version("task_pack_v2") or "2.1.0"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload, indent=2))
        archive.writestr("environment.json", json.dumps(payload["environment"], indent=2))
        archive.writestr("analysis.json", json.dumps(generate_analysis_payload(payload), indent=2))
        archive.writestr(
            "submission_manifest.json",
            json.dumps(
                {
                    "bundle_version": "1",
                    "task_pack": "task_pack_v2",
                    "task_pack_version": task_pack_version,
                    "git_commit_hash": "de5a929",
                    "cli_command": "python -m mentor_worker_benchmark run --suite dev50 --seed 1337",
                    "official_submission": True,
                    "protocol_version": "v0.3.0",
                    "protocol_seeds": [1337],
                    "protocol_seed_count": 1,
                    "suite": "dev50",
                    "run_group_id": "group_test",
                    "compute_budget": {
                        "max_turns": 2,
                        "timeout_seconds": 180,
                        "total_model_calls_attempted": 1,
                        "total_tokens_estimate": 42,
                        "total_wall_time_seconds": 1.0,
                    },
                },
                indent=2,
            ),
        )

    report = verify_submission_bundle(out_path)
    assert not report["ok"]
    assert any("Headline official bundles must use protocol seeds" in item for item in report["errors"])


def test_verify_allows_legacy_official_bundle_without_protocol_fields(tmp_path: Path) -> None:
    payload = _sample_results_payload()
    out_path = tmp_path / "official_legacy_bundle.zip"
    task_pack_version = resolve_task_pack_version("task_pack_v2") or "2.1.0"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.json", json.dumps(payload, indent=2))
        archive.writestr("environment.json", json.dumps(payload["environment"], indent=2))
        archive.writestr("analysis.json", json.dumps(generate_analysis_payload(payload), indent=2))
        archive.writestr(
            "submission_manifest.json",
            json.dumps(
                {
                    "bundle_version": "1",
                    "task_pack": "task_pack_v2",
                    "task_pack_version": task_pack_version,
                    "git_commit_hash": "de5a929",
                    "cli_command": "python -m mentor_worker_benchmark run --suite quick --seed 1337",
                    "official_submission": True,
                },
                indent=2,
            ),
        )

    report = verify_submission_bundle(out_path)
    assert report["ok"], report["errors"]
    assert report["details"]["official_protocol"] == "legacy"
