# Runtime Design

## 1. Purpose

The runtime is the core of the Flash-SRAM-DRAM Inference Fabric.

Its job is to make sure the compute engine receives data from SRAM or DRAM, while flash IO happens early enough to be invisible.

The runtime is responsible for:

- residency tracking
- prefetch scheduling
- flash IO orchestration
- SRAM promotion
- DRAM staging
- eviction
- compression/decompression coordination
- multi-tenant fairness
- latency-budget enforcement
- deadline tracking
- trace replay

---

## 2. Runtime Components

```text
+---------------------------------------------------------------+
|                         Runtime                               |
|                                                               |
| +---------------+  +----------------+  +-------------------+ |
| | Token Driver  |  | Residency Mgr  |  | Prefetch Planner  | |
| +-------+-------+  +--------+-------+  +---------+---------+ |
|         |                   |                     |           |
| +-------v--------+  +-------v--------+  +---------v---------+ |
| | SRAM Manager   |  | DRAM Manager   |  | Flash IO Engine   | |
| +-------+--------+  +-------+--------+  +---------+---------+ |
|         |                   |                     |           |
| +-------v-----------------------------------------v---------+ |
| |              Metrics + Policy Engine + Trace Replay       | |
| +-----------------------------------------------------------+ |
+---------------------------------------------------------------+
```

---

## 3. Token Driver

The token driver owns the decode loop.

Pseudo-flow:

```python
for token in generation:
    runtime.prepare_token(token)
    for layer in model.layers:
        runtime.ensure_layer_ready(layer)
        compute(layer)
        runtime.record_access(layer)
    runtime.commit_token(token)
```

The token driver should not synchronously wait for SSD during normal operation.

---

## 4. Residency Manager

The residency manager tracks where every object lives.

```python
class ObjectState:
    object_id: str
    object_type: str
    size_bytes: int
    tier: str
    temperature: float
    last_access_ns: int
    predicted_next_use_step: int
    reuse_distance: int
    pinned: bool
    compressed: bool
    dirty: bool
    owner_session: str
    priority: int
    deadline_step: int | None
```

Object types:

```text
KV_BLOCK
WEIGHT_TILE
EXPERT_PAGE
RETRIEVAL_CHUNK
ADAPTER_PAGE
SESSION_STATE
PREFETCH_BUNDLE
```

---

## 5. Residency States

Possible states:

```text
FLASH_ONLY
FLASH_TO_DRAM_IN_FLIGHT
DRAM_RESIDENT
DRAM_TO_SRAM_IN_FLIGHT
SRAM_RESIDENT
EVICTING_TO_DRAM
EVICTING_TO_FLASH
PINNED
COMPRESSED_COLD
```

---

## 6. Deadline-Aware Streaming

Each flash read should be modeled as a deadline-bearing operation, not a best-effort cache fill.

Each read carries:

- object id
- byte range
- target DRAM buffer
- deadline
- priority
- expected use step

Example request:

```python
class StreamingRequest:
    object_id: str
    byte_offset: int
    size_bytes: int
    dram_buffer_id: str
    deadline_step: int
    expected_use_step: int
    priority: float
```

Late completion is not just a lower hit rate. It is a policy failure against the runtime contract.

---

## 7. Prefetch Planner

The prefetch planner predicts future needs.

Inputs:

- current token
- current layer
- layer graph
- attention history
- KV access history
- expert routing probabilities
- compiler hints
- flash queue state
- DRAM free space
- latency budget
- trace replay metadata

Outputs:

- objects to prefetch from flash to DRAM
- objects to promote from DRAM to SRAM
- objects to evict
- objects to compress
- IO queue order

---

## 8. Prefetch Priority Score

Example scoring function:

```text
score =
  A * imminence
+ B * predicted_reuse
+ C * attention_probability
+ D * expert_probability
+ E * tenant_priority
- F * object_size_penalty
- G * decompression_cost
- H * dram_pressure_penalty
```

Where:

```text
imminence = 1 / predicted_steps_until_use
```

---

## 9. SRAM Manager

SRAM capacity is scarce.

SRAM manager responsibilities:

- hold active tiles
- reserve scratch buffers
- stage current compute micro-kernel inputs
- avoid thrashing
- respect compiler tile schedule
- maintain deterministic timing

SRAM is not modeled as a passive cache. It is explicitly scheduled as a scratchpad ring.

---

## 10. DRAM Manager

DRAM acts as the main predictive staging buffer.

Responsibilities:

- receive flash pages
- hold upcoming compute data
- hold warm KV
- store metadata
- support decompression
- feed SRAM
- absorb flash latency

DRAM admission policy:

```text
admit if:
  object is likely needed within prefetch_window
  or object is repeatedly accessed
  or object is required by compiler schedule
  or object is referenced by trace-guided metadata
```

---

## 11. Flash IO Engine

Flash IO must be asynchronous, batched, and mostly sequential.

Possible implementation:

- io_uring
- O_DIRECT
- fixed buffers
- registered files
- queue-depth management
- large sequential reads
- completion polling

Pseudo-flow:

```python
def submit_prefetch(bundle):
    for page in bundle.pages:
        io_uring_submit_read(page.flash_offset, page.size, page.dram_buffer)
    mark_state(bundle, "FLASH_TO_DRAM_IN_FLIGHT")
```

Completion:

```python
def on_flash_complete(page):
    if page.compressed:
        schedule_decompression(page)
    else:
        residency.mark_dram_resident(page)
```

---

## 12. Policy Failure Definition

The runtime should make policy failures explicit.

```text
Synchronous flash read on token-critical path = policy failure
```

Other policy failures:

- late prefetch completion
- decompression misses deadline
- SRAM tile not ready at use step
- random read burst dominates sequential plan

These should be reported directly in metrics and logs, not hidden inside generic cache statistics.

---

## 13. Runtime Modes

The repo should support multiple research modes:

### Compatibility RAM-Emulation Mode

- flash appears memory-like
- easier to get running
- good for functional bring-up
- fragile under random access

### Optimized Stream-to-Scratchpad Mode

- explicit sequential streaming
- explicit DRAM staging
- explicit SRAM promotion
- preferred high-performance direction

### Hybrid Migration Mode

- boot or cold-start with RAM-emulation semantics
- capture traces and hot paths
- migrate repeated accesses to explicit streaming

> RAM-emulation gets the model running. Stream-to-scratchpad gets the model fast.

---

## 14. Trace Replay Mode

The runtime can replay captured access traces to test:

- prefetch policy quality
- flash layout quality
- bundle ordering
- SRAM scheduling
- p95 and p99 latency behavior

Replay mode is especially useful before full integration with a live inference engine.

---

## 15. IO Batching

Bad:

```text
many small random 4KB reads
```

Good:

```text
large sequential 1MB-16MB reads
```

Batching opportunities:

- contiguous layer pages
- grouped KV blocks
- grouped experts
- session bundle prefetch
- retrieval chunk bundles

---

## 16. Decompression Pipeline

Cold flash pages may be compressed.

Pipeline:

```text
Flash read
  |
  v
DRAM compressed buffer
  |
  v
decompress worker
  |
  v
DRAM uncompressed buffer
  |
  v
SRAM promotion
```

Decompression must not block compute and must complete before the object's use deadline.

---

## 17. KV Cache Runtime

KV cache should be tracked by block.

```python
class KVBlock:
    session_id: str
    layer_id: int
    head_id: int
    token_start: int
    token_end: int
    tier: str
    attention_score: float
    last_used_token: int
    compressed: bool
```

---

## 18. MoE Runtime

For Mixture-of-Experts models:

```text
SRAM:
  selected expert tiles

DRAM:
  top probable experts

Flash:
  cold experts
```

Expert prefetch input:

- previous routing
- token embedding
- router logits
- batch-level expert distribution
- tenant workload history

---

## 19. Miss Handling

Miss types:

```text
SRAM_MISS_DRAM_HIT
DRAM_MISS_FLASH_HIT
FLASH_MISS
DECOMPRESSION_MISS
PREDICTOR_MISS
```

Severity:

```text
SRAM miss with DRAM hit:
  acceptable if DRAM-to-SRAM latency is hidden

DRAM miss requiring flash:
  dangerous

Flash miss on token path:
  policy failure
```

---

## 20. Miss Recovery

If a synchronous flash miss occurs:

1. pause affected session
2. continue other sessions if possible
3. submit urgent flash read
4. increase future prefetch window
5. update predictor penalty
6. optionally pin similar objects
7. record a policy failure metric

---

## 21. Multi-Tenant Runtime

Each tenant/session gets:

```text
dram budget
flash queue budget
sram reservation
latency target
priority
eviction class
```

Scheduling classes:

```text
interactive
batch
background
prefill-heavy
decode-heavy
```

---

## 22. Runtime Metrics

Track:

- tokens/sec
- time-to-first-token
- p50/p95/p99 token latency
- SRAM hit rate
- DRAM hit rate
- flash synchronous miss rate
- sync flash policy failures
- prefetch accuracy
- prefetch waste
- late prefetch rate
- DRAM pressure
- sequential read ratio
- random flash read count
- average read size
- compression ratio
- decompression time
- eviction churn
- tenant interference

---

## 23. Runtime Policy Loop

```python
while serving:
    observe_metrics()
    update_temperatures()
    predict_future_access()
    submit_prefetches()
    promote_hot_objects()
    evict_cold_objects()
    enforce_tenant_budgets()
    adjust_window_size()
```

---

## 24. Implementation Milestones

### Runtime v0

- in-memory simulation
- synthetic tiers
- trace replay

### Runtime v1

- real DRAM plus file-backed flash simulation
- async prefetch thread
- KV block tracking

### Runtime v2

- io_uring-based NVMe reads
- page-aligned tensor files
- latency measurements

### Runtime v3

- compatibility RAM-emulation mode
- stream-to-scratchpad mode
- hybrid migration experiments

### Runtime v4

- multi-session scheduling
- adaptive prefetch
- compression support

---

## 25. Runtime Summary

The runtime is the brain of the system.

Hardware tiers alone are not enough.

The invention is the policy and orchestration system that ensures:

```text
flash work happens early
dram absorbs latency
sram feeds compute
tokens do not wait
```
