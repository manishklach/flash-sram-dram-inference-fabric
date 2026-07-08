# Simulator Prototype Results

## Purpose

This document records the first runnable prototype results from the repo's trace-driven simulator path.

The point is not to claim final performance. The point is to demonstrate that the repo now has a reproducible mechanism for comparing memory-interface modes across both structured and adversarial synthetic workloads.

---

## Command

```text
python scripts/run_sim.py
```

---

## Workloads

The current prototype emits two traces:

- `long_context_kv`: mostly local KV access with occasional cold lookups
- `random_old_context`: adversarial irregular old-context access

This combination is intentional. The repo should show both where deterministic streaming works and where it degrades.

---

## Current Output

```text
workload,mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy
long_context_kv,ram_emulation,3838.4,3838.4,3838.4,0.000,512,0,512,0.000
long_context_kv,hybrid,2000.0,2195.3,3838.4,0.908,25,248,25,1.000
long_context_kv,stream_to_scratchpad,2000.0,2000.0,2000.0,1.000,0,248,0,1.000
random_old_context,ram_emulation,3838.4,3838.4,3838.4,0.000,512,0,512,0.000
random_old_context,hybrid,2000.0,3011.1,3838.4,0.926,35,441,35,1.000
random_old_context,stream_to_scratchpad,2000.0,2000.0,2425.1,0.989,5,449,5,1.000
```

---

## Expected Interpretation

For `long_context_kv`, the optimized streaming modes dominate because the access pattern is structured enough to benefit from lookahead and reuse.

For `random_old_context`, the results do degrade, but not catastrophically in this prototype:

- `hybrid` shows a materially worse p95 and more policy failures than on the structured trace
- `stream_to_scratchpad` remains strong, but now shows a non-zero p99 tail and non-zero policy failures instead of a perfect result

That is directionally useful because the adversarial case is no longer free.

The exact numbers matter less than the pattern:

- compatibility mode should remain the worst baseline
- hybrid mode should improve structured traces but preserve some warmup and fallback tails
- stream-to-scratchpad should look strongest on structured traces
- adversarial traces should show the architecture's limits instead of pretending everything streams cleanly

In this prototype, the limits show up as a worse tail and non-zero policy failures under `random_old_context`, but the workload is still not adversarial enough to fully break optimized streaming. That is an important caveat.

---

## Why This Matters

This is exactly the kind of directional result the repo needs:

- it is consistent with the deterministic streaming thesis
- it distinguishes compatibility mode from optimized mode
- it provides both a success case and a stress case
- it gives a concrete baseline for future simulator work

---

## What This Does Not Prove

This prototype does not prove:

- real hardware performance
- universal workload coverage
- full-weight decode streaming viability
- robust behavior under high-entropy MoE or random old-context access

It is an early evidence loop, not a production benchmark.

It also does not yet prove that the current adversarial workload is harsh enough. A stronger next step is to introduce traces with lower locality and more surprise cold-block fan-out per decode step.

---

## Why It Matters

This prototype is still useful because it demonstrates:

- the repo has moved from static docs to executable comparison
- the interface-mode distinction is now testable
- future work can plug in more realistic traces, policies, and latency models
- the project can now report both wins and failure boundaries

That makes the project more credible for both technical collaborators and potential design partners.
