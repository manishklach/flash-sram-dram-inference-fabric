from simulator.metrics import StreamingMetrics, percentile


def test_percentile_empty():
    assert percentile([], 0.5) == 0.0


def test_percentile_single():
    assert percentile([42.0], 0.5) == 42.0


def test_percentile_median():
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5) == 3.0


def test_percentile_p95():
    vals = [float(i) for i in range(100)]
    p95 = percentile(vals, 0.95)
    assert 94.0 <= p95 <= 95.0


def test_as_dict_keys():
    m = StreamingMetrics()
    d = m.as_dict()
    assert "p50_token_latency_us" in d
    assert "prefetch_accuracy" in d
    assert "prefetch_waste_rate" in d
    assert "energy_joules" in d


def test_record_read():
    m = StreamingMetrics()
    m.record_read(4096, sequential=True)
    assert m.sequential_flash_reads == 1
    assert m.total_read_size_bytes == 4096
    m.record_read(4096, sequential=False)
    assert m.random_flash_reads == 1


def test_recompute_ratios():
    m = StreamingMetrics()
    m.sequential_flash_reads = 3
    m.random_flash_reads = 1
    m.recompute_ratios()
    assert m.sequential_read_ratio == 0.75


def test_prefetch_accuracy():
    m = StreamingMetrics()
    m.prefetched_objects = 100
    m.useful_prefetches = 42
    d = m.as_dict()
    assert d["prefetch_accuracy"] == 0.42


def test_waste_and_accuracy_sum():
    m = StreamingMetrics()
    m.prefetched_objects = 100
    m.useful_prefetches = 30
    m.wasted_prefetches = 70
    d = m.as_dict()
    assert abs(d["prefetch_accuracy"] + d["prefetch_waste_rate"] - 1.0) < 0.001


def test_zero_prefetch():
    m = StreamingMetrics()
    d = m.as_dict()
    assert d["prefetch_accuracy"] == 0.0
    assert d["prefetch_waste_rate"] == 0.0


def test_token_latency_stats():
    m = StreamingMetrics()
    m.token_latencies_us = [100.0, 200.0, 300.0, 400.0, 500.0]
    d = m.as_dict()
    assert d["p50_token_latency_us"] == 300.0