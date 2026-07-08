# Energy Cost Model

## 1. Purpose

The long-term pitch of this architecture is lower-cost AI inference. Memory cost has two components: capital expenditure (CAPEX) per GB and operating expenditure (OPEX) per inference, dominated by energy.

This document models the energy per token across the SRAM-DRAM-flash hierarchy and compares it against an all-DRAM or all-HBM baseline.

---

## 2. Energy Per Access by Tier

| Tier | Energy per bit accessed | Source / Reference |
|---|---|---|
| **SRAM (on-chip)** | ~0.5 - 1 pJ/bit | 7nm process, on-chip |
| **DRAM (DDR5/LPDDR5X)** | ~2 - 5 pJ/bit | DRAM die + PHY + PCB |
| **HBM2e** | ~3 - 6 pJ/bit | Includes TSV + interposer |
| **NVMe SSD (NAND flash)** | ~0.01 - 0.1 pJ/bit | NAND die read (before controller) |
| **SSD controller + PCIe** | ~2 - 5 pJ/bit | Controller, DRAM buffer, SerDes |

Raw NAND reads are extremely energy-efficient. The overhead comes from the controller, DRAM buffer inside the SSD, and the PCIe link.

---

## 3. SSD Energy Breakdown

A realistic NVMe SSD energy model per read:

```text
E_ssd_read = E_nand + E_controller + E_pcie + E_dram_buffer
```

| Component | Energy per 4 KB read | Notes |
|---|---|---|
| NAND die read | ~0.4 µJ | 0.1 pJ/bit × 4096 × 8 |
| Controller + FTL | ~2 µJ | ECC, logical mapping, scheduling |
| PCIe Gen4 x4 transfer | ~1.5 µJ | SerDes power at ~10 pJ/bit |
| Internal DRAM buffer | ~0.5 µJ | Buffer copy for staging |
| **Total per 4 KB** | **~4.4 µJ** | |
| **Total per 1 MB** | **~1,100 µJ** | Sequential, amortized |
| **Total per 1 MB (random)** | **~4,400 µJ** | Higher controller + NAND die energy |

---

## 4. Energy Per Token: Weight Streaming

### Scenario: 7B-parameter model, FP16, 32 layers

Model size per layer: ~64 MB (weights + attention projections + MLP).

| Tier | Bytes read per layer | Energy per byte | Energy per layer |
|---|---|---|---|
| **SRAM (tile-level)** | 4 MB (active tile) | 0.75 pJ/bit = 0.75 µJ/MB | 3 µJ |
| **DRAM (warm staging)** | 64 MB (layer bundle) | 3.5 pJ/bit = 3.5 µJ/MB | 224 µJ |
| **Flash (cold, sequential)** | 21.3 MB (64 MB / 3x Zstd) | ~1.1 µJ/MB (sequential) | 23.4 µJ |

If layers are streamed from flash (cold start):

```
E_flash_weights_per_token = 32 layers × 23.4 µJ = 749 µJ
E_dram_weights_per_token  = 32 layers × 224 µJ  = 7,168 µJ
E_sram_weights_per_token  = 32 layers × 3 µJ    = 96 µJ
```

Weight streaming from flash uses 750 µJ vs 7,168 µJ for DRAM — **flash is ~10x more energy-efficient for weight access** when compressed.

---

## 5. Energy Per Token: KV Cache Decode

### Scenario: 128K context, FP16, 32 layers, 32 heads, 128 token KV blocks

KV size per block: 256 KB. Total KV: ~8 GB.

Per decode step, 8 KV blocks accessed (grouped-query attention, 8 KV heads).

| Tier | KB read per token | Energy per MB | Energy per token |
|---|---|---|---|
| **SRAM (hot tiles)** | 512 KB (2 blocks) | 0.75 µJ/MB | 0.38 µJ |
| **DRAM (warm blocks)** | 1.5 MB (6 blocks) | 3.5 µJ/MB | 5.25 µJ |
| **Flash (cold blocks)** | 0.5 MB (2 blocks, compressed 2x LZ4 → 0.25 MB flash read) | 1.1 µJ/MB | 0.275 µJ |

Total KV energy per decode step: ~5.9 µJ.

If all KV were DRAM-resident:

| Tier | MB read per token | Energy per MB | Energy per token |
|---|---|---|---|
| **DRAM** | 2 MB | 3.5 µJ/MB | 7.0 µJ |
| **Total** | | | **7.0 µJ** |

Flash tiering saves ~1.1 µJ per token on KV. Small in absolute terms.

---

## 6. Comparison: Flash-Backed vs All-DRAM vs HBM

| Configuration | Energy per token (weights) | Energy per token (KV) | Total | Relative |
|---|---|---|---|---|
| **All HBM** (80 MB) | ~2,880 µJ | ~0 (all hot) | ~2,880 µJ | 1.0x |
| **All DRAM** (16 GB) | ~7,168 µJ | ~7 µJ | ~7,175 µJ | 2.5x |
| **Flash-backed** (64 MB SRAM + 8 GB DRAM + 4 TB flash) | ~749 µJ | ~5.9 µJ | ~755 µJ | 0.26x |
| **Flash-backed + compressed weights** | ~250 µJ | ~5.9 µJ | ~256 µJ | 0.09x |

**Key finding: Flash-backed inference uses ~1/10 the energy of all-DRAM for weight-dominated workloads** because NAND reads are fundamentally more efficient than DRAM refreshes + row activations.

---

## 7. Energy Cost in Dollars

At average US commercial electricity rate of $0.12/kWh:

| Configuration | Energy per 1M tokens | Cost per 1M tokens |
|---|---|---|
| HBM | ~2,880 J | $0.096 |
| All DRAM | ~7,175 J | $0.239 |
| Flash-backed | ~755 J | $0.025 |
| Flash-backed + compressed | ~256 J | $0.009 |

**Flash-backed inference costs ~$0.025 per million tokens in energy alone.** At scale (100M tokens/day), this is $2.50/day vs $23.90/day for all-DRAM.

---

## 8. Total Cost of Ownership (TCO) Comparison

### Assumptions: 1 server, 3-year lifetime, 100M tokens/day

| Component | All-DRAM Server | Flash-Backed Server |
|---|---|---|
| **DRAM** (16 GB × $5/GB) | $80 | $80 |
| **Flash** (4 TB NVMe × $200/TB) | $0 | $800 |
| **HBM accelerator** (80 GB HBM × $15/GB) | $1,200 | $0 |
| **Compute** (GPU/NPU) | $10,000 | $5,000 (no HBM) |
| **Energy over 3 years** ($0.12/kWh, 100M tok/day) | $2,615 | $275 |
| **Total 3-year TCO** | **~$13,895** | **~$6,155** |

**Flash-backed offers ~55% TCO reduction** for this scenario.

---

## 9. Where the Energy Model Breaks

### 9.1 Write-Heavy Workloads

Energy model changes dramatically for training or frequent session writes:

- NAND writes consume ~10x more energy than reads
- SSD controller energy increases with write amplification
- DRAM buffer must stay active for write coalescing

Flash-backed architecture is 3-5x less energy-attractive for write-heavy workloads.

### 9.2 High Random-Read Workloads

If the predictor fails and random reads dominate:

- Random 4 KB reads consume ~4x more energy per MB than sequential (4,400 µJ vs 1,100 µJ per MB)
- Energy per token could approach or exceed all-DRAM

### 9.3 Very Small Batch

At batch size 1 with no lookahead, flash may not be hidden and DRAM must serve most data — energy savings shrink.

---

## 10. Simulator Energy Model

The simulator should track:

```python
class EnergyMetrics:
    sram_joules: float
    dram_joules: float
    flash_nand_joules: float
    flash_controller_joules: float
    flash_pcie_joules: float
    decompression_joules: float
    compute_joules: float  # for reference

    def total_joules(self) -> float:
        return (self.sram_joules + self.dram_joules
                + self.flash_nand_joules + self.flash_controller_joules
                + self.flash_pcie_joules + self.decompression_joules)

    def joules_per_token(self, tokens: int) -> float:
        return self.total_joules() / tokens
```

Energy counters increment per access event based on tier, object size, and access pattern (sequential vs random).

---

## 11. Summary

1. **Flash-backed inference is 5-10x more energy-efficient than DRAM-only** for weight-dominated workloads, because NAND flash reads use ~1/40 the energy per bit of DRAM reads.

2. **Energy savings come from weight streaming, not KV.** KV energy per token is small in absolute terms because only a fraction of KV is accessed per step.

3. **Compression amplifies energy savings.** Each compressed byte read from flash saves NAND + controller + PCIe energy, and fewer DRAM bytes need staging.

4. **TCO reduction is ~55%** for a typical serving server over 3 years, driven by eliminating HBM costs and reducing energy consumption.

5. **The model breaks on random reads and write-heavy workloads** — the energy advantage depends on the same sequential/predictable access pattern that the rest of the architecture requires.
