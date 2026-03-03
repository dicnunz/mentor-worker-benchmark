from __future__ import annotations

import hashlib
import json
from typing import Any

OFFICIAL_PROTOCOL_VERSION = "v0.3.0"
OFFICIAL_HEADLINE_SUITES = frozenset({"dev", "dev50", "test"})
OFFICIAL_HEADLINE_SEEDS = (1337, 2026, 9001)


def is_headline_suite(suite: str) -> bool:
    return suite in OFFICIAL_HEADLINE_SUITES


def parse_seed_list(raw: str) -> list[int]:
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        raise ValueError("Seed list is empty.")

    seeds: list[int] = []
    for item in parts:
        try:
            value = int(item)
        except ValueError as exc:
            raise ValueError(f"Invalid seed `{item}` in --seeds list.") from exc
        seeds.append(value)
    return seeds


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def deterministic_run_group_id(
    *,
    task_pack: str,
    suite: str,
    run_modes: list[str],
    mentor_models: list[str],
    worker_models: list[str],
    provider: str,
    mentor_provider: str,
    worker_provider: str,
    max_turns: int,
    timeout_seconds: int,
    repro_mode: bool,
    worker_num_predict: int,
    mentor_num_predict: int,
    seeds: list[int],
) -> str:
    material = {
        "task_pack": task_pack,
        "suite": suite,
        "run_modes": list(run_modes),
        "mentor_models": list(mentor_models),
        "worker_models": list(worker_models),
        "provider": provider,
        "mentor_provider": mentor_provider,
        "worker_provider": worker_provider,
        "max_turns": int(max_turns),
        "timeout_seconds": int(timeout_seconds),
        "repro_mode": bool(repro_mode),
        "worker_num_predict": int(worker_num_predict),
        "mentor_num_predict": int(mentor_num_predict),
        "seeds": [int(seed) for seed in seeds],
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return f"group_{digest[:12]}"


def seed_token(seeds: list[int] | tuple[int, ...]) -> str:
    return "-".join(str(int(seed)) for seed in seeds)


def protocol_token(version: str = OFFICIAL_PROTOCOL_VERSION) -> str:
    return f"protocol-{version}"
