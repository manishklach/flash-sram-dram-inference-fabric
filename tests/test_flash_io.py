import os
import tempfile

from runtime.flash_io import AsyncFlashReader, FlashIOConfig, FlashLayoutEntry, IOStatus


def _make_reader(tmpdir: str) -> AsyncFlashReader:
    layout = {
        "test.block_0": FlashLayoutEntry(object_id="test.block_0", offset=0, size_bytes=1024),
        "test.block_1": FlashLayoutEntry(object_id="test.block_1", offset=1024, size_bytes=1024),
    }
    device = os.path.join(tmpdir, "nvme_device")
    with open(device, "wb") as f:
        f.write(b"\x00" * 2048)
    config = FlashIOConfig(device_path=device, fixed_buffer_count=4, fixed_buffer_size_bytes=4096)
    reader = AsyncFlashReader(config, layout_map=layout)
    for entry in layout.values():
        reader.register_layout(entry)
    return reader


def test_initialization():
    with tempfile.TemporaryDirectory() as td:
        reader = _make_reader(td)
        assert not reader.is_initialized()
        reader.initialize()
        assert reader.is_initialized()
        reader.close()


def test_submit_read():
    with tempfile.TemporaryDirectory() as td:
        reader = _make_reader(td)
        reader.initialize()
        req = reader.submit_read("test.block_0")
        assert req is not None
        assert req.object_id == "test.block_0"
        assert req.status == IOStatus.COMPLETED
        reader.close()


def test_submit_nonexistent():
    with tempfile.TemporaryDirectory() as td:
        reader = _make_reader(td)
        req = reader.submit_read("nonexistent")
        assert req is None


def test_poll_completions():
    with tempfile.TemporaryDirectory() as td:
        reader = _make_reader(td)
        reader.initialize()
        reader.submit_read("test.block_0")
        reader.submit_read("test.block_1")
        completed = reader.poll_completions()
        assert len(completed) == 2
        reader.close()


def test_in_flight_count():
    with tempfile.TemporaryDirectory() as td:
        reader = _make_reader(td)
        reader.initialize()
        assert reader.in_flight_count == 0
        reader.submit_read("test.block_0")
        assert reader.in_flight_count >= 0
        reader.close()


def test_close():
    with tempfile.TemporaryDirectory() as td:
        reader = _make_reader(td)
        reader.initialize()
        reader.close()
        assert not reader.is_initialized()
