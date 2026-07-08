from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulator.interface_modes import InterfaceMode
from simulator.runner import SimulatorConfig, run_trace
from simulator.workloads import (
    generate_cold_fanout_trace,
    generate_long_context_kv_trace,
    generate_random_old_context_trace,
)

ARTIFACT_DIR = REPO_ROOT / "benchmarks" / "results"
CSV_ARTIFACT = ARTIFACT_DIR / "lookahead_dram_sweep.csv"
JSON_ARTIFACT = ARTIFACT_DIR / "lookahead_dram_sweep.json"


def main() -> None:
    workloads = [
        ("long_context_kv", generate_long_context_kv_trace()),
        ("random_old_context", generate_random_old_context_trace()),
        ("cold_fanout", generate_cold_fanout_trace()),
    ]
    dram_capacity_mb_values = [32, 64, 128, 256, 512]
    lookahead_values = [4, 8, 12, 16, 24]
    modes = [
        InterfaceMode.HYBRID,
        InterfaceMode.STREAM_TO_SCRATCHPAD,
    ]

    print(
        "workload,mode,dram_capacity_mb,lookahead_steps,p95_us,p99_us,seq_ratio,sync_failures,dram_evictions,prefetch_waste_rate"
    )

    rows: list[dict[str, object]] = []
    for dram_capacity_mb in dram_capacity_mb_values:
        for lookahead_steps in lookahead_values:
            config = SimulatorConfig(
                dram_capacity_bytes=dram_capacity_mb * 1_048_576,
                lookahead_steps=lookahead_steps,
            )
            for workload_name, trace in workloads:
                for mode in modes:
                    metrics = run_trace(trace, interface_mode=mode, config=config).as_dict()
                    row = {
                        "workload": workload_name,
                        "mode": mode.value,
                        "dram_capacity_mb": dram_capacity_mb,
                        "lookahead_steps": lookahead_steps,
                        "p50_token_latency_us": metrics["p50_token_latency_us"],
                        "p95_token_latency_us": metrics["p95_token_latency_us"],
                        "p99_token_latency_us": metrics["p99_token_latency_us"],
                        "sequential_read_ratio": metrics["sequential_read_ratio"],
                        "sync_flash_policy_failures": metrics["sync_flash_policy_failures"],
                        "dram_evictions": metrics["dram_evictions"],
                        "prefetch_accuracy": metrics["prefetch_accuracy"],
                        "prefetch_waste_rate": metrics["prefetch_waste_rate"],
                        "sync_flash_miss_rate": metrics["sync_flash_miss_rate"],
                    }
                    rows.append(row)
                    print(
                        ",".join(
                            [
                                workload_name,
                                mode.value,
                                str(dram_capacity_mb),
                                str(lookahead_steps),
                                f"{metrics['p95_token_latency_us']:.1f}",
                                f"{metrics['p99_token_latency_us']:.1f}",
                                f"{metrics['sequential_read_ratio']:.3f}",
                                str(int(metrics["sync_flash_policy_failures"])),
                                str(int(metrics["dram_evictions"])),
                                f"{metrics['prefetch_waste_rate']:.3f}",
                            ]
                        )
                    )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_ARTIFACT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with JSON_ARTIFACT.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2)

    print()
    print(f"# Wrote artifacts: {CSV_ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"# Wrote artifacts: {JSON_ARTIFACT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
