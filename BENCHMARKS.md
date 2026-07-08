# Benchmarks and Evaluation Methodology

## 1. Goal

The goal of benchmarking is to determine when the Flash–SRAM–DRAM Inference Fabric can hide flash latency and when it cannot.

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

Compiler-guided prefetch outperforms runtime-only caching.

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

## 3.3 Memory Metrics

```text
SRAM utilization
DRAM utilization
flash utilization
DRAM saved vs baseline
effective context capacity
```

## 3.4 Residency Metrics

```text
SRAM hit rate
DRAM hit rate
flash hit rate
synchronous flash miss rate
promotion rate
eviction rate
thrash rate
```

## 3.5 Prefetch Metrics

```text
prefetch accuracy
prefetch waste
late prefetch rate
average prefetch lead time
queue depth
sequential read ratio
random read ratio
```

## 3.6 Flash Metrics

```text
read bandwidth
read latency
queue depth
IO size distribution
thermal throttling events
write amplification
SSD endurance estimate
```

---

## 4. Baselines

The architecture must be compared against baselines.

## Baseline A: All DRAM

All inference state fits in DRAM.

This is the ideal non-flash baseline.

## Baseline B: Reactive LRU Cache

Flash-backed memory with simple LRU caching.

This shows whether prediction improves over generic caching.

## Baseline C: No Prefetch

Flash reads happen only on demand.

This should perform poorly but is useful for contrast.

## Baseline D: Fixed Window Prefetch

Always prefetch N layers or N KV blocks ahead.

## Baseline E: Oracle Prefetch

Perfect future knowledge.

This provides an upper bound.

---

## 5. Workloads

## 5.1 Sequential Layer Streaming

Tests model layer predictability.

Workload:

```text
layer 0 → layer 1 → ... → layer N
```

Expected result:

Good performance because layer order is predictable.

---

## 5.2 Long-Context KV Decode

Tests KV cache tiering.

Parameters:

```text
context length: 8K, 32K, 128K, 1M tokens
KV block size: 64, 128, 256 tokens
DRAM budget: small, medium, large
```

Expected result:

Good when attention is local/sparse.
Poor when attention randomly touches old context.

---

## 5.3 Sink Token Workload

Tests pinning of important early tokens.

Expected behavior:

Sink tokens remain in SRAM/DRAM.

---

## 5.4 Random Old-Context Lookup

Adversarial workload.

The model repeatedly attends to unpredictable old context.

Expected result:

Flash misses increase.
Latency worsens.
This defines limitations.

---

## 5.5 MoE Expert Serving

Tests expert prefetch.

Parameters:

```text
num_experts
experts_per_token
expert_size
routing_entropy
DRAM budget
```

Expected result:

Good when routing is predictable.
Poor when expert selection is high-entropy.

---

## 5.6 Multi-Tenant Sessions

Tests session spilling.

Workload:

```text
100 sessions
10 active
90 idle
idle sessions spill to flash
active sessions remain hot
```

Expected result:

DRAM use falls without hurting active latency.

---

## 5.7 RAG Memory Pages

Tests retrieval prefetch.

Workload:

```text
query → likely chunks → generation
```

Expected result:

If retrieval happens before decode, chunks can be prefetched.

---

## 6. Simulator Parameters

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

## 7. Experiment Matrix

## 7.1 DRAM Size Sweep

```text
DRAM = 2GB, 4GB, 8GB, 16GB, 32GB
```

Measure:

- flash misses
- latency
- prefetch waste

## 7.2 Prefetch Window Sweep

```text
window = 1, 2, 4, 8, 16, 32 layers/blocks
```

Measure:

- late prefetch
- wasted prefetch
- DRAM pressure

## 7.3 Flash Read Size Sweep

```text
read size = 4KB, 64KB, 1MB, 4MB, 16MB
```

Measure:

- bandwidth
- latency
- random vs sequential penalty

## 7.4 Context Length Sweep

```text
context = 8K, 32K, 128K, 512K, 1M
```

Measure:

- KV memory use
- cold spill rate
- p99 latency

---

## 8. Success Criteria

The architecture is promising if:

```text
synchronous flash miss rate < 1%
p95 latency close to DRAM baseline
p99 latency does not explode
DRAM usage materially lower than baseline
prefetch waste acceptable
SSD bandwidth not saturated
```

More aggressive success criterion:

```text
p95 token latency within 10–25% of DRAM baseline
DRAM usage reduced by 50%+
```

---

## 9. Failure Criteria

The design is failing if:

```text
flash reads frequently block decode
p99 latency is unstable
prefetch waste consumes DRAM
random IO dominates
compression blocks compute
SSD throttles under load
eviction churn is high
```

---

## 10. Benchmark Output Format

Example CSV:

```csv
workload,policy,dram_gb,context,p50_ms,p95_ms,p99_ms,sram_hit,dram_hit,flash_sync_miss,prefetch_accuracy
long_kv,predictive,8,128k,12,18,32,0.92,0.97,0.004,0.81
```

---

## 11. Visualization Ideas

Charts:

- p95 latency vs DRAM size
- synchronous flash miss rate vs prefetch window
- prefetch accuracy vs workload type
- DRAM savings vs p99 penalty
- sequential IO ratio vs layout strategy
- KV temperature heatmap
- expert routing predictability vs latency

---

## 12. Important Benchmark Warning

Do not only show average tokens/sec.

Average tokens/sec can hide catastrophic tail latency.

This project must optimize for:

```text
interactive inference latency
p95 / p99 stability
```

---

## 13. Benchmark Summary

A good benchmark suite should prove both sides:

1. Where the architecture works extremely well
2. Where it honestly fails

That credibility makes the project stronger.
