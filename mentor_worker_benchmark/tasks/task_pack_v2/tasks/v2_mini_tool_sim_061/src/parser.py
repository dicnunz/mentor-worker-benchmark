def parse_findings(raw: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Buggy: tool format uses '|', but this parser uses ';'.
        parts = [part.strip() for part in line.split(";")]
        if len(parts) != 4:
            continue
        payload: dict[str, object] = {}
        for part in parts:
            key, value = part.split(":", 1)
            payload[key.lower()] = value.strip().lower()
        findings.append(payload)
    return findings
