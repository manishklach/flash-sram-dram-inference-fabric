# Simulator Prototype Results

## Purpose

This document records the first runnable prototype result from the repo's trace-driven simulator path.

The point is not to claim final performance. The point is to demonstrate that the repo now has a reproducible mechanism for comparing memory-interface modes under a synthetic long-context-style workload.

---

## Command

```text
python scripts/run_sim.py
```

---

## Current Output

```text
mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy
ram_emulation,3838.4,3838.4,3838.4,0.000,512,0,512,0.000
hybrid,2000.0,2195.3,3838.4,0.908,25,248,25,1.000
stream_to_scratchpad,2000.0,2000.0,2000.0,1.000,0,248,0,1.000
```

---

## Interpretation

On this synthetic workload:

- `ram_emulation` falls back to random flash reads on every critical access
- `hybrid` greatly reduces random reads and policy failures, but still shows a p99 tail from warmup and fallback behavior
- `stream_to_scratchpad` converts the workload into fully sequential prefetch on this trace and eliminates synchronous flash policy failures

This is exactly the kind of directional result the repo needs:

- it is consistent with the deterministic streaming thesis
- it distinguishes compatibility mode from optimized mode
- it gives a concrete baseline for future simulator work

---

## What This Does Not Prove

This prototype does not prove:

- real hardware performance
- universal workload coverage
- full-weight decode streaming viability
- robust behavior under high-entropy MoE or random old-context access

It is an early evidence loop, not a production benchmark.

---

## Why It Matters

This prototype is still useful because it demonstrates:

- the repo has moved from static docs to executable comparison
- the interface-mode distinction is now testable
- future work can plug in more realistic traces, policies, and latency models

That makes the project more credible for both technical collaborators and potential design partners.
