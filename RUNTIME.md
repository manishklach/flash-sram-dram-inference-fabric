# Runtime Design

## 1. Purpose

The runtime is the core of the Flash–SRAM–DRAM Inference Fabric.

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

---

## 2. Runtime Components

```text
┌───────────────────────────────────────────────────────────────┐
│                         Runtime                               │
│                                                               │
│ ┌───────────────┐  ┌────────────────┐  ┌───────────────────┐ │
│ │ Token Driver  │  │ Residency Mgr  │  │ Prefetch Planner  │ │
│ └──────┬────────┘  └───────┬────────┘  └─────────┬─────────┘ │
│        │                   │                     │           │
│ ┌──────▼────────┐  ┌───────▼────────┐  ┌─────────▼─────────┐ │
│ │ SRAM Manager  │  │ DRAM Manager   │  │ Flash IO Engine   │ │
│ └──────┬────────┘  └───────┬────────┘  └─────────┬─────────┘ │
│        │                   │                     │           │
│ ┌──────▼───────────────────▼─────────────────────▼─────────┐ │
│ │                 Metrics + Policy Engine                    │ │
│ └───────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
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

The token driver should never synchronously wait for SSD unless a severe miss occurs.

---

## 4. Residency Manager

The residency manager tracks where every object lives.

Object metadata:

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

State transitions:

```text
FLASH_ONLY
  → FLASH_TO_DRAM_IN_FLIGHT
  → DRAM_RESIDENT
  → DRAM_TO_SRAM_IN_FLIGHT
  → SRAM_RESIDENT
```

Eviction:

```text
SRAM_RESIDENT
  → DRAM_RESIDENT
  → COMPRESSED_COLD
  → FLASH_ONLY
```

---

## 6. Prefetch Planner

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

Outputs:

- objects to prefetch from flash to DRAM
- objects to promote from DRAM to SRAM
- objects to evict
- objects to compress
- IO queue order

---

## 7. Prefetch Priority Score

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
- H * DRAM_pressure_penalty
```

Where:

```text
imminence = 1 / predicted_steps_until_use
```

---

## 8. SRAM Manager

SRAM capacity is scarce.

SRAM manager responsibilities:

- hold active tiles
- reserve scratch buffers
- stage current compute micro-kernel inputs
- avoid thrashing
- respect compiler tile schedule
- maintain deterministic timing

SRAM admission policy:

```text
admit if:
  predicted_next_use <= near_threshold
  and object fits
  and object is needed by active compute step
```

SRAM eviction policy:

```text
evict if:
  compute step complete
  and no near-term reuse
  and object is not pinned
```

---

## 9. DRAM Manager

DRAM acts as the main staging layer.

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
```

DRAM eviction policy:

```text
evict lowest score objects:
  cold KV
  low-probability experts
  old retrieval chunks
  inactive sessions
```

---

## 10. Flash IO Engine

Flash IO must be asynchronous and batched.

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

## 11. IO Batching

Bad:

```text
many small random 4KB reads
```

Good:

```text
large sequential 1MB–16MB reads
```

Batching opportunities:

- contiguous layer pages
- grouped KV blocks
- grouped experts
- session bundle prefetch
- retrieval chunk bundles

---

## 12. Decompression Pipeline

Cold flash pages may be compressed.

Pipeline:

```text
Flash read
  ↓
DRAM compressed buffer
  ↓
decompress worker
  ↓
DRAM uncompressed buffer
  ↓
SRAM promotion
```

Decompression must not block compute.

---

## 13. KV Cache Runtime

KV cache should be tracked by block.

KV block metadata:

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

KV temperature:

```text
hot:
  recent tokens
  sink tokens
  high-attention blocks

warm:
  medium-distance context
  occasionally attended blocks

cold:
  old low-attention context
  inactive session context
```

---

## 14. KV Promotion

Promote KV block when:

- attention probability rises
- sliding window approaches block
- retrieval points to block
- prompt asks about older context
- block belongs to pinned system prompt
- block is repeatedly used

---

## 15. KV Eviction

Evict KV block when:

- attention score decays
- outside active window
- session idle
- DRAM pressure high
- block compresses well
- recomputation is cheaper than retention

---

## 16. MoE Runtime

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

## 17. Miss Handling

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

Flash miss:
  critical failure for latency
```

---

## 18. Miss Recovery

If a synchronous flash miss occurs:

1. pause affected session
2. continue other sessions if possible
3. submit urgent flash read
4. increase future prefetch window
5. update predictor penalty
6. optionally pin similar objects

---

## 19. Multi-Tenant Runtime

Each tenant/session gets:

```text
DRAM budget
flash queue budget
SRAM reservation
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

## 20. Runtime Metrics

Track:

- tokens/sec
- time-to-first-token
- p50/p95/p99 token latency
- SRAM hit rate
- DRAM hit rate
- flash synchronous miss rate
- prefetch accuracy
- prefetch waste
- DRAM pressure
- SSD queue depth
- SSD read amplification
- compression ratio
- decompression time
- eviction churn
- tenant interference

---

## 21. Runtime Policy Loop

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

## 22. Adaptive Window Sizing

If misses increase:

```text
increase prefetch distance
increase DRAM reservation
reduce batch concurrency
compress fewer active objects
```

If waste increases:

```text
decrease prefetch distance
tighten prediction threshold
evict unused prefetched pages
```

---

## 23. Implementation Milestones

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

- integration with llama.cpp or vLLM-style serving prototype
- real KV offload experiments

### Runtime v4

- multi-session scheduling
- adaptive prefetch
- compression support

---

## 24. Runtime Summary

The runtime is the brain of the system.

Hardware tiers alone are not enough.

The invention is the policy and orchestration system that ensures:

```text
flash work happens early
DRAM absorbs latency
SRAM feeds compute
tokens do not wait
```
