from __future__ import annotations

import json
from pathlib import Path

from mentor_worker_benchmark.analysis import (
    ANALYSIS_VERSION,
    DEFAULT_BOOTSTRAP_SAMPLES,
    generate_analysis_payload,
)


def _two_replicates_payload() -> dict[str, object]:
    fixture = Path(__file__).resolve().parent / "fixtures" / "results_two_replicates.json"
    return json.loads(fixture.read_text(encoding="utf-8"))


def test_generate_analysis_is_deterministic_for_same_input() -> None:
    payload = _two_replicates_payload()
    first = generate_analysis_payload(payload, bootstrap_samples=512)
    second = generate_analysis_payload(payload, bootstrap_samples=512)
    assert first == second


def test_generate_analysis_includes_ci_and_significance_fields() -> None:
    payload = _two_replicates_payload()
    analysis = generate_analysis_payload(payload, bootstrap_samples=DEFAULT_BOOTSTRAP_SAMPLES)

    assert analysis["analysis_version"] == ANALYSIS_VERSION
    assert analysis["ci_method"]
    assert analysis["bootstrap_samples"] == DEFAULT_BOOTSTRAP_SAMPLES
    assert isinstance(analysis["bootstrap_seed"], int)
    assert analysis["group_count"] >= 1

    group = analysis["groups"][0]
    assert group["baseline_mean"] is not None
    assert group["baseline_ci_low"] is not None
    assert group["baseline_ci_high"] is not None
    assert group["mentored_mean"] is not None
    assert group["mentored_ci_low"] is not None
    assert group["mentored_ci_high"] is not None
    assert group["lift_mean"] is not None
    assert group["lift_ci_low"] is not None
    assert group["lift_ci_high"] is not None
    assert group["baseline_ci_low"] <= group["baseline_ci_high"]
    assert group["mentored_ci_low"] <= group["mentored_ci_high"]
    assert group["lift_ci_low"] <= group["lift_ci_high"]
    assert isinstance(group["lift_significant"], bool)
    assert isinstance(group["lift_p_value_gt_zero"], float)
    assert 0.0 <= group["lift_p_value_gt_zero"] <= 1.0
    assert isinstance(group["paired_significance"]["significant"], bool)
    assert isinstance(group["paired_significance"]["p_value_lift_gt_zero"], float)
    assert group["paired_significance"]["p_value_lift_gt_zero"] == group["lift_p_value_gt_zero"]
