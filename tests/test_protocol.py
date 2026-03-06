from __future__ import annotations

import pytest

from mentor_worker_benchmark.protocol import expand_replicate_seeds


def test_expand_replicate_seeds_is_deterministic() -> None:
    first = expand_replicate_seeds(base_seed=1337, replicates=4)
    second = expand_replicate_seeds(base_seed=1337, replicates=4)
    assert first == second
    assert first[0] == 1337


def test_expand_replicate_seeds_are_unique() -> None:
    seeds = expand_replicate_seeds(base_seed=42, replicates=16)
    assert len(seeds) == 16
    assert len(set(seeds)) == 16


def test_expand_replicate_seeds_rejects_invalid_replicate_count() -> None:
    with pytest.raises(ValueError, match="replicates must be >= 1"):
        expand_replicate_seeds(base_seed=1337, replicates=0)
