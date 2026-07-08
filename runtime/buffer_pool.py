from __future__ import annotations

from enum import Enum, auto


class BufferState(Enum):
    FREE = auto()
    IN_FLIGHT = auto()
    READY_COMPRESSED = auto()
    READY_UNCOMPRESSED = auto()
    CONSUMED = auto()
    EVICTABLE = auto()


class BufferSlot:
    def __init__(self, slot_id: int, size_bytes: int, dram_address: int):
        self.slot_id = slot_id
        self.state = BufferState.FREE
        self.object_id: str | None = None
        self.size_bytes = size_bytes
        self.dram_address = dram_address
        self.deadline_step: int | None = None

    def is_free(self) -> bool:
        return self.state == BufferState.FREE

    def assign(self, object_id: str, deadline_step: int | None = None) -> None:
        self.object_id = object_id
        self.deadline_step = deadline_step
        self.state = BufferState.IN_FLIGHT

    def mark_ready(self, compressed: bool = False) -> None:
        self.state = BufferState.READY_COMPRESSED if compressed else BufferState.READY_UNCOMPRESSED

    def mark_consumed(self) -> None:
        self.state = BufferState.CONSUMED
        self.deadline_step = None

    def mark_evictable(self) -> None:
        self.state = BufferState.EVICTABLE

    def reset(self) -> None:
        self.state = BufferState.FREE
        self.object_id = None
        self.size_bytes = 0
        self.deadline_step = None


class DRAMBufferPool:
    def __init__(self, total_bytes: int, slot_size_bytes: int = 4_194_304):
        self.slot_size_bytes = slot_size_bytes
        self.num_slots = total_bytes // slot_size_bytes
        self.slots: list[BufferSlot] = [
            BufferSlot(i, slot_size_bytes, i * slot_size_bytes)
            for i in range(self.num_slots)
        ]

    @property
    def free_count(self) -> int:
        return sum(1 for s in self.slots if s.is_free())

    @property
    def used_bytes(self) -> int:
        return sum(s.size_bytes for s in self.slots if not s.is_free())

    def allocate(self, object_id: str, deadline_step: int | None = None) -> BufferSlot | None:
        for slot in self.slots:
            if slot.is_free():
                slot.assign(object_id, deadline_step)
                return slot
        return None

    def find_by_object(self, object_id: str) -> BufferSlot | None:
        for slot in self.slots:
            if slot.object_id == object_id and not slot.is_free():
                return slot
        return slot

    def evict_one(self) -> BufferSlot | None:
        for slot in self.slots:
            if slot.state in (BufferState.EVICTABLE, BufferState.CONSUMED):
                slot.reset()
                return slot
        for slot in self.slots:
            if slot.state == BufferState.READY_UNCOMPRESSED:
                slot.reset()
                return slot
        return None

    def release(self, object_id: str) -> bool:
        for slot in self.slots:
            if slot.object_id == object_id and not slot.is_free():
                slot.reset()
                return True
        return False
