"""Contract tests for the read-only FastAPI integration."""

from src.core.integrations.fastapi_client import APIResponse, FastAPIClient, choose_preferred_simulation


def test_simulation_and_playback_pagination_are_consumed_once():
    calls = []

    def transport(method, url, **kwargs):
        calls.append((method, url, kwargs["params"]))
        if url.endswith("/simulations"):
            skip = kwargs["params"]["skip"]
            return APIResponse(200, [{"id": f"sim-{skip}"}] if skip == 0 else [])
        if url.endswith("/availability"):
            return APIResponse(200, {"provenance_class": "SIMULATION"})
        if url.endswith("/playback"):
            offset = kwargs["params"]["offset"]
            records = [{"date": f"2019-01-0{offset + 1}", "simulation_id": "sim-0"}] if offset == 0 else []
            return APIResponse(200, {"records": records, "total": 1})
        return APIResponse(200, {"id": "sim-0", "status": "COMPLETED"})

    client = FastAPIClient(token="token", transport=transport)
    assert client.list_simulations(page_size=1) == [{"id": "sim-0"}]
    snapshot = client.get_simulation_snapshot("sim-0")
    assert snapshot["playback"]["total"] == 1
    assert any("/availability" in call[1] for call in calls)
    assert any("/playback" in call[1] for call in calls)


def test_preference_is_corrected_v2_then_fallbacks():
    simulations = [
        {"id": "phase1-sf-2019-v3", "status": "COMPLETED"},
        {"id": "phase234-sf-2019-v2", "status": "COMPLETED"},
    ]
    assert choose_preferred_simulation(simulations)["id"] == "phase234-sf-2019-v2"


def test_login_keeps_token_in_memory_and_adds_bearer_header():
    requests = []

    def transport(method, url, **kwargs):
        requests.append((method, url, kwargs))
        if url.endswith("/auth/login"):
            return APIResponse(200, {"access_token": "memory-token"})
        return APIResponse(200, [])

    client = FastAPIClient(transport=transport)
    client.login("researcher@example.com", "secret")
    client.list_simulations()
    assert client.token == "memory-token"
    assert requests[0][2]["headers"].get("Authorization") is None
    assert requests[1][2]["headers"]["Authorization"] == "Bearer memory-token"
