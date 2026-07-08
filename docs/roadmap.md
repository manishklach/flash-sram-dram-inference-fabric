# Roadmap

## Phase 1: Simulator

Build a trace-driven simulator for SRAM, DRAM, and flash promotion/eviction behavior.

## Phase 2: Predictor

Prototype heuristics and learned predictors for next-use estimation.

## Phase 3: Residency engine

Implement temperature tracking and tier placement policies for KV, weights, and experts.

## Phase 4: Compiler hints

Define annotations for tensor placement, prefetch windows, and dependency-aware staging.

## Phase 5: Runtime

Develop a Linux userspace or kernel-adjacent runtime capable of asynchronous movement and scheduling.

## Phase 6: Evaluation

Benchmark cost, latency, miss rates, and quality-of-service behavior under realistic traces.
