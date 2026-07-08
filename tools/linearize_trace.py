\"\"\"Read trace JSONL, group co-accessed objects, emit linearized layout metadata.\"\"\"

from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LinearizedBundle:
    bundle_id: str
    objects: list[str]
    flash_offset_bytes: int
    total_size_bytes: int
    execution_order: int


def linearize(
    trace_path: Path,
    *,
    page_alignment: int = 1_048_576,
    bundle_strategy: str = "layer",
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    with open(trace_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    if bundle_strategy == "layer":
        groups: dict[str, list[str]] = defaultdict(list)
        for ev in events:
            layer = ev.get("layer_id", 0)
            oid = ev.get("object_id", "")
            if oid:
                groups[f"layer_{layer:03d}_bundle"].append(oid)

        bundles: list[dict[str, Any]] = []
        offset = 0
        for idx, (bundle_id, objs) in enumerate(sorted(groups.items())):
            unique = list(dict.fromkeys(objs))
            total_size = 0
            for ev in events:
                if ev.get("object_id") in unique:
                    total_size += ev.get("size_bytes", 0)
            aligned = ((total_size + page_alignment - 1) // page_alignment) * page_alignment
            bundles.append({
                "bundle_id": bundle_id,
                "objects": unique,
                "flash_offset_bytes": offset,
                "total_size_bytes": aligned,
                "execution_order": idx,
            })
            offset += aligned
        return bundles

    elif bundle_strategy == "coaccess":
        coaccess: dict[str, set[str]] = defaultdict(set)
        for ev in events:
            oid = ev.get("object_id", "")
            token_id = ev.get("token_id", -1)
            step = ev.get("step", 0)
            key = f"tok{token_id}_step{step}"
            coaccess[key].add(oid)

        merged: list[set[str]] = []
        for group in coaccess.values():
            found = False
            for existing in merged:
                if group & existing:
                    existing |= group
                    found = True
                    break
            if not found:
                merged.append(set(group))

        bundles = []
        offset = 0
        for idx, objs in enumerate(merged):
            bundle_id = f"coaccess_bundle_{idx:03d}"
            unique = list(objs)
            total_size = 0
            for ev in events:
                if ev.get("object_id") in unique:
                    total_size += ev.get("size_bytes", 0)
            aligned = ((total_size + page_alignment - 1) // page_alignment) * page_alignment
            bundles.append({
                "bundle_id": bundle_id,
                "objects": unique,
                "flash_offset_bytes": offset,
                "total_size_bytes": aligned,
                "execution_order": idx,
            })
            offset += aligned
        return bundles

    return []


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python linearize_trace.py <trace.jsonl> [--strategy layer|coaccess]")
        sys.exit(1)

    trace_path = Path(sys.argv[1])
    strategy = "layer"
    if "--strategy" in sys.argv:
        idx = sys.argv.index("--strategy")
        if idx + 1 < len(sys.argv):
            strategy = sys.argv[idx + 1]

    bundles = linearize(trace_path, bundle_strategy=strategy)
    print(json.dumps(bundles, indent=2))
    print(f"\n# {len(bundles)} bundles generated ({strategy} strategy)", file=sys.stderr)


if __name__ == "__main__":
    main()
