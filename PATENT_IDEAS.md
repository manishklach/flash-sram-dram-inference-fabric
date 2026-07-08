# Patent Ideas

## Important Note

This document is an invention brainstorming document, not legal advice.

The strongest direction is not "put model data on SSD." The stronger direction is a deterministic inference memory orchestration system that hides flash latency by using DRAM as a predictive staging tier and SRAM as a deterministic scratchpad.

---

## 1. Core Patent Title

System and Method for Deterministic Flash-Backed SRAM and DRAM Memory Orchestration for AI Inference

---

## 2. Existing Strong Directions

- token-aware flash prefetch
- SRAM deterministic hot-path scheduling
- DRAM as predictive shock absorber
- flash-native tensor layout
- KV cache temperature tracking
- MoE expert flash residency
- compiler-directed residency metadata
- adaptive prefetch windows
- multi-tenant flash-aware scheduling

---

## 3. Trace-Guided Flash Linearization for AI Inference

A method that records inference memory accesses and repacks flash-resident tensor objects into sequential layouts.

Claim themes:

- capture trace from inference run
- identify repeated access sequences
- group co-accessed objects
- repack contiguous flash bundles
- emit prefetch metadata
- replay and measure tail latency improvement

---

## 4. Hybrid RAM-Emulation to Scratchpad Migration

A system that initially runs flash-backed inference in RAM-emulation mode, records access traces, then migrates hot paths to explicit stream-to-scratchpad transfers.

Claim themes:

- compatibility first
- trace capture in functional mode
- identify optimized streaming path
- runtime migration to explicit transfer schedule

---

## 5. Redundant Sequential Placement

A method of duplicating tensor objects in multiple flash locations to preserve sequential read behavior when SRAM capacity is insufficient.

Claim themes:

- duplicate objects in multiple linear layouts
- trade extra flash capacity for lower random-access risk
- choose duplicated placement using trace and reuse constraints

---

## 6. Deadline-Aware Flash Page Streaming

A flash interface that transfers full pages or bundles into DRAM or SRAM based on predicted compute deadlines.

Claim themes:

- read requests carry expected use step
- read requests ordered by deadline
- late completions surfaced as policy failures
- decompression scheduled against deadline

---

## 7. Scratchpad Ring Buffer for AI Inference

A program-managed SRAM ring buffer where tile lifetimes are determined by compiler and runtime inference schedules.

Claim themes:

- explicit slot reservation
- fill from DRAM before deadline
- deterministic tile reuse
- no passive cache behavior

---

## 8. What Makes It More Than Caching

Ordinary caching is reactive.

This system is predictive and inference-aware.

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
  miss penalty accepted

This architecture:
  synchronous flash read on token path is failure
```
