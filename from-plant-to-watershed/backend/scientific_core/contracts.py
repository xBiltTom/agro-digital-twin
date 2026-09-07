from typing import Any, Mapping, Protocol, Sequence


class PlantModel(Protocol):
    def compute_daily_plant_step(self, **forcing: float) -> Mapping[str, Any]: ...


class ClimateProvider(Protocol):
    def generate_daily_weather(self, **controls: float) -> Sequence[Mapping[str, Any]]: ...


class HydrologyModel(Protocol):
    def calculate_daily_step(self, **fluxes: float) -> Mapping[str, Any]: ...
