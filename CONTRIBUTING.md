# Contributing

Thanks for considering contributing to the Flash-SRAM-DRAM Inference Fabric.

## Project Status

This is an early-stage research/simulator prototype with no hardware backend yet. Contributions that move the needle from simulation toward real inference are especially valuable.

## How to Contribute

1. Open an issue describing what you'd like to work on.
2. Fork the repo and create a branch from `main`.
3. Make your changes. Keep them focused — one pull request per feature or fix.
4. Run the test suite: `python -m pytest tests/ -v`
5. Run the simulator smoke test: `python -m scripts.run_sim --smoke`
6. Run the deployment model: `python -m scripts.run_deployment_model`
7. Submit a pull request.

## What Needs Help

- **Real NVMe backend** — wire `runtime/flash_io.py` and `runtime/trace_replay.py` against a real Linux NVMe device
- **llama.cpp integration** — test and fix `runtime/llama_bridge.py` end-to-end
- **Weight tile pipelining** — fix the simulator so weight workloads don't overwhelm DRAM capacity
- **More workload generators** — multi-tenant sessions, batch prefill, long-context with sliding window
- **Learned predictor** — graduate from heuristics to a lightweight learned model in `prefetch/`
- **Performance tuning guide** — doc on how to choose DRAM size, lookahead, compression level
- **Any task in the open issues**

## Guidelines

- No stubs or TODO placeholders — every new module must be fully runnable and testable.
- Every new feature should include at least one pytest test.
- Match existing code style (PEP 8, type hints, `from __future__ import annotations`).
- Commit messages should be descriptive of *what* changed and *why*.

## Code of Conduct

Be respectful. This is a research project; disagreement is fine, dismissal is not.