# Latency Budget Model

## 1. Purpose

The architecture claims that flash latency can be hidden behind compute time and DRAM staging. This document builds a quantitative latency budget model to:

- Show the algebraic conditions under which the claim holds
- Derive minimum DRAM window sizes, maximum flash latencies, and batch size constraints
- Provide testable predictions the simulator must validate

---

## 2. Model Parameters

| Symbol | Parameter | Example Value | Source |
|---|---|---|---|
| `T_compute_layer` | Compute time per layer | 500 µs | Model / hardware profile |
| `N_layers` | Number of transformer layers | 32 | Model config |
| `T_decode_token` | Total compute time per token | 16 ms | `T_compute_layer * N_layers` |
| `B_model` | Model weight size per layer bundle | 64 MB | Model config |
| `B_kv_block` | KV block size | 256 KB | KV policy |
| `N_kv_decode` | KV blocks accessed per decode step | 8 | Attention mechanism |
| `S_flash_seq` | Flash sequential read bandwidth | 7 GB/s | NVMe SSD spec |
| `S_flash_rand` | Flash random 4KB read IOPS | 1,000,000 IOPS | NVMe SSD spec |
| `L_flash_read` | Flash read latency (tail) | 80 µs | NVMe SSD spec |
| `T_dram_staging` | DRAM to SRAM copy latency | 2 µs per tile | Memory controller |
| `L_dram_read` | DRAM read latency | 80 ns | DDR5/LPDDR5X |
| `M_dram` | DRAM staging capacity | 8 GB | System config |
| `C_sram` | SRAM scratchpad capacity | 64 MB | On-chip SRAM |
| `R_compression` | Compression ratio (cold data) | 2x-4x | Zstd level 3 |
| `T_decompress` | Decompression time per 1 MB | 8 µs | Lightweight codec |

---

## 3. Fundamental Constraint

Flash is hidden if and only if:

```
T_available >= T_needed
```

Where:

```
T_available = T_compute_layer * N_lookahead_layers
T_needed    = (B_bundle / S_flash_seq) + L_flash_read + T_dram_overhead
```

`T_available` is the compute time during which the runtime can stream data from flash without blocking the token path. `T_needed` is the time to move a bundle from flash into DRAM and make it ready for SRAM promotion.

---

## 4. Layer Streaming Budget

### 4.1 Scenario: Sequential Weight Streaming

Model weights are packed in layer order. While the compute engine processes layer `i`, the runtime prefetches layers `i+1` through `i+N_window`.

Compute provides:

```
T_available = N_window * T_compute_layer
```

Flash requires:

```
T_needed = (N_window * B_layer_bundle / R_compression) / S_flash_seq
         + L_flash_read
         + T_dram_overhead
```

**Solve for minimum N_window:**

```
N_window * T_compute_layer >= (N_window * B_layer_bundle / R_compression) / S_flash_seq + L_flash_read + T_dram_overhead
```

Using example values (R_compression = 1 for uncompressed):

```
N_window * 500 µs >= (N_window * 64 MB) / (7000 MB/s) + 80 µs + 10 µs
N_window * 500 µs >= N_window * 9.14 µs + 90 µs
N_window * (500 - 9.14) µs >= 90 µs
N_window >= 90 / 490.86
N_window >= 0.18
```

**Result: N_window = 1 layer is sufficient for weight streaming with these parameters.**

### 4.2 With Compression

If cold layers are compressed 3x:

```
T_needed = (64 MB / 3) / 7000 MB/s + 80 µs + 10 µs + 8 µs decompress
         = 3.05 µs + 80 µs + 10 µs + 8 µs
         = 101.05 µs
```

Compute budget per layer: 500 µs. Flash IO + decompression consumes ~101 µs.

**Headroom: ~399 µs (80%).** Compression is safe.

### 4.3 Sensitivity: Slow SSD

If flash bandwidth drops to 1 GB/s (e.g., thermal throttle, shared bus):

```
T_needed = N_window * 64 MB / 1000 MB/s + 80 µs + 10 µs
         = N_window * 64 µs + 90 µs
```

Constraint:

```
N_window * 500 µs >= N_window * 64 µs + 90 µs
N_window * 436 µs >= 90 µs
N_window >= 0.21
```

**Still safe at N_window = 1.** The architecture is robust to significant SSD bandwidth degradation for weight streaming because compute is much slower than sequential IO.

---

## 5. KV Cache Decode Budget

### 5.1 Scenario: KV Block Prefetch

During decode, the engine accesses KV blocks for attention. KV blocks have temperature — old blocks may need prefetch from flash.

Per decode step, the predictor identifies N_kv_needed KV blocks. Of these, some are DRAM-resident (hit), some require flash read (miss).

For each flash KV miss:

```
T_needed_kv = (B_kv_block / R_compression) / S_flash_seq + L_flash_read
```

The available budget is the compute time for one decode step of *one layer*, because KV is consumed layer-by-layer. But KV prefetch can start earlier — the predictor has advance notice of which blocks will be attended to.

**Lookahead for KV is token-level, not layer-level.** The predictor knows recent attention patterns and can submit prefetches K tokens ahead.

```
T_available_kv = K_tokens_lookahead * T_decode_token
```

If one KV miss requires 256 KB / 7000 MB/s + 80 µs = 36.6 µs + 80 µs ≈ 117 µs, and the predictor has 1 token of lookahead (T_decode_token = 16 ms), then 16 ms >> 117 µs.

**KV prefetch is easy when lookahead exists.** The challenge is the first access to an unexpectedly needed KV block.

---

## 6. DRAM Staging Window Sizing

### 6.1 Weight Streaming Window

How much DRAM is needed to stage the prefetch window?

```
DRAM_weight_staging = N_window * B_layer_bundle
```

For N_window = 4, B_layer_bundle = 64 MB:

```
DRAM_weight_staging = 256 MB
```

Even N_window = 16 only requires 1 GB. This is negligible in a multi-GB DRAM system.

### 6.2 KV Staging Window

DRAM must hold warm KV blocks. For a model with KV cache of 128K tokens:

```
KV_total = N_layers * N_heads * d_head * 2 * context_length
```

Rough estimate for a 7B-parameter model: ~8 GB for 128K context at FP16.

DRAM staging window for KV = total KV * (dram_resident_fraction)

If dram_resident_fraction = 0.25 (75% on flash), DRAM usage = 2 GB.

### 6.3 Total DRAM Budget

| Component | Size | Priority |
|---|---|---|
| Warm KV blocks | 2 GB | High |
| Weight prefetch window | 256 MB | High |
| Decompression buffers | 512 MB | Medium |
| Metadata / page tables | 128 MB | Medium |
| Predictor state | 64 MB | Low |
| Other session state | 512 MB | Variable |
| **Total** | **~3.5 GB** | |

With 8 GB DRAM, the architecture has ~4.5 GB headroom. With 16 GB, ample staging capacity.

---

## 7. Batch Prefill Budget

Batch prefill processes many tokens simultaneously. Compute time is much longer per layer, giving more flash-hiding opportunity.

```
T_prefill_layer = T_compute_layer * batch_size
```

For batch_size = 32:

```
T_prefill_layer = 500 µs * 32 = 16,000 µs (16 ms)
```

Flash budget per layer: 16 ms minus DRAM copy overhead. This allows streaming entire model weights from flash per layer if needed.

**Batch prefill is the easiest case for flash-hiding.** Even slow SSDs can be hidden.

---

## 8. Hard Case: Random KV Access

If a model requires a random old KV block with no predictor lookahead:

```
T_stall = L_flash_read + (B_kv_block / S_flash_seq)
        = 80 µs + 36.6 µs
        = 116.6 µs
```

This stall is visible on the token path. With T_decode_token = 16 ms, a 117 µs stall adds ~0.7% to token latency. This is acceptable if rate is < 1% of tokens.

If multiple random KV blocks are needed synchronously:

```
T_stall_total = N_random_hits * 117 µs
```

At N = 10: 1.17 ms stall (7.3% of token time). This is where the architecture fails.

**Mitigations:**
- Predictor lookahead (convert to prefetch, not stall)
- Sink token pinning (prevent random access to critical old tokens)
- Redundant sequential placement (avoid seeking)
- Conservative DRAM reservation for hot KV

---

## 9. Latency Budget Summary Table

| Workload | Flash BW | N_window | DRAM staging | Flash hidden? | Risk |
|---|---|---|---|---|---|
| Weight streaming | 7 GB/s | 1 | 256 MB | Yes | None |
| Weight streaming (throttled) | 1 GB/s | 1 | 256 MB | Yes | Low |
| KV decode (predictable) | 7 GB/s | 1 token | 2 GB | Yes | Low |
| KV decode (random hit) | 7 GB/s | N/A | N/A | No (stall) | Medium |
| MoE low entropy | 7 GB/s | 2-4 | 512 MB | Yes | Low |
| MoE high entropy | 7 GB/s | N/A | N/A | No (stall) | High |
| Batch prefill | 1 GB/s | 1 | 256 MB | Yes | None |

---

## 10. Simulator Validation

The simulator must validate these algebraic predictions. Key test cases:

1. Weight streaming with N_window = 1 should show zero synchronous flash misses
2. KV decode with predictor lookahead >= 1 token should show < 1% miss rate
3. Random KV access without lookahead should show measurable p99 latency degradation
4. MoE high-entropy routing should exceed collapse threshold

If the simulator contradicts the algebraic model, either the model is wrong or the simulator implementation has a bug.

---

## 11. Key Takeaways

1. **Weight streaming is algebraically easy.** Compute is slow enough that even 1-layer lookahead hides flash.

2. **KV prefetch is easy with lookahead, fragile without it.** The predictor is the critical component.

3. **DRAM staging requirements are modest** — 3-4 GB for most configurations. 8-16 GB DRAM provides ample headroom.

4. **Random KV access is the primary threat.** The architecture succeeds or fails on whether the predictor can anticipate old-KV access.

5. **Batch prefill is the most flash-tolerant workload.** This aligns with the thesis that the architecture is strongest for serving scenarios.
