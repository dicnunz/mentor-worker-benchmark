from collections import Counter
from pathlib import Path

from .parser import parse_findings

SEVERITY_RANK = {"info": 1, "warn": 2, "error": 3}


def summarize_from_report(path: str, min_severity: str = "info") -> dict[str, object]:
    raw = Path(path).read_text(encoding="utf-8")
    findings = parse_findings(raw)
    min_rank = SEVERITY_RANK[min_severity]
    filtered = [
        finding
        for finding in findings
        if SEVERITY_RANK.get(str(finding.get("severity", "info")), 0) >= min_rank
    ]
    rule_counts = Counter(str(finding.get("rule", "")) for finding in filtered)
    severity_counts = Counter(str(finding.get("severity", "")) for finding in filtered)
    top_rule = None
    if rule_counts:
        top_rule = sorted(rule_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "count": len(filtered),
        "by_severity": dict(sorted(severity_counts.items())),
        "top_rule": top_rule,
    }
