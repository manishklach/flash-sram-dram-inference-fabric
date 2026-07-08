from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from .interface_modes import InterfaceMode
from .metrics import StreamingMetrics
from .tiers import DRAMTier, FlashTier, MemoryObject, SRAMTier
from .traces import AccessEvent


@dataclass(frozen=True)
class SimulatorConfig:
    sram: SRAMTier = field(default_factory=lambda: SRAMTier(capacity_mb=64))
    dram: DRAMTier = field(default_factory=lambda: DRAMTier(capacity_gb=8))
    flash: FlashTier = field(default_factory=lambda: FlashTier(capacity_tb=4))
    compute_time_us: float = 250.0
    lookahead_steps: int = 12
    warmup_steps: int = 24
    locality_block_threshold: int = 4
    useful_prefetch_window_steps: int = 8


def _extract_block_id(object_id: str) -> int | None:
    marker = ".block_"
    if marker not in object_id:
        return None
    suffix = object_id.split(marker, maxsplit=1)[1]
    try:
        return int(suffix)
    except ValueError:
        return None


def _can_predictably_prefetch(current: AccessEvent, future: AccessEvent, config: SimulatorConfig) -> bool:
    current_block = _extract_block_id(current.object_id)
    future_block = _extract_block_id(future.object_id)
    if current_block is None or future_block is None:
        return False
    return abs(future_block - current_block) <= config.locality_block_threshold


def _object_from_event(event: AccessEvent) -> MemoryObject:
    return MemoryObject(
        object_id=event.object_id,
        object_type=event.object_type,
        size_bytes=event.size_bytes,
        layer_id=event.layer_id,
        session_id=event.session_id,
    )


def _transfer_energy_joules(size_bytes: int, tier_key: str) -> float:
    pj_per_bit = {"sram": 0.75, "dram": 3.5, "flash_seq": 0.035, "flash_rand": 0.15}
    bits = size_bytes * 8
    return (bits * pj_per_bit.get(tier_key, 3.5)) / 1_000_000_000_000


def _make_room(tier, size_bytes: int, metrics, already_useful: set[str] | None = None, already_wasted: set[str] | None = None, prefetched_ready_step: dict | None = None) -> bool:
    if size_bytes <= tier.remaining_bytes:
        return True
    needed = size_bytes - tier.remaining_bytes
    freed = 0
    while freed < needed:
        evicted = tier.evict_one()
        if evicted is None:
            return False
        freed += evicted.size_bytes
        metrics.dram_evictions += 1
        if already_useful is not None and already_wasted is not None and prefetched_ready_step is not None:
            if evicted.object_id not in already_useful and evicted.object_id in prefetched_ready_step:
                if evicted.object_id not in already_wasted:
                    already_wasted.add(evicted.object_id)
                    metrics.wasted_prefetches += 1
    return True


def run_trace(
    events: Iterable[AccessEvent],
    *,
    interface_mode: InterfaceMode,
    config: SimulatorConfig | None = None,
) -> StreamingMetrics:
    config = config or SimulatorConfig()
    sram = config.sram
    dram = config.dram
    flash = config.flash

    ordered_events = sorted(events, key=lambda item: item.step)
    future_by_step = {event.step: event for event in ordered_events}
    prefetched_ready_step: dict[str, int] = {}
    prefetched_issue_step: dict[str, int] = {}
    already_useful: set[str] = set()
    already_wasted: set[str] = set()
    token_latencies: dict[int, float] = defaultdict(float)
    metrics = StreamingMetrics()

    for event in ordered_events:
        metrics.total_events += 1

        can_prefetch = interface_mode in {InterfaceMode.STREAM_TO_SCRATCHPAD, InterfaceMode.HYBRID}
        allow_prefetch = can_prefetch and (
            interface_mode == InterfaceMode.STREAM_TO_SCRATCHPAD
            or event.step >= config.warmup_steps
        )

        if allow_prefetch:
            for lookahead_step in range(event.step + 1, event.step + config.lookahead_steps + 1):
                future = future_by_step.get(lookahead_step)
                if future is None:
                    continue
                if future.object_id in prefetched_ready_step:
                    continue
                if not _can_predictably_prefetch(event, future, config):
                    continue

                size = future.size_bytes
                if flash.in_flight_count >= flash.queue_depth:
                    continue

                future_obj = _object_from_event(future)
                if not _make_room(dram, size, metrics, already_useful, already_wasted, prefetched_ready_step):
                    continue

                ttf = flash.submit_read(future.object_id, size, sequential=True)
                ready_step = event.step + int(ttf / config.compute_time_us)

                dram.add(future_obj)
                metrics.dram_peak_resident_objects = max(
                    metrics.dram_peak_resident_objects, dram.resident_count
                )

                prefetched_ready_step[future.object_id] = ready_step
                prefetched_issue_step[future.object_id] = event.step
                metrics.prefetched_objects += 1
                metrics.record_read(size, sequential=True)
                metrics.energy_joules += _transfer_energy_joules(size, "flash_seq")
                flash.complete_read(future.object_id)

        event_latency = config.compute_time_us

        if sram.contains(event.object_id):
            metrics.sram_hits += 1
            sram.touch(event.object_id)
            metrics.energy_joules += _transfer_energy_joules(event.size_bytes, "sram")

        elif dram.contains(event.object_id):
            metrics.dram_hits += 1
            dram.touch(event.object_id)
            dram_to_sram_us = dram.transfer_time_us(event.size_bytes)
            sram_obj = _object_from_event(event)

            if _make_room(sram, event.size_bytes, metrics, already_useful, already_wasted, prefetched_ready_step):
                sram.add(sram_obj)
                metrics.sram_promotions += 1
                event_latency += dram_to_sram_us
                metrics.energy_joules += _transfer_energy_joules(event.size_bytes, "dram")

            if event.object_id in prefetched_ready_step and event.object_id not in already_useful:
                already_useful.add(event.object_id)
                issued_at = prefetched_issue_step.get(event.object_id, event.step)
                if event.step - issued_at <= config.useful_prefetch_window_steps:
                    metrics.useful_prefetches += 1
                else:
                    metrics.wasted_prefetches += 1

        else:
            if event.object_id in prefetched_ready_step:
                ready = prefetched_ready_step[event.object_id]
                if ready > event.step:
                    metrics.late_prefetches += 1

            random_us = flash.transfer_time_us(event.size_bytes, sequential=False)
            event_latency += random_us
            metrics.record_read(event.size_bytes, sequential=False)
            metrics.energy_joules += _transfer_energy_joules(event.size_bytes, "flash_rand")

            if event.is_critical:
                metrics.sync_flash_policy_failures += 1

            future_obj = _object_from_event(event)
            if _make_room(dram, event.size_bytes, metrics, already_useful, already_wasted, prefetched_ready_step):
                dram.add(future_obj)

        token_latencies[event.token_id] += event_latency

    # End-of-run: objects still in prefetched_ready_step that were never useful count as waste
    for oid in prefetched_ready_step:
        if oid not in already_useful and oid not in already_wasted:
            metrics.wasted_prefetches += 1

    metrics.token_latencies_us = [token_latencies[tid] for tid in sorted(token_latencies)]
    metrics.recompute_ratios()
    metrics.sram_utilization_pct = sram.utilization_pct
    metrics.dram_utilization_pct = dram.utilization_pct
    metrics.flash_queue_peak = max(metrics.flash_queue_peak, flash.in_flight_count)
    return metrics

