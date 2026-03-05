from mentor_worker_benchmark.tasks.task_pack_v2.pack import read_pack_metadata
from mentor_worker_benchmark.tasks.task_pack_v2.validate import validate_task_pack


def test_task_pack_v2_counts() -> None:
    metadata = read_pack_metadata()
    counts = metadata["counts"]

    assert counts["total"] == 652
    assert counts["train"] == 444
    assert counts["dev"] == 104
    assert counts["test"] == 104
    assert counts["quick"] == 30


def test_task_pack_v2_categories() -> None:
    metadata = read_pack_metadata()
    categories = set(metadata["categories"])
    assert {
        "string_regex_parsing",
        "ds_algo",
        "file_io_serialization",
        "concurrency_basics",
        "numerical_edge_cases",
        "multi_file_mini_module",
        "mini_repo_bugfix",
        "mini_repo_feature",
        "mini_repo_cli",
        "mini_repo_tool_sim",
    } == categories


def test_task_pack_v2_difficulty_distribution() -> None:
    metadata = read_pack_metadata()
    tasks = metadata["tasks"]
    counts = {"easy": 0, "medium": 0, "hard": 0}
    for row in tasks:
        counts[row["difficulty"]] += 1
    assert counts == {"easy": 228, "medium": 293, "hard": 131}


def test_task_pack_v2_schema_validation() -> None:
    ok, errors = validate_task_pack()
    assert ok, f"task pack v2 validation failed: {errors}"
