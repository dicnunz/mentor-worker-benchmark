from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

DEFAULT_SIMILARITY_THRESHOLD = 0.985
DEFAULT_MAX_CLUSTERS = 12
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")

ORIGINALITY_PATTERNS: dict[str, re.Pattern[str]] = {
    "url_reference": re.compile(r"https?://", re.IGNORECASE),
    "github_reference": re.compile(r"github\\.com", re.IGNORECASE),
    "stackoverflow_reference": re.compile(r"stack\\s*overflow", re.IGNORECASE),
    "benchmark_dataset_reference": re.compile(
        r"\\b(human[-_ ]?eval|mbpp|apps dataset|leetcode|codeforces)\\b", re.IGNORECASE
    ),
    "copyright_notice": re.compile(r"copyright\\s+\\d{4}", re.IGNORECASE),
}


@dataclass(slots=True)
class TaskRecord:
    task_id: str
    category: str
    difficulty: str
    split: str
    path: Path
    similarity_text: str
    file_texts: dict[str, str]


def _pack_root() -> Path:
    return Path(__file__).resolve().parent


def _repo_root() -> Path:
    return _pack_root().parents[2]


def _read_metadata() -> dict[str, Any]:
    path = _pack_root() / "metadata.json"
    if not path.exists():
        raise RuntimeError(f"Missing metadata.json at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _git_commit_hash() -> str | None:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=_repo_root(),
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return output.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_is_dirty() -> bool | None:
    try:
        subprocess.check_output(
            ["git", "diff", "--quiet"],
            cwd=_repo_root(),
            stderr=subprocess.DEVNULL,
        )
        return False
    except subprocess.CalledProcessError:
        return True
    except OSError:
        return None


def _iter_text_files(task_dir: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    allowed_suffixes = {".py", ".md", ".txt", ".json", ".csv", ".toml", ".yaml", ".yml"}
    for path in sorted(task_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix and path.suffix.lower() not in allowed_suffixes:
            continue
        rel = path.relative_to(task_dir).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rows.append((rel, text))
    return rows


def _collect_task_records(metadata: dict[str, Any]) -> list[TaskRecord]:
    pack_root = _pack_root()
    records: list[TaskRecord] = []
    for row in metadata.get("tasks", []):
        task_id = str(row["task_id"])
        task_dir = pack_root / str(row["path"])
        if not task_dir.exists():
            raise RuntimeError(f"Task directory missing for `{task_id}`: {task_dir}")
        texts = _iter_text_files(task_dir)
        file_texts = {rel: text for rel, text in texts}
        prompt = file_texts.get("prompt.md", "")
        tests = "\n\n".join(
            text for rel, text in texts if rel.startswith("tests/") and rel.endswith(".py")
        )
        similarity_text = f"{prompt}\n{tests}"
        records.append(
            TaskRecord(
                task_id=task_id,
                category=str(row["category"]),
                difficulty=str(row["difficulty"]),
                split=str(row["split"]),
                path=task_dir,
                similarity_text=similarity_text,
                file_texts=file_texts,
            )
        )
    return sorted(records, key=lambda item: item.task_id)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _hash_bucket(payload: str, buckets: int) -> int:
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).hexdigest()
    return int(digest, 16) % buckets


def _hashed_ngram_vector(text: str, *, token_n: int = 3, buckets: int = 4096) -> dict[int, float]:
    tokens = _tokenize(text)
    vector: dict[int, float] = {}

    if len(tokens) >= token_n:
        for idx in range(len(tokens) - token_n + 1):
            gram = " ".join(tokens[idx : idx + token_n])
            bucket = _hash_bucket(f"tok:{gram}", buckets)
            vector[bucket] = vector.get(bucket, 0.0) + 1.0
    else:
        for token in tokens:
            bucket = _hash_bucket(f"tok:{token}", buckets)
            vector[bucket] = vector.get(bucket, 0.0) + 1.0

    compact = re.sub(r"\s+", " ", text.lower())
    if len(compact) >= 5:
        for idx in range(len(compact) - 4):
            shingle = compact[idx : idx + 5]
            bucket = _hash_bucket(f"char:{shingle}", buckets)
            vector[bucket] = vector.get(bucket, 0.0) + 0.35

    return vector


def _cosine_similarity(left: dict[int, float], right: dict[int, float]) -> float:
    if not left or not right:
        return 0.0
    dot = 0.0
    for key, value in left.items():
        dot += value * right.get(key, 0.0)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


class _UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            self.parent[right_root] = left_root
        else:
            self.parent[left_root] = right_root


def _cluster_average_similarity(cluster: list[str], pair_scores: dict[tuple[str, str], float]) -> float:
    scores: list[float] = []
    for idx, left in enumerate(cluster):
        for right in cluster[idx + 1 :]:
            key = (left, right) if left < right else (right, left)
            if key in pair_scores:
                scores.append(pair_scores[key])
    return mean(scores) if scores else 0.0


def _similarity_clusters(
    records: list[TaskRecord],
    *,
    threshold: float,
) -> tuple[list[list[str]], dict[tuple[str, str], float]]:
    task_ids = [item.task_id for item in records]
    by_id = {item.task_id: item for item in records}
    vectors = {task_id: _hashed_ngram_vector(by_id[task_id].similarity_text) for task_id in task_ids}
    pair_scores: dict[tuple[str, str], float] = {}
    union_find = _UnionFind(task_ids)

    for idx, left in enumerate(task_ids):
        for right in task_ids[idx + 1 :]:
            score = _cosine_similarity(vectors[left], vectors[right])
            if score >= threshold:
                union_find.union(left, right)
                pair_scores[(left, right)] = score

    clusters_by_root: dict[str, list[str]] = defaultdict(list)
    for task_id in task_ids:
        clusters_by_root[union_find.find(task_id)].append(task_id)
    clusters = [sorted(items) for items in clusters_by_root.values() if len(items) > 1]
    clusters.sort(key=lambda items: (-len(items), items[0]))
    return clusters, pair_scores


def _originality_flags(records: list[TaskRecord]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in records:
        for rel_path, text in record.file_texts.items():
            for marker, pattern in ORIGINALITY_PATTERNS.items():
                match = pattern.search(text)
                if not match:
                    continue
                snippet = text[max(0, match.start() - 40) : min(len(text), match.end() + 40)]
                rows.append(
                    {
                        "task_id": record.task_id,
                        "file": rel_path,
                        "marker": marker,
                        "snippet": re.sub(r"\s+", " ", snippet).strip(),
                    }
                )
                break
    return rows


def build_provenance_payload(
    *,
    seed: int | None = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_clusters: int = DEFAULT_MAX_CLUSTERS,
) -> dict[str, Any]:
    metadata = _read_metadata()
    records = _collect_task_records(metadata)

    effective_seed = int(metadata["generator_seed"]) if seed is None else seed
    clusters, pair_scores = _similarity_clusters(records, threshold=similarity_threshold)
    top_clusters: list[dict[str, Any]] = []
    for cluster_id, cluster in enumerate(clusters[:max_clusters], start=1):
        top_clusters.append(
            {
                "cluster_id": cluster_id,
                "size": len(cluster),
                "average_similarity": round(_cluster_average_similarity(cluster, pair_scores), 4),
                "members": cluster,
            }
        )

    originality_flags = _originality_flags(records)
    file_count = sum(len(record.file_texts) for record in records)

    payload: dict[str, Any] = {
        "pack_name": str(metadata["pack_name"]),
        "pack_version": str(metadata["pack_version"]),
        "seed": effective_seed,
        "generated_at": datetime.now(UTC).isoformat(),
        "generator": {
            "script": "mentor_worker_benchmark/tasks/task_pack_v2/generate_task_pack.py",
            "version": str(metadata["pack_version"]),
            "git_commit": _git_commit_hash(),
            "git_dirty": _git_is_dirty(),
        },
        "statement": {
            "synthetic_tasks": (
                "All task content in task_pack_v2 is synthetic and generated by internal scripts in this "
                "repository, then materialized as static files."
            ),
            "task_content_license": "MIT (same as repository license).",
        },
        "contamination": {
            "did": [
                "Used deterministic in-repo generators with fixed seed controls.",
                "Tracked generator metadata, repository commit hash, and similarity/originality scans.",
                "Checked internal overlap across prompt+test content with hashed n-gram cosine similarity.",
            ],
            "did_not": [
                "No web scraping of coding sites, blogs, or problem repositories.",
                "No copying from public benchmark datasets (e.g., HumanEval, MBPP, APPS).",
                "No direct import of third-party task corpora into this pack.",
            ],
            "limitations": [
                "This does not prove zero contamination risk in model pretraining corpora.",
                (
                    "Models may still have seen similar programming motifs or patterns during pretraining, "
                    "so results should be interpreted as relative benchmark behavior, not absolute novelty."
                ),
            ],
        },
        "checks": {
            "similarity_scan": {
                "method": "hashed token/char n-gram cosine similarity over prompt+tests",
                "threshold": similarity_threshold,
                "task_count": len(records),
                "cluster_count": len(clusters),
                "largest_cluster_size": max((len(cluster) for cluster in clusters), default=1),
                "top_clusters": top_clusters,
            },
            "originality_scan": {
                "method": "pattern scan for external-source markers in task files",
                "task_file_count": file_count,
                "pattern_keys": sorted(ORIGINALITY_PATTERNS),
                "flagged_files_count": len(originality_flags),
                "flagged_files": originality_flags,
            },
        },
    }
    return payload


def render_provenance_markdown(payload: dict[str, Any]) -> str:
    generator = payload["generator"]
    contamination = payload["contamination"]
    similarity = payload["checks"]["similarity_scan"]
    originality = payload["checks"]["originality_scan"]

    lines = [
        "# task_pack_v2 Provenance",
        "",
        "## Generation Metadata",
        "",
        f"- Pack: `{payload['pack_name']}`",
        f"- Pack version: `{payload['pack_version']}`",
        f"- Generator version: `{generator['version']}`",
        f"- Git commit: `{generator['git_commit'] or 'unknown'}`",
        f"- Git dirty state at generation: `{generator.get('git_dirty')}`",
        f"- Seed: `{payload['seed']}`",
        f"- Manifest generated at: `{payload['generated_at']}`",
        "",
        "## Synthetic Data Statement",
        "",
        f"- {payload['statement']['synthetic_tasks']}",
        f"- {payload['statement']['task_content_license']}",
        "",
        "## Contamination Checklist",
        "",
        "### What we did",
    ]
    lines.extend([f"- {item}" for item in contamination["did"]])
    lines.extend(["", "### What we did not do"])
    lines.extend([f"- {item}" for item in contamination["did_not"]])
    lines.extend(["", "### Known limitations"])
    lines.extend([f"- {item}" for item in contamination["limitations"]])
    lines.extend(
        [
            "",
            "## Similarity Scan (Intra-Pack)",
            "",
            f"- Method: `{similarity['method']}`",
            f"- Threshold: `{similarity['threshold']}`",
            f"- Task count scanned: `{similarity['task_count']}`",
            f"- Duplicate clusters flagged: `{similarity['cluster_count']}`",
            f"- Largest cluster size: `{similarity['largest_cluster_size']}`",
        ]
    )
    top_clusters = similarity.get("top_clusters", [])
    if top_clusters:
        lines.extend(["", "Top clusters:"])
        for row in top_clusters:
            lines.append(
                f"- Cluster {row['cluster_id']}: size={row['size']}, "
                f"avg_similarity={row['average_similarity']}, members={', '.join(row['members'])}"
            )
    else:
        lines.extend(["", "- No clusters above threshold."])

    lines.extend(
        [
            "",
            "## Originality Marker Scan",
            "",
            f"- Method: `{originality['method']}`",
            f"- Task files scanned: `{originality['task_file_count']}`",
            f"- Flagged files: `{originality['flagged_files_count']}`",
        ]
    )
    flagged = originality.get("flagged_files", [])
    if flagged:
        lines.extend(["", "Flag details:"])
        for row in flagged[:20]:
            lines.append(
                f"- `{row['task_id']}` `{row['file']}` marker=`{row['marker']}` snippet=`{row['snippet']}`"
            )
    else:
        lines.extend(["", "- No external-source markers detected in task files."])

    lines.append("")
    return "\n".join(lines)


def write_provenance_artifacts(
    *,
    seed: int | None = None,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    max_clusters: int = DEFAULT_MAX_CLUSTERS,
) -> dict[str, Any]:
    payload = build_provenance_payload(
        seed=seed,
        similarity_threshold=similarity_threshold,
        max_clusters=max_clusters,
    )
    root = _pack_root()
    (root / "provenance.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (root / "PROVENANCE.md").write_text(render_provenance_markdown(payload), encoding="utf-8")
    return payload


def validate_provenance_files(metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    root = _pack_root()
    errors: list[str] = []
    json_path = root / "provenance.json"
    markdown_path = root / "PROVENANCE.md"
    if not json_path.exists():
        errors.append(f"Missing provenance manifest: {json_path}")
        return False, errors
    if not markdown_path.exists():
        errors.append(f"Missing provenance markdown: {markdown_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("pack_name") != metadata.get("pack_name"):
        errors.append("provenance.json pack_name does not match metadata.json")
    if int(payload.get("seed", -1)) != int(metadata.get("generator_seed", -2)):
        errors.append("provenance.json seed does not match metadata.generator_seed")

    generator = payload.get("generator", {})
    if not isinstance(generator, dict) or not generator.get("version"):
        errors.append("provenance.json missing generator.version")

    statement = payload.get("statement", {})
    if not isinstance(statement, dict) or not statement.get("synthetic_tasks"):
        errors.append("provenance.json missing synthetic task statement")
    license_text = str(statement.get("task_content_license", "")).lower()
    if "mit" not in license_text:
        errors.append("provenance.json task content license must mention MIT")

    contamination = payload.get("contamination", {})
    did_not = " ".join(contamination.get("did_not", [])) if isinstance(contamination, dict) else ""
    limitations = " ".join(contamination.get("limitations", [])) if isinstance(contamination, dict) else ""
    if "web scraping" not in did_not.lower():
        errors.append("provenance.json contamination.did_not should include no web scraping statement")
    if "benchmark" not in did_not.lower():
        errors.append("provenance.json contamination.did_not should include no benchmark copying statement")
    if "pretraining" not in limitations.lower():
        errors.append("provenance.json contamination.limitations should acknowledge pretraining similarity risk")

    checks = payload.get("checks", {})
    similarity_scan = checks.get("similarity_scan", {}) if isinstance(checks, dict) else {}
    originality_scan = checks.get("originality_scan", {}) if isinstance(checks, dict) else {}
    if int(similarity_scan.get("task_count", 0)) != int(metadata["counts"]["total"]):
        errors.append("provenance.json similarity scan task_count mismatch")
    if int(originality_scan.get("flagged_files_count", -1)) < 0:
        errors.append("provenance.json originality scan missing flagged_files_count")
    elif int(originality_scan.get("flagged_files_count", 0)) > 0:
        errors.append("provenance.json originality scan flagged external-source markers")

    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate task_pack_v2 provenance manifest and checks.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--similarity-threshold", type=float, default=DEFAULT_SIMILARITY_THRESHOLD)
    parser.add_argument("--max-clusters", type=int, default=DEFAULT_MAX_CLUSTERS)
    parser.add_argument("--fail-on-overlap", action="store_true")
    args = parser.parse_args()

    payload = write_provenance_artifacts(
        seed=args.seed,
        similarity_threshold=args.similarity_threshold,
        max_clusters=args.max_clusters,
    )
    similarity = payload["checks"]["similarity_scan"]
    originality = payload["checks"]["originality_scan"]
    print(
        f"Wrote provenance manifest for {payload['pack_name']} "
        f"(clusters={similarity['cluster_count']}, flagged_files={originality['flagged_files_count']})."
    )

    if args.fail_on_overlap and int(similarity["cluster_count"]) > 0:
        raise SystemExit(1)
    if int(originality["flagged_files_count"]) > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
