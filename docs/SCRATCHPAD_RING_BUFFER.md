# Scratchpad Ring Buffer

## 1. Motivation

SRAM is too small for full layers or full models, so it should be managed as a program-controlled ring buffer rather than a passive cache.

The scratchpad only needs to hold the immediate working set for active compute.

---

## 2. Ring Buffer Model

```text
SRAM Scratchpad Ring

[ tile A ][ tile B ][ tile C ][ free ][ free ]
    ↑        ↑
 active   next
```

This model emphasizes:

- explicit slot ownership
- rolling forward through execution
- bounded tile lifetime

---

## 3. Tile Lifecycle

```text
reserved -> filled from DRAM -> active -> consumed -> reusable
```

Each slot moves through this lifecycle under runtime and compiler control.

---

## 4. Deadlines

Each tile has a deadline.

If the tile is not ready by deadline, compute stalls.

That means tile scheduling is not just capacity management. It is deadline management.

---

## 5. DRAM to SRAM Promotion

DRAM contains larger bundles.

SRAM contains only immediate tiles.

Promotion is scheduled by runtime and compiler logic that understands:

- active layer
- next microstep
- tile size
- dependency order
- slot availability

---

## 6. Cases Where SRAM Is Too Small

One possible response is an optical-drive-style duplication idea:

- duplicate frequently reused data in multiple places in flash layout
- avoid seeking or random reads
- store redundant sequential copies because flash capacity is cheap
- trade capacity for sequentiality

This is **Redundant Sequential Placement**.

It is especially useful when reuse order conflicts cannot be resolved inside a very small scratchpad.

---

## 7. Scratchpad vs Cache

Make this explicit:

- SRAM is not a passive cache
- SRAM is explicitly scheduled
- tile lifetimes are compiler and runtime managed

This distinction matters because performance depends on deterministic arrival, not cache luck.

---

## 8. Pseudo-Code

```python
class ScratchpadSlot:
    slot_id: int
    state: str
    object_id: str | None
    deadline: int | None

def schedule_tile(tile, deadline):
    slot = find_free_or_evictable_slot(deadline)
    issue_dram_to_sram_copy(tile, slot)
    slot.deadline = deadline
```

This pseudo-code is intentionally minimal. The key point is explicit scheduling, not accidental residency.
