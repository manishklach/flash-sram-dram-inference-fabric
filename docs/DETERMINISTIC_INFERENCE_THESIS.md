# Deterministic Inference Thesis

## 1. Why Inference Is Different

Inference is not the same as training, game rendering, or general-purpose CPU execution.

- training has large write volume, optimizer state, and activation churn
- inference often reuses a fixed graph and predictable execution order
- game rendering may be structured, but scene behavior and asset access are less tightly coupled to token-by-token semantics
- general CPU workloads tolerate broader randomness and rely on generic caching more heavily

Important inference properties:

- transformer layer order is deterministic
- weight access can often be linearized
- batch prefill exposes wide lookahead opportunities
- decode is narrower but still structured
- cold start may be tolerated more than per-token stalls
- continuous streaming bandwidth can matter more than random access capability

These properties make inference unusually suitable for explicit staging and streaming.

---

## 2. Why Flash Is Attractive

Flash is attractive because its cost per GB is directionally much lower than premium accelerator memory.

That matters for:

- larger model capacity
- cold weights
- cold experts
- long-context KV
- session suspend and resume
- enterprise inference appliances
- edge and on-prem systems

The thesis does not depend on exact public price ratios. The important directional point is that flash offers much cheaper capacity than the fastest compute-adjacent memory tiers.

---

## 3. Why Random Access Flash Fails

Flash has poor random-read latency compared to SRAM and DRAM.

Consequences:

- tiny random reads destroy effective bandwidth
- random flash on the token path creates p99 latency spikes
- RAM-emulation mode may work functionally but has fragile performance

If decode frequently falls back to unpredictable flash reads, the system may still run, but the latency profile becomes unsuitable for interactive inference.

---

## 4. Sequential Streaming Model

The preferred programming model is not random access. It is explicit sequential streaming.

Elements:

- full-page transfers
- 16KB+ page concept
- larger bundle reads
- flash-aligned tensor layout
- layer bundle streaming
- expert bundle streaming
- KV block streaming
- decompression before deadline

The question is not whether flash can answer arbitrary reads quickly. The question is whether inference objects can be laid out and consumed in bundle-sized streams early enough to hide flash latency.

---

## 5. Scratchpad vs Cache

Two programming models are worth studying.

### RAM-Emulation Mode

Pros:

- easier compatibility
- can reuse existing code
- incremental optimization path

Cons:

- fragile performance
- random access cliff
- cache hierarchy may hide problems until tail latency explodes

### Scratchpad / Explicit Transfer Mode

Pros:

- deterministic
- higher performance potential
- predictable SRAM use
- better for specialized accelerators

Cons:

- requires runtime and compiler changes
- requires explicit data movement
- harder developer model

Conclusion:

The repo should support both as research modes, but the high-performance path is scratchpad-oriented.

---

## 6. Trace Capture and Linearization

Key concept:

- run inference once
- capture memory access trace
- identify deterministic or repeated access sequences
- remap objects into linear flash layout
- replay with sequential prefetch
- perform profile-guided repacking

This is **Trace-Guided Flash Linearization**.

It is a bridge from observed behavior to an optimized flash layout instead of assuming the right layout a priori.

---

## 7. DRAM/LPDDR as Predictive Staging

DRAM is not simply a cache.

DRAM:

- absorbs flash latency
- holds upcoming bundles
- holds warm KV
- holds likely experts
- holds metadata and residency maps

> DRAM is the shock absorber between slow high-capacity flash and deterministic SRAM execution.

This is why the repo should prefer the terms "DRAM staging tier," "predictive staging buffer," and "warm residency layer" over generic cache language.

---

## 8. SRAM as Program-Managed Scratchpad

SRAM is the deterministic compute-local hot path.

Important concepts:

- active tile placement
- ring-buffer scratchpad
- explicit promotion from DRAM
- deterministic tile lifetime
- no accidental cache behavior
- tile deadlines

The SRAM programming model is closer to explicit scratchpad scheduling than to a passive hardware-managed cache.

---

## 9. Training Is Harder

Training is not the main target.

Limitations:

- training writes are frequent
- flash endurance becomes a major issue
- activations and optimizer state are harder to tier
- inference is the primary target
- training may require DRAM-heavy or specialized approaches

This repo should stay honest that the strongest thesis is about inference.

---

## 10. Summary

> The central bet is that inference memory access can be predicted, traced, linearized, and streamed. If true, commodity flash can become a useful capacity tier without behaving like random-access memory.
