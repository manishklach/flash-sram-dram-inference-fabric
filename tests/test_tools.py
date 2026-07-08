import json
import os
import tempfile

from tools.linearize_trace import linearize
from tools.pack_flash_layout import pack


def _sample_trace_jsonl(tmpdir: str) -> str:
    path = os.path.join(tmpdir, "trace.jsonl")
    events = [
        {"step": 0, "token_id": 0, "layer_id": 0, "object_id": "kv.session_0.layer_0.block_0", "object_type": "KV_BLOCK", "size_bytes": 1048576},
        {"step": 1, "token_id": 0, "layer_id": 0, "object_id": "kv.session_0.layer_0.block_1", "object_type": "KV_BLOCK", "size_bytes": 1048576},
        {"step": 2, "token_id": 0, "layer_id": 1, "object_id": "kv.session_0.layer_1.block_1", "object_type": "KV_BLOCK", "size_bytes": 1048576},
    ]
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    return path


def test_linearize_layer_strategy():
    with tempfile.TemporaryDirectory() as td:
        trace_path = _sample_trace_jsonl(td)
        bundles = linearize(trace_path, bundle_strategy="layer")
        assert len(bundles) > 0
        for b in bundles:
            assert "bundle_id" in b
            assert "objects" in b
            assert "flash_offset_bytes" in b


def test_linearize_coaccess_strategy():
    with tempfile.TemporaryDirectory() as td:
        trace_path = _sample_trace_jsonl(td)
        bundles = linearize(trace_path, bundle_strategy="coaccess")
        assert len(bundles) > 0
        for b in bundles:
            assert "total_size_bytes" in b


def test_linearize_empty():
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "empty.jsonl")
        with open(path, "w") as f:
            pass
        bundles = linearize(path)
        assert bundles == []


def test_pack_flash_layout():
    with tempfile.TemporaryDirectory() as td:
        bundles = [
            {
                "bundle_id": "bundle_0",
                "objects": ["kv.session_0.layer_0.block_0", "kv.session_0.layer_0.block_1"],
                "total_size_bytes": 2097152,
                "flash_offset_bytes": 0,
                "execution_order": 0,
            }
        ]
        bundle_path = os.path.join(td, "bundles.json")
        with open(bundle_path, "w") as f:
            json.dump(bundles, f)
        out_path = os.path.join(td, "output.pack")
        pack(bundles, out_path)
        assert os.path.exists(out_path)
        assert os.path.getsize(out_path) > 0


def test_pack_header():
    with tempfile.TemporaryDirectory() as td:
        bundles = [{"bundle_id": "bundle_0", "objects": ["obj_0"], "total_size_bytes": 4096, "flash_offset_bytes": 0, "execution_order": 0}]
        bundle_path = os.path.join(td, "bundles.json")
        with open(bundle_path, "w") as f:
            json.dump(bundles, f)
        out_path = os.path.join(td, "output.pack")
        pack(bundles, out_path)
        with open(out_path, "rb") as f:
            magic = f.read(8)
        assert magic == b"FSDIFPAC"