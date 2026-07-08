# Deployment Economics Results

## Purpose

This document converts the simulator's measured operating regions into product decisions.

The question is not just "can the memory fabric work?"

The business question is:

> Which workload classes support a lower-cost appliance with acceptable tail latency, and which ones still need premium-memory baselines?

The results in this document come from the measured `lookahead_dram_sweep` artifact plus an explicit appliance BOM and dynamic memory-energy model.

---

## Command

```text
python scripts/run_deployment_model.py
```

Artifacts:

```text
benchmarks/results/deployment_economics.csv
benchmarks/results/deployment_economics.json
```

---

## Modeling Notes

The deployment model does three things:

1. Selects only rows from the measured lookahead/DRAM sweep that satisfy scenario-specific service limits.
2. Attaches explicit appliance assumptions for host cost, accelerator cost, DRAM, and NVMe capacity.
3. Estimates dynamic memory-energy cost per million tokens using the sequential-read ratio and synchronous miss rate from the simulator.

This is not full datacenter TCO. It is a product-screening model.

Important limits:

- energy here is dynamic inference-memory energy, not total server power
- BOM assumptions are explicit but approximate
- workload viability still depends on real customer traces

---

## Scenarios Evaluated

- `enterprise_rag_long_context`
- `persistent_assistant_sessions`
- `cold_fanout_retrieval`

---

## Key Findings

## 1. Enterprise Long-Context RAG Is The Best First Wedge

Best selected configuration:

- workload: `long_context_kv`
- mode: `stream_to_scratchpad`
- DRAM staging: `128 MB`
- lookahead: `8` steps
- `p95`: `2750 us`
- sequential read ratio: `1.000`
- sync miss rate: `0.000`

Economic implication:

- fabric capex: `~$9,428`
- premium-memory baseline capex: `~$18,500`
- 3-year TCO savings: `~49.1%`

This is the cleanest current product story in the repo.

The system stays inside the latency target while preserving a nearly ideal flash access pattern. That makes the long-context private appliance the strongest v1 business wedge.

---

## 2. Persistent Assistant Sessions Look Viable, But More Fragile

Best selected configuration:

- workload: `random_old_context`
- mode: `stream_to_scratchpad`
- DRAM staging: `512 MB`
- lookahead: `16` steps
- `p95`: `4000 us`
- `p99`: `4680 us`
- sequential read ratio: `0.984`
- sync miss rate: `0.0083`
- prefetch waste rate: `0.968`

Economic implication:

- fabric capex: `~$11,932`
- premium-memory baseline capex: `~$19,500`
- 3-year TCO savings: `~38.8%`

This is an encouraging second wedge, but not as robust as long-context RAG.

The fabric can support the scenario only when both predictor horizon and DRAM depth are pushed upward. The very high waste rate means the current policy is commercially plausible but operationally inefficient. This belongs in the roadmap, not the first proof point.

---

## 3. Cold Fan-Out Is Not A Product Wedge Yet

For `cold_fanout`, the model found no configuration that satisfied the service thresholds.

That is a valuable negative result.

It means the repo should not currently position the product as a general-purpose answer for weak-locality retrieval or adversarial cold fan-out traces. In those cases, the premium-memory baseline remains the recommended deployment.

---

## Product Decision

If the goal is to build a real company from this repo, the current data says:

1. Lead with a private long-context RAG appliance.
2. Keep persistent assistant session tiering as a second product track once residency waste is reduced.
3. Explicitly avoid claiming broad support for cold fan-out or weak-locality workloads.

---

## Why This Matters

This artifact changes the repo from:

- "here is a memory architecture idea"

to:

- "here is the workload class where the idea already looks commercially credible"

That is the right direction for turning a research thesis into a defensible product wedge.
