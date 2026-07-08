# Original Concept Note

This file preserves the initial repository concept used to seed the project.

## Overview

Flash-SRAM-DRAM Inference Fabric (FSDIF) is a proposed AI inference memory architecture built from:

- on-chip SRAM
- commodity DRAM / LPDDR
- commodity NVMe SSD flash

The objective is not to make flash as fast as DRAM. The objective is to keep flash almost entirely off the critical inference path.

> Flash provides capacity. DRAM provides prediction. SRAM provides latency.

## Motivation

Modern LLM inference is increasingly constrained by memory capacity and cost. This architecture explores whether comparable inference behavior can be achieved with a software- and runtime-driven hierarchy built from inexpensive flash storage and commodity memory.

## Responsibilities

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

Flash must never be part of the synchronous decode path.

```text
Critical path
  SRAM -> Compute -> Next token

Hidden path
  Flash -> DRAM -> SRAM
```

The runtime continuously streams future data before compute requires it.

## Runtime scheduler

A predictive runtime determines:

- next layers
- next experts
- next KV blocks
- next attention windows
- future retrieval pages

Example pipeline while token `T` computes:

- SRAM serves current data
- DRAM stages upcoming data
- Flash streams future data

## Prediction engine signals

- token history
- attention locality
- layer order
- expert probabilities
- retrieval history
- compiler scheduling
- speculative decoding

## Memory promotion

Promotion path:

```text
Flash -> DRAM -> SRAM
```

Promotion factors:

- access frequency
- predicted reuse
- temporal locality
- decode order

Eviction factors:

- temperature
- reuse probability
- recency
- memory pressure

## Flash optimization

Instead of random reads, the design emphasizes:

- sequential streaming
- large page transfers
- compressed tensors
- batched reads
- flash-aligned layouts
- asynchronous DMA

## Compiler support

Possible compiler outputs:

- tensor placement hints
- prefetch schedules
- layer dependency graphs
- residency annotations
- expert grouping
- streaming windows

## Potential innovations

- token-aware flash prefetch
- KV temperature tracking
- compiler-directed residency
- layer-aware paging
- expert-aware prediction
- adaptive eviction
- flash-native tensor layout
- async decode pipeline
- background page migration

## Advantages

- lower memory cost
- larger supported models
- longer context windows
- reduced memory duplication
- better edge deployment
- commodity hardware

## Challenges

- flash latency
- prediction accuracy
- QoS under multi-tenancy
- SSD endurance
- DMA scheduling
- compression overhead

## Research questions

- How large should the DRAM staging window be?
- What prediction algorithms work best?
- Can compiler hints outperform runtime-only prediction?
- Can KV reuse be clustered semantically?
- Can MoE experts remain almost entirely off-chip?

## Prototype roadmap

1. Memory hierarchy simulator
2. Prefetch predictor
3. KV residency engine
4. Compiler annotations
5. Linux runtime
6. Hardware evaluation

## Disclaimer

This repository is a research exploration intended to investigate architectural techniques for AI inference memory hierarchies. Performance gains and latency characteristics remain hypotheses to be validated experimentally.
