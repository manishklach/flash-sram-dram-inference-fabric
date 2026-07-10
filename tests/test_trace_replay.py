import os
import tempfile

from runtime.flash_io import AsyncFlashReader, FlashIOConfig
from runtime.trace_replay import TraceReplayer, ReplayConfig, ReplayEvent, ReplayMetrics


def _make_flash_device(path: str, objects: dict[str, bytes]):
    offset = 0
    dev_size = sum(len(data) for data in objects.values())
    with open(path, "wb") as f:
        f.truncate(dev_size)
    layouts = {}
    for oid, data in sorted(objects.items()):
        layouts[oid] = {"offset": offset, "size_bytes": len(data), "object_id": oid}
        offset += len(data)
    return layouts


def test_replay_does_not_crash():
    with tempfile.TemporaryDirectory() as td:
        device_path = os.path.join(td, "flash.img")
        with open(device_path, "wb") as f:
            f.write(b"\x00" * (1024 * 1024))
        events = [
            ReplayEvent(step=0, token_id=0, object_id="obj_0",
                        object_type="KV_BLOCK", size_bytes=1024 * 1024,
                        deadline_step=1, is_critical=True),
        ]
        config = ReplayConfig(
            device_path=device_path, dram_capacity_gb=1,
            slot_size_bytes=4_194_304, lookahead_steps=0,
        )
        flash_reader = AsyncFlashReader(
            FlashIOConfig(device_path=device_path, direct_io=False)
        )
        replayer = TraceReplayer(config, flash_reader=flash_reader)
        metrics = replayer.replay(events, prefetch=False)
        assert isinstance(metrics, ReplayMetrics)
        assert metrics.total_events == 1
        assert metrics.flash_reads == 1


def test_replay_dram_hit_on_second_access():
    with tempfile.TemporaryDirectory() as td:
        device_path = os.path.join(td, "flash.img")
        obj_size = 512 * 1024
        with open(device_path, "wb") as f:
            f.write(b"\x00" * obj_size)
        events = [
            ReplayEvent(step=0, token_id=0, object_id="obj_A",
                        object_type="KV_BLOCK", size_bytes=obj_size,
                        deadline_step=2, is_critical=True),
            ReplayEvent(step=1, token_id=0, object_id="obj_A",
                        object_type="KV_BLOCK", size_bytes=obj_size,
                        deadline_step=3, is_critical=True),
        ]
        config = ReplayConfig(
            device_path=device_path, dram_capacity_gb=1,
            slot_size_bytes=obj_size, lookahead_steps=0,
        )
        flash_reader = AsyncFlashReader(
            FlashIOConfig(device_path=device_path, direct_io=False)
        )
        replayer = TraceReplayer(config, flash_reader=flash_reader)
        metrics = replayer.replay(events, prefetch=False)
        assert metrics.total_events == 2
        assert metrics.flash_reads == 1
        assert metrics.dram_hits == 1


def test_replay_metrics_populated():
    with tempfile.TemporaryDirectory() as td:
        device_path = os.path.join(td, "flash.img")
        sizes = [1024 * 1024, 2 * 1024 * 1024]
        with open(device_path, "wb") as f:
            f.write(b"\x00" * sum(sizes))
        events = [
            ReplayEvent(step=0, token_id=0, object_id=f"obj_{i}",
                        object_type="KV_BLOCK", size_bytes=sizes[i],
                        deadline_step=i + 1, is_critical=True)
            for i in range(2)
        ]
        config = ReplayConfig(
            device_path=device_path, dram_capacity_gb=1,
            slot_size_bytes=max(sizes), lookahead_steps=0,
        )
        flash_reader = AsyncFlashReader(
            FlashIOConfig(device_path=device_path, direct_io=False)
        )
        replayer = TraceReplayer(config, flash_reader=flash_reader)
        metrics = replayer.replay(events, prefetch=False)
        assert metrics.total_events == 2
        assert metrics.flash_reads == 2
        assert metrics.flash_bytes_read == sum(sizes)
        assert metrics.total_latency_us > 0

def test_replay_prefetch_no_crash():
    with tempfile.TemporaryDirectory() as td:
        device_path = os.path.join(td, "flash.img")
        obj_size = 512 * 1024
        with open(device_path, "wb") as f:
            f.write(b"\x00" * (obj_size * 3))
        events = [
            ReplayEvent(step=i, token_id=0, object_id=f"obj_{i}",
                        object_type="KV_BLOCK", size_bytes=obj_size,
                        deadline_step=i + 1, is_critical=True)
            for i in range(3)
        ]
        config = ReplayConfig(
            device_path=device_path, dram_capacity_gb=1,
            slot_size_bytes=obj_size, lookahead_steps=2,
        )
        flash_reader = AsyncFlashReader(
            FlashIOConfig(device_path=device_path, direct_io=False)
        )
        replayer = TraceReplayer(config, flash_reader=flash_reader)
        metrics = replayer.replay(events, prefetch=True)
        assert metrics.total_events == 3
        assert metrics.flash_reads >= 2
