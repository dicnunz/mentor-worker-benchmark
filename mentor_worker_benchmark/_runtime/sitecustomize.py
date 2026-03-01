"""Runtime isolation hooks for benchmark task execution."""

from __future__ import annotations

import os
import socket


def _raise_network_block(*args: object, **kwargs: object) -> None:
    raise RuntimeError("Network access is disabled during benchmark task tests.")


if os.environ.get("MWB_BLOCK_NETWORK") == "1":
    socket.create_connection = _raise_network_block  # type: ignore[assignment]

    class _BlockedSocket(socket.socket):
        def connect(self, address: object) -> None:  # type: ignore[override]
            _raise_network_block(address)

    socket.socket = _BlockedSocket  # type: ignore[assignment]
