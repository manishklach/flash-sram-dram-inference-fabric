# Repository Structure

## Recommended Repository Name

```text
flash-sram-dram-inference-fabric
```

## Short Description

A research architecture and simulator for low-cost AI inference using a predictive SRAM, DRAM/LPDDR, and SSD flash memory fabric.

---

## Full Structure

```text
flash-sram-dram-inference-fabric/
  README.md
  LICENSE
  pyproject.toml
  requirements.txt
  .gitignore

  docs/
    ARCHITECTURE.md
    RUNTIME.md
    COMPILER.md
    ROADMAP.md
    BENCHMARKS.md
    PATENT_IDEAS.md
    THREATS_AND_LIMITATIONS.md
    SIMULATOR_DESIGN.md
    DATA_FORMATS.md
    FLASH_LAYOUT.md
    KV_CACHE_TIERING.md
    MOE_EXPERT_TIERING.md
    LINUX_IO_RUNTIME.md
    DIAGRAMS.md
    REPO_STRUCTURE.md
    CODEX_PROMPT.md

  simulator/
    config.py
    objects.py
    tiers.py
    traces.py
    metrics.py
    runner.py
    workloads/
    policies/

  runtime/
    flash_io.md
    residency_manager.md
    prefetcher.md

  compiler/
    metadata_schema.md
    pack_format.md

  tools/
    pack_model.py
    inspect_pack.py
    repack_profile.py
    generate_trace.py

  scripts/
    run_sim.py
    sweep_dram.py
    sweep_prefetch.py
    plot_results.py

  examples/
    configs/
    traces/

  tests/
    test_tiers.py
    test_policies.py
    test_traces.py
    test_metrics.py
```

---

## GitHub About

Description:

```text
Predictive SRAM–DRAM–SSD flash memory fabric for low-cost AI inference, long-context KV cache tiering, and MoE expert staging.
```

Topics:

```text
ai-inference
llm-inference
memory-hierarchy
sram
dram
lpddr
ssd
nvme
flash-storage
kv-cache
moe
long-context
prefetching
compiler-runtime
systems-research
edge-ai
```

---

## Initial Commit Plan

```text
docs: add architecture and research docs
simulator: add memory tier simulator scaffold
workloads: add layer, KV, and MoE trace generators
policies: add no-prefetch, LRU, fixed-window, predictive, and oracle policies
benchmarks: add configs, scripts, and plotting
```
