from __future__ import annotations

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


def generate_long_context_kv_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    kv_block_size_bytes: int = 1_048_576,
    local_window: int = 4,
    cold_block_every: int = 11,
) -> list[AccessEvent]:
    """Generate a synthetic decode-style trace with mostly local KV access."""

    events: list[AccessEvent] = []
    step = 0

    for token_id in range(tokens):
        current_block = token_id // 2
        for layer_id in range(layers):
            base_block = max(0, current_block - (token_id % max(1, local_window)))
            block_id = base_block

            # Inject occasional cold lookups to expose policy differences.
            if token_id > local_window and token_id % cold_block_every == 0 and layer_id % 3 == 0:
                block_id = max(0, current_block - local_window - 8)

            _append_event(
                events,
                step=step,
                token_id=token_id,
                layer_id=layer_id,
                block_id=block_id,
                kv_block_size_bytes=kv_block_size_bytes,
            )
            step += 1

    return events


def generate_random_old_context_trace(
    *,
    tokens: int = 64,
    layers: int = 8,
    kv_block_size_bytes: int = 1_048_576,
    history_span_blocks: int = 64,
) -> list[AccessEvent]:
    """Generate a synthetic adversarial decode trace with irregular cold lookups."""

    events: list[AccessEvent] = []
    step = 0

    for token_id in range(tokens):
        current_block = token_id // 2
        for layer_id in range(layers):
            # Mix recent access with pseudo-random old-context jumps.
            if token_id < 8:
                block_id = current_block
            else:
                block_id = (token_id * 17 + layer_id * 13) % max(history_span_blocks, current_block + 1)

            _append_event(
                events,
                step=step,
                token_id=token_id,
                layer_id=layer_id,
                block_id=block_id,
                kv_block_size_bytes=kv_block_size_bytes,
            )
            step += 1

    return events
