# Simulator Design

## Purpose

The simulator is the first executable proof point for the Flash–SRAM–DRAM Inference Fabric. It answers one question: **when can SSD flash latency be hidden behind DRAM staging and SRAM hot-path execution?**

The simulator models:

```text
SRAM  = hot deterministic working set
DRAM  = warm staging and prediction tier
Flash = cold capacity tier
```

It does not need to run a real LLM initially. It should replay synthetic or captured memory traces that resemble LLM inference.

---

## Architecture

```text
Trace Driver
  -> Policy Engine
  -> Memory Tier Model
  -> Metrics Engine
```

The trace driver emits events such as layer weight access, KV block access, expert-page access, and retrieval-page access. The policy engine decides whether to prefetch, promote, evict, or do nothing. The tier model simulates SRAM, DRAM, and flash latency/capacity. The metrics engine records p50/p95/p99 latency, hit rates, miss rates, and wasted prefetch.

---

## Core Classes

```python
class MemoryObject:
    id: str
    type: str
    size_bytes: int
    layer_id: int | None
    head_id: int | None
    expert_id: int | None
    session_id: str | None
    token_start: int | None
    token_end: int | None
    current_tier: str
    compressed: bool
    last_access_step: int
    predicted_next_use_step: int | None
    temperature: float

class AccessEvent:
    step: int
    token_id: int
    layer_id: int
    object_id: str
    object_type: str
    size_bytes: int
    deadline_step: int
    is_critical: bool
```

Object types:

```text
WEIGHT_TILE
KV_BLOCK
EXPERT_PAGE
RETRIEVAL_CHUNK
ADAPTER_PAGE
SESSION_STATE
METADATA_PAGE
```

---

## Memory Tier Model

Each tier has capacity, latency, bandwidth, and contained objects.

```yaml
sram:
  size_mb: 64
  latency_ns: 5

dram:
  size_gb: 16
  latency_ns: 80
  bandwidth_gbps: 100

flash:
  size_tb: 4
  read_latency_us: 80
  bandwidth_gbps: 7
  optimal_read_size_mb: 4
```

---

## Policies

Implement these policies first:

1. **NoPrefetchPolicy** — demand-load only.
2. **LRUPolicy** — generic cache baseline.
3. **FixedWindowPrefetchPolicy** — always prefetch N layers or KV blocks ahead.
4. **PredictivePolicy** — uses temperature, deadlines, reuse distance, and hints.
5. **OraclePolicy** — perfect future knowledge; upper bound.
6. **AdaptivePolicy** — adjusts window based on late misses and wasted prefetch.

---

## Workloads

### Layer Streaming

Predictable access pattern:

```text
layer_0 -> layer_1 -> ... -> layer_N
```

### KV Cache

Supports local attention, sink tokens, sparse old-context reads, and random old-context stress tests.

### MoE

Supports configurable routing entropy. Low entropy should perform well; high entropy should expose failure.

### RAG

Models retrieval pages loaded before or during generation.

### Multi-Tenant

Models active and idle sessions, session spill, and resume from flash.

---

## Metrics

The most important metric is:

```text
synchronous_flash_miss_rate
```

Other metrics:

```text
p50 token latency
p95 token latency
p99 token latency
SRAM hit rate
DRAM hit rate
flash synchronous miss rate
prefetch accuracy
prefetch waste
eviction churn
DRAM pressure
read amplification
```

---

## Output Format

```csv
run_id,policy,workload,sram_mb,dram_gb,flash_latency_us,p50_ms,p95_ms,p99_ms,sram_hit_rate,dram_hit_rate,sync_flash_miss_rate,prefetch_accuracy,prefetch_waste
```

---

## Success Criteria

The simulator is useful if it can show:

```text
when flash can be hidden
when flash cannot be hidden
how much DRAM is needed
which policies work
how p99 latency fails
```
