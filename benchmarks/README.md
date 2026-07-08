# Benchmarks

Home for workload traces, evaluation harnesses, metrics definitions, and exported experiment summaries.

## Current runnable experiments

- `scripts/run_sim.py` — single-shot comparison across 3 interface modes
- `scripts/sweep_dram.py` — sweeps DRAM capacity across workloads
- `scripts/sweep_lookahead_dram.py` — 2D sweep of DRAM capacity × lookahead steps

## Metrics tracked (as of simulator v2)

| Metric | Description |
|---|---|
| p50/p95/p99 token latency | Token latency distribution in microseconds |
| flash queue peak/avg | In-flight NVMe read queue depth |
| sram/dram utilization % | Capacity utilization at end of run |
| sram/dram hit rate | Fraction of accesses satisfied at each tier |
| sync flash miss rate | Critical-path flash reads (policy failures) |
| sequential read ratio | Fraction of flash reads that are sequential |
| prefetch accuracy / waste / late | Prefetch quality metrics |
| energy joules | Approximate energy per run (pJ/bit model) |
| sram/dram promotions | Count of upward data movements |

## Artifacts

```
results/simulator_matrix.csv
results/simulator_matrix.json
results/dram_capacity_sweep.csv
results/dram_capacity_sweep.json
results/lookahead_dram_sweep.csv
results/lookahead_dram_sweep.json
results/deployment_economics.csv
results/deployment_economics.json
```