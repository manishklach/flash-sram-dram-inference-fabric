# Threats and Limitations

## 1. Core Reality

SSD flash is not SRAM.

SSD flash is not DRAM.

This project does not claim otherwise.

Raw latency hierarchy:

```text
SRAM  <<  DRAM  <<  NVMe SSD flash
```

The project only works when flash can be moved off the critical path.

---

## 2. Main Limitation

If the model requires unpredictable data from flash during token decode, latency will collapse.

Bad case:

```text
compute reaches object
object is not in SRAM
object is not in DRAM
runtime must synchronously read SSD
token waits
```

This is the main failure mode.

---

## 3. Workloads That May Work Well

- predictable layer streaming
- long-context with local/sparse attention
- old KV rarely accessed
- MoE with predictable expert routing
- RAG where retrieval happens before generation
- inactive session spill/resume
- batch prefill with enough lookahead
- edge systems with relaxed latency

---

## 4. Workloads That May Perform Poorly

- random access to old context
- high-entropy MoE routing
- very small batch with no lookahead
- workloads with frequent branch rollback
- models requiring full-context dense attention every token
- workloads with little compute to hide IO
- highly fragmented flash layouts
- multi-tenant workloads with all sessions active

---

## 5. Tail Latency Risk

Even if average performance looks good, p99 can be bad.

Possible causes:

- late flash completion
- SSD queue congestion
- thermal throttling
- decompression delay
- DRAM eviction mistake
- predictor miss
- OS scheduler noise
- filesystem fragmentation

Mitigation:

- large prefetch window
- direct IO
- pinned buffers
- sequential layout
- latency-aware eviction
- urgent IO class
- per-session DRAM reserve
- thermal-aware prefetch reduction

---

## 6. DRAM Pressure

If DRAM is too small, it cannot absorb flash latency.

Symptoms:

- prefetched pages evicted before use
- high eviction churn
- repeated flash reads
- low prefetch accuracy
- high p99 latency

Mitigation:

- better placement
- compression
- smaller prefetch window
- larger DRAM
- per-session budgets
- workload admission control

---

## 7. SRAM Thrashing

SRAM is tiny.

If too many hot objects compete, SRAM thrashes.

Symptoms:

- repeated DRAM-to-SRAM transfers
- compute stalls
- micro-kernel inefficiency
- poor tile reuse

Mitigation:

- compiler tile scheduling
- deterministic SRAM allocation
- pin only current tiles
- avoid generic cache behavior
- evict immediately after use

---

## 8. Flash Random IO Problem

SSD performs best with large sequential reads.

Bad pattern:

```text
4KB random read
4KB random read
4KB random read
...
```

Good pattern:

```text
4MB sequential read
8MB sequential read
16MB sequential read
```

Mitigation:

- flash-aware tensor layout
- prefetch bundles
- profile-guided repacking
- group co-accessed objects
- align compression blocks

---

## 9. Compression Tradeoffs

Compression saves capacity but adds latency.

Bad case:

```text
data arrives from flash
decompression not complete
compute waits
```

Mitigation:

- decompress ahead of time
- do not compress near-hot data
- choose fast codecs
- track decompression cost in policy
- reserve decompression workers

---

## 10. SSD Endurance

KV spill may create writes.

Frequent writes can harm SSD endurance.

Mitigation:

- append-only KV logs
- write batching
- compression
- avoid spilling frequently updated hot state
- spill only cold stable data
- endurance-aware policies

---

## 11. Thermal Throttling

Sustained SSD reads can throttle.

Mitigation:

- monitor device temperature
- reduce speculative prefetch
- increase DRAM reuse
- distribute across drives
- avoid unnecessary prefetch waste

---

## 12. Operating System Noise

Linux IO scheduling, page cache, filesystem behavior, and CPU scheduling can add jitter.

Mitigation:

- io_uring
- O_DIRECT
- fixed buffers
- CPU affinity
- huge pages
- isolated cores
- preallocated files
- direct device testing

---

## 13. Prediction Error

The architecture depends heavily on prediction.

Prediction can fail because:

- attention shifts unexpectedly
- user asks about old context
- MoE routing changes
- retrieval result is surprising
- speculative decoding branch fails
- batch composition changes

Mitigation:

- adaptive feedback
- larger DRAM window
- fallback policies
- priority-based urgent fetch
- predictor retraining
- profile-guided layout

---

## 14. Multi-Tenant Interference

Many sessions may compete for flash and DRAM.

Problems:

- noisy neighbor flash queue
- DRAM pollution
- hot-session eviction
- p99 spikes

Mitigation:

- per-session quotas
- priority scheduling
- admission control
- idle-session demotion
- latency-class-aware policies

---

## 15. Hardware Variability

Consumer SSDs and enterprise SSDs behave very differently.

Factors:

- queue depth
- sustained bandwidth
- random-read latency
- thermal limits
- controller cache
- NAND type
- PCIe generation

Benchmarks must report exact device details.

---

## 16. What This Architecture Cannot Promise

It cannot promise:

- raw SSD latency equal to DRAM
- universal HBM-class performance
- zero miss penalty
- no DRAM requirement
- no workload-specific tuning
- no tail-latency risk

---

## 17. Honest Best-Case Use

The best case is:

```text
predictable future access
enough compute time to hide IO
large sequential flash reads
sufficient DRAM staging
small hot SRAM set
```

---

## 18. Honest Worst-Case Use

The worst case is:

```text
random unpredictable access
small DRAM
high concurrency
flash thermal throttling
dense old-context attention
```

---

## 19. Security and Isolation

If multiple tenants share flash-backed memory:

Risks:

- data leakage through shared pages
- timing side channels
- stale KV cache exposure
- improper session restore

Mitigation:

- per-tenant encryption
- page ownership tracking
- secure zeroing
- access control
- encrypted flash objects
- isolation-aware scheduler

---

## 20. Summary

The architecture is powerful but conditional.

It works only if:

```text
flash latency is hidden
prediction is accurate enough
DRAM is large enough
SRAM is deterministic
IO is mostly sequential
tail latency is controlled
```

This limitations document should remain part of the repo because honest constraints make the project more credible.
