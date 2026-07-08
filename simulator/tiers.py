from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryObject:
    object_id: str
    object_type: str
    size_bytes: int
    layer_id: int | None = None
    head_id: int | None = None
    expert_id: int | None = None
    session_id: str | None = None
    token_start: int | None = None
    token_end: int | None = None
    compressed: bool = False
    temperature: float = 0.0
    last_access_step: int = 0
    predicted_next_use_step: int | None = None

    def __hash__(self) -> int:
        return hash(self.object_id)


@dataclass
class TransferRequest:
    object_id: str
    size_bytes: int
    submit_step: int
    deadline_step: int
    is_critical: bool
    target_tier: str


class TierState(ABC):
    def __init__(self, capacity_bytes: int) -> None:
        self.capacity_bytes = capacity_bytes
        self._resident: dict[str, MemoryObject] = {}
        self._resident_order: deque[str] = deque()
        self._resident_bytes = 0

    @property
    def remaining_bytes(self) -> int:
        return self.capacity_bytes - self._resident_bytes

    @property
    def utilization_pct(self) -> float:
        return 100.0 * self._resident_bytes / self.capacity_bytes if self.capacity_bytes > 0 else 0.0

    @property
    def resident_count(self) -> int:
        return len(self._resident)

    def contains(self, object_id: str) -> bool:
        return object_id in self._resident

    def get(self, object_id: str) -> MemoryObject | None:
        return self._resident.get(object_id)

    def add(self, obj: MemoryObject) -> None:
        self._resident[obj.object_id] = obj
        self._resident_order.append(obj.object_id)
        self._resident_bytes += obj.size_bytes

    def remove(self, object_id: str) -> MemoryObject | None:
        obj = self._resident.pop(object_id, None)
        if obj is not None:
            self._resident_bytes -= obj.size_bytes
        return obj

    def touch(self, object_id: str) -> None:
        if object_id in self._resident:
            self._resident_order.remove(object_id)
            self._resident_order.append(object_id)

    @abstractmethod
    def transfer_time_us(self, size_bytes: int) -> float:
        ...

    def evict_one(self) -> MemoryObject | None:
        while self._resident_order:
            candidate_id = self._resident_order.popleft()
            obj = self._resident.pop(candidate_id, None)
            if obj is not None:
                self._resident_bytes -= obj.size_bytes
                return obj
        return None

    def evict_objects(self, count: int) -> list[MemoryObject]:
        evicted: list[MemoryObject] = []
        for _ in range(count):
            obj = self.evict_one()
            if obj is None:
                break
            evicted.append(obj)
        return evicted

    def as_dict(self) -> dict[str, Any]:
        return {
            "capacity_bytes": self.capacity_bytes,
            "resident_bytes": self._resident_bytes,
            "resident_count": self.resident_count,
            "utilization_pct": self.utilization_pct,
        }


class SRAMTier(TierState):
    def __init__(self, capacity_mb: int = 64, latency_ns: int = 5, bandwidth_gbps: int = 1000):
        super().__init__(capacity_bytes=capacity_mb * 1_048_576)
        self.latency_ns = latency_ns
        self.bandwidth_gbps = bandwidth_gbps

    def transfer_time_us(self, size_bytes: int) -> float:
        bytes_per_us = self.bandwidth_gbps * 1000.0 / 8.0
        return (self.latency_ns / 1000.0) + (size_bytes / bytes_per_us) if bytes_per_us > 0 else 0.0


class DRAMTier(TierState):
    def __init__(self, capacity_gb: int = 8, latency_ns: int = 80, bandwidth_gbps: int = 100):
        super().__init__(capacity_bytes=capacity_gb * 1_073_741_824)
        self.latency_ns = latency_ns
        self.bandwidth_gbps = bandwidth_gbps

    def transfer_time_us(self, size_bytes: int) -> float:
        bytes_per_us = self.bandwidth_gbps * 1000.0 / 8.0
        return (self.latency_ns / 1000.0) + (size_bytes / bytes_per_us) if bytes_per_us > 0 else 0.0


class FlashTier(TierState):
    def __init__(
        self,
        capacity_tb: int = 4,
        read_latency_us: int = 80,
        seq_bw_gbps: int = 7,
        rand_read_iops: int = 1_000_000,
        queue_depth: int = 64,
    ):
        super().__init__(capacity_bytes=capacity_tb * 1_099_511_627_776)
        self.read_latency_us = read_latency_us
        self.seq_bw_gbps = seq_bw_gbps
        self.rand_read_iops = rand_read_iops
        self.queue_depth = queue_depth
        self._in_flight: dict[str, int] = {}
        self._in_flight_bytes: int = 0

    @property
    def in_flight_count(self) -> int:
        return len(self._in_flight)

    @property
    def in_flight_bytes(self) -> int:
        return self._in_flight_bytes

    def submit_read(self, object_id: str, size_bytes: int, *, sequential: bool) -> float:
        self._in_flight[object_id] = size_bytes
        self._in_flight_bytes += size_bytes
        return self.transfer_time_us(size_bytes, sequential=sequential)

    def complete_read(self, object_id: str) -> None:
        size = self._in_flight.pop(object_id, 0)
        self._in_flight_bytes -= size

    def transfer_time_us(self, size_bytes: int, *, sequential: bool = True) -> float:
        if sequential:
            bw = self.seq_bw_gbps
            base = self.read_latency_us
        else:
            bw = (self.rand_read_iops * 4096) * 8 / 1_000_000_000
            base = self.read_latency_us * 2
        bytes_per_us = bw * 1000.0 / 8.0
        wait_stalls = (self.in_flight_count / self.queue_depth) * self.read_latency_us if self.queue_depth > 0 else 0.0
        return base + wait_stalls + (size_bytes / bytes_per_us) if bytes_per_us > 0 else 0.0

    def as_dict(self) -> dict[str, Any]:
        base = super().as_dict()
        base["in_flight_count"] = self.in_flight_count
        base["in_flight_bytes"] = self.in_flight_bytes
        base["queue_depth"] = self.queue_depth
        return base
