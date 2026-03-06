from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mentor_worker_benchmark.protocol import canonical_json

CHECKPOINT_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class RunUnitKey:
    seed: int
    mode: str
    task_id: str
    worker_model: str
    mentor_model: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "seed": int(self.seed),
            "mode": self.mode,
            "task_id": self.task_id,
            "worker_model": self.worker_model,
            "mentor_model": self.mentor_model,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RunUnitKey:
        return cls(
            seed=int(payload["seed"]),
            mode=str(payload["mode"]),
            task_id=str(payload["task_id"]),
            worker_model=str(payload["worker_model"]),
            mentor_model=(
                str(payload["mentor_model"])
                if payload.get("mentor_model") is not None
                else None
            ),
        )

    def token(self) -> str:
        return canonical_json(self.as_dict())


class BenchmarkCheckpointStore:
    def __init__(self, *, path: Path, metadata: dict[str, Any]) -> None:
        self.path = path
        self.metadata = json.loads(json.dumps(metadata))
        self.metadata_fingerprint = self._fingerprint(self.metadata)
        self._completed_runs: dict[str, dict[str, Any]] = {}
        self._loaded = False

    @staticmethod
    def _fingerprint(metadata: dict[str, Any]) -> str:
        return hashlib.sha256(canonical_json(metadata).encode("utf-8")).hexdigest()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.exists():
            return

        metadata_seen = False
        for line_number, raw_line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise RuntimeError(
                    f"Checkpoint file is invalid JSONL at line {line_number}: {self.path}"
                ) from exc

            if not isinstance(event, dict):
                raise RuntimeError(
                    f"Checkpoint file contains a non-object event at line {line_number}: {self.path}"
                )

            event_type = str(event.get("event", ""))
            event_fingerprint = str(event.get("config_fingerprint", ""))
            if event_fingerprint and event_fingerprint != self.metadata_fingerprint:
                raise RuntimeError(
                    "Checkpoint config mismatch for "
                    f"{self.path}. Use a new results path for a fresh run."
                )

            if event_type == "metadata":
                metadata_seen = True
                event_metadata = event.get("metadata")
                if not isinstance(event_metadata, dict):
                    raise RuntimeError(f"Checkpoint metadata is invalid in {self.path}")
                if self._fingerprint(event_metadata) != self.metadata_fingerprint:
                    raise RuntimeError(
                        "Checkpoint metadata mismatch for "
                        f"{self.path}. Use a new results path for a fresh run."
                    )
                continue

            if event_type != "run_completed":
                raise RuntimeError(
                    f"Unknown checkpoint event `{event_type}` at line {line_number}: {self.path}"
                )

            unit_payload = event.get("unit")
            run_payload = event.get("run")
            if not isinstance(unit_payload, dict) or not isinstance(run_payload, dict):
                raise RuntimeError(
                    f"Checkpoint run event is malformed at line {line_number}: {self.path}"
                )
            unit_key = RunUnitKey.from_dict(unit_payload)
            self._completed_runs[unit_key.token()] = json.loads(json.dumps(run_payload))

        if self.path.exists() and self.path.stat().st_size > 0 and not metadata_seen:
            raise RuntimeError(
                f"Checkpoint file is missing metadata header: {self.path}"
            )

    def completed_runs(self) -> dict[str, dict[str, Any]]:
        self._ensure_loaded()
        return {
            key: json.loads(json.dumps(value))
            for key, value in self._completed_runs.items()
        }

    def get_completed_run(self, unit_key: RunUnitKey) -> dict[str, Any] | None:
        self._ensure_loaded()
        payload = self._completed_runs.get(unit_key.token())
        if payload is None:
            return None
        return json.loads(json.dumps(payload))

    def record_completed_run(self, unit_key: RunUnitKey, run_payload: dict[str, Any]) -> None:
        self._ensure_loaded()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        events: list[dict[str, Any]] = []
        if not self.path.exists() or self.path.stat().st_size == 0:
            events.append(
                {
                    "schema_version": CHECKPOINT_SCHEMA_VERSION,
                    "event": "metadata",
                    "config_fingerprint": self.metadata_fingerprint,
                    "metadata": self.metadata,
                }
            )

        normalized_run = json.loads(json.dumps(run_payload))
        events.append(
            {
                "schema_version": CHECKPOINT_SCHEMA_VERSION,
                "event": "run_completed",
                "config_fingerprint": self.metadata_fingerprint,
                "unit": unit_key.as_dict(),
                "run": normalized_run,
            }
        )

        with self.path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(canonical_json(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

        self._completed_runs[unit_key.token()] = normalized_run
