from mentor_worker_benchmark.tasks.task_pack_v1.pack import read_pack_metadata
from mentor_worker_benchmark.tasks.task_pack_v1.validate import validate_task_pack


def test_task_pack_v1_counts() -> None:
    metadata = read_pack_metadata()
    counts = metadata["counts"]

    assert counts["total"] == 300
    assert counts["train"] == 200
    assert counts["dev"] == 50
    assert counts["test"] == 50
    assert counts["quick"] == 18


def test_task_pack_v1_categories() -> None:
    metadata = read_pack_metadata()
    expected = {
        "string_regex_parsing",
        "ds_algo",
        "file_io_serialization",
        "concurrency_basics",
        "numerical_edge_cases",
        "multi_file_mini_module",
    }

    assert set(metadata["categories"]) == expected


def test_task_pack_v1_schema_validation() -> None:
    ok, errors = validate_task_pack()
    assert ok, f"task pack validation failed: {errors}"
