from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulator.interface_modes import InterfaceMode
from simulator.policies import (
    FixedWindowPrefetchPolicy,
    LRUPolicy,
    NoPrefetchPolicy,
    OraclePolicy,
    PredictivePolicy,
)
from simulator.runner import SimulatorConfig, run_trace
from simulator.workloads import (
    generate_cold_fanout_trace,
    generate_long_context_kv_trace,
    generate_moe_trace,
    generate_rag_staging_trace,
    generate_random_old_context_trace,
    generate_weight_layer_trace,
)

ARTIFACT_DIR = REPO_ROOT / "benchmarks" / "results"
CSV_ARTIFACT = ARTIFACT_DIR / "simulator_matrix.csv"
JSON_ARTIFACT = ARTIFACT_DIR / "simulator_matrix.json"

WORKLOADS = [
    ("long_context_kv", generate_long_context_kv_trace),
    ("random_old_context", generate_random_old_context_trace),
    ("cold_fanout", generate_cold_fanout_trace),
    ("weight_layer", generate_weight_layer_trace),
    ("moe_low_entropy", lambda: generate_moe_trace(entropy=0.1)),
    ("moe_high_entropy", lambda: generate_moe_trace(entropy=0.8)),
    ("rag", generate_rag_staging_trace),
]

INTERFACE_MODES = [
    InterfaceMode.RAM_EMULATION,
    InterfaceMode.HYBRID,
    InterfaceMode.STREAM_TO_SCRATCHPAD,
]

POLICIES = [
    ("no_prefetch", NoPrefetchPolicy()),
    ("lru", LRUPolicy()),
    ("fixed_window", FixedWindowPrefetchPolicy()),
    ("predictive", PredictivePolicy()),
    ("oracle", OraclePolicy()),
]


def _run_matrix() -> list[dict]:
    rows = []
    config = SimulatorConfig()
    for workload_name, trace_fn in WORKLOADS:
        trace = trace_fn()
        for mode in INTERFACE_MODES:
            metrics = run_trace(trace, interface_mode=mode, config=config)
            row = {
                "workload": workload_name,
                "mode": mode.value,
                "policy": "fixed_window",
            }
            row.update(metrics.as_dict())
            rows.append(row)
    return rows


def main() -> None:
    print("workload,mode,policy,p50_us,p95_us,p99_us,seq_ratio,sync_failures,prefetch_accuracy,prefetch_waste_rate,energy_joules")
    results = _run_matrix()
    for row in results:
        print(
            "%s,%s,%s,%.1f,%.1f,%.1f,%.3f,%d,%.3f,%.3f,%.6f" % (
                row["workload"], row["mode"], row["policy"],
                row["p50_token_latency_us"], row["p95_token_latency_us"],
                row["p99_token_latency_us"], row["sequential_read_ratio"],
                int(row["sync_flash_policy_failures"]),
                row["prefetch_accuracy"], row["prefetch_waste_rate"],
                row["energy_joules"],
            )
        )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_ARTIFACT.open("w", newline="", encoding="utf-8") as handle:
        if results:
            writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
            writer.writeheader()
            writer.writerows(results)
    with JSON_ARTIFACT.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print("\n# Wrote artifacts: %s" % CSV_ARTIFACT.relative_to(REPO_ROOT))
    print("# Wrote artifacts: %s" % JSON_ARTIFACT.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
