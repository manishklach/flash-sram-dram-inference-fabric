# Roadmap

## 1. Project Vision

Build a software-defined memory fabric for AI inference using:

```text
SRAM + DRAM/LPDDR + commodity SSD flash
```

The goal is to explore whether large models, long context, and cold expert storage can be served at dramatically lower memory cost by hiding flash latency through predictive scheduling.

---

## 2. Guiding Principles

1. Flash is never on the synchronous token path.
2. DRAM absorbs latency.
3. SRAM feeds compute.
4. Prediction is more important than raw bandwidth.
5. Sequential flash IO is acceptable; random flash IO is dangerous.
6. Runtime and compiler must cooperate.
7. Benchmarks must measure p95/p99 latency, not only average tokens/sec.
8. Honest failure analysis is part of the project.

---

## 3. Milestone 0: Documentation and Research Framing

### Goals

- define architecture
- identify target workloads
- describe memory hierarchy
- document runtime policies
- document compiler interface
- identify patentable concepts

### Deliverables

```text
README.md
ARCHITECTURE.md
RUNTIME.md
COMPILER.md
PATENT_IDEAS.md
BENCHMARKS.md
THREATS_AND_LIMITATIONS.md
```

### Success Criteria

- repo has clear technical story
- architecture is understandable from diagrams
- limitations are explicitly stated
- roadmap is credible

---

## 4. Milestone 1: Memory Hierarchy Simulator

### Goal

Build a simulator that models SRAM, DRAM, and flash tiers.

### Features

- configurable SRAM size
- configurable DRAM size
- configurable flash bandwidth/latency
- synthetic model layers
- synthetic KV cache traces
- prefetch window simulation
- hit/miss tracking

### Inputs

```text
model_layers
tensor_sizes
context_length
batch_size
flash_latency
flash_bandwidth
dram_size
sram_size
```

### Outputs

```text
token_latency
SRAM_hit_rate
DRAM_hit_rate
flash_sync_misses
prefetch_accuracy
prefetch_waste
```

### Success Criteria

The simulator shows when flash can be hidden and when it cannot.

---

## 5. Milestone 2: KV Cache Residency Simulator

### Goal

Model KV cache movement across tiers.

### Features

- KV blocks
- token ranges
- layer/head grouping
- hot/warm/cold classification
- sliding-window access
- sink-token pinning
- attention-score decay
- compression modeling

### Experiments

- long-context decode
- recent-token-heavy attention
- random old-context lookup
- retrieval-triggered old KV access
- multi-session idle/resume

### Success Criteria

Show which KV policies reduce DRAM use while preserving latency.

---

## 6. Milestone 3: Predictive Prefetch Engine

### Goal

Implement multiple prefetch policies.

### Policies

```text
next-layer prefetch
sliding-window KV prefetch
attention-temperature prefetch
MoE probability prefetch
profile-guided prefetch
adaptive-window prefetch
```

### Metrics

- useful prefetch %
- wasted prefetch %
- late prefetch %
- synchronous flash miss %
- DRAM pressure
- IO queue depth

### Success Criteria

Demonstrate that predictive policies outperform simple LRU caching.

---

## 7. Milestone 4: Flash-Aware Tensor Layout

### Goal

Create packed tensor files optimized for sequential flash access.

### Features

- large contiguous bundles
- page-aligned offsets
- metadata index
- checksum support
- compression block alignment
- per-layer bundles
- expert bundles
- KV block files

### Deliverables

```text
tools/pack_model.py
tools/inspect_pack.py
tools/repack_profile.py
```

### Success Criteria

Sequential reads dominate over random reads.

---

## 8. Milestone 5: Async IO Runtime

### Goal

Prototype real flash reads using Linux async IO.

### Options

- io_uring
- O_DIRECT
- mmap metadata
- fixed buffers
- pinned DRAM buffers

### Features

- submit prefetch
- track completions
- queue-depth control
- urgent miss handling
- background decompression
- DRAM buffer pool

### Success Criteria

Measured flash reads are overlapped with simulated compute.

---

## 9. Milestone 6: Integration with Existing Inference Runtime

### Possible Targets

- llama.cpp
- vLLM-style KV manager
- custom Python inference simulator
- ONNX Runtime prototype
- tiny transformer runtime

### Initial Integration

Start with KV offload rather than full model offload.

Why?

KV cache is easier to isolate and naturally has hot/cold behavior.

### Success Criteria

Real model or realistic trace demonstrates:

- lower DRAM footprint
- acceptable latency under predictable access
- clear failure mode when access becomes random

---

## 10. Milestone 7: Multi-Tenant Session Manager

### Goal

Support many sessions with different context lengths.

### Features

- per-session memory budget
- idle session demotion
- active session pinning
- session resume from flash
- priority scheduling
- latency class enforcement

### Success Criteria

Idle sessions can be spilled to flash while active sessions maintain low latency.

---

## 11. Milestone 8: Compression Layer

### Goal

Compress cold pages.

### Candidates

- cold KV blocks
- old retrieval chunks
- inactive expert pages
- dormant session state

### Metrics

- compression ratio
- decompression latency
- CPU overhead
- DRAM savings
- impact on p95/p99 latency

### Success Criteria

Compression improves effective capacity without excessive latency.

---

## 12. Milestone 9: Compiler Metadata

### Goal

Add model metadata to guide prefetch and placement.

### Features

- layer dependency graph
- tensor bundle metadata
- prefetch deadlines
- reuse-distance hints
- KV block hints
- MoE grouping hints

### Success Criteria

Compiler-guided prefetch beats runtime-only prefetch.

---

## 13. Milestone 10: Profile-Guided Repacking

### Goal

Rearrange flash layout based on real traces.

### Workflow

```text
run workload
collect access trace
identify co-access groups
repack model
rerun workload
compare latency
```

### Success Criteria

Profile-guided layout reduces random IO and late prefetches.

---

## 14. Milestone 11: Hardware-Aware Optimization

### Goal

Tune behavior based on SSD and DRAM characteristics.

### Features

- SSD queue-depth tuning
- thermal throttling detection
- read-size optimization
- NUMA placement
- CPU affinity
- memory pinning
- huge pages
- direct IO

### Success Criteria

System adapts to consumer SSD, enterprise SSD, and embedded flash profiles.

---

## 15. Milestone 12: Research Paper / Patent Package

### Deliverables

- architecture paper
- benchmark report
- patent claim set
- diagrams
- implementation screenshots
- trace results
- limitations section

### Target Story

Commodity flash can become a hidden AI inference capacity tier if the system uses predictive DRAM staging and deterministic SRAM scheduling.

---

## 16. Stretch Goals

- computational storage decompression
- CXL memory support
- remote flash pools
- edge appliance prototype
- NPU integration
- kernel-bypass IO
- hardware prefetch controller
- FPGA proof-of-concept
- flash endurance model
- inference memory OS abstraction

---

## 17. Near-Term TODO List

```text
[ ] Build simulator skeleton
[ ] Define tier latency model
[ ] Define KV block trace format
[ ] Implement LRU baseline
[ ] Implement predictive prefetch baseline
[ ] Add metrics collector
[ ] Add visualization scripts
[ ] Create sample workloads
[ ] Write benchmark methodology
[ ] Add architecture diagrams
[ ] Add patent concept list
```

---

## 18. Roadmap Summary

The project should proceed in this order:

```text
docs → simulator → KV residency → async flash IO → real runtime integration → compiler hints → profile-guided layout
```

This keeps the project credible and testable.
