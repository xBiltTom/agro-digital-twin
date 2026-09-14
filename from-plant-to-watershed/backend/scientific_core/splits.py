"""Reproducible spatial and chronological splits for observational evaluation."""

from __future__ import annotations

from datetime import date
from typing import Iterable, Mapping


VALID_SPLITS = frozenset({"TRAIN", "VALIDATION", "TEST"})


def assign_temporal_split(
    dates: Iterable[str | date], *, train_end: str | date, validation_end: str | date,
) -> dict[str, str]:
    """Assign each *unique* date to a chronological split without row leakage."""
    def parse(value: str | date) -> str:
        iso = value.isoformat() if isinstance(value, date) else str(value)
        try:
            date.fromisoformat(iso)
        except ValueError as exc:
            raise ValueError(f"invalid ISO date {iso!r}") from exc
        return iso

    normalized_dates = [parse(item) for item in dates]
    if len(normalized_dates) != len(set(normalized_dates)):
        raise ValueError("temporal split requires one row per unique date")
    train_boundary, validation_boundary = parse(train_end), parse(validation_end)
    if train_boundary >= validation_boundary:
        raise ValueError("train_end must be strictly before validation_end")
    assigned = {
        item: "TRAIN" if item <= train_boundary else "VALIDATION" if item <= validation_boundary else "TEST"
        for item in normalized_dates
    }
    present = set(assigned.values())
    if present != VALID_SPLITS:
        raise ValueError("temporal split requires non-empty TRAIN, VALIDATION, and TEST date groups")
    return assigned


def validate_spatial_split(assignments: Mapping[str, str]) -> dict[str, tuple[str, ...]]:
    """Validate a watershed-level split; a watershed has one, and only one, role."""
    if not assignments:
        raise ValueError("spatial split requires at least one watershed")
    if any(not watershed_id.strip() for watershed_id in assignments):
        raise ValueError("spatial split contains an empty watershed id")
    unknown = {split for split in assignments.values() if split not in VALID_SPLITS}
    if unknown:
        raise ValueError(f"unknown spatial split labels: {sorted(unknown)}")
    grouped = {split: tuple(sorted(watershed for watershed, role in assignments.items() if role == split)) for split in sorted(VALID_SPLITS)}
    if not grouped["TEST"]:
        raise ValueError("spatial split requires at least one held-out TEST watershed")
    return grouped
