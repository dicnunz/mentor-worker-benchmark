from mentor_worker_benchmark.tasks.task_pack_v2.pack import read_pack_metadata
from mentor_worker_benchmark.tasks.task_pack_v2.provenance import validate_provenance_files


def test_task_pack_v2_provenance_manifest_is_valid() -> None:
    metadata = read_pack_metadata()
    ok, errors = validate_provenance_files(metadata)
    assert ok, f"task pack v2 provenance validation failed: {errors}"
