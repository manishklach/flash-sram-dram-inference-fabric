# KV Cache Tiering

## Purpose

KV cache is the best first target for this architecture because it naturally has hot, warm, and cold regions.

```text
recent tokens       = hot
near history        = warm
old long-context    = cold
```

---

## Tiered KV Placement

```text
SRAM:
  active attention tiles

DRAM:
  recent KV blocks
  high-attention KV blocks
  sink tokens
  near-future blocks

Flash:
  old low-attention KV blocks
  inactive session KV
  compressed historical context
```

---

## KV Block Metadata

```yaml
session_id: session_7
layer_id: 12
head_id: 3
token_start: 5632
token_end: 5759
size_bytes: 262144
tier: DRAM
temperature: 0.72
compressed: false
```

Object ID:

```text
kv.session_7.layer_12.head_3.block_44
```

---

## Temperature Model

```text
temperature =
  A * recency_score
+ B * attention_score
+ C * sink_token_bonus
+ D * retrieval_relevance
+ E * reuse_frequency
```

---

## Sink Token Policy

Pin important early tokens:

```text
system prompt
beginning of conversation
document headers
role metadata
long-context anchors
```

Policy:

```text
keep sink tokens in DRAM
promote active sink tiles to SRAM
do not spill critical sink tokens to flash
```

---

## Spill Policy

Spill KV to flash when:

```text
block_age > threshold
attention_score < threshold
DRAM_pressure is high
session is not latency-critical
```

---

## Restore Policy

Restore from flash when:

```text
attention predictor indicates old block
retrieval points to block
session resumes
prompt references old context
block enters next sliding window
```

---

## Hard Failure Case

If the model suddenly needs an old cold KV block that is only on flash, token latency spikes.

Mitigations:

```text
semantic KV clustering
old-context prefetch
sink-token pinning
summaries in DRAM
retrieval-triggered prefetch
```

---

## Benchmark Cases

```text
local attention
sink-token attention
random old-context access
retrieval-triggered old-context access
idle session resume
multi-tenant active/idle mix
```

---

## Success Metrics

```text
DRAM saved
p95 token latency
p99 token latency
synchronous flash KV miss rate
KV prefetch accuracy
KV compression ratio
resume latency
```
