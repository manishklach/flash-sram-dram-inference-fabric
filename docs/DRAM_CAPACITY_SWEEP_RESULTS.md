# DRAM Capacity Sweep Results

## Purpose

This document summarizes the simulator's DRAM-capacity sweep.

The goal is to answer a practical systems question:

> How much DRAM staging capacity is needed before the architecture meaningfully improves over RAM-emulation for different workload classes?

---

## Command

```text
python scripts/sweep_dram.py
```

Artifacts:

```text
benchmarks/results/dram_capacity_sweep.csv
benchmarks/results/dram_capacity_sweep.json
```

---

## Capacities Swept

```text
16 MB
32 MB
64 MB
128 MB
256 MB
512 MB
```

Modes:

- `hybrid`
- `stream_to_scratchpad`

Workloads:

- `long_context_kv`
- `random_old_context`
- `cold_fanout`

---

## Key Findings

## 1. Structured Long-Context Workloads Improve Early

For `long_context_kv`:

- `16 MB` to `32 MB` DRAM is still too small and leaves p95 near the fallback regime
- `64 MB` materially improves p95
- `128 MB` is the first clearly strong region
- `256 MB` and above remove DRAM evictions in this prototype

This suggests that structured KV access can benefit from modest staging windows, but not tiny ones.

---

## 2. Random Old-Context Access Needs Much More DRAM

For `random_old_context`:

- even `64 MB` remains poor
- `128 MB` helps, but still leaves significant synchronous flash failures
- `256 MB` improves meaningfully
- `512 MB` is the first point where the optimized modes look relatively stable

This is important because it shows the architecture's dependence on both predictor quality and staging depth.

---

## 3. Cold Fan-Out Is Close to a Failure Regime

For `cold_fanout`:

- performance stays poor across the whole sweep
- more DRAM helps somewhat, but not enough to make the workload look healthy
- even at `512 MB`, synchronous flash failures remain high

This is a valuable negative result. It shows a regime where staging depth alone is not enough because locality itself has collapsed.

---

## 4. DRAM Evictions Are a First-Order Signal

The sweep makes DRAM evictions visible as a key bottleneck:

- structured workloads can drive evictions to zero at moderate capacity
- adversarial workloads continue to generate heavy eviction pressure
- eviction counts explain why p95 and p99 remain high even when sequentiality improves

This means the architecture is not just about flash speed or predictor quality. It is also about whether the staging tier is deep enough to absorb the workload.

---

## 5. Break-Even Insight

In this prototype:

- `long_context_kv` break-even begins around `128 MB`
- `random_old_context` break-even is closer to `512 MB`
- `cold_fanout` does not reach a healthy regime in the tested range

These are prototype results, not product claims, but they are exactly the kind of sizing insight the repo needs.

---

## Why This Matters

This sweep changes the repo from:

- "streaming can help"

to:

- "streaming helps in some workloads at modest DRAM depth"
- "streaming needs much more DRAM under random old-context pressure"
- "some fan-out regimes may remain uneconomic or unstable"

That is a far stronger basis for architecture decisions, fundraising, and design-partner discussion.
