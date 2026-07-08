# Architecture: Flash–SRAM–DRAM Inference Fabric

## 1. Executive Summary

The Flash–SRAM–DRAM Inference Fabric is a tiered memory architecture for AI inference systems.

It combines:

```text
SRAM  → ultra-low-latency working set
DRAM  → predictive staging and warm memory
Flash → high-capacity low-cost backing tier
```

The architecture is designed around one rule:

> SSD flash must not sit on the synchronous token-critical path.

Instead, the runtime and compiler collaborate to predict future memory needs and stage data into DRAM and SRAM before the compute engine requires it.

---

## 2. System Goal

The system aims to reduce the cost of large-model inference by allowing large quantities of model state, KV cache, expert weights, and retrieval memory to live on commodity flash, while maintaining low visible latency through:

- asynchronous prefetch
- token-aware prediction
- compiler-guided scheduling
- DRAM staging
- SRAM hot-set residency
- flash-aligned tensor layout
- compression and decompression pipelines
- eviction and promotion policies

---

## 3. High-Level Block Diagram

```text
┌──────────────────────────────────────────────────────────────────┐
│                       Inference Runtime                           │
│                                                                  │
│ ┌──────────────┐  ┌────────────────┐  ┌───────────────────────┐ │
│ │ Token Engine │  │ Residency Mgr  │  │ Predictive Prefetcher │ │
│ └──────┬───────┘  └───────┬────────┘  └──────────┬────────────┘ │
│        │                  │                      │              │
└────────┼──────────────────┼──────────────────────┼──────────────┘
         │                  │                      │
         ▼                  ▼                      ▼
┌────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│     SRAM        │  │     DRAM / LPDDR     │  │     NVMe Flash       │
│ hot token tiles │  │ staging / warm pages │  │ cold capacity tier    │
└────────────────┘  └─────────────────────┘  └─────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────┐
│                  GPU / NPU / ASIC / CPU Compute                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. Memory Tier Responsibilities

## 4.1 SRAM Tier

SRAM is the deterministic low-latency tier.

It should contain only the data needed for the immediate compute step or near-immediate microstep.

### Stores

- active matrix tiles
- active KV blocks
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
- low miss rate
- tight integration with compute
- high reuse over a short window

### SRAM Should Not Store

- full model weights
- long-context KV history
- cold experts
- full retrieval index
- low-probability speculative pages

---

## 4.2 DRAM / LPDDR Tier

DRAM is the prediction and staging tier.

It is large enough to absorb flash latency but cheaper and more available than premium accelerator memory.

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

Flash has high latency relative to DRAM.

Therefore DRAM acts as a shock absorber:

```text
flash latency variation → absorbed by DRAM staging window
```

The larger the DRAM window, the more tolerant the system is to flash latency spikes.

---

## 4.3 SSD Flash Tier

Flash is the capacity tier.

It is not treated as memory in the conventional random-access sense. It is treated as a large sequential streaming reservoir.

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
- store frequently changing active decode state unless buffered

---

## 5. Critical Path vs Hidden Path

## 5.1 Critical Path

```text
SRAM → compute → token output
```

The critical path must be deterministic.

## 5.2 Near-Critical Path

```text
DRAM → SRAM
```

DRAM refills SRAM before the compute unit stalls.

## 5.3 Hidden Path

```text
Flash → DRAM
```

Flash operates ahead of time.

---

## 6. Data Types

## 6.1 Model Weights

Model weights can be divided into:

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

---

## 6.2 KV Cache

KV cache is a major target for this architecture.

KV cache naturally has temperature:

```text
recent tokens       → hot
near history        → warm
old long context    → cold
rarely attended     → cold
sink tokens         → pinned hot/warm
```

Placement:

```text
SRAM: current attention tiles
DRAM: recent/high-attention KV blocks
Flash: old or low-attention KV blocks
```

---

## 6.3 MoE Experts

MoE models are attractive because only a subset of experts are active per token.

Placement:

```text
SRAM: active expert tiles
DRAM: likely top-k experts
Flash: cold experts
```

The predictor can use routing probabilities to prefetch likely experts.

---

## 6.4 Retrieval Pages

RAG workloads often require external memory.

Placement:

```text
SRAM: active retrieved chunks
DRAM: candidate chunks
Flash: full retrieval memory
```

---

## 7. Residency Manager

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

## 8. Promotion Policy

Promotion moves data upward:

```text
Flash → DRAM → SRAM
```

Promotion triggers:

- predicted imminent use
- repeated access
- high attention score
- high expert routing probability
- compiler hint
- speculative branch probability
- session priority

---

## 9. Eviction Policy

Eviction moves data downward:

```text
SRAM → DRAM → Flash
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

## 10. Prefetch Windows

A prefetch window defines how far ahead the runtime streams data.

Example:

```text
current layer: 12
SRAM: layer 12 tiles
DRAM: layers 13–16
Flash streaming: layers 17–32
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

## 11. Flash-Aware Tensor Layout

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

Example:

```text
/model/layer_000/qkv.block
/model/layer_001/qkv.block
/model/layer_002/qkv.block

/kv/session_42/head_00/block_0000.kv
/kv/session_42/head_00/block_0001.kv
/kv/session_42/head_01/block_0000.kv
```

---

## 12. Compression

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

Compression metadata:

```text
compression_type
original_size
compressed_size
decompress_cost
decompress_target_tier
checksum
```

---

## 13. DMA and IO Pipeline

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
    ↓
SSD DMA to DRAM buffer
    ↓
optional decompression
    ↓
residency table update
    ↓
SRAM promotion request
    ↓
compute consumes tile
```

---

## 14. Multi-Tenant Scheduling

For serving multiple users, the runtime must manage memory fairness.

State per session:

```text
session_id
priority
latency_budget
context_length
active_decode_state
DRAM_reservation
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

## 15. Failure Modes

Critical failure modes:

- flash read appears on token path
- predictor miss rate too high
- DRAM staging window too small
- random IO dominates
- decompression bottleneck
- SRAM thrashing
- DRAM thrashing
- multi-tenant interference
- SSD thermal throttling
- write amplification from KV spills

---

## 16. Architecture Summary

```text
SRAM:
  deterministic hot path

DRAM:
  prediction and staging

Flash:
  low-cost capacity

Runtime:
  residency and prefetch

Compiler:
  placement hints and dependency graph

Goal:
  hide flash behind compute and DRAM staging
```

---

## 17. One-Sentence IP Framing

A predictive AI inference memory fabric that uses compiler/runtime guidance to convert commodity SSD flash into a hidden high-capacity tier, while SRAM and DRAM maintain deterministic low-latency token generation.
