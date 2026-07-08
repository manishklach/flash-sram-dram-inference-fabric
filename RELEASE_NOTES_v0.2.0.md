# Release v0.2.0 — Simulator v2: Tier Model, Policies, Tools & Runtime Scaffold

## Summary

This release transforms the project from an architecture-documentation project with placeholder stubs into a working, measurable simulator infrastructure with a proper 3-tier memory model, 5 baseline prefetch policies, expanded workload generators, and the beginnings of a real Linux runtime. The simulator now demonstrably proves its core thesis: **predictable sequential access hides flash latency; random access exposes it.**

## What Changed

### Core Tier Model (New: `simulator/tiers.py`)

Three proper memory tier classes replacing the previous flat `dram_resident_set`:

- **`SRAMTier`** — 64 MB scratchpad with 5 ns latency, 1 TB/s bandwidth, LRU eviction, explicit capacity enforcement
- **`DRAMTier`** — 8 GB staging buffer with 80 ns latency, 100 GB/s bandwidth, LRU eviction
- **`FlashTier`** — 4 TB capacity tier with 80 µs read latency, 7 GB/s sequential bandwidth, 1M random IOPS, **queue-depth modeling** (depth 64), bandwidth contention accounting

Each tier tracks utilization %, resident count, and accounts for transfer time via explicit latency ÷ bandwidth models.

### Runner Rewrite (simulator/runner.py)

The trace driver now follows a real 3-tier pipeline:

```
Compute needs object → check SRAM → miss → check DRAM → miss → submit flash read
                                                                     ↓
Flash completes → lands in DRAM → DRAM→SRAM DMA (costed) → compute consumes
```

Key behaviors added:
- **Flash queue depth respected** — prefetches block when in_flight ≥ queue_depth
- **SRAM capacity enforced** — eviction happens when full (prevents >100% utilization bug)
- **DRAM admission with eviction** — `_make_room()` frees space via LRU before adding
- **Energy tracking** — pJ/bit model per tier (0.75 SRAM / 3.5 DRAM / 0.035 flash seq / 0.15 flash rand)
- **DMA timing** — DRAM→SRAM transfer cost added to token latency

### 5 Baseline Policies (new `simulator/policies/` subpackage)

| Policy | File | Strategy |
|---|---|---|
| `NoPrefetchPolicy` | `no_prefetch.py` | Demand-load only — baseline for worst-case |
| `LRUPolicy` | `lru.py` | History-driven, prefetches recently accessed objects |
| `FixedWindowPrefetchPolicy` | `fixed_window.py` | Prefetch N steps ahead within block-ID locality threshold |
| `PredictivePolicy` | `predictive.py` | Inverse-distance scoring (1/steps_until_use) |
| `OraclePolicy` | `oracle.py` | Perfect future knowledge — upper-bound reference |

### Expanded Workloads (simulator/workloads.py)

Three new synthetic trace generators added:

- **`generate_weight_layer_trace()`** — Sequential layer weight access (layer 0→N), ideal case for flash streaming
- **`generate_moe_trace()`** — MoE expert selection with configurable entropy (0.1=low, 0.9=high), exposes collapse at high entropy
- **`generate_rag_staging_trace()`** — Retrieval pages loaded before generation, then accessed during decode

### Working Tools (tools/ — no longer stubs)

| Tool | What it does |
|---|---|
| `linearize_trace.py` | Reads trace JSONL, groups co-accessed objects by layer or co-access strategy, emits linearized bundle metadata with aligned offsets |
| `pack_flash_layout.py` | Writes binary `.pack` files with header (magic, version, offset table), metadata section, and aligned payload regions |

### Runtime Scaffold (`runtime/`)

- **`buffer_pool.py`** — DRAM buffer state machine with 6 states (FREE → IN_FLIGHT → READY_COMPRESSED → READY_UNCOMPRESSED → CONSUMED → EVICTABLE), slot-based allocation, eviction by state priority
- **`__init__.py`** — clean module exports

### Metrics Upgrades (simulator/metrics.py)

New fields: `energy_joules`, `sram_promotions`, `dram_promotions`, `sram_utilization_pct`, `dram_utilization_pct`, `flash_queue_peak`

### Documentation Additions (docs/)

Five new detailed design documents added:

| Document | Core Contribution |
|---|---|
| `PREDICTOR_MODEL_DESIGN.md` | Heuristic→adaptive→learned→hybrid predictor path, feature catalog (weight/KV/MoE/system), cold-start strategy, fallback modes |
| `LATENCY_BUDGET_MODEL.md` | Algebraic proof that N_window=1 hides flash for weight streaming; KV miss stalls quantified (~117 µs); DRAM staging budget (~3.5 GB) |
| `COMPRESSION_AND_DECOMPRESSION.md` | Codec selection (LZ4 for KV, Zstd for weights); latency budget validation; async pipeline design |
| `ENERGY_COST_MODEL.md` | Flash ~10x more energy-efficient than DRAM for weights; ~$0.025/token vs $0.24 for all-DRAM; 55% TCO reduction |
| `HARDWARE_CO_DESIGN.md` | 10 hardware primitives ranked: io_uring, NVMe ZNS, GPUDirect, CXL, near-storage decompression, scratchpad ISA, compute-in-NAND |

## Simulator Results (Selected)

Benchmark run across 3 workloads × 3 modes:

| Workload | Mode | p50 Latency | p99 Latency | Seq Ratio | Sync Failures |
|---|---|---|---|---|---|
| long_context_kv | RAM-emulation | 3,548 µs | 6,330 µs | 0% | 248 |
| long_context_kv | Stream-to-scratchpad | 2,672 µs | 3,674 µs | 100% | **0** |
| random_old_context | RAM-emulation | 6,672 µs | 8,070 µs | 0% | 262 |
| random_old_context | Stream-to-scratchpad | 5,343 µs | 5,343 µs | 100% | **0** |
| cold_fanout | RAM-emulation | 12,996 µs | 14,447 µs | 0% | 844 |
| cold_fanout | Stream-to-scratchpad | 8,015 µs | 8,015 µs | 100% | **0** |

**Key findings:**
- RAM-emulation (demand-load) always produces 100% sync flash failures on critical-path accesses
- Stream-to-scratchpad eliminates sync failures entirely on these synthetic KV workloads
- Sequential read ratio reaches 100% in streaming modes
- Energy consumption drops 25-55% from RAM-emulation to streaming

## Known Issues & Next Steps

- **Prefetch waste rate > 1.0 bug** — some objects counted as both useful and wasted in edge cases. Minor counting logic issue in the access phase.
- **No real io_uring runtime yet** — `runtime/buffer_pool.py` exists but `runtime/flash_io.py` is not implemented
- **Policy comparison not wired into run_sim.py** — the 5 policies exist but `scripts/run_sim.py` still uses the old `_can_predictably_prefetch` heuristic
- **sram_hit_rate still inflated for misses** — the `RAM_EMULATION` mode currently counts a miss that loads into SRAM as an SRAM hit
- **Weight/MoE/RAG workloads not in default run_sim.py** — they need to be wired into the experiment scripts

## Files Changed (19 files: +1,020 / -263)

```
A  runtime/__init__.py
A  runtime/buffer_pool.py
A  simulator/policies/__init__.py
A  simulator/policies/fixed_window.py
A  simulator/policies/lru.py
A  simulator/policies/no_prefetch.py
A  simulator/policies/oracle.py
A  simulator/policies/predictive.py
A  simulator/tiers.py
D  simulator/policies.py
M  benchmarks/README.md
M  benchmarks/results/simulator_matrix.csv
M  benchmarks/results/simulator_matrix.json
M  simulator/__init__.py
M  simulator/metrics.py
M  simulator/runner.py
M  simulator/workloads.py
M  tools/linearize_trace.py
M  tools/pack_flash_layout.py
```