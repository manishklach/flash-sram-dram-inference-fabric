from simulator.tiers import SRAMTier, DRAMTier, FlashTier, MemoryObject


def test_sram_defaults():
    t = SRAMTier()
    assert t.capacity_bytes == 64 * 1_048_576
    assert t.remaining_bytes == t.capacity_bytes
    assert t.utilization_pct == 0.0


def test_dram_defaults():
    t = DRAMTier()
    assert t.capacity_bytes == 8 * 1_073_741_824


def test_flash_defaults():
    t = FlashTier()
    assert t.capacity_bytes == 4 * 1_099_511_627_776
    assert t.queue_depth == 64
    assert t.in_flight_count == 0


def test_add_and_contains():
    t = SRAMTier(capacity_mb=1)
    obj = MemoryObject(object_id="test.1", object_type="KV_BLOCK", size_bytes=1024)
    t.add(obj)
    assert t.contains("test.1")
    assert t.resident_count == 1
    assert t.remaining_bytes == t.capacity_bytes - 1024


def test_evict_one():
    t = SRAMTier(capacity_mb=1)
    t.add(MemoryObject(object_id="a", object_type="KV_BLOCK", size_bytes=512))
    t.add(MemoryObject(object_id="b", object_type="KV_BLOCK", size_bytes=512))
    evicted = t.evict_one()
    assert evicted is not None
    assert not t.contains(evicted.object_id)
    assert t.resident_count == 1


def test_touch_moves_to_end():
    t = SRAMTier(capacity_mb=1)
    t.add(MemoryObject(object_id="a", object_type="KV_BLOCK", size_bytes=256))
    t.add(MemoryObject(object_id="b", object_type="KV_BLOCK", size_bytes=256))
    t.touch("a")
    evicted = t.evict_one()
    assert evicted is not None
    assert evicted.object_id == "b"


def test_flash_submit_complete():
    t = FlashTier()
    ttf = t.submit_read("obj1", 4096, sequential=True)
    assert t.in_flight_count == 1
    assert t.in_flight_bytes == 4096
    assert ttf > 0
    t.complete_read("obj1")
    assert t.in_flight_count == 0


def test_flash_queue_depth():
    t = FlashTier(queue_depth=4)
    for i in range(4):
        t.submit_read(f"obj{i}", 4096, sequential=True)
    assert t.in_flight_count == 4
    ttf = t.submit_read("overflow", 4096, sequential=True)
    wait_stall = (4 / 4) * t.read_latency_us
    base_min = t.read_latency_us + wait_stall + (4096 / ((t.seq_bw_gbps * 1000.0 / 8.0)))
    assert ttf >= base_min * 0.99


def test_transfer_time_us():
    sram = SRAMTier()
    dram = DRAMTier()
    flash = FlashTier()
    t_sram = sram.transfer_time_us(1_048_576)
    t_dram = dram.transfer_time_us(1_048_576)
    t_flash = flash.transfer_time_us(1_048_576, sequential=True)
    assert t_sram < t_dram
    assert t_dram < t_flash * 2
    assert t_flash > flash.read_latency_us


def test_memory_object_hash():
    a = MemoryObject(object_id="x", object_type="KV_BLOCK", size_bytes=1024)
    b = MemoryObject(object_id="x", object_type="KV_BLOCK", size_bytes=2048)
    assert hash(a) == hash(b)
    c = MemoryObject(object_id="y", object_type="KV_BLOCK", size_bytes=1024)
    assert hash(a) != hash(c)


def test_evict_objects():
    t = SRAMTier(capacity_mb=1)
    for i in range(8):
        t.add(MemoryObject(object_id=f"o{i}", object_type="KV_BLOCK", size_bytes=131072))
    evicted = t.evict_objects(3)
    assert len(evicted) == 3
    assert t.resident_count == 5