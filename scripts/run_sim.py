from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from simulator.interface_modes import InterfaceMode
from simulator.runner import SimulatorConfig, run_trace
from simulator.workloads import generate_long_context_kv_trace


def main() -> None:
    trace = generate_long_context_kv_trace()
    config = SimulatorConfig()

    print("mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy")
    for mode in (
        InterfaceMode.RAM_EMULATION,
        InterfaceMode.HYBRID,
        InterfaceMode.STREAM_TO_SCRATCHPAD,
    ):
        metrics = run_trace(trace, interface_mode=mode, config=config)
        result = metrics.as_dict()
        print(
            ",".join(
                [
                    mode.value,
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
    for mode in (
        InterfaceMode.RAM_EMULATION,
        InterfaceMode.HYBRID,
        InterfaceMode.STREAM_TO_SCRATCHPAD,
    ):
        metrics = run_trace(trace, interface_mode=mode, config=config)
        print(json.dumps({"mode": mode.value, "metrics": metrics.as_dict()}))


if __name__ == "__main__":
    main()
