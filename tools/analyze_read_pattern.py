from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def analyze_csv(path: Path) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    by_workload: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_workload[r.get("workload", "unknown")].append(r)

    result: dict[str, Any] = {}
    for wl, group in by_workload.items():
        seq_ratios = []
        sync_fails = []
        accuracies = []
        waste_rates = []
        energies = []
        for r in group:
            try:
                seq_ratios.append(float(r.get("sequential_read_ratio", r.get("seq_ratio", 0))))
                sync_fails.append(int(r.get("sync_flash_policy_failures", r.get("sync_failures", 0))))
                accuracies.append(float(r.get("prefetch_accuracy", r.get("accuracy", 0))))
                waste_rates.append(float(r.get("prefetch_waste_rate", r.get("waste_rate", 0))))
                energies.append(float(r.get("energy_joules", r.get("energy", 0))))
            except (ValueError, TypeError):
                continue

        result[wl] = {
            "num_rows": len(group),
            "avg_seq_ratio": sum(seq_ratios) / len(seq_ratios) if seq_ratios else 0.0,
            "total_sync_failures": sum(sync_fails),
            "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0.0,
            "avg_waste_rate": sum(waste_rates) / len(waste_rates) if waste_rates else 0.0,
            "min_energy_joules": min(energies) if energies else 0.0,
            "max_energy_joules": max(energies) if energies else 0.0,
        }
    return result


def analyze_trace(path: Path) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    if not events:
        return {"num_events": 0}

    object_types: dict[str, int] = defaultdict(int)
    total_bytes = 0
    unique_objects: set[str] = set()
    steps: set[int] = set()
    sequential_runs = 0
    prev_block: int | None = None

    for ev in events:
        otype = ev.get("object_type", "unknown")
        object_types[otype] += 1
        total_bytes += ev.get("size_bytes", 0)
        unique_objects.add(ev.get("object_id", ""))
        steps.add(ev.get("step", 0))

        oid = ev.get("object_id", "")
        if ".block_" in oid:
            suffix = oid.split(".block_", maxsplit=1)[1]
            parts = suffix.split(".")
            try:
                block_id = int(parts[0])
                if prev_ok and block_id == prev_block + 1:
                    sequential_runs += 1
                prev_block = block_id
            except (ValueError, IndexError):
                pass
        prev_ok = True

    return {
        "num_events": len(events),
        "object_types": dict(object_types),
        "total_size_bytes": total_bytes,
        "unique_objects": len(unique_objects),
        "unique_steps": len(steps),
        "sequential_transitions": sequential_runs,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python analyze_read_pattern.py <path> [--type csv|json|jsonl]", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    ftype = "auto"
    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            ftype = sys.argv[idx + 1]

    if ftype == "auto":
        if path.suffix == ".csv":
            ftype = "csv"
        elif path.suffix in (".json",):
            ftype = "json"
        elif path.suffix in (".jsonl", ".jsonlines"):
            ftype = "jsonl"
        else:
            ftype = "jsonl"

    if ftype == "csv":
        result = analyze_csv(path)
    else:
        result = analyze_trace(path)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()