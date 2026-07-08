# Flash Layout and Tensor Packing

## Purpose

Commodity SSD flash is efficient when the system performs large sequential reads. It is inefficient for tiny unpredictable random reads during token decode.

The flash layout must therefore match inference execution order and co-access patterns.

---

## Core Principle

Bad:

```text
random 4KB reads during decode
```

Good:

```text
large sequential prefetch bundles before decode needs them
```

---

## Pack Files

Recommended files:

```text
model.pack
kv.pack
experts.pack
adapters.pack
retrieval.pack
```

Each pack contains:

```text
header
metadata table
object payloads
checksums
optional compression blocks
```

---

## Model Weight Layout

Transformer layers execute in order, so model weights should be packed by layer order.

```text
model.pack
  header
  metadata
  layer_00_bundle
  layer_01_bundle
  layer_02_bundle
  ...
  layer_31_bundle
  output_head_bundle
```

Layer bundle example:

```text
layer_12_bundle
  q_proj
  k_proj
  v_proj
  o_proj
  gate_proj
  up_proj
  down_proj
  norm constants
```

---

## Flash Offset Metadata

```json
{
  "object_id": "layer_12_bundle",
  "pack_file": "model.pack",
  "offset": 805306368,
  "size_bytes": 67108864,
  "compressed": true,
  "compression_type": "zstd",
  "alignment": 1048576
}
```

---

## Alignment

Suggested alignment:

```text
metadata: 4KB
small objects: 64KB
large tensor bundles: 1MB+
compression blocks: 1MB–16MB
```

---

## KV Cache Layout

KV should be append-friendly because tokens are generated over time.

```text
kv/session_{session_id}/layer_{layer}/head_{head}/block_{block}.kv
```

For packed storage:

```text
kv.pack
  session_7_header
  session_7_layer_00_head_00_blocks
  session_7_layer_00_head_01_blocks
  ...
```

---

## MoE Expert Layout

Group experts by co-access probability.

```text
experts.pack
  layer_18_group_0
  layer_18_group_1
  layer_18_group_2
```

If experts 4, 17, and 22 are often selected together, store them together.

---

## Profile-Guided Repacking

Workflow:

```text
1. collect access trace
2. compute co-access matrix
3. group objects frequently used together
4. rewrite pack files
5. update flash index
6. rerun benchmark
```

---

## Layout Quality Metrics

```text
sequential_read_ratio
average_read_size
random_read_count
flash_bytes_read
useful_bytes_read
read_amplification
late_read_count
```

---

## Summary

Flash layout is not a detail. A poor layout creates random SSD paging. A good layout turns flash into a predictable sequential streaming tier.
