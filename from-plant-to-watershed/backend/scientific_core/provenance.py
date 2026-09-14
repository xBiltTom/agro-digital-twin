from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class EvidenceType(str, Enum):
    SIMPLIFIED = "SIMPLIFIED"
    SYNTHETIC = "SYNTHETIC"
    DEMO = "DEMO"
    ILLUSTRATIVE = "ILLUSTRATIVE"
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"


@dataclass(frozen=True)
class Provenance:
    model: str
    implementation_version: str
    evidence_type: EvidenceType
    spatial_support: str
    temporal_support: str
    units: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_type"] = self.evidence_type.value
        return value
