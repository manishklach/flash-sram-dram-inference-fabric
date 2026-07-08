# Benchmarks and Evaluation Methodology

## 1. Goal

The goal of benchmarking is to determine when the Flash-SRAM-DRAM Inference Fabric can hide flash latency and when it cannot.

The benchmark must not only measure average throughput.

It must measure:

- p50 latency
- p95 latency
- p99 latency
- time to first token
- synchronous flash miss rate
- prefetch accuracy
- DRAM hit rate
- SRAM hit rate
- memory cost reduction

---

## 2. Key Hypotheses

## Hypothesis 1

If data access is predictable, flash can be hidden behind DRAM staging and compute.

## Hypothesis 2

If access is random and unpredictable, latency collapses.

## Hypothesis 3

Trace-guided layout and compiler-guided prefetch outperform runtime-only caching.

## Hypothesis 4

KV cache has enough temperature structure to tier across SRAM, DRAM, and flash.

## Hypothesis 5

MoE expert serving benefits from flash residency because only a subset of experts is active per token.

---

## 3. Metrics

## 3.1 Latency Metrics

```text
TTFT: time to first token
TPOT: time per output token
p50 token latency
p95 token latency
p99 token latency
max token latency
```

## 3.2 Throughput Metrics

```text
tokens/sec
requests/sec
batch throughput
prefill throughput
decode throughput
```

## 3.3 Residency and Streaming Metrics

```text
SRAM hit rate
DRAM hit rate
synchronous flash miss rate
prefetch accuracy
prefetch waste
late prefetch rate
sequential read ratio
random read count
average read size
trace layout efficiency
redundant capacity overhead
```

---

## 4. Baselines

## Baseline A: All DRAM

All inference state fits in DRAM.

## Baseline B: Reactive LRU Cache

Flash-backed memory with simple LRU caching.

## Baseline C: No Prefetch

Flash reads happen only on demand.

## Baseline D: Fixed Window Prefetch

Always prefetch N layers or N KV blocks ahead.

## Baseline E: Oracle Prefetch

Perfect future knowledge.

---

## 5. Core Workloads

## 5.1 Sequential Layer Streaming

```text
layer 0 -> layer 1 -> ... -> layer N
```

## 5.2 Long-Context KV Decode

Test local attention, sink tokens, sparse access, and random old-context lookup.

## 5.3 MoE Expert Serving

Test expert prefetch under low-entropy and high-entropy routing.

## 5.4 RAG Memory Pages

Test retrieval-prefetch timing before and during generation.

## 5.5 Multi-Tenant Sessions

Test active and idle session spill and resume.

---

## 6. RAM-Emulation vs Stream-to-Scratchpad

Compare:

- functional RAM-emulation mode
- optimized explicit streaming mode
- hybrid mode

Metrics:

- p50/p95/p99 token latency
- random read count
- sequential read ratio
- synchronous flash miss rate

This benchmark should highlight the difference between compatibility and performance.

---

## 7. Trace-Guided Layout Benchmark

Compare:

- naive layout
- layer-order layout
- trace-guided layout
- oracle layout

Track:

- sequential read ratio
- average read size
- late prefetch rate
- p95/p99 token latency
- synchronous flash miss rate

---

## 8. Redundant Sequential Placement Benchmark

Measure:

- capacity overhead
- reduction in random reads
- latency improvement

This benchmark tests when extra flash duplication is cheaper than unpredictable access.

---

## 9. Simulator Parameters

Example config:

```yaml
sram:
  size_mb: 64
  latency_ns: 5

dram:
  size_gb: 16
  latency_ns: 80
  bandwidth_gbps: 100

flash:
  read_latency_us: 80
  bandwidth_gbps: 7
  queue_depth: 64
  optimal_read_size_mb: 4

model:
  layers: 32
  hidden_size: 4096
  kv_block_tokens: 128
```

---

## 10. Success Criteria

The architecture is promising if:

```text
synchronous flash miss rate stays low
p95 latency stays near the DRAM baseline
p99 latency does not explode
random read count drops materially under streaming modes
sequential read ratio improves with trace-guided layout
DRAM use drops materially relative to baseline
```

---

## 11. Failure Criteria

The design is failing if:

```text
flash reads frequently block decode
RAM-emulation mode hides a severe p99 cliff
trace-guided layout does not reduce randomness
prefetch waste consumes DRAM
compression blocks compute
SSD throttles under load
eviction churn is high
```

---

## 12. Benchmark Summary

A good benchmark suite should prove both sides:

1. Where the architecture works extremely well
2. Where it honestly fails

The most important comparison is not just flash versus DRAM. It is generic flash-backed compatibility mode versus deterministic stream-to-scratchpad orchestration.
