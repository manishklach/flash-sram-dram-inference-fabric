from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .interface_modes import InterfaceMode
from .metrics import StreamingMetrics
from .traces import AccessEvent


@dataclass(frozen=True)
class SimulatorConfig:
    compute_time_us: float = 250.0
    flash_random_latency_us: float = 80.0
    flash_sequential_overhead_us: float = 20.0
    flash_bandwidth_gbps: float = 7.0
    lookahead_steps: int = 12
    warmup_steps: int = 24


def _transfer_time_us(size_bytes: int, *, bandwidth_gbps: float, base_latency_us: float) -> float:
    bytes_per_us = bandwidth_gbps * 1_000.0
    return base_latency_us + (size_bytes / bytes_per_us)


def run_trace(
    events: Iterable[AccessEvent],
    *,
    interface_mode: InterfaceMode,
    config: SimulatorConfig | None = None,
) -> StreamingMetrics:
    config = config or SimulatorConfig()
    ordered_events = sorted(events, key=lambda event: event.step)
    future_by_step = {event.step: event for event in ordered_events}
    prefetched_ready_step: dict[str, int] = {}
    used_prefetch: set[str] = set()
    token_latencies: dict[int, float] = defaultdict(float)
    metrics = StreamingMetrics()

    for event in ordered_events:
        metrics.total_events += 1

        if interface_mode in {InterfaceMode.STREAM_TO_SCRATCHPAD, InterfaceMode.HYBRID}:
            allow_prefetch = interface_mode == InterfaceMode.STREAM_TO_SCRATCHPAD or event.step >= config.warmup_steps
            if allow_prefetch:
                for lookahead_step in range(event.step + 1, event.step + config.lookahead_steps + 1):
                    future = future_by_step.get(lookahead_step)
                    if future is None:
                        continue
                    if future.object_id in prefetched_ready_step:
                        continue
                    ready_step = event.step + _transfer_time_us(
                        future.size_bytes,
                        bandwidth_gbps=config.flash_bandwidth_gbps,
                        base_latency_us=config.flash_sequential_overhead_us,
                    ) / config.compute_time_us
                    prefetched_ready_step[future.object_id] = int(ready_step)
                    metrics.prefetched_objects += 1
                    metrics.record_read(future.size_bytes, sequential=True)

        event_latency = config.compute_time_us
        ready_step = prefetched_ready_step.get(event.object_id)

        if ready_step is not None and ready_step <= event.step:
            metrics.dram_hits += 1
            if event.object_id not in used_prefetch:
                used_prefetch.add(event.object_id)
                metrics.useful_prefetches += 1
        else:
            if ready_step is not None and ready_step > event.step:
                metrics.late_prefetches += 1

            event_latency += _transfer_time_us(
                event.size_bytes,
                bandwidth_gbps=config.flash_bandwidth_gbps,
                base_latency_us=config.flash_random_latency_us,
            )
            metrics.record_read(event.size_bytes, sequential=False)
            if event.is_critical:
                metrics.sync_flash_policy_failures += 1

        if event.layer_id == 0:
            metrics.sram_hits += 1

        token_latencies[event.token_id] += event_latency

    metrics.token_latencies_us = [token_latencies[token_id] for token_id in sorted(token_latencies)]
    metrics.redundant_capacity_overhead = 0.05 if interface_mode == InterfaceMode.STREAM_TO_SCRATCHPAD else 0.0
    metrics.recompute_ratios()
    return metrics
