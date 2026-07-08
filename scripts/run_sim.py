from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulator.interface_modes import InterfaceMode
from simulator.runner import SimulatorConfig, run_trace
from simulator.workloads import generate_long_context_kv_trace, generate_random_old_context_trace


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
    ]

    print(
        "workload,mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy"
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
                    ]
                )
            )

    print()
    print("# JSON summary")
    for row in results:
        print(json.dumps(row))


if __name__ == "__main__":
    main()
