# Flash-SRAM-DRAM Inference Fabric

<p>
  <img src="https://img.shields.io/badge/status-simulator/research--prototype-yellow" alt="Status">
  <img src="https://img.shields.io/github/actions/workflow/status/manishklach/flash-sram-dram-inference-fabric/ci.yml?branch=main&label=tests" alt="CI">
  <img src="https://img.shields.io/github/license/manishklach/flash-sram-dram-inference-fabric" alt="License">
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12-blue" alt="Python">
  <img src="https://img.shields.io/github/v/tag/manishklach/flash-sram-dram-inference-fabric" alt="Version">
</p>

> Flash is capacity. DRAM is prediction. SRAM is latency. A synchronous flash read during token generation is treated as a **policy failure**, not a cache miss.

**[View the project site](https://manishklach.github.io/flash-sram-dram-inference-fabric/)**

---

## Quickstart

```bash
git clone https://github.com/manishklach/flash-sram-dram-inference-fabric.git
cd flash-sram-dram-inference-fabric

# Run the full simulator matrix (105 configurations):
python -m scripts.run_sim

# Run all tests:
python -m pytest tests/ -v
```

Sample output from `python -m scripts.run_sim`:

```
workload,mode,policy,p50_us,p95_us,p99_us,seq_ratio,sync_failures,prefetch_accuracy,prefetch_waste_rate,energy_joules
long_context_kv,stream_to_scratchpad,fixed_window,2671.7,2821.4,3673.6,1.000,0,0.032,0.968,0.009340
cold_fanout,hybrid,fixed_window,8015.2,8015.2,8015.2,1.000,0,0.984,0.024,0.042928
rag,hybrid,fixed_window,3671.7,4247.7,6238.0,0.845,42,0.031,0.969,0.010497
```

---

## Headline Results

The simulator runs **7 workloads × 3 interface modes × 5 prefetch policies** (105 configs). Key findings:

### Stream-to-scratchpad eliminates synchronous flash failures

| Workload | RAM-emulation failures | Stream-to-scratchpad failures | Latency change |
|---|---|---|---|
| long_context_kv | 248 | **0** | -25% p50 |
| random_old_context | 262 | **0** | -20% p50 |
| cold_fanout | 844 | **0** | -38% p50 |
| weight_layer | 16,384 | **0** | — (see below) |

### 5-policy comparison on hybrid mode

| Policy | long_context_kv p50 | random_old p50 | cold_fanout p50 | cold_fanout accuracy |
|---|---|---|---|---|
| NoPrefetch | 2,672 µs | 5,343 µs | 8,015 µs | — |
| LRU | 2,672 µs | 5,343 µs | 8,015 µs | 0.000 |
| FixedWindow | 2,672 µs | 5,343 µs | 8,015 µs | **0.984** |
| Predictive | 2,672 µs | 5,343 µs | 8,015 µs | 0.001 |
| Oracle | 2,672 µs | 5,343 µs | 8,015 µs | 0.001 |

### Deployment economics

| Scenario | Viable | Fabric capex | Baseline capex | TCO savings (3yr) |
|---|---|---|---|---|
| Enterprise RAG | Yes | $9,428 | $18,500 | **49.1%** |
| Persistent assistant | Yes | $11,932 | $19,500 | **38.8%** |
| Cold fan-out retrieval | **No** | — | — | — |

---

## Core Thesis

Model inference has highly predictable access patterns — transformer layers execute in order, weights can be linearized, KV cache has temperature and locality, MoE expert routing is often predictable. This means low-cost NVMe flash can act as a **hidden sequential streaming tier**, with DRAM as the predictive staging buffer and SRAM as the deterministic hot path.

The goal is **not** to make flash behave like DRAM. The goal is to avoid putting flash on the synchronous token path entirely.

```
Visible latency = max(compute time, SRAM/DRAM service time)
Not:             compute time + SSD read latency
```

![Memory hierarchy](diagrams/highlevel_memory_hierarchy.svg)

![Critical vs hidden path](diagrams/critical_path_vs_hidden_path.svg)

---

## What Makes This Different

| Approach | How flash is used | Failure mode |
|---|---|---|
| **Generic virtual memory / SSD swap** | Demand-page random access | Page fault adds 80+ µs to token path |
| **SSD cache (vLLM-style)** | Write-back cache with eviction | Cache miss adds random read latency |
| **FlexGen / AirLLM** | Offload to CPU DRAM + SSD | CPU→SSD→CPU round trip on every offload |
| **This project** | Sequential streaming into DRAM before compute needs it | **Policy failure, not cache miss** — synchronous SSD during decode is a design bug |

---

## Related Work

This project draws from and differs from prior work:

- **vLLM / PagedAttention** (Kwon et al., 2023): Uses OS-style paging for KV cache, but keeps everything in GPU HBM. This project targets systems where GPU HBM is uneconomical and uses flash as a capacity tier with explicit residency management.
- **FlexGen** (Sheng et al., 2023): Offloads KV cache to CPU DRAM + SSD with a cost model for optimal placement. FlexGen treats SSD as a swapping tier with random access; this project insists on transforming SSD access into sequential streaming before compute needs data.
- **DeepSpeed-ZeRO-Infinity** (Rajbhandari et al., 2021): Offloads model states to CPU/NVMe during training. Addresses a different phase (training vs. inference) but shares the insight that NVMe bandwidth can be leveraged at scale.
- **AirLLM** (Ding et al., 2024): Offloads individual transformer layers to CPU DRAM for single-GPU inference. This project extends the same principle to a continuous streaming pipeline across SRAM, DRAM, and flash with explicit prefetch scheduling.
- **InfiniGen** (Lee et al., 2024): Predicts future KV cache needs for long-context inference. Complements this project — their predictor could drive this project's prefetch engine.

---

## Architecture

### Three-tier memory hierarchy

| Tier | Role | Typical capacity | Latency | Bandwidth |
|---|---|---|---|---|
| **SRAM** | Deterministic scratchpad, hot tiles, active KV | 64 MB | 5 ns | 1 TB/s |
| **DRAM / LPDDR** | Predictive staging buffer, warm KV, decompression | 8-512 GB | 80 ns | 100 GB/s |
| **NVMe Flash** | Sequential capacity tier, cold KV, model bundles | 2-4 TB | 80 µs | 7 GB/s (seq) |

### Example decode pipeline

```
Token T, layer 12 is computing:
  SRAM:   serves active layer-12 tiles
  DRAM:   holds layers 13-16 and hot KV blocks
  Flash:  streams layers 17-32 and cold KV bundles into DRAM
```

## Repository Structure

```
  simulator/        # 3-tier simulator: tiers, runner, metrics, 5 policies, 7 workloads
  runtime/             — buffer_pool, flash_io, trace_replay, llama_bridge
  scripts/          — run_sim, sweep_dram, sweep_lookahead, run_deployment_model
  tools/            — linearize_trace, pack_flash_layout, analyze_read_pattern
  tests/             — 63 pytest tests across all modules
  docs/             — 26 design documents (thesis, trace layout, KV tiering, MoE, etc.)
  diagrams/         — 6 SVG exports of system architecture diagrams
```

---

## Repository Contents

- **`simulator/`** — 3-tier SRAM/DRAM/Flash memory model with 5 prefetch policies (NoPrefetch, LRU, FixedWindow, Predictive, Oracle), 7 synthetic workload generators (KV, weight, MoE, RAG), 3 interface modes (RAM-emulation, hybrid, stream-to-scratchpad), and a StreamingMetrics engine tracking 20+ metrics including energy consumption.
- **`runtime/`** — DRAM buffer state machine, async flash reader (io_uring-style), trace-driven NVMe replayer, and a ctypes bridge to llama.cpp.
- **`scripts/`** — Runner scripts for the simulator matrix, DRAM capacity sweep, combined lookahead+DRAM sweep, and deployment economics model.
- **`tools/`** — Trace linearizer (groups co-accessed objects into bundled layouts), flash packer (writes binary `.pack` files), and read pattern analyzer (reports sequential ratios, sync failures, energy by workload).
- **`tests/`** — 63 passing pytest tests covering tiers, metrics, workloads, runner, buffer pool, flash IO, and tools.
- **`docs/`** — 26 design documents covering the core thesis, trace-guided linearization, scratchpad ring buffer, flash interface modes, simulator design, flash layout, KV cache tiering, MoE expert tiering, Linux IO runtime, data formats, compression, latency budget model, predictor model design, energy cost model, hardware co-design, and commercialization.

---

## Non-Goals

This project does not claim:
- SSD raw latency equals DRAM latency
- SSD should be accessed randomly during decode
- All model weights can be fetched from flash per token
- Every workload can reach HBM-class performance
- Training is solved
- Prediction misses are free

---

## Project Status

**Current phase:** Simulator/research prototype — no hardware backend yet. The simulator is runnable and produces measured results. The runtime modules (`flash_io.py`, `trace_replay.py`, `llama_bridge.py`) are implemented and testable with temp files but lack real NVMe device validation on Linux.

### Build / test signal

| Signal | Status |
|---|---|
| Tests (63) | Passing |
| Simulator (105 configs) | Runs clean |
| Deployment model | Runs clean |
| Real NVMe backend | Not yet validated |
| llama.cpp integration | Implemented, not tested end-to-end |

### What's next

- Fix weight tile pipeline (SRAM weight pipelining to avoid DRAM overflow)
- Wire `runtime/flash_io.py` against real Linux NVMe device
- Graduate predictor from heuristics to learned model
- Multi-tenant scheduling in simulator

---

## Commercialization Path

The strongest first product is a low-cost inference appliance for enterprise long-context RAG — the scenario where the deployment model shows a clear 49% TCO advantage. See `docs/DEPLOYMENT_ECONOMICS_RESULTS.md` and `docs/COMMERCIALIZATION_STRATEGY.md` for details.

## Big Vision

A software-defined memory operating system for AI inference that continuously moves tensors, KV blocks, experts, and retrieval state across SRAM, DRAM, and flash based on predicted future use and explicit deadlines.

---

## License

MIT. See [LICENSE](LICENSE).