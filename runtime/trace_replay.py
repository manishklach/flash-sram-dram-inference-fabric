from __future__ import annotations

import csv
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .buffer_pool import DRAMBufferPool
from .flash_io import AsyncFlashReader, FlashIOConfig, FlashLayoutEntry, IORequest, IOStatus

logger = logging.getLogger(__name__)


@dataclass
class ReplayEvent:
    step: int
    token_id: int
    object_id: str
    object_type: str
    size_bytes: int
    deadline_step: int
    is_critical: bool
    layer_id: int = 0


@dataclass
class ReplayConfig:
    compute_time_us: float = 250.0
    dram_capacity_gb: int = 8
    slot_size_bytes: int = 4_194_304
    lookahead_steps: int = 12
    warmup_steps: int = 24
    device_path: str | Path = "/dev/nvme0n1"


@dataclass
class ReplayMetrics:
    total_events: int = 0
    sram_hits: int = 0
    dram_hits: int = 0
    flash_reads: int = 0
    flash_bytes_read: int = 0
    sync_flash_policy_failures: int = 0
    late_prefetches: int = 0
    total_latency_us: float = 0.0
    total_time_seconds: float = 0.0

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class TraceReplayer:
    def __init__(self, config: ReplayConfig, flash_reader: AsyncFlashReader | None = None):
        self.config = config
        self.flash_reader = flash_reader or AsyncFlashReader(
            FlashIOConfig(device_path=config.device_path)
        )
        dram_bytes = config.dram_capacity_gb * 1024 * 1024 * 1024
        self.buffer_pool = DRAMBufferPool(dram_bytes, config.slot_size_bytes)

    def load_trace_csv(self, path: str | Path) -> list[ReplayEvent]:
        events: list[ReplayEvent] = []
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append(ReplayEvent(
                    step=int(row["step"]),
                    token_id=int(row.get("token_id", -1)),
                    object_id=row["object_id"],
                    object_type=row.get("object_type", "KV_BLOCK"),
                    size_bytes=int(row["size_bytes"]),
                    deadline_step=int(row.get("deadline_step", row["step"])),
                    is_critical=row.get("is_critical", "true").lower() == "true",
                    layer_id=int(row.get("layer_id", 0)),
                ))
        return events

    def load_trace_json(self, path: str | Path) -> list[ReplayEvent]:
        with open(path) as f:
            data = json.load(f)
        return [ReplayEvent(**item) for item in data]

    def build_layout(self, events: Iterable[ReplayEvent]) -> dict[str, FlashLayoutEntry]:
        flash_objects: dict[str, ReplayEvent] = {}
        for e in events:
            flash_objects[e.object_id] = e
        offset = 0
        layout: dict[str, FlashLayoutEntry] = {}
        for object_id in sorted(flash_objects.keys()):
            size = flash_objects[object_id].size_bytes
            layout[object_id] = FlashLayoutEntry(
                object_id=object_id,
                offset=offset,
                size_bytes=size,
                compressed_size_bytes=None,
            )
            offset += size
        return layout

    def replay(self, events: list[ReplayEvent], prefetch: bool = True) -> ReplayMetrics:
        self.flash_reader.initialize()
        layout = self.load_layout(events)
        for entry in layout.values():
            self.flash_reader.register_layout(entry)

        ordered = sorted(events, key=lambda e: e.step)
        metrics = ReplayMetrics()
        prefetched: set[str] = set()
        t0 = time.monotonic()

        for i, event in enumerate(ordered):
            metrics.total_events += 1
            event_latency = self.config.compute_time_us

            if self.buffer_pool.find_by_object(event.object_id):
                metrics.dram_hits += 1
                slot = self.buffer_pool.find_by_object(event.object_id)
                if slot:
                    self.buffer_pool.release(event.object_id)
            else:
                if prefetch and i < len(ordered) - 1:
                    for lookahead in range(1, self.config.lookahead_steps + 1):
                        if i + lookahead >= len(ordered):
                            break
                        future = ordered[i + lookahead]
                        if future.object_id not in prefetched:
                            req = self.flash_reader.submit_read(future.object_id)
                            if req is not None:
                                prefetched.add(future.object_id)

                req = self.flash_reader.submit_read(event.object_id)
                if req is None:
                    metrics.sync_flash_policy_failures += 1
                else:
                    result = self.flash_reader.wait_completion(event.object_id, timeout=10.0)
                    if result and result.status == IOStatus.COMPLETED:
                        metrics.flash_reads += 1
                        metrics.flash_bytes_read += event.size_bytes
                    else:
                        metrics.sync_flash_policy_failures += 1

                access_us = (event.size_bytes / (7_000_000_000 / 8)) * 1_000_000
                event_latency += access_us

            metrics.total_latency_us += event_latency

        metrics.total_time_seconds = time.monotonic() - t0
        self.flash_reader.close()
        return metrics