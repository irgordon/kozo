from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "fixed_user_mapping_foundation.v0.json"

PRESENT = 1 << 0
WRITABLE = 1 << 1
USER = 1 << 2
NX = 1 << 63


@dataclass(frozen=True)
class FixedUserMappingFoundation:
    version: int
    architecture: str
    source_files: dict[str, str]
    paging: dict[str, Any]
    page_tables: dict[str, Any]
    kernel_regions: tuple[dict[str, Any], ...]
    user_regions: tuple[dict[str, Any], ...]
    permission_policy: dict[str, Any]
    activation: dict[str, Any]
    software_walk: dict[str, Any]
    survival_probe: dict[str, Any]
    success_markers: tuple[str, ...]
    failure_statuses: dict[str, int]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


@dataclass(frozen=True)
class EffectivePagePermissions:
    present: bool
    user_accessible: bool
    writable: bool
    executable: bool


def load_fixed_user_mapping_foundation(
    path: Path = CONTRACT_PATH,
) -> FixedUserMappingFoundation:
    data = json.loads(path.read_text())
    validate_named_document("fixed_user_mapping_foundation", data)
    return _parse_contract(data)


def effective_page_permissions(entries: Iterable[int]) -> EffectivePagePermissions:
    values = tuple(entries)
    if len(values) != 4:
        raise ValueError("four-level paging requires exactly four entries")
    return EffectivePagePermissions(
        present=all(value & PRESENT for value in values),
        user_accessible=all(value & USER for value in values),
        writable=all(value & WRITABLE for value in values),
        executable=not any(value & NX for value in values),
    )


def _parse_contract(data: dict[str, Any]) -> FixedUserMappingFoundation:
    return FixedUserMappingFoundation(
        version=data["version"],
        architecture=data["architecture"],
        source_files=dict(data["source_files"]),
        paging=dict(data["paging"]),
        page_tables=dict(data["page_tables"]),
        kernel_regions=tuple(dict(region) for region in data["kernel_regions"]),
        user_regions=tuple(dict(region) for region in data["user_regions"]),
        permission_policy=dict(data["permission_policy"]),
        activation=dict(data["activation"]),
        software_walk=dict(data["software_walk"]),
        survival_probe=dict(data["survival_probe"]),
        success_markers=tuple(data["success_markers"]),
        failure_statuses=dict(data["failure_statuses"]),
        claim_boundary={
            key: tuple(values)
            for key, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )
