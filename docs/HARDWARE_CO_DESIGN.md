# Hardware Co-Design

## 1. Purpose

The Flash-SRAM-DRAM Inference Fabric is primarily a software architecture, but certain hardware primitives would dramatically improve its performance, energy efficiency, and practical deployability.

This document identifies hardware features — existing, emerging, and aspirational — that the software stack should target, and quantifies the benefit of each.

---

## 2. Hardware Primitive Impact Matrix

| Primitive | Benefit | Complexity | Availability |
|---|---|---|---|
| **io_uring + NVMe** | Async flash IO without kernel context switch | Low | Shipping |
| **NVMe ZNS (Zoned Namespaces)** | Append-friendly KV log, write amplification reduction | Medium | Shipping |
| **CXL-attached memory** | Shared DRAM pool, disaggregated staging | Medium | Emerging |
| **PCIe DMA engine (GPU/NPU)** | Direct flash-to-device transfers, zero CPU copy | Medium | Shipping (GPUDirect) |
| **Near-storage decompression** | Eliminate CPU decompression bottleneck | High | Research |
| **SRAM scratchpad ISA** | Compiler-controlled SRAM residency, explicit DMA | High | Research (some DSPs) |
| **Deadline-aware NVMe scheduler** | Reorder SSD reads by deadline, not FCFS | Medium | Research |
| **Compute-in/memory (NAND)** | In-storage attention or projection | Very high | Early research |
| **CXL.mem with flash backend** | Memory-semantic flash access with hardware staging | High | Emerging |

---

## 3. Existing: io_uring + NVMe

Already covered in `docs/LINUX_IO_RUNTIME.md`. The key requirements:

- **Fixed buffers**: Register DRAM buffers to avoid page-by-page pinning
- **Registered files**: Bypass dentry/inode overhead for pack files
- **IOPOLL**: Completion polling reduces interrupt latency for synchronous miss recovery
- **Multi-queue**: Separate submission queues for prefetch classes (urgent, normal, background)

No new hardware needed — this is a software optimization of existing NVMe capabilities.

---

## 4. Shipping: NVMe ZNS (Zoned Namespaces)

### Problem

KV cache is append-heavy. Each new token writes KV blocks. Standard NVMe FTL treats all writes as random, causing write amplification (WA) of 3-5x.

### Solution

ZNS exposes flash erase blocks as append-only zones. KV sessions can each own a zone:

```
zone 0: session_7 KV cache
zone 1: session_12 KV cache
...
```

### Benefits

- Write amplification drops from 3-5x to ~1.1x
- Predictable write latency (no garbage collection spikes)
- Append semantics match KV token generation perfectly
- Flash endurance extends 3-4x

### Interface

```python
class ZNSKVAppender:
    def append_block(self, session_id: str, kv_block: bytes) -> int:
        zone = self.zone_allocator.get_zone(session_id)
        lba = zone.append(kv_block)
        return lba

    def read_block(self, lba: int) -> bytes:
        return self.device.read(lba)
```

---

## 5. Emerging: CXL-Attached Memory

### Problem

DRAM capacity per server socket is limited (typically 1-2 TB max). For multi-tenant long-context inference, staging windows may need more DRAM than locally available.

### Solution

CXL (Compute Express Link) provides cache-coherent shared memory across hosts. A CXL-attached DRAM pool can serve as a shared staging tier:

```text
+------------------+     CXL      +-------------------+
|  Server A (GPU)  | <---------> |  CXL DRAM Pool    |
|  SRAM + local    |             |  64 GB shared      |
|  DRAM 16 GB      |             |  staging buffer    |
+------------------+             +-------------------+
         |                               |
    local flash                    shared flash
    (per-server)                   (capacity tier)
```

### Benefits

- Decouple staging capacity from per-server DRAM limits
- Enable memory-overcommitted multi-tenant serving
- CXL.mem latency (~100-200 ns) is acceptable for DRAM staging (not for SRAM hot path)

### CXL for Flash Tier

CXL-attached SSDs (CXL.mem with NAND backend) provide memory-semantic flash access. This is useful for RAM-emulation mode but does not replace the stream-to-scratchpad programming model.

---

## 6. Shipping: GPUDirect / NPU DMA Engine

### Problem

Without DMA, flash reads must go: SSD → CPU DRAM → PCIe → GPU DRAM. This adds latency and consumes CPU bandwidth.

### Solution

GPUDirect Storage (GDS) or equivalent NPU DMA allows the SSD to DMA directly to device memory:

```text
Standard path:
  SSD → CPU DRAM (PCIe) → CPU copy → GPU DRAM (PCIe)

GPUDirect path:
  SSD → GPU DRAM (PCIe directly)
```

### Benefits

- Saves one PCIe hop and CPU copy (~5-10 µs per 1 MB)
- CPU DRAM not consumed by staging buffers
- Enables the GPU/NPU to manage flash residency directly

### Integration

```python
# With GPUDirect
io_uring_prep_read_fixed(
    sqe,
    fd=pack_file_fd,
    buf=gpu_dram_buffer,   # GPU-accessible registered buffer
    offset=flash_offset,
    len=size
)
```

---

## 7. Emerging: Near-Storage Decompression

### Problem

Decompression consumes CPU cores. At high throughput, decompression can become the bottleneck.

### Solution

SSD controllers or compute-in-NAND with inline decompression:

```text
Current:
  SSD → PCIe → CPU DRAM → CPU decompress → DRAM → GPU/NPU

Near-storage decompression:
  SSD (decompress inline) → PCIe → GPU/NPU DRAM
```

### Requirements

- SSD controller exposes decompression context per I/O
- Codec negotiation between runtime and SSD
- Supports Zstd/LZ4 at line rate

### Benefit Estimate

At 7 GB/s flash bandwidth with Zstd decompression at 1.5 GB/s per core:

```
Without near-storage: need 5 CPU cores just for decompression
With near-storage: 0 CPU cores, 7 GB/s sustained
```

---

## 8. Research: SRAM Scratchpad ISA Extensions

### Problem

Current CPU/GPU ISAs do not expose SRAM scratchpad management as an explicit compiler primitive. SRAM is treated as a hardware cache, not a software-managed buffer.

### Solution

ISA extensions for explicit SRAM scratchpad management:

```c
// Hypothetical intrinsics
void scratchpad_reserve(void *sram_addr, size_t size);
void scratchpad_fill(void *sram_addr, void *dram_addr, size_t size, int deadline);
void scratchpad_release(void *sram_addr);
bool scratchpad_is_ready(void *sram_addr);
```

### Benefits

- Compiler can schedule SRAM tile lifetimes deterministically
- No cache pollution from streaming data
- Bounded SRAM residency — no thrashing
- Explicit deadline management

### Target Platforms

- RISC-V custom extensions (most accessible for research)
- DSPs with hardware scratchpads (TI C66x, CEVA)
- Future NPU architectures

---

## 9. Research: Deadline-Aware NVMe Scheduler

### Problem

Standard NVMe drives process commands FIFO. If a high-priority (urgent miss) read arrives after 32 low-priority prefetch reads, it waits.

### Solution

Deadline-aware NVMe command scheduler:

```text
Current:
  [prefetch_1][prefetch_2]...[prefetch_32][urgent_miss] → 32x delay

Deadline-aware:
  [urgent_miss][prefetch_1][prefetch_2]...  → immediate issue
```

### Implementation Options

| Approach | Complexity | Benefit |
|---|---|---|
| Multiple NVMe queues (one per priority class) | Low (existing feature) | Priority classes isolated |
| Deadline tag in NVMe command | Medium (spec change) | SSD reorders internally |
| Software reordering before submission | Low (runtime change) | Limited to single queue depth |

---

## 10. Early Research: Compute-in-NAND

### Prospect

If NAND die can perform simple operations (vector multiply, attention dot product) before data leaves the flash chip, the effective bandwidth explosion is enormous.

### Scenario: In-Storage Attention

KV blocks are read from NAND and attention scores computed at the storage die:

```
Instead of:
  read 1 MB KV from flash → PCIe → DRAM → GPU compute attention

Do:
  query → flash controller → NAND die computes attention → return top-K results (4 KB)
```

### Benefit

- PCIe bandwidth reduction: 1 MB → 4 KB (256x reduction)
- GPU/NPU compute saved: attention score computation offloaded
- DRAM staging buffer saved: only top-K results cached

### Reality

This is early research. No production NAND supports compute-in-storage. But the architecture should keep this as a future target for the KV cache tiering scenario.

---

## 11. Hardware Profile: Reference System

A recommended hardware platform for prototyping:

| Component | Specification | Rationale |
|---|---|---|
| **CPU** | AMD EPYC / Intel Xeon, 16+ cores | io_uring submission, decompression workers |
| **DRAM** | 16-64 GB DDR5 | Staging window |
| **SSD** | Samsung PM9A3 / Kioxia CD8, 4+ TB, Gen4 | High sequential BW, ZNS support preferred |
| **GPU/NPU** | NVIDIA A2 / Intel ARC / AMD W5500 | GPUDirect support, moderate VRAM |
| **CXL** | (Optional) Samsung CXL Memory Module | If exploring disaggregated staging |
| **OS** | Linux 6.0+ | io_uring features, ZNS support |

---

## 12. Implementation Roadmap

| Phase | Hardware Feature | Software Dependency |
|---|---|---|
| **Phase 1** | NVMe + io_uring | Linux 5.1+ |
| **Phase 2** | NVMe ZNS | Linux 5.10+, ZNS SSD |
| **Phase 3** | GPUDirect Storage | CUDA 11+, NVIDIA driver |
| **Phase 4** | CXL-attached DRAM pool | Linux 6.x, CXL hardware |
| **Phase 5** | Near-storage decompression | Vendor SDK (research) |
| **Phase 6** | Scratchpad ISA | Custom RISC-V / simulator |

---

## 13. Summary

The software architecture is viable on current hardware (NVMe + io_uring + standard DRAM and SRAM). However, the following hardware primitives would each unlock step-function improvements:

| Primitive | Current Hardware | With Primitive | Improvement |
|---|---|---|---|
| io_uring | Blocking reads | Async, batched | Critical for viability |
| NVMe ZNS | 3-5x write amplification | ~1.1x | 3x endurance, stable latency |
| GPUDirect | CPU-midpoint DMA | Direct device-DMA | -5 µs latency, less CPU load |
| Near-storage decompression | 5 CPU cores for decompress | 0 CPU cores | Higher throughput, lower cost |
| Scratchpad ISA | Cache-based SRAM | Explicit SRAM schedule | Deterministic latency |
| Compute-in-NAND | Full KV block transfer | Top-K only | 256x bandwidth reduction |

The software stack should target current hardware first (phases 1-3), but the design should anticipate and inform these hardware advances.
