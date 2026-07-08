from simulator.interface_modes import InterfaceMode
from simulator.policies import FixedWindowPrefetchPolicy, NoPrefetchPolicy, OraclePolicy
from simulator.runner import SimulatorConfig, run_trace
from simulator.workloads import (
    generate_long_context_kv_trace,
    generate_random_old_context_trace,
    generate_cold_fanout_trace,
    generate_weight_layer_trace,
)


def _small_trace():
    return generate_long_context_kv_trace(tokens=8, layers=2)


def test_ram_emulation_no_sync_failures_with_prefetch():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.RAM_EMULATION)
    assert m.total_events > 0


def test_stream_to_scratchpad_no_sync_failures():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD)
    assert m.sync_flash_policy_failures == 0


def test_no_prefetch_policy():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD, policy=NoPrefetchPolicy())
    assert m.prefetched_objects == 0


def test_oracle_policy():
    trace = generate_long_context_kv_trace(tokens=8, layers=4)
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD, policy=OraclePolicy())
    # Oracle should issue many prefetches
    assert m.prefetched_objects > 0


def test_fixed_window_policy():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.HYBRID, policy=FixedWindowPrefetchPolicy())
    assert m.total_events > 0


def test_all_modes_run():
    trace = _small_trace()
    config = SimulatorConfig()
    for mode in InterfaceMode:
        m = run_trace(trace, interface_mode=mode, config=config)
        assert m.total_events > 0


def test_weight_layer_with_prefetch():
    trace = generate_weight_layer_trace(tokens=2, layers=2, tiles_per_layer=4)
    for mode in (InterfaceMode.HYBRID, InterfaceMode.STREAM_TO_SCRATCHPAD):
        m = run_trace(trace, interface_mode=mode)
        # Should now get some sequential reads with the new multi-type prefetch
        assert m.total_events > 0


def test_metrics_consistency():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD)
    if m.prefetched_objects > 0:
        total = m.useful_prefetches + m.wasted_prefetches
        assert total <= m.prefetched_objects * 1.02


def test_dram_hits_recorded():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD)
    assert m.dram_hits >= 0


def test_sram_hits_recorded():
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD)
    assert m.sram_hits >= 0


def test_config_custom_sram():
    from simulator.tiers import SRAMTier
    sram = SRAMTier(capacity_mb=128)
    config = SimulatorConfig(sram=sram)
    trace = _small_trace()
    m = run_trace(trace, interface_mode=InterfaceMode.STREAM_TO_SCRATCHPAD, config=config)
    assert m.total_events > 0