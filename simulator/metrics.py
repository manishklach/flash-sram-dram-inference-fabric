from dataclasses import dataclass, field
from statistics import median


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


@dataclass
class StreamingMetrics:
    random_flash_reads: int = 0
    sequential_flash_reads: int = 0
    sequential_read_ratio: float = 0.0
    sync_flash_policy_failures: int = 0
    average_read_size_bytes: float = 0.0
    trace_layout_efficiency: float = 0.0
    redundant_capacity_overhead: float = 0.0
    total_read_size_bytes: int = 0
    token_latencies_us: list[float] = field(default_factory=list)
    prefetched_objects: int = 0
    useful_prefetches: int = 0
    wasted_prefetches: int = 0
    late_prefetches: int = 0
    dram_evictions: int = 0
    dram_peak_resident_objects: int = 0
    dram_hits: int = 0
    sram_hits: int = 0
    total_events: int = 0
    energy_joules: float = 0.0
    sram_promotions: int = 0
    dram_promotions: int = 0
    dram_evictions_to_flash: int = 0
    sram_utilization_pct: float = 0.0
    dram_utilization_pct: float = 0.0
    flash_queue_peak: int = 0
    flash_queue_avg: float = 0.0
    flash_bandwidth_util_pct: float = 0.0

    def recompute_ratios(self) -> None:
        total_reads = self.random_flash_reads + self.sequential_flash_reads
        if total_reads == 0:
            self.sequential_read_ratio = 0.0
            self.average_read_size_bytes = 0.0
        else:
            self.sequential_read_ratio = self.sequential_flash_reads / total_reads
            self.average_read_size_bytes = self.total_read_size_bytes / total_reads
        if self.prefetched_objects == 0:
            self.trace_layout_efficiency = 0.0
        else:
            self.trace_layout_efficiency = self.useful_prefetches / self.prefetched_objects

    def record_read(self, size_bytes: int, *, sequential: bool) -> None:
        self.total_read_size_bytes += size_bytes
        if sequential:
            self.sequential_flash_reads += 1
        else:
            self.random_flash_reads += 1

    def as_dict(self) -> dict[str, float]:
        self.recompute_ratios()
        return {
            "p50_token_latency_us": median(self.token_latencies_us) if self.token_latencies_us else 0.0,
            "p95_token_latency_us": percentile(self.token_latencies_us, 0.95),
            "p99_token_latency_us": percentile(self.token_latencies_us, 0.99),
            "random_flash_reads": float(self.random_flash_reads),
            "sequential_flash_reads": float(self.sequential_flash_reads),
            "sequential_read_ratio": self.sequential_read_ratio,
            "sync_flash_policy_failures": float(self.sync_flash_policy_failures),
            "average_read_size_bytes": self.average_read_size_bytes,
            "trace_layout_efficiency": self.trace_layout_efficiency,
            "redundant_capacity_overhead": self.redundant_capacity_overhead,
            "prefetch_accuracy": (
                self.useful_prefetches / self.prefetched_objects if self.prefetched_objects else 0.0
            ),
            "prefetch_waste_rate": (
                self.wasted_prefetches / self.prefetched_objects if self.prefetched_objects else 0.0
            ),
            "late_prefetch_rate": (
                self.late_prefetches / self.prefetched_objects if self.prefetched_objects else 0.0
            ),
            "dram_evictions": float(self.dram_evictions),
            "dram_peak_resident_objects": float(self.dram_peak_resident_objects),
            "dram_hit_rate": self.dram_hits / self.total_events if self.total_events else 0.0,
            "sram_hit_rate": self.sram_hits / self.total_events if self.total_events else 0.0,
            "sync_flash_miss_rate": (
                self.sync_flash_policy_failures / self.total_events if self.total_events else 0.0
            ),
            "energy_joules": self.energy_joules,
            "sram_promotions": float(self.sram_promotions),
            "dram_promotions": float(self.dram_promotions),
            "sram_utilization_pct": self.sram_utilization_pct,
            "dram_utilization_pct": self.dram_utilization_pct,
            "flash_queue_peak": float(self.flash_queue_peak),
        }
