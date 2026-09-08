from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExternalModelRegister(BaseModel):
    artifact_path: str = Field(min_length=1)


class ExternalModelResponse(BaseModel):
    id: str
    name: str
    target: str
    framework: str
    artifact_path: str
    version: str | None
    feature_schema: dict[str, Any]
    metrics: dict[str, Any]
    checksum: str
    status: str
    provenance: dict[str, Any]
    model_config = ConfigDict(from_attributes=True)
