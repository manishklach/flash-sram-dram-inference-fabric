# Patent Ideas

## Important Note

This document is an invention brainstorming document, not legal advice.

The goal is to identify potentially protectable technical concepts around a low-cost inference memory hierarchy using SRAM, DRAM/LPDDR, and SSD flash.

The strongest patent direction is not merely:

> Put model data on SSD.

That is too broad and obvious.

The stronger direction is:

> A predictive runtime/compiler memory fabric that hides flash latency by using DRAM as a staging tier and SRAM as a deterministic compute-adjacent tier.

---

# 1. Core Patent Title

## System and Method for Flash-Backed SRAM and DRAM Tiered Memory Orchestration for AI Inference

### Core Claim Concept

A system for AI inference that places inference state across SRAM, DRAM, and flash based on predicted future token-level access, where flash reads are issued asynchronously before the corresponding data is required by the compute engine.

### Key Elements

- SRAM hot tier
- DRAM staging tier
- flash capacity tier
- token-aware prediction
- tiered residency map
- asynchronous flash prefetch
- SRAM promotion before compute
- flash miss penalty feedback

---

# 2. Token-Aware Flash Prefetcher

## Concept

A prefetcher predicts data required by future tokens and initiates flash reads before the token path reaches those objects.

### Claims

- predicting future KV blocks based on token position
- predicting future layer tensors based on execution order
- predicting future expert pages based on router probabilities
- dynamically adjusting prefetch distance based on latency misses

---

# 3. SRAM Deterministic Hot-Path Scheduler

## Concept

SRAM is managed as a deterministic compute-adjacent tier, not as a conventional cache.

### Claims

- reserving SRAM regions per compute step
- promoting only objects with bounded next-use deadlines
- evicting immediately after micro-kernel completion
- using compiler tile schedule to avoid SRAM thrash

---

# 4. DRAM as Predictive Shock Absorber

## Concept

DRAM absorbs flash variability by holding a rolling window of predicted future inference objects.

### Claims

- DRAM window size based on flash latency and model layer time
- dynamic enlargement after late flash completions
- dynamic shrinking when prefetch waste is high
- per-session DRAM reservations based on latency class

---

# 5. Flash-Native Tensor Layout

## Concept

Tensors are stored in flash-aligned sequential bundles matching inference execution order.

### Claims

- packing layer tensors in execution order
- grouping co-accessed tensors into flash bundles
- aligning compression blocks to flash page boundaries
- profile-guided repacking based on runtime traces

---

# 6. KV Cache Temperature Tracking

## Concept

KV cache blocks are assigned temperatures based on recency, attention probability, and reuse.

### Claims

- hot KV in SRAM
- warm KV in DRAM
- cold KV in flash
- temperature based on attention heat map
- temperature decay over token distance
- sink-token pinning

---

# 7. Long-Context KV Flash Spill

## Concept

Long-context KV cache is selectively spilled to flash while preserving interactive latency.

### Claims

- old low-attention KV blocks compressed and spilled
- retrieval-triggered prefetch of old KV
- semantic clustering of old KV blocks
- reconstructing attention windows from DRAM and flash-resident blocks

---

# 8. MoE Expert Flash Residency

## Concept

MoE experts are stored in flash and prefetched to DRAM based on predicted routing.

### Claims

- storing cold experts in flash
- staging top-k probable experts in DRAM
- promoting selected expert tiles to SRAM
- using router logits to schedule flash reads
- grouping co-selected experts in flash layout

---

# 9. Compiler-Directed Memory Residency

## Concept

A compiler emits metadata that instructs the runtime where and when tensors should be staged.

### Claims

- tensor prefetch deadlines
- tier placement hints
- reuse-distance annotations
- compression eligibility
- prefetch bundle metadata
- eviction-after-use annotations

---

# 10. Runtime Feedback for Profile-Guided Repacking

## Concept

The runtime records access traces, and a repacking tool reorganizes flash layout.

### Claims

- collecting miss traces
- identifying co-accessed tensors
- repacking flash bundles
- updating compiler metadata
- improving sequential IO ratio

---

# 11. Adaptive Prefetch Window

## Concept

Prefetch distance is adjusted based on measured miss rate, flash latency, compute rate, and DRAM pressure.

### Claims

- increasing window when flash completes late
- reducing window when unused prefetched pages grow
- tenant-specific window sizing
- model-layer-specific window sizing

---

# 12. Multi-Tenant Flash-Aware Inference Scheduler

## Concept

The runtime schedules flash and DRAM resources across multiple inference sessions.

### Claims

- per-session DRAM quotas
- per-session flash queue-depth limits
- idle session compression
- active session SRAM pinning
- latency-class-aware eviction

---

# 13. Session Suspend/Resume Using Flash Memory Fabric

## Concept

Inactive inference sessions are demoted into flash and later resumed with predictive prefetch.

### Claims

- storing inactive KV state in flash
- retaining minimal resume metadata in DRAM
- prefetching resume window before user-visible continuation
- priority-based session restoration

---

# 14. Flash-Aware Speculative Decoding

## Concept

Speculative decoding branches are stored across tiers depending on probability of acceptance.

### Claims

- accepted branch hot state in SRAM/DRAM
- likely branch state in DRAM
- unlikely branch state in flash
- flash demotion of rejected branch KV
- branch-aware prefetch

---

# 15. Compression-Aware Tier Placement

## Concept

Compression decisions are tied to tier placement and predicted reuse.

### Claims

- do not compress SRAM-resident objects
- optionally compress DRAM warm objects
- compress flash cold objects
- decompression scheduled before predicted use
- compression policy based on latency budget

---

# 16. Flash IO Urgency Classes

## Concept

Flash read requests are assigned urgency classes based on predicted deadline.

### Claims

- urgent miss reads
- near-future prefetch reads
- background cold migration reads
- idle-session restore reads
- batch prefill reads

---

# 17. AI Memory Operating System

## Concept

A unified software layer manages AI inference memory across heterogeneous tiers.

### Claims

- abstract object residency across SRAM, DRAM, flash
- policy-driven promotion/eviction
- token-aware prefetch
- compiler metadata ingestion
- workload-adaptive placement

---

# 18. Semantic KV Clustering

## Concept

KV blocks are clustered by semantic or attention relevance before flash placement.

### Claims

- grouping KV blocks likely to be retrieved together
- layout based on semantic similarity
- prefetching clusters rather than individual blocks
- updating clusters based on observed attention

---

# 19. Flash-Aware RAG Memory

## Concept

Retrieval memory is stored on flash and staged into DRAM/SRAM based on prompt and query prediction.

### Claims

- prefetching likely retrieval pages before generation
- storing embeddings and chunks in flash-aligned groups
- combining vector search results with memory residency hints
- pinning high-confidence retrieved chunks

---

# 20. Thermal-Aware Flash Prefetch Control

## Concept

Prefetch intensity is adjusted based on SSD thermal and throttling state.

### Claims

- detecting flash thermal throttling
- reducing speculative prefetch during throttle
- increasing compression or DRAM reuse during throttle
- shifting requests across multiple SSDs

---

# 21. Endurance-Aware KV Spill

## Concept

The system reduces SSD writes by batching and compressing KV spills.

### Claims

- append-only KV logs
- write coalescing
- compression before spill
- write amplification tracking
- endurance-aware eviction

---

# 22. Flash-Backed Adapter Serving

## Concept

LoRA or adapter weights are stored in flash and loaded predictively.

### Claims

- tenant-specific adapters in flash
- hot adapters in DRAM
- active adapter tiles in SRAM
- adapter prefetch based on request routing

---

# 23. Deadline-Based Memory Promotion

## Concept

Objects are promoted based on deadline rather than just recency.

### Claims

- predicted-use deadline
- deadline-aware DRAM admission
- deadline-aware SRAM promotion
- flash IO ordered by deadline

---

# 24. Latency-Budgeted Residency Policy

## Concept

Objects are placed based on session latency budgets.

### Claims

- premium session pins more DRAM
- batch session uses flash more aggressively
- interactive session gets deeper prefetch
- policy updates when latency SLO is missed

---

# 25. Patent Package Structure

A strong filing could include:

## Independent Claims

1. Tiered SRAM/DRAM/flash inference memory system
2. Token-aware flash prefetch method
3. Compiler-directed tensor layout and residency method
4. KV cache temperature and tiering method
5. MoE expert flash residency method

## Dependent Claims

- compression
- multi-tenancy
- adaptive window sizing
- profile-guided repacking
- semantic clustering
- session suspend/resume
- SSD thermal control
- flash endurance management

---

# 26. Strongest Commercial Framing

The strongest commercial claim:

> Enables long-context and large-model inference on lower-cost commodity memory systems by converting SSD flash into a hidden capacity tier through predictive DRAM staging and SRAM deterministic scheduling.

---

# 27. What Makes It More Than Caching

Ordinary caching is reactive.

This system is predictive and inference-aware.

Differences:

```text
Caching:
  responds after access

This architecture:
  predicts before access
```

```text
Caching:
  recency-based

This architecture:
  token/layer/expert/deadline-based
```

```text
Caching:
  generic blocks

This architecture:
  tensors, KV blocks, experts, retrieval pages
```

```text
Caching:
  miss penalty accepted

This architecture:
  miss on token path is treated as failure
```
