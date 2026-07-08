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
CSV_ARTIFACT = ARTIFACT_DIR / "simulator_matrix.csv"
JSON_ARTIFACT = ARTIFACT_DIR / "simulator_matrix.json"


def _run_workload(name: str, trace, config: SimulatorConfig) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for mode in (
        InterfaceMode.RAM_EMULATION,
        InterfaceMode.HYBRID,
        InterfaceMode.STREAM_TO_SCRATCHPAD,
    ):
        metrics = run_trace(trace, interface_mode=mode, config=config)
        rows.append(
            {
                "workload": name,
                "mode": mode.value,
                "metrics": metrics.as_dict(),
            }
        )
    return rows


def main() -> None:
    config = SimulatorConfig()
    workloads = [
        ("long_context_kv", generate_long_context_kv_trace()),
        ("random_old_context", generate_random_old_context_trace()),
        ("cold_fanout", generate_cold_fanout_trace()),
    ]

    print(
        "workload,mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy,prefetch_waste_rate,dram_evictions"
    )
    results: list[dict[str, object]] = []
    for workload_name, trace in workloads:
        workload_results = _run_workload(workload_name, trace, config)
        results.extend(workload_results)
        for row in workload_results:
            result = row["metrics"]
            print(
                ",".join(
                    [
                        str(row["workload"]),
                        str(row["mode"]),
                        f"{result['p50_token_latency_us']:.1f}",
                        f"{result['p95_token_latency_us']:.1f}",
                        f"{result['p99_token_latency_us']:.1f}",
                        f"{result['sequential_read_ratio']:.3f}",
                        str(int(result["random_flash_reads"])),
                        str(int(result["sequential_flash_reads"])),
                        str(int(result["sync_flash_policy_failures"])),
                        f"{result['prefetch_accuracy']:.3f}",
                        f"{result['prefetch_waste_rate']:.3f}",
                        str(int(result["dram_evictions"])),
                    ]
                )
            )

    print()
    print("# JSON summary")
    for row in results:
        print(json.dumps(row))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    csv_rows: list[dict[str, object]] = []
    for row in results:
        metrics = row["metrics"]
        csv_rows.append(
            {
                "workload": row["workload"],
                "mode": row["mode"],
                "p50_token_latency_us": metrics["p50_token_latency_us"],
                "p95_token_latency_us": metrics["p95_token_latency_us"],
                "p99_token_latency_us": metrics["p99_token_latency_us"],
                "sequential_read_ratio": metrics["sequential_read_ratio"],
                "random_flash_reads": metrics["random_flash_reads"],
                "sequential_flash_reads": metrics["sequential_flash_reads"],
                "sync_flash_policy_failures": metrics["sync_flash_policy_failures"],
                "prefetch_accuracy": metrics["prefetch_accuracy"],
                "prefetch_waste_rate": metrics["prefetch_waste_rate"],
                "dram_evictions": metrics["dram_evictions"],
                "dram_peak_resident_objects": metrics["dram_peak_resident_objects"],
                "sync_flash_miss_rate": metrics["sync_flash_miss_rate"],
            }
        )

    with CSV_ARTIFACT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    with JSON_ARTIFACT.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print()
    print(f"# Wrote artifacts: {CSV_ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"# Wrote artifacts: {JSON_ARTIFACT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
