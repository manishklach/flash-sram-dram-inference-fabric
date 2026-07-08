# Simulator Prototype Results

## Purpose

This document records the current runnable prototype results from the repo's trace-driven simulator path.

The point is not to claim final performance. The point is to demonstrate that the repo now has a reproducible mechanism for comparing memory-interface modes across both structured and adversarial synthetic workloads, and to show where the architecture approaches failure.

---

## Command

```text
python scripts/run_sim.py
```

Artifacts written by the script:

```text
benchmarks/results/simulator_matrix.csv
benchmarks/results/simulator_matrix.json
```

---

## Workloads

The current prototype emits three traces:

- `long_context_kv`: mostly local KV access with occasional cold lookups
- `random_old_context`: adversarial irregular old-context access
- `cold_fanout`: harsher low-locality cold-block fan-out designed to challenge prefetch locality assumptions

This combination is intentional. The repo should show both where deterministic streaming works and where it degrades.

---

## Current Output

```text
workload,mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy,prefetch_waste_rate,dram_evictions
long_context_kv,ram_emulation,3838.4,5277.8,5277.8,0.000,527,0,527,0.000,0.000,0
long_context_kv,hybrid,2000.0,3439.4,3838.4,0.870,37,248,37,0.032,0.968,184
long_context_kv,stream_to_scratchpad,2000.0,3336.0,3439.4,0.954,12,248,12,0.032,0.968,184
random_old_context,ram_emulation,7676.7,7676.7,7676.7,0.000,960,0,960,0.000,0.000,0
random_old_context,hybrid,5378.8,5838.4,6068.2,0.584,355,498,355,0.430,0.570,434
random_old_context,stream_to_scratchpad,5378.8,6033.7,6068.2,0.601,332,500,332,0.422,0.578,436
cold_fanout,ram_emulation,11515.1,11515.1,11515.1,0.000,1472,0,1472,0.000,0.000,0
cold_fanout,hybrid,9446.9,9906.5,10136.3,0.344,962,504,962,1.000,0.000,440
cold_fanout,stream_to_scratchpad,9446.9,9906.5,10136.3,0.352,939,510,939,0.984,0.016,446
```

---

## Interpretation

For `long_context_kv`, the optimized streaming modes dominate because the access pattern is structured enough to benefit from lookahead and reuse.

However, the stricter usefulness window now shows that much of the speculative prefetch volume is not actually helping the immediate token-critical path:

- `hybrid` and `stream_to_scratchpad` both show about `0.968` prefetch waste rate on this trace
- both optimized modes now also suffer `184` DRAM evictions because the simulated staging window is capacity-limited

That is a useful correction. The architecture may still hide latency, but the current prefetch strategy is overly eager.

For `random_old_context`, the results do degrade, but not catastrophically in this prototype:

- `hybrid` shows a materially worse p95, much lower sequentiality, and `434` DRAM evictions
- `stream_to_scratchpad` remains somewhat better, but now shows a non-zero p99 tail, `332` synchronous flash failures, and `436` DRAM evictions
- both optimized modes now show meaningful speculative waste in the `0.57` range

For `cold_fanout`, the architecture enters a much harsher regime:

- `hybrid` loses most of its advantage and falls back to `962` synchronous flash policy failures
- `stream_to_scratchpad` is no longer close to perfect and still suffers `939` synchronous flash policy failures
- sequential-read ratio collapses to roughly `0.34` to `0.35`
- both optimized modes incur roughly `440` DRAM evictions
- latency rises close to the `ram_emulation` baseline because multi-block cold demand overwhelms the current locality model

That is the most important result in the current prototype because it shows a regime where deterministic staging assumptions break down instead of always looking strong.

The exact numbers matter less than the pattern:

- compatibility mode remains the worst baseline
- hybrid mode improves structured traces but preserves warmup and fallback tails
- stream-to-scratchpad looks strongest on structured traces
- adversarial traces now show a meaningful boundary where low locality overwhelms the current prefetch model

---

## Why This Matters

This is exactly the kind of directional result the repo needs:

- it is consistent with the deterministic streaming thesis
- it distinguishes compatibility mode from optimized mode
- it provides both a success case and two stress cases
- it shows a near-failure regime instead of only happy-path wins
- it exposes that prefetch quality and prefetch quantity are different things
- it exposes DRAM staging capacity as a first-order system constraint
- it gives a concrete baseline for future simulator work

---

## What This Does Not Prove

This prototype does not prove:

- real hardware performance
- universal workload coverage
- full-weight decode streaming viability
- robust behavior under high-entropy MoE or real production traces
- that the current prefetch-accuracy metric captures every form of wasted speculative work
- that the current useful-prefetch window is the right threshold for all workloads
- that the current DRAM capacity and eviction model is sufficient for production-quality conclusions

It is an early evidence loop, not a production benchmark.

---

## Reuse

This prototype is still useful because it demonstrates:

- the repo has moved from static docs to executable comparison
- the interface-mode distinction is now testable
- future work can plug in more realistic traces, policies, and latency models
- the project can now report both wins and failure boundaries
- benchmark artifacts are exported in reusable CSV and JSON formats

That makes the project more credible for technical collaborators, design partners, and serious commercialization conversations.
