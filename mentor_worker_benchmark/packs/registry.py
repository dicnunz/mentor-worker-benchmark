from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _registry_path() -> Path:
    return Path(__file__).resolve().parent / "registry.json"


@lru_cache(maxsize=1)
def load_pack_registry() -> dict[str, Any]:
    path = _registry_path()
    if not path.exists():
        raise RuntimeError(f"Pack registry not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid pack registry JSON at {path}: {exc}") from exc

    packs = payload.get("packs")
    if not isinstance(packs, list):
        raise RuntimeError("Pack registry payload must define a `packs` list.")
    return payload


def list_pack_cards() -> list[dict[str, Any]]:
    payload = load_pack_registry()
    cards = payload.get("packs", [])
    return [row for row in cards if isinstance(row, dict)]


def get_pack_card(pack_id: str) -> dict[str, Any] | None:
    normalized = pack_id.strip()
    if not normalized:
        return None

    for card in list_pack_cards():
        card_id = card.get("pack_id")
        if isinstance(card_id, str) and card_id == normalized:
            return card
        aliases = card.get("module_aliases")
        if isinstance(aliases, list) and normalized in aliases:
            return card
    return None
