# Simulator

Planned home for a trace-driven simulator covering:

- SRAM scratchpad scheduling
- DRAM staging windows
- flash prefetch timing
- promotion and eviction policies
- trace-guided layout experiments
- RAM-emulation versus stream-to-scratchpad interface modes
- policy failure accounting

Current stubs:

- `interface_modes.py`
- `metrics.py`
- `policies.py`

Runnable prototype:

- `traces.py`
- `workloads.py`
- `runner.py`
- `../scripts/run_sim.py`

Example:

```text
python scripts/run_sim.py
```
