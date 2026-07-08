# Flash–SRAM–DRAM Inference Fabric

## One-Line Summary

A low-cost AI inference memory architecture that combines **SRAM**, **commodity DRAM/LPDDR**, and **NVMe SSD flash** into a predictive, software-defined memory fabric for large-model inference.

> **Flash is capacity. DRAM is prediction. SRAM is latency.**

---

## Detailed Repository Description

Flash–SRAM–DRAM Inference Fabric is a research project exploring a software-defined memory hierarchy for large-scale AI inference that combines on-chip SRAM, commodity DRAM/LPDDR, and low-cost NVMe SSD flash into a predictive multi-tier memory fabric.

Instead of treating flash as directly addressable inference memory, the architecture uses compiler-guided scheduling, runtime prediction, asynchronous prefetching, and dynamic memory residency to transform flash into a hidden high-capacity tier while keeping the synchronous token-generation path serviced from SRAM and DRAM.

The project investigates long-context KV cache tiering, Mixture-of-Experts (MoE) expert staging, flash-native tensor layouts, predictive residency management, profile-guided memory placement, and Linux asynchronous I/O pipelines. It includes architecture documentation, simulator design, runtime concepts, compiler metadata, benchmarking methodology, and implementation roadmaps for building lower-cost AI inference systems without relying on massive pools of premium accelerator memory.

---

## Why This Exists

AI inference is increasingly limited by memory cost, capacity, bandwidth, and energy.

Modern LLM serving typically assumes that important model state must live in expensive high-bandwidth accelerator memory. This makes long-context inference, large MoE models, edge deployment, and on-prem enterprise inference expensive.

This project explores a different path:

Instead of relying on large pools of premium accelerator memory, use:

- **SRAM** for the deterministic hot path
- **DRAM / LPDDR** for warm staging and prediction
- **NVMe SSD flash** for low-cost high-capacity storage

The central idea is not to make SSD flash as fast as DRAM. That is impossible at the raw-device level.

The central idea is to ensure that flash is **almost never on the synchronous token-critical path**.

---

## Core Architecture

```text
                      ┌──────────────────────────┐
                      │      AI Compute           │
                      │  GPU / NPU / ASIC / CPU   │
                      └─────────────┬────────────┘
                                    │
                                    ▼
                      ┌──────────────────────────┐
                      │          SRAM             │
                      │  hot tiles / active KV    │
                      │  decode scratch / queues  │
                      └─────────────┬────────────┘
                                    │
                                    ▼
                      ┌──────────────────────────┐
                      │       DRAM / LPDDR        │
                      │ warm KV / prefetch window │
                      │ staging / metadata / maps │
                      └─────────────┬────────────┘
                                    │
                                    ▼
                      ┌──────────────────────────┐
                      │       NVMe SSD Flash      │
                      │ cold KV / model pages     │
                      │ experts / long context    │
                      └──────────────────────────┘
```

---

## Main Claim

A system can approach DRAM-like end-to-end inference latency for selected workloads by transforming SSD access from:

```text
random synchronous read on token path
```

into:

```text
large sequential asynchronous prefetch into DRAM before compute needs the data
```

The token path becomes:

```text
SRAM → compute → output token
```

while SSD traffic happens in the background:

```text
SSD → DRAM → SRAM
```

---

## What This Repository Contains

Suggested documentation structure:

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

Optional future source-tree structure:

```text
simulator/
  memory_model.py
  tier_model.py
  kv_trace.py
  prefetch_sim.py

runtime/
  residency_manager/
  prefetcher/
  flash_io/
  scheduler/

compiler/
  annotations/
  placement/
  graph_analysis/

benchmarks/
  traces/
  workloads/
  latency/
  throughput/

docs/
  diagrams/
  papers/
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

This project does **not** claim that:

- SSD raw latency equals DRAM latency
- SSD should be accessed randomly during decode
- all model weights can be fetched from flash per token
- every workload can reach GPU-HBM-class performance
- prediction misses are free

The goal is narrower but powerful:

> Design the memory hierarchy so the compute engine almost never waits for flash.

---

## Key Components

### 1. SRAM Hot Path

SRAM holds:

- current token working set
- active attention tiles
- current KV blocks
- decode scratch buffers
- routing metadata
- decompressed tensor tiles
- DMA queues and descriptors

### 2. DRAM Prediction Layer

DRAM / LPDDR holds:

- warm KV blocks
- upcoming layer data
- staging buffers
- prefetch windows
- decompression buffers
- residency metadata
- page tables
- token history
- predictor state

### 3. Flash Capacity Layer

SSD flash holds:

- cold KV cache
- long-context history
- model pages
- cold MoE experts
- embedding pages
- retrieval memory
- checkpoint state
- suspended sessions

### 4. Predictive Residency Engine

The residency engine decides:

- what should stay in SRAM
- what should stay in DRAM
- what should remain in flash
- what should be prefetched
- what should be evicted
- what should be compressed
- what should be pinned

### 5. Token-Aware Prefetcher

The prefetcher predicts:

- next layers
- next heads
- next KV pages
- next experts
- next retrieval chunks
- likely future prompts
- reuse distance

---

## Core Principle

```text
Visible latency = max(compute time, SRAM/DRAM service time)

Not:

Visible latency = compute time + SSD read latency
```

If SSD appears directly in the critical path, the design has failed.

---

## Example Decode Pipeline

```text
Token T, layer 12 is computing:

SRAM:
  serves active layer-12 tiles

DRAM:
  holds layers 13–16 and hot KV blocks

SSD:
  streams layers 17–32 and cold KV pages into DRAM
```

By the time the model reaches layer 17, data should already be resident in DRAM.

---

## Design Philosophy

This is not merely caching.

It is a **software-defined inference memory fabric**.

The fabric combines:

- compiler scheduling
- runtime prediction
- memory residency control
- flash-aware tensor layout
- async IO
- compression
- KV temperature tracking
- latency-aware eviction
- multi-tier placement

---

## Possible Repo Description

> A research architecture for low-cost AI inference that combines SRAM, commodity DRAM/LPDDR, and NVMe SSD flash into a predictive memory fabric for long-context LLMs, MoE models, and edge/on-prem inference.

---

## Suggested GitHub Topics

```text
ai-inference
llm-inference
memory-hierarchy
sram
dram
lpddr
ssd
nvme
flash-storage
kv-cache
long-context
moe
prefetching
compiler-runtime
inference-optimization
edge-ai
rag
systems-research
```

---

## Project Status

Research concept and architecture documentation.

Future phases may include:

- trace simulator
- KV-cache residency prototype
- Linux async IO runtime
- benchmark harness
- compiler annotation experiments
- flash-aware tensor layout prototype

---

## Big Vision

The long-term goal is to create a **software-defined memory operating system for AI inference**.

Instead of treating memory as a static hardware constraint, the runtime continuously moves tensors, KV blocks, experts, and retrieval memory across SRAM, DRAM, and flash based on predicted future use.

The result is a path toward larger models, longer context windows, and lower-cost AI serving.
