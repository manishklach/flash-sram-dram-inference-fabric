# Trace-Guided Linearization

## 1. Concept

Trace-guided linearization records inference memory accesses and uses them to repack model objects into sequential flash layouts.

This is a key differentiator from generic SSD caching. Instead of reacting to misses, the system learns repeated access structure and rewrites flash layout around it.

---

## 2. Pipeline

```text
Run inference workload
        ↓
Capture memory trace
        ↓
Identify repeated access sequences
        ↓
Group co-accessed objects
        ↓
Repack flash layout
        ↓
Generate prefetch metadata
        ↓
Replay with sequential streaming
        ↓
Measure p95/p99 latency
```

---

## 3. Trace Events

Example JSONL event format:

```json
{
  "step": 1204,
  "session_id": "s1",
  "token_id": 42,
  "layer_id": 18,
  "op": "attention",
  "object_id": "layer_18.attn.qkv.tile_3",
  "object_type": "WEIGHT_TILE",
  "size_bytes": 1048576,
  "access_kind": "read",
  "deadline_step": 1210
}
```

The schema must be rich enough to recover:

- access order
- co-access groups
- deadlines
- session context
- whether an object is token-critical

---

## 4. Linearization Algorithm

```python
def linearize_trace(events):
    sequences = find_repeated_sequences(events)
    groups = group_by_coaccess(sequences)
    layout = assign_contiguous_offsets(groups)
    metadata = emit_prefetch_metadata(layout)
    return layout, metadata
```

This pseudo-code hides several hard problems, but it captures the intended flow:

- identify repeatable access order
- convert order into groups
- allocate contiguous layout
- emit runtime-visible metadata

---

## 5. Co-Access Grouping

Potential group types:

- layer bundles
- QKV bundles
- MLP bundles
- expert groups
- KV clusters
- retrieval chunks

Co-access grouping should optimize for sequentiality without destroying future reuse opportunities.

---

## 6. Output Layout

Example:

```text
model.pack
  layer_00_bundle
  layer_01_bundle
  layer_02_bundle
  ...
  moe_layer_18_group_0
  moe_layer_18_group_1
```

The same approach can be applied to KV packs, expert packs, and retrieval packs.

---

## 7. Runtime Integration

The runtime uses emitted metadata to:

- submit reads N steps ahead
- track completion
- stage in DRAM
- promote to SRAM
- mark late reads as policy failures

This lets layout generation and runtime scheduling reinforce each other.

---

## 8. Metrics

Track:

- sequential read ratio
- random read count
- average read size
- prefetch accuracy
- late prefetch rate
- p95/p99 token latency
- synchronous flash miss rate

These metrics are more informative than generic cache hit rate alone.

---

## 9. Why This Matters

This is one of the repo's strongest differentiators versus generic SSD caching.

The strongest story is not "put tensors on SSD." The strongest story is:

- inference access is often structured
- structure can be captured in traces
- traces can drive flash repacking
- repacking can transform random access into sequential streaming
- sequential streaming can be staged through DRAM into SRAM before compute needs it
