from __future__ import annotations

import logging
import os
import sys
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


class IOStatus(Enum):
    PENDING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class IORequest:
    object_id: str
    offset: int
    size_bytes: int
    buffer_addr: int
    status: IOStatus = IOStatus.PENDING
    compressed_size: int | None = None


@dataclass
class FlashIOConfig:
    device_path: str | Path = "/dev/nvme0n1"
    namespace_id: int = 1
    fixed_buffer_count: int = 64
    fixed_buffer_size_bytes: int = 4_194_304
    queue_depth: int = 256
    use_compression: bool = True
    compression_algorithm: str = "lz4"
    numa_node: int | None = None
    direct_io: bool = True
    deferred_completion: bool = True


@dataclass
class FlashLayoutEntry:
    object_id: str
    offset: int
    size_bytes: int
    compressed_size_bytes: int | None = None

    @property
    def read_size(self) -> int:
        return self.compressed_size_bytes or self.size_bytes


class AsyncFlashReader:
    def __init__(self, config: FlashIOConfig, layout_map: dict[str, FlashLayoutEntry] | None = None):
        self.config = config
        self.layout_map: dict[str, FlashLayoutEntry] = layout_map or {}
        self._fd: int | None = None
        self._fixed_buffers: list[bytearray] = []
        self._lock = threading.Lock()
        self._in_flight: dict[str, IORequest] = {}
        self._cq: list[IORequest] = []
        self._initialized = False

    def _open_device(self) -> None:
        flags = os.O_RDONLY
        os_sync = getattr(os, "O_SYNC", 0)
        flags |= os_sync
        if self.config.direct_io:
            os_direct = getattr(os, "O_DIRECT", 0)
            flags |= os_direct
        dev_path = str(self.config.device_path)
        self._fd = os.open(dev_path, flags)
        logger.info("Opened %s (fd=%d)", dev_path, self._fd)

    def _allocate_fixed_buffers(self) -> None:
        buf_size = self.config.fixed_buffer_size_bytes
        alignment = 4096
        for i in range(self.config.fixed_buffer_count):
            buf = bytearray(buf_size + alignment)
            self._fixed_buffers.append(buf)
        logger.info(
            "Allocated %d fixed buffers (%d bytes each)",
            self.config.fixed_buffer_count,
            buf_size,
        )

    def initialize(self) -> None:
        if self._initialized:
            return
        self._open_device()
        self._allocate_fixed_buffers()
        self._initialized = True

    def close(self) -> None:
        self._initialized = False
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def register_layout(self, entry: FlashLayoutEntry) -> None:
        self.layout_map[entry.object_id] = entry

    def _read_at(self, fd: int, buf: memoryview, offset: int) -> int:
        raw = bytearray(buf)
        if hasattr(os, "pread"):
            result = os.pread(fd, raw, offset)
            nread = len(result) if isinstance(result, bytes) else result
        else:
            with self._lock:
                old_pos = os.lseek(fd, offset, os.SEEK_SET)
                data = os.read(fd, len(raw))
                nread = len(data)
                raw[:nread] = data[:nread]
        buf[:nread] = raw[:nread]
        return nread

    def submit_read(self, object_id: str) -> IORequest | None:
        entry = self.layout_map.get(object_id)
        if entry is None:
            return None
        if not self._initialized:
            self.initialize()
        with self._lock:
            if object_id in self._in_flight:
                return None
            buffer_idx = hash(object_id) % self.config.fixed_buffer_count
            buf = self._fixed_buffers[buffer_idx]
            request = IORequest(
                object_id=object_id,
                offset=entry.offset,
                size_bytes=entry.read_size,
                buffer_addr=id(buf),
                compressed_size=entry.read_size if entry.compressed_size_bytes else None,
            )
            self._in_flight[object_id] = request
        if self._fd is not None and self.config.deferred_completion:
            buf_view = memoryview(buf)[: entry.read_size]
            nread = self._read_at(self._fd, buf_view, entry.offset)
            if nread != entry.read_size:
                request.status = IOStatus.FAILED
            else:
                request.status = IOStatus.COMPLETED
            with self._lock:
                self._cq.append(request)
                self._in_flight.pop(object_id, None)
        return request

    def poll_completions(self) -> list[IORequest]:
        with self._lock:
            completed = list(self._cq)
            self._cq.clear()
        return completed

    def wait_completion(self, object_id: str, timeout: float = 5.0) -> IORequest | None:
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                for req in self._cq:
                    if req.object_id == object_id:
                        self._cq.remove(req)
                        return req
            time.sleep(0.001)
        return None

    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)