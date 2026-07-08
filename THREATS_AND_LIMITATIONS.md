# Threats and Limitations

## 1. Core Reality

SSD flash is not SRAM.

SSD flash is not DRAM.

This project does not claim otherwise.

```text
SRAM << DRAM << NVMe SSD flash
```

The project only works when flash can be moved off the critical path.

---

## 2. Main Limitation

If the model requires unpredictable data from flash during token decode, latency will collapse.

```text
compute reaches object
object is not in SRAM
object is not in DRAM
runtime must synchronously read SSD
token waits
```

That event is treated as a policy failure, not a normal cache miss.

---

## 3. Scope Limitation

This architecture is mainly for inference, not training.

Training is harder because:

- writes are frequent
- flash endurance becomes a major issue
- activations are larger and more dynamic
- optimizer state is harder to tier predictively

Inference is the primary target. Training likely needs DRAM-heavy or specialized approaches.

---

## 4. Workloads That May Work Well

- predictable layer streaming
- long-context with local or sparse attention
- old KV rarely accessed
- MoE with predictable expert routing
- RAG where retrieval happens before generation
- inactive session spill and resume
- batch prefill with enough lookahead
- edge systems with relaxed latency

---

## 5. Workloads That May Perform Poorly

- random access to old context
- fully random attention over old context
- high-entropy MoE routing
- very small batch with no lookahead
- workloads with frequent branch rollback
- models requiring full-context dense attention every token
- workloads with little compute to hide IO
- highly fragmented flash layouts
- multi-tenant workloads with all sessions active

---

## 6. RAM-Emulation Risk

RAM-emulation mode may be easy to adopt but dangerously slow.

Problems:

- performance cliff on random access
- fragile tail latency
- cache hierarchy may hide bad behavior until p99 explodes

This mode is useful for compatibility and bring-up, not as proof that the architecture is performant.

---

## 7. Stream-to-Scratchpad Cost

Stream-to-scratchpad mode requires significant software changes.

Costs:

- runtime redesign
- compiler metadata
- explicit transfer scheduling
- tile deadline management
- scratchpad programming model

This is the higher-performance path, but also the harder engineering path.

---

## 8. SRAM and Linearization Limits

If SRAM is too small and data cannot be linearized effectively, performance may degrade.

Symptoms:

- repeated DRAM-to-SRAM transfers
- compute stalls
- poor tile reuse
- random flash fallback

Mitigations:

- better tile schedule
- larger DRAM staging window
- redundant sequential placement
- revised layout groups

---

## 9. Trace-Guided Overfitting Risk

If trace-guided layout overfits one workload, generalization may suffer.

Problems:

- one trace may not represent all prompts
- expert routing may shift
- attention patterns may change
- different tenants may disrupt the layout assumptions

Mitigations:

- use workload families, not single traces
- maintain hybrid fallback modes
- compare trace-guided versus generic layouts across workloads

---

## 10. Summary

The architecture is powerful but conditional.

It works only if:

```text
flash latency is hidden
prediction is accurate enough
dram is large enough
sram is explicitly managed
io is mostly sequential
tail latency is controlled
```

The repo should stay honest about these limits because the strongest claim here is not that flash behaves like RAM. It is that deterministic inference access may be predictable enough to make flash useful as a hidden capacity tier.
