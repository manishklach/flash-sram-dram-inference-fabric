# Flash-SRAM-DRAM Inference Fabric

## One-Line Summary

A research project exploring deterministic inference memory orchestration across SRAM, commodity DRAM/LPDDR, and NVMe SSD flash.

> Flash is capacity. DRAM is prediction. SRAM is latency.

---

## Detailed Repository Description

Flash-SRAM-DRAM Inference Fabric is a research project exploring a software-defined memory hierarchy for large-scale AI inference that combines on-chip SRAM, commodity DRAM/LPDDR, and low-cost NVMe SSD flash into a predictive multi-tier memory fabric.

Instead of treating flash as directly addressable inference memory, the architecture uses compiler-guided scheduling, runtime prediction, asynchronous prefetching, and dynamic memory residency to transform flash into a hidden high-capacity tier while keeping the synchronous token-generation path serviced from SRAM and DRAM.

The project investigates long-context KV cache tiering, Mixture-of-Experts (MoE) expert staging, flash-native tensor layouts, predictive residency management, profile-guided memory placement, and Linux asynchronous I/O pipelines. It includes architecture documentation, simulator design, runtime concepts, compiler metadata, benchmarking methodology, and implementation roadmaps for building lower-cost AI inference systems without relying on massive pools of premium accelerator memory.

---

## Core Thesis: Deterministic Inference Memory Orchestration

Model inference, unlike game rendering or general CPU workloads, often has highly predictable access patterns.

- Transformer layer execution is deterministic.
- Weight access can often be linearized into layer bundles and tile sequences.
- KV cache access has temperature and locality rather than uniform randomness.
- MoE expert access can often be predicted from router behavior and routing history.
- Retrieval and RAG memory can often be staged before generation begins.
- Batch prefill and decode phases expose repeated, traceable access patterns that a runtime can exploit.

Because of this, low-cost flash can be used as a high-capacity sequential streaming tier.

The goal is not to make flash behave like true random-access memory.

The goal is to avoid putting flash on the synchronous token path.

> Flash is not treated as slow RAM. Flash is treated as a high-capacity sequential stream source. DRAM/LPDDR is the predictive staging buffer. SRAM is the deterministic scratchpad hot path.

> A synchronous flash read during token generation is treated as a policy failure, not a normal cache miss.

This framing is the main difference between this repo and generic virtual memory or SSD caching. The core idea is to exploit deterministic or traceable inference access patterns to linearize, prefetch, stage, and promote data before compute needs it.

---

## Why This Exists

AI inference is increasingly limited by memory cost, capacity, bandwidth, and energy.

Modern LLM serving often assumes that important model state must live in expensive accelerator-attached memory. This makes long-context inference, large MoE models, edge deployment, and on-prem enterprise inference costly.

This project explores a different path:

- SRAM for the deterministic compute-local hot path
- DRAM / LPDDR for predictive staging and warm residency
- NVMe SSD flash for low-cost high-capacity storage

The central idea is not to make SSD flash as fast as DRAM. That is not the claim.

The central idea is to determine whether deterministic inference access can be transformed into mostly sequential flash streams that are hidden behind DRAM staging and explicit SRAM scheduling.

---

## Core Architecture

```text
                      +--------------------------+
                      |       AI Compute         |
                      |  GPU / NPU / ASIC / CPU |
                      +-------------+------------+
                                    |
                                    v
                      +--------------------------+
                      |           SRAM           |
                      | deterministic scratchpad|
                      | hot tiles / active KV   |
                      +-------------+------------+
                                    |
                                    v
                      +--------------------------+
                      |       DRAM / LPDDR       |
                      | predictive staging buffer|
                      | warm KV / metadata / maps|
                      +-------------+------------+
                                    |
                                    v
                      +--------------------------+
                      |      NVMe SSD Flash      |
                      | sequential capacity tier |
                      | cold KV / model bundles  |
                      +--------------------------+
```

---

## Main Claim

A system can approach DRAM-like end-to-end inference latency for selected workloads by transforming SSD access from:

```text
random synchronous reads on the token path
```

into:

```text
large sequential asynchronous prefetch into DRAM before compute needs the data
```

The visible token path becomes:

```text
SRAM -> compute -> output token
```

while SSD traffic happens in the hidden path:

```text
SSD -> DRAM staging -> SRAM promotion
```

---

## What This Repository Contains

Core documents:

```text
README.md
ARCHITECTURE.md
RUNTIME.md
COMPILER.md
ROADMAP.md
BENCHMARKS.md
PATENT_IDEAS.md
THREATS_AND_LIMITATIONS.md
```

Key supporting documents:

```text
docs/DETERMINISTIC_INFERENCE_THESIS.md
docs/TRACE_GUIDED_LINEARIZATION.md
docs/SCRATCHPAD_RING_BUFFER.md
docs/FLASH_INTERFACE_MODES.md
docs/SIMULATOR_DESIGN.md
docs/FLASH_LAYOUT.md
docs/KV_CACHE_TIERING.md
docs/MOE_EXPERT_TIERING.md
docs/LINUX_IO_RUNTIME.md
docs/DATA_FORMATS.md
docs/DIAGRAMS.md
docs/COMPRESSION_AND_DECOMPRESSION.md
docs/LATENCY_BUDGET_MODEL.md
docs/PREDICTOR_MODEL_DESIGN.md
docs/COMMERCIALIZATION_STRATEGY.md
docs/PRODUCT_WEDGE.md
```

Early implementation stubs:

```text
simulator/
tools/
scripts/run_sim.py
```

---

## Target Workloads

This architecture is especially relevant for:

- long-context LLM inference
- retrieval-augmented generation
- MoE expert serving
- enterprise on-prem inference
- low-cost inference appliances
- CPU/NPU inference systems
- edge servers
- local AI assistants
- large batch prefill
- multi-tenant inference with cold state

---

## Non-Goals

This project does not claim that:

- SSD raw latency equals DRAM latency
- SSD should be accessed randomly during decode
- all model weights can be fetched from flash per token
- every workload can reach HBM-class performance
- training is solved
- prediction misses are free

The goal is narrower:

> Explore whether deterministic inference access can be predicted, traced, linearized, and streamed so that commodity flash can act as a low-cost capacity tier.

---

## Key Components

### 1. SRAM Scratchpad Hot Path

SRAM holds:

- current token working set
- active attention tiles
- current KV tiles
- decode scratch buffers
- routing metadata
- decompressed tensor tiles
- DMA queue descriptors

### 2. DRAM / LPDDR Predictive Staging Layer

DRAM / LPDDR holds:

- warm KV blocks
- upcoming layer bundles
- staged flash reads
- likely experts
- decompression buffers
- residency metadata
- page tables
- token history
- predictor state

### 3. Flash Sequential Capacity Layer

SSD flash holds:

- cold KV cache
- long-context history
- model bundles
- cold MoE experts
- embedding pages
- retrieval memory
- suspended sessions
- compressed cold state

### 4. Trace-Guided Layout and Prefetch Engine

The system can:

- capture inference traces
- identify repeated sequences
- repack flash-resident objects into linear layouts
- generate prefetch metadata
- replay with sequential streaming

---

## Core Principle

```text
Visible latency = max(compute time, SRAM/DRAM service time)

Not:

Visible latency = compute time + SSD read latency
```

If SSD appears directly in the token-critical path, the design has failed.

---

## Example Decode Pipeline

```text
Token T, layer 12 is computing:

SRAM:
  serves active layer-12 tiles

DRAM:
  holds layers 13-16 and hot KV blocks

SSD:
  streams layers 17-32 and cold KV bundles into DRAM
```

By the time the model reaches layer 17, the next data should already be present in DRAM and ready for promotion into SRAM.

---

## Design Philosophy

This is not generic SSD caching.

It is a deterministic inference memory orchestration system built from:

- compiler scheduling
- runtime prediction
- trace capture and replay
- flash-aware tensor layout
- async IO
- compression
- KV temperature tracking
- deadline-aware promotion
- program-managed SRAM scratchpad execution

---

## Project Status

The repo currently focuses on architecture, runtime, compiler, and benchmark design, plus an early runnable simulator path for trace-guided streaming research.

Current runnable evidence path:

```text
python scripts/run_sim.py
```

See:

- `docs/SIMULATOR_PROTOTYPE_RESULTS.md`
- `docs/LATENCY_BUDGET_MODEL.md`
- `docs/PREDICTOR_MODEL_DESIGN.md`

---

## Commercialization Path

The most credible first business is not a general-purpose replacement for accelerator memory.

The strongest initial wedge is a low-cost inference system for workloads where:

- long-context KV dominates memory cost
- regulated or on-prem deployment matters
- latency still matters, but not every workload needs frontier-scale HBM clusters
- MoE hot sets and cold state can be staged predictively
- customers care about total system cost, not just benchmark peak throughput

Practical first products could include:

- enterprise on-prem inference appliances for long-context RAG
- edge and sovereign AI servers with large cold-state capacity
- MoE-serving systems that keep only hot experts in premium memory
- software plus reference-platform licensing for OEMs and accelerator vendors

The business thesis is that lower memory cost can unlock workloads that are uneconomic on premium-memory-heavy systems, especially when customers need large context, private deployment, or many idle-but-resumable sessions.

---

## Big Vision

The long-term goal is to create a software-defined memory operating system for AI inference.

Instead of treating memory as a static hardware constraint, the runtime continuously moves tensors, KV blocks, experts, and retrieval state across SRAM, DRAM, and flash based on predicted future use and explicit deadlines.

The result, if the thesis holds, is a path toward larger models, longer context windows, and lower-cost AI serving on commodity memory systems.
