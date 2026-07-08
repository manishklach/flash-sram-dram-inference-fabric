# Lookahead and DRAM Sweep Results

## Purpose

This document summarizes the joint sweep over:

- DRAM staging capacity
- lookahead horizon

The key question is:

> When does more lookahead help, and when does it just create more speculative pressure on a too-small DRAM staging tier?

---

## Command

```text
python scripts/sweep_lookahead_dram.py
```

Artifacts:

```text
benchmarks/results/lookahead_dram_sweep.csv
benchmarks/results/lookahead_dram_sweep.json
```

---

## Parameters

DRAM capacities:

```text
32 MB
64 MB
128 MB
256 MB
512 MB
```

Lookahead steps:

```text
4
8
12
16
24
```

Modes:

- `hybrid`
- `stream_to_scratchpad`

Workloads:

- `long_context_kv`
- `random_old_context`
- `cold_fanout`

---

## Observed Design Insight

This sweep answers three design questions directly:

1. Does larger lookahead always help?
2. At what point does larger lookahead just create more staging pressure and waste?
3. How much DRAM is needed before additional predictor horizon starts paying off?

Short answer:

- no, larger lookahead does not always help
- small DRAM tiers can be hurt badly by aggressive lookahead
- extra lookahead becomes useful only after staging capacity is deep enough to hold the prefetched set

---

## Key Findings

## 1. Long-Context KV Has An Early Plateau

For `long_context_kv`:

- `4` to `8` lookahead steps already capture most of the benefit
- at `32 MB`, pushing lookahead from `4` to `12` raises hybrid `p95` from `3439 us` to `3838 us`
- at `128 MB`, hybrid `p95` already drops to `2750 us` with only `4` lookahead steps
- beyond `8` steps, extra lookahead mostly adds waste rather than lower latency
- by `256 MB`, DRAM evictions disappear on this trace and further lookahead changes little

This suggests that structured workloads need enough DRAM first; after that, more horizon quickly hits diminishing returns.

---

## 2. Random Old-Context Needs Both More DRAM and More Lookahead

For `random_old_context`:

- low DRAM and low lookahead are both bad
- low DRAM plus high lookahead can also be bad because it creates extra staging churn
- the best region in this prototype appears at `512 MB` and `16` to `24` lookahead steps
- at `32 MB`, hybrid `p95` improves from `6758 us` at `4` steps to `6528 us` at `8` steps, but then wastes heavily at larger horizons
- at `256 MB`, hybrid `p95` falls from `6068 us` at `4` steps to `5149 us` at `12` steps
- at `512 MB`, hybrid `p95` reaches `4230 us` at `16` steps and `stream_to_scratchpad` reaches `4000 us` with only `8` synchronous misses at `24` steps

This is the most important positive interaction in the current sweep:

> Predictor horizon only pays off when the staging tier is deep enough to absorb it.

---

## 3. Cold Fan-Out Is Mostly Capacity- and Locality-Bound

For `cold_fanout`:

- increasing lookahead helps only modestly
- increasing DRAM helps only modestly
- even the best tested settings remain poor relative to structured traces
- hybrid `p95` stays near `9907 us` through much of the sweep and only reaches `9447 us` in the best tested region
- even at `512 MB` and `24` lookahead steps, `stream_to_scratchpad` still records `518` synchronous failures

This is a useful negative result. It shows a workload class where neither horizon nor staging depth is enough by itself because the fundamental locality model is weak.

---

## 4. Over-Lookahead Can Backfire

At small DRAM sizes, larger lookahead can make things worse:

- more prefetched objects compete for limited staging space
- evictions rise
- useful data can be displaced before use
- waste stays high or increases
- for `long_context_kv`, waste jumps to about `0.968` once the horizon reaches `12` steps
- for `random_old_context`, waste rises from `0.000` at short horizons to about `0.570` at `12` steps and about `0.962` by `16` to `24` steps

That means predictor horizon is not free. It must be co-designed with staging capacity.

---

## 5. Break-Even Interaction

The strongest architecture-sizing conclusion from this sweep is:

- `long_context_kv`: modest DRAM plus modest lookahead is enough
- `random_old_context`: deep DRAM plus longer lookahead is required
- `cold_fanout`: neither parameter alone produces a healthy regime in the tested range

In this prototype, the most efficient operating regions look like:

- `long_context_kv`: `128 MB` to `256 MB` DRAM with `4` to `8` lookahead steps
- `random_old_context`: `256 MB` to `512 MB` DRAM with `12` to `24` lookahead steps
- `cold_fanout`: no clearly healthy operating point in the tested envelope

This is exactly the kind of systems insight that turns the repo from a concept into a design-space exploration tool.

---

## Why This Matters

This sweep matters because the product problem is not just "how much DRAM?" or "how much lookahead?"

The real question is the interaction:

- predictor horizon without enough DRAM can cause staging thrash
- DRAM without enough predictor horizon leaves flash latency exposed

That interaction is central to any real hardware-software co-design story.
