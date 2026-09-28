from types import SimpleNamespace

from app.services.simulation_provenance import (
    SimulationProvenanceClass as Origin,
    classify_simulation_provenance,
    public_origin,
)


def test_legacy_south_fork_experiment_id_overrides_inherited_executed_label():
    sim = SimpleNamespace(
        name="A name is not evidence",
        provenance={
            "experiment_id": "south-fork-final-coupled-2015-2020",
            "evidence_type": "REAL_SWAT_PLUS",
        },
        requested_config={"swat_plus": {"run_type": "SWAT_MULTISCALE_COUPLED"}},
    )

    assert classify_simulation_provenance(sim) is Origin.HISTORICAL_IMPORT
    assert public_origin(Origin.HISTORICAL_IMPORT) == "HISTORICAL_IMPORT"


def test_new_historical_import_is_classified_before_any_run_type_or_evidence():
    assert classify_simulation_provenance({
        "source_kind": "HISTORICAL_IMPORT", "evidence_type": "REAL_SWAT_PLUS_COUPLED",
    }) is Origin.HISTORICAL_IMPORT


def test_real_swat_and_coupled_runs_have_distinct_classes():
    assert classify_simulation_provenance({"evidence_type": "REAL_SWAT_PLUS"}) is Origin.SWAT_EXECUTED
    assert classify_simulation_provenance({"evidence_type": "REAL_SWAT_PLUS_COUPLED"}) is Origin.COUPLED_EXECUTED


def test_simplified_and_unknown_runs_do_not_claim_a_real_swat_execution():
    simplified = {"hydrology": {"model": "SimplifiedHydrologyModel"}}
    unknown = {"evidence_type": "LEGACY_UNKNOWN"}
    assert classify_simulation_provenance(simplified) is Origin.SIMPLIFIED
    assert classify_simulation_provenance(unknown) is Origin.UNKNOWN
    assert public_origin(Origin.SIMPLIFIED) == "EXECUTED"
    assert public_origin(Origin.UNKNOWN) == "UNKNOWN"


def test_legacy_experiment_name_alone_is_not_a_historical_classification():
    sim = SimpleNamespace(name="south-fork-final-coupled-2015-2020", provenance={"evidence_type": "LEGACY_UNKNOWN"})
    assert classify_simulation_provenance(sim) is Origin.UNKNOWN
