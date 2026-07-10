import json
import os
import tempfile

from runtime.llama_bridge import LlamaBridge, LlamaBridgeConfig, BridgeMetrics


def test_bridge_metrics_defaults():
    config = LlamaBridgeConfig(flash_device="")
    bridge = LlamaBridge(config)
    assert isinstance(bridge.metrics, BridgeMetrics)
    assert bridge.metrics.kv_loads_from_flash == 0
    assert bridge.metrics.kv_loads_from_dram == 0
    bridge.close()


def test_kv_load_dram_fallback():
    config = LlamaBridgeConfig(flash_device="")
    bridge = LlamaBridge(config)
    result = bridge.kv_load("nonexistent.object")
    ptr, size = result
    assert size == 0
    assert bridge.metrics.kv_loads_from_dram == 1
    assert bridge.metrics.kv_loads_from_flash == 0
    bridge.close()


def test_kv_load_flash_path():
    with tempfile.TemporaryDirectory() as td:
        device_path = os.path.join(td, "flash.img")
        obj_size = 1024 * 1024
        with open(device_path, "wb") as f:
            f.write(b"\x00" * obj_size)
        config = LlamaBridgeConfig(
            flash_device=device_path,
            dram_buffer_gb=1,
        )
        bridge = LlamaBridge(config)
        layout_path = os.path.join(td, "layout.json")
        layout = [{"object_id": "kv.block_0", "offset": 0, "size_bytes": obj_size}]
        with open(layout_path, "w") as f:
            json.dump(layout, f)
        bridge.register_kv_layout(layout_path)
        result = bridge.kv_load("kv.block_0")
        ptr, size = result
        assert size == obj_size
        assert bridge.metrics.kv_loads_from_flash == 1
        assert bridge.metrics.kv_loads_from_dram == 0
        bridge.close()


def test_maybe_prefetch():
    with tempfile.TemporaryDirectory() as td:
        device_path = os.path.join(td, "flash.img")
        obj_size = 1024 * 1024
        with open(device_path, "wb") as f:
            f.write(b"\x00" * (obj_size * 3))
        config = LlamaBridgeConfig(
            flash_device=device_path,
            dram_buffer_gb=1,
            enable_prefetch=True,
            lookahead_tokens=2,
        )
        bridge = LlamaBridge(config)
        import json
        layout_path = os.path.join(td, "layout.json")
        layout = [
            {"object_id": "obj_0", "offset": 0, "size_bytes": obj_size},
            {"object_id": "obj_1", "offset": obj_size, "size_bytes": obj_size},
            {"object_id": "obj_2", "offset": obj_size * 2, "size_bytes": obj_size},
        ]
        with open(layout_path, "w") as f:
            json.dump(layout, f)
        bridge.register_kv_layout(layout_path)
        bridge.maybe_prefetch(["obj_0", "obj_1", "obj_2"])
        assert bridge.metrics.prefetches_issued == 2
        assert bridge.metrics.prefetch_hits == 2
        bridge.close()


def test_close_idempotent():
    config = LlamaBridgeConfig(flash_device="")
    bridge = LlamaBridge(config)
    bridge.close()
    bridge.close()
