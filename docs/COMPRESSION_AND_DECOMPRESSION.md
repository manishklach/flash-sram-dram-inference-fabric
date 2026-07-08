# Compression and Decompression

## 1. Purpose

Compression makes the flash tier more effective by increasing effective capacity and bandwidth. However, decompression must complete before the object's deadline — a decompression miss is equivalent to a synchronous flash miss.

This document defines compression strategy, codec selection, per-tier policies, pipeline design, and deadline budgeting.

---

## 2. Compression by Tier

| Tier | Compression | Rationale |
|---|---|---|
| **SRAM** | Never compressed | Latency-critical, bandwidth-hungry; compression saves nothing at this scale |
| **DRAM** | Selective compression | Warm objects remain uncompressed for fast promotion; cold DRAM objects may be lightly compressed (LZ4) to increase effective tier capacity |
| **Flash** | Always compressed | Cold state benefits most; compression increases effective bandwidth by 2-4x |

---

## 3. Codec Selection

### 3.1 Candidate Codecs

| Codec | Compression Ratio | Decompress Speed | Use Case |
|---|---|---|---|
| **LZ4** | 1.5x - 2.5x | ~4 GB/s per core | DRAM cold objects, latency-sensitive flash layers |
| **Zstd (level 1-3)** | 2x - 4x | ~1.5 GB/s per core | General flash compression, KV blocks |
| **Zstd (level 6+)** | 3x - 5x | ~500 MB/s per core | Infrequently accessed cold KV, archived sessions |
| **Sparse compression** | Variable | N/A | Pruned / sparse MoE activations |
| **FP16->FP8/INT8 quantization** | 2x | ~0 (reinterpretation) | Model weights, KV cache |

### 3.2 Recommendation

| Object Type | Codec | Rationale |
|---|---|---|
| Cold layer weights | Zstd level 3 | Good ratio (3x), fast enough for streaming budget (~8 µs/MB) |
| Cold KV blocks | LZ4 | Speed over ratio; KV is accessed more unpredictably |
| Archive KV (inactive sessions) | Zstd level 6 | Maximize flash capacity; accessed rarely |
| MoE experts | Zstd level 3 | Balance of ratio and speed for router-triggered access |
| Retrieval embeddings | LZ4 | Accessed under time pressure from RAG pipeline |
| Activations (if spilled) | FP8 quantization | Minimal compute overhead |

---

## 4. Decompression Latency Budget

Decompression must fit within the flash-to-compute pipeline:

```text
Flash read → DRAM compressed → decompress → DRAM uncompressed → SRAM promotion → compute
                ^                                    ^
           deadline_1                            deadline_2
```

Budget:

```
T_total_budget = deadline_2 - submit_time
T_flash_read   = (B_compressed / S_flash) + L_flash_latency
T_decompress   = B_compressed / S_decompress
T_dram_copy    = B_uncompressed / S_dram_bw
```

Constraint:

```
T_flash_read + T_decompress + T_dram_copy <= T_total_budget
```

### Example: Cold KV Block

| Parameter | Value |
|---|---|
| B_uncompressed | 256 KB |
| Compression ratio (LZ4) | 2x |
| B_compressed | 128 KB |
| S_flash_seq | 7 GB/s |
| L_flash_latency | 80 µs |
| S_decompress (LZ4) | 4 GB/s |
| T_total_budget | 500 µs (one layer compute time) |

```
T_flash_read  = (128 KB / 7 GB/s) + 80 µs = 17.9 µs + 80 µs ≈ 98 µs
T_decompress  = 128 KB / 4 GB/s ≈ 31 µs
T_dram_copy   = 256 KB / 100 GB/s ≈ 2.5 µs
Total         = 98 + 31 + 2.5 = 131.5 µs
```

**Result: 131.5 µs < 500 µs.** Decompression fits with 74% headroom.

---

## 5. Decompression Pipeline Options

### 5.1 Inline (CPU fallback)

Flash IO completion → CPU decompress on DRAM buffer → mark ready.

Pros: Simple, no specialized hardware.
Cons: Consumes CPU cycles that could serve other sessions.

### 5.2 Async worker pool

Dedicated decompression threads fed from a work queue.

```text
io_uring CQ → decompress_work_queue → decompress_worker_pool → residency update
```

Pros: Parallelizes decompression with compute.
Cons: Thread management, NUMA considerations.

### 5.3 DMA + hardware decompression

If available, use GPU/NPU DMA engine with inline decompression.

Pros: Zero CPU overhead, minimal latency.
Cons: Hardware dependency, not universally available.

### Recommendation

Start with async worker pool (phase 1), add inline GPU decompression if target hardware supports it (phase 2).

---

## 6. Compression Policy

### 6.1 When to Compress

```python
def should_compress(object, tier):
    if tier == "SRAM":
        return False
    if tier == "DRAM":
        return object.temperature < DRAM_COMPRESS_THRESHOLD
    if tier == "FLASH":
        return True  # always compress on flash write
```

### 6.2 When to Decompress

```python
def schedule_decompression(object):
    if object.target_tier == "SRAM":
        # Must decompress before SRAM promotion
        decompress_async(object)
    elif object.tier == "DRAM":
        if object.temperature > DRAM_DECOMPRESS_THRESHOLD:
            # Promote to uncompressed in DRAM
            decompress_async(object)
```

### 6.3 Recompression

Objects evicted from DRAM to flash should be recompressed if:

- Compression ratio deteriorated (writes to KV blocks)
- Object was previously held uncompressed in DRAM
- Flash capacity pressure is high

```python
def on_evict_to_flash(object):
    if object.compressed:
        return  # already compressed, write as-is
    compress_async(object, compression_level=ZSTD_LEVEL_3)
```

---

## 7. Compression Metadata

```json
{
  "object_id": "kv.session_7.layer_12.head_3.block_44",
  "compression_type": "lz4",
  "uncompressed_size_bytes": 262144,
  "compressed_size_bytes": 131072,
  "flash_offset": 1207959552,
  "checksum_algorithm": "xxhash64",
  "checksum_value": "0xa1b2c3d4",
  "decompression_estimate_us": 31
}
```

This metadata is stored in the flash pack index for quick lookup.

---

## 8. Compression Benchmark Plan

Benchmark each codec on representative inference objects:

| Object | Size | Target Ratio | Decompress Time | Acceptable? |
|---|---|---|---|---|
| Layer weight tile | 1 MB | 2-3x | < 50 µs | Yes |
| KV block | 256 KB | 1.5-2.5x | < 15 µs | Yes |
| MoE expert | 64 MB | 2-3x | < 500 µs | Marginal |
| Retrieval embedding | 128 KB | 1.5-2x | < 10 µs | Yes |

If decompression time exceeds half the compute budget for the consuming layer, the codec is too slow.

---

## 9. Implementation Plan

### Phase 1

- LZ4 for KV, Zstd for weights and experts
- Async decompression worker pool (4 threads)
- Inline decompression as fallback

### Phase 2

- Adaptive compression level (warm objects use faster codec, cold objects use better ratio)
- Checksum verification on decompression
- Compression ratio tracking per object type

### Phase 3

- Recompression on DRAM eviction
- Quantization-aware pipeline for FP16 ↔ FP8 conversion
- Hardware decompression path (if available)

---

## 10. Summary

Compression is not optional for a flash-backed inference system. Without it, effective flash bandwidth is halved or worse. With Zstd level 3 and LZ4, the architecture gains 2-4x capacity and bandwidth at a latency cost that fits comfortably within the compute budget.

The key constraints are:
1. Decompression must finish before the object's deadline
2. Latency-sensitive objects (KV blocks on miss path) should use fast codecs (LZ4)
3. Cold bulk data (weights, archived KV) should use dense codecs (Zstd)
4. The pipeline must be async and parallelized to avoid blocking compute
