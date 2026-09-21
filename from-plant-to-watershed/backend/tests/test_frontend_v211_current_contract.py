"""Static regression checks for the current-contract scientific UI.

The components are intentionally checked as source because their correct
NOT_EXECUTED branch must not need a browser or historical report fixture.
"""

from pathlib import Path


ROOT = Path(__file__).parents[2]
SCIENTIFIC_UI = (
    ROOT / "frontend/src/app/(dashboard)/page.tsx",
    ROOT / "frontend/src/app/(dashboard)/reports/page.tsx",
    ROOT / "frontend/src/app/(dashboard)/simulations/page.tsx",
    ROOT / "frontend/src/components/scientific/HypothesisValidationPanel.tsx",
    ROOT / "frontend/src/components/scientific/ClimateScenariosPanel.tsx",
    ROOT / "frontend/src/components/scientific/StatisticalBatteryPanel.tsx",
)


def test_current_contract_ui_has_no_v1_metric_or_conclusion_fallbacks():
    source = "\n".join(path.read_text(encoding="utf-8") for path in SCIENTIFIC_UI)
    for stale_value in (
        "9.447", "-0.675", "-0.540", "-79.58", "0.547", "4.4e-143",
        "-25.9%", "-46.1%", "35,072", "36 pares mensuales", "100% Empates",
        "Base = Coupled", "solver produjo caudales idénticos",
    ):
        assert stale_value not in source


def test_not_executed_panels_gate_current_metrics_and_scenarios():
    hypothesis, climate, statistics = (path.read_text(encoding="utf-8") for path in SCIENTIFIC_UI[3:])
    for source in (hypothesis, climate, statistics):
        assert 'current_execution_status === "NOT_EXECUTED"' in source
        assert "current_result" in source
    assert "Escenarios v2 pendientes de ejecución" in climate
    assert "current_result.scenarios" in climate
    assert 'sobol.parameters || ["transpiration_capacity_scale"' not in statistics
