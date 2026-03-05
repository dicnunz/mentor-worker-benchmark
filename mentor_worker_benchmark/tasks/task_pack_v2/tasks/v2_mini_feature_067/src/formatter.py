def render(plan: list[dict[str, object]], *, status_breakdown: dict[str, int] | None = None) -> dict[str, object]:
    payload = {
        "count": len(plan),
        "tasks": [str(item["name"]) for item in plan],
    }
    if status_breakdown is not None:
        payload["status_breakdown"] = dict(status_breakdown)
    return payload
