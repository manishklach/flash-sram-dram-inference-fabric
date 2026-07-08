# Flash-SRAM-DRAM Inference Fabric

Flash-SRAM-DRAM Inference Fabric (FSDIF) is a research repository exploring an inference memory architecture that uses a tiered hierarchy of SRAM, commodity DRAM/LPDDR, and NVMe SSD flash to reduce dependence on large pools of premium accelerator-attached memory.

The core idea is simple:

> Flash provides capacity. DRAM provides prediction. SRAM provides latency.

The design goal is not to make flash behave like DRAM. The design goal is to keep flash off the synchronous decode path by relying on prediction, prefetch, and carefully managed promotion across tiers.

## Why this exists

Modern LLM inference is increasingly constrained by memory capacity and cost. This repo explores whether comparable end-to-end inference behavior can be achieved with:

- small, deterministic on-chip SRAM working sets
- commodity DRAM as the staging tier
- commodity NVMe SSDs as the capacity tier
- software runtime and compiler guidance that move data before compute needs it

## Architecture

```text
            Compute ASIC / GPU / NPU
                     |
                     v
               +----------+
               |   SRAM   |
               +----------+
                     |
                     v
        +------------------------+
        |  DRAM / LPDDR Tier     |
        +------------------------+
                     |
                     v
        +------------------------+
        |  NVMe SSD Flash Tier   |
        +------------------------+
```

### Tier responsibilities

`SRAM`

- active attention tiles
- current token working set
- routing metadata
- decode scratchpad
- decompression buffers
- active KV fragments

`DRAM / LPDDR`

- warm KV cache
- prefetch windows
- activation staging
- current layer weights
- page tables
- residency metadata

`Flash / SSD`

- cold KV cache
- long-context history
- model pages
- MoE experts
- embeddings
- retrieval pages
- checkpoint state

## Critical design principle

Flash should not sit on the synchronous decode path.

```text
Critical path
  SRAM -> Compute -> Next token

Hidden path
  Flash -> DRAM -> SRAM
```

The runtime continuously streams future data while the current token is being processed.

## Research areas

- token-aware flash prefetch
- KV temperature tracking
- compiler-directed residency
- layer-aware paging
- expert-aware prediction
- adaptive eviction
- flash-native tensor layout
- async decode pipelines
- background page migration

## Key questions

- How large should the DRAM staging window be?
- Which prediction algorithms work best?
- When do compiler hints beat runtime-only prediction?
- Can KV reuse be clustered semantically?
- Can MoE experts remain mostly off-chip without hurting latency?

## Roadmap

1. Memory hierarchy simulator
2. Prefetch predictor
3. KV residency engine
4. Compiler annotations
5. Linux runtime
6. Hardware evaluation

## Repository layout

```text
docs/
simulator/
runtime/
compiler/
prefetch/
benchmarks/
papers/
diagrams/
```

## Status

This is an early-stage public research repository. The current contents focus on the architecture thesis, repository structure, and workstreams needed to begin simulation and prototype development.

## Disclaimer

This project is a research exploration. Performance gains and latency characteristics described here are hypotheses that need to be validated experimentally.
