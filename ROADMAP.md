# Roadmap

## 1. Project Vision

Build a deterministic inference memory fabric for AI inference using:

```text
SRAM + DRAM/LPDDR + commodity SSD flash
```

The goal is to explore whether large models, long context, and cold expert storage can be served at dramatically lower memory cost by turning predictable inference access into sequential flash streams.

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

- define architecture
- identify target workloads
- describe memory hierarchy
- document runtime policies
- document compiler interface
- identify patentable concepts

---

## 4. Phase: Deterministic Trace and Layout Engine

Tasks:

```text
[ ] Add access trace schema
[ ] Add synthetic deterministic layer trace generator
[ ] Add trace capture interface
[ ] Add trace linearizer
[ ] Add flash pack layout generator
[ ] Add sequential read ratio metric
[ ] Add RAM-emulation baseline
[ ] Add stream-to-scratchpad simulation mode
[ ] Add redundant sequential placement experiment
[ ] Add trace-guided benchmark configs
```

This phase is the bridge between the thesis and a testable simulator.

---

## 5. Milestone 1: Memory Hierarchy Simulator

Build a simulator that models SRAM, DRAM, and flash tiers.

Success criterion:

The simulator shows when flash can be hidden and when it cannot.

---

## 6. Milestone 2: KV Cache Residency Simulator

Model KV cache movement across tiers.

Experiments:

- long-context decode
- recent-token-heavy attention
- random old-context lookup
- retrieval-triggered old KV access
- multi-session idle/resume

---

## 7. Milestone 3: Predictive Prefetch Engine

Implement multiple prefetch policies:

- next-layer prefetch
- sliding-window KV prefetch
- attention-temperature prefetch
- MoE probability prefetch
- profile-guided prefetch
- adaptive-window prefetch
- trace-guided streaming

---

## 8. Milestone 4: Flash-Aware Tensor Layout

Create packed tensor files optimized for sequential flash access.

Deliverables:

```text
tools/linearize_trace.py
tools/pack_flash_layout.py
tools/analyze_read_pattern.py
```

---

## 9. Milestone 5: Async IO Runtime

Prototype real flash reads using Linux async IO.

Features:

- submit prefetch
- track completions
- queue-depth control
- urgent miss handling
- background decompression
- DRAM buffer pool

---

## 10. Milestone 6: Integration with Existing Inference Runtime

Possible targets:

- llama.cpp
- vLLM-style KV manager
- custom Python inference simulator
- ONNX Runtime prototype
- tiny transformer runtime

Initial integration should start with KV offload rather than full model offload.

---

## 11. Roadmap Summary

```text
docs -> traces -> simulator -> trace-guided layout -> async flash IO -> runtime integration -> compiler-guided scheduling
```

This keeps the project credible and testable.
