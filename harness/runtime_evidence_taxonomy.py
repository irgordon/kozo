from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "runtime_evidence_taxonomy.v0.json"


@dataclass(frozen=True)
class RuntimeEvidenceTaxonomy:
    version: int
    smoke_markers: tuple[str, ...]
    smoke_marker_order: tuple[str, ...]
    expected_smoke_marker: str
    smoke_outcomes: tuple[str, ...]
    blocker_categories: dict[str, str]
    qemu_smoke_blockers: tuple[str, ...]
    boot_blocker_categories: tuple[str, ...]
    kernel_elf_blockers: tuple[str, ...]
    pass_condition: dict[str, str]
    blocked_condition: dict[str, str]
    non_goals: tuple[str, ...]


def load_runtime_evidence_taxonomy(path: Path = CONTRACT_PATH) -> RuntimeEvidenceTaxonomy:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_runtime_evidence_taxonomy(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("runtime_evidence_taxonomy", data)


def parse_runtime_evidence_taxonomy(data: dict[str, Any]) -> RuntimeEvidenceTaxonomy:
    return RuntimeEvidenceTaxonomy(
        data["version"],
        tuple(data["smoke_markers"]),
        tuple(data["smoke_marker_order"]),
        data["expected_smoke_marker"],
        tuple(data["smoke_outcomes"]),
        dict(data["blocker_categories"]),
        tuple(data["qemu_smoke_blockers"]),
        tuple(data["boot_blocker_categories"]),
        tuple(data["kernel_elf_blockers"]),
        dict(data["pass_condition"]),
        dict(data["blocked_condition"]),
        tuple(data["non_goals"]),
    )


def get_smoke_marker_order() -> tuple[str, ...]:
    return load_runtime_evidence_taxonomy().smoke_marker_order


def get_expected_smoke_marker() -> str:
    return load_runtime_evidence_taxonomy().expected_smoke_marker


def get_blocker_categories() -> tuple[str, ...]:
    taxonomy = load_runtime_evidence_taxonomy()
    return tuple(taxonomy.blocker_categories.keys())


def get_smoke_outcomes() -> tuple[str, ...]:
    return load_runtime_evidence_taxonomy().smoke_outcomes


def get_qemu_smoke_blocker_categories() -> tuple[str, ...]:
    return load_runtime_evidence_taxonomy().qemu_smoke_blockers


def get_boot_blocker_categories() -> tuple[str, ...]:
    return load_runtime_evidence_taxonomy().boot_blocker_categories


def get_kernel_elf_blocker_categories() -> tuple[str, ...]:
    return load_runtime_evidence_taxonomy().kernel_elf_blockers


def is_complete_ordered_marker_sequence(markers: list[str] | tuple[str, ...]) -> bool:
    if not isinstance(markers, (list, tuple)):
        raise TypeError("markers must be a list or tuple of strings")
    if any(not isinstance(marker, str) for marker in markers):
        raise TypeError("markers must contain only strings")
    return tuple(markers) == get_smoke_marker_order()
