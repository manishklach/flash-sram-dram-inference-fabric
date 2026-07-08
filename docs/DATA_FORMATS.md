# Data Formats

## Purpose

This document defines repo data formats for traces, memory objects, prefetch records, residency movement, compiler hints, benchmark results, and flash-pack indices.

---

## Memory Object Metadata

```json
{
  "object_id": "kv.session_7.layer_12.head_3.block_44",
  "object_type": "KV_BLOCK",
  "size_bytes": 262144,
  "layer_id": 12,
  "head_id": 3,
  "session_id": "session_7",
  "token_start": 5632,
  "token_end": 5759,
  "preferred_tier": "DRAM",
  "compression_allowed": true,
  "pinning_allowed": false
}
```

---

## Access Trace JSONL

Each line is one access event.

```json
{
  "step": 10524,
  "timestamp_ns": 982340000,
  "session_id": "session_7",
  "token_id": 82,
  "layer_id": 12,
  "op_type": "ATTENTION",
  "object_id": "kv.session_7.layer_12.head_3.block_44",
  "object_type": "KV_BLOCK",
  "size_bytes": 262144,
  "is_critical": true,
  "deadline_step": 10528
}
```

---

## Prefetch Trace

```json
{
  "event": "PREFETCH_SUBMIT",
  "step": 10500,
  "object_id": "layer_16.attn.qkv.bundle",
  "source_tier": "FLASH",
  "target_tier": "DRAM",
  "size_bytes": 8388608,
  "deadline_step": 10580,
  "priority": 0.91,
  "reason": "LAYER_LOOKAHEAD"
}
```

Completion:

```json
{
  "event": "PREFETCH_COMPLETE",
  "step": 10562,
  "object_id": "layer_16.attn.qkv.bundle",
  "source_tier": "FLASH",
  "target_tier": "DRAM",
  "status": "ON_TIME"
}
```

---

## Residency Trace

```json
{
  "step": 10562,
  "object_id": "layer_16.attn.qkv.bundle",
  "old_tier": "FLASH",
  "new_tier": "DRAM",
  "reason": "PREFETCH_COMPLETE"
}
```

---

## Compiler Hint YAML

```yaml
model_id: example-7b
format_version: 1
layers:
  - layer_id: 12
    prefetch_distance_layers: 4
    bundles:
      - bundle_id: layer_12.attn.qkv
        target_tier: DRAM
        deadline: layer_12_start
        objects:
          - layer_12.q_proj.weight
          - layer_12.k_proj.weight
          - layer_12.v_proj.weight
```

---

## KV Policy YAML

```yaml
kv_policy:
  block_tokens: 128
  group_by: [session, layer, head]
  hot_window_tokens: 4096
  sink_tokens: 256
  compress_cold_after_tokens: 32768
  spill_to_flash_after_tokens: 65536
  attention_temperature_decay: 0.98
```

---

## Benchmark Result JSON

```json
{
  "run_id": "2026-07-07-001",
  "workload": "long_context_kv",
  "policy": "predictive",
  "config": {
    "sram_mb": 64,
    "dram_gb": 8,
    "flash_latency_us": 80,
    "context_tokens": 131072
  },
  "metrics": {
    "p50_ms": 12.4,
    "p95_ms": 19.8,
    "p99_ms": 42.1,
    "sram_hit_rate": 0.91,
    "dram_hit_rate": 0.97,
    "sync_flash_miss_rate": 0.006,
    "prefetch_accuracy": 0.84,
    "prefetch_waste": 0.12
  }
}
```

---

## Naming Rules

```text
weight.layer_{L}.{name}.tile_{T}
kv.session_{S}.layer_{L}.head_{H}.block_{B}
expert.layer_{L}.expert_{E}.page_{P}
rag.session_{S}.chunk_{C}
adapter.tenant_{T}.adapter_{A}.page_{P}
```
