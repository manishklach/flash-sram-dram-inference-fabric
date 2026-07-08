from dataclasses import dataclass


@dataclass
class StreamingMetrics:
    random_flash_reads: int = 0
    sequential_flash_reads: int = 0
    sequential_read_ratio: float = 0.0
    sync_flash_policy_failures: int = 0
    average_read_size_bytes: float = 0.0
    trace_layout_efficiency: float = 0.0
    redundant_capacity_overhead: float = 0.0

    def recompute_ratios(self) -> None:
        total_reads = self.random_flash_reads + self.sequential_flash_reads
        if total_reads == 0:
            self.sequential_read_ratio = 0.0
            return
        self.sequential_read_ratio = self.sequential_flash_reads / total_reads
