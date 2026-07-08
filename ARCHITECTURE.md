# Architecture: Flash-SRAM-DRAM Inference Fabric

## 1. Executive Summary

The Flash-SRAM-DRAM Inference Fabric is a tiered memory architecture for AI inference systems.

It combines:

```text
SRAM  -> deterministic compute-local working set
DRAM  -> predictive staging buffer and warm residency layer
Flash -> low-cost high-capacity sequential stream source
```

The architecture is designed around one rule:

> SSD flash must not sit on the synchronous token-critical path.

Instead, the runtime and compiler collaborate to predict future memory needs and stage data into DRAM and SRAM before compute requires it.

---

## 2. System Goal

The system aims to reduce the cost of large-model inference by allowing large quantities of model state, KV cache, expert weights, and retrieval memory to live on commodity flash, while maintaining low visible latency through:

- asynchronous prefetch
- trace-guided layout
- token-aware prediction
- compiler-guided scheduling
- DRAM staging
- SRAM scratchpad residency
- flash-aligned tensor layout
- compression and decompression pipelines
- deadline-aware promotion and eviction

---

## 3. High-Level Block Diagram

```text
+------------------------------------------------------------------+
|                       Inference Runtime                          |
|                                                                  |
| +--------------+  +----------------+  +-----------------------+ |
| | Token Engine |  | Residency Mgr  |  | Predictive Prefetcher | |
| +------+-------+  +--------+-------+  +-----------+-----------+ |
+--------+-------------------+---------------------- +------------+
         |                   |                       |
         v                   v                       v
+----------------+  +----------------------+  +----------------------+
|      SRAM      |  |    DRAM / LPDDR      |  |     NVMe Flash       |
| scratchpad ring|  | predictive staging   |  | sequential capacity  |
+----------------+  +----------------------+  +----------------------+
         |
         v
+------------------------------------------------------------------+
|                  GPU / NPU / ASIC / CPU Compute                  |
+------------------------------------------------------------------+
```

---

## 4. Memory Tier Responsibilities

## 4.1 SRAM Tier

SRAM is the deterministic low-latency tier.

It should contain only the data needed for the immediate compute step or near-immediate microstep.

### Stores

- active matrix tiles
- active KV tiles
- attention metadata
- decode scratch buffers
- decompressed tensor fragments
- DMA descriptors
- prefetch completion queues
- routing metadata
- selected MoE expert tiles

### Design Goals

- deterministic access
- bounded latency
- predictable lifetimes
- tight integration with compute
- explicit tile deadlines

### SRAM Should Not Store

- full model weights
- long-context KV history
- cold experts
- full retrieval index
- low-probability speculative pages

---

## 4.2 DRAM / LPDDR Tier

DRAM is the predictive staging tier.

It is not simply a cache. It is the buffer that absorbs flash latency and feeds the SRAM scratchpad ahead of deadlines.

### Stores

- warm KV pages
- upcoming layer tensors
- recently used experts
- prefetch windows
- decompression output
- page tables
- residency map
- scheduling queues
- token history
- predictor state
- session metadata

### Design Goals

- keep flash misses off the critical path
- provide enough capacity for N future layers or windows
- allow async streaming from flash
- provide a landing zone for sequential flash reads
- provide source data for SRAM promotion

### DRAM as Shock Absorber

> DRAM is the shock absorber between slow high-capacity flash and deterministic SRAM execution.

The larger and better-managed the DRAM staging window, the more tolerant the system is to flash latency variation.

---

## 4.3 SSD Flash Tier

Flash is the capacity tier.

It is not treated as generic random-access memory. It is treated as a sequential streaming reservoir that can supply large bundles ahead of use.

### Stores

- cold KV cache
- long-context history
- inactive sessions
- model pages
- cold MoE experts
- embeddings
- retrieval pages
- adapter weights
- checkpoint state
- speculative branch state
- compressed tensors

### Design Goals

- maximize sequential reads
- minimize random reads
- batch IO requests
- align tensor pages with flash pages
- compress cold state
- avoid synchronous decode stalls

### Flash Should Not Do

- service random per-token fetches synchronously
- act as a direct replacement for SRAM
- act as a direct replacement for DRAM
- hide poor layouts behind a generic cache model

---

## 5. Critical Path vs Hidden Path

## 5.1 Critical Path

```text
SRAM -> compute -> token output
```

The critical path must be deterministic.

## 5.2 Near-Critical Path

```text
DRAM -> SRAM
```

DRAM refills the scratchpad before compute stalls.

## 5.3 Hidden Path

```text
Flash -> DRAM
```

Flash operates ahead of time.

---

## 6. Data Types

## 6.1 Model Weights

Many inference paths do not require truly random weight access.

Transformer layers execute in order, so weights can often be organized as:

- always-hot weights
- layer-sequential weights
- rarely used weights
- expert weights
- adapter weights
- quantized pages
- compressed pages

Placement:

```text
SRAM: current tile
DRAM: upcoming layers / hot weights
Flash: cold layer pages / experts / adapters
```

## 6.2 KV Cache

KV cache naturally has temperature:

```text
recent tokens       -> hot
near history        -> warm
old long context    -> cold
rarely attended     -> cold
sink tokens         -> pinned hot/warm
```

Placement:

```text
SRAM: current attention tiles
DRAM: recent/high-attention KV blocks
Flash: old or low-attention KV blocks
```

## 6.3 MoE Experts

MoE models are attractive because only a subset of experts are active per token.

Placement:

```text
SRAM: active expert tiles
DRAM: likely top-k experts
Flash: cold experts
```

## 6.4 Retrieval Pages

RAG workloads often expose retrieval activity before generation, which makes staging possible.

Placement:

```text
SRAM: active retrieved chunks
DRAM: candidate chunks
Flash: full retrieval memory
```

---

## 7. Deterministic Access and Linearized Flash

Model weights do not need true random access in many inference paths.

- layer access can be streamed
- trace capture can identify repeated access order
- flash layout should be optimized around sequential reads
- runtime should treat random flash reads as exceptional
- late reads should be surfaced as policy failures, not normalized as ordinary misses

```text
Compiler / Trace Capture
        |
        v
Linear Flash Layout
        |
        v
Async Sequential Flash Reads
        |
        v
DRAM Staging Window
        |
        v
SRAM Scratchpad Ring
        |
        v
Compute
```

This is one of the main distinctions from virtual memory or generic caching.

---

## 8. Residency Manager

The residency manager tracks every object:

```text
object_id
object_type
size
tier_location
temperature
last_access_time
predicted_next_use
reuse_distance
compression_state
pinned_state
eviction_priority
deadline
```

Example object types:

```text
KV_BLOCK
WEIGHT_TILE
EXPERT_PAGE
EMBEDDING_PAGE
RETRIEVAL_CHUNK
ADAPTER_PAGE
SESSION_STATE
```

---

## 9. Promotion Policy

Promotion moves data upward:

```text
Flash -> DRAM -> SRAM
```

Promotion triggers:

- predicted imminent use
- repeated access
- high attention score
- high expert routing probability
- compiler hint
- trace-derived bundle ordering
- session priority
- explicit tile deadline

---

## 10. Eviction Policy

Eviction moves data downward:

```text
SRAM -> DRAM -> Flash
```

Eviction triggers:

- low predicted reuse
- long reuse distance
- low attention probability
- cold expert
- DRAM pressure
- SRAM pressure
- tenant priority change

---

## 11. Prefetch Windows

A prefetch window defines how far ahead the runtime streams data.

Example:

```text
current layer: 12
SRAM: layer 12 tiles
DRAM: layers 13-16
Flash streaming: layers 17-32
```

The window size depends on:

- flash latency
- flash bandwidth
- DRAM capacity
- model layer time
- batch size
- decode vs prefill
- queue depth
- compression ratio

---

## 12. Flash-Aware Tensor Layout

Tensor storage on flash should avoid random access.

Recommended layout properties:

- page-aligned tensor blocks
- sequential layer ordering
- grouped experts
- contiguous KV regions
- compression blocks aligned to IO boundaries
- metadata separated from bulk payload
- append-friendly session KV logs
- read-optimized cold pages
- optional redundant sequential placement when capacity is cheaper than seeks

Example:

```text
/model/layer_000/qkv.bundle
/model/layer_001/qkv.bundle
/model/layer_002/qkv.bundle

/kv/session_42/head_00/block_0000.kv
/kv/session_42/head_00/block_0001.kv
/kv/session_42/head_01/block_0000.kv
```

---

## 13. Compression

Cold objects are good compression candidates.

Candidate compression targets:

- old KV blocks
- inactive experts
- adapter pages
- retrieval embeddings
- sparse activations

Compression strategy:

```text
SRAM: uncompressed
DRAM: mixed compressed/uncompressed
Flash: compressed
```

Decompression must complete before the object's deadline.

---

## 14. DMA and IO Pipeline

The system should use asynchronous IO.

Possible Linux mechanisms:

- io_uring
- O_DIRECT
- huge pages
- pinned memory
- mmap for metadata
- asynchronous decompression
- batched NVMe queues

Pipeline:

```text
submit flash read
    |
    v
SSD DMA to DRAM buffer
    |
    v
optional decompression
    |
    v
residency table update
    |
    v
SRAM promotion request
    |
    v
compute consumes tile
```

---

## 15. Multi-Tenant Scheduling

For serving multiple users, the runtime must manage memory fairness.

State per session:

```text
session_id
priority
latency_budget
context_length
active_decode_state
dram_reservation
flash_queue_depth
miss_history
```

Policies:

- pin high-priority session hot sets
- demote idle sessions
- compress inactive KV
- limit flash queue per tenant
- prefetch based on SLA

---

## 16. Failure Modes

Critical failure modes:

- flash read appears on token path
- predictor miss rate too high
- DRAM staging window too small
- random IO dominates
- decompression misses a deadline
- SRAM thrashing
- DRAM thrashing
- trace-guided layout overfits one workload
- multi-tenant interference
- SSD thermal throttling

---

## 17. Architecture Summary

```text
SRAM:
  deterministic scratchpad hot path

DRAM:
  predictive staging buffer and warm residency layer

Flash:
  low-cost capacity and sequential stream source

Runtime:
  residency, deadlines, and prefetch orchestration

Compiler / Packer:
  placement hints, trace-guided repacking, and tile scheduling

Goal:
  hide flash behind compute and predictive staging
```

---

## 18. One-Sentence IP Framing

A deterministic inference memory orchestration system that converts commodity SSD flash into a hidden high-capacity streaming tier through compiler/runtime guidance, predictive DRAM staging, and explicit SRAM scratchpad scheduling.
