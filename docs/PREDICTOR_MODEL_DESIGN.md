# Predictor Model Design

## 1. Purpose

The predictor answers one question:

> Which objects will be needed, and when?

The answer drives every prefetch, promotion, and eviction decision. If the predictor is wrong, flash appears on the critical path. If it is right, flash is hidden.

This document defines the predictor architecture, feature set, training protocol, cold-start strategy, evaluation methodology, and fallback modes.

---

## 2. Predictor Architecture

```text
+------------------------------------------------------------+
|                  Predictor Pipeline                         |
|                                                            |
| Input signals  -->  Feature encoder  -->  Score model      |
|                                              |             |
|                                              v             |
|                              Object scores + deadlines     |
|                                                            |
|                                              |             |
|                                              v             |
|                              Prefetch planner              |
+------------------------------------------------------------+
```

Two architectural families will be evaluated:

### 2.1 Heuristic Scorer (Runtime v1)

A weighted linear scoring function with hand-tuned coefficients:

```
score(object) =
    w1 * imminence
  + w2 * reuse_frequency
  + w3 * temperature
  + w4 * attention_probability
  + w5 * expert_router_probability
  + w6 * tenant_priority
  - w7 * size_penalty
  - w8 * dram_pressure
  - w9 * decompression_cost
```

Where:

```
imminence = 1 / max(1, predicted_steps_until_use)
```

Coefficients are tuned via grid search on trace replay.

### 2.2 Learned Scorer (Runtime v2+)

A lightweight neural network or gradient-boosted tree:

```
input:  [layer_id, token_pos, attention_entropy, router_logits,
         reuse_distance, object_size, session_age, ...]
output: probability_of_use_within_window, expected_use_step
```

Constraints:
- inference latency < 10 µs per prediction
- model size < 256 KB
- updateable online (no full retrain per session)

Decision: start with heuristic scorer (interpretable, zero training data required), graduate to learned scorer once trace data accumulates.

---

## 3. Feature Catalog

### 3.1 Weight Access Features

| Feature | Source | Description |
|---|---|---|
| layer_id | token driver | Current layer being computed |
| token_position | token driver | Position in generation |
| layer_progression | compiler | Layer N always follows layer N-1 |
| tile_offset | compiler | Current tile within layer |

### 3.2 KV Cache Features

| Feature | Source | Description |
|---|---|---|
| recency_score | runtime | Steps since block was last accessed |
| attention_score | attention module | Cumulative attention weight to block |
| sink_token_flag | compiler/kv policy | Block is a sink/pinned token |
| sliding_window_pos | compiler | Position relative to sliding window |
| retrieval_relevance | RAG pipeline | Score from retrieval system |
| access_frequency | runtime | Count of accesses per block |

### 3.3 MoE Features

| Feature | Source | Description |
|---|---|---|
| router_logits | model forward | Logits for each expert |
| routing_history | runtime | Last K expert selections |
| expert_cotraining | compiler | Probability expert B is used if A is selected |
| domain_hint | prompt classifier | Domain classification of input |
| batch_expert_dist | runtime | Expert distribution across current batch |

### 3.4 System Features

| Feature | Source | Description |
|---|---|---|
| dram_pressure | DRAM manager | Fraction of DRAM staging buffer consumed |
| flash_queue_depth | IO engine | Pending flash reads |
| session_priority | scheduler | QoS class of current session |
| tenant_load | scheduler | Number of active sessions |
| ssd_temperature | NVMe health | Thermal throttling state |

---

## 4. Prediction Horizon

The predictor operates at three timescales:

| Horizon | Scope | Update Frequency | Objective |
|---|---|---|---|
| **Micro** (1-10 steps) | Next tiles, next KV block | Per compute step | Drive SRAM promotion from DRAM |
| **Meso** (10-100 steps) | Next layers, next experts | Per token | Drive DRAM staging from flash |
| **Macro** (100+ steps) | Session migration, long-context | Per N tokens or on retrieval | Drive flash layout and admission |

---

## 5. Training Protocol

### 5.1 Offline Training Phase

1. Collect inference traces from target workloads
2. Extract feature vectors at each access event
3. Label: was the object used within `W` steps? What was the actual reuse distance?
4. Train heuristic weights via grid search or learned model via supervised regression
5. Evaluate on held-out workloads (cross-validation against overfitting)

### 5.2 Online Adaptation

The predictor should adapt to distribution shift without full retraining:

- Track prediction error per object type
- If error exceeds threshold, boost weight of recent observations
- Decay stale coefficients exponentially
- Fall back to wider prefetch (more conservative) when uncertainty is high

```python
def adapt_on_miss(miss_event):
    object_type = miss_event.object_type
    self.error_tracker[object_type].append(miss_event)
    if self.error_tracker[object_type].recency_weighted_error() > ADAPT_THRESHOLD:
        self.coefficients[object_type] *= 0.9  # reduce confidence
        self.prefetch_window_multiplier *= 1.1  # widen window
```

---

## 6. Cold-Start Strategy

Before any trace data exists, the predictor must still function:

| Phase | Strategy | Expected Quality |
|---|---|---|
| **Cold start** (first prompt) | Use compiler-provided static layout + fixed prefetch window (N layers ahead) | Moderate — misses on non-sequential access |
| **Warm-up** (first K tokens) | Bootstrap recency and frequency counters | Improving |
| **Stable** (K+ tokens) | Full predictor with history, attention, router signals | Best |

Cold-start default values:

```yaml
cold_start:
  default_prefetch_window_layers: 4
  default_kv_prefetch_blocks: 8
  moe_dram_reservation: 2  # keep 2 experts in DRAM always
  attention_temperature_decay: 0.98
  imminence_weight: 0.4
  reuse_frequency_weight: 0.3
  size_penalty_weight: 0.2
  dram_pressure_weight: 0.1
```

---

## 7. Prediction Quality Metrics

| Metric | Definition | Target |
|---|---|---|
| **Prefetch accuracy** | Fraction of prefetched objects actually used before eviction | > 0.80 |
| **Prefetch waste** | Fraction of DRAM occupied by prefetched-but-unused objects | < 0.15 |
| **Synchronous miss rate** | Fraction of accesses that require synchronous flash read | < 0.01 |
| **Late prefetch rate** | Prefetch completes after the object's deadline | < 0.05 |
| **MAP@K** | Mean average precision of top-K prefetch candidates | > 0.85 |
| **Reuse distance error** | |predicted - actual| reuse distance in steps | < 5 steps |

---

## 8. Fallback Modes

When prediction confidence is low:

| Mode | Behavior | Cost |
|---|---|---|
| **Conservative** | Increase prefetch window, over-prefetch, accept higher DRAM usage | Higher DRAM pressure, lower flash miss rate |
| **Aggressive** | Shrink window, trust compiler layout, accept higher miss rate | Lower DRAM usage, higher latency risk |
| **Oracle-assisted** | Replay known trace for deterministic workloads | No generalization |

Default: switch to conservative when synchronous miss rate exceeds 0.01 over a sliding 100-token window.

```python
def choose_fallback_mode():
    miss_rate = rolling_sync_miss_rate(window=100)
    if miss_rate < 0.005:
        return Mode.AGGRESSIVE
    elif miss_rate < 0.01:
        return Mode.NORMAL
    else:
        return Mode.CONSERVATIVE
```

---

## 9. Implementation Plan

### Phase 1: Heuristic Predictor

- Implement weighted scoring in `predictor/heuristic.py`
- Tune weights via trace replay on synthetic workloads
- Compare against oracle and LRU baselines

### Phase 2: Online Adaptation

- Add error tracking and coefficient adjustment
- Add fallback mode switching
- Validate on distribution-shift scenarios (workload change mid-session)

### Phase 3: Learned Predictor

- Collect corpus of traces across multiple workloads
- Train small MLP or GBDT model
- Compare against tuned heuristic on held-out traces
- Decide whether the complexity is justified

### Phase 4: Hybrid

- Use heuristic as fallback when learned model confidence is low
- Online fine-tune learned model weights on per-session data
- Measure p95/p99 improvement over heuristic-only

---

## 10. Summary

The predictor is the single most important component for the architecture's success. A weak predictor means synchronous flash misses on the token path. A strong predictor means flash is hidden.

The path is:
1. Heuristic — fast, interpretable, zero-data start
2. Adaptive — handles distribution shift
3. Learned — extracts structure heuristic cannot capture
4. Hybrid — best of both, with graceful degradation
