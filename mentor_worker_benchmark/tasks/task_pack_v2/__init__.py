"""Task pack v2 (mini-repo realism corpus)."""

from mentor_worker_benchmark.tasks.task_pack_v2.pack import load_task_pack_v2, read_pack_metadata


def write_provenance_artifacts(*args, **kwargs):
    from mentor_worker_benchmark.tasks.task_pack_v2.provenance import (
        write_provenance_artifacts as _write_provenance_artifacts,
    )

    return _write_provenance_artifacts(*args, **kwargs)

__all__ = ["load_task_pack_v2", "read_pack_metadata", "write_provenance_artifacts"]
