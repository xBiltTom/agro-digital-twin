"""Read-only client for the digital-twin FastAPI simulation contracts.

Authentication tokens live only in the in-memory client instance.  The client
never writes credentials, tokens, or downloaded playback to the repository.
Playback is fetched page-by-page and cached per client so an EDA operation does
not issue one request per variable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Dict, Iterable, Mapping, Optional


class FastAPIConnectionError(RuntimeError):
    """A connection, authentication, HTTP, or contract error from FastAPI."""


@dataclass(frozen=True)
class APIResponse:
    status_code: int
    payload: Any


Transport = Callable[..., Any]


class FastAPIClient:
    """Minimal authenticated client for read-only simulation endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: Optional[str] = None,
        timeout: float = 20.0,
        transport: Optional[Transport] = None,
    ):
        normalized = base_url.rstrip("/")
        self.base_url = normalized if normalized.endswith("/api/v1") else f"{normalized}/api/v1"
        self.token = token
        self.timeout = timeout
        self._transport = transport
        self._cache: Dict[tuple, Any] = {}

    @classmethod
    def from_environment(cls) -> "FastAPIClient":
        return cls(os.environ.get("AGRO_TWIN_FASTAPI_URL", "http://localhost:8000"))

    @property
    def is_authenticated(self) -> bool:
        return bool(self.token)

    def _default_transport(self, method: str, url: str, **kwargs: Any) -> Any:
        try:
            import httpx

            with httpx.Client(timeout=self.timeout) as client:
                return client.request(method, url, **kwargs)
        except Exception as exc:  # pragma: no cover - exercised through connection tests
            raise FastAPIConnectionError(f"No se pudo conectar con FastAPI: {exc}") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
        authenticated: bool = True,
    ) -> Any:
        headers = {"Accept": "application/json"}
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        url = f"{self.base_url}/{path.lstrip('/')}"
        transport = self._transport or self._default_transport
        try:
            response = transport(method, url, headers=headers, params=params, json=json)
        except FastAPIConnectionError:
            raise
        except Exception as exc:
            raise FastAPIConnectionError(f"No se pudo conectar con FastAPI: {exc}") from exc

        if isinstance(response, APIResponse):
            status_code, payload = response.status_code, response.payload
        else:
            status_code = int(getattr(response, "status_code", 0))
            try:
                payload = response.json()
            except Exception as exc:
                raise FastAPIConnectionError("FastAPI devolvió una respuesta no JSON") from exc
        if status_code < 200 or status_code >= 300:
            detail = payload.get("detail", payload) if isinstance(payload, Mapping) else payload
            raise FastAPIConnectionError(f"FastAPI respondió HTTP {status_code}: {detail}")
        return payload

    def login(self, email: str, password: str) -> Mapping[str, Any]:
        """Authenticate using FastAPI's JSON login contract; never persist secrets."""
        if not email.strip() or not password:
            raise FastAPIConnectionError("El correo y la contraseña son obligatorios")
        payload = self._request(
            "POST",
            "/auth/login",
            json={"email": email.strip(), "password": password},
            authenticated=False,
        )
        token = payload.get("access_token") if isinstance(payload, Mapping) else None
        if not token:
            raise FastAPIConnectionError("La respuesta de login no contiene access_token")
        self.token = str(token)
        return payload

    def list_simulations(self, page_size: int = 100, max_pages: int = 100) -> list[Mapping[str, Any]]:
        """Retrieve every visible simulation using the API's skip/limit pagination."""
        cache_key = ("simulations", page_size, max_pages)
        if cache_key in self._cache:
            return list(self._cache[cache_key])
        simulations: list[Mapping[str, Any]] = []
        skip = 0
        for _ in range(max_pages):
            page = self._request("GET", "/simulations", params={"skip": skip, "limit": page_size})
            if not isinstance(page, list):
                raise FastAPIConnectionError("El catálogo de simulaciones no tiene formato de lista")
            simulations.extend(page)
            if len(page) < page_size:
                break
            skip += len(page)
        else:
            raise FastAPIConnectionError("Se alcanzó el máximo de páginas de simulaciones")
        self._cache[cache_key] = list(simulations)
        return simulations

    def get_availability(self, simulation_id: str, on: Optional[date] = None) -> Mapping[str, Any]:
        params = {"date": on.isoformat()} if on else None
        key = ("availability", simulation_id, params.get("date") if params else None)
        if key not in self._cache:
            self._cache[key] = self._request("GET", f"/simulations/{simulation_id}/availability", params=params)
        return self._cache[key]

    def get_playback(
        self,
        simulation_id: str,
        *,
        resolution: Optional[str] = "DAILY",
        start: Optional[date] = None,
        end: Optional[date] = None,
        page_size: int = 500,
        max_pages: int = 100,
    ) -> Mapping[str, Any]:
        """Retrieve one playback stream with offset pagination and one cache key."""
        cache_key = (
            "playback", simulation_id, resolution,
            start.isoformat() if start else None,
            end.isoformat() if end else None,
            page_size,
        )
        if cache_key in self._cache:
            return self._cache[cache_key]
        records: list[Mapping[str, Any]] = []
        offset = 0
        first_page: Optional[Mapping[str, Any]] = None
        for _ in range(max_pages):
            params: Dict[str, Any] = {"offset": offset, "limit": page_size}
            if resolution:
                params["resolution"] = resolution
            if start:
                params["start"] = start.isoformat()
            if end:
                params["end"] = end.isoformat()
            page = self._request("GET", f"/simulations/{simulation_id}/playback", params=params)
            if not isinstance(page, Mapping) or not isinstance(page.get("records", []), list):
                raise FastAPIConnectionError("El playback no tiene el contrato esperado")
            if first_page is None:
                first_page = page
            records.extend(page["records"])
            total = int(page.get("total", len(records)))
            if not page["records"] or len(records) >= total:
                break
            offset += len(page["records"])
        else:
            raise FastAPIConnectionError("Se alcanzó el máximo de páginas de playback")

        result = dict(first_page or {})
        result["records"] = records
        result["offset"] = 0
        result["limit"] = len(records)
        result["total"] = len(records)
        self._cache[cache_key] = result
        return result

    def get_simulation_snapshot(
        self,
        simulation_id: str,
        *,
        resolution: str = "DAILY",
        simulation: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """Fetch availability and playback using only confirmed read endpoints."""
        key = ("snapshot", simulation_id, resolution)
        if key not in self._cache:
            self._cache[key] = {
                "simulation": dict(simulation or {"id": simulation_id}),
                "availability": self.get_availability(simulation_id),
                "playback": self.get_playback(simulation_id, resolution=resolution),
            }
        return self._cache[key]

    def clear_cache(self) -> None:
        self._cache.clear()


def choose_preferred_simulation(simulations: Iterable[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    """Prefer corrected phase234 v2, then v1, then a completed compatible run."""
    items = list(simulations)
    preferred_tokens = ("phase234-sf-2019-v2", "phase234-sf-2019-v1", "phase1-sf-2019-v3")
    for token in preferred_tokens:
        for simulation in items:
            identity = " ".join(str(simulation.get(key, "")) for key in ("id", "name", "external_model_id"))
            if token.lower() in identity.lower():
                return simulation
    completed = [item for item in items if str(item.get("status", "")).upper() == "COMPLETED"]
    return completed[0] if completed else (items[0] if items else None)
