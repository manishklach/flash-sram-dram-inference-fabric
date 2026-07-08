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
workload,mode,p50_us,p95_us,p99_us,seq_ratio,random_reads,seq_reads,sync_failures,prefetch_accuracy
long_context_kv,ram_emulation,3838.4,3838.4,3838.4,0.000,512,0,512,0.000
long_context_kv,hybrid,2000.0,2195.3,3838.4,0.908,25,248,25,1.000
long_context_kv,stream_to_scratchpad,2000.0,2000.0,2000.0,1.000,0,248,0,1.000
random_old_context,ram_emulation,3838.4,3838.4,3838.4,0.000,512,0,512,0.000
random_old_context,hybrid,2000.0,3011.1,3838.4,0.926,35,441,35,1.000
random_old_context,stream_to_scratchpad,2000.0,2000.0,2425.1,0.989,5,449,5,1.000
cold_fanout,ram_emulation,3838.4,3838.4,3838.4,0.000,512,0,512,0.000
cold_fanout,hybrid,3608.6,3803.9,3838.4,0.131,444,67,444,1.000
cold_fanout,stream_to_scratchpad,3608.6,3608.6,3693.6,0.152,417,75,417,1.000
```

---

## Interpretation

For `long_context_kv`, the optimized streaming modes dominate because the access pattern is structured enough to benefit from lookahead and reuse.

For `random_old_context`, the results do degrade, but not catastrophically in this prototype:

- `hybrid` shows a materially worse p95 and more policy failures than on the structured trace
- `stream_to_scratchpad` remains strong, but now shows a non-zero p99 tail and non-zero policy failures instead of a perfect result

For `cold_fanout`, the architecture enters a much harsher regime:

- `hybrid` loses most of its advantage and falls back to `444` synchronous flash policy failures
- `stream_to_scratchpad` is no longer close to perfect and still suffers `417` synchronous flash policy failures
- sequential-read ratio collapses from near-ideal values to roughly `0.13` to `0.15`

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
- it gives a concrete baseline for future simulator work

---

## What This Does Not Prove

This prototype does not prove:

- real hardware performance
- universal workload coverage
- full-weight decode streaming viability
- robust behavior under high-entropy MoE or real production traces
- that the current prefetch-accuracy metric captures every form of wasted speculative work

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
