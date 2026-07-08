# MoE Expert Tiering

## Purpose

Mixture-of-Experts models are a strong fit for flash-backed memory because only a subset of experts is active per token.

```text
active expert tiles -> SRAM
likely experts      -> DRAM
cold experts        -> Flash
```

---

## Runtime Flow

```text
Router / predictor
  -> prefetch top probable experts Flash to DRAM
  -> promote selected expert tiles DRAM to SRAM
  -> compute selected experts
```

---

## Expert Metadata

```yaml
expert_id: expert_42
layer_id: 18
size_bytes: 67108864
current_tier: FLASH
routing_probability: 0.04
last_used_token: 9021
temperature: 0.13
group_id: expert_group_5
```

---

## Placement

```text
SRAM:
  active expert tiles only

DRAM:
  top-k likely experts
  recently used experts
  tenant-hot experts

Flash:
  cold experts
  low-probability experts
  rare domain experts
```

---

## Router-Aware Prefetch

Router logits can guide prefetch. The challenge is timing. If router output arrives too late, flash cannot be hidden.

Before router logits are available, predict experts using:

```text
previous token expert choices
prompt domain
tenant history
batch-level expert distribution
recent routing locality
semantic class of request
```

---

## Routing Entropy

Low entropy:

```text
same experts repeatedly selected
easy to prefetch
good for flash tiering
```

High entropy:

```text
experts unpredictable
more flash misses
bad for latency
```

---

## Expert Prefetch Score

```text
score =
  A * router_probability
+ B * recent_frequency
+ C * tenant_hotness
+ D * coaccess_probability
- E * expert_size_penalty
- F * flash_distance_penalty
```

---

## Batch Scheduling

The runtime can group requests likely to use the same experts. This improves DRAM reuse and reduces flash reads.

---

## Failure Mode

If the selected expert is not in DRAM and must be read from flash synchronously, latency spikes.

Mitigations:

```text
keep top-k experts in DRAM
over-prefetch when uncertainty is high
use smaller expert pages
batch similar requests
maintain fallback experts
increase DRAM budget for MoE layers
```
