# Compiler and Graph Support

## 1. Purpose

The compiler helps the runtime understand the future.

Without compiler support, the runtime can only infer future access patterns from observation. With compiler support, it can know:

- layer order
- tensor dependencies
- reuse distance
- tile shapes
- expected access windows
- MoE expert grouping
- KV access structure
- prefetch opportunities

The compiler does not replace the runtime. It gives the runtime better hints.

---

## 2. Compiler Role

The compiler emits metadata alongside the model.

Metadata may include:

```text
layer dependency graph
tensor placement hints
tile schedule
prefetch schedule
reuse-distance estimates
KV layout hints
expert grouping hints
compression eligibility
pinning requirements
```

---

## 3. Model Graph Analysis

The compiler analyzes the model graph:

```text
input embeddings
attention layers
MLP layers
normalization
MoE routing
projection heads
adapter modules
```

For each node:

```text
node_id
op_type
input_tensors
output_tensors
weight_tensors
expected_size
compute_cost
memory_cost
next_use
last_use
```

---

## 4. Tensor Metadata Format

Example:

```yaml
tensor_id: layer_12.attn.q_proj.weight
tensor_type: WEIGHT_TILE
layer: 12
size_bytes: 8388608
preferred_tier: DRAM
hot_window:
  start_layer: 11
  end_layer: 13
prefetch_distance_layers: 4
compression_allowed: true
pinning_required: false
layout: flash_sequential
```

---

## 5. Residency Annotations

Possible annotations:

```text
PIN_SRAM
PREFER_SRAM
PREFER_DRAM
FLASH_COLD_OK
PREFETCH_EARLY
COMPRESS_WHEN_COLD
DO_NOT_COMPRESS
SEQUENTIAL_STREAM
GROUP_WITH
EVICT_AFTER_USE
```

Example:

```yaml
tensor: layer_20.mlp.down_proj.weight
annotation:
  - PREFETCH_EARLY
  - PREFER_DRAM
  - EVICT_AFTER_USE
```

---

## 6. Layer-Aware Scheduling

Transformer inference has predictable layer order.

The compiler can tell the runtime:

```text
Layer 0 will be used before layer 1
Layer 1 before layer 2
...
Layer N before output head
```

This enables streaming:

```text
current layer in SRAM
next K layers in DRAM
future layers streaming from flash
```

---

## 7. Tile Schedule

Large tensors are divided into tiles.

Tile metadata:

```yaml
tile_id: layer_10.attn.k_proj.tile_004
parent_tensor: layer_10.attn.k_proj.weight
offset: 4194304
size: 1048576
flash_offset: 982515712
alignment: 1048576
next_use_step: 1024
reuse_distance: 8
```

---

## 8. Prefetch Bundle Generation

The compiler can group objects into prefetch bundles.

Example:

```yaml
bundle_id: layer_16_bundle
objects:
  - layer_16.attn.q_proj
  - layer_16.attn.k_proj
  - layer_16.attn.v_proj
  - layer_16.attn.o_proj
read_pattern: sequential
target_tier: DRAM
deadline_layer: 16
submit_by_layer: 12
```

---

## 9. Flash-Aware Layout

The compiler or packaging tool should write model artifacts in flash-friendly order.

Bad layout:

```text
random small tensor files scattered across filesystem
```

Good layout:

```text
large contiguous packed regions
ordered by execution
aligned to flash page / erase block boundaries
```

Example packed model:

```text
model.pack
  header
  metadata table
  layer_00_bundle
  layer_01_bundle
  layer_02_bundle
  ...
  expert_group_00
  expert_group_01
  kv_template_region
```

---

## 10. Layout Goals

- minimize random IO
- maximize sequential reads
- group tensors used together
- align compression blocks
- allow direct DMA into DRAM buffers
- support partial loading
- support checksums
- allow versioning

---

## 11. KV Compiler Hints

KV cache is runtime-generated, but compiler can help define layout.

Hints:

```text
KV block size
head grouping
layer grouping
sliding-window size
sink-token policy
compression eligibility
attention sparsity pattern
```

Example:

```yaml
kv_policy:
  block_tokens: 128
  group_by: [layer, head]
  compress_cold_after_tokens: 4096
  pin_sink_tokens: true
  sink_token_count: 256
```

---

## 12. Attention-Aware Hints

Compiler can expose attention structure:

- full attention
- sliding window attention
- grouped-query attention
- multi-query attention
- sparse attention
- sink tokens
- local/global blocks

This matters because it changes memory needs.

---

## 13. MoE Compiler Support

For MoE models, compiler can group experts.

Expert metadata:

```yaml
expert_id: expert_42
layer: 18
size_bytes: 67108864
group: expert_group_5
coaccess_probability:
  expert_17: 0.12
  expert_31: 0.08
compression_allowed: true
default_tier: FLASH
```

Compiler can group experts that are often selected together.

---

## 14. Router-Aware Prefetch

At runtime, router logits may become available shortly before expert execution.

Compiler can expose:

```text
router location
expert decision deadline
minimum prefetch lead time
fallback expert policy
```

This lets the runtime prefetch top probable experts into DRAM before final selection.

---

## 15. Speculative Decoding Support

Speculative decoding creates branches.

Compiler/runtime should track:

```text
main branch
draft branch
accepted tokens
rejected tokens
branch KV state
rollback cost
```

Placement:

```text
SRAM: currently validated branch
DRAM: likely speculative branch
Flash: abandoned or low-probability branches
```

---

## 16. Compiler–Runtime Interface

Possible JSON schema:

```json
{
  "model": "example-llm",
  "layers": [
    {
      "id": 0,
      "prefetch_distance": 4,
      "bundles": [
        {
          "id": "layer_0_attention",
          "objects": ["q_proj", "k_proj", "v_proj"],
          "deadline": "layer_0_start",
          "preferred_tier": "DRAM"
        }
      ]
    }
  ],
  "kv_policy": {
    "block_tokens": 128,
    "pin_sink_tokens": true
  }
}
```

---

## 17. Runtime Feedback to Compiler

The runtime can emit profiles:

```text
actual reuse distance
miss events
prefetch waste
DRAM pressure
expert selection frequency
attention heat map
```

These can be used to repack the model.

---

## 18. Profile-Guided Repacking

After observing real workloads:

1. collect traces
2. identify frequent co-access
3. reorder flash layout
4. adjust prefetch bundles
5. adjust compression blocks
6. regenerate metadata

This creates a profile-guided memory layout.

---

## 19. Compiler Implementation Phases

### Phase 1

Static metadata generator.

### Phase 2

Layer bundle generator.

### Phase 3

Flash packer.

### Phase 4

KV policy emitter.

### Phase 5

MoE expert grouping.

### Phase 6

Profile-guided repacking.

---

## 20. Compiler Summary

The compiler makes the runtime predictive instead of reactive.

The runtime answers:

```text
What should move now?
```

The compiler answers:

```text
What will be needed later?
```

Together, they make flash usable as a hidden capacity tier.
