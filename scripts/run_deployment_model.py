from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SWEEP_ARTIFACT = REPO_ROOT / "benchmarks" / "results" / "lookahead_dram_sweep.csv"
ARTIFACT_DIR = REPO_ROOT / "benchmarks" / "results"
CSV_ARTIFACT = ARTIFACT_DIR / "deployment_economics.csv"
JSON_ARTIFACT = ARTIFACT_DIR / "deployment_economics.json"


@dataclass(frozen=True)
class SweepRow:
    workload: str
    mode: str
    dram_capacity_mb: int
    lookahead_steps: int
    p50_token_latency_us: float
    p95_token_latency_us: float
    p99_token_latency_us: float
    sequential_read_ratio: float
    sync_flash_policy_failures: float
    dram_evictions: float
    prefetch_accuracy: float
    prefetch_waste_rate: float
    sync_flash_miss_rate: float


@dataclass(frozen=True)
class Scenario:
    name: str
    workload: str
    description: str
    preferred_modes: tuple[str, ...]
    max_p95_us: float
    max_sync_miss_rate: float
    max_prefetch_waste_rate: float
    baseline_system_capex_usd: float
    baseline_energy_j_per_million_tokens: float
    fabric_host_capex_usd: float
    fabric_accelerator_capex_usd: float
    fabric_nvme_tb: float
    fabric_dram_gb: float
    fabric_energy_floor_j_per_million_tokens: float
    random_energy_penalty_j_per_million_tokens: float
    miss_energy_penalty_j_per_million_tokens: float
    daily_token_volume_millions: float
    notes: str


@dataclass(frozen=True)
class DeploymentResult:
    scenario: str
    viable: bool
    workload: str
    description: str
    selected_mode: str | None
    dram_capacity_mb: int | None
    lookahead_steps: int | None
    p95_token_latency_us: float | None
    p99_token_latency_us: float | None
    sequential_read_ratio: float | None
    sync_flash_miss_rate: float | None
    prefetch_waste_rate: float | None
    fabric_capex_usd: float | None
    baseline_capex_usd: float
    capex_savings_pct: float | None
    fabric_energy_j_per_million_tokens: float | None
    baseline_energy_j_per_million_tokens: float
    fabric_three_year_energy_cost_usd: float | None
    baseline_three_year_energy_cost_usd: float
    fabric_three_year_tco_usd: float | None
    baseline_three_year_tco_usd: float
    three_year_tco_savings_pct: float | None
    notes: str


POWER_PRICE_PER_KWH = 0.12
DRAM_COST_PER_GB_USD = 3.5
NVME_COST_PER_TB_USD = 120.0
DAYS_PER_YEAR = 365
YEARS = 3
JOULES_PER_KWH = 3_600_000


SCENARIOS = (
    Scenario(
        name="enterprise_rag_long_context",
        workload="long_context_kv",
        description="Private long-context RAG appliance where predictable KV reuse dominates.",
        preferred_modes=("stream_to_scratchpad", "hybrid"),
        max_p95_us=3_000.0,
        max_sync_miss_rate=0.02,
        max_prefetch_waste_rate=0.98,
        baseline_system_capex_usd=18_500.0,
        baseline_energy_j_per_million_tokens=2_880.0,
        fabric_host_capex_usd=3_500.0,
        fabric_accelerator_capex_usd=5_000.0,
        fabric_nvme_tb=4.0,
        fabric_dram_gb=128.0,
        fabric_energy_floor_j_per_million_tokens=755.0,
        random_energy_penalty_j_per_million_tokens=1_200.0,
        miss_energy_penalty_j_per_million_tokens=400.0,
        daily_token_volume_millions=100.0,
        notes="Best fit for the current architecture because the trace is structured and flash can stay hidden.",
    ),
    Scenario(
        name="persistent_assistant_sessions",
        workload="random_old_context",
        description="Many resumable assistant sessions with colder context revivals and larger staging windows.",
        preferred_modes=("stream_to_scratchpad", "hybrid"),
        max_p95_us=4_600.0,
        max_sync_miss_rate=0.03,
        max_prefetch_waste_rate=0.98,
        baseline_system_capex_usd=19_500.0,
        baseline_energy_j_per_million_tokens=3_600.0,
        fabric_host_capex_usd=3_800.0,
        fabric_accelerator_capex_usd=6_500.0,
        fabric_nvme_tb=8.0,
        fabric_dram_gb=192.0,
        fabric_energy_floor_j_per_million_tokens=1_150.0,
        random_energy_penalty_j_per_million_tokens=2_100.0,
        miss_energy_penalty_j_per_million_tokens=700.0,
        daily_token_volume_millions=120.0,
        notes="The fabric can work here, but only when DRAM depth and predictor horizon both increase.",
    ),
    Scenario(
        name="cold_fanout_retrieval",
        workload="cold_fanout",
        description="Adversarial cold fan-out where locality is weak and the fabric is expected to struggle.",
        preferred_modes=("stream_to_scratchpad", "hybrid"),
        max_p95_us=6_000.0,
        max_sync_miss_rate=0.10,
        max_prefetch_waste_rate=0.75,
        baseline_system_capex_usd=20_000.0,
        baseline_energy_j_per_million_tokens=4_100.0,
        fabric_host_capex_usd=4_000.0,
        fabric_accelerator_capex_usd=7_000.0,
        fabric_nvme_tb=8.0,
        fabric_dram_gb=256.0,
        fabric_energy_floor_j_per_million_tokens=1_600.0,
        random_energy_penalty_j_per_million_tokens=3_000.0,
        miss_energy_penalty_j_per_million_tokens=900.0,
        daily_token_volume_millions=120.0,
        notes="This is intentionally a negative-control business case. If no viable row is found, the baseline stays the recommendation.",
    ),
)


def _read_sweep_rows() -> list[SweepRow]:
    with SWEEP_ARTIFACT.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                SweepRow(
                    workload=row["workload"],
                    mode=row["mode"],
                    dram_capacity_mb=int(row["dram_capacity_mb"]),
                    lookahead_steps=int(row["lookahead_steps"]),
                    p50_token_latency_us=float(row["p50_token_latency_us"]),
                    p95_token_latency_us=float(row["p95_token_latency_us"]),
                    p99_token_latency_us=float(row["p99_token_latency_us"]),
                    sequential_read_ratio=float(row["sequential_read_ratio"]),
                    sync_flash_policy_failures=float(row["sync_flash_policy_failures"]),
                    dram_evictions=float(row["dram_evictions"]),
                    prefetch_accuracy=float(row["prefetch_accuracy"]),
                    prefetch_waste_rate=float(row["prefetch_waste_rate"]),
                    sync_flash_miss_rate=float(row["sync_flash_miss_rate"]),
                )
            )
    return rows


def _energy_cost_usd(joules_per_million_tokens: float, daily_token_volume_millions: float) -> float:
    total_joules = joules_per_million_tokens * daily_token_volume_millions * DAYS_PER_YEAR * YEARS
    return (total_joules / JOULES_PER_KWH) * POWER_PRICE_PER_KWH


def _fabric_capex_usd(scenario: Scenario) -> float:
    return (
        scenario.fabric_host_capex_usd
        + scenario.fabric_accelerator_capex_usd
        + (scenario.fabric_dram_gb * DRAM_COST_PER_GB_USD)
        + (scenario.fabric_nvme_tb * NVME_COST_PER_TB_USD)
    )


def _fabric_energy_j_per_million_tokens(scenario: Scenario, row: SweepRow) -> float:
    return (
        scenario.fabric_energy_floor_j_per_million_tokens
        + (1.0 - row.sequential_read_ratio) * scenario.random_energy_penalty_j_per_million_tokens
        + row.sync_flash_miss_rate * scenario.miss_energy_penalty_j_per_million_tokens
    )


def _row_is_viable(scenario: Scenario, row: SweepRow) -> bool:
    return (
        row.workload == scenario.workload
        and row.mode in scenario.preferred_modes
        and row.p95_token_latency_us <= scenario.max_p95_us
        and row.sync_flash_miss_rate <= scenario.max_sync_miss_rate
        and row.prefetch_waste_rate <= scenario.max_prefetch_waste_rate
    )


def _score_candidate(scenario: Scenario, row: SweepRow) -> tuple[float, float, float, int]:
    energy = _fabric_energy_j_per_million_tokens(scenario, row)
    return (energy, row.p95_token_latency_us, -row.sequential_read_ratio, row.lookahead_steps)


def _build_result(scenario: Scenario, row: SweepRow | None) -> DeploymentResult:
    baseline_energy_cost = _energy_cost_usd(
        scenario.baseline_energy_j_per_million_tokens, scenario.daily_token_volume_millions
    )
    baseline_tco = scenario.baseline_system_capex_usd + baseline_energy_cost

    if row is None:
        return DeploymentResult(
            scenario=scenario.name,
            viable=False,
            workload=scenario.workload,
            description=scenario.description,
            selected_mode=None,
            dram_capacity_mb=None,
            lookahead_steps=None,
            p95_token_latency_us=None,
            p99_token_latency_us=None,
            sequential_read_ratio=None,
            sync_flash_miss_rate=None,
            prefetch_waste_rate=None,
            fabric_capex_usd=None,
            baseline_capex_usd=scenario.baseline_system_capex_usd,
            capex_savings_pct=None,
            fabric_energy_j_per_million_tokens=None,
            baseline_energy_j_per_million_tokens=scenario.baseline_energy_j_per_million_tokens,
            fabric_three_year_energy_cost_usd=None,
            baseline_three_year_energy_cost_usd=baseline_energy_cost,
            fabric_three_year_tco_usd=None,
            baseline_three_year_tco_usd=baseline_tco,
            three_year_tco_savings_pct=None,
            notes=scenario.notes,
        )

    fabric_capex = _fabric_capex_usd(scenario)
    fabric_energy = _fabric_energy_j_per_million_tokens(scenario, row)
    fabric_energy_cost = _energy_cost_usd(fabric_energy, scenario.daily_token_volume_millions)
    fabric_tco = fabric_capex + fabric_energy_cost
    capex_savings_pct = 100.0 * (scenario.baseline_system_capex_usd - fabric_capex) / scenario.baseline_system_capex_usd
    tco_savings_pct = 100.0 * (baseline_tco - fabric_tco) / baseline_tco

    return DeploymentResult(
        scenario=scenario.name,
        viable=True,
        workload=scenario.workload,
        description=scenario.description,
        selected_mode=row.mode,
        dram_capacity_mb=row.dram_capacity_mb,
        lookahead_steps=row.lookahead_steps,
        p95_token_latency_us=row.p95_token_latency_us,
        p99_token_latency_us=row.p99_token_latency_us,
        sequential_read_ratio=row.sequential_read_ratio,
        sync_flash_miss_rate=row.sync_flash_miss_rate,
        prefetch_waste_rate=row.prefetch_waste_rate,
        fabric_capex_usd=fabric_capex,
        baseline_capex_usd=scenario.baseline_system_capex_usd,
        capex_savings_pct=capex_savings_pct,
        fabric_energy_j_per_million_tokens=fabric_energy,
        baseline_energy_j_per_million_tokens=scenario.baseline_energy_j_per_million_tokens,
        fabric_three_year_energy_cost_usd=fabric_energy_cost,
        baseline_three_year_energy_cost_usd=baseline_energy_cost,
        fabric_three_year_tco_usd=fabric_tco,
        baseline_three_year_tco_usd=baseline_tco,
        three_year_tco_savings_pct=tco_savings_pct,
        notes=scenario.notes,
    )


def main() -> None:
    rows = _read_sweep_rows()
    results: list[DeploymentResult] = []

    print(
        "scenario,viable,mode,dram_capacity_mb,lookahead_steps,p95_us,seq_ratio,sync_miss_rate,fabric_capex_usd,baseline_capex_usd,fabric_tco_3y_usd,baseline_tco_3y_usd,tco_savings_pct"
    )
    for scenario in SCENARIOS:
        candidates = [row for row in rows if _row_is_viable(scenario, row)]
        selected = min(candidates, key=lambda row: _score_candidate(scenario, row)) if candidates else None
        result = _build_result(scenario, selected)
        results.append(result)

        print(
            ",".join(
                [
                    result.scenario,
                    str(result.viable).lower(),
                    result.selected_mode or "none",
                    str(result.dram_capacity_mb or 0),
                    str(result.lookahead_steps or 0),
                    f"{result.p95_token_latency_us:.1f}" if result.p95_token_latency_us is not None else "nan",
                    f"{result.sequential_read_ratio:.3f}" if result.sequential_read_ratio is not None else "nan",
                    f"{result.sync_flash_miss_rate:.4f}" if result.sync_flash_miss_rate is not None else "nan",
                    f"{result.fabric_capex_usd:.0f}" if result.fabric_capex_usd is not None else "nan",
                    f"{result.baseline_capex_usd:.0f}",
                    f"{result.fabric_three_year_tco_usd:.0f}" if result.fabric_three_year_tco_usd is not None else "nan",
                    f"{result.baseline_three_year_tco_usd:.0f}",
                    f"{result.three_year_tco_savings_pct:.1f}" if result.three_year_tco_savings_pct is not None else "nan",
                ]
            )
        )

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_ARTIFACT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))

    with JSON_ARTIFACT.open("w", encoding="utf-8") as handle:
        json.dump([asdict(result) for result in results], handle, indent=2)

    print()
    print(f"# Wrote artifacts: {CSV_ARTIFACT.relative_to(REPO_ROOT)}")
    print(f"# Wrote artifacts: {JSON_ARTIFACT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
