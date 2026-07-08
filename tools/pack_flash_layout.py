\"\"\"Pack model, KV, or expert bundles into sequential flash-oriented layout files.\"\"\"

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path
from typing import Any


PACK_MAGIC = b"FSDIFPACK"
PACK_VERSION = 1


def pack(
    bundles: list[dict[str, Any]],
    pack_path: Path,
    *,
    alignment: int = 1_048_576,
) -> None:
    with open(pack_path, "wb") as f:
        header_size = 56
        num_bundles = len(bundles)
        metadata_offset = header_size
        metadata_size = num_bundles * 64

        f.write(PACK_MAGIC)
        f.write(struct.pack("<I", PACK_VERSION))
        f.write(struct.pack("<Q", header_size))
        f.write(struct.pack("<Q", metadata_offset))
        f.write(struct.pack("<Q", metadata_size))
        f.write(struct.pack("<I", num_bundles))
        f.write(b"\x00" * (header_size - 28))

        for bundle in bundles:
            bundle_id = bundle["bundle_id"].encode("utf-8")
            f.write(bundle_id.ljust(64, b"\x00"))
            f.write(struct.pack("<Q", bundle["flash_offset_bytes"]))
            f.write(struct.pack("<Q", bundle["total_size_bytes"]))
            f.write(struct.pack("<I", bundle["execution_order"]))
            f.write(b"\x00" * (256 - 64 - 8 - 8 - 4))

        payload_start = metadata_offset + metadata_size
        payload_start = ((payload_start + alignment - 1) // alignment) * alignment
        f.seek(payload_start)

        for bundle in bundles:
            current_pos = f.tell()
            if current_pos < bundle["flash_offset_bytes"]:
                f.write(b"\x00" * (bundle["flash_offset_bytes"] - current_pos))
            f.write(b"\x00" * bundle["total_size_bytes"])

        print(f"Wrote {len(bundles)} bundles to {pack_path}", file=sys.stderr)


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python pack_flash_layout.py <bundles.json> <output.pack>")
        sys.exit(1)

    bundles_path = Path(sys.argv[1])
    pack_path = Path(sys.argv[2])

    with open(bundles_path, "r") as f:
        bundles = json.load(f)

    pack(bundles, pack_path)


if __name__ == "__main__":
    main()
