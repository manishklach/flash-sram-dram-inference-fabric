from runtime.buffer_pool import DRAMBufferPool, BufferState


def test_pool_defaults():
    pool = DRAMBufferPool(total_bytes=1_073_741_824, slot_size_bytes=4_194_304)
    assert pool.num_slots == 256
    assert pool.free_count == 256
    assert pool.used_bytes == 0


def test_allocate():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    slot = pool.allocate("obj1", deadline_step=42)
    assert slot is not None
    assert slot.state == BufferState.IN_FLIGHT
    assert slot.object_id == "obj1"
    assert pool.free_count == 1


def test_allocate_full():
    pool = DRAMBufferPool(total_bytes=4_194_304, slot_size_bytes=4_194_304)
    pool.allocate("obj1")
    assert pool.allocate("obj2") is None


def test_find_by_object():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    pool.allocate("obj1")
    slot = pool.find_by_object("obj1")
    assert slot is not None
    assert slot.object_id == "obj1"
    assert pool.find_by_object("nonexistent") is None


def test_state_transitions():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    slot = pool.allocate("obj1")
    slot.mark_ready(compressed=True)
    assert slot.state == BufferState.READY_COMPRESSED
    slot.mark_consumed()
    assert slot.state == BufferState.CONSUMED
    slot.mark_evictable()
    assert slot.state == BufferState.EVICTABLE


def test_evict_one():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    pool.allocate("obj1")
    pool.allocate("obj2")
    assert pool.free_count == 0
    # mark consumed and evict
    slot = pool.find_by_object("obj1")
    assert slot is not None
    slot.mark_consumed()
    evicted = pool.evict_one()
    assert evicted is not None
    assert evicted.is_free()
    assert pool.free_count == 1


def test_release():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    pool.allocate("obj1")
    assert pool.release("obj1")
    assert pool.free_count == 2
    assert not pool.release("nonexistent")


def test_used_bytes():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    assert pool.used_bytes == 0
    pool.allocate("obj1")
    pool.allocate("obj2")
    assert pool.used_bytes == 8_388_608


def test_lifecycle():
    pool = DRAMBufferPool(total_bytes=8_388_608, slot_size_bytes=4_194_304)
    a = pool.allocate("a")
    b = pool.allocate("b")
    assert pool.free_count == 0
    a.mark_ready(compressed=False)
    a.mark_consumed()
    pool.release("a")
    assert pool.free_count == 1
    c = pool.allocate("c")
    assert c is not None
    assert pool.free_count == 0