from __future__ import annotations

import random as _random

from .traces import AccessEvent


def _append_event(
    events: list[AccessEvent],
    *,
    step: int,
    token_id: int,
    layer_id: int,
    block_id: int,
    kv_block_size_bytes: int,
) -> None:
    object_id = f"kv.session_0.layer_{layer_id}.block_{block_id}"
    events.append(
        AccessEvent(
            step=step,
            token_id=token_id,
            layer_id=layer_id,
            object_id=object_id,
            object_type="KV_BLOCK",
            size_bytes=kv_block_size_bytes,
            deadline_step=step + 1,
            is_critical=True,
        )
    )


def _append_multi_block_layer(
    events: list[AccessEvent],
    *,
    step: int,
    token_id: int,
    layer_id: int,
    block_ids: list[int],
    kv_block_size_bytes: int,
) -> int:
    for block_id in block_ids:
        _append_event(
            events,
            step=step,
            token_id=token_id,
            layer_id=layer_id,
            block_id=block_id,
            kv_block_size_bytes=kv_block_size_bytes,
        )
        step += 1
    return step


def generate_long_context_kv_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    kv_block_size_bytes: int = 1_048_576,
    local_window: int = 4,
    cold_block_every: int = 11,
) -> list[AccessEvent]:
    events: list[AccessEvent] = []
    step = 0
    for token_id in range(tokens):
        current_block = token_id // 2
        for layer_id in range(layers):
            base_block = max(0, current_block - (token_id % max(1, local_window)))
            block_ids = [base_block]
            if token_id > local_window and token_id % cold_block_every == 0 and layer_id % 3 == 0:
                block_ids.append(max(0, current_block - local_window - 8))
            step = _append_multi_block_layer(
                events, step=step, token_id=token_id, layer_id=layer_id,
                block_ids=block_ids, kv_block_size_bytes=kv_block_size_bytes,
            )
    return events


def generate_random_old_context_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    kv_block_size_bytes: int = 1_048_576,
    history_span_blocks: int = 64,
) -> list[AccessEvent]:
    events: list[AccessEvent] = []
    step = 0
    for token_id in range(tokens):
        current_block = token_id // 2
        for layer_id in range(layers):
            if token_id < 8:
                block_ids = [current_block]
            else:
                primary = (token_id * 17 + layer_id * 13) % max(history_span_blocks, current_block + 1)
                secondary = (primary + 19 + layer_id) % max(history_span_blocks, current_block + 17)
                block_ids = [primary, secondary]
            step = _append_multi_block_layer(
                events, step=step, token_id=token_id, layer_id=layer_id,
                block_ids=block_ids, kv_block_size_bytes=kv_block_size_bytes,
            )
    return events


def generate_cold_fanout_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    kv_block_size_bytes: int = 1_048_576,
    history_span_blocks: int = 256,
    fanout_stride: int = 29,
) -> list[AccessEvent]:
    events: list[AccessEvent] = []
    step = 0
    for token_id in range(tokens):
        current_block = token_id // 2
        for layer_id in range(layers):
            if token_id < 4:
                block_ids = [current_block]
            else:
                primary = (
                    token_id * fanout_stride
                    + layer_id * (fanout_stride + 8)
                    + (token_id % 5) * 37
                ) % max(history_span_blocks, current_block + 32)
                block_ids = [
                    primary,
                    (primary + 41) % max(history_span_blocks, current_block + 64),
                    (primary + 97 + layer_id) % max(history_span_blocks, current_block + 96),
                ]
            step = _append_multi_block_layer(
                events, step=step, token_id=token_id, layer_id=layer_id,
                block_ids=block_ids, kv_block_size_bytes=kv_block_size_bytes,
            )
    return events


# ---- New workloads ---------------------------------------------------------


def generate_weight_layer_trace(
    *,
    tokens: int = 32,
    layers: int = 32,
    weight_tile_size_bytes: int = 4_194_304,
    tiles_per_layer: int = 16,
    flash_bundle_prefix: str = "weight",
) -> list[AccessEvent]:
    events: list[AccessEvent] = []
    step = 0
    for token_id in range(tokens):
        for layer_id in range(layers):
            for tile in range(tiles_per_layer):
                object_id = f"{flash_bundle_prefix}.layer_{layer_id:03d}.tile_{tile:03d}"
                events.append(
                    AccessEvent(
                        step=step, token_id=token_id, layer_id=layer_id,
                        object_id=object_id, object_type="WEIGHT_TILE",
                        size_bytes=weight_tile_size_bytes,
                        deadline_step=step + 1, is_critical=True,
                    )
                )
                step += 1
    return events


def generate_moe_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    experts_per_layer: int = 64,
    expert_page_size_bytes: int = 1_048_576,
    top_k: int = 2,
    entropy: float = 0.2,
    seed: int = 42,
) -> list[AccessEvent]:
    rng = _random.Random(seed)
    events: list[AccessEvent] = []
    step = 0
    active_experts: list[int] = []
    for token_id in range(tokens):
        if entropy < 0.3:
            stable = rng.sample(range(experts_per_layer), top_k * 2)
            active_experts = stable[:top_k]
        for layer_id in range(layers):
            if entropy >= 0.3:
                chosen = rng.sample(range(experts_per_layer), min(top_k, experts_per_layer))
            else:
                chosen = active_experts if active_experts else rng.sample(range(experts_per_layer), top_k)
            for expert_id in chosen:
                object_id = f"expert.layer_{layer_id:03d}.expert_{expert_id:03d}"
                events.append(
                    AccessEvent(
                        step=step, token_id=token_id, layer_id=layer_id,
                        object_id=object_id, object_type="EXPERT_PAGE",
                        size_bytes=expert_page_size_bytes,
                        deadline_step=step + 1, is_critical=True,
                    )
                )
                step += 1
    return events


def generate_rag_staging_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    retrieval_chunks: int = 32,
    chunk_size_bytes: int = 524_288,
    kv_block_size_bytes: int = 1_048_576,
    prefill_steps: int = 16,
    seed: int = 42,
) -> list[AccessEvent]:
    rng = _random.Random(seed)
    events: list[AccessEvent] = []
    step = 0
    for chunk_id in range(retrieval_chunks):
        object_id = f"rag.chunk_{chunk_id:03d}"
        events.append(
            AccessEvent(
                step=step, token_id=-1, layer_id=0,
                object_id=object_id, object_type="RETRIEVAL_CHUNK",
                size_bytes=chunk_size_bytes,
                deadline_step=prefill_steps, is_critical=False,
            )
        )
        step += 1
    while step < prefill_steps:
        step += 1
    for token_id in range(tokens):
        accessed_chunks = rng.sample(range(retrieval_chunks), max(1, retrieval_chunks // 8))
        for chunk_id in accessed_chunks:
            object_id = f"rag.chunk_{chunk_id:03d}"
            events.append(
                AccessEvent(
                    step=step, token_id=token_id, layer_id=0,
                    object_id=object_id, object_type="RETRIEVAL_CHUNK",
                    size_bytes=chunk_size_bytes,
                    deadline_step=step + 1, is_critical=True,
                )
            )
            step += 1
        for layer_id in range(layers):
            block_id = token_id // 2
            object_id = f"kv.session_0.layer_{layer_id}.block_{block_id}"
            events.append(
                AccessEvent(
                    step=step, token_id=token_id, layer_id=layer_id,
                    object_id=object_id, object_type="KV_BLOCK",
                    size_bytes=kv_block_size_bytes,
                    deadline_step=step + 1, is_critical=True,
                )
            )
            step += 1
    return events
