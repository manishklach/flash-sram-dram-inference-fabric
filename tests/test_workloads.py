from simulator.workloads import (
    generate_long_context_kv_trace,
    generate_random_old_context_trace,
    generate_cold_fanout_trace,
    generate_weight_layer_trace,
    generate_moe_trace,
    generate_rag_staging_trace,
)
from simulator.traces import AccessEvent


def _count_by_type(events: list[AccessEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in events:
        counts[e.object_type] = counts.get(e.object_type, 0) + 1
    return counts


def test_long_context_kv():
    events = generate_long_context_kv_trace(tokens=16, layers=4)
    assert len(events) > 0
    types = _count_by_type(events)
    assert types.get("KV_BLOCK", 0) == len(events)


def test_random_old_context():
    trace = generate_random_old_context_trace(tokens=32, layers=4)
    assert len(trace) > 0
    assert all(e.object_type == "KV_BLOCK" for e in trace)


def test_cold_fanout():
    trace = generate_cold_fanout_trace(tokens=16, layers=4)
    assert len(trace) > 0
    assert all(e.object_type == "KV_BLOCK" for e in trace)


def test_weight_layer():
    trace = generate_weight_layer_trace(tokens=2, layers=4, tiles_per_layer=8)
    expected = 2 * 4 * 8
    assert len(trace) == expected
    assert all(e.object_type == "WEIGHT_TILE" for e in trace)
    assert all(e.size_bytes == 4_194_304 for e in trace)


def test_moe_low_entropy():
    trace = generate_moe_trace(tokens=16, layers=4, entropy=0.1)
    assert len(trace) > 0
    assert all(e.object_type == "EXPERT_PAGE" for e in trace)


def test_moe_high_entropy():
    trace = generate_moe_trace(tokens=16, layers=4, entropy=0.8)
    assert len(trace) > 0
    # high entropy should produce more unique expert IDs
    high_ids = {e.step: e for e in trace}
    assert len(high_ids) > 0


def test_moe_entropy_difference():
    lo = generate_moe_trace(tokens=32, layers=4, entropy=0.1)
    hi = generate_moe_trace(tokens=32, layers=4, entropy=0.8)
    lo_experts = {(e.layer_id, e.object_id.split("_")[-1]) for e in lo}
    hi_experts = {(e.layer_id, e.object_id.split("_")[-1]) for e in hi}
    lo_unique = len(lo_experts)
    hi_unique = len(hi_experts)


def test_rag():
    trace = generate_rag_staging_trace(tokens=16, layers=4)
    assert len(trace) > 0
    types = _count_by_type(trace)
    assert "RETRIEVAL_CHUNK" in types
    assert "KV_BLOCK" in types


def test_events_have_required_fields():
    trace = generate_long_context_kv_trace(tokens=4, layers=2)
    for e in trace:
        assert e.step >= 0
        assert e.token_id >= 0
        assert e.layer_id >= 0
        assert len(e.object_id) > 0
        assert e.size_bytes > 0


def test_steps_are_monotonic():
    trace = generate_long_context_kv_trace(tokens=64, layers=8)
    steps = [e.step for e in trace]
    for i in range(1, len(steps)):
        assert steps[i] > steps[i - 1]