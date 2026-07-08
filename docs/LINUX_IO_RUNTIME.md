# Linux IO Runtime

## Purpose

The Linux IO runtime moves data from SSD flash into DRAM without blocking token generation. It is a deadline-aware flash streaming engine, not a generic file reader.

---

## Core Requirement

Flash IO must be:

```text
asynchronous
batched
mostly sequential
deadline-aware
low jitter
```

The compute thread should not issue blocking reads.

---

## Recommended Mechanisms

```text
io_uring
O_DIRECT
registered buffers
fixed files
huge pages
CPU affinity
NUMA pinning
asynchronous decompression
```

---

## Pipeline

```text
Prefetch planner
  -> Flash IO engine
  -> io_uring submit queue
  -> NVMe SSD
  -> completion queue
  -> DRAM buffer pool
  -> decompression worker
  -> residency update
  -> SRAM promotion
```

---

## Buffer States

```text
FREE
IN_FLIGHT
READY_COMPRESSED
READY_UNCOMPRESSED
CONSUMED
EVICTABLE
```

---

## IO Classes

```text
CLASS_0 urgent miss recovery
CLASS_1 near-deadline prefetch
CLASS_2 normal lookahead prefetch
CLASS_3 background migration
CLASS_4 idle-session restore
```

---

## Read Size Sweep

Benchmark:

```text
64KB
256KB
1MB
4MB
8MB
16MB
```

---

## Completion Handling

On completion:

```text
1. validate status
2. check checksum if enabled
3. mark buffer ready
4. schedule decompression if needed
5. update residency table
6. notify SRAM promotion manager
```

---

## Thermal Handling

If SSD temperature rises:

```text
reduce speculative prefetch
increase prefetch selectivity
compress more cold objects
spread reads across drives
lower queue depth
```

---

## Minimal Prototype

```text
one pack file
one metadata index
one io_uring read worker
one DRAM buffer pool
one synthetic compute loop
one fixed prefetch policy
latency logging
```
