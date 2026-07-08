# Flash--SRAM--DRAM Inference Fabric

## Overview

**Flash--SRAM--DRAM Inference Fabric (FSDIF)** is a proposed AI
inference memory architecture that replaces expensive, high-capacity
accelerator memory with a tiered hierarchy built from:

-   On-chip SRAM
-   Commodity DRAM / LPDDR
-   Commodity NVMe SSD flash

The objective is **not** to make flash as fast as DRAM. The objective is
to ensure that flash is almost never on the critical inference path.

Core philosophy:

> **Flash provides capacity. DRAM provides prediction. SRAM provides
> latency.**

------------------------------------------------------------------------

# Motivation

Modern LLM inference is increasingly constrained by memory capacity and
cost.

Traditional systems often rely on very large pools of expensive
accelerator-attached memory.

This architecture explores whether similar end-to-end inference
performance can be achieved using a software- and runtime-driven
hierarchy based on inexpensive flash storage.

------------------------------------------------------------------------

# Memory Hierarchy

``` text
            Compute ASIC / GPU / NPU
                     │
                     ▼
               ┌──────────┐
               │   SRAM   │
               └──────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  DRAM / LPDDR Tier     │
        └────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │  NVMe SSD Flash Tier   │
        └────────────────────────┘
```

------------------------------------------------------------------------

# Responsibilities

## SRAM

Ultra-low latency working memory.

Stores:

-   active attention tiles
-   current token working set
-   routing metadata
-   decode scratchpad
-   decompression buffers
-   active KV fragments

Goal:

Never stall compute.

------------------------------------------------------------------------

## DRAM / LPDDR

Prediction and staging layer.

Stores:

-   warm KV cache
-   prefetch windows
-   activation staging
-   current layer weights
-   page tables
-   residency metadata

Goal:

Hide flash latency.

------------------------------------------------------------------------

## Flash / SSD

Capacity layer.

Stores:

-   cold KV cache
-   long-context history
-   model pages
-   MoE experts
-   embeddings
-   retrieval pages
-   checkpoint state

Goal:

Massive capacity at very low cost.

------------------------------------------------------------------------

# Critical Design Principle

Flash must never be part of the synchronous decode path.

Instead:

    Critical path

    SRAM
    ↓

    Compute

    ↓

    Next token

Hidden path

    Flash

    ↓

    DRAM

    ↓

    SRAM

The runtime continuously streams future data before compute requires it.

------------------------------------------------------------------------

# Runtime Scheduler

A predictive runtime determines:

-   next layers
-   next experts
-   next KV blocks
-   next attention windows
-   future retrieval pages

Example pipeline

While token T computes:

-   SRAM serves current data
-   DRAM stages upcoming data
-   Flash streams future data

------------------------------------------------------------------------

# Prediction Engine

Possible signals:

-   token history
-   attention locality
-   layer order
-   expert probabilities
-   retrieval history
-   compiler scheduling
-   speculative decoding

------------------------------------------------------------------------

# Memory Promotion

Flash

↓

DRAM

↓

SRAM

Promotion based on:

-   access frequency
-   predicted reuse
-   temporal locality
-   decode order

Eviction based on:

-   temperature
-   reuse probability
-   recency
-   memory pressure

------------------------------------------------------------------------

# Flash Optimization

Instead of random reads:

-   sequential streaming
-   large page transfers
-   compressed tensors
-   batched reads
-   flash-aligned layouts
-   asynchronous DMA

------------------------------------------------------------------------

# Compiler Support

Compiler may emit:

-   tensor placement hints
-   prefetch schedule
-   layer dependency graph
-   residency annotations
-   expert grouping
-   streaming windows

------------------------------------------------------------------------

# Potential Innovations

-   Token-aware flash prefetch
-   KV temperature tracking
-   Compiler-directed residency
-   Layer-aware paging
-   Expert-aware prediction
-   Adaptive eviction
-   Flash-native tensor layout
-   Async decode pipeline
-   Background page migration

------------------------------------------------------------------------

# Advantages

-   Much lower memory cost
-   Larger supported models
-   Longer context windows
-   Reduced memory duplication
-   Better edge deployment
-   Commodity hardware

------------------------------------------------------------------------

# Challenges

-   Flash latency
-   Prediction accuracy
-   QoS under multi-tenancy
-   SSD endurance
-   DMA scheduling
-   Compression overhead

------------------------------------------------------------------------

# Research Questions

-   How large should the DRAM staging window be?
-   What prediction algorithms work best?
-   Can compiler hints outperform runtime-only prediction?
-   Can KV reuse be clustered semantically?
-   Can MoE experts remain almost entirely off-chip?

------------------------------------------------------------------------

# Prototype Roadmap

## Phase 1

Memory hierarchy simulator.

## Phase 2

Prefetch predictor.

## Phase 3

KV residency engine.

## Phase 4

Compiler annotations.

## Phase 5

Linux runtime.

## Phase 6

Hardware evaluation.

------------------------------------------------------------------------

# Repository Structure

    docs/
    simulator/
    runtime/
    compiler/
    prefetch/
    benchmarks/
    papers/
    diagrams/

------------------------------------------------------------------------

# Long-Term Vision

Transform commodity SSD flash into an effective inference-capacity tier
through predictive software, compiler guidance, and deterministic SRAM
scheduling---enabling large-model inference on dramatically lower-cost
systems without requiring massive pools of premium accelerator memory.

------------------------------------------------------------------------

# Disclaimer

This repository is a research exploration intended to investigate
architectural techniques for AI inference memory hierarchies.
Performance gains and latency characteristics are hypotheses to be
validated experimentally.
